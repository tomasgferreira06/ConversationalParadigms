"""Coimbra Expert Agent orchestration with mocks (no Ollama, Open-Meteo, Chroma or MCP process)."""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import expert_agent as ea  # noqa: E402
from planner import Plan, Planner, PlannerError, WeatherRequest  # noqa: E402
from weather_mcp_client import WeatherMCPError  # noqa: E402

TODAY = date(2026, 10, 5)
FORECAST = WeatherRequest("get_weather_forecast", "Coimbra, Portugal", 2)
CURRENT = WeatherRequest("get_current_weather", "Coimbra, Portugal", None)
WEATHER_DATA = {"location": {"name": "Coimbra"}, "forecast": [{"date": "2026-10-06", "weather_description": "Chuva fraca"}]}
DOC = Document(page_content="O Jardim Botânico foi criado em 1772.", metadata={
    "title": "Jardim Botânico", "document_id": "jb", "source_type": "web", "canonical_url": "https://x/jb",
    "section_path": ["História"]})


def build(plan=None, planner_error=None, results=None):
    planner = mock.Mock()
    if planner_error:
        planner.plan.side_effect = planner_error
    else:
        planner.plan.return_value = plan
    rag = mock.Mock()
    rag.respond.return_value = "Resposta RAG.\n\nFontes:\n- doc"
    rag.config = mock.Mock(top_k=3)
    weather = mock.Mock()
    weather.get_current_weather.return_value = {"current": {"temperature_c": 20.0}}
    weather.get_weather_forecast.return_value = WEATHER_DATA
    generate = mock.Mock(return_value="Resposta final.")
    pipeline = mock.Mock(wraps=ea.rag_pipeline)
    pipeline.retrieve = mock.Mock(return_value=[(DOC, 0.2)] if results is None else results)
    logs = []
    agent = ea.CoimbraExpertAgent(rag, planner, weather, generate=generate, pipeline=pipeline,
                                  today=lambda: TODAY, debug=logs.append)
    return agent, planner, rag, weather, generate, pipeline, logs


def prompt_text(generate):
    """The human message of the final generation (the system prompt names the sections itself)."""

    return generate.call_args.args[0][1].content


class RagRouteTests(unittest.TestCase):
    def test_rag_calls_the_d2_agent_unchanged_and_not_the_mcp(self):
        agent, _planner, rag, weather, generate, pipeline, _ = build(Plan("RAG", None, None))
        reply = agent.respond("Quem foi D. Dinis?")
        self.assertEqual(reply, "Resposta RAG.\n\nFontes:\n- doc")  # byte-for-byte the RAGAgent reply
        rag.respond.assert_called_once_with("Quem foi D. Dinis?")
        weather.get_current_weather.assert_not_called()
        weather.get_weather_forecast.assert_not_called()
        generate.assert_not_called()
        pipeline.retrieve.assert_not_called()


class WeatherRouteTests(unittest.TestCase):
    def test_weather_forecast_calls_mcp_and_no_retrieval(self):
        agent, _p, rag, weather, generate, pipeline, _ = build(Plan("WEATHER", None, FORECAST))
        reply = agent.respond("Vai chover amanhã?")
        weather.get_weather_forecast.assert_called_once_with("Coimbra, Portugal", 2)
        weather.get_current_weather.assert_not_called()
        pipeline.retrieve.assert_not_called()
        rag.respond.assert_not_called()
        text = prompt_text(generate)
        self.assertIn("[WEATHER DATA]", text)
        self.assertIn("Chuva fraca", text)
        self.assertNotIn("[RAG CONTEXT]", text)
        self.assertIn("2026-10-05", text)
        self.assertEqual(reply, f"Resposta final.\n\n{ea.WEATHER_SOURCE}")

    def test_weather_current_uses_the_current_tool(self):
        agent, _p, _r, weather, _g, _pl, _ = build(Plan("WEATHER", None, CURRENT))
        agent.respond("q")
        weather.get_current_weather.assert_called_once_with("Coimbra, Portugal")
        weather.get_weather_forecast.assert_not_called()


class ForecastLabelTests(unittest.TestCase):
    def test_days_are_labelled_without_changing_the_values(self):
        from prompts import label_forecast_days
        data = {"location": {"name": "Coimbra"}, "forecast": [
            {"date": "2026-10-05", "precipitation_sum_mm": 0.0},
            {"date": "2026-10-06", "precipitation_sum_mm": 4.3},
            {"date": "2026-10-07", "precipitation_sum_mm": 1.0}]}
        labelled = label_forecast_days(data, TODAY)
        self.assertEqual([d["day"] for d in labelled["forecast"]],
                         ["segunda-feira (hoje)", "terça-feira (amanhã)", "quarta-feira"])
        self.assertEqual([d["precipitation_sum_mm"] for d in labelled["forecast"]], [0.0, 4.3, 1.0])
        self.assertNotIn("day", data["forecast"][0])  # the tool result itself is not mutated

    def test_current_weather_is_passed_through(self):
        from prompts import label_forecast_days
        data = {"current": {"temperature_c": 20.0}}
        self.assertEqual(label_forecast_days(data, TODAY), data)


class BothRouteTests(unittest.TestCase):
    PLAN = Plan("BOTH", "O que é o Jardim Botânico de Coimbra?", FORECAST)

    def test_both_retrieves_calls_mcp_and_generates_once_with_both_contexts(self):
        agent, _p, rag, weather, generate, pipeline, _ = build(self.PLAN)
        reply = agent.respond("Vai chover amanhã e fala-me do Jardim Botânico.")
        pipeline.retrieve.assert_called_once_with(rag.store, "O que é o Jardim Botânico de Coimbra?", k=3)
        weather.get_weather_forecast.assert_called_once_with("Coimbra, Portugal", 2)
        rag.respond.assert_not_called()  # no complete RAG answer is generated first
        generate.assert_called_once()
        text = prompt_text(generate)
        self.assertIn("[WEATHER DATA]", text)
        self.assertIn("[RAG CONTEXT]", text)
        self.assertIn("O Jardim Botânico foi criado em 1772.", text)
        self.assertIn("Vai chover amanhã e fala-me do Jardim Botânico.", text)  # the original question
        self.assertLess(text.index("[WEATHER DATA]"), text.index("[RAG CONTEXT]"))
        self.assertIn("Fontes:\n- Jardim Botânico [jb]", reply)
        self.assertTrue(reply.endswith(ea.WEATHER_SOURCE))

    def test_empty_retrieval_does_not_invent_context(self):
        agent, _p, _r, _w, generate, _pl, _ = build(self.PLAN, results=[])
        reply = agent.respond("q")
        text = prompt_text(generate)
        self.assertIn("(nenhum contexto recuperado)", text)
        self.assertNotIn("Jardim Botânico foi criado", text)
        self.assertNotIn("Fontes:", reply)
        self.assertTrue(reply.endswith(ea.WEATHER_SOURCE))


class ErrorTests(unittest.TestCase):
    def test_mcp_error_is_a_controlled_error_and_nothing_is_generated(self):
        for plan in (Plan("WEATHER", None, FORECAST), Plan("BOTH", "q", FORECAST)):
            agent, _p, _r, weather, generate, _pl, _ = build(plan)
            weather.get_weather_forecast.side_effect = WeatherMCPError("Weather MCP tool x returned an error: boom")
            with self.assertRaisesRegex(ea.ExpertAgentError, "boom"):
                agent.respond("q")
            generate.assert_not_called()

    def test_invalid_planner_is_an_explicit_error_with_no_route_chosen(self):
        agent, _p, rag, weather, generate, pipeline, _ = build(planner_error=PlannerError("invalid twice"))
        with self.assertRaisesRegex(ea.ExpertAgentError, "invalid twice"):
            agent.respond("q")
        rag.respond.assert_not_called()
        weather.get_weather_forecast.assert_not_called()
        weather.get_current_weather.assert_not_called()
        pipeline.retrieve.assert_not_called()
        generate.assert_not_called()

    def test_planner_retry_budget_is_one(self):
        calls = []

        def llm(messages):
            calls.append(1)
            return "garbage"
        agent, *_ = build(Plan("RAG", None, None))
        agent.planner = Planner(llm, today=lambda: TODAY)
        with self.assertRaises(ea.ExpertAgentError):
            agent.respond("q")
        self.assertEqual(len(calls), 2)


class NoKeywordRoutingTests(unittest.TestCase):
    """The orchestration follows the planner's decision, never the words of the question."""

    def test_weather_plan_for_a_sentence_without_weather_words(self):
        agent, _p, rag, weather, _g, _pl, _ = build(Plan("WEATHER", None, CURRENT))
        agent.respond("Preciso de saber se levo casaco para a Alta.")
        weather.get_current_weather.assert_called_once()
        rag.respond.assert_not_called()

    def test_rag_plan_for_a_sentence_with_the_word_tempo(self):
        agent, _p, rag, weather, _g, _pl, _ = build(Plan("RAG", None, None))
        agent.respond("Quanto tempo demora a visita à Biblioteca Joanina?")
        rag.respond.assert_called_once()
        weather.get_current_weather.assert_not_called()
        weather.get_weather_forecast.assert_not_called()

    def test_source_has_no_keyword_lists_or_regex(self):
        for name in ("expert_agent.py", "planner.py"):
            source = (Path(__file__).resolve().parents[1] / name).read_text(encoding="utf-8")
            self.assertNotRegex(source, r"import re\b")
            self.assertNotRegex(source, r"(?i)\b(chover|chuva|tempo|amanh)")
            self.assertNotIn(" in question", source)


class DebugTests(unittest.TestCase):
    def test_debug_lines(self):
        agent, *_rest, logs = build(Plan("BOTH", "Jardim Botânico de Coimbra", FORECAST))
        agent.respond("q")
        text = "\n".join(logs)
        self.assertIn('[expert-plan]\nroute=BOTH\nrag_query="Jardim Botânico de Coimbra"\n'
                      'weather_tool=get_weather_forecast\nlocation="Coimbra, Portugal"\ndays=2', text)
        self.assertIn("[rag]\nretrieved=1 chunks", text)
        self.assertIn("[weather]\ntool=get_weather_forecast\nsuccess=true", text)

    def test_no_debug_callback_prints_nothing(self):
        agent, *_ = build(Plan("RAG", None, None))
        agent.debug = None
        with mock.patch("builtins.print") as printed:
            agent.respond("q")
        printed.assert_not_called()


class LoadTests(unittest.TestCase):
    def test_load_expert_starts_the_mcp_once_and_close_closes_it(self):
        with mock.patch.object(ea, "WeatherMCPClient") as client_cls:
            agent = ea.load_expert(mock.Mock(), debug=None)
        client_cls.return_value.start.assert_called_once_with()
        agent.close()
        client_cls.return_value.close.assert_called_once_with()

    def test_load_expert_propagates_startup_failure(self):
        with mock.patch.object(ea, "WeatherMCPClient") as client_cls:
            client_cls.return_value.start.side_effect = WeatherMCPError("cannot start")
            with self.assertRaisesRegex(WeatherMCPError, "cannot start"):
                ea.load_expert(mock.Mock())


if __name__ == "__main__":
    unittest.main()
