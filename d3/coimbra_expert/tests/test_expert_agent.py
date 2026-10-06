"""Coimbra Expert Agent orchestration with mocks (no Ollama, Open-Meteo, Nominatim, Chroma or MCP process)."""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import expert_agent as ea  # noqa: E402
import prompts  # noqa: E402
from mcp_stdio_client import MCPClientError  # noqa: E402
from places_mcp_client import PlacesMCPError  # noqa: E402
from planner import Plan, Planner, PlannerError, ToolCall  # noqa: E402
from weather_mcp_client import WeatherMCPError  # noqa: E402

TODAY = date(2026, 10, 5)
W_CURRENT = ToolCall("weather", "get_current_weather", {"location": "Coimbra, Portugal"})
W_FORECAST = ToolCall("weather", "get_weather_forecast", {"location": "Coimbra, Portugal", "days": 2})
P_SEARCH = ToolCall("places", "search_place", {"query": "Sé Velha, Coimbra", "country_code": "pt"})
P_DISTANCE = ToolCall("places", "get_distance_between_places",
                      {"origin": "A, Coimbra", "destination": "B, Coimbra", "country_code": "pt"})
WEATHER_DATA = {"location": {"name": "Coimbra"}, "forecast": [{"date": "2026-10-06", "weather_description": "Chuva fraca"}]}
PLACES_DATA = {"query": "Sé Velha, Coimbra", "results": [{"display_name": "Sé Velha, Coimbra, Portugal",
                                                          "latitude": 40.2, "longitude": -8.4}],
               "attribution": "© OpenStreetMap contributors (data and geocoding via Nominatim)"}
DOC = Document(page_content="A Sé Velha é uma catedral românica do século XII.", metadata={
    "title": "Sé Velha", "document_id": "se", "source_type": "web", "canonical_url": "https://x/se",
    "section_path": ["História"]})


def rag_plan(*calls, query="O que é a Sé Velha de Coimbra?"):
    return Plan(True, query, tuple(calls))


def tools_plan(*calls):
    return Plan(False, None, tuple(calls))


def build(plan=None, planner_error=None, results=None):
    planner = mock.Mock()
    if planner_error:
        planner.plan.side_effect = planner_error
    else:
        planner.plan.return_value = plan
    rag = mock.Mock()
    rag.respond.return_value = "Resposta RAG.\n\nFontes:\n- doc"
    rag.config = mock.Mock(top_k=3)
    weather, places = mock.Mock(), mock.Mock()
    weather.call_tool.return_value = WEATHER_DATA
    places.call_tool.return_value = PLACES_DATA
    generate = mock.Mock(return_value="Resposta final.")
    pipeline = mock.Mock(wraps=ea.rag_pipeline)
    pipeline.retrieve = mock.Mock(return_value=[(DOC, 0.2)] if results is None else results)
    logs = []
    agent = ea.CoimbraExpertAgent(rag, planner, {"weather": weather, "places": places}, generate=generate,
                                  pipeline=pipeline, today=lambda: TODAY, debug=logs.append)
    return agent, rag, weather, places, generate, pipeline, logs


def human(generate):
    """The human message of the final generation (the system prompt names the sections itself)."""

    return generate.call_args.args[0][1].content


def used(text, title):
    """Content of a final-prompt block, or None when it is marked as not used."""

    body = text.split(f"[{title}]\n", 1)[1].split("\n\n[", 1)[0].split("\n\nResponde apenas", 1)[0]
    return None if body == prompts.NOT_USED else body


class SingleCapabilityTests(unittest.TestCase):
    def test_A_rag_only_calls_the_d2_agent_unchanged_and_no_mcp(self):
        agent, rag, weather, places, generate, pipeline, _ = build(rag_plan())
        reply = agent.respond("Quem foi D. Dinis?")
        self.assertEqual(reply, "Resposta RAG.\n\nFontes:\n- doc")  # byte-for-byte the RAGAgent reply
        rag.respond.assert_called_once_with("Quem foi D. Dinis?")
        weather.call_tool.assert_not_called()
        places.call_tool.assert_not_called()
        generate.assert_not_called()  # no additional D3 generation
        pipeline.retrieve.assert_not_called()

    def test_B_weather_only(self):
        agent, rag, weather, places, generate, pipeline, _ = build(tools_plan(W_FORECAST))
        reply = agent.respond("q")
        weather.call_tool.assert_called_once_with("get_weather_forecast", {"location": "Coimbra, Portugal", "days": 2})
        places.call_tool.assert_not_called()
        pipeline.retrieve.assert_not_called()
        rag.respond.assert_not_called()
        text = human(generate)
        self.assertIn("Chuva fraca", used(text, "WEATHER DATA"))
        self.assertIsNone(used(text, "RAG CONTEXT"))
        self.assertIsNone(used(text, "PLACES DATA"))
        self.assertEqual(reply, f"Resposta final.\n\n{ea.WEATHER_SOURCE}")

    def test_C_places_only(self):
        agent, rag, weather, places, generate, pipeline, _ = build(tools_plan(P_SEARCH))
        reply = agent.respond("q")
        places.call_tool.assert_called_once_with("search_place", {"query": "Sé Velha, Coimbra", "country_code": "pt"})
        weather.call_tool.assert_not_called()
        pipeline.retrieve.assert_not_called()
        rag.respond.assert_not_called()
        text = human(generate)
        self.assertIn("Sé Velha, Coimbra, Portugal", used(text, "PLACES DATA"))
        self.assertIsNone(used(text, "WEATHER DATA"))
        self.assertIsNone(used(text, "RAG CONTEXT"))
        self.assertEqual(reply, "Resposta final.\n\nFonte geográfica: "
                                "© OpenStreetMap contributors (data and geocoding via Nominatim) via Places MCP")

    def test_places_distance_is_just_another_planned_call(self):
        agent, _r, _w, places, _g, _p, _ = build(tools_plan(P_DISTANCE))
        agent.respond("q")
        places.call_tool.assert_called_once_with("get_distance_between_places", P_DISTANCE.arguments)


class CompositionTests(unittest.TestCase):
    def test_D_rag_plus_weather(self):
        agent, rag, weather, places, generate, pipeline, _ = build(rag_plan(W_FORECAST))
        reply = agent.respond("Vai chover amanhã e fala-me da Sé.")
        pipeline.retrieve.assert_called_once_with(rag.store, "O que é a Sé Velha de Coimbra?", k=3)
        weather.call_tool.assert_called_once()
        places.call_tool.assert_not_called()
        rag.respond.assert_not_called()  # no complete RAG answer is generated first
        generate.assert_called_once()
        text = human(generate)
        self.assertIn("catedral românica", used(text, "RAG CONTEXT"))
        self.assertIsNotNone(used(text, "WEATHER DATA"))
        self.assertIsNone(used(text, "PLACES DATA"))
        self.assertIn("Vai chover amanhã e fala-me da Sé.", used(text, "USER QUESTION"))  # the original question
        self.assertIn("Fontes:\n- Sé Velha [se]", reply)
        self.assertTrue(reply.endswith(ea.WEATHER_SOURCE))

    def test_E_rag_plus_places(self):
        agent, rag, weather, places, generate, pipeline, _ = build(rag_plan(P_SEARCH))
        reply = agent.respond("q")
        pipeline.retrieve.assert_called_once()
        places.call_tool.assert_called_once()
        weather.call_tool.assert_not_called()
        text = human(generate)
        self.assertIsNotNone(used(text, "RAG CONTEXT"))
        self.assertIsNotNone(used(text, "PLACES DATA"))
        self.assertIsNone(used(text, "WEATHER DATA"))
        self.assertIn("Fontes:\n- Sé Velha [se]", reply)
        self.assertIn("Fonte geográfica:", reply)
        self.assertNotIn(ea.WEATHER_SOURCE, reply)

    def test_F_weather_plus_places_without_retrieval(self):
        agent, rag, weather, places, generate, pipeline, _ = build(tools_plan(W_CURRENT, P_SEARCH))
        reply = agent.respond("q")
        weather.call_tool.assert_called_once()
        places.call_tool.assert_called_once()
        pipeline.retrieve.assert_not_called()
        rag.respond.assert_not_called()
        text = human(generate)
        self.assertIsNone(used(text, "RAG CONTEXT"))
        self.assertIsNotNone(used(text, "WEATHER DATA"))
        self.assertIsNotNone(used(text, "PLACES DATA"))
        self.assertNotIn("Fontes:", reply)
        self.assertTrue(reply.index(ea.WEATHER_SOURCE) < reply.index("Fonte geográfica:"))

    def test_G_rag_plus_weather_plus_places_with_one_final_generation(self):
        agent, rag, weather, places, generate, pipeline, _ = build(rag_plan(W_FORECAST, P_SEARCH))
        reply = agent.respond("q")
        pipeline.retrieve.assert_called_once()
        weather.call_tool.assert_called_once()
        places.call_tool.assert_called_once()
        rag.respond.assert_not_called()
        generate.assert_called_once()  # a single final generation
        text = human(generate)
        for title in ("RAG CONTEXT", "WEATHER DATA", "PLACES DATA"):
            self.assertIsNotNone(used(text, title), title)
        self.assertLess(text.index("[RAG CONTEXT]"), text.index("[WEATHER DATA]"))
        self.assertLess(text.index("[WEATHER DATA]"), text.index("[PLACES DATA]"))
        self.assertIn("Fontes:\n- Sé Velha [se]", reply)
        self.assertIn(ea.WEATHER_SOURCE, reply)
        self.assertIn("Fonte geográfica:", reply)

    def test_J_empty_retrieval_does_not_invent_context(self):
        for tool in (W_FORECAST, P_SEARCH):
            agent, _r, _w, _p, generate, _pl, _ = build(rag_plan(tool), results=[])
            reply = agent.respond("q")
            rag_block = used(human(generate), "RAG CONTEXT")
            self.assertEqual(rag_block, "(nenhum contexto recuperado)")
            self.assertNotIn("catedral românica", human(generate))
            self.assertNotIn("Fontes:", reply)

    def test_tool_calls_run_in_plan_order_and_each_server_once(self):
        agent, _r, weather, places, _g, _p, logs = build(tools_plan(P_SEARCH, W_CURRENT))
        order = []
        places.call_tool.side_effect = lambda *a: order.append("places") or PLACES_DATA
        weather.call_tool.side_effect = lambda *a: order.append("weather") or WEATHER_DATA
        agent.respond("q")
        self.assertEqual(order, ["places", "weather"])


class ErrorTests(unittest.TestCase):
    def test_H_weather_error_is_controlled(self):
        for plan in (tools_plan(W_FORECAST), rag_plan(W_FORECAST), tools_plan(W_CURRENT, P_SEARCH)):
            agent, _r, weather, _p, generate, _pl, logs = build(plan)
            weather.call_tool.side_effect = WeatherMCPError("Weather MCP tool x returned an error: boom")
            with self.assertRaisesRegex(ea.ExpertAgentError, "boom"):
                agent.respond("q")
            generate.assert_not_called()
            self.assertIn("[weather]\nsuccess=false", "\n".join(logs))

    def test_I_places_error_is_controlled(self):
        for plan in (tools_plan(P_SEARCH), rag_plan(P_DISTANCE), tools_plan(W_CURRENT, P_SEARCH)):
            agent, _r, _w, places, generate, _pl, logs = build(plan)
            places.call_tool.side_effect = PlacesMCPError("Places MCP tool x returned an error: Local não encontrado")
            with self.assertRaisesRegex(ea.ExpertAgentError, "Local não encontrado"):
                agent.respond("q")
            generate.assert_not_called()
            self.assertIn("[places]\nsuccess=false", "\n".join(logs))

    def test_failed_tool_stops_before_retrieval(self):
        agent, _r, weather, _p, _g, pipeline, _ = build(rag_plan(W_FORECAST))
        weather.call_tool.side_effect = WeatherMCPError("boom")
        with self.assertRaises(ea.ExpertAgentError):
            agent.respond("q")
        pipeline.retrieve.assert_not_called()

    def test_invalid_planner_is_an_explicit_error_with_no_capability_chosen(self):
        agent, rag, weather, places, generate, pipeline, _ = build(planner_error=PlannerError("invalid twice"))
        with self.assertRaisesRegex(ea.ExpertAgentError, "invalid twice"):
            agent.respond("q")
        for untouched in (rag.respond, weather.call_tool, places.call_tool, pipeline.retrieve, generate):
            untouched.assert_not_called()

    def test_planner_retry_budget_is_one(self):
        calls = []

        def llm(messages):
            calls.append(1)
            return "garbage"
        agent, *_ = build(rag_plan())
        agent.planner = Planner(llm, today=lambda: TODAY)
        with self.assertRaises(ea.ExpertAgentError):
            agent.respond("q")
        self.assertEqual(len(calls), 2)


class NoKeywordRoutingTests(unittest.TestCase):
    """The orchestration follows the planner's plan exactly, never the words of the question."""

    def test_places_plan_for_a_sentence_without_location_words(self):
        agent, rag, weather, places, _g, _pl, _ = build(tools_plan(P_SEARCH))
        agent.respond("Preciso de conhecer melhor aquele monumento românico.")
        places.call_tool.assert_called_once()
        weather.call_tool.assert_not_called()
        rag.respond.assert_not_called()

    def test_rag_plan_for_a_sentence_with_the_word_tempo(self):
        agent, rag, weather, places, _g, _pl, _ = build(rag_plan())
        agent.respond("Quanto tempo demora a visita à Biblioteca Joanina?")
        rag.respond.assert_called_once()
        weather.call_tool.assert_not_called()
        places.call_tool.assert_not_called()

    def test_weather_plus_places_plan_for_a_sentence_without_either_kind_of_word(self):
        agent, rag, weather, places, _g, pipeline, _ = build(tools_plan(W_FORECAST, P_SEARCH))
        agent.respond("Vou almoçar com a minha avó.")
        weather.call_tool.assert_called_once()
        places.call_tool.assert_called_once()
        rag.respond.assert_not_called()
        pipeline.retrieve.assert_not_called()

    def test_source_has_no_keyword_lists_or_regex(self):
        for name in ("expert_agent.py", "planner.py", "places_mcp_client.py", "weather_mcp_client.py",
                     "mcp_stdio_client.py"):
            source = (Path(__file__).resolve().parents[1] / name).read_text(encoding="utf-8")
            self.assertNotRegex(source, r"import re\b")
            self.assertNotRegex(source, r"(?i)\b(chover|chuva|tempo|amanh|onde fica|dist[âa]ncia|localiza)")
            self.assertNotIn(" in question", source)


class FinalPromptTests(unittest.TestCase):
    def messages(self, **kwargs):
        return prompts.final_messages("Pergunta?", TODAY, **kwargs)

    def test_blocks_are_organised_and_unused_ones_are_marked(self):
        text = self.messages(places_data=PLACES_DATA)[1].content
        for title in ("USER QUESTION", "RAG CONTEXT", "WEATHER DATA", "PLACES DATA"):
            self.assertIn(f"[{title}]", text)
        self.assertEqual(used(text, "USER QUESTION"), "Pergunta?")
        self.assertIsNone(used(text, "RAG CONTEXT"))
        self.assertIsNone(used(text, "WEATHER DATA"))
        self.assertIsNotNone(used(text, "PLACES DATA"))

    def test_system_prompt_has_the_geodesic_and_ambiguity_rules(self):
        system = self.messages()[0].content
        self.assertIn("linha reta", system)
        self.assertIn("nunca como distância a pé, de carro, percurso ou tempo de viagem", system)
        self.assertIn("candidates_found", system)
        self.assertIn("vários candidatos", system)
        self.assertIn("não substituas nem inventes coordenadas", system)

    def test_forecast_days_are_labelled_without_changing_the_values(self):
        data = {"location": {"name": "Coimbra"}, "forecast": [
            {"date": "2026-10-05", "precipitation_sum_mm": 0.0},
            {"date": "2026-10-06", "precipitation_sum_mm": 4.3},
            {"date": "2026-10-07", "precipitation_sum_mm": 1.0}]}
        labelled = prompts.label_forecast_days(data, TODAY)
        self.assertEqual([d["day"] for d in labelled["forecast"]],
                         ["segunda-feira (hoje)", "terça-feira (amanhã)", "quarta-feira"])
        self.assertEqual([d["precipitation_sum_mm"] for d in labelled["forecast"]], [0.0, 4.3, 1.0])
        self.assertNotIn("day", data["forecast"][0])  # the tool result itself is not mutated

    def test_current_weather_is_passed_through(self):
        data = {"current": {"temperature_c": 20.0}}
        self.assertEqual(prompts.label_forecast_days(data, TODAY), data)


class DebugTests(unittest.TestCase):
    def test_debug_lines_for_a_composed_plan(self):
        agent, *_rest, logs = build(rag_plan(W_FORECAST, P_SEARCH, query="História da Sé Velha"))
        agent.respond("q")
        text = "\n".join(logs)
        self.assertIn('[expert-plan]\nuse_rag=true\nrag_query="História da Sé Velha"\ntool_calls=2', text)
        self.assertIn('[tool-call 1]\nserver=weather\ntool=get_weather_forecast\n'
                      'arguments={"location":"Coimbra, Portugal","days":2}', text)
        self.assertIn('[tool-call 2]\nserver=places\ntool=search_place\n'
                      'arguments={"query":"Sé Velha, Coimbra","country_code":"pt"}', text)
        for line in ("[weather]\nsuccess=true", "[places]\nsuccess=true", "[rag]\nretrieved=1 chunks"):
            self.assertIn(line, text)
        self.assertLess(text.index("[expert-plan]"), text.index("[tool-call 1]"))
        self.assertLess(text.index("[tool-call 2]"), text.index("[weather]\nsuccess"))

    def test_debug_never_prints_prompts_or_reasoning(self):
        agent, *_rest, logs = build(rag_plan(W_FORECAST))
        agent.respond("q")
        text = "\n".join(logs)
        self.assertNotIn("planner of a Coimbra", text)
        self.assertNotIn("assistente de turismo", text)

    def test_no_debug_callback_prints_nothing(self):
        agent, *_ = build(rag_plan())
        agent.debug = None
        with mock.patch("builtins.print") as printed:
            agent.respond("q")
        printed.assert_not_called()


class LifecycleTests(unittest.TestCase):
    def test_load_expert_starts_both_servers_once_and_close_closes_both(self):
        with mock.patch.object(ea, "WeatherMCPClient") as weather_cls, mock.patch.object(ea, "PlacesMCPClient") as places_cls:
            agent = ea.load_expert(mock.Mock(), debug=None)
        weather_cls.return_value.start.assert_called_once_with()
        places_cls.return_value.start.assert_called_once_with()
        self.assertEqual(set(agent.clients), {"weather", "places"})
        agent.close()
        weather_cls.return_value.close.assert_called_once_with()
        places_cls.return_value.close.assert_called_once_with()

    def test_weather_startup_failure_propagates_and_places_is_never_started(self):
        with mock.patch.object(ea, "WeatherMCPClient") as weather_cls, mock.patch.object(ea, "PlacesMCPClient") as places_cls:
            weather_cls.return_value.start.side_effect = WeatherMCPError("cannot start weather")
            with self.assertRaisesRegex(MCPClientError, "cannot start weather"):
                ea.load_expert(mock.Mock())
        places_cls.return_value.start.assert_not_called()

    def test_places_startup_failure_closes_the_weather_server_again(self):
        with mock.patch.object(ea, "WeatherMCPClient") as weather_cls, mock.patch.object(ea, "PlacesMCPClient") as places_cls:
            places_cls.return_value.start.side_effect = PlacesMCPError("cannot start places")
            with self.assertRaisesRegex(PlacesMCPError, "cannot start places"):
                ea.load_expert(mock.Mock())
        weather_cls.return_value.close.assert_called_once_with()

    def test_close_closes_every_session_even_if_one_fails(self):
        agent, _r, weather, places, *_ = build(rag_plan())
        weather.close.side_effect = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            agent.close()
        places.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
