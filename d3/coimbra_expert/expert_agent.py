"""Coimbra Expert Agent: LLM planner -> RAG and/or MCP tools (Weather, Places) -> final answer.

    question -> Planner (LLM) -> use_rag only        : the D2 RAGAgent.respond(question), unchanged
                              -> any tool call(s)    : the planned MCP calls (+ RAG retrieval if use_rag)
                                                       -> ONE final generation with a block per capability

The plan decides everything (nothing here looks at the question text): Python only validates
(planner.py) and executes it. There is one long-lived MCP session per server for the whole run.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (REPO_ROOT / "d2_rag" / "scripts", Path(__file__).resolve().parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import rag_pipeline  # noqa: E402
from mcp_stdio_client import MCPClientError  # noqa: E402
from places_mcp_client import PlacesMCPClient, PlacesMCPError  # noqa: E402
from planner import Plan, Planner, PlannerError  # noqa: E402
from prompts import final_messages  # noqa: E402
from weather_mcp_client import WeatherMCPClient, WeatherMCPError  # noqa: E402

WEATHER_SOURCE = "Fonte meteorológica: Open-Meteo via Weather MCP"
PLACES_SOURCE_PREFIX = "Fonte geográfica: "
PLACES_ATTRIBUTION = "© OpenStreetMap contributors (data and geocoding via Nominatim)"


class ExpertAgentError(RuntimeError):
    """A step of the expert agent failed; the message is meant to be shown to the user."""


class CoimbraExpertAgent:
    def __init__(self, rag, planner: Planner, clients: dict, generate: Callable | None = None,
                 pipeline=rag_pipeline, today: Callable[[], date] = date.today,
                 debug: Callable[[str], None] | None = None):
        self.rag = rag  # D2 RAGAgent: .respond(question), .store, .config
        self.planner = planner
        self.clients = clients  # server name ("weather", "places") -> started MCP client
        self.pipeline = pipeline
        self.generate = generate or (lambda messages: pipeline.generate(messages, rag.config))
        self.today = today
        self.debug = debug

    def close(self) -> None:
        """Close every MCP session, even if one of them fails to close."""

        errors = []
        for client in self.clients.values():
            try:
                client.close()
            except Exception as exc:  # keep closing the others
                errors.append(exc)
        if errors:
            raise errors[0]

    def _log(self, text: str) -> None:
        if self.debug:
            self.debug(text)

    def respond(self, question: str) -> str:
        try:
            plan = self.planner.plan(question)
        except PlannerError as exc:
            raise ExpertAgentError(str(exc)) from exc
        self._log_plan(plan)
        if plan.use_rag and not plan.tool_calls:
            return self.rag.respond(question)  # exactly the D2 behaviour, sources included
        tool_data = self._run_tool_calls(plan)
        rag_context, results = None, []
        if plan.use_rag:
            results = self.pipeline.retrieve(self.rag.store, plan.rag_query, k=self.rag.config.top_k)
            self._log(f"[rag]\nretrieved={len(results)} chunks")
            rag_context = self._rag_context(results)
        messages = final_messages(question, self.today(), rag_context,
                                  weather_data=tool_data.get("weather"), places_data=tool_data.get("places"))
        parts = [self.generate(messages)]
        if results:
            parts.append(f"Fontes:\n{self.pipeline.format_sources(results)}")
        if "weather" in tool_data:
            parts.append(WEATHER_SOURCE)
        if "places" in tool_data:
            attribution = tool_data["places"].get("attribution") or PLACES_ATTRIBUTION
            parts.append(f"{PLACES_SOURCE_PREFIX}{attribution} via Places MCP")
        return "\n\n".join(parts)

    def _rag_context(self, results) -> str:
        context = self.pipeline.build_context(results)
        note = self.pipeline.conflict_note(results)
        return f"{context}\n\n{note}" if note else context

    def _run_tool_calls(self, plan: Plan) -> dict[str, dict]:
        """Execute the planned MCP calls in order; the first failure is a controlled error."""

        data: dict[str, dict] = {}
        for call in plan.tool_calls:
            try:
                data[call.server] = self.clients[call.server].call_tool(call.tool, call.arguments)
            except MCPClientError as exc:
                self._log(f"[{call.server}]\nsuccess=false")
                raise ExpertAgentError(str(exc)) from exc
            self._log(f"[{call.server}]\nsuccess=true")
        return data

    def _log_plan(self, plan: Plan) -> None:
        lines = ["[expert-plan]", f"use_rag={str(plan.use_rag).lower()}"]
        if plan.rag_query:
            lines.append(f'rag_query="{plan.rag_query}"')
        lines.append(f"tool_calls={len(plan.tool_calls)}")
        for number, call in enumerate(plan.tool_calls, start=1):
            arguments = json.dumps(call.arguments, ensure_ascii=False, separators=(",", ":"))
            lines += ["", f"[tool-call {number}]", f"server={call.server}", f"tool={call.tool}", f"arguments={arguments}"]
        self._log("\n".join(lines))


def load_expert(rag, debug: Callable[[str], None] | None = None) -> CoimbraExpertAgent:
    """Start the Weather and Places MCP servers (one session each for the whole run) and build the agent.

    Raises MCPClientError (WeatherMCPError / PlacesMCPError) if a server does not start or lacks a
    required tool; a server already started is closed again.
    """

    weather = WeatherMCPClient()
    weather.start()
    places = PlacesMCPClient()
    try:
        places.start()
    except BaseException:
        weather.close()
        raise
    return CoimbraExpertAgent(rag, Planner(), {"weather": weather, "places": places}, debug=debug)
