"""Weather service unit tests: Open-Meteo is mocked with httpx.MockTransport (no Internet)."""

import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import weather_service as ws  # noqa: E402

COIMBRA = {
    "name": "Coimbra", "country": "Portugal", "country_code": "PT",
    "latitude": 40.20564, "longitude": -8.41955, "timezone": "Europe/Lisbon",
}
COIMBRA_BR = {
    "name": "Coimbra", "country": "Brasil", "country_code": "BR",
    "latitude": -20.85, "longitude": -42.8, "timezone": "America/Sao_Paulo",
}

CURRENT = {
    "timezone": "Europe/Lisbon",
    "current": {
        "time": "2026-10-05T12:00", "temperature_2m": 21.4, "apparent_temperature": 20.1,
        "precipitation": 0.0, "rain": 0.0, "cloud_cover": 40, "wind_speed_10m": 11.2, "weather_code": 2,
    },
}


def daily_payload(days: int) -> dict:
    return {
        "timezone": "Europe/Lisbon",
        "daily": {
            "time": [f"2026-10-{5 + i:02d}" for i in range(days)],
            "weather_code": [61] * days,
            "temperature_2m_min": [12.0] * days,
            "temperature_2m_max": [22.5] * days,
            "precipitation_sum": [3.4] * days,
            "precipitation_probability_max": [80] * days,
            "wind_speed_10m_max": [25.0] * days,
        },
    }


def make_service(forecast=None, geocoding=None, handler=None) -> tuple[ws.WeatherService, list]:
    """A service over a mock transport; returns it and the list of requests it made.

    By default geocoding answers with `geocoding` (Coimbra, PT) and the forecast host
    with `forecast`; `handler` replaces both to simulate failures.
    """

    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if handler is not None:
            return handler(request)
        if request.url.host == "geocoding-api.open-meteo.com":
            return httpx.Response(200, json=geocoding if geocoding is not None else {"results": [COIMBRA]})
        return httpx.Response(200, json=forecast)

    return ws.WeatherService(httpx.Client(transport=httpx.MockTransport(respond))), requests


def failing_forecast(error):
    """Geocoding works; the forecast request fails with `error` (an exception or a status code)."""

    def handler(request):
        if request.url.host == "geocoding-api.open-meteo.com":
            return httpx.Response(200, json={"results": [COIMBRA]})
        if isinstance(error, int):
            return httpx.Response(error)
        raise error("simulated failure", request=request)
    return handler


class LocationTests(unittest.TestCase):
    def test_coimbra_resolves_to_portugal(self):
        service, requests = make_service()
        place = service.resolve_location("Coimbra")
        self.assertEqual(place["name"], "Coimbra")
        self.assertEqual(place["country"], "Portugal")
        self.assertAlmostEqual(place["latitude"], 40.20564)
        self.assertEqual(place["timezone"], "Europe/Lisbon")
        self.assertEqual(requests[0].url.params["name"], "Coimbra")

    def test_city_country_form_searches_city_and_filters_country(self):
        service, requests = make_service(geocoding={"results": [COIMBRA_BR, COIMBRA]})
        place = service.resolve_location("Coimbra, Portugal")
        self.assertEqual(place["country"], "Portugal")
        self.assertEqual(requests[0].url.params["name"], "Coimbra")

    def test_country_code_and_accents_are_accepted(self):
        service, _ = make_service(geocoding={"results": [COIMBRA_BR, COIMBRA]})
        self.assertEqual(service.resolve_location("Coimbra, pt")["country"], "Portugal")
        service, _ = make_service(geocoding={"results": [dict(COIMBRA, country="Côte")]})
        self.assertEqual(service.resolve_location("Coimbra, COTE")["country"], "Côte")

    def test_unknown_location(self):
        service, _ = make_service(geocoding={"generationtime_ms": 0.3})  # Open-Meteo omits "results"
        with self.assertRaisesRegex(ws.WeatherError, "não encontrada"):
            service.resolve_location("Xyzzyville")

    def test_country_mismatch_is_not_found(self):
        service, _ = make_service(geocoding={"results": [COIMBRA_BR]})
        with self.assertRaisesRegex(ws.WeatherError, "não encontrada"):
            service.resolve_location("Coimbra, Portugal")

    def test_empty_location(self):
        service, requests = make_service()
        for bad in ("", "   ", ",", None):
            with self.assertRaisesRegex(ws.WeatherError, "vazia"):
                service.resolve_location(bad)
        self.assertEqual(requests, [])


class CurrentWeatherTests(unittest.TestCase):
    def test_format_and_units(self):
        service, requests = make_service(forecast=CURRENT)
        result = service.get_current_weather("Coimbra, Portugal")
        self.assertEqual(result["location"], {
            "name": "Coimbra", "country": "Portugal", "latitude": 40.20564,
            "longitude": -8.41955, "timezone": "Europe/Lisbon",
        })
        self.assertEqual(result["current"], {
            "time": "2026-10-05T12:00", "temperature_c": 21.4, "apparent_temperature_c": 20.1,
            "precipitation_mm": 0.0, "rain_mm": 0.0, "cloud_cover_percent": 40,
            "wind_speed_kmh": 11.2, "weather_code": 2, "weather_description": "Parcialmente nublado",
        })
        params = requests[-1].url.params
        self.assertEqual(params["temperature_unit"], "celsius")
        self.assertEqual(params["wind_speed_unit"], "kmh")
        self.assertEqual(params["precipitation_unit"], "mm")
        self.assertEqual(params["timezone"], "auto")
        self.assertEqual(float(params["latitude"]), 40.20564)

    def test_zero_values_are_valid_not_missing(self):
        service, _ = make_service(forecast=CURRENT)  # precipitation 0.0 must not count as missing
        self.assertEqual(service.get_current_weather("Coimbra")["current"]["rain_mm"], 0.0)


class ForecastTests(unittest.TestCase):
    def check_days(self, days):
        service, requests = make_service(forecast=daily_payload(days))
        result = service.get_weather_forecast("Coimbra", days)
        self.assertEqual(len(result["forecast"]), days)
        self.assertEqual(requests[-1].url.params["forecast_days"], str(days))
        return result

    def test_one_day(self):
        day = self.check_days(1)["forecast"][0]
        self.assertEqual(day, {
            "date": "2026-10-05", "temperature_min_c": 12.0, "temperature_max_c": 22.5,
            "precipitation_sum_mm": 3.4, "precipitation_probability_max_percent": 80,
            "wind_speed_max_kmh": 25.0, "weather_code": 61, "weather_description": "Chuva fraca",
        })

    def test_three_days(self):
        result = self.check_days(3)
        self.assertEqual([d["date"] for d in result["forecast"]], ["2026-10-05", "2026-10-06", "2026-10-07"])
        self.assertEqual(result["location"]["name"], "Coimbra")

    def test_seven_days(self):
        self.check_days(7)

    def test_default_is_three_days(self):
        service, _ = make_service(forecast=daily_payload(3))
        self.assertEqual(len(service.get_weather_forecast("Coimbra")["forecast"]), 3)

    def test_invalid_days_rejected_before_any_request(self):
        service, requests = make_service(forecast=daily_payload(1))
        for bad in (0, 8, -1, 2.5, "3", True):
            with self.assertRaises(ws.WeatherError, msg=repr(bad)):
                service.get_weather_forecast("Coimbra", bad)
        self.assertEqual(requests, [])


class FailureTests(unittest.TestCase):
    def test_timeout(self):
        service, _ = make_service(handler=failing_forecast(httpx.ReadTimeout))
        with self.assertRaisesRegex(ws.WeatherError, "Timeout"):
            service.get_current_weather("Coimbra")

    def test_http_error(self):
        service, _ = make_service(handler=failing_forecast(503))
        with self.assertRaisesRegex(ws.WeatherError, "HTTP 503"):
            service.get_current_weather("Coimbra")

    def test_geocoding_http_error(self):
        service, _ = make_service(handler=lambda request: httpx.Response(500))
        with self.assertRaisesRegex(ws.WeatherError, "geocoding.*HTTP 500"):
            service.resolve_location("Coimbra")

    def test_network_error(self):
        service, _ = make_service(handler=failing_forecast(httpx.ConnectError))
        with self.assertRaisesRegex(ws.WeatherError, "rede"):
            service.get_weather_forecast("Coimbra", 2)

    def test_non_json_response(self):
        service, _ = make_service(handler=lambda request: httpx.Response(200, text="<html>"))
        with self.assertRaisesRegex(ws.WeatherError, "JSON"):
            service.get_current_weather("Coimbra")

    def test_missing_current_block(self):
        service, _ = make_service(forecast={"timezone": "Europe/Lisbon"})
        with self.assertRaisesRegex(ws.WeatherError, "current"):
            service.get_current_weather("Coimbra")

    def test_missing_current_field(self):
        broken = {"current": {k: v for k, v in CURRENT["current"].items() if k != "wind_speed_10m"}}
        service, _ = make_service(forecast=broken)
        with self.assertRaisesRegex(ws.WeatherError, "wind_speed_10m"):
            service.get_current_weather("Coimbra")

    def test_missing_daily_column(self):
        payload = daily_payload(2)
        del payload["daily"]["precipitation_sum"]
        service, _ = make_service(forecast=payload)
        with self.assertRaisesRegex(ws.WeatherError, "precipitation_sum"):
            service.get_weather_forecast("Coimbra", 2)

    def test_daily_length_mismatch(self):
        payload = daily_payload(3)
        payload["daily"]["temperature_2m_max"] = [20.0]
        service, _ = make_service(forecast=payload)
        with self.assertRaisesRegex(ws.WeatherError, "tamanho"):
            service.get_weather_forecast("Coimbra", 3)

    def test_null_daily_value(self):
        payload = daily_payload(2)
        payload["daily"]["precipitation_probability_max"][1] = None
        service, _ = make_service(forecast=payload)
        with self.assertRaisesRegex(ws.WeatherError, "em falta"):
            service.get_weather_forecast("Coimbra", 2)


class WeatherCodeTests(unittest.TestCase):
    def test_official_groups(self):
        expected = {
            0: "Céu limpo", 1: "Maioritariamente limpo", 2: "Parcialmente nublado", 3: "Nublado",
            45: "Nevoeiro", 48: "Nevoeiro com deposição de geada",
            51: "Chuvisco fraco", 55: "Chuvisco intenso", 56: "Chuvisco gelado fraco",
            61: "Chuva fraca", 65: "Chuva forte", 67: "Chuva gelada forte",
            71: "Queda de neve fraca", 77: "Grãos de neve",
            80: "Aguaceiros fracos", 82: "Aguaceiros violentos", 85: "Aguaceiros de neve fracos",
            95: "Trovoada", 96: "Trovoada com granizo fraco", 99: "Trovoada com granizo forte",
        }
        for code, text in expected.items():
            self.assertEqual(ws.describe_weather_code(code), text)

    def test_only_official_codes_exist(self):
        official = {0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
                    71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99}
        self.assertEqual(set(ws.WEATHER_CODES), official)

    def test_unknown_code(self):
        for bad in (4, 100, None):
            with self.assertRaises(ws.WeatherError):
                ws.describe_weather_code(bad)


if __name__ == "__main__":
    unittest.main()
