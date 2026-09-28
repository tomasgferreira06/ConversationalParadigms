"""Unified RAG baseline: interactive smoke test over the frozen 35-document corpus.

Not a formal evaluation. Command-line interface to rag_pipeline with one of
its CONFIGS (--config, default frozen-v2; --rebuild only ever touches that
configuration's own store, never the historical BASELINE_V* stores): builds the
Chroma index of the content chunks in data/chunks/chunks.jsonl, then answers
independent questions with visible retrieval, context, answer and sources.

Usage:
    uv run python d2_rag/scripts/rag_baseline.py --config frozen-v0 --rebuild
    uv run python d2_rag/scripts/rag_baseline.py                         # interactive, frozen-v2
    uv run python d2_rag/scripts/rag_baseline.py --config frozen-v1 --question "..."
    uv run python d2_rag/scripts/rag_baseline.py --question "..." --retrieval-only
"""

from __future__ import annotations

import argparse
import sys

from langchain_core.documents import Document

from rag_pipeline import (
    CONFIGS,
    BaselineError,
    RAGConfig,
    build_messages,
    build_store,
    check_ollama,
    format_sources,
    generate,
    load_chunks,
    load_embeddings,
    location,
    open_store,
    retrieve,
    section_label,
)


RULE = "=" * 60


def print_section(title: str) -> None:
    print(f"\n{RULE}\n{title}\n{RULE}\n")


def chunk_body(document: Document) -> str:
    """The chunk text without its heading context, for display."""

    text = document.page_content
    head, sep, body = text.partition("\n\n")
    return body if sep and head.startswith("#") else text


def print_retrieval(results: list[tuple[Document, float]]) -> None:
    print_section("RETRIEVED CHUNKS")
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


def answer_question(store, question: str, retrieval_only: bool, show_context: bool, config: RAGConfig) -> None:
    print_section("QUESTION")
    print(question)
    results = retrieve(store, question, k=config.top_k)
    print_retrieval(results)
    if retrieval_only:
        return
    messages = build_messages(question, results)
    if show_context:
        print_section("CONTEXT (user message sent to the LLM)")
        print(messages[1].content)
    print_section("ANSWER")
    print(generate(messages, config))
    print_section("SOURCES")
    print(format_sources(results))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    # Piped stdin on Windows is decoded with the console code page (cp1252),
    # which garbles accented questions; a real console already yields Unicode.
    if hasattr(sys.stdin, "reconfigure") and not sys.stdin.isatty():
        sys.stdin.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Unified RAG baseline (interactive smoke test).")
    parser.add_argument("--config", choices=sorted(CONFIGS), default="frozen-v2",
                        help="retrieval configuration and the vector store it owns (default: frozen-v2)")
    parser.add_argument("--rebuild", action="store_true", help="delete and rebuild the selected configuration's vector store")
    parser.add_argument("--question", help="ask one question and exit")
    parser.add_argument("--retrieval-only", action="store_true", help="show retrieved chunks, do not call the LLM")
    parser.add_argument("--show-context", action="store_true", help="print the exact user message sent to the LLM")
    args = parser.parse_args(argv)
    config = CONFIGS[args.config]

    try:
        if not args.retrieval_only and (args.question or not args.rebuild):
            check_ollama(config.llm_model)  # fail before loading anything heavy
        embeddings = load_embeddings(config)
        if args.rebuild:
            store, report = build_store(load_chunks(), embeddings, config=config)
            print_section("VECTOR STORE BUILD")
            print(f"Expected input chunks: {report['input_chunks']}")
            print(f"Indexed chunks: {report['indexed_chunks']}")
            for role, count in sorted(report["excluded"].items()):
                print(f"Excluded {role}: {count}")
            print(f"Collection '{config.collection_name}' count: {report['collection_count']} ({config.store_dir})")
            if not args.question:
                return 0
        else:
            store = open_store(embeddings, config=config)

        if args.question:
            answer_question(store, args.question, args.retrieval_only, args.show_context, config)
            return 0
        print(f"Coimbra RAG baseline, {args.config} (each question is independent; no chat history).")
        print("Type 'exit' to quit.")
        while True:
            try:
                question = input("\nQuestion> ").strip()
            except EOFError:
                break
            if question.lower() in {"exit", "quit", "sair"}:
                break
            if question:
                answer_question(store, question, args.retrieval_only, args.show_context, config)
    except BaselineError as exc:
        print(f"\nERROR {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
