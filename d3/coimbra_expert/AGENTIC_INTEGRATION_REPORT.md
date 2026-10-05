# Coimbra Expert Agent — RAG + Weather MCP

## 1. Objective

Integrate the Weather MCP into the Coimbra Expert Agent and let the **LLM** decide which capabilities
a question needs: `RAG`, `WEATHER` or `BOTH`. No keyword, regex or hand-written routing is used.

## 2. Previous Architecture

`User → text classifier → eliza_rude | rag (D2 RAGAgent)`. The Weather MCP (`d3/weather_mcp/`) existed
in isolation. The classifier (labels `eliza_rude` / `rag`), ELIZA_RUDE and the RAG are unchanged.

## 3. New Agentic Architecture

```
User
 │
 ▼
Text Classifier
 ├──────────────► ELIZA_RUDE
 │
 └──────────────► Coimbra Expert Agent        (label "rag" now means "send to the Expert")
                         │
                         ▼
                    LLM Planner (llama3.2:3b, JSON schema)
                   /     |      \
                  /      |       \
               RAG    WEATHER    BOTH
                │        │       /  \
                │    Weather   RAG  Weather
                │      MCP    retrieve MCP
                \        |       \    /
                 \       |        \  /
                  └──────┴─────────┘
                         │
                 Final generation (WEATHER, BOTH)
                         │
                    Final Answer
```

Code: `d3/coimbra_expert/{planner.py, prompts.py, weather_mcp_client.py, expert_agent.py}`;
`integration/integrated_agent.py` builds the Expert over the existing `RAGAgent` and dispatches the
`rag` label to it.

## 4. Agent Planner

`llama3.2:3b` via `ChatOllama(format=<JSON schema>)` (Ollama's native structured output), temperature 0.
It never answers the user and returns only a structured decision (no reasoning is requested or kept).
The system prompt describes the capabilities and routes, gives the runtime local date and weekday
(for "hoje/amanhã/próximos dias"), and a few illustrative examples (other places/phrasings than any
smoke or evaluation question). The output is validated in Python (`parse_plan`); invalid output gets
**one** retry ("Return a valid object matching this schema."), then an explicit `PlannerError`. There is
no fallback route. Python never inspects the question text (a unit test scans the sources for this).

## 5. Available Capabilities

- **RAG**: the existing D2 pipeline (`BASELINE = FROZEN_V2`), untouched.
- **Weather MCP**: `get_current_weather(location)`, `get_weather_forecast(location, days)`.

## 6. Structured Plan Schema

```json
{"route": "RAG" | "WEATHER" | "BOTH",
 "rag_query": string | null,
 "weather": {"tool": "get_current_weather" | "get_weather_forecast",
             "location": string, "days": integer | null} | null}
```

Validation: route in the three values; WEATHER/BOTH need `weather` with a valid tool and a non-empty
location; a forecast needs an integer `1 <= days <= 7` (`days` is ignored for current weather); BOTH
also needs a non-empty `rag_query`; RAG needs nothing (a stray `weather` is dropped).

## 7. RAG Route

`RAGAgent.respond(question)` with the original question: the same retrieve → build_messages → generate
and the same "Fontes" as in D2. The MCP is not called.

## 8. WEATHER Route

The planner's tool is called through the MCP client, and its structured result goes to one final
generation (llama3.2:3b, temperature 0.1, D3 prompt) that may only use that data. The reply ends with
`Fonte meteorológica: Open-Meteo via Weather MCP`. No retrieval. Forecast days are labelled in Python with
their weekday and "hoje"/"amanhã" (values unchanged), because the small model did date arithmetic badly.

## 9. BOTH Route

planner → `retrieve(store, rag_query, k=top_k)` (the focused knowledge query) + MCP call → **one** final
generation with `[WEATHER DATA]` and `[RAG CONTEXT]` as separate sections and the original question.
No complete RAG answer is generated first. Sources: the existing RAG "Fontes" plus the weather source
line. With empty retrieval the prompt says "(nenhum contexto recuperado)" and no context is invented.
The prompt only allows recommending places present in the RAG context and forbids assuming a place is
indoor/covered/rain-suitable unless the context says so.

## 10. MCP Client Lifecycle

mcp 2.3.0's `Client` is async and must be entered/exited in the same task. `WeatherMCPClient` keeps the
app synchronous: one background thread runs one event loop with one long-lived task owning
`async with Client(StdioServerParameters(...))`; chat-thread calls are scheduled on that loop with
`run_coroutine_threadsafe`. So: one server subprocess and one session per chatbot run (never per
message), tools discovered at startup, clean close on exit (`finally` in `main`; verified: no orphan
server process). At startup both tools must exist, otherwise `WeatherMCPError` and exit code 2; there
is no fallback to calling `weather_service` (it is never imported). ELIZA_RUDE, the RAG and
`integrated_agent.run` stay synchronous (acceptable for a single-user CLI); no async refactor was done.
Per-call timeout 30 s.

## 11. Final Generation

llama3.2:3b, temperature 0.1, `FINAL_SYSTEM` in `prompts.py`: European Portuguese, concise, only the
provided data, say when data cannot answer a part, integrate weather and tourism without inventing
relations, never invent source URLs. The weather and RAG sections are never mixed.

## 12. Tests

47 new unit tests in `d3/coimbra_expert/tests` (no Ollama/Open-Meteo/Chroma): planner validation and
retry (19), expert orchestration A–F plus no-keyword-routing, forecast labels, debug output and loading
(17), MCP client lifecycle/calls/errors including one real stdio server run that needs no Internet (11).
5 tests were added to `integration/tests/test_integrated_agent.py` (63 in the suite now) and one startup
test was adapted (it now mocks `load_expert`). `test_router.py` was not touched.

| Suite | Result |
|---|---|
| `d3/weather_mcp/tests` | 35 OK |
| `d3/coimbra_expert/tests` | 47 OK |
| `d2_rag/tests` | 123 OK |
| `integration/tests` | 63 run, 2 failures (the same 2 pre-existing ones) |

Pre-existing failures (before D3, unchanged, not hidden): `test_router.TrainedRouterTests.test_boundary_cases`
("Quero ir para casa.") and `test_chit_chat_goes_to_eliza_rude` (thanks message). New regressions: none.

## 13. Real Smoke Tests

Real Ollama llama3.2:3b, real embeddings, a runtime copy of `chroma_frozen_v2`, real Weather MCP and
Open-Meteo, run on 2026-10-05 through `smoke_test.py`. Routes were never given. Not the D3 evaluation.

| # | Question | Planner | Result |
|---|---|---|---|
| 1 | Estação Nova: when and who signed | RAG | RAG answer + sources; MCP not called |
| 2 | Que tempo está agora em Coimbra? | WEATHER, `get_current_weather`, "Coimbra, Portugal" | correct answer from tool data |
| 3 | Vai chover amanhã em Coimbra? | WEATHER, `get_weather_forecast`, days=3 | "Sim… 78%… 4.3 mm" (matches the data) |
| 4 | Tempo amanhã + Jardim Botânico | BOTH, forecast days=2, rag_query about the Jardim Botânico | one answer with weather (min/max, 78%, 4.3 mm) and RAG facts; both sources |
| 5 | Vai chover amanhã? Se chover, o que posso visitar? | BOTH (not forced), forecast days=2 | weather correct; see below |

Observations: in the first run, #3 answered "Não… probabilidade 78%" and mislabelled the weekday; the
forecast day labels (a general fix, not specific to that question) removed that in the second run. In #4
the planner wrote "Botãnico" (typo in `rag_query`); retrieval still found the right chunks. #5 is the
weak case: the generic `rag_query` ("O que visitar em Coimbra se chover?") retrieved night-life/sport
chunks, and the answer drifted into unsupported suggestions ("bares e cafés protegidos", "evitar
atividades ao ar livre") in spite of the prompt rules. This was not patched for that example; it is a
limitation of the 3B model and of retrieval for conditional questions, to be measured in the evaluation.

## 14. Full-System Classifier Pre-check

Run before any change, classifier untouched (threshold 0.45):

| Message | Label | P(rag) |
|---|---|---|
| Que tempo está agora em Coimbra? | rag | 0.59 |
| Vai chover amanhã em Coimbra? | rag | 0.49 (borderline) |
| Que tempo vai estar amanhã em Coimbra e fala-me do Jardim Botânico. | rag | 0.62 |
| Quando foi construída a Estação Nova de Coimbra? | rag | 0.65 |
| Vai chover amanhã em Coimbra? Se chover, o que posso visitar? | rag | 0.57 |

All reach the Expert Agent. No misrouting; "Vai chover amanhã" is close to the threshold, a separate
fragility of the outer classifier (not trained on weather questions).

## 15. Files Created / Modified

Created (`d3/coimbra_expert/`): `__init__.py`, `planner.py`, `prompts.py`, `weather_mcp_client.py`,
`expert_agent.py`, `smoke_test.py`, `AGENTIC_INTEGRATION_REPORT.md`, `tests/test_planner.py`,
`tests/test_expert_agent.py`, `tests/test_weather_mcp_client.py`.
Modified: `integration/agents.py` (adds `d3/coimbra_expert` to `sys.path`, imports `expert_agent`),
`integration/integrated_agent.py` (`rag` label → Expert, `--debug-agent`, MCP close, expert error
handling), `integration/tests/test_integrated_agent.py`, `d3/weather_mcp/server.py` (server log level
WARNING so HTTP lines do not pollute the chat), `d3/weather_mcp/WEATHER_MCP_IMPLEMENTATION_REPORT.md`
(one note), `README.md`; `pyproject.toml`/`uv.lock` (mcp, previous step).
Not touched: classifier, dataset, models, ELIZA_RUDE, D2 code/corpus/chunks/manifest/stores/evaluation.

## 16. Limitations

- The 3B planner and generator are imperfect (typos in `rag_query`, weak conditional recommendations).
- A generic `rag_query` for "what to visit if it rains" retrieves poorly; there is no rain-suitability
  data in the corpus, so such answers are necessarily limited.
- The planner's `days` choice and relative-date handling depend on the LLM (the date is given in the prompt).
- A weather/MCP failure is an explicit error message to the user (no RAG-only fallback, by design).
- The outer classifier is borderline for some weather questions and still has its 2 pre-existing failures.
- The full interactive CLI was not run against the protected `chroma_frozen_v2`; the smoke used a copy.
- Calls block the (single-user) chat while waiting for Ollama/Open-Meteo.

## 17. Next Step

Perform the detailed D3-O1 evaluation of retrieval, generation and agentic tool selection.
