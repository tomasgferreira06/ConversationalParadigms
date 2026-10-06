# Coimbra Expert Agent — RAG + Weather MCP + Places MCP

## 1. Objective

Let the **LLM** decide which capabilities a question needs and compose them: the stable-knowledge RAG,
the Weather MCP and the Places MCP. No keyword, regex or hand-written routing is used anywhere.

## 2. Previous Architecture

`User → text classifier → eliza_rude | rag`, where `rag` went to an Expert Agent whose planner returned a
fixed route: `RAG | WEATHER | BOTH` (RAG + one Weather MCP). Adding a second MCP to that scheme would
have required `PLACES`, `RAG_PLACES`, `WEATHER_PLACES`, `RAG_WEATHER_PLACES`…: a combinatorial enum
that does not scale and does not represent agency. The Places MCP existed in isolation (`d3/places_mcp/`).

## 3. New Agentic Architecture

```
User
 │
 ▼
Text Classifier                       (unchanged: labels eliza_rude | rag)
 ├──────────────► ELIZA_RUDE
 │
 └──────────────► Coimbra Expert Agent        ("rag" label = "send to the Expert")
                         │
                         ▼
                    LLM Planner  (llama3.2:3b, JSON schema)  →  use_rag + tool_calls
                         │
              ┌──────────┼──────────┐
              │          │          │
             RAG      Weather MCP  Places MCP
          (retrieve)  (stdio)      (stdio)
              │          │          │
              └──────────┼──────────┘
                         │
         use_rag only?  ─┴─ yes → D2 RAGAgent.respond(question), unchanged
                          no  → ONE final generation with a block per capability
                         │
                      Answer
```

## 4. Agent Planner and Plan Schema

The enum `RAG / WEATHER / BOTH` was **replaced by `use_rag` + `tool_calls`**:

```json
{"use_rag": true | false,
 "rag_query": string | null,
 "tool_calls": [{"server": "weather" | "places", "tool": string, "arguments": {...}}]}
```

`llama3.2:3b` through Ollama's native structured output (`format=<JSON schema>`), temperature 0. It never
answers the user, no reasoning is requested or kept, and it receives the runtime local date and weekday.
Python only **validates and executes** the plan (`planner.parse_plan`):

- `use_rag` is a boolean; `tool_calls` is a list of at most **2** calls and at most **one per server**
  (two Weather calls, two Places calls or more than two calls are rejected); an empty plan is rejected;
- known server and tool of that server; strict arguments (unknown keys rejected, `null` = not given):
  `get_current_weather(location)`, `get_weather_forecast(location, days 1..7)`, `search_place(query,
  country_code?)`, `get_distance_between_places(origin, destination, country_code?)`;
  `country_code` null or two letters; non-empty strings;
- `rag_query` is required when RAG is combined with tool calls (RAG-only answers the original question);
- invalid output gets **one** retry ("Return a valid object matching this schema."), then `PlannerError`;
  there is no default capability and no fallback.

## 5. Capability Composition

Any subset of {RAG, Weather, Places} is expressible without extra routes. Expected behaviour (the planner
decides; these are illustrations, not rules in code):

| Combination | Example | Execution |
|---|---|---|
| RAG | "Quem foi D. Dinis?" | `RAGAgent.respond(question)`, unchanged |
| Weather | "Está frio agora no Porto?" | weather call → final generation |
| Places | "Onde fica o Portugal dos Pequenitos?" | places call → final generation |
| RAG + Weather | "Previsão para amanhã e história do Penedo da Saudade" | retrieval + weather call → one generation |
| RAG + Places | "Onde fica o Penedo da Saudade e o que é?" | retrieval + places call → one generation |
| Weather + Places | "Que tempo está e onde fica o Penedo da Saudade?" | both calls, no retrieval → one generation |
| RAG + Weather + Places | "Previsão para amanhã, onde fica e fala-me sobre o Penedo da Saudade" | retrieval + both calls → one generation |

## 6. RAG, Weather and Places Behaviour

- **RAG-only** (`use_rag` and no tool calls): the validated D2 pipeline, same reply and same "Fontes".
- **Tool calls (with or without RAG)**: calls run in plan order; with RAG, `retrieve(store, rag_query)` runs
  after them; then **one** final generation (llama3.2:3b, temperature 0.1) over
  `[USER QUESTION] [RAG CONTEXT] [WEATHER DATA] [PLACES DATA]`, where a block that was not planned reads
  "(não utilizado)". No complete RAG answer is generated first. An empty retrieval is shown as
  "(nenhum contexto recuperado)" (nothing is invented).
- Forecast days are annotated in Python with the weekday and "hoje"/"amanhã" (values unchanged).
- **Final prompt rules**: only the given data; Portuguese (Portugal); no invented relations between sources;
  recommend only places present in the RAG context; Places ambiguity: say which candidate (the first) is used
  and that others exist, never replace coordinates; **distances are straight-line/geodesic only**, never
  walking, driving, route or travel time, and if `candidates_found > 1` the distance depends on the places the
  service resolved.
- **Sources**: RAG "Fontes" kept; weather → `Fonte meteorológica: Open-Meteo via Weather MCP`; places →
  `Fonte geográfica: © OpenStreetMap contributors (data and geocoding via Nominatim) via Places MCP` (the
  attribution returned by the Places MCP).

## 7. Places MCP Integration

`places_mcp_client.py` (`PlacesMCPClient`) talks to `d3/places_mcp/server.py` through the real `mcp.Client`
over stdio; it never imports `places_service` (a test scans the sources and checks `sys.modules`). At startup it
requires `search_place` and `get_distance_between_places`, otherwise `PlacesMCPError` (no fallback to Python
services). The Expert executes `call.server → client.call_tool(call.tool, call.arguments)` generically.

## 8. Multi-MCP Lifecycle

`load_expert` starts **one Weather MCP session and one Places MCP session**, both long-lived for the whole
run (never per question or per tool call), and `close()` closes both (even if one fails). If the Places
server cannot start, the already started Weather server is closed again and the error is explicit.
The shared lifecycle was extracted to a small base class, `mcp_stdio_client.MCPStdioClient` (one background
thread with one event loop and one long-lived task owning `async with Client(...)`, calls scheduled with
`run_coroutine_threadsafe`, 30 s call timeout); `WeatherMCPClient` and `PlacesMCPClient` only name the
server, its tools and its error class. ELIZA_RUDE, the RAG and the chat loop stay synchronous. In the CLI,
`[router]` is now printed *before* the Expert runs, so it precedes `[expert-plan]`.

## 9. Debug Output (`--debug-agent`)

```
[expert-plan]
use_rag=true
rag_query="..."
tool_calls=2

[tool-call 1]
server=weather
tool=get_weather_forecast
arguments={"location":"Coimbra, Portugal","days":2}
...
[weather]
success=true
[rag]
retrieved=3 chunks
```

No prompts and no reasoning are printed; nothing is printed in normal mode.

## 10. Tests

| Suite | Result |
|---|---|
| `d3/places_mcp/tests` | 57 OK |
| `d3/weather_mcp/tests` | 35 OK |
| `d3/coimbra_expert/tests` | 101 OK (94 before the planner prompt refinement; 47 before the Places integration) |
| `d2_rag/tests` | 123 OK |
| `integration/tests` | 66 run (before: 63), 2 failures: the same 2 pre-existing `test_router` failures |

`coimbra_expert` (94): planner 38 (valid plans 1–9, invalid 10–24 and extras, retry, schema consistency),
expert orchestration 30 (A–J, no-keyword tests, final prompt, debug, lifecycle), Places client 15,
Weather client 11 (kept, now on the shared base). No Internet, Ollama or Chroma; two tests start the real
stdio servers but only trigger validation errors. The 3 new `integration` tests cover the debug order.
New regressions: none. The 2 pre-existing failures ("Quero ir para casa." and a thanks message routed to `rag`)
are untouched and were not "fixed".

## 11. Real Smoke Tests

Real llama3.2:3b, real embeddings, runtime copy of `chroma_frozen_v2`, real Weather MCP/Open-Meteo, real
Places MCP/Nominatim, on 2026-10-05. **No prompt or rule was tuned for these questions.** They are smoke
tests only and must not be reused in the D3 evaluation dataset.

### 11.1 LLM-driven (the planner chooses)

| # | Question (short) | Expected | Planner chose | Outcome |
|---|---|---|---|---|
| 1 | Jardim da Sereia, original purpose | RAG | RAG | correct answer + sources |
| 2 | Temperatura atual em Coimbra | Weather | Weather `get_current_weather` | correct ("26.0°C") |
| 3 | Onde fica a Sé Velha | Places | RAG only | not as expected; Places not used; the RAG answer is contradictory about coordinates |
| 4 | Distância em linha reta Sé Velha ↔ Jardim Botânico | Places distance | RAG only | not as expected; "informação insuficiente" |
| 5 | Previsão amanhã + Jardim da Sereia | RAG + Weather | RAG + Weather + Places | weather values and RAG part correct; the answer wrote "segunda-feira, 2026-10-06" (it is a Tuesday); the Places call (Jardim da Sereia) was unnecessary and unused in the text |
| 6 | Onde fica a Sé Velha + importância | Places + RAG | RAG only | not as expected; RAG answer is good and mentions the location from the corpus |
| 7 | Que tempo agora + onde fica a Sé Velha | Weather + Places | RAG only | not as expected; weather ignored ("informação insuficiente") |
| 8 | Previsão amanhã + onde fica + sobre a Sé Velha | RAG + Weather + Places | RAG + Weather | no Places; weather values and RAG part correct, with the same wrong weekday |

The capability selection of the 3B planner is **unreliable for Places**: it chose a Places call in 1 of 8
questions (and there it was not needed) and under-called it in the 5 where it was expected. Weather and RAG
selection were good in 1, 2, 5 and 8. This was documented, not corrected with prompt tuning or keyword rules,
as instructed.

### 11.2 Scripted-plan execution check (`smoke_test.py --scripted`)

To verify the execution path independently of planner quality, a fixed plan (still validated by `parse_plan`)
is injected for the questions the planner got wrong, using the real RAG, MCP servers and final generation.
It checks execution, **not** selection.

| Combination | Result |
|---|---|
| Places search only | OK: location, address and coordinates of the Sé Velha, geographic source line |
| Places distance only | OK: "distância em linha reta … 0,7 km" (states straight-line) |
| RAG + Places | executed (retrieval + places, both sources); the 3B answer added an unsupported "distance not determined" sentence |
| Weather + Places | both calls executed, both source lines; the answer used the weather and omitted the Places location, and said "probabilidade de chuva 0%" which the current-weather data does not contain |
| RAG + Weather + Places | all three executed in one generation, three source blocks; weather and RAG parts correct, Places location omitted |

No orphan server process after any run; the protected `chroma_frozen_v2` was not opened by the smokes and its
hash was unchanged after starting the CLI.

### 11.3 CLI entrypoint

`uv run python integration/integrated_agent.py --debug-routing --debug-agent` starts, loads router, ELIZA_RUDE,
RAG, Weather MCP and Places MCP, runs and exits with code 0 (closing both sessions); the frozen store's hash is
unchanged. (A PowerShell pipe delivered the exit word with a leading byte-order mark, so that input was handled
as a normal message; unrelated to this change.)

## Planner Prompt Refinement

**Why.** The smoke tests (11.1) showed that the 3B planner does not decompose multi-intent questions: it often
selected only RAG, forgot Weather or Places, or put a weather need into `rag_query`. Execution was fine (11.2);
the weakness was capability selection.

**What changed: only the planner system prompt (`PLANNER_SYSTEM` in `prompts.py`).** Everything else is
byte-identical: `PLAN_SCHEMA`, `parse_plan` and the validation, the retry, the temperature, the Expert
orchestration, the MCPs, the RAG, the classifier and `FINAL_SYSTEM` (the final generation). No Python keyword,
regex or string-matching routing was added; the unit tests still scan the Python sources for it.

- **Silent decomposition**: "identify every need; match each to a capability; select ALL the capabilities that
  are needed; `rag_query` only for the stable-knowledge part". The model is told not to write its analysis
  (output stays JSON only, no reasoning).
- **Capabilities defined semantically**: RAG = stable tourist/cultural knowledge, and explicitly *not* the
  source for weather, coordinates, addresses, location or distance; Weather = any current/future weather need
  (current, temperature, rain, wind, forecast, today/tomorrow/next days), never looked up in RAG; Places = any
  geographic need (where, location, address, coordinates, distance), not to be answered from RAG when a Places
  tool fits; `get_distance_between_places` is chosen for any distance question even without "in a straight line".
  These are semantic descriptions for the LLM, not conditional rules.
- **Multi-intent rule** (do not choose only the dominant capability; analyse each need separately) with the
  four combinations as illustration, and an **independence rule** (needing RAG does not remove Weather or Places,
  and so on).
- **`rag_query`** only for the knowledge part; the weather/geographic part is never moved into it (with a
  counter-example).
- **Few-shot examples**: 9 instead of 6: 5 added (RAG+Weather, RAG+Places, Weather+Places, RAG+Weather+Places,
  distance) and 2 older ones (a distance and a composition example) replaced by them. They use other places
  (Lisboa, Belém, Jerónimos, Porto) and no smoke-test question; together the 9 show all 7 capability
  combinations.
- **Tests**: 7 invariant tests (`PlannerPromptTests`: the new instructions are present, every example is a valid
  plan, the 7 combinations are covered, no smoke question in the examples, no reasoning requested, no keyword
  rule). They do not claim that planning improved; `coimbra_expert` now has 101 tests (94 before).
- **Method**: this was one controlled round. After the dev check below, the prompt was **not** tuned again and no
  example was added for the questions that failed.

## Planner Development Check

Planner only (real llama3.2:3b, temperature 0, no RAG/MCP/final generation), `dev_planner_check.py`, 2026-10-05.
The 14 questions are a **dev set, separate from the future D3 evaluation dataset** (they must not be included in
it), and they do not reuse the smoke questions or the prompt examples. Metric: Exact Capability Match
(`use_rag`, Weather selected, Places selected must all equal the expectation).

| # | Category | Question | Expected | Predicted | Exact match |
|---|---|---|---|---|---|
| 1 | RAG | Quais são os doces conventuais típicos de Coimbra? | RAG | RAG | yes |
| 2 | RAG | Quem foi Inês de Castro e que ligação tem a Coimbra? | RAG | RAG | yes |
| 3 | Weather | Vai haver vento forte em Coimbra nos próximos dias? | Weather | Weather (forecast, 3 days) | yes |
| 4 | Weather | Está a chover neste momento em Aveiro? | Weather | Weather (current) | yes |
| 5 | Places | Onde está situado o Mosteiro de Santa Cruz em Coimbra? | Places | RAG + Places | **no** |
| 6 | Places | Quantos quilómetros separam o Museu da Ciência da estação Coimbra-B? | Places | Places (distance) | yes |
| 7 | RAG+Weather | Como vai estar o tempo hoje em Coimbra? Aproveito para perguntar o que é a Queima das Fitas. | RAG + Weather | RAG + Weather | yes |
| 8 | RAG+Weather | Vai estar frio nos próximos três dias em Coimbra? Fala-me também da tradição da capa e batina. | RAG + Weather | RAG + Weather | yes |
| 9 | RAG+Places | Onde fica o Museu da Ciência da Universidade de Coimbra e o que se pode ver lá? | RAG + Places | RAG + Places | yes |
| 10 | RAG+Places | Diz-me a localização do Convento de Santa Clara-a-Nova e conta-me a sua história. | RAG + Places | RAG + Weather | **no** |
| 11 | Weather+Places | Qual é a temperatura atual em Coimbra e onde fica o Estádio Cidade de Coimbra? | Weather + Places | RAG + Weather | **no** |
| 12 | Weather+Places | Como estará o tempo amanhã em Évora e qual é a distância entre a Sé de Évora e o Templo Romano? | Weather + Places | RAG + Weather + Places | **no** |
| 13 | RAG+Weather+Places | Vai chover amanhã em Guimarães? Onde fica o Castelo de Guimarães e qual é a sua importância histórica? | all three | RAG + Weather + Places | yes |
| 14 | RAG+Weather+Places | Que tempo vai fazer amanhã em Coimbra, onde fica a Quinta das Lágrimas e qual é a sua história? | all three | RAG + Weather | **no** |

**Exact Capability Match: 9/14.** By category: RAG 2/2, Weather 2/2, Places 1/2, RAG+Weather 2/2, RAG+Places 1/2,
Weather+Places 0/2, RAG+Weather+Places 1/2.

For reference only (not a tuning step), the planner prompt used before this round (reconstructed from this
session's earlier version, same dev set, same settings) scored 6/14 (RAG 2/2, Weather 2/2, Places 1/2,
RAG+Weather 0/2, RAG+Places 0/2, Weather+Places 0/2, RAG+Weather+Places 1/2). One run each at temperature 0 on 14
questions is a small, noisy sample.

Remaining error patterns:

- **Places dropped in combinations** (11, 14): Weather is now selected reliably, Places is still omitted when it is
  the second or third need.
- **A dynamic or geographic need moved into `rag_query`** (11: "Temperatura atual em Coimbra"; 12: "Distância entre
  a Sé de Évora e o Templo Romano"), exactly what the prompt forbids, which also turns on RAG unnecessarily.
- **Over-selecting RAG for a pure location question** (5) and **wrong capability for a geographic need** (10:
  a weather forecast was chosen for a location + history question).
- **Accent corruption in generated strings** ("Guimarçes", "Importãncia", "Inès"): a 3B artifact; in 13 it also
  reached the tool arguments ("Guimarçes, Portugal"), which would probably fail geocoding in a real run.

These results are for review before any new change; the dev set must stay out of the D3 evaluation dataset.

## 12. Files Created / Modified

Created: `d3/coimbra_expert/mcp_stdio_client.py`, `places_mcp_client.py`, `tests/test_places_mcp_client.py`,
`dev_planner_check.py` (planner-only dev check, 14 questions kept out of the D3 evaluation dataset).
In the planner prompt refinement round only `PLANNER_SYSTEM` in `prompts.py`, `tests/test_planner.py` (+7 prompt
invariant tests), this report and the new `dev_planner_check.py` were touched.
Modified: `d3/coimbra_expert/{planner.py, prompts.py, expert_agent.py, weather_mcp_client.py, smoke_test.py}`,
`d3/coimbra_expert/tests/{test_planner.py, test_expert_agent.py}`, `integration/integrated_agent.py`,
`integration/tests/test_integrated_agent.py`, `README.md`, this report.
Not touched: D1, classifier (model, dataset, `router.py`, `test_router.py`), D2 code/corpus/chunks/manifest/stores/
evaluation, `d3/weather_mcp/`, `d3/places_mcp/`.

## 13. Limitations

- **Planner reliability**: llama3.2:3b under-selects the Places MCP and sometimes ignores a needed capability
  (see 11.1), and can add an unneeded call. This is the main weakness; it is what the evaluation should measure.
- **Generation**: the 3B final generation sometimes omits a block (e.g. the Places location), writes the wrong
  weekday for "amanhã" despite the labelled data, over-reads data ("0%" probability for current weather) or adds
  unsupported sentences; the prompt rules do not prevent all of it.
- Ambiguous Places results: the distance uses the best-ranked candidate (`candidates_found` is passed to the model).
- Conditional recommendations ("what to visit if it rains") remain limited by the corpus, as before.
- At most one Weather and one Places call per question; no multi-step loops.
- A failing MCP call is an explicit error to the user (no RAG-only fallback, by design).
- The outer classifier is unchanged: "Vai chover amanhã" is borderline and 2 old tests still fail.
- Synchronous single-user CLI; calls block while waiting for Ollama, Open-Meteo or Nominatim (1 req/s limit).

## 14. Next Step

Create and freeze the D3 evaluation dataset, then perform the detailed D3-O1 evaluation of retrieval, generation
and agentic capability selection. Planner improvements (if any) should be developed on a separate dev set, never
on the evaluation questions or on these smoke questions.
