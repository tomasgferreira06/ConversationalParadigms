"""D3 prompts: the planner (decides the capabilities needed) and the final generation.

No routing rules live in Python: what the question needs is decided by the LLM from
these descriptions. The planner examples are illustrative only (other places and
phrasings than any evaluation or smoke question).
"""

from __future__ import annotations

import json
from datetime import date

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

WEEKDAYS_PT = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "route": {"type": "string", "enum": ["RAG", "WEATHER", "BOTH"]},
        "rag_query": {"type": ["string", "null"]},
        "weather": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "enum": ["get_current_weather", "get_weather_forecast"]},
                        "location": {"type": "string"},
                        "days": {"type": ["integer", "null"]},
                    },
                    "required": ["tool", "location", "days"],
                },
            ]
        },
    },
    "required": ["route", "rag_query", "weather"],
}

PLANNER_SYSTEM = """\
You are the planner of a Coimbra (Portugal) tourism assistant. You never answer the user.
You only decide which capabilities are needed to answer the question and output ONE JSON object.

Capabilities:
- RAG: a fixed knowledge base about Coimbra (history, heritage, monuments, museums, gardens, culture, gastronomy, practical tourist information). It knows nothing about the weather.
- WEATHER: live weather data for a place, through two tools:
  - get_current_weather(location): conditions right now.
  - get_weather_forecast(location, days): daily forecast, 1 to 7 days, where day 1 is today.

Routes:
- "RAG": the question only needs the fixed knowledge base.
- "WEATHER": the question only needs current or future weather.
- "BOTH": the question needs weather AND knowledge from the knowledge base (including questions that depend on the weather, such as what to visit if it rains).

Output format (JSON only, no explanations, no reasoning):
{"route": "RAG" | "WEATHER" | "BOTH",
 "rag_query": string | null,
 "weather": {"tool": "get_current_weather" | "get_weather_forecast", "location": string, "days": integer | null} | null}

Rules:
- RAG: rag_query = the question; weather = null.
- WEATHER: rag_query = null; weather is required.
- BOTH: rag_query is required and rewrites ONLY the knowledge part of the question as a short, self-contained question in Portuguese (never answer it, never mention weather in it); weather is required.
- location: the place in the form "City, Country" (for Coimbra: "Coimbra, Portugal").
- Weather right now -> get_current_weather, with days = null.
- Weather in the future -> get_weather_forecast. days must be enough to include the requested date, counting today as day 1 (tomorrow needs at least 2), between 1 and 7. For vague "next days" use 3.
- Use the current date below to interpret relative dates.

Examples (illustrative):
Question: Qual é a história da Sé Velha?
{"route": "RAG", "rag_query": "Qual é a história da Sé Velha de Coimbra?", "weather": null}
Question: Está frio agora no Porto?
{"route": "WEATHER", "rag_query": null, "weather": {"tool": "get_current_weather", "location": "Porto, Portugal", "days": null}}
Question: Vai estar sol no sábado em Coimbra?
{"route": "WEATHER", "rag_query": null, "weather": {"tool": "get_weather_forecast", "location": "Coimbra, Portugal", "days": 7}}
Question: Como estará o tempo amanhã em Coimbra e o que é o Museu Machado de Castro?
{"route": "BOTH", "rag_query": "O que é o Museu Machado de Castro?", "weather": {"tool": "get_weather_forecast", "location": "Coimbra, Portugal", "days": 2}}"""

PLANNER_RETRY = "Return a valid object matching this schema.\n{schema}\nProblem with the previous output: {problem}"

FINAL_SYSTEM = """\
És o assistente de turismo de Coimbra. Respondes em Português de Portugal, de forma clara e relativamente concisa.
Usa apenas os dados fornecidos nas secções abaixo; não uses conhecimento externo e não inventes informação.
- [WEATHER DATA] são dados meteorológicos reais (Open-Meteo). Nas previsões, a primeira entrada é o dia de hoje. Responde sobre meteorologia apenas com estes dados.
- [RAG CONTEXT] é conhecimento turístico recuperado do corpus. Responde sobre locais, história e cultura apenas com este contexto.
- Cada dia da previsão traz o campo "day" (dia da semana, "hoje" ou "amanhã"): usa-o para identificar os dias. Para perguntas sobre chuva, baseia-te na precipitação (mm), na probabilidade máxima de precipitação e na descrição do tempo, e não contradigas estes números.
- Se os dados não permitirem responder a alguma parte da pergunta, diz isso explicitamente.
- Quando houver as duas secções, integra-as numa única resposta natural, distinguindo o que é meteorologia do que é informação turística. Não inventes relações entre elas.
- Só podes recomendar locais que constem do [RAG CONTEXT]. Não assumas que um local é interior, coberto ou adequado à chuva, a menos que o contexto o diga; se não disser, indica que o corpus não confirma essa característica.
- Não inventes fontes."""


def describe_today(today: date) -> str:
    return f"{WEEKDAYS_PT[today.weekday()]}, {today.isoformat()}"


def planner_messages(question: str, today: date) -> list[BaseMessage]:
    system = f"{PLANNER_SYSTEM}\n\nCurrent local date: {describe_today(today)}."
    return [SystemMessage(content=system), HumanMessage(content=f"Question: {question}")]


def planner_retry_messages(question: str, today: date, previous: str, problem: str) -> list[BaseMessage]:
    retry = PLANNER_RETRY.format(schema=json.dumps(PLAN_SCHEMA), problem=problem)
    return planner_messages(question, today) + [
        HumanMessage(content=f"Previous output: {previous}"),
        HumanMessage(content=retry),
    ]


def label_forecast_days(weather_data: dict, today: date) -> dict:
    """Copy of the tool result whose forecast days also say "hoje"/"amanhã" and the weekday,
    so the model does not have to do date arithmetic (the values themselves are unchanged)."""

    labelled = dict(weather_data)
    days = weather_data.get("forecast")
    if isinstance(days, list):
        labelled["forecast"] = []
        for entry in days:
            try:
                day = date.fromisoformat(entry["date"])
            except (KeyError, TypeError, ValueError):
                labelled["forecast"].append(entry)
                continue
            offset = (day - today).days
            relative = {0: "hoje", 1: "amanhã"}.get(offset)
            label = f"{WEEKDAYS_PT[day.weekday()]}" + (f" ({relative})" if relative else "")
            labelled["forecast"].append({"day": label, **entry})
    return labelled


def final_messages(question: str, today: date, weather_data: dict | None, rag_context: str | None) -> list[BaseMessage]:
    parts = [f"Data de hoje: {describe_today(today)}."]
    if weather_data is not None:
        labelled = label_forecast_days(weather_data, today)
        parts.append("[WEATHER DATA]\n" + json.dumps(labelled, ensure_ascii=False, indent=1))
    if rag_context is not None:
        parts.append("[RAG CONTEXT]\n" + (rag_context or "(nenhum contexto recuperado)"))
    parts.append(f"PERGUNTA:\n{question}\n\nResponde apenas com base nos dados acima.")
    return [SystemMessage(content=FINAL_SYSTEM), HumanMessage(content="\n\n".join(parts))]
