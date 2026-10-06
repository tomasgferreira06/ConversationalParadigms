"""Places domain/API layer for the Places MCP (no MCP code here).

place query -> OpenStreetMap Nominatim /search (public server) -> trimmed place dicts,
and a straight-line (geodesic, Haversine) distance between two resolved places.

Nominatim usage policy (https://operations.osmfoundation.org/policies/nominatim/):
  * at most 1 request per second   -> sequential requests behind a lock + a minimum interval
  * identifiable User-Agent        -> USER_AGENT (override with PLACES_MCP_USER_AGENT), never httpx's default
  * attribution                    -> every result carries ATTRIBUTION
  * caching of repeated queries    -> in-memory, successful lookups only
  * only /search: no /details, no autocomplete, no bulk or systematic crawling, no routing.

Every failure raises PlacesError with a clear message; no default or invented coordinates.
"""

from __future__ import annotations

import math
import os
import threading
import time
from typing import Any, Callable

import httpx

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = os.environ.get("PLACES_MCP_USER_AGENT", "ConversationalParadigms-CoimbraTourism/1.0")
ATTRIBUTION = "© OpenStreetMap contributors (data and geocoding via Nominatim)"
REQUEST_TIMEOUT_SECONDS = 10.0
MIN_REQUEST_INTERVAL_SECONDS = 1.0
MAX_RESULTS = 3
EARTH_MEAN_RADIUS_KM = 6371.0088  # IUGG mean Earth radius


class PlacesError(Exception):
    """Any failure to resolve a place or compute a distance; the message is meant to be shown as is."""


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km on a sphere of EARTH_MEAN_RADIUS_KM."""

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlam = phi2 - phi1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_MEAN_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def _clean_query(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlacesError(f"{what} não pode estar vazio.")
    return " ".join(value.split())


def _clean_country_code(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) != 2 or not value.isascii() or not value.isalpha():
        raise PlacesError(f"country_code tem de ter duas letras (código ISO 3166-1 alpha-2, ex.: 'pt'); recebido: {value!r}.")
    return value.lower()


def _coordinate(item: dict[str, Any], key: str, limit: float) -> float:
    raw = item.get(key)
    if raw is None:
        raise PlacesError(f"Resposta incompleta do Nominatim: falta '{key}'.")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise PlacesError(f"Resposta inválida do Nominatim: '{key}' não é numérico ({raw!r}).") from None
    if not math.isfinite(value) or abs(value) > limit:
        raise PlacesError(f"Resposta inválida do Nominatim: '{key}' fora do intervalo ({value}).")
    return value


def _parse_place(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise PlacesError("Resposta inesperada do Nominatim: resultado inválido.")
    display_name = item.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        raise PlacesError("Resposta incompleta do Nominatim: falta 'display_name'.")
    address = item.get("address")
    return {
        "name": item.get("name") or display_name.split(",")[0].strip(),
        "display_name": display_name,
        "latitude": _coordinate(item, "lat", 90.0),
        "longitude": _coordinate(item, "lon", 180.0),
        "category": item.get("category"),
        "type": item.get("type"),
        "address": address if isinstance(address, dict) else {},
        "osm_type": item.get("osm_type"),
        "osm_id": item.get("osm_id"),
    }


class PlacesService:
    """Synchronous service; an httpx.Client, a clock and a sleep can be injected (tests)."""

    def __init__(self, client: httpx.Client | None = None, user_agent: str = USER_AGENT,
                 min_interval: float = MIN_REQUEST_INTERVAL_SECONDS,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep):
        self._client = client
        self._user_agent = user_agent
        self._min_interval = min_interval
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()  # requests to Nominatim are strictly sequential
        self._last_request: float | None = None
        self._cache: dict[tuple[str, str | None], list[dict[str, Any]]] = {}

    # ---- Nominatim ---------------------------------------------------------

    def _wait_for_turn(self) -> None:
        if self._last_request is not None:
            wait = self._min_interval - (self._clock() - self._last_request)
            if wait > 0:
                self._sleep(wait)

    def _fetch(self, query: str, country_code: str | None) -> Any:
        params: dict[str, Any] = {"q": query, "format": "jsonv2", "addressdetails": 1,
                                  "limit": MAX_RESULTS, "accept-language": "pt"}
        if country_code:
            params["countrycodes"] = country_code
        headers = {"User-Agent": self._user_agent}
        self._wait_for_turn()
        self._last_request = self._clock()
        try:
            if self._client is not None:
                response = self._client.get(NOMINATIM_SEARCH_URL, params=params, headers=headers,
                                            timeout=REQUEST_TIMEOUT_SECONDS)
            else:
                with httpx.Client() as client:
                    response = client.get(NOMINATIM_SEARCH_URL, params=params, headers=headers,
                                          timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise PlacesError("Timeout ao contactar o Nominatim.") from None
        except httpx.HTTPStatusError as exc:
            raise PlacesError(f"O Nominatim respondeu com erro HTTP {exc.response.status_code}.") from None
        except httpx.HTTPError as exc:
            raise PlacesError(f"Falha de rede ao contactar o Nominatim: {exc}.") from None
        except ValueError:
            raise PlacesError("Resposta inválida (não é JSON) do Nominatim.") from None

    def _search(self, query: Any, country_code: Any, what: str = "A pesquisa") -> tuple[str, str | None, list[dict[str, Any]]]:
        """Validated query, country code and parsed places (cached; empty result is an error)."""

        query = _clean_query(query, what)
        country_code = _clean_country_code(country_code)
        key = (query.casefold(), country_code)
        with self._lock:
            if key in self._cache:
                return query, country_code, self._cache[key]
            data = self._fetch(query, country_code)
            if not isinstance(data, list):
                raise PlacesError("Resposta inesperada do Nominatim (esperava uma lista de resultados).")
            if not data:
                suffix = f" (país: {country_code})" if country_code else ""
                raise PlacesError(f"Local não encontrado: '{query}'{suffix}.")
            places = [_parse_place(item) for item in data[:MAX_RESULTS]]
            self._cache[key] = places  # only valid, non-empty results are cached
            return query, country_code, places

    # ---- tools -------------------------------------------------------------

    def search_place(self, query: str, country_code: str | None = None) -> dict[str, Any]:
        """Up to MAX_RESULTS candidates, in the order Nominatim ranked them (no disambiguation)."""

        query, country_code, places = self._search(query, country_code, "A pesquisa (query)")
        return {"query": query, "country_code": country_code, "results": [dict(p) for p in places],
                "attribution": ATTRIBUTION}

    def get_distance_between_places(self, origin: str, destination: str,
                                    country_code: str | None = None) -> dict[str, Any]:
        """Straight-line (geodesic) distance between the best-ranked match of each place."""

        _, country_code, origin_places = self._search(origin, country_code, "A origem")
        _, _, destination_places = self._search(destination, country_code, "O destino")
        a, b = origin_places[0], destination_places[0]
        distance = haversine_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"])

        def used(place: dict[str, Any], candidates: int) -> dict[str, Any]:
            return {"name": place["name"], "display_name": place["display_name"],
                    "latitude": place["latitude"], "longitude": place["longitude"],
                    "candidates_found": candidates}

        return {
            "origin": used(a, len(origin_places)),
            "destination": used(b, len(destination_places)),
            "straight_line_distance_km": round(distance, 3),
            "distance_type": "geodesic",
            "note": ("Distância geodésica em linha reta entre os melhores resultados do Nominatim; "
                     "não é distância a pé ou de carro, nem tempo de viagem."),
            "attribution": ATTRIBUTION,
        }
