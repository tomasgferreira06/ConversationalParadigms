"""DEV check of the planner's capability selection (NOT a unit test, NOT the D3 evaluation).

Runs ONLY the real LLM planner (llama3.2:3b via Ollama): no RAG, no MCP, no final generation.
It compares the capabilities selected (RAG / Weather / Places) with the expected ones.

These 14 questions are a development set used for ONE prompt-refinement round. They must not be
reused in the D3 evaluation dataset, nor have been used in the planner prompt examples or in the
earlier smoke tests.

Usage:
    uv run python d3/coimbra_expert/dev_planner_check.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from planner import Planner, PlannerError  # noqa: E402

# (category, question, expected use_rag, expected weather, expected places)
DEV_SET = [
    ("RAG", "Quais são os doces conventuais típicos de Coimbra?", True, False, False),
    ("RAG", "Quem foi Inês de Castro e que ligação tem a Coimbra?", True, False, False),
    ("Weather", "Vai haver vento forte em Coimbra nos próximos dias?", False, True, False),
    ("Weather", "Está a chover neste momento em Aveiro?", False, True, False),
    ("Places", "Onde está situado o Mosteiro de Santa Cruz em Coimbra?", False, False, True),
    ("Places", "Quantos quilómetros separam o Museu da Ciência da estação Coimbra-B?", False, False, True),
    ("RAG+Weather", "Como vai estar o tempo hoje em Coimbra? Aproveito para perguntar o que é a Queima das Fitas.",
     True, True, False),
    ("RAG+Weather", "Vai estar frio nos próximos três dias em Coimbra? Fala-me também da tradição da capa e batina.",
     True, True, False),
    ("RAG+Places", "Onde fica o Museu da Ciência da Universidade de Coimbra e o que se pode ver lá?", True, False, True),
    ("RAG+Places", "Diz-me a localização do Convento de Santa Clara-a-Nova e conta-me a sua história.", True, False, True),
    ("Weather+Places", "Qual é a temperatura atual em Coimbra e onde fica o Estádio Cidade de Coimbra?",
     False, True, True),
    ("Weather+Places", "Como estará o tempo amanhã em Évora e qual é a distância entre a Sé de Évora e o Templo Romano?",
     False, True, True),
    ("RAG+Weather+Places",
     "Vai chover amanhã em Guimarães? Onde fica o Castelo de Guimarães e qual é a sua importância histórica?",
     True, True, True),
    ("RAG+Weather+Places",
     "Que tempo vai fazer amanhã em Coimbra, onde fica a Quinta das Lágrimas e qual é a sua história?",
     True, True, True),
]


def label(use_rag: bool, weather: bool, places: bool) -> str:
    parts = [name for name, on in (("RAG", use_rag), ("Weather", weather), ("Places", places)) if on]
    return "+".join(parts) or "(none)"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    planner = Planner()
    per_category: dict[str, list[bool]] = {}
    for category, question, use_rag, weather, places in DEV_SET:
        expected = label(use_rag, weather, places)
        try:
            plan = planner.plan(question)
            predicted = label(plan.use_rag, plan.call_for("weather") is not None, plan.call_for("places") is not None)
            detail = f'rag_query={plan.rag_query!r} calls={[(c.tool, c.arguments) for c in plan.tool_calls]}'
        except PlannerError as exc:
            predicted, detail = "(planner error)", str(exc)
        match = predicted == expected
        per_category.setdefault(category, []).append(match)
        print(f"[{'OK ' if match else 'BAD'}] {category:19s} expected={expected:22s} predicted={predicted}")
        print(f"      Q: {question}\n      {detail}")
    total = sum(sum(v) for v in per_category.values())
    print(f"\nExact Capability Match: {total}/{len(DEV_SET)}")
    for category, results in per_category.items():
        print(f"  {category:19s} {sum(results)}/{len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
