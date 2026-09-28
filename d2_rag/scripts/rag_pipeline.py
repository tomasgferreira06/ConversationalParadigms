"""Unified RAG pipeline over the 32-document corpus (no CLI, no printing).

chunks.jsonl -> content chunks -> Chroma (HuggingFace embeddings) -> top-k
retrieval -> context and prompt -> Ollama answer, plus source formatting.
Every experimental setting, including the vector store it owns, is in a
RAGConfig; BASELINE is the configuration of the interactive baseline
(rag_baseline.py). Retrieval can be run without the LLM, and prompts built
without Chroma.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from corpus import CHUNKS_PATH, DATA_DIR, read_jsonl


@dataclass(frozen=True)
class RAGConfig:
    embedding_model: str
    # Name of a prompt defined by the embedding model itself (its
    # SentenceTransformer config), applied to queries only; None for models
    # that embed queries and documents the same way.
    query_prompt_name: str | None
    collection_name: str
    store_dir: Path
    distance_space: str
    top_k: int
    llm_model: str
    llm_temperature: float
    indexed_roles: frozenset[str]


# ---- TEMPORARY BASELINE / TO BE EVALUATED -----------------------------------
# The first smoke test's store (data/chroma_smoke) is historical and never opened.

# V0: first unified baseline (RAG_BASELINE_SMOKE_TEST.md). Kept as a diagnostic
# reference; its store is never rebuilt by the CLI.
BASELINE_V0 = RAGConfig(
    embedding_model="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",  # 768-d
    query_prompt_name=None,
    collection_name="coimbra_rag_baseline",
    store_dir=DATA_DIR / "chroma_baseline",
    distance_space="cosine",
    top_k=3,
    llm_model="llama3.2:3b",
    llm_temperature=0.1,
    indexed_roles=frozenset({"content"}),  # page_labels and caption_panel stay out of the index
)
# V1: the course RAG worksheet's embedding model, matching its 1000/100-char
# chunking (RAG_BASELINE_V1_SMOKE_TEST.md). Only the embedding model and the
# store identity differ from V0.
BASELINE_V1 = replace(
    BASELINE_V0,
    embedding_model="sentence-transformers/all-mpnet-base-v2",  # 768-d
    collection_name="coimbra_rag_baseline_v1",
    store_dir=DATA_DIR / "chroma_baseline_v1",
)
# V2: Qwen3 embedding, instruction-aware: queries get the model's own "query"
# prompt, documents are embedded as they are (RAG_BASELINE_V2_QWEN_SMOKE_TEST.md).
# Written out in full because the query prompt is model-specific.
BASELINE_V2 = RAGConfig(
    embedding_model="Qwen/Qwen3-Embedding-0.6B",  # 1024-d (native, no MRL truncation)
    query_prompt_name="query",
    collection_name="coimbra_rag_baseline_v2",
    store_dir=DATA_DIR / "chroma_baseline_v2",
    distance_space="cosine",
    top_k=3,
    llm_model="llama3.2:3b",
    llm_temperature=0.1,
    indexed_roles=frozenset({"content"}),
)
BASELINE = BASELINE_V2
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
    return read_jsonl(path)


def select_indexable(
    chunks: list[dict[str, Any]], config: RAGConfig = BASELINE
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Content chunks to index, and a count of the excluded roles."""

    kept = [c for c in chunks if c["unit_role"] in config.indexed_roles]
    excluded: dict[str, int] = {}
    for chunk in chunks:
        if chunk["unit_role"] not in config.indexed_roles:
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


def load_embeddings(config: RAGConfig = BASELINE) -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    encode_kwargs = {"normalize_embeddings": True}
    extra = {}
    if config.query_prompt_name:
        # embed_query uses these instead of encode_kwargs; documents never get the prompt.
        extra["query_encode_kwargs"] = {**encode_kwargs, "prompt_name": config.query_prompt_name}
    try:
        return HuggingFaceEmbeddings(model_name=config.embedding_model, encode_kwargs=encode_kwargs, **extra)
    except Exception as exc:
        raise BaselineError(f"[embeddings] could not load {config.embedding_model}: {exc}") from exc


def _chroma(embeddings: Embeddings, store_dir: Path, config: RAGConfig):
    import chromadb
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=config.collection_name,
        embedding_function=embeddings,
        persist_directory=str(store_dir),
        collection_configuration={"hnsw": {"space": config.distance_space}},
        client_settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


def build_store(
    chunks: list[dict[str, Any]], embeddings: Embeddings, store_dir: Path | None = None,
    config: RAGConfig = BASELINE,
):
    """Delete and rebuild the store (default: config.store_dir); returns (store, report)."""

    store_dir = config.store_dir if store_dir is None else store_dir
    indexable, excluded = select_indexable(chunks, config)
    ids = [c["chunk_id"] for c in indexable]
    if len(ids) != len(set(ids)):
        raise BaselineError("[build] duplicate chunk_id among indexable chunks")
    if store_dir.exists():
        shutil.rmtree(store_dir)
    store = _chroma(embeddings, store_dir, config)
    store.add_documents([to_document(c) for c in indexable], ids=ids)
    report = {
        "input_chunks": len(chunks),
        "indexed_chunks": len(indexable),
        "excluded": excluded,
        # langchain_chroma has no public count; the collection is the documented escape hatch.
        "collection_count": store._collection.count(),
    }
    stored_ids = set(store._collection.get(include=[])["ids"])
    if report["collection_count"] != len(indexable) or stored_ids != set(ids):
        raise BaselineError(f"[build] collection does not match the indexed chunks: {report}")
    return store, report


def open_store(embeddings: Embeddings, store_dir: Path | None = None, config: RAGConfig = BASELINE):
    store_dir = config.store_dir if store_dir is None else store_dir
    if not (store_dir / "chroma.sqlite3").exists():
        raise BaselineError("Baseline vector store not found. Run with --rebuild.")
    store = _chroma(embeddings, store_dir, config)
    if store._collection.count() == 0:
        raise BaselineError("Baseline vector store is empty. Run with --rebuild.")
    return store


# ---------------------------------------------------------------------------
# Retrieval, context, prompt
# ---------------------------------------------------------------------------


def retrieve(store, question: str, k: int = BASELINE.top_k) -> list[tuple[Document, float]]:
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


def check_ollama(model: str = BASELINE.llm_model) -> None:
    import ollama

    try:
        installed = {m.model for m in ollama.list().models}
    except Exception as exc:
        raise BaselineError(f"[ollama] Ollama is not reachable ({exc}). Start Ollama and retry.") from exc
    if model not in installed:
        raise BaselineError(f"[ollama] model {model!r} is not installed. Run: ollama pull {model}")


def generate(messages: list[BaseMessage], config: RAGConfig = BASELINE) -> str:
    from langchain_ollama import ChatOllama

    return ChatOllama(model=config.llm_model, temperature=config.llm_temperature).invoke(messages).content
