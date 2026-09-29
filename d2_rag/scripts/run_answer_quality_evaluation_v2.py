"""Run the frozen V2 answer-quality evaluation (20 No-RAG + 20 RAG).

Generation is deliberately separate from scoring. This script extracts only
question IDs and question text, generates all 40 answers, and writes an
unscored, immutable raw-results file. It never rebuilds a vector store.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
import shutil
import sys
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from rag_pipeline import (
    FROZEN_V2,
    BaselineError,
    build_messages,
    check_ollama,
    generate,
    load_embeddings,
    open_store,
    retrieve,
    section_label,
)


ROOT = Path(__file__).resolve().parents[2]
EVALUATION_SET = ROOT / "d2_rag" / "D2_ANSWER_QUALITY_EVALUATION_SET_V2.md"
RAW_RESULTS = ROOT / "d2_rag" / "evaluation" / "d2_rag_vs_no_rag_v2_raw_results.json"
RUNTIME_STORE = ROOT / "d2_rag" / "data" / "chroma_eval_v2_runtime"

NO_RAG_SYSTEM_PROMPT = (
    "És um assistente especializado em turismo, história, património, cultura e gastronomia de Coimbra.\n"
    "Responde em Português de Portugal, de forma clara, direta e concisa.\n"
    "Não inventes informação. Se não tiveres conhecimento suficiente para responder com segurança, diz que não sabes."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(path: Path) -> dict[str, object]:
    """Stable digest of file paths and contents below a path."""

    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    total_bytes = 0
    for file_path in files:
        relative = file_path.name if path.is_file() else file_path.relative_to(path).as_posix()
        file_hash = sha256_file(file_path)
        size = file_path.stat().st_size
        total_bytes += size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return {"sha256": digest.hexdigest(), "files": len(files), "bytes": total_bytes}


def integrity_snapshot() -> dict[str, dict[str, object]]:
    targets = {
        "evaluation_set_v2": EVALUATION_SET,
        "corpus_raw": ROOT / "d2_rag" / "data" / "raw",
        "corpus_processed": ROOT / "d2_rag" / "data" / "processed",
        "chunks": ROOT / "d2_rag" / "data" / "chunks",
        "manifest": ROOT / "d2_rag" / "data" / "manifest.jsonl",
        "chroma_frozen_v2_original": ROOT / "d2_rag" / "data" / "chroma_frozen_v2",
        "rag_pipeline": ROOT / "d2_rag" / "scripts" / "rag_pipeline.py",
        "rag_baseline": ROOT / "d2_rag" / "scripts" / "rag_baseline.py",
        "integration": ROOT / "integration",
    }
    return {name: tree_digest(path) for name, path in targets.items()}


def parse_questions(path: Path = EVALUATION_SET) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^### (Q\d{2})\s*$", text)[1:]
    questions = []
    for question_id, body in zip(blocks[0::2], blocks[1::2], strict=True):
        match = re.search(r"(?m)^\*\*Question:\*\* (.+)$", body)
        if not match:
            raise ValueError(f"Missing Question field for {question_id}")
        questions.append({"question_id": question_id, "question": match.group(1).strip()})
    if [q["question_id"] for q in questions] != [f"Q{i:02d}" for i in range(1, 21)]:
        raise ValueError("The evaluation set must contain Q01-Q20 exactly once and in order")
    return questions


def config_record(config) -> dict[str, object]:
    record = asdict(config)
    record["store_dir"] = str(record["store_dir"])
    record["indexed_roles"] = sorted(record["indexed_roles"])
    return record


def invoke_no_rag(question: str) -> str:
    llm = ChatOllama(model=FROZEN_V2.llm_model, temperature=FROZEN_V2.llm_temperature)
    response = llm.invoke([
        SystemMessage(content=NO_RAG_SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]).content
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("No-RAG generation returned an empty response")
    return response


def retrieved_record(results) -> list[dict[str, object]]:
    records = []
    for document, distance in results:
        metadata = document.metadata
        records.append({
            "chunk_id": metadata.get("chunk_id"),
            "document_id": metadata.get("document_id"),
            "section": section_label(metadata),
            "distance": float(distance),
        })
    return records


def validate_only() -> None:
    questions = parse_questions()
    if len(questions) != 20:
        raise ValueError("Expected 20 questions")
    if FROZEN_V2.collection_name != "coimbra_rag_frozen_v2":
        raise ValueError("Unexpected frozen collection")
    if FROZEN_V2.top_k != 3 or FROZEN_V2.llm_model != "llama3.2:3b" or FROZEN_V2.llm_temperature != 0.1:
        raise ValueError("Unexpected frozen generation settings")
    if not (FROZEN_V2.store_dir / "chroma.sqlite3").is_file():
        raise ValueError("Frozen V2 store is missing")
    print("VALIDATION OK: 20 questions; FROZEN_V2; top_k=3; llama3.2:3b; temperature=0.1")


def run() -> None:
    if RAW_RESULTS.exists():
        raise FileExistsError(f"Refusing to overwrite frozen raw results: {RAW_RESULTS}")
    if RUNTIME_STORE.exists():
        raise FileExistsError(f"Runtime store already exists: {RUNTIME_STORE}")

    questions = parse_questions()
    before = integrity_snapshot()
    check_ollama(FROZEN_V2.llm_model)

    retry_log: list[dict[str, object]] = []
    generated = {
        item["question_id"]: {
            "question_id": item["question_id"],
            "question": item["question"],
            "no_rag": {},
            "rag": {},
        }
        for item in questions
    }

    # Phase A1: all No-RAG answers, with no corpus or retrieval access.
    for index, item in enumerate(questions, start=1):
        generated[item["question_id"]]["no_rag"]["answer"] = invoke_no_rag(item["question"])
        print(f"[{index:02d}/20] NO-RAG done", flush=True)

    # Phase A2: copy and query the exact frozen store. Never open the original.
    shutil.copytree(FROZEN_V2.store_dir, RUNTIME_STORE)
    runtime_config = replace(FROZEN_V2, store_dir=RUNTIME_STORE)
    store = None
    try:
        embeddings = load_embeddings(runtime_config)
        store = open_store(embeddings, config=runtime_config)
        collection_count = store._collection.count()
        if collection_count != 348:
            raise BaselineError(f"Runtime collection has {collection_count} chunks; expected 348")
        for index, item in enumerate(questions, start=1):
            results = retrieve(store, item["question"], k=runtime_config.top_k)
            answer = generate(build_messages(item["question"], results), runtime_config)
            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError(f"RAG generation returned an empty response for {item['question_id']}")
            generated[item["question_id"]]["rag"] = {
                "answer": answer,
                "retrieved_chunks": retrieved_record(results),
            }
            print(f"[{index:02d}/20] RAG done", flush=True)
    finally:
        store = None
        gc.collect()

    after = integrity_snapshot()
    changed = [key for key in before if before[key] != after[key]]
    if changed:
        raise RuntimeError(f"Protected inputs changed during generation: {changed}")

    payload = {
        "evaluation": "D2 RAG vs No-RAG Answer Quality V2",
        "phase": "generation_complete_unscored",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": FROZEN_V2.llm_model,
        "temperature": FROZEN_V2.llm_temperature,
        "generation_count_per_question_and_condition": 1,
        "no_rag_system_prompt": NO_RAG_SYSTEM_PROMPT,
        "rag_system_prompt": __import__("rag_pipeline").SYSTEM_PROMPT,
        "rag_config": config_record(FROZEN_V2),
        "runtime_store": {
            "path": str(RUNTIME_STORE),
            "copied_from": str(FROZEN_V2.store_dir),
            "collection_count": 348,
            "rebuilt": False,
        },
        "technical_retries": retry_log,
        "integrity_before": before,
        "integrity_after_generation": after,
        "results": [generated[item["question_id"]] for item in questions],
    }
    RAW_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RAW_RESULTS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RAW RESULTS FROZEN: {RAW_RESULTS}", flush=True)
    print(f"RAW RESULTS SHA256: {sha256_file(RAW_RESULTS)}", flush=True)

    try:
        shutil.rmtree(RUNTIME_STORE)
        print("Runtime store removed", flush=True)
    except OSError as exc:
        print(f"WARNING: runtime store retained because cleanup failed: {exc}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.validate_only:
            validate_only()
        else:
            run()
    except (BaselineError, FileExistsError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
