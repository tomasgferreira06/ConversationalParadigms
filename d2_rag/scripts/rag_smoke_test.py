"""End-to-end RAG smoke test for D2.

TEMPORARY BASELINE — not the final D2 architecture or configuration.
Its only goal is to prove that the pipeline works end-to-end:

    processed Markdown -> page Documents -> chunks -> embeddings -> Chroma
    -> top-k retrieval -> prompt -> Ollama LLM -> answer

Every configuration value below is a smoke-test baseline, to be evaluated later.

Usage:
    uv run python d2_rag/scripts/rag_smoke_test.py --rebuild
    uv run python d2_rag/scripts/rag_smoke_test.py --question "..."
    uv run python d2_rag/scripts/rag_smoke_test.py --rebuild --question "..."
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter


SCRIPT_PATH = Path(__file__).resolve()
D2_ROOT = SCRIPT_PATH.parents[1]
MANIFEST_PATH = D2_ROOT / "data" / "manifest.jsonl"
CHROMA_DIR = D2_ROOT / "data" / "chroma_smoke"  # generated artefact, git-ignored

# ---- TEMPORARY BASELINE / TO BE EVALUATED -----------------------------------
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
COLLECTION_NAME = "d2_rag_smoke"
DISTANCE_SPACE = "cosine"
TOP_K = 3
LLM_MODEL = "llama3.2:3b"
LLM_TEMPERATURE = 0.1
# -----------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
PAGE_MARKER_RE = re.compile(r"<!--\s*source_page:\s*(\d+)\s*-->")

SYSTEM_PROMPT = (
    "És um assistente especialista em turismo, história e cultura de Coimbra.\n"
    "Responde à pergunta utilizando apenas a informação fornecida no contexto.\n"
    "Se o contexto não contiver informação suficiente para responder com "
    "segurança, diz explicitamente que a informação disponível não é suficiente.\n"
    "Não inventes factos.\n"
    "Responde em Português de forma clara e concisa."
)


class SmokeTestError(RuntimeError):
    """A pipeline step failed; the message says which step and what to do."""


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    """Return the accepted manifest records, in manifest order."""
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if record.get("status") == "accepted":
                records.append(record)
    return records


def split_markdown_by_page(markdown: str) -> list[tuple[int, str]]:
    """Split a processed Markdown file into (source_page, text) units.

    The front matter and the title heading before the first page marker are
    dropped (they become metadata). The marker comments themselves are not
    kept in the text. Pages without text are skipped.
    """
    body = FRONTMATTER_RE.sub("", markdown.replace("\r\n", "\n"), count=1)
    parts = PAGE_MARKER_RE.split(body)
    # parts = [before_first_marker, page, text, page, text, ...]
    pages = []
    for page_str, text in zip(parts[1::2], parts[2::2]):
        text = text.strip()
        if text:
            pages.append((int(page_str), text))
    return pages


def load_processed_documents(
    manifest_path: Path = MANIFEST_PATH, d2_root: Path = D2_ROOT
) -> list[Document]:
    """Load every accepted processed Markdown as one Document per source page."""
    documents = []
    for record in load_manifest(manifest_path):
        path = d2_root / record["processed_path"]
        if not path.exists():
            raise SmokeTestError(
                f"[load] Processed file missing for {record['document_id']}: {path}"
            )
        for page, text in split_markdown_by_page(path.read_text(encoding="utf-8")):
            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "document_id": record["document_id"],
                        "title": record["title"],
                        "source_organization": record["source_organization"],
                        "source_file": record["original_filename"],
                        "source_page": page,
                    },
                )
            )
    return documents


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def split_documents(
    page_documents: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """Split each page separately so that no chunk crosses a page boundary."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunks = []
    for page_doc in page_documents:
        pieces = splitter.split_documents([page_doc])
        for index, piece in enumerate(p for p in pieces if p.page_content.strip()):
            meta = piece.metadata
            piece.metadata["chunk_id"] = (
                f"{meta['document_id']}::p{meta['source_page']}::c{index}"
            )
            chunks.append(piece)
    return chunks


# ---------------------------------------------------------------------------
# Embeddings / vector store
# ---------------------------------------------------------------------------


def load_embeddings(model_name: str = EMBEDDING_MODEL) -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    try:
        return HuggingFaceEmbeddings(
            model_name=model_name,
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception as exc:  # surfaced, never swallowed
        raise SmokeTestError(
            f"[embeddings] Could not load '{model_name}': {exc}"
        ) from exc


def _chroma(embeddings: Embeddings, persist_dir: Path):
    import chromadb
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
        collection_configuration={"hnsw": {"space": DISTANCE_SPACE}},
        client_settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


def build_vector_store(
    chunks: list[Document], embeddings: Embeddings, persist_dir: Path = CHROMA_DIR
):
    """Delete and rebuild the smoke-test Chroma collection from scratch."""
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
    store = _chroma(embeddings, persist_dir)
    store.add_documents(chunks, ids=[c.metadata["chunk_id"] for c in chunks])
    return store


def open_vector_store(embeddings: Embeddings, persist_dir: Path = CHROMA_DIR):
    if not persist_dir.exists():
        raise SmokeTestError(
            f"[chroma] No index at {persist_dir}. Run with --rebuild first."
        )
    store = _chroma(embeddings, persist_dir)
    if store._collection.count() == 0:
        raise SmokeTestError("[chroma] Collection is empty. Run with --rebuild.")
    return store


# ---------------------------------------------------------------------------
# Retrieval / generation
# ---------------------------------------------------------------------------


def retrieve(store, question: str, k: int = TOP_K) -> list[tuple[Document, float]]:
    """Return (chunk, cosine_distance) pairs, best first.

    With hnsw space 'cosine', Chroma's similarity_search_with_score returns the
    cosine DISTANCE (lower = more similar); cosine similarity = 1 - distance.
    """
    return store.similarity_search_with_score(question, k=k)


def build_context(results: list[tuple[Document, float]]) -> str:
    blocks = []
    for rank, (doc, _distance) in enumerate(results, start=1):
        meta = doc.metadata
        header = f"[{rank}] {meta['title']} (p. {meta['source_page']})"
        blocks.append(f"{header}\n{doc.page_content}")
    return "\n\n".join(blocks)


def build_prompt(context: str, question: str) -> list[BaseMessage]:
    return [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\nCONTEXTO:\n\n{context}"),
        HumanMessage(content=question),
    ]


def check_ollama_model(model: str = LLM_MODEL) -> None:
    """Fail loudly if Ollama is unreachable or the model is not pulled."""
    import ollama

    try:
        installed = {m.model for m in ollama.list().models}
    except Exception as exc:
        raise SmokeTestError(
            f"[ollama] Ollama server is not reachable ({exc}). "
            "Start Ollama (e.g. `ollama serve`) and retry."
        ) from exc
    if model not in installed:
        raise SmokeTestError(
            f"[ollama] Model '{model}' is not installed locally "
            f"(installed: {sorted(installed) or 'none'}). Run: ollama pull {model}"
        )


def generate_answer(messages: list[BaseMessage]) -> str:
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
    return llm.invoke(messages).content


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_section(name: str) -> None:
    print(f"\n===== {name} =====\n")


def print_config() -> None:
    print_section("CONFIGURATION (TEMPORARY BASELINE / TO BE EVALUATED)")
    print(f"embedding model : {EMBEDDING_MODEL}")
    print(f"chunking        : RecursiveCharacterTextSplitter, "
          f"chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP} (chars)")
    print(f"vector store    : Chroma @ {CHROMA_DIR} (collection '{COLLECTION_NAME}')")
    print(f"metric          : {DISTANCE_SPACE} (Chroma returns cosine distance)")
    print(f"top-k           : {TOP_K}")
    print(f"LLM             : Ollama {LLM_MODEL}, temperature={LLM_TEMPERATURE}")


def print_retrieval(results: list[tuple[Document, float]]) -> None:
    print_section("RETRIEVAL")
    for rank, (doc, distance) in enumerate(results, start=1):
        meta = doc.metadata
        print(f"Rank: {rank}")
        print(f"Cosine distance: {distance:.4f}  "
              f"(cosine similarity = 1 - distance = {1 - distance:.4f})")
        print(f"Document: {meta['document_id']} — {meta['title']}")
        print(f"Page: {meta['source_page']}")
        print(f"Chunk ID: {meta['chunk_id']}")
        print(f"\n{doc.page_content}\n")
        print("-" * 60)


def print_sources(results: list[tuple[Document, float]]) -> None:
    print_section("SOURCES")
    print("Fontes recuperadas:")
    seen = set()
    for doc, _distance in results:
        meta = doc.metadata
        key = (meta["document_id"], meta["source_page"])
        if key not in seen:
            seen.add(key)
            print(f"- {meta['title']} [{meta['document_id']}] — p. {meta['source_page']}")


def answer_question(store, question: str) -> str:
    print_section("QUESTION")
    print(question)
    results = retrieve(store, question)
    print_retrieval(results)
    context = build_context(results)
    print_section("CONTEXT")
    print(context)
    answer = generate_answer(build_prompt(context, question))
    print_section("ANSWER")
    print(answer)
    print_sources(results)
    return answer


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="D2 RAG smoke test (temporary baseline).")
    parser.add_argument("--rebuild", action="store_true",
                        help="delete and rebuild the Chroma index from processed Markdown")
    parser.add_argument("--question", action="append", default=[],
                        help="question to ask (repeatable)")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _build_parser().parse_args(argv)
    if not args.rebuild and not args.question:
        _build_parser().print_help()
        return 1

    try:
        print_config()
        if args.question:
            check_ollama_model()  # fail before loading anything heavy
        embeddings = load_embeddings()

        if args.rebuild:
            pages = load_processed_documents()
            chunks = split_documents(pages)
            store = build_vector_store(chunks, embeddings)
            print_section("INDEX")
            print(f"documents loaded : {len({p.metadata['document_id'] for p in pages})}")
            print(f"page units       : {len(pages)}")
            print(f"chunks created   : {len(chunks)}")
            print(f"chroma count     : {store._collection.count()}")
        else:
            store = open_vector_store(embeddings)

        for question in args.question:
            answer_question(store, question)
    except SmokeTestError as exc:
        print(f"\nERROR {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
