"""LLM planner: decides which capabilities a question needs (RAG and/or MCP tool calls).

Instead of a fixed set of routes, the plan is generic: `use_rag` plus a list of MCP
`tool_calls` (at most one Weather call and one Places call). Any combination of the
three capabilities is therefore expressible without a combinatorial enum.

The planner never answers the user; it produces a validated structured Plan. The
decision comes only from the LLM (llama3.2:3b with Ollama's native JSON-schema
output); nothing here inspects the question. Invalid output gets at most ONE retry,
then PlannerError: there is no silent fallback to any capability.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from langchain_core.messages import BaseMessage

from prompts import PLAN_SCHEMA, planner_messages, planner_retry_messages

PLANNER_MODEL = "llama3.2:3b"
PLANNER_TEMPERATURE = 0.0

SERVER_TOOLS = {
    "weather": ("get_current_weather", "get_weather_forecast"),
    "places": ("search_place", "get_distance_between_places"),
}
MAX_TOOL_CALLS = 2  # at most one call per server
MIN_DAYS, MAX_DAYS = 1, 7

# tool -> (required arguments, optional arguments); anything else is rejected
TOOL_ARGUMENTS = {
    "get_current_weather": (("location",), ("days",)),  # `days` is tolerated (null) and dropped
    "get_weather_forecast": (("location", "days"), ()),
    "search_place": (("query",), ("country_code",)),
    "get_distance_between_places": (("origin", "destination"), ("country_code",)),
}


class PlanError(ValueError):
    """The planner output is not a valid plan; the message names the problem."""


class PlannerError(RuntimeError):
    """The planner could not produce a valid plan, even after one retry."""


@dataclass(frozen=True)
class ToolCall:
    server: str  # "weather" | "places"
    tool: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Plan:
    use_rag: bool
    rag_query: str | None  # the knowledge need; always set when use_rag and tool calls are combined
    tool_calls: tuple[ToolCall, ...]

    def call_for(self, server: str) -> ToolCall | None:
        return next((call for call in self.tool_calls if call.server == server), None)


def _non_empty_str(value, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanError(f"{what} must be a non-empty string")
    return value.strip()


def _country_code(value) -> str:
    if not isinstance(value, str) or len(value) != 2 or not value.isascii() or not value.isalpha():
        raise PlanError(f"country_code must be null or a two-letter code, got {value!r}")
    return value.lower()


def _parse_arguments(tool: str, raw) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PlanError(f"{tool}: arguments must be an object")
    args = {key: value for key, value in raw.items() if value is not None}  # null = not given
    required, optional = TOOL_ARGUMENTS[tool]
    unknown = sorted(set(args) - set(required) - set(optional))
    if unknown:
        raise PlanError(f"{tool}: unexpected arguments {unknown}")
    parsed: dict[str, Any] = {}
    for key in required:
        if key not in args:
            raise PlanError(f"{tool}: missing required argument '{key}'")
        if key == "days":
            days = args[key]
            if isinstance(days, bool) or not isinstance(days, int) or not MIN_DAYS <= days <= MAX_DAYS:
                raise PlanError(f"{tool}: days must be an integer between {MIN_DAYS} and {MAX_DAYS}, got {days!r}")
            parsed[key] = days
        else:
            parsed[key] = _non_empty_str(args[key], f"{tool}: {key}")
    if "country_code" in args:
        parsed["country_code"] = _country_code(args["country_code"])
    return parsed


def _parse_tool_call(raw) -> ToolCall:
    if not isinstance(raw, dict):
        raise PlanError("each tool call must be an object")
    server, tool = raw.get("server"), raw.get("tool")
    if server not in SERVER_TOOLS:
        raise PlanError(f"server must be one of {list(SERVER_TOOLS)}, got {server!r}")
    if tool not in SERVER_TOOLS[server]:
        raise PlanError(f"tool must be one of {list(SERVER_TOOLS[server])} for server {server!r}, got {tool!r}")
    return ToolCall(server, tool, _parse_arguments(tool, raw.get("arguments")))


def parse_plan(text: str) -> Plan:
    """Validate the planner's JSON text; raises PlanError."""

    try:
        data = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise PlanError(f"not valid JSON ({exc})") from None
    if not isinstance(data, dict):
        raise PlanError("the plan must be a JSON object")
    use_rag = data.get("use_rag")
    if not isinstance(use_rag, bool):
        raise PlanError(f"use_rag must be true or false, got {use_rag!r}")
    raw_calls = data.get("tool_calls")
    if not isinstance(raw_calls, list):
        raise PlanError("tool_calls must be a list (possibly empty)")
    if len(raw_calls) > MAX_TOOL_CALLS:
        raise PlanError(f"at most {MAX_TOOL_CALLS} tool calls are allowed, got {len(raw_calls)}")
    calls = tuple(_parse_tool_call(raw) for raw in raw_calls)
    servers = [call.server for call in calls]
    if len(set(servers)) != len(servers):
        raise PlanError("at most one tool call per server is allowed")
    if not use_rag and not calls:
        raise PlanError("the plan uses no capability (use_rag is false and tool_calls is empty)")
    rag_query = data.get("rag_query")
    if not use_rag:
        rag_query = None
    elif calls:
        rag_query = _non_empty_str(rag_query, "rag_query (required when RAG is combined with tool calls)")
    else:  # RAG-only: the original question is answered by the D2 pipeline, the query is informative
        rag_query = rag_query.strip() if isinstance(rag_query, str) and rag_query.strip() else None
    return Plan(use_rag, rag_query, calls)


def ollama_planner_llm(messages: list[BaseMessage]) -> str:
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model=PLANNER_MODEL, temperature=PLANNER_TEMPERATURE, format=PLAN_SCHEMA)
    return llm.invoke(messages).content


class Planner:
    def __init__(self, llm: Callable[[list[BaseMessage]], str] = ollama_planner_llm,
                 today: Callable[[], date] = date.today):
        self.llm = llm
        self.today = today

    def plan(self, question: str) -> Plan:
        today = self.today()
        first = self.llm(planner_messages(question, today))
        try:
            return parse_plan(first)
        except PlanError as problem:
            retry = self.llm(planner_retry_messages(question, today, first, str(problem)))
            try:
                return parse_plan(retry)
            except PlanError as second:
                raise PlannerError(
                    f"The planner returned an invalid plan twice (first: {problem}; second: {second})."
                ) from None
