# Weather MCP

## Purpose

Complements the Coimbra Tourism Expert with **dynamic weather information**, which does not
belong in the static RAG corpus (current conditions and short-term forecasts change by the hour).
It is an MCP server exposing two tools, so that a future MCP client (the conversational agent)
can discover and call them.

## Architecture

```
MCP Client
    ↓  (stdio)
Weather MCP Server      server.py           MCP protocol layer only (tools, descriptions, error mapping)
    ↓
Weather Service         weather_service.py  geocoding, Open-Meteo calls, validation, transformation, errors
    ↓
Open-Meteo              geocoding-api.open-meteo.com + api.open-meteo.com (no API key)
```

- SDK: official Python `mcp` package (2.x), `mcp.server.mcpserver.MCPServer` (the 1.x `FastMCP` was renamed).
- Transport: **stdio**, so the agent can later launch the server as a local subprocess.
- HTTP client: `httpx` with an explicit 10 s timeout.
- Units are fixed: °C, km/h, mm; timezone `auto` (the one of the resolved location).

## Tools

### `get_current_weather(location: str)`

Current conditions: temperature, apparent temperature, precipitation, rain, cloud cover, wind,
WMO weather code and its description (Portuguese).

### `get_weather_forecast(location: str, days: int = 3)`

Daily forecast for `1 <= days <= 7` days starting today: min/max temperature, precipitation sum,
max precipitation probability, max wind, weather code and description.

`location` is `"Coimbra"` or `"City, Country"` (country name or ISO code). The place is resolved
through the Open-Meteo geocoding API (nothing is hard-coded) and the resolved name, country,
coordinates and timezone are returned in every result. An unknown place is an error; no weather
is returned for guessed coordinates.

Failures (empty location, unknown place, invalid `days`, timeout, HTTP/network error, incomplete
response) are returned as MCP tool errors (`is_error=true`) with a clear message. No fallback data.

## Data Source

[Open-Meteo](https://open-meteo.com/) (geocoding + forecast APIs, WMO weather codes).

## Running

```bash
# start the server (stdio; normally launched by an MCP client, not by hand)
uv run python d3/weather_mcp/server.py

# manual end-to-end check: SDK client -> stdio server -> real Open-Meteo (needs Internet)
uv run python d3/weather_mcp/check_mcp_client.py
```

## Testing

```bash
# unit tests (no Internet, no subprocess)
uv run python -m unittest discover -s d3/weather_mcp/tests
```

## Current Scope

The Weather MCP is functional **in isolation**. It is **not yet connected** to the Coimbra Expert
Agent: there is no routing, tool selection or RAG + MCP combination. Agency/tool selection is the
next phase.
