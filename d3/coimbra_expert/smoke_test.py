"""Manual smoke test of the Coimbra Expert Agent (NOT a unit test, NOT the D3 evaluation).

Real Ollama (llama3.2:3b), real embeddings, a RUNTIME COPY of the frozen Chroma store
(the protected store is never opened) and the real Weather MCP + Open-Meteo and Places MCP +
Nominatim. The capabilities are never given: the planner decides. These questions are smoke
tests only and must not be reused in the D3 evaluation dataset.

Usage:
    uv run python d3/coimbra_expert/smoke_test.py [question ...]
"""

import dataclasses
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "integration"))

import agents  # noqa: E402  (sets up the sys.path of D1, D2 and D3)

QUESTIONS = [
    "Para que servia originalmente o Jardim da Sereia?",
    "Qual é a temperatura atual em Coimbra?",
    "Onde fica a Sé Velha de Coimbra?",
    "Qual é a distância em linha reta entre a Sé Velha de Coimbra e o Jardim Botânico da Universidade de Coimbra?",
    "Qual é a previsão para amanhã em Coimbra e para que servia o Jardim da Sereia?",
    "Onde fica a Sé Velha de Coimbra e o que caracteriza a sua importância no património da cidade?",
    "Que tempo está agora em Coimbra e onde fica a Sé Velha?",
    "Qual é a previsão para amanhã em Coimbra, onde fica a Sé Velha e fala-me brevemente sobre ela.",
]


def _call(server: str, tool: str, **arguments) -> dict:
    return {"server": server, "tool": tool, "arguments": arguments}


_SE = _call("places", "search_place", query="Sé Velha, Coimbra", country_code="pt")
_FORECAST = _call("weather", "get_weather_forecast", location="Coimbra, Portugal", days=2)
# `--scripted`: execution-path check ONLY. The plan is fixed here instead of coming from the LLM planner
# (it still goes through the real plan validation, the real MCP servers, the real RAG and the real final
# generation). It says nothing about whether the planner would choose these capabilities.
SCRIPTED = [
    (QUESTIONS[2], {"use_rag": False, "rag_query": None, "tool_calls": [_SE]}),
    (QUESTIONS[3], {"use_rag": False, "rag_query": None, "tool_calls": [_call(
        "places", "get_distance_between_places", origin="Sé Velha, Coimbra",
        destination="Jardim Botânico da Universidade de Coimbra", country_code="pt")]}),
    (QUESTIONS[5], {"use_rag": True, "rag_query": "Qual é a importância da Sé Velha de Coimbra no património da cidade?",
                    "tool_calls": [_SE]}),
    (QUESTIONS[6], {"use_rag": False, "rag_query": None, "tool_calls": [
        _call("weather", "get_current_weather", location="Coimbra, Portugal"), _SE]}),
    (QUESTIONS[7], {"use_rag": True, "rag_query": "Fala-me brevemente sobre a Sé Velha de Coimbra.",
                    "tool_calls": [_FORECAST, _SE]}),
]


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    scripted = "--scripted" in argv
    argv = [a for a in argv if a != "--scripted"]
    questions = argv or ([q for q, _ in SCRIPTED] if scripted else QUESTIONS)
    plans = dict(SCRIPTED) if scripted else {}
    rp = agents.rag_pipeline
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        store_copy = Path(tmp) / "chroma_frozen_v2_runtime_copy"
        shutil.copytree(rp.BASELINE.store_dir, store_copy)
        rag = agents.RAGAgent.load(dataclasses.replace(rp.BASELINE, store_dir=store_copy))
        expert = agents.expert_agent.load_expert(rag, debug=print)
        try:
            for question in questions:
                print("=" * 78, f"\nTu: {question}")
                if plans:  # execution-path check: a fixed plan, validated like any planner output
                    plan_text = json.dumps(plans[question])
                    expert.planner = agents.expert_agent.Planner(lambda _messages, text=plan_text: text)
                try:
                    print(f"Agente: {expert.respond(question)}")
                except agents.expert_agent.ExpertAgentError as exc:
                    print(f"Agente: [erro] {exc}")
        finally:
            expert.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
