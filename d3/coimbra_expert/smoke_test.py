"""Manual smoke test of the Coimbra Expert Agent (NOT a unit test, NOT the D3 evaluation).

Real Ollama (llama3.2:3b), real embeddings, a RUNTIME COPY of the frozen Chroma store
(the protected store is never opened) and the real Weather MCP + Open-Meteo.
The routes are never given: the planner decides.

Usage:
    uv run python d3/coimbra_expert/smoke_test.py [question ...]
"""

import dataclasses
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "integration"))

import agents  # noqa: E402  (sets up the sys.path of D1, D2 and D3)

QUESTIONS = [
    "Quando foi construída a Estação Nova de Coimbra e quem assinou o projeto?",
    "Que tempo está agora em Coimbra?",
    "Vai chover amanhã em Coimbra?",
    "Que tempo vai estar amanhã em Coimbra e fala-me do Jardim Botânico.",
    "Vai chover amanhã em Coimbra? Se chover, o que posso visitar?",
]


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    questions = argv or QUESTIONS
    rp = agents.rag_pipeline
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        store_copy = Path(tmp) / "chroma_frozen_v2_runtime_copy"
        shutil.copytree(rp.BASELINE.store_dir, store_copy)
        rag = agents.RAGAgent.load(dataclasses.replace(rp.BASELINE, store_dir=store_copy))
        expert = agents.expert_agent.load_expert(rag, debug=print)
        try:
            for question in questions:
                print("=" * 78, f"\nTu: {question}")
                try:
                    print(f"Agente: {expert.respond(question)}")
                except agents.expert_agent.ExpertAgentError as exc:
                    print(f"Agente: [erro] {exc}")
        finally:
            expert.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
