# Places MCP Implementation

Data/geocoding © OpenStreetMap contributors via Nominatim.

## 1. Objective

D3-O1, second MCP: an isolated Places MCP server giving geographic information (location of a place,
straight-line distance between two places) that complements the static RAG corpus. It is **not**
integrated into the Coimbra Expert Agent in this phase (no planner changes, no new routes).

## 2. Repository Audit

- Reference architecture: `d3/weather_mcp/` (`server.py` protocol layer, `weather_service.py` domain layer,
  `check_mcp_client.py`, `unittest` tests with `httpx.MockTransport`). Working tree was clean at the start.
- Confirmed: `mcp` 2.3.0, `httpx` 0.28.1; server pattern `mcp.server.mcpserver.MCPServer` with
  `@mcp.tool(name=..., description=...)` and `ToolError` for anticipated failures (→ `is_error=true`);
  client pattern `mcp.Client(StdioServerParameters(...))`; transport stdio; tests run with
  `uv run python -m unittest discover -s <dir>/tests` (flat modules, `sys.path` insert in tests).
- No Nominatim/places code existed anywhere. Baseline: Weather MCP 35 OK.
- Not touched: `d3/coimbra_expert/` (planner, expert agent, prompts, MCP client), `integration/`, RAG, classifier.

## 3. Architecture

`MCP client → server.py (MCP layer) → places_service.py (domain/API layer) → Nominatim /search`.
`server.py` only declares the tools and maps `PlacesError` to `ToolError`. No new dependency
(`httpx` and `mcp` were already installed; Haversine uses `math`).

## 4. MCP Tools

- `search_place(query: str, country_code: str | None = None)`: up to 3 candidates in Nominatim order
  (name, display_name, latitude, longitude, category, type, address, osm_type, osm_id) + attribution.
  No disambiguation is attempted.
- `get_distance_between_places(origin, destination, country_code=None)`: resolves both places and returns
  the geodesic distance between the best-ranked match of each, the places actually used (display_name,
  coordinates, `candidates_found`), `distance_type: "geodesic"`, an explicit note that it is not walking or
  driving distance or travel time, and the attribution.

Descriptions follow the requested wording and state the distance semantics.

## 5. Nominatim Integration

Only `https://nominatim.openstreetmap.org/search` with `format=jsonv2`, `addressdetails=1`, `limit=3`,
`accept-language=pt`, and `countrycodes` only when a (validated, two-letter, lower-cased) `country_code` is
given. No `/details`, no scraping, no autocomplete, no Overpass, no routing. The raw response is reduced to
the relevant fields; coordinates (strings in the API) are parsed to floats and range-checked.

## 6. Usage Policy Compliance

| Requirement | Implementation |
|---|---|
| ≤ 1 request/s | sequential requests behind a lock; minimum interval 1.0 s between real requests (failed requests count) |
| identifiable User-Agent | `ConversationalParadigms-CoimbraTourism/1.0` (env `PLACES_MCP_USER_AGENT` override), sent on every request; no personal data; httpx default never used |
| attribution | `© OpenStreetMap contributors (data and geocoding via Nominatim)` in every result; README and report |
| cache | in-memory, per process (see 8) |
| no bulk/systematic use | only on-demand single lookups; at most 3 results; no crawling |

## 7. Distance Calculation

Haversine on a sphere of mean radius 6371.0088 km (`math` only), rounded to 3 decimals. The distance is
**straight-line/geodesic only**; the output and the tool description say it is not a route, walking/driving
distance or travel time. Mathematically tested: 0 for the same point, symmetry, 1° on the equator
(111.195 km), quarter circumference, antipodes, Lisboa–Porto (~274 km).

## 8. Cache and Rate Limiting

Cache key = (whitespace-normalised, case-folded query, lower-cased country code). Only valid non-empty
results are stored; timeouts, network/HTTP errors, malformed responses and "not found" are not cached.
Callers get copies, so they cannot corrupt the cache. A cache hit makes no request and never waits. On a
miss the service waits only the remaining part of the 1 s interval since the previous real request (clock
and sleep are injectable, so tests do not really wait). The two lookups of a distance call are throttled
like any others.

## 9. Error Handling

`PlacesError` (→ MCP `is_error=true` with the message, as in the Weather MCP) for: empty query/origin/
destination, invalid `country_code`, zero results, timeout, HTTP status error (403/429/5xx…), network
error, non-JSON body, unexpected response shape, missing `lat`/`lon`/`display_name`, non-numeric,
non-finite or out-of-range coordinates. No fake or default coordinates are ever returned.

## 10. Tests

57 new unit tests, no Internet, no subprocess: 47 for the service (search, country code, parameters, limit
of 3, transformation, attribution, validation, all failure modes, User-Agent, cache, rate limiter, Haversine,
distance semantics) and 10 for the MCP layer (in-process `mcp.Client` over the real `MCPServer` with a fake
service: exactly two tools, schemas, descriptions, delegation, structured output, controlled errors, import
without starting the server).

| Suite | Result |
|---|---|
| `d3/places_mcp/tests` | 57 OK |
| `d3/weather_mcp/tests` | 35 OK |
| `d3/coimbra_expert/tests` | 47 OK |
| `d2_rag/tests` | 123 OK |
| `integration/tests` | 63 run, 2 failures (the same 2 pre-existing `test_router` failures) |

## 11. Real Smoke Test

Run on 2026-10-05 (real Nominatim, through the MCP check below):

- `search_place("Jardim Botânico da Universidade de Coimbra", "pt")` → 1 result, a `leisure/park` way in
  Alta, Coimbra, Portugal; (40.2035, -8.4234); attribution present.
- `get_distance_between_places("Universidade de Coimbra", "Jardim Botânico da Universidade de Coimbra", "pt")`
  → both resolved; **2.05 km**, `distance_type: "geodesic"`. The origin had 2 candidates and the best-ranked
  one is a point in the Baixa (40.1861, -8.4153), not the Alta campus; so 2.05 km is the distance between
  the places *as resolved*, and the real campus–garden distance is much shorter (see limitations).

## 12. MCP Protocol Verification

`check_mcp_client.py` (real `mcp.Client` over stdio, `places_service` never imported): the server starts, exactly
the 2 tools are discovered, `search_place` and `get_distance_between_places` return valid structured
content, an unknown place returns `is_error=true` ("Local não encontrado: …"), the session closes cleanly
(no orphan server process). Exit code 0, 10 of 10 checks OK. The MCP Inspector UI was not used.

## 13. Files Created / Modified

Created (`d3/places_mcp/`): `__init__.py`, `server.py`, `places_service.py`, `check_mcp_client.py`,
`README.md`, `PLACES_MCP_IMPLEMENTATION_REPORT.md`, `tests/test_places_service.py`, `tests/test_places_mcp.py`.
Modified: `README.md` (short Places MCP subsection). No dependency or lock change.

## 14. Current Limitations

- **Ambiguity**: the distance uses the best-ranked candidate; for broad names ("Universidade de Coimbra") that
  can be an imprecise point, so the distance can be misleading. `candidates_found` and the used display_name
  make it visible; resolving it (e.g. more specific queries, using the candidates) is left to the agent/LLM.
- Straight-line distance only; no routing, walking/driving time or opening hours.
- The cache is per process (lost on restart); the 1 req/s limit is per process (two processes would not share it).
- The service is synchronous: a tool call blocks the server while waiting on Nominatim or the rate limit.
- Dependence on the public Nominatim server (availability, policy, its ranking); results are in Portuguese
  when OSM has Portuguese names.
- Not connected to the Coimbra Expert Agent.

## 15. Next Step

Integrate the Places MCP into the Coimbra Expert Agent and generalise agent-driven capability selection
across RAG, Weather MCP and Places MCP.
