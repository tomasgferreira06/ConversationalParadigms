"""Weather MCP server (MCP protocol layer only; all logic lives in weather_service).

Two tools over stdio: get_current_weather and get_weather_forecast. Importing this
module does not start anything; the server only runs from main().

Usage:
    uv run python d3/weather_mcp/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from weather_service import WeatherError, WeatherService  # noqa: E402

service = WeatherService()

mcp = MCPServer("weather", log_level="WARNING")  # INFO would print every HTTP request into the chat's stderr


@mcp.tool(
    name="get_current_weather",
    description=(
        "Obtém as condições meteorológicas atuais de uma localização. Use esta tool para perguntas "
        "sobre o tempo neste momento, temperatura atual, chuva atual, vento ou condições "
        "meteorológicas atuais. Unidades: °C, km/h, mm."
    ),
)
def get_current_weather(location: str) -> dict[str, Any]:
    try:
        return service.get_current_weather(location)
    except WeatherError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(
    name="get_weather_forecast",
    description=(
        "Obtém a previsão meteorológica para os próximos dias numa localização (1 a 7 dias, a "
        "começar hoje). Use esta tool para perguntas sobre amanhã, próximos dias, previsão de "
        "chuva ou temperaturas futuras. Unidades: °C, km/h, mm."
    ),
)
def get_weather_forecast(location: str, days: int = 3) -> dict[str, Any]:
    try:
        return service.get_weather_forecast(location, days)
    except WeatherError as exc:
        raise ToolError(str(exc)) from exc


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
