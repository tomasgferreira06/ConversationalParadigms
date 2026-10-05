"""Real MCP client for the Weather MCP server (stdio); it never imports weather_service.

mcp 2.x's Client is async and must be entered and exited in the same task. To keep ONE
MCP session (one server subprocess) for the whole chat while the app stays synchronous,
a single dedicated event loop runs in a background thread: one long-lived task owns
`async with Client(...)`, and calls from the chat thread are scheduled on that loop.

    client = WeatherMCPClient()
    client.start()                                   # spawns the server, discovers tools
    client.get_weather_forecast("Coimbra, Portugal", 2)
    client.close()                                   # closes the session and the subprocess
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import sys
import threading
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = REPO_ROOT / "d3" / "weather_mcp" / "server.py"
REQUIRED_TOOLS = ("get_current_weather", "get_weather_forecast")
START_TIMEOUT_SECONDS = 30.0
CALL_TIMEOUT_SECONDS = 30.0
CLOSE_TIMEOUT_SECONDS = 10.0


class WeatherMCPError(RuntimeError):
    """The Weather MCP could not start, lacks a required tool, or a tool call failed."""


def stdio_client_factory():
    """Default: the SDK Client launching server.py as a stdio subprocess."""

    from mcp import Client, StdioServerParameters

    return Client(StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)]))


class WeatherMCPClient:
    def __init__(self, client_factory: Callable[[], Any] = stdio_client_factory,
                 call_timeout: float = CALL_TIMEOUT_SECONDS):
        self._factory = client_factory
        self._call_timeout = call_timeout
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None
        self._client = None
        self.tools: tuple[str, ...] = ()

    @property
    def started(self) -> bool:
        return self._client is not None

    # ---- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            raise WeatherMCPError("The Weather MCP client is already started.")
        ready: concurrent.futures.Future = concurrent.futures.Future()
        self._thread = threading.Thread(target=self._run, args=(ready,), name="weather-mcp", daemon=True)
        self._thread.start()
        try:
            ready.result(timeout=START_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            self.close()
            raise WeatherMCPError("Timeout while starting the Weather MCP server.") from None
        except BaseException:
            self._join()
            raise

    def _run(self, ready: concurrent.futures.Future) -> None:
        asyncio.run(self._serve(ready))

    async def _serve(self, ready: concurrent.futures.Future) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        try:
            async with self._factory() as client:
                names = tuple(tool.name for tool in (await client.list_tools()).tools)
                missing = [name for name in REQUIRED_TOOLS if name not in names]
                if missing:
                    raise WeatherMCPError(f"The Weather MCP server does not expose the required tools: {missing}.")
                self._client, self.tools = client, names
                ready.set_result(None)
                await self._stop.wait()
        except BaseException as exc:  # reported to start() if it is still waiting
            if not ready.done():
                error = exc if isinstance(exc, WeatherMCPError) else WeatherMCPError(
                    f"The Weather MCP server could not be started: {type(exc).__name__}: {exc}")
                ready.set_exception(error)
        finally:
            self._client = None

    def close(self) -> None:
        """Close the MCP session and the server subprocess (safe to call more than once)."""

        if self._loop is not None and self._stop is not None and self._thread is not None:
            try:
                self._loop.call_soon_threadsafe(self._stop.set)
            except RuntimeError:  # loop already closed
                pass
        self._join()

    def _join(self) -> None:
        if self._thread is not None:
            self._thread.join(timeout=CLOSE_TIMEOUT_SECONDS)
        self._thread = self._loop = self._stop = self._client = None

    # ---- tools -------------------------------------------------------------

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._client is None or self._loop is None:
            raise WeatherMCPError("The Weather MCP client is not running.")
        future = asyncio.run_coroutine_threadsafe(self._client.call_tool(name, arguments), self._loop)
        try:
            result = future.result(timeout=self._call_timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise WeatherMCPError(f"Timeout calling the Weather MCP tool {name}.") from None
        except Exception as exc:
            raise WeatherMCPError(f"Weather MCP call to {name} failed: {type(exc).__name__}: {exc}") from exc
        if result.is_error:
            message = " ".join(getattr(block, "text", "") for block in result.content).strip()
            raise WeatherMCPError(f"Weather MCP tool {name} returned an error: {message}")
        if not isinstance(result.structured_content, dict):
            raise WeatherMCPError(f"Weather MCP tool {name} returned no structured content.")
        return result.structured_content

    def get_current_weather(self, location: str) -> dict[str, Any]:
        return self.call_tool("get_current_weather", {"location": location})

    def get_weather_forecast(self, location: str, days: int) -> dict[str, Any]:
        return self.call_tool("get_weather_forecast", {"location": location, "days": days})
