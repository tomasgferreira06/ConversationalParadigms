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
