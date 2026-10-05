"""WeatherMCPClient: lifecycle, discovery, calls, errors and shutdown.

Most tests use a fake async MCP client; one real stdio test launches the actual Weather MCP
server (no Internet: it only lists tools and triggers a validation error that the server
rejects before any HTTP request).
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import weather_mcp_client as wc  # noqa: E402


def tool_result(structured=None, is_error=False, text=""):
    return SimpleNamespace(is_error=is_error, structured_content=structured, content=[SimpleNamespace(text=text)])


class FakeClient:
    """Async context manager with the bits of mcp.Client the wrapper uses."""

    def __init__(self, tools=wc.REQUIRED_TOOLS, results=None, fail_on_enter=None):
        self.tools, self.results, self.fail_on_enter = tools, results or {}, fail_on_enter
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
        return self.results.get(name, tool_result({"ok": True}))


def started(fake):
    client = wc.WeatherMCPClient(client_factory=lambda: fake)
    client.start()
    return client


class LifecycleTests(unittest.TestCase):
    def test_start_discovers_tools_and_close_exits_the_session_once(self):
        fake = FakeClient()
        client = started(fake)
        self.assertTrue(client.started)
        self.assertEqual(client.tools, wc.REQUIRED_TOOLS)
        self.assertEqual((fake.entered, fake.exited), (1, 0))
        client.close()
        self.assertEqual((fake.entered, fake.exited), (1, 1))
        self.assertFalse(client.started)
        client.close()  # idempotent
        self.assertEqual(fake.exited, 1)

    def test_one_session_serves_many_calls(self):
        fake = FakeClient()
        client = started(fake)
        for _ in range(3):
            client.get_current_weather("Coimbra, Portugal")
        client.close()
        self.assertEqual(fake.entered, 1)
        self.assertEqual(len(fake.calls), 3)

    def test_missing_required_tool_fails_clearly_and_closes(self):
        fake = FakeClient(tools=("get_current_weather",))
        client = wc.WeatherMCPClient(client_factory=lambda: fake)
        with self.assertRaisesRegex(wc.WeatherMCPError, "get_weather_forecast"):
            client.start()
        self.assertEqual(fake.exited, 1)
        self.assertFalse(client.started)

    def test_server_that_cannot_start_fails_clearly(self):
        client = wc.WeatherMCPClient(client_factory=lambda: FakeClient(fail_on_enter=FileNotFoundError("no server")))
        with self.assertRaisesRegex(wc.WeatherMCPError, "could not be started.*no server"):
            client.start()

    def test_calls_before_start_or_after_close_are_errors(self):
        client = wc.WeatherMCPClient(client_factory=lambda: FakeClient())
        with self.assertRaisesRegex(wc.WeatherMCPError, "not running"):
            client.get_current_weather("Coimbra")
        client = started(FakeClient())
        client.close()
        with self.assertRaisesRegex(wc.WeatherMCPError, "not running"):
            client.get_current_weather("Coimbra")


class CallTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeClient(results={
            "get_current_weather": tool_result({"current": {"temperature_c": 20.0}}),
            "get_weather_forecast": tool_result({"forecast": [{"date": "2026-10-06"}]}),
        })
        self.client = started(self.fake)
        self.addCleanup(self.client.close)

    def test_current_call(self):
        self.assertEqual(self.client.get_current_weather("Coimbra, Portugal"), {"current": {"temperature_c": 20.0}})
        self.assertEqual(self.fake.calls, [("get_current_weather", {"location": "Coimbra, Portugal"})])

    def test_forecast_call(self):
        self.assertEqual(self.client.get_weather_forecast("Coimbra, Portugal", 3), {"forecast": [{"date": "2026-10-06"}]})
        self.assertEqual(self.fake.calls, [("get_weather_forecast", {"location": "Coimbra, Portugal", "days": 3})])

    def test_controlled_mcp_error(self):
        self.fake.results["get_current_weather"] = tool_result(is_error=True, text="Localização não encontrada")
        with self.assertRaisesRegex(wc.WeatherMCPError, "Localização não encontrada"):
            self.client.get_current_weather("Xyzzy")

    def test_transport_failure_is_wrapped(self):
        async def boom(name, arguments):
            raise ConnectionError("pipe closed")
        self.fake.call_tool = boom
        with self.assertRaisesRegex(wc.WeatherMCPError, "pipe closed"):
            self.client.get_current_weather("Coimbra")

    def test_missing_structured_content_is_an_error(self):
        self.fake.results["get_current_weather"] = tool_result(None)
        with self.assertRaisesRegex(wc.WeatherMCPError, "structured"):
            self.client.get_current_weather("Coimbra")


class RealStdioServerTests(unittest.TestCase):
    def test_real_server_over_stdio_without_internet(self):
        client = wc.WeatherMCPClient()
        client.start()
        try:
            self.assertEqual(set(client.tools), set(wc.REQUIRED_TOOLS))
            with self.assertRaisesRegex(wc.WeatherMCPError, "entre 1 e 7"):
                client.get_weather_forecast("Coimbra, Portugal", 8)  # rejected before any request
        finally:
            client.close()
        self.assertFalse(client.started)


if __name__ == "__main__":
    unittest.main()
