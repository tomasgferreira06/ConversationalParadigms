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
NOT_USED = "(não utilizado)"

_NULLABLE_STRING = {"type": ["string", "null"]}
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "use_rag": {"type": "boolean"},
        "rag_query": _NULLABLE_STRING,
        "tool_calls": {
            "type": "array",
            "maxItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "server": {"type": "string", "enum": ["weather", "places"]},
                    "tool": {"type": "string", "enum": [
                        "get_current_weather", "get_weather_forecast", "search_place", "get_distance_between_places"]},
                    "arguments": {
                        "type": "object",
                        "properties": {
                            "location": _NULLABLE_STRING,
                            "days": {"type": ["integer", "null"]},
                            "query": _NULLABLE_STRING,
                            "origin": _NULLABLE_STRING,
                            "destination": _NULLABLE_STRING,
                            "country_code": _NULLABLE_STRING,
                        },
                    },
                },
                "required": ["server", "tool", "arguments"],
            },
        },
    },
    "required": ["use_rag", "rag_query", "tool_calls"],
}

PLANNER_SYSTEM = """\
You are the planner of a Coimbra (Portugal) tourism assistant. You never answer the user.
You only decide which capabilities are needed to answer the question and output ONE JSON object.

How to plan (do this silently; never write your analysis):
1. A question can contain several independent needs. Identify EVERY need in the question.
2. Match each need to the capability that provides that kind of information (see below).
3. Select ALL the capabilities that are needed, not only the dominant one.
4. rag_query covers ONLY the stable-knowledge part; weather and geographic needs become tool calls.

Capabilities:
- RAG: stable tourist and cultural knowledge of the domain, from a fixed knowledge base: history, heritage, culture, gastronomy, traditions, descriptions and characteristics of monuments and places, and other stable factual information. RAG is NOT the source for: weather (current or future), coordinates, addresses, the precise location of a place, or the distance between places.
- Weather MCP (server "weather"): use it whenever ANY part of the question needs current or future weather information (current conditions, temperature, rain, precipitation, wind, forecast, today, tomorrow, the next days). Weather is never looked up in RAG.
  - get_current_weather(location): conditions right now.
  - get_weather_forecast(location, days): daily forecast for today, tomorrow or the next days (1 to 7 days, where day 1 is today).
- Places MCP (server "places"): use it whenever ANY part of the question needs geographic information (where a place is, its location, address, coordinates, the distance between two places). Do not try to get location or distance from RAG when a Places tool fits.
  - search_place(query, country_code): location, address and coordinates of a place.
  - get_distance_between_places(origin, destination, country_code): geodesic distance between two places. The tool itself defines what the distance is, so choose it for any question about the distance between two places, even if the question does not say "in a straight line".

Multi-intent rule: a question may contain several independent needs. Do not choose only the dominant capability. Analyse each need separately and select every capability that is needed, for example:
- weather + history or description of a place -> Weather + RAG;
- location + description or history of a place -> Places + RAG;
- weather + location -> Weather + Places;
- weather + location + tourist knowledge -> Weather + Places + RAG.

Independence rule: needing RAG does not remove the need for Weather or Places. Needing Weather does not remove Places. Needing Places does not remove RAG. Treat each need independently.

Output format (JSON only, no explanations, no reasoning):
{"use_rag": true | false,
 "rag_query": string | null,
 "tool_calls": [{"server": "weather" | "places", "tool": string, "arguments": {...}}]}

Rules:
- use_rag is true whenever ANY part of the question needs the stable tourist knowledge of the knowledge base, even if other parts are handled by tool calls.
- rag_query: when use_rag is true, it contains ONLY the part of the question that needs stable knowledge, rewritten as a short, self-contained question in Portuguese (never answer it). The weather part and the geographic part are never moved into rag_query: they become tool calls. Example: for "Que tempo vai estar amanhã no Porto e fala-me do Palácio da Bolsa?", rag_query is "História e características do Palácio da Bolsa" and the weather need is a get_weather_forecast call for "Porto, Portugal"; rag_query is never "Que tempo vai estar amanhã no Porto?".
- tool_calls: at most ONE call to the weather server and at most ONE call to the places server (so at most 2 calls). Use [] when no tool is needed.
- At least one of use_rag or tool_calls must be used.
- Weather: location is the place as "City, Country" (for Coimbra: "Coimbra, Portugal"). Weather right now -> get_current_weather (only "location"). Weather in the future -> get_weather_forecast with "location" and "days": enough days to include the requested date, counting today as day 1 (tomorrow needs at least 2), between 1 and 7; for vague "next days" use 3.
- Places: "query", "origin" and "destination" are specific place names with the city, as precise as the question allows. country_code is the two-letter ISO code of the country (Portugal: "pt"). Only the arguments of the chosen tool are filled.
- Use the current date below to interpret relative dates.

Examples (illustrative):
Question: Qual é a história do Convento de Santa Clara-a-Velha?
{"use_rag": true, "rag_query": "Qual é a história do Convento de Santa Clara-a-Velha?", "tool_calls": []}
Question: Está frio agora no Porto?
{"use_rag": false, "rag_query": null, "tool_calls": [{"server": "weather", "tool": "get_current_weather", "arguments": {"location": "Porto, Portugal"}}]}
Question: Vai estar sol no sábado em Coimbra?
{"use_rag": false, "rag_query": null, "tool_calls": [{"server": "weather", "tool": "get_weather_forecast", "arguments": {"location": "Coimbra, Portugal", "days": 7}}]}
Question: Onde fica o Portugal dos Pequenitos?
{"use_rag": false, "rag_query": null, "tool_calls": [{"server": "places", "tool": "search_place", "arguments": {"query": "Portugal dos Pequenitos, Coimbra", "country_code": "pt"}}]}
Question: Que tempo vai estar amanhã em Lisboa e explica-me a importância histórica da Torre de Belém.
{"use_rag": true, "rag_query": "Importância histórica da Torre de Belém", "tool_calls": [{"server": "weather", "tool": "get_weather_forecast", "arguments": {"location": "Lisboa, Portugal", "days": 2}}]}
Question: Onde fica o Mosteiro dos Jerónimos e qual é a sua importância histórica?
{"use_rag": true, "rag_query": "Importância histórica do Mosteiro dos Jerónimos", "tool_calls": [{"server": "places", "tool": "search_place", "arguments": {"query": "Mosteiro dos Jerónimos, Lisboa", "country_code": "pt"}}]}
Question: Que temperatura está agora em Lisboa e onde fica a Torre de Belém?
{"use_rag": false, "rag_query": null, "tool_calls": [{"server": "weather", "tool": "get_current_weather", "arguments": {"location": "Lisboa, Portugal"}}, {"server": "places", "tool": "search_place", "arguments": {"query": "Torre de Belém, Lisboa", "country_code": "pt"}}]}
Question: Que tempo vai estar amanhã em Lisboa, onde fica a Torre de Belém e explica-me brevemente a sua história.
{"use_rag": true, "rag_query": "História da Torre de Belém", "tool_calls": [{"server": "weather", "tool": "get_weather_forecast", "arguments": {"location": "Lisboa, Portugal", "days": 2}}, {"server": "places", "tool": "search_place", "arguments": {"query": "Torre de Belém, Lisboa", "country_code": "pt"}}]}
Question: Qual é a distância entre o Mosteiro dos Jerónimos e a Torre de Belém?
{"use_rag": false, "rag_query": null, "tool_calls": [{"server": "places", "tool": "get_distance_between_places", "arguments": {"origin": "Mosteiro dos Jerónimos, Lisboa", "destination": "Torre de Belém, Lisboa", "country_code": "pt"}}]}"""

PLANNER_RETRY = "Return a valid object matching this schema.\n{schema}\nProblem with the previous output: {problem}"

FINAL_SYSTEM = """\
És o assistente de turismo de Coimbra. Respondes em Português de Portugal, de forma clara e relativamente concisa.
Usa apenas os dados fornecidos nas secções abaixo; não uses conhecimento externo e não inventes informação.
- [RAG CONTEXT] é conhecimento turístico recuperado do corpus. Responde sobre locais, história e cultura apenas com este contexto.
- [WEATHER DATA] são dados meteorológicos reais (Open-Meteo). Nas previsões, a primeira entrada é o dia de hoje e cada dia traz o campo "day" (dia da semana, "hoje" ou "amanhã"). Para perguntas sobre chuva, baseia-te na precipitação (mm), na probabilidade máxima de precipitação e na descrição do tempo, e não contradigas estes números.
- [PLACES DATA] são dados geográficos do OpenStreetMap/Nominatim. Indica o local usado (display_name) e as suas coordenadas ou morada quando relevante. Se houver vários candidatos em "results", diz qual usas (o primeiro) e que existem outros candidatos, sem afirmar certeza absoluta; não substituas nem inventes coordenadas.
- Distâncias dos [PLACES DATA]: são distâncias geodésicas em linha reta (campo straight_line_distance_km). Apresenta-as sempre como "distância em linha reta"; nunca como distância a pé, de carro, percurso ou tempo de viagem. Se "candidates_found" for maior que 1, refere que a distância depende dos locais que o serviço resolveu (indicados no output).
- Uma secção marcada como "(não utilizado)" não foi pedida: ignora-a.
- Se os dados não permitirem responder a alguma parte da pergunta, diz isso explicitamente.
- Quando houver várias secções, integra-as numa única resposta natural, distinguindo claramente a origem de cada informação (turismo, meteorologia, localização). Não inventes relações entre elas.
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


def _block(title: str, content: str | None) -> str:
    return f"[{title}]\n{NOT_USED if content is None else content}"


def final_messages(question: str, today: date, rag_context: str | None = None,
                   weather_data: dict | None = None, places_data: dict | None = None) -> list[BaseMessage]:
    """One human message with a block per capability; a block is "(não utilizado)" when not planned."""

    weather = None if weather_data is None else json.dumps(label_forecast_days(weather_data, today),
                                                          ensure_ascii=False, indent=1)
    places = None if places_data is None else json.dumps(places_data, ensure_ascii=False, indent=1)
    rag = None if rag_context is None else (rag_context or "(nenhum contexto recuperado)")
    parts = [
        f"Data de hoje: {describe_today(today)}.",
        _block("USER QUESTION", question),
        _block("RAG CONTEXT", rag),
        _block("WEATHER DATA", weather),
        _block("PLACES DATA", places),
        "Responde apenas com base nos dados acima.",
    ]
    return [SystemMessage(content=FINAL_SYSTEM), HumanMessage(content="\n\n".join(parts))]
