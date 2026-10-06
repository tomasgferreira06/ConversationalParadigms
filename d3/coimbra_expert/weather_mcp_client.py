"""Real MCP client for the Weather MCP server (stdio); it never imports weather_service.

    client = WeatherMCPClient()
    client.start()                                   # spawns the server, discovers tools
    client.get_weather_forecast("Coimbra, Portugal", 2)
    client.close()                                   # closes the session and the subprocess

The lifecycle (one session per run, one background event loop) is in mcp_stdio_client.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from mcp_stdio_client import CALL_TIMEOUT_SECONDS, MCPClientError, MCPStdioClient, stdio_client_factory

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = REPO_ROOT / "d3" / "weather_mcp" / "server.py"
REQUIRED_TOOLS = ("get_current_weather", "get_weather_forecast")


class WeatherMCPError(MCPClientError):
    """The Weather MCP could not start, lacks a required tool, or a tool call failed."""


class WeatherMCPClient(MCPStdioClient):
    label = "Weather MCP"
    required_tools = REQUIRED_TOOLS
    error_class = WeatherMCPError

    def __init__(self, client_factory: Callable[[], Any] | None = None, call_timeout: float = CALL_TIMEOUT_SECONDS):
        super().__init__(client_factory or stdio_client_factory(SERVER_PATH), call_timeout)

    def get_current_weather(self, location: str) -> dict[str, Any]:
        return self.call_tool("get_current_weather", {"location": location})

    def get_weather_forecast(self, location: str, days: int) -> dict[str, Any]:
        return self.call_tool("get_weather_forecast", {"location": location, "days": days})
