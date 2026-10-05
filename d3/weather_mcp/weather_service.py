"""Weather domain/API layer for the Weather MCP (no MCP code here).

location name -> Open-Meteo geocoding -> latitude/longitude -> Open-Meteo forecast
-> validated, structured dicts. Units are fixed: Celsius, km/h, mm; timezone "auto"
(the timezone of the resolved location). Every failure raises WeatherError with a
clear message; no default or invented data is ever returned.
"""

from __future__ import annotations

import unicodedata
from typing import Any

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10.0
MIN_FORECAST_DAYS = 1
MAX_FORECAST_DAYS = 7
GEOCODING_CANDIDATES = 10

CURRENT_VARIABLES = (
    "temperature_2m,apparent_temperature,precipitation,rain,cloud_cover,wind_speed_10m,weather_code"
)
DAILY_VARIABLES = (
    "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "precipitation_probability_max,wind_speed_10m_max"
)
UNIT_PARAMS = {
    "temperature_unit": "celsius",
    "wind_speed_unit": "kmh",
    "precipitation_unit": "mm",
    "timezone": "auto",
}

# Official WMO weather interpretation codes, as documented by Open-Meteo.
WEATHER_CODES = {
    0: "Céu limpo",
    1: "Maioritariamente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Nevoeiro",
    48: "Nevoeiro com deposição de geada",
    51: "Chuvisco fraco",
    53: "Chuvisco moderado",
    55: "Chuvisco intenso",
    56: "Chuvisco gelado fraco",
    57: "Chuvisco gelado intenso",
    61: "Chuva fraca",
    63: "Chuva moderada",
    65: "Chuva forte",
    66: "Chuva gelada fraca",
    67: "Chuva gelada forte",
    71: "Queda de neve fraca",
    73: "Queda de neve moderada",
    75: "Queda de neve forte",
    77: "Grãos de neve",
    80: "Aguaceiros fracos",
    81: "Aguaceiros moderados",
    82: "Aguaceiros violentos",
    85: "Aguaceiros de neve fracos",
    86: "Aguaceiros de neve fortes",
    95: "Trovoada",
    96: "Trovoada com granizo fraco",
    99: "Trovoada com granizo forte",
}


class WeatherError(Exception):
    """Any failure to produce weather data; the message is meant to be shown as is."""


def describe_weather_code(code: int) -> str:
    try:
        return WEATHER_CODES[code]
    except (KeyError, TypeError):
        raise WeatherError(f"Código meteorológico WMO desconhecido: {code!r}.") from None


def _fold(text: str) -> str:
    """Case- and accent-insensitive form, for matching country names."""

    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().strip()


def _get_json(client: httpx.Client, url: str, params: dict[str, Any], what: str) -> dict[str, Any]:
    try:
        response = client.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        raise WeatherError(f"Timeout ao contactar a Open-Meteo ({what}).") from None
    except httpx.HTTPStatusError as exc:
        raise WeatherError(f"A Open-Meteo ({what}) respondeu com erro HTTP {exc.response.status_code}.") from None
    except httpx.HTTPError as exc:
        raise WeatherError(f"Falha de rede ao contactar a Open-Meteo ({what}): {exc}.") from None
    except ValueError:
        raise WeatherError(f"Resposta inválida (não é JSON) da Open-Meteo ({what}).") from None
    if not isinstance(data, dict):
        raise WeatherError(f"Resposta inesperada da Open-Meteo ({what}).")
    return data


def _require(mapping: Any, key: str, what: str) -> Any:
    if not isinstance(mapping, dict) or mapping.get(key) is None:
        raise WeatherError(f"Resposta incompleta da Open-Meteo: falta '{key}' em {what}.")
    return mapping[key]


class WeatherService:
    """Synchronous service; an httpx.Client can be injected (tests use a MockTransport)."""

    def __init__(self, client: httpx.Client | None = None):
        self._client = client

    def _request(self, url: str, params: dict[str, Any], what: str) -> dict[str, Any]:
        if self._client is not None:
            return _get_json(self._client, url, params, what)
        with httpx.Client() as client:
            return _get_json(client, url, params, what)

    # ---- geocoding ---------------------------------------------------------

    def resolve_location(self, location: str) -> dict[str, Any]:
        """"Coimbra" or "Coimbra, Portugal" -> the best matching place (never guessed)."""

        if not isinstance(location, str) or not location.strip():
            raise WeatherError("A localização não pode estar vazia.")
        name, _, qualifier = (part.strip() for part in location.partition(","))
        if not name:
            raise WeatherError("A localização não pode estar vazia.")
        data = self._request(
            GEOCODING_URL,
            {"name": name, "count": GEOCODING_CANDIDATES, "language": "pt", "format": "json"},
            "geocoding",
        )
        candidates = data.get("results") or []
        if qualifier:
            wanted = _fold(qualifier)
            candidates = [
                c for c in candidates
                if wanted in (_fold(str(c.get("country", ""))), _fold(str(c.get("country_code", ""))))
            ]
        if not candidates:
            raise WeatherError(f"Localização não encontrada: '{location.strip()}'.")
        best = candidates[0]  # Open-Meteo ranks by relevance
        return {
            "name": _require(best, "name", "geocoding"),
            "country": best.get("country"),
            "latitude": float(_require(best, "latitude", "geocoding")),
            "longitude": float(_require(best, "longitude", "geocoding")),
            "timezone": best.get("timezone"),
        }

    # ---- weather -----------------------------------------------------------

    def _forecast_payload(self, place: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        params = {"latitude": place["latitude"], "longitude": place["longitude"], **UNIT_PARAMS, **extra}
        return self._request(FORECAST_URL, params, "forecast")

    @staticmethod
    def _location_block(place: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return {**place, "timezone": payload.get("timezone") or place.get("timezone")}

    def get_current_weather(self, location: str) -> dict[str, Any]:
        place = self.resolve_location(location)
        payload = self._forecast_payload(place, {"current": CURRENT_VARIABLES})
        current = _require(payload, "current", "resposta")
        code = _require(current, "weather_code", "current")
        return {
            "location": self._location_block(place, payload),
            "current": {
                "time": _require(current, "time", "current"),
                "temperature_c": _require(current, "temperature_2m", "current"),
                "apparent_temperature_c": _require(current, "apparent_temperature", "current"),
                "precipitation_mm": _require(current, "precipitation", "current"),
                "rain_mm": _require(current, "rain", "current"),
                "cloud_cover_percent": _require(current, "cloud_cover", "current"),
                "wind_speed_kmh": _require(current, "wind_speed_10m", "current"),
                "weather_code": code,
                "weather_description": describe_weather_code(code),
            },
        }

    def get_weather_forecast(self, location: str, days: int = 3) -> dict[str, Any]:
        if isinstance(days, bool) or not isinstance(days, int):
            raise WeatherError("'days' tem de ser um número inteiro.")
        if not MIN_FORECAST_DAYS <= days <= MAX_FORECAST_DAYS:
            raise WeatherError(
                f"'days' tem de estar entre {MIN_FORECAST_DAYS} e {MAX_FORECAST_DAYS} (recebido: {days})."
            )
        place = self.resolve_location(location)
        payload = self._forecast_payload(place, {"daily": DAILY_VARIABLES, "forecast_days": days})
        daily = _require(payload, "daily", "resposta")
        dates = _require(daily, "time", "daily")
        columns = {
            key: _require(daily, key, "daily")
            for key in (
                "weather_code", "temperature_2m_min", "temperature_2m_max",
                "precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max",
            )
        }
        if not isinstance(dates, list) or len(dates) != days or any(
            not isinstance(col, list) or len(col) != days for col in columns.values()
        ):
            raise WeatherError("Resposta incompleta da Open-Meteo: previsão diária com tamanho inesperado.")
        forecast = []
        for i, date in enumerate(dates):
            values = {key: col[i] for key, col in columns.items()}
            if any(v is None for v in values.values()):
                raise WeatherError(f"Resposta incompleta da Open-Meteo: valores em falta para {date}.")
            forecast.append({
                "date": date,
                "temperature_min_c": values["temperature_2m_min"],
                "temperature_max_c": values["temperature_2m_max"],
                "precipitation_sum_mm": values["precipitation_sum"],
                "precipitation_probability_max_percent": values["precipitation_probability_max"],
                "wind_speed_max_kmh": values["wind_speed_10m_max"],
                "weather_code": values["weather_code"],
                "weather_description": describe_weather_code(values["weather_code"]),
            })
        return {"location": self._location_block(place, payload), "forecast": forecast}
