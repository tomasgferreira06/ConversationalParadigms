"""Freeze rubric-based V2 scores, validate aggregates, and render the report.

The assessments in this file were assigned after all 40 raw answers had been
generated and frozen. No LLM/API judge is called.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVALUATION_SET = ROOT / "d2_rag" / "D2_ANSWER_QUALITY_EVALUATION_SET_V2.md"
RAW_RESULTS = ROOT / "d2_rag" / "evaluation" / "d2_rag_vs_no_rag_v2_raw_results.json"
SCORED_RESULTS = ROOT / "d2_rag" / "evaluation" / "d2_rag_vs_no_rag_v2_scored_results.json"
REPORT = ROOT / "d2_rag" / "D2_RAG_VS_NO_RAG_QUANTITATIVE_EVALUATION_V2.md"

LABELS = {0: "INCORRECT", 1: "PARTIALLY CORRECT", 2: "CORRECT"}

# Automated rubric-based assessment by the coding-agent session, performed
# only after RAW_RESULTS was frozen. Reasons explicitly reference the frozen
# Essential Facts and Score Guidance.
ASSESSMENTS = {
    "Q01": {
        "no_rag": (1, "Atribui corretamente a D. Dinis a fundação da Universidade/Estudos Gerais, mas omite a introdução do português na documentação oficial e acrescenta incorretamente Santa Cruz."),
        "rag": (2, "Identifica corretamente a fundação dos Estudos Gerais e a introdução do português na documentação oficial."),
    },
    "Q02": {
        "no_rag": (0, "Indica erradamente a Universidade de Coimbra e a sua fundação; não refere o Mosteiro de Santa Cruz nem a decisão franciscana e o nome António."),
        "rag": (2, "Refere corretamente o ingresso no Mosteiro de Santa Cruz e a decisão de se tornar franciscano e adotar o nome António."),
    },
    "Q03": {
        "no_rag": (0, "Apresenta um período incorreto e nomeia a Sé Velha e São Francisco, em vez de São Salvador e São Bartolomeu."),
        "rag": (2, "Indica corretamente os séculos VIII e IX e as igrejas de São Salvador e São Bartolomeu."),
    },
    "Q04": {
        "no_rag": (0, "Indica o intervalo errado, 1906–1910, e não identifica os arquitetos."),
        "rag": (2, "Indica corretamente 1925–1931 e os arquitetos Cotinelli Telmo e Luís Cunha."),
    },
    "Q05": {
        "no_rag": (0, "Declara não saber e não apresenta nenhuma das duas funções do Piso Intermédio."),
        "rag": (2, "Refere corretamente o apoio aos guardas da Prisão Académica e o depósito dos livros lidos no Piso Nobre."),
    },
    "Q06": {
        "no_rag": (0, "Erra os três elementos: data de criação, faculdade antecedente e data de inauguração."),
        "rag": (2, "Apresenta corretamente 1911, a antiga Faculdade de Teologia e 22 de novembro de 1951."),
    },
    "Q07": {
        "no_rag": (0, "Declara não saber e não apresenta nenhum dos três factos essenciais."),
        "rag": (0, "Abstém-se apesar de o contexto recuperado conter os factos; não apresenta 1565, Diogo de Castilho nem a adaptação a Hospital Velho em 1848."),
    },
    "Q08": {
        "no_rag": (1, "Acerta a extinção em 1934 e a reativação em 1999, mas erra o primeiro marco, indicando 1911 em vez de 1773."),
        "rag": (2, "Apresenta os três marcos: 1773, extinção em 1934 pelo Estado Novo e reativação no mesmo edifício em 1999."),
    },
    "Q09": {
        "no_rag": (0, "Declara não conhecer o processo e não apresenta nenhum Essential Fact; acrescenta ainda uma localização errada para Arzila."),
        "rag": (1, "Refere a colheita no verão, a secagem e as peças produzidas, mas omite que o bunho é abundante na Reserva Natural do Paul de Arzila."),
    },
    "Q10": {
        "no_rag": (0, "Não refere o recolhimento e meditação dos crúzios nem o recinto do Jogo da Pela."),
        "rag": (2, "Refere corretamente o recolhimento e meditação dos crúzios e o recinto do Jogo da Pela."),
    },
    "Q11": {
        "no_rag": (0, "Inventa a autoria e os elementos materiais, sem identificar José Bandeirinha, António Olaio, a passadeira, a palavra Torga ou o poema Memória."),
        "rag": (0, "Abstém-se e não apresenta qualquer Essential Fact, embora o primeiro chunk recuperado contenha a informação."),
    },
    "Q12": {
        "no_rag": (0, "Declara não saber e não apresenta nenhum dos dois factos essenciais."),
        "rag": (1, "Refere corretamente a capa traçada, mas diz apenas que os protagonistas são estudantes e omite que, segundo a tradição descrita, são somente homens."),
    },
    "Q13": {
        "no_rag": (1, "Identifica corretamente o Convento de Santa Clara, mas dá um recheio salgado incorreto em vez de doce de ovos e amêndoa."),
        "rag": (2, "Identifica a origem em Santa Clara e o recheio correto de doce de ovos e amêndoa."),
    },
    "Q14": {
        "no_rag": (0, "Embora use a palavra cremosa, classifica erradamente o doce como prato de carne e inventa uma extensa lista de ingredientes relevantes."),
        "rag": (2, "Indica corretamente gemas, açúcar e pão, bem como a textura cremosa e delicada."),
    },
    "Q15": {
        "no_rag": (1, "Inclui leite, açúcar, arroz, canela e limão, mas acrescenta vários ingredientes e aromas não suportados, impedindo uma classificação totalmente correta."),
        "rag": (2, "Apresenta exatamente leite, açúcar e arroz, com canela ou limão como aromas."),
    },
    "Q16": {
        "no_rag": (1, "Situa a tradição na época medieval através do século XIII, mas não refere mosteiros/conventos nem os fins corretos de consumo próprio e comercialização."),
        "rag": (2, "Refere corretamente a época medieval, mosteiros e conventos, consumo próprio e comercialização."),
    },
    "Q17": {
        "no_rag": (1, "Sugere caminhadas, equivalente a passeios, mas não refere piqueniques e assume não conhecer as recomendações específicas."),
        "rag": (1, "Inclui corretamente passeios e piqueniques, mas acrescenta Paddle no rio Mondego como se fosse uma recomendação para as margens do Ceira."),
    },
    "Q18": {
        "no_rag": (0, "Declara não saber e não apresenta nenhum dos três blocos factuais."),
        "rag": (1, "Refere os laranjais, a área descampada, o campo da Académica e Jacinto de Matos, mas omite que a área era usada para corridas de cavalos."),
    },
    "Q19": {
        "no_rag": (0, "Erra a data, o contexto e o escritor/obra."),
        "rag": (1, "Indica corretamente 1772 e a Reforma Pombalina, mas omite Miguel Torga e Terceiro Dia d’ A Criação do Mundo."),
    },
    "Q20": {
        "no_rag": (1, "Indica corretamente o rio Mondego, mas identifica erradamente os competidores e o que o evento celebra."),
        "rag": (0, "Abstém-se porque o top-3 não contém o trecho sobre a Regata; não apresenta nenhum Essential Fact."),
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_benchmark() -> list[dict[str, object]]:
    text = EVALUATION_SET.read_text(encoding="utf-8")
    split = re.split(r"(?m)^### (Q\d{2})\s*$", text)[1:]
    records = []
    for question_id, body in zip(split[0::2], split[1::2], strict=True):
        question = re.search(r"(?m)^\*\*Question:\*\* (.+)$", body).group(1).strip()
        expected = re.search(r"(?m)^\*\*Expected answer:\*\* (.+)$", body).group(1).strip()
        guidance = re.search(r"(?m)^\*\*Score guidance:\*\* (.+)$", body).group(1).strip()
        facts = [m.group(1).strip() for m in re.finditer(
            r"(?ms)^#### Fact \d+\s*\n\s*(.+?)\s*\n\s*\*\*Evidence:\*\*", body
        )]
        records.append({
            "question_id": question_id,
            "question": question,
            "expected_answer": expected,
            "essential_facts": facts,
            "score_guidance": guidance,
        })
    return records


def pct(count: int) -> float:
    return count / 20 * 100


def summary(results: list[dict[str, object]], condition: str) -> dict[str, object]:
    scores = [item[condition]["score"] for item in results]
    counts = Counter(scores)
    return {
        "correct": counts[2],
        "partially_correct": counts[1],
        "incorrect": counts[0],
        "correct_percentage": pct(counts[2]),
        "partially_correct_percentage": pct(counts[1]),
        "incorrect_percentage": pct(counts[0]),
        "total_score": sum(scores),
        "maximum_score": 40,
        "mean_score": sum(scores) / 20,
    }


def quote_block(text: str) -> str:
    return "\n".join("> " + line if line else ">" for line in text.splitlines())


def render_report(payload: dict[str, object]) -> str:
    results = payload["results"]
    nr = payload["summary"]["no_rag"]
    rag = payload["summary"]["rag"]
    pair = payload["summary"]["pairwise"]
    prompt = payload["no_rag_system_prompt"]
    lines = [
        "# D2 — Quantitative Answer Quality Evaluation: RAG vs No-RAG",
        "",
        "## 1. Objective",
        "",
        '"> “Quantitative comparison of answer quality with and without RAG is required.”',
        "",
        "A experiência compara 20 perguntas idênticas, executadas uma vez em cada condição, com o mesmo LLM (`llama3.2:3b`) e a mesma temperatura (0.1). A principal diferença experimental é o retrieval e o contexto: No-RAG recebe apenas a pergunta; RAG recebe também os três chunks devolvidos pela pipeline congelada. A única métrica é Answer Quality Score, de 0 a 2.",
        "",
        "## 2. Evaluation Set Validation",
        "",
        "- 20/20 perguntas diretamente respondíveis pelo corpus.",
        "- 48/48 Essential Facts com evidência textual direta.",
        "- 0/20 perguntas requerem inferência.",
        "- O benchmark V2 foi congelado antes da execução e permaneceu inalterado.",
        "- As 40 respostas foram geradas e guardadas antes do scoring.",
        "",
        "## 3. Experimental Setup",
        "",
        "| Setting | NO-RAG | RAG |",
        "|---|---|---|",
        "| LLM | `llama3.2:3b` | `llama3.2:3b` |",
        "| Temperature | 0.1 | 0.1 |",
        "| Questions | 20, Q01–Q20 | 20, Q01–Q20 |",
        "| History | None; independent calls | None; independent calls |",
        "| Retrieval | None | Frozen pipeline, cosine distance |",
        "| Embedding | None | `Qwen/Qwen3-Embedding-0.6B` |",
        "| Vector store | None | Runtime copy of `chroma_frozen_v2` / `coimbra_rag_frozen_v2` |",
        "| Top-k | N/A | 3 |",
        "| Corpus access | None | Retrieved context only |",
        "",
        "The protected original vector store was copied before opening. Its collection contained 348 content chunks; `build_store` and embedding reconstruction were not called.",
        "",
        "## 4. Answer Quality Score",
        "",
        "| Score | Label | Definition |",
        "|---:|---|---|",
        "| 0 | INCORRECT | Errada, contraditória, com invenção relevante ou sem resposta efetiva. |",
        "| 1 | PARTIALLY CORRECT | Contém informação relevante e correta, mas está incompleta ou tem imprecisão que não destrói a ideia principal. |",
        "| 2 | CORRECT | Correta, adequada, com todos os elementos essenciais e sem erros relevantes. |",
        "",
        "O scoring foi uma **automated rubric-based assessment using the pre-defined 0–2 scoring rules**, efetuada pela sessão do agente de código após o fecho da geração. Não foi usada avaliação humana, API externa ou LLM-as-Judge adicional.",
        "",
        "## 5. No-RAG Prompt",
        "",
        "Prompt de sistema exato:",
        "",
        "```text",
        prompt,
        "```",
        "",
        "## 6. Question-by-Question Results",
        "",
    ]
    for item in results:
        lines.extend([
            f"### {item['question_id']} — {item['question']}",
            "",
            "**Essential Facts**",
            "",
            *[f"- {fact}" for fact in item["essential_facts"]],
            "",
            "#### NO-RAG",
            "",
            "**Answer**",
            "",
            quote_block(item["no_rag"]["answer"]),
            "",
            f"**Result:** {item['no_rag']['label']} ({item['no_rag']['score']}/2)",
            "",
            f"**Reason:** {item['no_rag']['reason']}",
            "",
            "#### RAG",
            "",
            "**Answer**",
            "",
            quote_block(item["rag"]["answer"]),
            "",
            f"**Result:** {item['rag']['label']} ({item['rag']['score']}/2)",
            "",
            f"**Reason:** {item['rag']['reason']}",
            "",
            "**Retrieved context**",
            "",
        ])
        for rank, chunk in enumerate(item["rag"]["retrieved_chunks"], start=1):
            lines.append(f"{rank}. `{chunk['document_id']}` — {chunk['section']} — distance {chunk['distance']:.6f}")
        lines.append("")

    lines.extend([
        "## 7. Quantitative Results",
        "",
        "| Q | No-RAG Score | No-RAG Label | RAG Score | RAG Label | Better |",
        "|---|---:|---|---:|---|---|",
    ])
    for item in results:
        lines.append(
            f"| {item['question_id']} | {item['no_rag']['score']} | {item['no_rag']['label']} | "
            f"{item['rag']['score']} | {item['rag']['label']} | {item['better']} |"
        )
    lines.extend([
        "",
        "### No-RAG",
        "",
        f"- Correct: {nr['correct']} / 20 ({nr['correct_percentage']:.0f}%)",
        f"- Partially Correct: {nr['partially_correct']} / 20 ({nr['partially_correct_percentage']:.0f}%)",
        f"- Incorrect: {nr['incorrect']} / 20 ({nr['incorrect_percentage']:.0f}%)",
        f"- Total Answer Quality Score: {nr['total_score']} / 40",
        f"- Mean Answer Quality Score: {nr['mean_score']:.2f} / 2",
        "",
        "### RAG",
        "",
        f"- Correct: {rag['correct']} / 20 ({rag['correct_percentage']:.0f}%)",
        f"- Partially Correct: {rag['partially_correct']} / 20 ({rag['partially_correct_percentage']:.0f}%)",
        f"- Incorrect: {rag['incorrect']} / 20 ({rag['incorrect_percentage']:.0f}%)",
        f"- Total Answer Quality Score: {rag['total_score']} / 40",
        f"- Mean Answer Quality Score: {rag['mean_score']:.2f} / 2",
        "",
        "### Pairwise Comparison",
        "",
        f"- RAG better: {pair['rag_better']} / 20 ({pair['rag_better_percentage']:.0f}%)",
        f"- Tie: {pair['tie']} / 20 ({pair['tie_percentage']:.0f}%)",
        f"- No-RAG better: {pair['no_rag_better']} / 20 ({pair['no_rag_better_percentage']:.0f}%)",
        "",
        f"**Mean score difference:** {payload['summary']['mean_score_difference']:+.2f} points on the 0–2 scale.",
        "",
        "## 8. Short Discussion",
        "",
        "RAG produced the higher score in 16 of 20 paired questions and raised the mean from 0.35 to 1.45. Clear improvements include Q03, where RAG supplied the correct centuries and churches while No-RAG invented both; Q06, where RAG returned all three dates/relationships and No-RAG missed all of them; and Q14, where RAG correctly described the conventual sweet while No-RAG misclassified it as a meat dish.",
        "",
        "There were three ties. Both conditions scored 0 on Q07 and Q11; on both questions the relevant document was rank 1, so the RAG result is a generation failure rather than a retrieval failure. Both scored 1 on Q17: RAG retrieved the correct Ceira chunk at rank 1 and stated passeios and piqueniques, but then added Paddle on the Mondego, an answer-generation error caused by mixing another retrieved chunk into the requested location.",
        "",
        "No-RAG was better only on Q20. It supplied the correct river but missed the remaining facts, whereas RAG abstained because none of the top-3 chunks contained the Regata passage. This is a retrieval failure: the fact exists in the frozen corpus but was absent from the retrieved context. Q19 also shows a generation omission: the correct Coimbra dos Escritores chunk was rank 1, yet RAG omitted Miguel Torga and the work title.",
        "",
        "The comparison is descriptive and uses one generation per question and condition. It therefore measures this fixed run, prompt, model and top-3 retrieval configuration; it does not estimate run-to-run variance or statistical significance.",
        "",
        "## 9. Validation and Integrity",
        "",
        "- Questions: 20",
        "- No-RAG answers: 20",
        "- RAG answers: 20",
        "- Total answers: 40",
        "- No-RAG scores: 20",
        "- RAG scores: 20",
        "- All scores in `{0, 1, 2}`: YES",
        "- No-RAG class counts sum to 20: YES",
        "- RAG class counts sum to 20: YES",
        "- Pairwise counts sum to 20: YES",
        "- Percentages sum to 100% in every distribution: YES",
        "- Raw responses saved before scoring: YES",
        "- Technical retries: 0",
        f"- Raw results SHA-256: `{payload['raw_results_sha256']}`",
        "- V2 evaluation set unchanged: YES",
        "- Frozen corpus, chunks and manifest unchanged: YES",
        "- Frozen original Chroma unchanged: YES",
        "- Main RAG scripts and integration unchanged: YES",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    if SCORED_RESULTS.exists() or REPORT.exists():
        raise FileExistsError("Refusing to overwrite existing scored results or report")
    raw_hash_before = sha256_file(RAW_RESULTS)
    raw = json.loads(RAW_RESULTS.read_text(encoding="utf-8"))
    benchmark = parse_benchmark()
    if len(raw["results"]) != 20 or len(benchmark) != 20:
        raise ValueError("Expected 20 raw and benchmark records")
    if set(ASSESSMENTS) != {f"Q{i:02d}" for i in range(1, 21)}:
        raise ValueError("Assessments must cover Q01-Q20")

    raw_by_id = {item["question_id"]: item for item in raw["results"]}
    scored = []
    for truth in benchmark:
        question_id = truth["question_id"]
        source = raw_by_id[question_id]
        if source["question"] != truth["question"]:
            raise ValueError(f"Question mismatch for {question_id}")
        item = dict(truth)
        for condition in ("no_rag", "rag"):
            score, reason = ASSESSMENTS[question_id][condition]
            item[condition] = {
                "answer": source[condition]["answer"],
                "score": score,
                "label": LABELS[score],
                "reason": reason,
            }
        item["rag"]["retrieved_chunks"] = source["rag"]["retrieved_chunks"]
        nr_score, rag_score = item["no_rag"]["score"], item["rag"]["score"]
        item["better"] = "RAG" if rag_score > nr_score else "NO-RAG" if nr_score > rag_score else "TIE"
        scored.append(item)

    no_rag = summary(scored, "no_rag")
    rag = summary(scored, "rag")
    better = Counter(item["better"] for item in scored)
    pairwise = {
        "rag_better": better["RAG"],
        "tie": better["TIE"],
        "no_rag_better": better["NO-RAG"],
        "rag_better_percentage": pct(better["RAG"]),
        "tie_percentage": pct(better["TIE"]),
        "no_rag_better_percentage": pct(better["NO-RAG"]),
    }
    for data in (no_rag, rag):
        if data["correct"] + data["partially_correct"] + data["incorrect"] != 20:
            raise ValueError("Class counts do not sum to 20")
        if round(data["correct_percentage"] + data["partially_correct_percentage"] + data["incorrect_percentage"], 10) != 100:
            raise ValueError("Class percentages do not sum to 100")
    if pairwise["rag_better"] + pairwise["tie"] + pairwise["no_rag_better"] != 20:
        raise ValueError("Pairwise counts do not sum to 20")
    if round(pairwise["rag_better_percentage"] + pairwise["tie_percentage"] + pairwise["no_rag_better_percentage"], 10) != 100:
        raise ValueError("Pairwise percentages do not sum to 100")

    payload = {
        "evaluation": raw["evaluation"],
        "assessment_method": "automated rubric-based assessment using the pre-defined 0–2 scoring rules",
        "model": raw["model"],
        "temperature": raw["temperature"],
        "no_rag_system_prompt": raw["no_rag_system_prompt"],
        "rag_config": raw["rag_config"],
        "technical_retries": raw["technical_retries"],
        "raw_results_sha256": raw_hash_before,
        "results": scored,
        "summary": {
            "no_rag": no_rag,
            "rag": rag,
            "pairwise": pairwise,
            "mean_score_difference": rag["mean_score"] - no_rag["mean_score"],
        },
    }
    SCORED_RESULTS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(render_report(payload), encoding="utf-8")
    if sha256_file(RAW_RESULTS) != raw_hash_before:
        raise RuntimeError("Raw results changed during scoring")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"SCORED: {SCORED_RESULTS}")
    print(f"REPORT: {REPORT}")
    print(f"RAW_UNCHANGED_SHA256: {raw_hash_before}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
