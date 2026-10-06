"""Generic long-lived MCP client over stdio (shared by the Weather and Places clients).

mcp 2.x's Client is async and must be entered and exited in the same task. To keep ONE
MCP session (one server subprocess) for the whole chat while the app stays synchronous,
a dedicated event loop runs in a background thread: one long-lived task owns
`async with Client(...)`, and calls from the chat thread are scheduled on that loop.

Subclasses only name the server (label, script, required tools) and its error class; they
never import the server's service code: everything goes through the MCP protocol.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import sys
import threading
from pathlib import Path
from typing import Any, Callable

START_TIMEOUT_SECONDS = 30.0
CALL_TIMEOUT_SECONDS = 30.0
CLOSE_TIMEOUT_SECONDS = 10.0


class MCPClientError(RuntimeError):
    """An MCP server could not start, lacks a required tool, or a tool call failed."""


def stdio_client_factory(server_path: Path) -> Callable[[], Any]:
    """The SDK Client launching `server_path` as a stdio subprocess."""

    def factory():
        from mcp import Client, StdioServerParameters

        return Client(StdioServerParameters(command=sys.executable, args=[str(server_path)]))

    return factory


class MCPStdioClient:
    label = "MCP"  # used in messages, e.g. "Weather MCP"
    required_tools: tuple[str, ...] = ()
    error_class: type[MCPClientError] = MCPClientError

    def __init__(self, client_factory: Callable[[], Any], call_timeout: float = CALL_TIMEOUT_SECONDS):
        self._factory = client_factory
        self._call_timeout = call_timeout
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None
        self._client = None
        self.tools: tuple[str, ...] = ()

    def _error(self, message: str) -> MCPClientError:
        return self.error_class(message)

    @property
    def started(self) -> bool:
        return self._client is not None

    # ---- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            raise self._error(f"The {self.label} client is already started.")
        ready: concurrent.futures.Future = concurrent.futures.Future()
        self._thread = threading.Thread(target=self._run, args=(ready,), name=self.label, daemon=True)
        self._thread.start()
        try:
            ready.result(timeout=START_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            self.close()
            raise self._error(f"Timeout while starting the {self.label} server.") from None
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
                missing = [name for name in self.required_tools if name not in names]
                if missing:
                    raise self._error(f"The {self.label} server does not expose the required tools: {missing}.")
                self._client, self.tools = client, names
                ready.set_result(None)
                await self._stop.wait()
        except BaseException as exc:  # reported to start() if it is still waiting
            if not ready.done():
                error = exc if isinstance(exc, MCPClientError) else self._error(
                    f"The {self.label} server could not be started: {type(exc).__name__}: {exc}")
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
            raise self._error(f"The {self.label} client is not running.")
        future = asyncio.run_coroutine_threadsafe(self._client.call_tool(name, arguments), self._loop)
        try:
            result = future.result(timeout=self._call_timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise self._error(f"Timeout calling the {self.label} tool {name}.") from None
        except Exception as exc:
            raise self._error(f"{self.label} call to {name} failed: {type(exc).__name__}: {exc}") from exc
        if result.is_error:
            message = " ".join(getattr(block, "text", "") for block in result.content).strip()
            raise self._error(f"{self.label} tool {name} returned an error: {message}")
        if not isinstance(result.structured_content, dict):
            raise self._error(f"{self.label} tool {name} returned no structured content.")
        return result.structured_content
