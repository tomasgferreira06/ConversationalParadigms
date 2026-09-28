"""Unified RAG baseline: interactive smoke test over the 32-document corpus.

Not a formal evaluation. Builds a Chroma index of the content chunks in
data/chunks/chunks.jsonl, then answers independent questions with visible
retrieval, context, answer and sources.

Usage:
    uv run python d2_rag/scripts/rag_baseline.py --rebuild
    uv run python d2_rag/scripts/rag_baseline.py                         # interactive
    uv run python d2_rag/scripts/rag_baseline.py --question "..."
    uv run python d2_rag/scripts/rag_baseline.py --question "..." --retrieval-only
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage


D2_ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = D2_ROOT / "data" / "chunks" / "chunks.jsonl"
# The first smoke test's store (data/chroma_smoke) is historical and never opened.
STORE_DIR = D2_ROOT / "data" / "chroma_baseline"

# ---- TEMPORARY BASELINE / TO BE EVALUATED -----------------------------------
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # 768-d
COLLECTION_NAME = "coimbra_rag_baseline"
DISTANCE_SPACE = "cosine"
TOP_K = 3
LLM_MODEL = "llama3.2:3b"
LLM_TEMPERATURE = 0.1
INDEXED_ROLES = {"content"}  # page_labels and caption_panel stay out of the index
# -----------------------------------------------------------------------------

# Chroma 1.5 stores lists natively; None values are dropped, so absent = null.
METADATA_FIELDS = (
    "chunk_id", "document_id", "source_type", "title", "source_organization",
    "primary_category", "section", "subsection", "section_path", "source_page",
    "source_pages", "source_file", "url", "canonical_url", "unit_role",
    "unit_chunk_index", "unit_chunk_count", "conflict_notes",
)

INSUFFICIENT = "Não tenho informação suficiente no contexto disponível para responder com segurança."
SYSTEM_PROMPT = (
    "És um assistente especializado em turismo, história, património, cultura e gastronomia de Coimbra.\n"
    "Responde à pergunta utilizando apenas o contexto fornecido.\n"
    "Não uses conhecimento externo para preencher informação que não esteja no contexto.\n"
    "Se o contexto não for suficiente para responder com segurança, diz explicitamente:\n"
    f"\"{INSUFFICIENT}\"\n"
    "Se existirem fontes recuperadas que apresentam versões contraditórias do mesmo facto, não escolhas "
    "silenciosamente uma delas. Explica brevemente que existem formulações divergentes e identifica as fontes.\n"
    "Responde em Português de Portugal, de forma clara e concisa.\n"
    "Não inventes fontes."
)


class BaselineError(RuntimeError):
    """A pipeline step failed; the message says what to do."""


# ---------------------------------------------------------------------------
# Chunks and metadata
# ---------------------------------------------------------------------------


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def select_indexable(chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Content chunks to index, and a count of the excluded roles."""

    kept = [c for c in chunks if c["unit_role"] in INDEXED_ROLES]
    excluded: dict[str, int] = {}
    for chunk in chunks:
        if chunk["unit_role"] not in INDEXED_ROLES:
            excluded[chunk["unit_role"]] = excluded.get(chunk["unit_role"], 0) + 1
    return kept, excluded


def to_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
    """Chunk fields stored as Chroma metadata (only the text is embedded)."""

    meta = {}
    for key in METADATA_FIELDS:
        value = chunk.get(key)
        if value is None or value == []:
            continue
        meta[key] = value
    return meta


def to_document(chunk: dict[str, Any]) -> Document:
    return Document(page_content=chunk["text"], metadata=to_metadata(chunk), id=chunk["chunk_id"])


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------


def load_embeddings() -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    try:
        return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL, encode_kwargs={"normalize_embeddings": True})
    except Exception as exc:
        raise BaselineError(f"[embeddings] could not load {EMBEDDING_MODEL}: {exc}") from exc


def _chroma(embeddings: Embeddings, store_dir: Path):
    import chromadb
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(store_dir),
        collection_configuration={"hnsw": {"space": DISTANCE_SPACE}},
        client_settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


def build_store(chunks: list[dict[str, Any]], embeddings: Embeddings, store_dir: Path = STORE_DIR):
    """Delete and rebuild the baseline store from the chunks; returns (store, report)."""

    indexable, excluded = select_indexable(chunks)
    ids = [c["chunk_id"] for c in indexable]
    if len(ids) != len(set(ids)):
        raise BaselineError("[build] duplicate chunk_id among indexable chunks")
    if store_dir.exists():
        shutil.rmtree(store_dir)
    store = _chroma(embeddings, store_dir)
    store.add_documents([to_document(c) for c in indexable], ids=ids)
    report = {
        "input_chunks": len(chunks),
        "indexed_chunks": len(indexable),
        "excluded": excluded,
        "collection_count": store._collection.count(),
    }
    stored_ids = set(store._collection.get(include=[])["ids"])
    if report["collection_count"] != len(indexable) or stored_ids != set(ids):
        raise BaselineError(f"[build] collection does not match the indexed chunks: {report}")
    return store, report


def open_store(embeddings: Embeddings, store_dir: Path = STORE_DIR):
    if not (store_dir / "chroma.sqlite3").exists():
        raise BaselineError("Baseline vector store not found. Run with --rebuild.")
    store = _chroma(embeddings, store_dir)
    if store._collection.count() == 0:
        raise BaselineError("Baseline vector store is empty. Run with --rebuild.")
    return store


# ---------------------------------------------------------------------------
# Retrieval, context, prompt
# ---------------------------------------------------------------------------


def retrieve(store, question: str, k: int = TOP_K) -> list[tuple[Document, float]]:
    """(chunk, cosine distance) pairs, best first.

    With hnsw space 'cosine', similarity_search_with_score returns the cosine
    DISTANCE (lower = closer; cosine similarity = 1 - distance).
    """

    return store.similarity_search_with_score(question, k=k)


def location(meta: dict[str, Any]) -> str:
    if meta.get("source_type") == "pdf":
        pages = meta.get("source_pages") or []
        return "p. " + ", ".join(str(p) for p in pages)
    return meta.get("canonical_url") or meta.get("url") or ""


def section_label(meta: dict[str, Any]) -> str:
    path = meta.get("section_path") or []
    return " > ".join(path) if path else "(sem secção)"


def chunk_body(document: Document) -> str:
    """The chunk text without its heading context, for display."""

    text = document.page_content
    head, sep, body = text.partition("\n\n")
    return body if sep and head.startswith("#") else text


def build_context(results: list[tuple[Document, float]]) -> str:
    blocks = []
    for rank, (doc, _distance) in enumerate(results, start=1):
        meta = doc.metadata
        blocks.append(
            f"[Fonte {rank}]\n"
            f"Documento: {meta.get('title')} ({meta.get('document_id')})\n"
            f"Secção: {section_label(meta)}\n"
            f"{'Páginas' if meta.get('source_type') == 'pdf' else 'URL'}: {location(meta)}\n\n"
            f"{doc.page_content}"
        )
    return "\n\n".join(blocks)


def conflict_note(results: list[tuple[Document, float]]) -> str | None:
    """Curation metadata about known conflicts among the retrieved sources."""

    notes: list[tuple[int, str]] = []
    for rank, (doc, _distance) in enumerate(results, start=1):
        note = doc.metadata.get("conflict_notes")
        if note and note not in [n for _r, n in notes]:
            notes.append((rank, note))
    if not notes:
        return None
    lines = [f"- Fonte {rank}: {note}" for rank, note in notes]
    return (
        "[Metadados de curadoria sobre conflitos conhecidos entre fontes]\n"
        "Isto não é conteúdo das fontes. Se o contexto acima contiver versões divergentes, indica-o; "
        "se só uma versão estiver no contexto, não inventes a outra.\n" + "\n".join(lines)
    )


def build_messages(question: str, results: list[tuple[Document, float]]) -> list[BaseMessage]:
    user = f"CONTEXTO:\n\n{build_context(results)}\n\n"
    note = conflict_note(results)
    if note:
        user += f"{note}\n\n"
    user += f"PERGUNTA:\n\n{question}\n\nResponde apenas com base no contexto acima."
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user)]


def format_sources(results: list[tuple[Document, float]]) -> str:
    lines, seen = [], set()
    for doc, _distance in results:
        meta = doc.metadata
        key = (meta.get("document_id"), section_label(meta), location(meta))
        if key in seen:
            continue
        seen.add(key)
        where = location(meta).replace("p. ", "páginas ", 1) if meta.get("source_type") == "pdf" else location(meta)
        lines.append(f"- {meta.get('title')} [{meta.get('document_id')}] — {section_label(meta)} — {where}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------


def check_ollama(model: str = LLM_MODEL) -> None:
    import ollama

    try:
        installed = {m.model for m in ollama.list().models}
    except Exception as exc:
        raise BaselineError(f"[ollama] Ollama is not reachable ({exc}). Start Ollama and retry.") from exc
    if model not in installed:
        raise BaselineError(f"[ollama] model {model!r} is not installed. Run: ollama pull {model}")


def generate(messages: list[BaseMessage]) -> str:
    from langchain_ollama import ChatOllama

    return ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE).invoke(messages).content


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


RULE = "=" * 60


def section(title: str) -> None:
    print(f"\n{RULE}\n{title}\n{RULE}\n")


def print_retrieval(results: list[tuple[Document, float]]) -> None:
    section("RETRIEVED CHUNKS")
    for rank, (doc, distance) in enumerate(results, start=1):
        meta = doc.metadata
        print(f"Rank {rank}")
        print(f"Cosine distance: {distance:.4f}  (cosine similarity = 1 - distance = {1 - distance:.4f})")
        print(f"Chunk ID: {meta.get('chunk_id')}")
        print(f"Document: {meta.get('title')} [{meta.get('document_id')}]")
        print(f"Source type: {'PDF' if meta.get('source_type') == 'pdf' else 'Web'}")
        print(f"Section: {section_label(meta)}")
        print(f"{'Pages' if meta.get('source_type') == 'pdf' else 'URL'}: {location(meta)}")
        if meta.get("conflict_notes"):
            print(f"Known conflict (curation metadata): {meta['conflict_notes']}")
        print(f"\nText:\n{chunk_body(doc)}\n")
        print("-" * 60)


def answer_question(store, question: str, retrieval_only: bool, show_context: bool) -> None:
    section("QUESTION")
    print(question)
    results = retrieve(store, question)
    print_retrieval(results)
    if retrieval_only:
        return
    messages = build_messages(question, results)
    if show_context:
        section("CONTEXT (user message sent to the LLM)")
        print(messages[1].content)
    section("ANSWER")
    print(generate(messages))
    section("SOURCES")
    print(format_sources(results))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    # Piped stdin on Windows is decoded with the console code page (cp1252),
    # which garbles accented questions; a real console already yields Unicode.
    if hasattr(sys.stdin, "reconfigure") and not sys.stdin.isatty():
        sys.stdin.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Unified RAG baseline (interactive smoke test).")
    parser.add_argument("--rebuild", action="store_true", help="delete and rebuild the baseline vector store")
    parser.add_argument("--question", help="ask one question and exit")
    parser.add_argument("--retrieval-only", action="store_true", help="show retrieved chunks, do not call the LLM")
    parser.add_argument("--show-context", action="store_true", help="print the exact user message sent to the LLM")
    args = parser.parse_args(argv)

    try:
        if not args.retrieval_only and (args.question or not args.rebuild):
            check_ollama()  # fail before loading anything heavy
        embeddings = load_embeddings()
        if args.rebuild:
            store, report = build_store(load_chunks(), embeddings)
            section("VECTOR STORE BUILD")
            print(f"Expected input chunks: {report['input_chunks']}")
            print(f"Indexed chunks: {report['indexed_chunks']}")
            for role, count in sorted(report["excluded"].items()):
                print(f"Excluded {role}: {count}")
            print(f"Collection '{COLLECTION_NAME}' count: {report['collection_count']} ({STORE_DIR})")
            if not args.question:
                return 0
        else:
            store = open_store(embeddings)

        if args.question:
            answer_question(store, args.question, args.retrieval_only, args.show_context)
            return 0
        print("Coimbra RAG baseline (each question is independent; no chat history).")
        print("Type 'exit' to quit.")
        while True:
            try:
                question = input("\nQuestion> ").strip()
            except EOFError:
                break
            if question.lower() in {"exit", "quit", "sair"}:
                break
            if question:
                answer_question(store, question, args.retrieval_only, args.show_context)
    except BaselineError as exc:
        print(f"\nERROR {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
