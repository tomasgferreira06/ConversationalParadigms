"""MCP layer tests: tools are listed and called through an in-process MCP Client.

The places service is replaced by a fake, so no HTTP and no subprocess is involved
(the real stdio round trip is checked separately by check_mcp_client.py).
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

from mcp import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server  # noqa: E402  (importing it must not start the server)
from places_service import PlacesError  # noqa: E402

SEARCH_RESULT = {"query": "Sé Velha", "country_code": "pt", "results": [{"name": "Sé Velha"}], "attribution": "© OSM"}
DISTANCE_RESULT = {"origin": {"name": "A"}, "destination": {"name": "B"}, "straight_line_distance_km": 0.84,
                   "distance_type": "geodesic", "attribution": "© OSM"}


class FakeService:
    def __init__(self):
        self.calls, self.error = [], None

    def search_place(self, query, country_code=None):
        self.calls.append(("search", query, country_code))
        if self.error:
            raise self.error
        return SEARCH_RESULT

    def get_distance_between_places(self, origin, destination, country_code=None):
        self.calls.append(("distance", origin, destination, country_code))
        if self.error:
            raise self.error
        return DISTANCE_RESULT


class PlacesMCPTests(unittest.IsolatedAsyncioTestCase):
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
        self.assertEqual(server.mcp.name, "places")

    async def test_exactly_the_two_expected_tools(self):
        self.assertEqual(set(await self.tools()), {"search_place", "get_distance_between_places"})

    async def test_search_place_schema(self):
        schema = (await self.tools())["search_place"].input_schema
        self.assertEqual(set(schema["properties"]), {"query", "country_code"})
        self.assertEqual(schema["properties"]["query"]["type"], "string")
        self.assertEqual(schema["required"], ["query"])  # country_code is optional

    async def test_distance_schema(self):
        schema = (await self.tools())["get_distance_between_places"].input_schema
        self.assertEqual(set(schema["properties"]), {"origin", "destination", "country_code"})
        self.assertEqual(sorted(schema["required"]), ["destination", "origin"])

    async def test_descriptions_guide_tool_use_and_state_distance_semantics(self):
        tools = await self.tools()
        self.assertIn("onde fica", tools["search_place"].description)
        description = tools["get_distance_between_places"].description
        self.assertIn("geodésica em linha reta", description)
        self.assertIn("Não representa distância rodoviária, pedonal ou tempo de viagem", description)

    async def test_search_place_delegates_to_service(self):
        result = await self.call("search_place", {"query": "Sé Velha", "country_code": "pt"})
        self.assertFalse(result.is_error)
        self.assertEqual(self.fake.calls, [("search", "Sé Velha", "pt")])
        self.assertEqual(result.structured_content, SEARCH_RESULT)

    async def test_search_place_country_code_defaults_to_none(self):
        await self.call("search_place", {"query": "Sé Velha"})
        self.assertEqual(self.fake.calls, [("search", "Sé Velha", None)])

    async def test_distance_delegates_to_service(self):
        result = await self.call("get_distance_between_places", {"origin": "A", "destination": "B", "country_code": "pt"})
        self.assertFalse(result.is_error)
        self.assertEqual(self.fake.calls, [("distance", "A", "B", "pt")])
        self.assertEqual(result.structured_content, DISTANCE_RESULT)

    async def test_service_error_is_a_controlled_tool_error(self):
        self.fake.error = PlacesError("Local não encontrado: 'Xyzzy'.")
        for name, args in (("search_place", {"query": "Xyzzy"}),
                           ("get_distance_between_places", {"origin": "Xyzzy", "destination": "B"})):
            result = await self.call(name, args)
            self.assertTrue(result.is_error)
            self.assertIn("Local não encontrado", result.content[0].text)

    async def test_missing_required_argument_is_rejected_by_schema(self):
        result = await self.call("get_distance_between_places", {"origin": "A"})
        self.assertTrue(result.is_error)
        self.assertEqual(self.fake.calls, [])


if __name__ == "__main__":
    unittest.main()
