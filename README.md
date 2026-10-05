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

### Coimbra Expert Agent (RAG / WEATHER / BOTH)

The classifier's `rag` label now goes to the Coimbra Expert Agent (`d3/coimbra_expert/`). An LLM planner
(`llama3.2:3b`, structured output; no keyword routing) decides whether a question needs the RAG, the
Weather MCP or both, then the answer is produced (RAG-only keeps the D2 behaviour). The integrated agent
starts one Weather MCP server (stdio) per run. Details: `d3/coimbra_expert/AGENTIC_INTEGRATION_REPORT.md`.

```bash
# run the integrated agent (needs Ollama + llama3.2:3b); --debug-agent shows the plan and capabilities used
uv run python integration/integrated_agent.py --debug-agent

# tests (no Ollama, no Internet)
uv run python -m unittest discover -s d3/coimbra_expert/tests

# manual smoke test: real Ollama + Open-Meteo, on a runtime copy of the frozen Chroma store
uv run python d3/coimbra_expert/smoke_test.py
```
