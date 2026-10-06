"""Places service unit tests: Nominatim is mocked with httpx.MockTransport (no Internet, no real waiting)."""

import math
import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import places_service as ps  # noqa: E402


def item(name="Jardim Botânico da Universidade de Coimbra", lat="40.2075", lon="-8.4163", **extra):
    base = {
        "place_id": 1, "osm_type": "way", "osm_id": 123, "lat": lat, "lon": lon,
        "category": "leisure", "type": "garden", "name": name,
        "display_name": f"{name}, Coimbra, Portugal",
        "address": {"city": "Coimbra", "country": "Portugal", "country_code": "pt"},
        "boundingbox": ["1", "2", "3", "4"], "importance": 0.4,
    }
    base.update(extra)
    return base


COIMBRA = item("Coimbra", "40.2056", "-8.4196", category="boundary", type="administrative")
UNIVERSITY = item("Universidade de Coimbra", "40.2074", "-8.4260", category="amenity", type="university")
GARDEN = item()


class Clock:
    """Fake monotonic clock whose sleep advances time and is recorded."""

    def __init__(self):
        self.now, self.sleeps = 1000.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make_service(payload=None, handler=None, **kwargs):
    """A service over a mock transport; returns it, the requests it made and the fake clock."""

    requests, clock = [], Clock()

    def respond(request):
        requests.append(request)
        if handler is not None:
            return handler(request)
        return httpx.Response(200, json=payload if payload is not None else [COIMBRA])

    service = ps.PlacesService(httpx.Client(transport=httpx.MockTransport(respond)),
                               clock=clock, sleep=clock.sleep, **kwargs)
    return service, requests, clock


class SearchTests(unittest.TestCase):
    def test_search_coimbra(self):
        service, requests, _ = make_service([COIMBRA])
        result = service.search_place("Coimbra")
        self.assertEqual(result["query"], "Coimbra")
        self.assertEqual(result["results"][0]["name"], "Coimbra")
        self.assertAlmostEqual(result["results"][0]["latitude"], 40.2056)
        self.assertEqual(requests[0].url.params["q"], "Coimbra")

    def test_search_jardim_botanico(self):
        service, _, _ = make_service([GARDEN])
        place = service.search_place("Jardim Botânico da Universidade de Coimbra", "pt")["results"][0]
        self.assertEqual(place["name"], "Jardim Botânico da Universidade de Coimbra")
        self.assertEqual((place["category"], place["type"]), ("leisure", "garden"))
        self.assertEqual(place["address"]["city"], "Coimbra")
        self.assertAlmostEqual(place["longitude"], -8.4163)

    def test_country_code_is_sent_as_countrycodes(self):
        service, requests, _ = make_service([GARDEN])
        result = service.search_place("Jardim Botânico", "PT")
        self.assertEqual(requests[0].url.params["countrycodes"], "pt")
        self.assertEqual(result["country_code"], "pt")

    def test_without_country_code_no_countrycodes_param(self):
        service, requests, _ = make_service([GARDEN])
        self.assertIsNone(service.search_place("Jardim Botânico")["country_code"])
        self.assertNotIn("countrycodes", requests[0].url.params)

    def test_recommended_nominatim_parameters(self):
        service, requests, _ = make_service([GARDEN])
        service.search_place("x")
        params = requests[0].url.params
        self.assertEqual(requests[0].url.path, "/search")  # never /details
        self.assertEqual(params["format"], "jsonv2")
        self.assertEqual(params["addressdetails"], "1")
        self.assertEqual(params["accept-language"], "pt")
        self.assertEqual(params["limit"], "3")

    def test_at_most_three_results_in_nominatim_order(self):
        many = [item(f"Local {i}", lat=f"40.{i}", lon="-8.4") for i in range(5)]
        service, _, _ = make_service(many)
        names = [r["name"] for r in service.search_place("Local")["results"]]
        self.assertEqual(names, ["Local 0", "Local 1", "Local 2"])

    def test_result_is_transformed_not_raw(self):
        service, _, _ = make_service([GARDEN])
        place = service.search_place("x")["results"][0]
        self.assertEqual(set(place), {"name", "display_name", "latitude", "longitude", "category", "type",
                                      "address", "osm_type", "osm_id"})
        self.assertIsInstance(place["latitude"], float)  # Nominatim sends strings
        self.assertEqual((place["osm_type"], place["osm_id"]), ("way", 123))
        self.assertNotIn("boundingbox", place)

    def test_name_falls_back_to_first_part_of_display_name(self):
        no_name = {k: v for k, v in GARDEN.items() if k != "name"}
        no_name["display_name"] = "Rua Larga, Coimbra, Portugal"
        service, _, _ = make_service([no_name])
        self.assertEqual(service.search_place("x")["results"][0]["name"], "Rua Larga")

    def test_attribution(self):
        service, _, _ = make_service([GARDEN])
        self.assertIn("OpenStreetMap contributors", service.search_place("x")["attribution"])


class ValidationTests(unittest.TestCase):
    def test_empty_query(self):
        service, requests, _ = make_service()
        for bad in ("", "   ", None, 5):
            with self.assertRaisesRegex(ps.PlacesError, "vazi"):
                service.search_place(bad)
        self.assertEqual(requests, [])

    def test_invalid_country_code(self):
        service, requests, _ = make_service()
        for bad in ("", "p", "prt", "p1", "é1", 12, "p t"):
            with self.assertRaisesRegex(ps.PlacesError, "country_code", msg=repr(bad)):
                service.search_place("Coimbra", bad)
        self.assertEqual(requests, [])

    def test_empty_origin_and_destination(self):
        service, requests, _ = make_service()
        with self.assertRaisesRegex(ps.PlacesError, "origem"):
            service.get_distance_between_places("", "Coimbra")
        with self.assertRaisesRegex(ps.PlacesError, "destino"):
            service.get_distance_between_places("Coimbra", " ")
        self.assertEqual(len(requests), 1)  # the valid origin was looked up before the empty destination failed


class FailureTests(unittest.TestCase):
    def test_zero_results(self):
        service, _, _ = make_service([])
        with self.assertRaisesRegex(ps.PlacesError, "não encontrado.*Xyzzy"):
            service.search_place("Xyzzy", "pt")

    def test_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout("slow", request=request)
        service, _, _ = make_service(handler=handler)
        with self.assertRaisesRegex(ps.PlacesError, "Timeout"):
            service.search_place("Coimbra")

    def test_http_failure(self):
        for status in (403, 429, 503):
            service, _, _ = make_service(handler=lambda request, s=status: httpx.Response(s))
            with self.assertRaisesRegex(ps.PlacesError, f"HTTP {status}"):
                service.search_place("Coimbra")

    def test_network_failure(self):
        def handler(request):
            raise httpx.ConnectError("down", request=request)
        service, _, _ = make_service(handler=handler)
        with self.assertRaisesRegex(ps.PlacesError, "rede"):
            service.search_place("Coimbra")

    def test_invalid_json(self):
        service, _, _ = make_service(handler=lambda request: httpx.Response(200, text="<html>"))
        with self.assertRaisesRegex(ps.PlacesError, "JSON"):
            service.search_place("Coimbra")

    def test_unexpected_shape(self):
        for payload in ({"error": "x"}, "text", 5):
            service, _, _ = make_service(payload)
            with self.assertRaisesRegex(ps.PlacesError, "inesperada"):
                service.search_place("Coimbra")

    def test_missing_required_fields(self):
        for field in ("lat", "lon", "display_name"):
            broken = {k: v for k, v in GARDEN.items() if k != field}
            service, _, _ = make_service([broken])
            with self.assertRaisesRegex(ps.PlacesError, field):
                service.search_place("x")

    def test_non_dict_result(self):
        service, _, _ = make_service(["nope"])
        with self.assertRaises(ps.PlacesError):
            service.search_place("x")

    def test_invalid_latitude(self):
        for bad in ("abc", "91", "-90.5", "nan", "inf", ""):
            service, _, _ = make_service([item(lat=bad)])
            with self.assertRaisesRegex(ps.PlacesError, "lat", msg=bad):
                service.search_place("x")

    def test_invalid_longitude(self):
        for bad in ("abc", "181", "-180.1", "nan"):
            service, _, _ = make_service([item(lon=bad)])
            with self.assertRaisesRegex(ps.PlacesError, "lon", msg=bad):
                service.search_place("x")


class UserAgentTests(unittest.TestCase):
    def test_identifiable_user_agent_is_sent(self):
        service, requests, _ = make_service([GARDEN])
        service.search_place("x")
        agent = requests[0].headers["user-agent"]
        self.assertEqual(agent, ps.USER_AGENT)
        self.assertIn("ConversationalParadigms", agent)
        self.assertNotIn("python-httpx", agent)

    def test_user_agent_is_configurable(self):
        service, requests, _ = make_service([GARDEN], user_agent="Other-App/2.0")
        service.search_place("x")
        self.assertEqual(requests[0].headers["user-agent"], "Other-App/2.0")


class CacheTests(unittest.TestCase):
    def test_repeated_query_is_served_from_cache(self):
        service, requests, _ = make_service([GARDEN])
        first = service.search_place("Jardim Botânico", "pt")
        second = service.search_place("  jardim   botânico ", "PT")  # same normalised key
        self.assertEqual(len(requests), 1)
        self.assertEqual(first["results"], second["results"])

    def test_cache_key_includes_country_code(self):
        service, requests, _ = make_service([GARDEN])
        service.search_place("Coimbra", "pt")
        service.search_place("Coimbra", "br")
        service.search_place("Coimbra")
        self.assertEqual(len(requests), 3)

    def test_failures_are_not_cached(self):
        state = {"calls": 0}

        def handler(request):
            state["calls"] += 1
            if state["calls"] == 1:
                raise httpx.ReadTimeout("slow", request=request)
            return httpx.Response(200, json=[GARDEN])
        service, requests, _ = make_service(handler=handler)
        with self.assertRaises(ps.PlacesError):
            service.search_place("Coimbra")
        self.assertEqual(service.search_place("Coimbra")["results"][0]["name"], GARDEN["name"])
        self.assertEqual(len(requests), 2)

    def test_empty_results_are_not_cached(self):
        service, requests, _ = make_service([])
        for _ in range(2):
            with self.assertRaises(ps.PlacesError):
                service.search_place("Xyzzy")
        self.assertEqual(len(requests), 2)

    def test_caller_cannot_corrupt_the_cache(self):
        service, _, _ = make_service([GARDEN])
        service.search_place("x")["results"][0]["name"] = "mutated"
        self.assertEqual(service.search_place("x")["results"][0]["name"], GARDEN["name"])


class RateLimitTests(unittest.TestCase):
    def test_first_request_does_not_wait_and_the_next_waits_one_second(self):
        service, requests, clock = make_service([GARDEN])
        service.search_place("a")
        self.assertEqual(clock.sleeps, [])
        service.search_place("b")  # distinct query, no time has passed
        self.assertEqual(len(requests), 2)
        self.assertEqual(len(clock.sleeps), 1)
        self.assertAlmostEqual(clock.sleeps[0], 1.0)

    def test_only_the_remaining_interval_is_waited(self):
        service, _, clock = make_service([GARDEN])
        service.search_place("a")
        clock.now += 0.4
        service.search_place("b")
        self.assertAlmostEqual(clock.sleeps[0], 0.6)

    def test_no_wait_when_the_interval_has_already_passed(self):
        service, _, clock = make_service([GARDEN])
        service.search_place("a")
        clock.now += 2.0
        service.search_place("b")
        self.assertEqual(clock.sleeps, [])

    def test_cache_hit_does_not_wait(self):
        service, requests, clock = make_service([GARDEN])
        service.search_place("a")
        for _ in range(3):
            service.search_place("a")
        self.assertEqual((len(requests), clock.sleeps), (1, []))

    def test_failed_requests_also_count_towards_the_limit(self):
        service, _, clock = make_service(handler=lambda request: httpx.Response(503))
        for query in ("a", "b"):
            with self.assertRaises(ps.PlacesError):
                service.search_place(query)
        self.assertEqual(len(clock.sleeps), 1)

    def test_distance_lookups_are_throttled(self):
        service, requests, clock = make_service([GARDEN])
        service.get_distance_between_places("A", "B")
        self.assertEqual(len(requests), 2)
        self.assertAlmostEqual(clock.sleeps[0], 1.0)


class HaversineTests(unittest.TestCase):
    def test_same_point_is_zero(self):
        self.assertAlmostEqual(ps.haversine_km(40.2, -8.4, 40.2, -8.4), 0.0, places=9)

    def test_symmetry(self):
        a, b = (40.2074, -8.4260), (40.2075, -8.4163)
        self.assertAlmostEqual(ps.haversine_km(*a, *b), ps.haversine_km(*b, *a), places=12)

    def test_one_degree_on_the_equator(self):
        expected = 2 * math.pi * ps.EARTH_MEAN_RADIUS_KM / 360  # 111.195 km
        self.assertAlmostEqual(ps.haversine_km(0, 0, 0, 1), expected, places=6)
        self.assertAlmostEqual(ps.haversine_km(0, 0, 0, 1), 111.195, places=2)
        self.assertAlmostEqual(ps.haversine_km(0, 0, 1, 0), expected, places=6)

    def test_quarter_circumference_and_antipodes(self):
        self.assertAlmostEqual(ps.haversine_km(0, 0, 90, 0), math.pi * ps.EARTH_MEAN_RADIUS_KM / 2, places=6)
        self.assertAlmostEqual(ps.haversine_km(0, 0, 0, 180), math.pi * ps.EARTH_MEAN_RADIUS_KM, places=6)

    def test_known_city_pair(self):
        # Lisboa (38.7223, -9.1393) to Porto (41.1579, -8.6291): about 274 km in a straight line
        self.assertAlmostEqual(ps.haversine_km(38.7223, -9.1393, 41.1579, -8.6291), 274, delta=3)


class DistanceTests(unittest.TestCase):
    def two_places(self, request):
        query = request.url.params["q"]
        return httpx.Response(200, json=[UNIVERSITY] if "Universidade" in query else [GARDEN])

    def test_distance_uses_resolved_places_and_says_geodesic(self):
        service, requests, _ = make_service(handler=self.two_places)
        result = service.get_distance_between_places("Universidade de Coimbra", "Jardim Botânico", "pt")
        self.assertEqual(result["distance_type"], "geodesic")
        self.assertIn("linha reta", result["note"])
        self.assertIn("não é distância a pé ou de carro", result["note"])
        self.assertEqual(result["origin"]["display_name"], "Universidade de Coimbra, Coimbra, Portugal")
        self.assertEqual(result["destination"]["name"], GARDEN["name"])
        self.assertEqual((result["origin"]["latitude"], result["origin"]["longitude"]), (40.2074, -8.4260))
        self.assertEqual(result["origin"]["candidates_found"], 1)
        expected = ps.haversine_km(40.2074, -8.4260, 40.2075, -8.4163)
        self.assertAlmostEqual(result["straight_line_distance_km"], expected, places=3)
        self.assertGreater(result["straight_line_distance_km"], 0)
        self.assertIn("OpenStreetMap", result["attribution"])
        self.assertTrue(all(r.url.params["countrycodes"] == "pt" for r in requests))

    def test_distance_to_itself_is_zero(self):
        service, requests, _ = make_service([GARDEN])
        result = service.get_distance_between_places("Jardim", "Jardim")
        self.assertEqual(result["straight_line_distance_km"], 0.0)
        self.assertEqual(len(requests), 1)  # the second lookup is a cache hit

    def test_distance_is_symmetric(self):
        service, _, _ = make_service(handler=self.two_places)
        ab = service.get_distance_between_places("Universidade", "Jardim")["straight_line_distance_km"]
        ba = service.get_distance_between_places("Jardim", "Universidade")["straight_line_distance_km"]
        self.assertEqual(ab, ba)

    def test_best_ranked_result_is_used_and_ambiguity_is_reported(self):
        service, _, _ = make_service([COIMBRA, item("Coimbra", "-20.85", "-42.8")])
        result = service.get_distance_between_places("Coimbra", "Coimbra")
        self.assertEqual(result["origin"]["latitude"], 40.2056)  # the first one, not the Brazilian one
        self.assertEqual(result["origin"]["candidates_found"], 2)

    def test_origin_not_found(self):
        def handler(request):
            return httpx.Response(200, json=[] if "Xyzzy" in request.url.params["q"] else [GARDEN])
        service, _, _ = make_service(handler=handler)
        with self.assertRaisesRegex(ps.PlacesError, "não encontrado.*Xyzzy"):
            service.get_distance_between_places("Xyzzy", "Jardim")

    def test_destination_not_found(self):
        def handler(request):
            return httpx.Response(200, json=[] if "Xyzzy" in request.url.params["q"] else [GARDEN])
        service, _, _ = make_service(handler=handler)
        with self.assertRaisesRegex(ps.PlacesError, "não encontrado.*Xyzzy"):
            service.get_distance_between_places("Jardim", "Xyzzy")

    def test_invalid_country_code_is_rejected(self):
        service, requests, _ = make_service()
        with self.assertRaisesRegex(ps.PlacesError, "country_code"):
            service.get_distance_between_places("A", "B", "portugal")
        self.assertEqual(requests, [])


if __name__ == "__main__":
    unittest.main()
