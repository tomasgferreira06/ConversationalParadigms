# Weather MCP Implementation

## 1. Objective

D3-O1, first step: an isolated, working Weather MCP server (official Python MCP SDK, Open-Meteo
backend) for the Coimbra Tourism Expert domain. Not connected to the agent in this phase.

## 2. Repository Audit

- Python `>=3.13` (`.python-version` 3.13), managed with `uv` (`pyproject.toml`, `uv.lock`).
- D1: `d1_rule_based_v2/eliza_rude.py`. D2: `d2_rag/` (scripts, tests, data, frozen corpora/stores).
  Integration: `integration/` (`integrated_agent.py`, `agents.py`, `router.py`, classifier model,
  tests). `agents.py` wraps D1/D2 via `sys.path` inserts of flat script directories.
- Tests: standard `unittest`, run as `uv run python -m unittest discover -s <dir>/tests`.
- `httpx` 0.28.1 was already installed (transitive); no `mcp` and no `asyncio` usage in project code;
  no MCP code anywhere before this work.
- Baseline before changes: D2 123 tests OK; integration 58 tests with **2 pre-existing failures**
  (`test_router.TrainedRouterTests`: "Quero ir para casa." and a "thanks" message are routed to `rag`
  instead of `eliza_rude`). Unrelated to this work and left untouched.
- Chosen location: `d3/weather_mcp/`, following the repo's flat-module convention (tests add the
  module directory to `sys.path`, as the existing scripts do).

## 3. Architecture

`MCP client → server.py (MCP layer) → weather_service.py (domain/API layer) → Open-Meteo`.
`server.py` only declares tools, descriptions and maps `WeatherError` to `ToolError`; all HTTP,
geocoding, validation and transformation are in `weather_service.py`. Transport: stdio.

## 4. MCP Tools

- `get_current_weather(location: str)`
- `get_weather_forecast(location: str, days: int = 3)`, `1 <= days <= 7`

Both return structured dicts (location block + current/forecast) and carry Portuguese descriptions
that say when each should be used, without any routing logic.

SDK: `mcp` 2.3.0 (`mcp[cli]`). The 2.x API differs from the 1.x examples: `FastMCP` became
`mcp.server.mcpserver.MCPServer`, and the client is `mcp.Client`. The installed API was inspected
before writing code.

## 5. Open-Meteo Integration

- Geocoding: `geocoding-api.open-meteo.com/v1/search` (`language=pt`, 10 candidates). `"City, Country"`
  searches the city and filters by country name or ISO code (accent/case-insensitive), because the API
  does not understand the combined form. Nothing is hard-coded.
- Forecast: `api.open-meteo.com/v1/forecast` with `current=` / `daily=` variables, `celsius`, `kmh`,
  `mm`, `timezone=auto`, `forecast_days=N`.
- WMO codes translated to Portuguese for the 28 official codes Open-Meteo documents; unknown codes
  are an error, not a guess.
- `httpx`, 10 s timeout on every request.

## 6. Error Handling

`WeatherError` for: empty location, unknown location (or country mismatch), `days` outside 1..7 or not
an integer (checked before any request), timeout, HTTP status error, network error, non-JSON body,
missing blocks/fields/columns, daily arrays of unexpected length, null values, unknown weather code.
Via MCP these become `is_error=true` results with the message. No defaults or fabricated data.

## 7. Tests

35 new unit tests, no Internet and no subprocess: 26 for the service (`httpx.MockTransport`) and
9 for the MCP layer (in-process `mcp.Client` over the real `MCPServer`, with a fake service).
Covered: Coimbra resolution, country filter, current format and units, forecast 1/3/7 days, days 0/8
(and invalid types), unknown location, timeout, HTTP failure, network failure, malformed/missing
fields, weather code mapping; exactly two tools, names, schemas, delegation, controlled errors,
import without starting the server.

## 8. Real Smoke Test

Run on 2026-10-05 with Internet: `"Coimbra, Portugal"` resolved to Coimbra, Portugal
(40.20686, -8.41996, Europe/Lisbon); current weather and a 3-day forecast parsed correctly
(see section 9 for output). Not a permanent test.

## 9. MCP Protocol Verification

`check_mcp_client.py`: SDK `Client` launches `server.py` as a stdio subprocess, discovers the two
tools, calls `get_current_weather("Coimbra, Portugal")` (27.5 °C, "Parcialmente nublado") and
`get_weather_forecast("Coimbra, Portugal", 3)` (3 daily entries) and receives valid structured
content. `days=8` and `"Xyzzyville"` return `is_error=true` with clear messages. The MCP Inspector
UI was not used.

## 10. Files Created / Modified

Created: `d3/weather_mcp/{__init__.py, server.py, weather_service.py, check_mcp_client.py, README.md,
WEATHER_MCP_IMPLEMENTATION_REPORT.md, tests/test_weather_service.py, tests/test_weather_mcp.py}`.
Modified: `pyproject.toml` (+`mcp[cli]>=2.3.0`), `uv.lock`, `README.md` (short D3-O1 section).
Nothing under `d1_rule_based*`, `d2_rag/` or `integration/` changed.

## 11. Current Limitations

- Not connected to the agent; no tool selection.
- The service is synchronous, so a tool call blocks the server event loop while it waits on
  Open-Meteo (acceptable for one local stdio client).
- Geocoding picks the first (best-ranked) candidate; ambiguous names without a country qualifier may
  resolve to an unintended place.
- The daily forecast starts today (no hourly data, no day offsets such as "tomorrow").
- The server logs at WARNING level (set when it was integrated into the chat); stdout stays protocol-only.
- The 2 pre-existing `integration` router test failures remain.

## 12. Next Step

Integrate the Weather MCP with the Coimbra Expert Agent and implement agent-driven tool selection.
