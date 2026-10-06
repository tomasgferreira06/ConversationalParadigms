"""Real MCP client for the Places MCP server (stdio); it never imports places_service.

    client = PlacesMCPClient()
    client.start()                                   # spawns the server, discovers tools
    client.search_place("Sé Velha, Coimbra", "pt")
    client.close()                                   # closes the session and the subprocess

The lifecycle (one session per run, one background event loop) is in mcp_stdio_client.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from mcp_stdio_client import CALL_TIMEOUT_SECONDS, MCPClientError, MCPStdioClient, stdio_client_factory

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = REPO_ROOT / "d3" / "places_mcp" / "server.py"
REQUIRED_TOOLS = ("search_place", "get_distance_between_places")


class PlacesMCPError(MCPClientError):
    """The Places MCP could not start, lacks a required tool, or a tool call failed."""


class PlacesMCPClient(MCPStdioClient):
    label = "Places MCP"
    required_tools = REQUIRED_TOOLS
    error_class = PlacesMCPError

    def __init__(self, client_factory: Callable[[], Any] | None = None, call_timeout: float = CALL_TIMEOUT_SECONDS):
        super().__init__(client_factory or stdio_client_factory(SERVER_PATH), call_timeout)

    def search_place(self, query: str, country_code: str | None = None) -> dict[str, Any]:
        return self.call_tool("search_place", {"query": query, "country_code": country_code})

    def get_distance_between_places(self, origin: str, destination: str,
                                    country_code: str | None = None) -> dict[str, Any]:
        return self.call_tool("get_distance_between_places",
                              {"origin": origin, "destination": destination, "country_code": country_code})
