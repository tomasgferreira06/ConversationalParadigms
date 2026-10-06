# ConversationalParadigms

## D1 + D2 integrated agent (text-classification routing)

A text classifier (TF-IDF + Logistic Regression) routes each message either to
ELIZA_RUDE (D1, chit-chat) or to the Coimbra Tourism Expert RAG (D2). Details
and results: `integration/CLASSIFIER_ROUTING_REPORT.md`.

Requires Ollama with `llama3.2:3b` and the existing `d2_rag/data/chroma_frozen_v2` store.

```bash
# (re)train the router: dataset validation, 70/30 split, models A and B, saves the selected one
uv run python integration/train_classifier.py

# run the integrated agent ("sair" ends the program)
uv run python integration/integrated_agent.py

# same, showing the class probabilities and the selected agent for each message
uv run python integration/integrated_agent.py --debug-routing

# tests (no Ollama, no embedding model, no Chroma)
uv run python -m unittest discover -s integration/tests
```

## D3-O1 — Weather MCP

An MCP server (stdio, official Python SDK) with two tools, `get_current_weather` and
`get_weather_forecast`, backed by Open-Meteo. Path: `d3/weather_mcp/` (see its `README.md`).

```bash
uv run python -m unittest discover -s d3/weather_mcp/tests
```

Status: connected to the integrated agent through the Coimbra Expert Agent (below).

### Places MCP

A second MCP server (stdio) with `search_place` and `get_distance_between_places` (straight-line
distance), backed by OpenStreetMap Nominatim with its usage policy (≤1 req/s, own User-Agent, cache,
attribution). Path: `d3/places_mcp/` (see its `README.md`).

```bash
uv run python -m unittest discover -s d3/places_mcp/tests
```

### Coimbra Expert Agent (RAG + Weather MCP + Places MCP)

The classifier's `rag` label goes to the Coimbra Expert Agent (`d3/coimbra_expert/`). An LLM planner
(`llama3.2:3b`, structured output; no keyword routing) returns `use_rag` plus up to two MCP `tool_calls`
(at most one Weather and one Places call), so the agent can compose RAG, Weather MCP and Places MCP in any
combination (RAG-only keeps the D2 behaviour; otherwise one final generation uses all the results). The
integrated agent starts one Weather MCP and one Places MCP server (stdio) per run. Details and the
(mixed) smoke-test results: `d3/coimbra_expert/AGENTIC_INTEGRATION_REPORT.md`.

```bash
# run the integrated agent (needs Ollama + llama3.2:3b); --debug-routing shows the classifier,
# --debug-agent shows the Expert's plan, tool calls and capabilities used
uv run python integration/integrated_agent.py --debug-routing --debug-agent

# tests (no Ollama, no Internet)
uv run python -m unittest discover -s d3/coimbra_expert/tests

# manual smoke test: real Ollama + Open-Meteo + Nominatim, on a runtime copy of the frozen Chroma store
uv run python d3/coimbra_expert/smoke_test.py             # the LLM planner chooses
uv run python d3/coimbra_expert/smoke_test.py --scripted  # fixed plans: execution-path check only
```
