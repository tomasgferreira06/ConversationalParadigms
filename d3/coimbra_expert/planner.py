"""LLM planner: decides which capabilities (RAG / WEATHER / BOTH) a question needs.

The planner never answers the user; it produces a validated structured Plan. The
decision comes only from the LLM (llama3.2:3b with Ollama's native JSON-schema
output); nothing here inspects the question. Invalid output gets at most ONE retry,
then PlannerError: there is no silent fallback to any route.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Callable

from langchain_core.messages import BaseMessage

from prompts import PLAN_SCHEMA, planner_messages, planner_retry_messages

PLANNER_MODEL = "llama3.2:3b"
PLANNER_TEMPERATURE = 0.0

ROUTES = ("RAG", "WEATHER", "BOTH")
WEATHER_TOOLS = ("get_current_weather", "get_weather_forecast")
MIN_DAYS, MAX_DAYS = 1, 7


class PlanError(ValueError):
    """The planner output is not a valid plan; the message names the problem."""


class PlannerError(RuntimeError):
    """The planner could not produce a valid plan, even after one retry."""


@dataclass(frozen=True)
class WeatherRequest:
    tool: str
    location: str
    days: int | None  # only for get_weather_forecast


@dataclass(frozen=True)
class Plan:
    route: str
    rag_query: str | None  # BOTH only: the knowledge part of the question
    weather: WeatherRequest | None  # WEATHER and BOTH only


def _non_empty_str(value, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanError(f"{what} must be a non-empty string")
    return value.strip()


def _parse_weather(raw) -> WeatherRequest:
    if not isinstance(raw, dict):
        raise PlanError("weather is required for this route and must be an object")
    tool = raw.get("tool")
    if tool not in WEATHER_TOOLS:
        raise PlanError(f"weather.tool must be one of {list(WEATHER_TOOLS)}, got {tool!r}")
    location = _non_empty_str(raw.get("location"), "weather.location")
    days = raw.get("days")
    if tool == "get_current_weather":
        return WeatherRequest(tool, location, None)
    if isinstance(days, bool) or not isinstance(days, int) or not MIN_DAYS <= days <= MAX_DAYS:
        raise PlanError(f"weather.days must be an integer between {MIN_DAYS} and {MAX_DAYS} for a forecast, got {days!r}")
    return WeatherRequest(tool, location, days)


def parse_plan(text: str) -> Plan:
    """Validate the planner's JSON text; raises PlanError."""

    try:
        data = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise PlanError(f"not valid JSON ({exc})") from None
    if not isinstance(data, dict):
        raise PlanError("the plan must be a JSON object")
    route = data.get("route")
    if route not in ROUTES:
        raise PlanError(f"route must be one of {list(ROUTES)}, got {route!r}")
    if route == "RAG":
        return Plan("RAG", None, None)  # RAG-only answers the original question, as in D2
    weather = _parse_weather(data.get("weather"))
    if route == "WEATHER":
        return Plan("WEATHER", None, weather)
    return Plan("BOTH", _non_empty_str(data.get("rag_query"), "rag_query"), weather)


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
