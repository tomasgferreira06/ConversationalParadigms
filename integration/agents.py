"""Thin respond(text) wrappers over the existing D1 and D2 agents (no logic duplicated).

- ElizaRudeAgent: D1 ELIZA_RUDE (d1_rule_based_v2/eliza_rude.py), its NLTK Chat
  used as is: same pairs, reflections and rule order. Only respond() is used,
  never converse(), because the integrated system owns the conversation loop.
- RAGAgent: D2 Coimbra Expert RAG (d2_rag/scripts/rag_pipeline.py) with
  its active frozen configuration, BASELINE (= FROZEN_V2): the existing
  retrieve -> build_messages -> generate steps over the existing vector store,
  opened once at startup and never rebuilt.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (REPO_ROOT / "d1_rule_based_v2", REPO_ROOT / "d2_rag" / "scripts", REPO_ROOT / "d3" / "coimbra_expert"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import eliza_rude as d1  # noqa: E402
import expert_agent  # noqa: E402  (D3: planner + RAG / Weather MCP; wraps the RAGAgent below)
import rag_pipeline  # noqa: E402


class ElizaRudeAgent:
    def __init__(self, chat=d1.eliza_rude):
        self.chat = chat

    def respond(self, text: str) -> str:
        # The same input preparation as nltk Chat.converse(), which D1 runs:
        # trailing "!" and "." are dropped before matching the rules.
        return self.chat.respond(text.rstrip("!."))


class RAGAgent:
    def __init__(self, store, config: rag_pipeline.RAGConfig = rag_pipeline.BASELINE):
        self.store = store
        self.config = config

    @classmethod
    def load(cls, config: rag_pipeline.RAGConfig = rag_pipeline.BASELINE) -> "RAGAgent":
        """Check Ollama, load the embedding model and open the existing store (once)."""

        rag_pipeline.check_ollama(config.llm_model)  # fail before loading anything heavy
        embeddings = rag_pipeline.load_embeddings(config)
        return cls(rag_pipeline.open_store(embeddings, config=config), config)

    def respond(self, question: str) -> str:
        results = rag_pipeline.retrieve(self.store, question, k=self.config.top_k)
        answer = rag_pipeline.generate(rag_pipeline.build_messages(question, results), self.config)
        return f"{answer}\n\nFontes:\n{rag_pipeline.format_sources(results)}"
