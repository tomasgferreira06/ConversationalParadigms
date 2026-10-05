"""MCP layer tests: tools are listed and called through an in-process MCP Client.

The weather service is replaced by a fake, so no HTTP and no subprocess is involved
(the real stdio round trip is checked separately by check_mcp_client.py).
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

from mcp import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server  # noqa: E402  (importing it must not start the server)
from weather_service import WeatherError  # noqa: E402

CURRENT_RESULT = {"location": {"name": "Coimbra"}, "current": {"temperature_c": 20.0}}
FORECAST_RESULT = {"location": {"name": "Coimbra"}, "forecast": [{"date": "2026-10-06"}]}


class FakeService:
    def __init__(self):
        self.calls = []
        self.error = None

    def get_current_weather(self, location):
        self.calls.append(("current", location))
        if self.error:
            raise self.error
        return CURRENT_RESULT

    def get_weather_forecast(self, location, days=3):
        self.calls.append(("forecast", location, days))
        if self.error:
            raise self.error
        return FORECAST_RESULT


class WeatherMCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fake = FakeService()
        patcher = mock.patch.object(server, "service", self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def tools(self):
        async with Client(server.mcp) as client:
            return {tool.name: tool for tool in (await client.list_tools()).tools}

    async def call(self, name, arguments):
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    def test_import_does_not_start_server(self):
        self.assertTrue(callable(server.main))
        self.assertEqual(server.mcp.name, "weather")

    async def test_exactly_the_two_expected_tools(self):
        self.assertEqual(set(await self.tools()), {"get_current_weather", "get_weather_forecast"})

    async def test_schemas(self):
        tools = await self.tools()
        current = tools["get_current_weather"].input_schema
        self.assertEqual(set(current["properties"]), {"location"})
        self.assertEqual(current["properties"]["location"]["type"], "string")
        self.assertEqual(current["required"], ["location"])
        forecast = tools["get_weather_forecast"].input_schema
        self.assertEqual(set(forecast["properties"]), {"location", "days"})
        self.assertEqual(forecast["properties"]["days"]["type"], "integer")
        self.assertEqual(forecast["properties"]["days"]["default"], 3)
        self.assertEqual(forecast["required"], ["location"])

    async def test_descriptions_guide_tool_use(self):
        tools = await self.tools()
        self.assertIn("neste momento", tools["get_current_weather"].description)
        self.assertIn("amanhã", tools["get_weather_forecast"].description)

    async def test_current_weather_delegates_to_service(self):
        result = await self.call("get_current_weather", {"location": "Coimbra, Portugal"})
        self.assertFalse(result.is_error)
        self.assertEqual(self.fake.calls, [("current", "Coimbra, Portugal")])
        self.assertEqual(result.structured_content, CURRENT_RESULT)

    async def test_forecast_delegates_to_service(self):
        result = await self.call("get_weather_forecast", {"location": "Coimbra", "days": 5})
        self.assertFalse(result.is_error)
        self.assertEqual(self.fake.calls, [("forecast", "Coimbra", 5)])
        self.assertEqual(result.structured_content, FORECAST_RESULT)

    async def test_forecast_default_days(self):
        await self.call("get_weather_forecast", {"location": "Coimbra"})
        self.assertEqual(self.fake.calls, [("forecast", "Coimbra", 3)])

    async def test_service_error_is_a_controlled_tool_error(self):
        self.fake.error = WeatherError("Localização não encontrada: 'Xyzzy'.")
        for name, args in (("get_current_weather", {"location": "Xyzzy"}),
                           ("get_weather_forecast", {"location": "Xyzzy", "days": 2})):
            result = await self.call(name, args)
            self.assertTrue(result.is_error)
            self.assertIn("Localização não encontrada", result.content[0].text)

    async def test_wrong_argument_type_is_rejected_by_schema(self):
        result = await self.call("get_weather_forecast", {"location": "Coimbra", "days": "many"})
        self.assertTrue(result.is_error)
        self.assertEqual(self.fake.calls, [])


if __name__ == "__main__":
    unittest.main()
