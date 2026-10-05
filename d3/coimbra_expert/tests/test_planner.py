"""Planner validation, retry and prompt-context tests (no Ollama)."""

import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import planner as pl  # noqa: E402


def dump(**plan):
    return json.dumps(plan)


FORECAST = {"tool": "get_weather_forecast", "location": "Coimbra, Portugal", "days": 2}


class ValidPlanTests(unittest.TestCase):
    def test_rag(self):
        plan = pl.parse_plan(dump(route="RAG", rag_query="Quem foi D. Dinis?", weather=None))
        self.assertEqual((plan.route, plan.weather), ("RAG", None))

    def test_rag_ignores_a_stray_weather_object(self):
        plan = pl.parse_plan(dump(route="RAG", rag_query=None, weather=FORECAST))
        self.assertEqual((plan.route, plan.weather), ("RAG", None))

    def test_weather_current(self):
        plan = pl.parse_plan(dump(route="WEATHER", rag_query=None, weather={
            "tool": "get_current_weather", "location": "Coimbra, Portugal", "days": None}))
        self.assertEqual(plan.weather, pl.WeatherRequest("get_current_weather", "Coimbra, Portugal", None))

    def test_weather_forecast(self):
        plan = pl.parse_plan(dump(route="WEATHER", rag_query=None, weather=FORECAST))
        self.assertEqual(plan.weather, pl.WeatherRequest("get_weather_forecast", "Coimbra, Portugal", 2))
        self.assertIsNone(plan.rag_query)

    def test_both(self):
        plan = pl.parse_plan(dump(route="BOTH", rag_query="O que é o Jardim Botânico?", weather=FORECAST))
        self.assertEqual(plan.route, "BOTH")
        self.assertEqual(plan.rag_query, "O que é o Jardim Botânico?")
        self.assertEqual(plan.weather.days, 2)

    def test_forecast_day_limits_are_inclusive(self):
        for days in (1, 7):
            plan = pl.parse_plan(dump(route="WEATHER", rag_query=None, weather=dict(FORECAST, days=days)))
            self.assertEqual(plan.weather.days, days)


class InvalidPlanTests(unittest.TestCase):
    def assertInvalid(self, text, fragment):
        with self.assertRaisesRegex(pl.PlanError, fragment):
            pl.parse_plan(text)

    def test_unknown_route(self):
        self.assertInvalid(dump(route="SEARCH", rag_query=None, weather=None), "route")

    def test_missing_route(self):
        self.assertInvalid(dump(rag_query=None, weather=None), "route")

    def test_unknown_weather_tool(self):
        bad = dict(FORECAST, tool="get_air_quality")
        self.assertInvalid(dump(route="WEATHER", rag_query=None, weather=bad), "weather.tool")

    def test_empty_location(self):
        for location in ("", "   ", None):
            self.assertInvalid(dump(route="WEATHER", rag_query=None, weather=dict(FORECAST, location=location)),
                               "location")

    def test_forecast_days_out_of_range(self):
        for days in (0, 8, -1, None, 2.5, "3", True):
            self.assertInvalid(dump(route="WEATHER", rag_query=None, weather=dict(FORECAST, days=days)),
                               "weather.days")

    def test_both_without_rag_query(self):
        for query in (None, "", "  "):
            self.assertInvalid(dump(route="BOTH", rag_query=query, weather=FORECAST), "rag_query")

    def test_both_without_weather(self):
        self.assertInvalid(dump(route="BOTH", rag_query="Jardim Botânico", weather=None), "weather")

    def test_weather_route_without_weather(self):
        self.assertInvalid(dump(route="WEATHER", rag_query=None, weather=None), "weather")

    def test_invalid_json(self):
        for text in ("not json", "", "[1, 2]", "null"):
            self.assertInvalid(text, "JSON|object")


class PlannerRetryTests(unittest.TestCase):
    def make(self, outputs):
        calls = []

        def llm(messages):
            calls.append(messages)
            return outputs[len(calls) - 1]

        return pl.Planner(llm, today=lambda: date(2026, 10, 5)), calls

    def test_valid_first_output_makes_one_call(self):
        planner, calls = self.make([dump(route="RAG", rag_query="x", weather=None)])
        self.assertEqual(planner.plan("Quem foi D. Dinis?").route, "RAG")
        self.assertEqual(len(calls), 1)

    def test_one_retry_recovers(self):
        planner, calls = self.make(["oops", dump(route="WEATHER", rag_query=None, weather=FORECAST)])
        self.assertEqual(planner.plan("q").route, "WEATHER")
        self.assertEqual(len(calls), 2)
        retry_text = "\n".join(m.content for m in calls[1])
        self.assertIn("Return a valid object matching this schema.", retry_text)

    def test_two_invalid_outputs_raise_and_never_fall_back(self):
        planner, calls = self.make(["oops", dump(route="NOPE", rag_query=None, weather=None), "third"])
        with self.assertRaises(pl.PlannerError):
            planner.plan("q")
        self.assertEqual(len(calls), 2)  # at most one retry

    def test_planner_receives_the_runtime_date(self):
        planner, calls = self.make([dump(route="RAG", rag_query="x", weather=None)])
        planner.plan("q")
        system = calls[0][0].content
        self.assertIn("2026-10-05", system)
        self.assertIn("segunda-feira", system)  # 2026-10-05 is a Monday


if __name__ == "__main__":
    unittest.main()
