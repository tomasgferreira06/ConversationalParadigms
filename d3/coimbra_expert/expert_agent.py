"""Coimbra Expert Agent: LLM planner -> RAG / WEATHER / BOTH -> final answer.

    question -> Planner (LLM) -> RAG     : the D2 RAGAgent.respond(question), unchanged
                              -> WEATHER : Weather MCP tool -> final generation
                              -> BOTH    : RAG retrieval + Weather MCP tool -> ONE final generation

The route is whatever the planner returns; nothing here looks at the question text.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (REPO_ROOT / "d2_rag" / "scripts", Path(__file__).resolve().parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import rag_pipeline  # noqa: E402
from planner import Plan, Planner, PlannerError  # noqa: E402
from prompts import final_messages  # noqa: E402
from weather_mcp_client import WeatherMCPClient, WeatherMCPError  # noqa: E402

WEATHER_SOURCE = "Fonte meteorológica: Open-Meteo via Weather MCP"


class ExpertAgentError(RuntimeError):
    """A step of the expert agent failed; the message is meant to be shown to the user."""


class CoimbraExpertAgent:
    def __init__(self, rag, planner: Planner, weather: WeatherMCPClient,
                 generate: Callable | None = None, pipeline=rag_pipeline,
                 today: Callable[[], date] = date.today, debug: Callable[[str], None] | None = None):
        self.rag = rag  # D2 RAGAgent: .respond(question), .store, .config
        self.planner = planner
        self.weather = weather
        self.pipeline = pipeline
        self.generate = generate or (lambda messages: pipeline.generate(messages, rag.config))
        self.today = today
        self.debug = debug

    def close(self) -> None:
        self.weather.close()

    def _log(self, text: str) -> None:
        if self.debug:
            self.debug(text)

    def respond(self, question: str) -> str:
        try:
            plan = self.planner.plan(question)
        except PlannerError as exc:
            raise ExpertAgentError(str(exc)) from exc
        self._log_plan(plan)
        if plan.route == "RAG":
            return self.rag.respond(question)  # exactly the D2 behaviour, sources included
        weather_data = self._call_weather(plan)
        rag_context, results = None, []
        if plan.route == "BOTH":
            results = self.pipeline.retrieve(self.rag.store, plan.rag_query, k=self.rag.config.top_k)
            self._log(f"[rag]\nretrieved={len(results)} chunks")
            rag_context = self._rag_context(results)
        answer = self.generate(final_messages(question, self.today(), weather_data, rag_context))
        parts = [answer]
        if results:
            parts.append(f"Fontes:\n{self.pipeline.format_sources(results)}")
        parts.append(WEATHER_SOURCE)
        return "\n\n".join(parts)

    def _rag_context(self, results) -> str:
        context = self.pipeline.build_context(results)
        note = self.pipeline.conflict_note(results)
        return f"{context}\n\n{note}" if note else context

    def _call_weather(self, plan: Plan) -> dict:
        request = plan.weather
        try:
            if request.tool == "get_current_weather":
                data = self.weather.get_current_weather(request.location)
            else:
                data = self.weather.get_weather_forecast(request.location, request.days)
        except WeatherMCPError as exc:
            self._log(f"[weather]\ntool={request.tool}\nsuccess=false")
            raise ExpertAgentError(str(exc)) from exc
        self._log(f"[weather]\ntool={request.tool}\nsuccess=true")
        return data

    def _log_plan(self, plan: Plan) -> None:
        lines = ["[expert-plan]", f"route={plan.route}"]
        if plan.rag_query:
            lines.append(f'rag_query="{plan.rag_query}"')
        if plan.weather:
            lines += [f"weather_tool={plan.weather.tool}", f'location="{plan.weather.location}"']
            if plan.weather.days is not None:
                lines.append(f"days={plan.weather.days}")
        self._log("\n".join(lines))


def load_expert(rag, debug: Callable[[str], None] | None = None) -> CoimbraExpertAgent:
    """Start the Weather MCP (one session for the whole run) and build the agent.

    Raises WeatherMCPError if the server does not start or lacks a required tool.
    """

    weather = WeatherMCPClient()
    weather.start()
    return CoimbraExpertAgent(rag, Planner(), weather, debug=debug)
