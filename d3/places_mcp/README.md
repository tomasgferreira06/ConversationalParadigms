# Places MCP

## Purpose

Provides **geographic information** (where a place is, how far apart two places are) that complements
the static tourist knowledge of the Coimbra RAG corpus. It is an MCP server with two tools, so that a
future MCP client (the Coimbra Expert Agent) can discover and call them.

Data/geocoding © OpenStreetMap contributors via Nominatim.

## Architecture

```
MCP Client
    ↓  (stdio)
Places MCP Server      server.py          MCP protocol layer only (tools, descriptions, error mapping)
    ↓
Places Service         places_service.py  Nominatim calls, validation, cache, rate limit, distance
    ↓
OpenStreetMap Nominatim   https://nominatim.openstreetmap.org/search (public server)
```

SDK: official Python `mcp` 2.x (`mcp.server.mcpserver.MCPServer`), transport **stdio**, HTTP client
`httpx` (explicit 10 s timeout). Same conventions as the Weather MCP.

## Tools

### `search_place(query: str, country_code: str | None = None)`

Resolves a place, monument, establishment or address. Returns up to 3 candidates **in the order
Nominatim ranked them** (name, display_name, latitude, longitude, category, type, address, osm_type,
osm_id) plus the attribution. Ambiguity is not resolved: the caller sees all candidates.
`country_code` is an optional ISO 3166-1 alpha-2 code (e.g. `"pt"`), sent as `countrycodes`; nothing
is hard-coded to Coimbra or Portugal.

### `get_distance_between_places(origin: str, destination: str, country_code: str | None = None)`

Resolves both places with the same search and computes the distance between the **best-ranked** result
of each. The output names the places actually used (display_name and coordinates) and how many
candidates each query had (`candidates_found`), so ambiguity is visible.

## Distance Semantics

The distance is **straight-line / geodesic** (Haversine on a sphere of mean radius 6371.0088 km, standard
library `math` only). It is **not** walking or driving distance, not a route, and not a travel time; no
routing service is used. The result says so (`distance_type: "geodesic"` and a note).

## Nominatim Usage Policy

Implemented as required by the [public server policy](https://operations.osmfoundation.org/policies/nominatim/):

- at most **1 request per second** (requests are sequential, behind a lock, with a minimum interval);
- an **identifiable User-Agent**: `ConversationalParadigms-CoimbraTourism/1.0` (override with the
  `PLACES_MCP_USER_AGENT` environment variable; httpx's default is never used; no personal data);
- **cache** of repeated queries (in memory, key = normalised query + country code; only valid results;
  errors and empty results are not cached; a cache hit makes no request and does not wait);
- **attribution** `© OpenStreetMap contributors` in every result;
- only `/search`: no `/details`, no autocomplete, no bulk or systematic crawling, no Overpass.

The public server is meant for light use; this is an academic, short-lived, single-user application.

## Running

```bash
# start the server (stdio; normally launched by an MCP client, not by hand)
uv run python d3/places_mcp/server.py

# manual end-to-end check: SDK client -> stdio server -> real Nominatim (needs Internet, a few requests)
uv run python d3/places_mcp/check_mcp_client.py
```

## Testing

```bash
# unit tests (no Internet, no subprocess, no real waiting)
uv run python -m unittest discover -s d3/places_mcp/tests
```

## Current Scope

The Places MCP is functional **in isolation**. It is **not yet connected** to the Coimbra Expert Agent:
the planner does not know it and there is no RAG + Places routing. That is the next phase.
