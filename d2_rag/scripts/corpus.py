"""Shared D2 corpus layout, file formats and I/O helpers.

Only what more than one pipeline stage relies on lives here: the data/ paths
that connect stages, JSONL and manifest I/O, content hashes, and the markers
that the PDF preprocessing writes and the chunker reads. Stage-specific rules
stay in their own scripts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


D2_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = D2_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "manifest.jsonl"
# Written by chunk_documents.py, read by the RAG pipeline.
CHUNKS_DIR = DATA_DIR / "chunks"
CHUNKS_PATH = CHUNKS_DIR / "chunks.jsonl"

# Municipal route leaflets: page 1 is a numbered route, page 2 a map with an
# editorial sidebar (see PREPROCESSING_REPORT.md). Preprocessing uses this to
# pick the route layout; chunking uses it to start a new region on page 2.
ROUTE_DOCUMENT_IDS = {
    "coimbra-para-os-pequenitos",
    "coimbra-dos-escritores",
    "fado-e-tradicoes-academicas",
    "fundacao-da-nacionalidade",
    "jardins-historicos",
    "viver-o-patrimonio-em-coimbra",
}

# Written by the PDF preprocessing before a route page's photo-caption panel;
# the chunker turns what follows into a separate caption_panel unit.
CAPTION_PANEL_MARKER = "<!-- caption_panel -->"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    """One JSON object per line, UTF-8 kept literal, LF line endings."""

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    """All manifest records in file order; fails on bad JSON or a missing/duplicate id."""

    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on manifest line {line_number}: {exc}") from exc
        document_id = record.get("document_id")
        if not document_id or document_id in seen_ids:
            raise ValueError(f"Missing or duplicate document_id on manifest line {line_number}")
        seen_ids.add(document_id)
        records.append(record)
    return records


def sha256_bytes(data: bytes) -> str:
    """Content hash in the manifest's "sha256:<hex>" format."""

    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"
