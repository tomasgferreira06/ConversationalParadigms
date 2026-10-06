"""PlacesMCPClient: lifecycle, discovery, calls, errors, timeout and shutdown (no Internet).

Most tests use a fake async MCP client; one real stdio test launches the actual Places MCP server and
only triggers validation errors that the server raises before any HTTP request to Nominatim.
"""

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import places_mcp_client as pc  # noqa: E402
from mcp_stdio_client import MCPClientError  # noqa: E402


def tool_result(structured=None, is_error=False, text=""):
    return SimpleNamespace(is_error=is_error, structured_content=structured, content=[SimpleNamespace(text=text)])


class FakeClient:
    """Async context manager with the bits of mcp.Client the wrapper uses."""

    def __init__(self, tools=pc.REQUIRED_TOOLS, results=None, fail_on_enter=None, delay=0.0):
        self.tools, self.results, self.fail_on_enter, self.delay = tools, results or {}, fail_on_enter, delay
        self.calls, self.entered, self.exited = [], 0, 0

    async def __aenter__(self):
        if self.fail_on_enter:
            raise self.fail_on_enter
        self.entered += 1
        return self

    async def __aexit__(self, *exc):
        self.exited += 1

    async def list_tools(self):
        return SimpleNamespace(tools=[SimpleNamespace(name=name) for name in self.tools])

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.results.get(name, tool_result({"ok": True}))


def started(fake, **kwargs):
    client = pc.PlacesMCPClient(client_factory=lambda: fake, **kwargs)
    client.start()
    return client


class LifecycleTests(unittest.TestCase):
    def test_start_discovers_the_two_required_tools_and_close_exits_the_session_once(self):
        fake = FakeClient()
        client = started(fake)
        self.assertTrue(client.started)
        self.assertEqual(client.tools, ("search_place", "get_distance_between_places"))
        self.assertEqual((fake.entered, fake.exited), (1, 0))
        thread = client._thread
        client.close()
        self.assertEqual((fake.entered, fake.exited), (1, 1))
        self.assertFalse(client.started)
        self.assertFalse(thread.is_alive())  # nothing left running
        client.close()  # idempotent
        self.assertEqual(fake.exited, 1)

    def test_one_session_serves_many_calls(self):
        fake = FakeClient()
        client = started(fake)
        for _ in range(3):
            client.search_place("Sé Velha, Coimbra", "pt")
        client.close()
        self.assertEqual(fake.entered, 1)
        self.assertEqual(len(fake.calls), 3)

    def test_missing_required_tool_fails_clearly_and_closes(self):
        fake = FakeClient(tools=("search_place",))
        client = pc.PlacesMCPClient(client_factory=lambda: fake)
        with self.assertRaisesRegex(pc.PlacesMCPError, "Places MCP.*get_distance_between_places"):
            client.start()
        self.assertEqual(fake.exited, 1)
        self.assertFalse(client.started)

    def test_server_that_cannot_start_fails_clearly(self):
        client = pc.PlacesMCPClient(client_factory=lambda: FakeClient(fail_on_enter=FileNotFoundError("no server")))
        with self.assertRaisesRegex(pc.PlacesMCPError, "Places MCP server could not be started.*no server"):
            client.start()

    def test_calls_before_start_or_after_close_are_errors(self):
        client = pc.PlacesMCPClient(client_factory=lambda: FakeClient())
        with self.assertRaisesRegex(pc.PlacesMCPError, "not running"):
            client.search_place("Sé")
        client = started(FakeClient())
        client.close()
        with self.assertRaisesRegex(pc.PlacesMCPError, "not running"):
            client.search_place("Sé")

    def test_errors_are_mcp_client_errors(self):
        self.assertTrue(issubclass(pc.PlacesMCPError, MCPClientError))


class CallTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeClient(results={
            "search_place": tool_result({"results": [{"name": "Sé Velha"}]}),
            "get_distance_between_places": tool_result({"straight_line_distance_km": 0.84, "distance_type": "geodesic"}),
        })
        self.client = started(self.fake)
        self.addCleanup(self.client.close)

    def test_search_place_call(self):
        self.assertEqual(self.client.search_place("Sé Velha, Coimbra", "pt"), {"results": [{"name": "Sé Velha"}]})
        self.assertEqual(self.fake.calls, [("search_place", {"query": "Sé Velha, Coimbra", "country_code": "pt"})])

    def test_distance_call(self):
        result = self.client.get_distance_between_places("A", "B", "pt")
        self.assertEqual(result["distance_type"], "geodesic")
        self.assertEqual(self.fake.calls, [("get_distance_between_places",
                                            {"origin": "A", "destination": "B", "country_code": "pt"})])

    def test_generic_call_tool_is_what_the_expert_uses(self):
        self.client.call_tool("search_place", {"query": "Sé"})
        self.assertEqual(self.fake.calls, [("search_place", {"query": "Sé"})])

    def test_controlled_tool_error(self):
        self.fake.results["search_place"] = tool_result(is_error=True, text="Local não encontrado: 'Xyzzy'.")
        with self.assertRaisesRegex(pc.PlacesMCPError, "Places MCP tool search_place returned an error.*Xyzzy"):
            self.client.search_place("Xyzzy")

    def test_transport_failure_is_wrapped(self):
        async def boom(name, arguments):
            raise ConnectionError("pipe closed")
        self.fake.call_tool = boom
        with self.assertRaisesRegex(pc.PlacesMCPError, "pipe closed"):
            self.client.search_place("Sé")

    def test_missing_structured_content_is_an_error(self):
        self.fake.results["search_place"] = tool_result(None)
        with self.assertRaisesRegex(pc.PlacesMCPError, "structured"):
            self.client.search_place("Sé")


class TimeoutTests(unittest.TestCase):
    def test_slow_tool_call_times_out_and_the_session_keeps_working(self):
        fake = FakeClient(delay=2.0)
        client = started(fake, call_timeout=0.2)
        self.addCleanup(client.close)
        with self.assertRaisesRegex(pc.PlacesMCPError, "Timeout calling the Places MCP tool search_place"):
            client.search_place("Sé")
        fake.delay = 0.0
        self.assertEqual(client.search_place("Sé"), {"ok": True})  # the session survived the timeout


class NoDirectServiceUseTests(unittest.TestCase):
    def test_clients_never_import_the_service_modules(self):
        for name in ("places_mcp_client.py", "weather_mcp_client.py", "mcp_stdio_client.py", "expert_agent.py"):
            source = (Path(__file__).resolve().parents[1] / name).read_text(encoding="utf-8")
            self.assertNotRegex(source, r"(?m)^\s*(import|from)\s+(places_service|weather_service)\b")
        self.assertNotIn("places_service", sys.modules)
        self.assertNotIn("weather_service", sys.modules)


class RealStdioServerTests(unittest.TestCase):
    def test_real_server_over_stdio_without_internet(self):
        client = pc.PlacesMCPClient()
        client.start()
        thread = client._thread
        try:
            self.assertEqual(set(client.tools), set(pc.REQUIRED_TOOLS))
            with self.assertRaisesRegex(pc.PlacesMCPError, "country_code"):
                client.search_place("Sé Velha, Coimbra", "portugal")  # rejected before any request
            with self.assertRaisesRegex(pc.PlacesMCPError, "vazio"):
                client.get_distance_between_places("", "B", "pt")
        finally:
            client.close()
        self.assertFalse(client.started)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
