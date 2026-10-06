"""Planner validation, retry and prompt-context tests (no Ollama)."""

import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import planner as pl  # noqa: E402
import prompts  # noqa: E402


def plan_json(use_rag=False, rag_query=None, calls=()):
    return json.dumps({"use_rag": use_rag, "rag_query": rag_query, "tool_calls": list(calls)})


def call(server, tool, **arguments):
    return {"server": server, "tool": tool, "arguments": arguments}


W_CURRENT = call("weather", "get_current_weather", location="Coimbra, Portugal")
W_FORECAST = call("weather", "get_weather_forecast", location="Coimbra, Portugal", days=2)
P_SEARCH = call("places", "search_place", query="Sé Velha, Coimbra", country_code="pt")
P_DISTANCE = call("places", "get_distance_between_places", origin="A, Coimbra", destination="B, Coimbra",
                  country_code="pt")


class ValidPlanTests(unittest.TestCase):
    def test_1_rag_only(self):
        plan = pl.parse_plan(plan_json(True, "Quem foi D. Dinis?"))
        self.assertEqual((plan.use_rag, plan.tool_calls), (True, ()))
        self.assertEqual(plan.rag_query, "Quem foi D. Dinis?")

    def test_1b_rag_only_does_not_need_a_rag_query(self):
        plan = pl.parse_plan(plan_json(True, None))
        self.assertEqual((plan.use_rag, plan.rag_query, plan.tool_calls), (True, None, ()))

    def test_2_weather_current_only(self):
        plan = pl.parse_plan(plan_json(calls=[W_CURRENT]))
        self.assertFalse(plan.use_rag)
        self.assertIsNone(plan.rag_query)
        self.assertEqual(plan.tool_calls, (pl.ToolCall("weather", "get_current_weather",
                                                       {"location": "Coimbra, Portugal"}),))

    def test_3_weather_forecast_only(self):
        plan = pl.parse_plan(plan_json(calls=[W_FORECAST]))
        self.assertEqual(plan.tool_calls[0].arguments, {"location": "Coimbra, Portugal", "days": 2})

    def test_4_places_search_only(self):
        plan = pl.parse_plan(plan_json(calls=[P_SEARCH]))
        self.assertEqual(plan.tool_calls[0], pl.ToolCall("places", "search_place",
                                                         {"query": "Sé Velha, Coimbra", "country_code": "pt"}))

    def test_5_places_distance_only(self):
        plan = pl.parse_plan(plan_json(calls=[P_DISTANCE]))
        self.assertEqual(plan.tool_calls[0].arguments["destination"], "B, Coimbra")

    def test_6_rag_plus_weather(self):
        plan = pl.parse_plan(plan_json(True, "O que é o Jardim da Sereia?", [W_FORECAST]))
        self.assertTrue(plan.use_rag)
        self.assertEqual([c.server for c in plan.tool_calls], ["weather"])

    def test_7_rag_plus_places(self):
        plan = pl.parse_plan(plan_json(True, "Importância da Sé Velha", [P_SEARCH]))
        self.assertEqual([c.server for c in plan.tool_calls], ["places"])

    def test_8_weather_plus_places(self):
        plan = pl.parse_plan(plan_json(False, None, [W_CURRENT, P_SEARCH]))
        self.assertEqual([c.server for c in plan.tool_calls], ["weather", "places"])
        self.assertFalse(plan.use_rag)

    def test_9_rag_plus_weather_plus_places(self):
        plan = pl.parse_plan(plan_json(True, "Sé Velha", [W_FORECAST, P_SEARCH]))
        self.assertEqual((plan.use_rag, [c.server for c in plan.tool_calls]), (True, ["weather", "places"]))
        self.assertEqual(plan.call_for("places").tool, "search_place")
        self.assertIsNone(pl.parse_plan(plan_json(calls=[W_CURRENT])).call_for("places"))

    def test_order_of_calls_is_kept(self):
        plan = pl.parse_plan(plan_json(False, None, [P_SEARCH, W_CURRENT]))
        self.assertEqual([c.server for c in plan.tool_calls], ["places", "weather"])

    def test_null_arguments_are_treated_as_not_given(self):
        plan = pl.parse_plan(plan_json(calls=[call("places", "search_place", query="Sé", country_code=None,
                                                    origin=None, destination=None, location=None, days=None)]))
        self.assertEqual(plan.tool_calls[0].arguments, {"query": "Sé"})

    def test_current_weather_tolerates_null_days_and_drops_it(self):
        plan = pl.parse_plan(plan_json(calls=[call("weather", "get_current_weather", location="X, Portugal", days=3)]))
        self.assertEqual(plan.tool_calls[0].arguments, {"location": "X, Portugal"})

    def test_country_code_is_normalised_and_forecast_limits_are_inclusive(self):
        plan = pl.parse_plan(plan_json(calls=[call("places", "search_place", query="Sé", country_code="PT")]))
        self.assertEqual(plan.tool_calls[0].arguments["country_code"], "pt")
        for days in (1, 7):
            ok = pl.parse_plan(plan_json(calls=[call("weather", "get_weather_forecast", location="X", days=days)]))
            self.assertEqual(ok.tool_calls[0].arguments["days"], days)

    def test_rag_query_is_dropped_when_rag_is_not_used(self):
        self.assertIsNone(pl.parse_plan(plan_json(False, "ignored", [W_CURRENT])).rag_query)


class InvalidPlanTests(unittest.TestCase):
    def assertInvalid(self, text, fragment):
        with self.assertRaisesRegex(pl.PlanError, fragment):
            pl.parse_plan(text)

    def test_10_rag_with_tool_calls_needs_a_rag_query(self):
        for query in (None, "", "  "):
            self.assertInvalid(plan_json(True, query, [W_CURRENT]), "rag_query")

    def test_11_unknown_server(self):
        self.assertInvalid(plan_json(calls=[call("maps", "search_place", query="x")]), "server")

    def test_12_unknown_tool(self):
        self.assertInvalid(plan_json(calls=[call("weather", "get_air_quality", location="x")]), "tool")
        self.assertInvalid(plan_json(calls=[call("weather", "search_place", query="x")]), "tool")  # wrong server

    def test_13_weather_location_empty(self):
        for location in ("", "   ", None):
            self.assertInvalid(plan_json(calls=[call("weather", "get_current_weather", location=location)]), "location")
            self.assertInvalid(plan_json(calls=[call("weather", "get_weather_forecast", location=location, days=2)]),
                               "location")

    def test_14_15_forecast_days_out_of_range(self):
        for days in (0, 8, -1, None, 2.5, "3", True):
            self.assertInvalid(plan_json(calls=[call("weather", "get_weather_forecast", location="X", days=days)]),
                               "days")

    def test_16_places_query_empty(self):
        for query in ("", "  ", None):
            self.assertInvalid(plan_json(calls=[call("places", "search_place", query=query)]), "query")

    def test_17_distance_origin_empty(self):
        for origin in ("", " ", None):
            self.assertInvalid(plan_json(calls=[call("places", "get_distance_between_places",
                                                     origin=origin, destination="B")]), "origin")

    def test_18_distance_destination_empty(self):
        for destination in ("", " ", None):
            self.assertInvalid(plan_json(calls=[call("places", "get_distance_between_places",
                                                     origin="A", destination=destination)]), "destination")

    def test_19_invalid_country_code(self):
        for bad in ("portugal", "p", "1a", "", 5, "p t"):
            self.assertInvalid(plan_json(calls=[call("places", "search_place", query="Sé", country_code=bad)]),
                               "country_code")
            self.assertInvalid(plan_json(calls=[call("places", "get_distance_between_places", origin="A",
                                                     destination="B", country_code=bad)]), "country_code")

    def test_20_two_weather_calls(self):
        self.assertInvalid(plan_json(calls=[W_CURRENT, W_FORECAST]), "one tool call per server")

    def test_21_two_places_calls(self):
        self.assertInvalid(plan_json(calls=[P_SEARCH, P_DISTANCE]), "one tool call per server")

    def test_22_more_than_two_calls(self):
        self.assertInvalid(plan_json(calls=[W_CURRENT, P_SEARCH, P_DISTANCE]), "at most 2")

    def test_23_invalid_json(self):
        for text in ("not json", "", "[1, 2]", "null"):
            self.assertInvalid(text, "JSON|object")

    def test_no_capability_at_all_is_invalid(self):
        self.assertInvalid(plan_json(False, None, []), "no capability")

    def test_use_rag_must_be_a_boolean(self):
        for bad in ("true", 1, None):
            self.assertInvalid(json.dumps({"use_rag": bad, "rag_query": "x", "tool_calls": []}), "use_rag")

    def test_tool_calls_must_be_a_list(self):
        for bad in (None, "x", {}):
            self.assertInvalid(json.dumps({"use_rag": True, "rag_query": "x", "tool_calls": bad}), "tool_calls")
        self.assertInvalid(json.dumps({"use_rag": True, "rag_query": "x"}), "tool_calls")

    def test_missing_or_unexpected_arguments(self):
        self.assertInvalid(plan_json(calls=[call("places", "get_distance_between_places", origin="A")]), "destination")
        self.assertInvalid(plan_json(calls=[call("places", "search_place", query="Sé", location="Coimbra")]),
                           "unexpected arguments")
        self.assertInvalid(plan_json(calls=[{"server": "places", "tool": "search_place", "arguments": "Sé"}]),
                           "arguments must be an object")
        self.assertInvalid(plan_json(calls=["search_place"]), "must be an object")

    def test_old_route_schema_is_not_accepted(self):
        self.assertInvalid(json.dumps({"route": "RAG", "rag_query": None, "weather": None}), "use_rag")


class PlannerRetryTests(unittest.TestCase):
    def make(self, outputs):
        calls = []

        def llm(messages):
            calls.append(messages)
            return outputs[len(calls) - 1]

        return pl.Planner(llm, today=lambda: date(2026, 10, 5)), calls

    def test_valid_first_output_makes_one_call(self):
        planner, calls = self.make([plan_json(True, "x")])
        self.assertTrue(planner.plan("Quem foi D. Dinis?").use_rag)
        self.assertEqual(len(calls), 1)

    def test_one_retry_recovers(self):
        planner, calls = self.make(["oops", plan_json(calls=[W_FORECAST])])
        self.assertEqual(planner.plan("q").tool_calls[0].tool, "get_weather_forecast")
        self.assertEqual(len(calls), 2)
        retry_text = "\n".join(m.content for m in calls[1])
        self.assertIn("Return a valid object matching this schema.", retry_text)

    def test_24_retry_failing_again_raises_and_never_falls_back(self):
        planner, calls = self.make(["oops", plan_json(False, None, []), "third"])
        with self.assertRaises(pl.PlannerError):
            planner.plan("q")
        self.assertEqual(len(calls), 2)  # at most one retry

    def test_planner_receives_the_runtime_date(self):
        planner, calls = self.make([plan_json(True, "x")])
        planner.plan("q")
        system = calls[0][0].content
        self.assertIn("2026-10-05", system)
        self.assertIn("segunda-feira", system)  # 2026-10-05 is a Monday


class PlannerPromptTests(unittest.TestCase):
    """Invariants of the planner system prompt (they do not prove that planning improves: that is a dev check)."""

    SYSTEM = prompts.PLANNER_SYSTEM

    def test_capabilities_are_defined_semantically(self):
        for text in ("RAG is NOT the source for", "Weather is never looked up in RAG", "whenever ANY part of the question",
                     "Do not try to get location or distance from RAG", "even if the question does not say"):
            self.assertIn(text, self.SYSTEM)

    def test_multi_intent_and_independence_rules(self):
        for text in ("Multi-intent rule", "Do not choose only the dominant capability", "select every capability that is needed",
                     "Independence rule", "needing RAG does not remove the need for Weather or Places",
                     "Needing Weather does not remove Places", "Needing Places does not remove RAG"):
            self.assertIn(text, self.SYSTEM)

    def test_rag_query_is_only_the_knowledge_part(self):
        self.assertIn("ONLY the part of the question that needs stable knowledge", self.SYSTEM)
        self.assertIn("never moved into rag_query", self.SYSTEM)

    def test_decomposition_is_silent_no_reasoning_is_requested(self):
        self.assertIn("do this silently; never write your analysis", self.SYSTEM)
        self.assertIn("JSON only, no explanations, no reasoning", self.SYSTEM)

    def test_every_few_shot_example_is_a_valid_plan(self):
        lines = self.SYSTEM.splitlines()
        examples = [(q, lines[i + 1]) for i, q in enumerate(lines) if q.startswith("Question:")]
        self.assertEqual(len(examples), 9)
        shapes = set()
        for _question, answer in examples:
            plan = pl.parse_plan(answer)
            shapes.add((plan.use_rag, tuple(sorted(c.server for c in plan.tool_calls))))
        self.assertEqual(len(shapes), 7)  # every combination of RAG / Weather / Places is shown at least once

    def test_examples_do_not_reuse_the_smoke_test_questions(self):
        for smoke_term in ("Sé Velha", "Jardim da Sereia", "Jardim Botânico", "Estação Nova", "Universidade de Coimbra"):
            self.assertNotIn(smoke_term, self.SYSTEM)

    def test_the_prompt_is_not_a_keyword_rule(self):
        self.assertNotRegex(self.SYSTEM, r"(?i)\bif the (text|question) contains\b")
        self.assertNotRegex(self.SYSTEM, r"(?i)\bkeyword")


class PlanSchemaTests(unittest.TestCase):
    def test_schema_matches_the_validator(self):
        schema = prompts.PLAN_SCHEMA
        self.assertEqual(set(schema["required"]), {"use_rag", "rag_query", "tool_calls"})
        item = schema["properties"]["tool_calls"]["items"]["properties"]
        self.assertEqual(schema["properties"]["tool_calls"]["maxItems"], pl.MAX_TOOL_CALLS)
        self.assertEqual(set(item["server"]["enum"]), set(pl.SERVER_TOOLS))
        self.assertEqual(set(item["tool"]["enum"]), {t for tools in pl.SERVER_TOOLS.values() for t in tools})
        known = set(item["arguments"]["properties"])
        allowed = {key for required, optional in pl.TOOL_ARGUMENTS.values() for key in required + optional}
        self.assertEqual(known, allowed)


if __name__ == "__main__":
    unittest.main()
