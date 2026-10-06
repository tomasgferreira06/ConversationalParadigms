"""Manual check (not a unit test; needs Internet): real MCP client -> real stdio server -> Nominatim.

Launches server.py as a subprocess over stdio with the SDK client, checks that exactly the
two expected tools exist, calls both for Coimbra and checks that an unknown place is an
error result. It never imports places_service. Exit code 0 only if every check holds.

Usage:
    uv run python d3/places_mcp/check_mcp_client.py
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

SERVER = Path(__file__).resolve().parent / "server.py"
EXPECTED_TOOLS = {"search_place", "get_distance_between_places"}
GARDEN = "Jardim Botânico da Universidade de Coimbra"


async def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    failures = []

    def check(condition: bool, text: str) -> None:
        print(("OK   " if condition else "FAIL ") + text)
        if not condition:
            failures.append(text)

    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with Client(params) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        check(names == EXPECTED_TOOLS, f"exactly the two tools are exposed: {sorted(names)}")

        search = await client.call_tool("search_place", {"query": GARDEN, "country_code": "pt"})
        print(json.dumps(search.structured_content, ensure_ascii=False, indent=2))
        check(not search.is_error and bool(search.structured_content["results"]), "search_place returns results")
        top = search.structured_content["results"][0]
        check("Coimbra" in top["display_name"], "top result is in Coimbra")
        check(39.5 < top["latitude"] < 41 and -9 < top["longitude"] < -8, "coordinates are plausible")
        check("OpenStreetMap" in search.structured_content["attribution"], "attribution present")

        distance = await client.call_tool("get_distance_between_places", {
            "origin": "Universidade de Coimbra", "destination": GARDEN, "country_code": "pt"})
        print(json.dumps(distance.structured_content, ensure_ascii=False, indent=2))
        data = distance.structured_content
        check(not distance.is_error, "get_distance_between_places succeeds")
        check(data["distance_type"] == "geodesic", "distance_type is geodesic")
        check(0 < data["straight_line_distance_km"] < 5, f"distance is plausible: {data['straight_line_distance_km']} km")

        missing = await client.call_tool("search_place", {"query": "Xyzzyville Qwertyland Nonexistent 12345"})
        print("unknown place ->", missing.is_error, missing.content[0].text)
        check(missing.is_error, "unknown place returns is_error=true")
    print("session closed cleanly")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
