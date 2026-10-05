"""Manual check (not a unit test; needs Internet): real MCP client -> real stdio server -> Open-Meteo.

Launches server.py as a subprocess over stdio with the SDK client, lists the tools and
calls both of them for Coimbra, printing the structured results.

Usage:
    uv run python d3/weather_mcp/check_mcp_client.py
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

SERVER = Path(__file__).resolve().parent / "server.py"


async def main() -> int:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with Client(params) as client:
        tools = (await client.list_tools()).tools
        print("tools:", [tool.name for tool in tools])
        for name, arguments in (
            ("get_current_weather", {"location": "Coimbra, Portugal"}),
            ("get_weather_forecast", {"location": "Coimbra, Portugal", "days": 3}),
            ("get_weather_forecast", {"location": "Coimbra, Portugal", "days": 8}),
            ("get_current_weather", {"location": "Xyzzyville"}),
        ):
            result = await client.call_tool(name, arguments)
            print(f"\n{name}({arguments}) is_error={result.is_error}")
            print(json.dumps(result.structured_content, ensure_ascii=False, indent=2)
                  if not result.is_error else result.content[0].text)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
