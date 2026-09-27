"""Structure-aware chunking of the D2 processed corpus (PDF + Web).

Structure first, character splitting second: each processed Markdown is parsed
into semantic units (a heading and the content under it, carried across PDF
page markers). A unit that fits in CHUNK_SIZE is one chunk; a longer unit is
split with RecursiveCharacterTextSplitter inside the unit only, so overlap never
crosses a section boundary. Every chunk keeps its heading context and
provenance (PDF pages or Web URL). Nothing is embedded or indexed here.

Usage:
    uv run python d2_rag/scripts/chunk_documents.py
    uv run python d2_rag/scripts/chunk_documents.py --documents ID [ID ...]   # pilot / inspection
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preprocess_documents import ROUTE_DOCUMENT_IDS  # noqa: E402


D2_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = D2_ROOT / "data" / "manifest.jsonl"
CHUNKS_DIR = D2_ROOT / "data" / "chunks"

# ---- TEMPORARY BASELINE (course worksheet) / TO BE EVALUATED ----------------
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
# Paragraph, then line (lists/verse), then sentence, then word.
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
# -----------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6}) (.+)$")
PAGE_MARKER_RE = re.compile(r"^<!-- source_page: (\d+) -->$")
CAPTION_PANEL_MARKER = "<!-- caption_panel -->"
FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
# Printed page numbers / map index numbers (only in the UC brochure).
PAGE_NUMBER_LINE_RE = re.compile(r"^\d{1,3}( \d{1,3})*$")
# A PDF page of captions/labels: no heading, every line short and unpunctuated.
LABEL_LINE_MAX_CHARS = 60
# A run of text-less PDF pages this long is a graphic insert (map spread, title
# page) that separates editorial parts; a single text-less page is a
# full-page photograph inside the flow (UC brochure p12 sits inside section 1).
MIN_BLANK_PAGES_FOR_BREAK = 2
# In the municipal route PDFs page 2 is the editorial sidebar of the map page,
# a separate layout region (see PREPROCESSING_REPORT.md), not a continuation of
# the last numbered point of page 1.
SECTION_RESET_PAGES = {document_id: {2} for document_id in ROUTE_DOCUMENT_IDS}


@dataclass
class Block:
    text: str
    page: int | None


@dataclass
class Unit:
    """A heading path and the content blocks under it."""

    path: list[tuple[int, str]]  # (markdown level, heading text), top-down
    role: str = "content"  # content | caption_panel | page_labels
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Stats:
    page_number_lines_skipped: int = 0
    label_pages: list[int] = field(default_factory=list)
    section_resets: list[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def split_front_matter(markdown: str) -> tuple[dict[str, str], str]:
    markdown = markdown.replace("\r\n", "\n")
    match = FRONT_MATTER_RE.match(markdown)
    if not match:
        return {}, markdown
    meta = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        meta[key.strip()] = json.loads(value) if value.startswith('"') else value
    return meta, markdown[match.end():]


def _paragraphs(body: str) -> list[list[str]]:
    """Blank-line separated paragraphs, each as its list of lines."""

    paragraphs, current = [], []
    for line in body.split("\n"):
        if line.strip():
            current.append(line.rstrip())
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def _is_label_page(paragraphs: list[list[str]]) -> bool:
    lines = [l for p in paragraphs for l in p if not PAGE_NUMBER_LINE_RE.match(l)]
    if not lines or any(HEADING_RE.match(l) or l == CAPTION_PANEL_MARKER for l in lines):
        return False
    return all(len(l) <= LABEL_LINE_MAX_CHARS and not re.search(r"[.!?:;]$", l) for l in lines)


def _content_lines(paragraph: list[str], stats: Stats) -> list[str]:
    lines = [l for l in paragraph if not PAGE_NUMBER_LINE_RE.match(l)]
    stats.page_number_lines_skipped += len(paragraph) - len(lines)
    return lines


def parse_units(document_id: str, body: str, stats: Stats) -> list[Unit]:
    """Turn a processed Markdown body into semantic units."""

    # Group paragraphs by page (Web documents have a single page None).
    pages: list[tuple[int | None, list[list[str]]]] = [(None, [])]
    for paragraph in _paragraphs(body):
        marker = PAGE_MARKER_RE.match(paragraph[0]) if len(paragraph) == 1 else None
        if marker:
            pages.append((int(marker.group(1)), []))
        else:
            pages[-1][1].append(paragraph)

    units: list[Unit] = []
    path: list[tuple[int, str]] = []
    role = "content"
    current = Unit(path=[])
    units.append(current)
    resets = SECTION_RESET_PAGES.get(document_id, set())
    blank_run = 0

    for page, paragraphs in pages:
        if page is not None:
            has_text = any(not PAGE_NUMBER_LINE_RE.match(l) for p in paragraphs for l in p)
            if not has_text:
                stats.page_number_lines_skipped += sum(len(p) for p in paragraphs)
                blank_run += 1
                continue
            if page in resets or (blank_run >= MIN_BLANK_PAGES_FOR_BREAK and path):
                stats.section_resets.append(page)
                path, role = [], "content"
                current = Unit(path=[])
                units.append(current)
            blank_run = 0
        if page is not None and _is_label_page(paragraphs):
            stats.label_pages.append(page)
            labels = Unit(path=[], role="page_labels")
            for paragraph in paragraphs:
                lines = _content_lines(paragraph, stats)
                if lines:
                    labels.blocks.append(Block("\n".join(lines), page))
            units.append(labels)
            # The interrupted section continues after the label page.
            current = Unit(path=list(path), role=role)
            units.append(current)
            continue
        for paragraph in paragraphs:
            heading = HEADING_RE.match(paragraph[0]) if len(paragraph) == 1 else None
            if heading:
                level, text = len(heading.group(1)), heading.group(2).strip()
                if level == 1:
                    continue  # document title: metadata, not a section
                path = [(l, t) for l, t in path if l < level] + [(level, text)]
                role = "content"
                current = Unit(path=list(path))
                units.append(current)
                continue
            if paragraph == [CAPTION_PANEL_MARKER]:
                path, role = [], "caption_panel"
                current = Unit(path=[], role=role)
                units.append(current)
                continue
            lines = _content_lines(paragraph, stats)
            if lines:
                current.blocks.append(Block("\n".join(lines), page))
    return [u for u in units if u.blocks]


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=SEPARATORS,
        keep_separator="end",
        add_start_index=True,
    )


def _unit_body(unit: Unit) -> tuple[str, list[tuple[int, int, int | None]]]:
    """Body text plus (start, end, page) spans for page provenance."""

    parts, spans, offset = [], [], 0
    for block in unit.blocks:
        if parts:
            offset += 2  # "\n\n"
        spans.append((offset, offset + len(block.text), block.page))
        parts.append(block.text)
        offset += len(block.text)
    return "\n\n".join(parts), spans


def split_unit_body(text: str, splitter: RecursiveCharacterTextSplitter) -> list[tuple[int, str]]:
    """(start offset, piece) for one unit; the unit is never mixed with another.

    RecursiveCharacterTextSplitter does not merge the remainder of an oversized
    paragraph with the next paragraph, which leaves orphan fragments (e.g. a
    lone coordinates line). Adjacent pieces are therefore re-merged whenever the
    contiguous text from the first to the second still fits in CHUNK_SIZE.
    """

    if len(text) <= CHUNK_SIZE:
        return [(0, text)]
    pieces = [(d.metadata["start_index"], d.page_content) for d in splitter.create_documents([text])]
    merged: list[tuple[int, str]] = []
    for start, piece in pieces:
        if merged:
            prev_start, prev_piece = merged[-1]
            end = start + len(piece)
            if end - prev_start <= CHUNK_SIZE and start >= prev_start:
                merged[-1] = (prev_start, text[prev_start:end])
                continue
        merged.append((start, piece))
    return merged


def _pages_for(start: int, end: int, spans: list[tuple[int, int, int | None]]) -> list[int]:
    return sorted({p for s, e, p in spans if p is not None and s < end and e > start})


def heading_context(title: str, unit: Unit) -> str:
    return "\n".join([f"# {title}"] + [f"{'#' * level} {text}" for level, text in unit.path])


def chunk_document(record: dict[str, Any], markdown: str) -> tuple[list[dict[str, Any]], Stats]:
    stats = Stats()
    front, body = split_front_matter(markdown)
    if front and front.get("document_id") != record["document_id"]:
        raise ValueError(f"front matter document_id {front.get('document_id')} != manifest {record['document_id']}")
    is_pdf = record["source_type"] == "pdf"
    splitter = _splitter()
    chunks = []
    for unit in parse_units(record["document_id"], body, stats):
        text, spans = _unit_body(unit)
        pieces = split_unit_body(text, splitter)
        context = heading_context(record["title"], unit)
        headings = [t for _level, t in unit.path]
        previous_end = None
        for index, (start, piece) in enumerate(pieces):
            end = start + len(piece)
            overlap = max(0, previous_end - start) if previous_end is not None else 0
            previous_end = end
            pages = _pages_for(start, end, spans) if is_pdf else None
            chunks.append({
                "chunk_id": None,  # assigned below, in document order
                "document_id": record["document_id"],
                "source_type": record["source_type"],
                "title": record["title"],
                "source_organization": record["source_organization"],
                "primary_category": record["primary_category"],
                "language": record.get("language"),
                "section": headings[0] if headings else None,
                "subsection": headings[1] if len(headings) > 1 else None,
                "section_path": headings,
                "unit_role": unit.role,
                "source_pages": pages,
                "source_page": pages[0] if pages and len(pages) == 1 else None,
                "source_file": record.get("original_filename") if is_pdf else None,
                "url": None if is_pdf else record["url"],
                "canonical_url": None if is_pdf else record.get("canonical_url"),
                "conflict_notes": record.get("conflict_notes"),
                "unit_chunk_index": index,
                "unit_chunk_count": len(pieces),
                "overlap_chars": overlap,
                "body_chars": len(piece),
                "heading_context": context,
                "text": f"{context}\n\n{piece}",
            })
    for number, chunk in enumerate(chunks, start=1):
        chunk["chunk_id"] = f"{record['document_id']}::c{number:04d}"
    return chunks, stats


def load_records(document_ids: list[str] | None = None) -> list[dict[str, Any]]:
    records = [json.loads(l) for l in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    records = [r for r in records if r.get("status") == "accepted"]
    if document_ids:
        unknown = set(document_ids) - {r["document_id"] for r in records}
        if unknown:
            raise SystemExit(f"Unknown or non-accepted document_id(s): {sorted(unknown)}")
        records = [r for r in records if r["document_id"] in document_ids]
    return sorted(records, key=lambda r: r["document_id"])


def chunk_corpus(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_chunks, per_document = [], {}
    for record in records:
        markdown = (D2_ROOT / record["processed_path"]).read_text(encoding="utf-8")
        chunks, stats = chunk_document(record, markdown)
        all_chunks.extend(chunks)
        per_document[record["document_id"]] = {
            "chunks": len(chunks),
            "page_number_lines_skipped": stats.page_number_lines_skipped,
            "label_pages": stats.label_pages,
            "section_resets": stats.section_resets,
        }
    return all_chunks, per_document


# ---------------------------------------------------------------------------
# Validation and statistics
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ("chunk_id", "document_id", "source_type", "title", "primary_category", "source_organization")
WEB_TEMPLATE_RESIDUE = ("Agentes e profissionais", "© Página oficial", "turismo@cm-coimbra.pt", "Preparar visita")


def chunk_body(chunk: dict[str, Any]) -> str:
    return chunk["text"][len(chunk["heading_context"]) + 2:]


def validate_chunks(chunks: list[dict[str, Any]]) -> list[str]:
    """Return every violation of the chunk contract (empty list = valid)."""

    problems = []
    ids = [c["chunk_id"] for c in chunks]
    if len(ids) != len(set(ids)):
        problems.append("duplicate chunk_id")
    previous: dict[str, Any] | None = None
    for chunk in chunks:
        cid, body = chunk["chunk_id"], chunk_body(chunk)
        if not chunk["text"].startswith(chunk["heading_context"] + "\n\n"):
            problems.append(f"{cid}: text does not start with its heading context")
        if not body.strip():
            problems.append(f"{cid}: empty body")
        for key in REQUIRED_FIELDS:
            if not chunk.get(key):
                problems.append(f"{cid}: missing {key}")
        if not cid.startswith(chunk["document_id"] + "::"):
            problems.append(f"{cid}: chunk_id / document_id mismatch")
        if chunk["source_type"] == "pdf":
            if not chunk["source_pages"] or chunk["url"] is not None:
                problems.append(f"{cid}: PDF chunk needs source_pages and no url")
        else:
            if not chunk["url"] or chunk["source_pages"] is not None or chunk["source_page"] is not None:
                problems.append(f"{cid}: web chunk needs url and no pages")
        if "<!--" in chunk["text"] or re.search(r"(?m)^(---|document_id:|source_type:)", body):
            problems.append(f"{cid}: marker or front matter in text")
        if re.search(r"(?m)^#{1,6} ", body):
            problems.append(f"{cid}: heading inside body")
        if chunk["source_type"] == "web_page" and any(r in body for r in WEB_TEMPLATE_RESIDUE):
            problems.append(f"{cid}: web template residue")
        if chunk["overlap_chars"]:
            same_unit = (
                previous is not None
                and previous["document_id"] == chunk["document_id"]
                and previous["section_path"] == chunk["section_path"]
                and previous["unit_chunk_index"] == chunk["unit_chunk_index"] - 1
            )
            if not same_unit:
                problems.append(f"{cid}: overlap outside its semantic unit")
        previous = chunk
    return problems


def _percentiles(values: list[int]) -> dict[str, float]:
    ordered = sorted(values)

    def pct(q: float) -> float:
        position = (len(ordered) - 1) * q
        low, high = int(position), min(int(position) + 1, len(ordered) - 1)
        return round(ordered[low] + (ordered[high] - ordered[low]) * (position - low), 1)

    return {"min": ordered[0], "p25": pct(0.25), "median": pct(0.5),
            "mean": round(sum(ordered) / len(ordered), 1), "p75": pct(0.75), "max": ordered[-1]}


def _shingles(text: str, n: int = 5) -> set[tuple[str, ...]]:
    words = re.findall(r"[^\W_]+", text.lower())
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def duplicate_analysis(chunks: list[dict[str, Any]], threshold: float = 0.8) -> dict[str, Any]:
    """Exact and near duplicates of chunk bodies (reported, never removed)."""

    def scope(a: dict[str, Any], b: dict[str, Any]) -> str:
        if a["document_id"] == b["document_id"]:
            return "same_document"
        if a["source_type"] != b["source_type"]:
            return "pdf_web"
        return "cross_document_" + ("pdf" if a["source_type"] == "pdf" else "web")

    normalized: dict[str, list[str]] = {}
    for chunk in chunks:
        key = re.sub(r"\s+", " ", chunk_body(chunk).lower()).strip()
        normalized.setdefault(key, []).append(chunk["chunk_id"])
    exact = [ids for ids in normalized.values() if len(ids) > 1]

    by_id = {c["chunk_id"]: c for c in chunks}
    shingles = {c["chunk_id"]: _shingles(chunk_body(c)) for c in chunks}
    near = []
    ids = [c["chunk_id"] for c in chunks]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            sa, sb = shingles[a], shingles[b]
            if not sa or not sb:
                continue
            containment = len(sa & sb) / min(len(sa), len(sb))
            if containment >= threshold:
                near.append({"a": a, "b": b, "containment": round(containment, 3),
                             "scope": scope(by_id[a], by_id[b])})
    near.sort(key=lambda p: (-p["containment"], p["a"], p["b"]))
    scopes: dict[str, int] = {}
    for pair in near:
        scopes[pair["scope"]] = scopes.get(pair["scope"], 0) + 1
    return {"exact_duplicate_groups": exact, "near_duplicate_threshold": threshold,
            "near_duplicate_pairs_by_scope": scopes, "near_duplicate_pairs": near}


def corpus_stats(chunks: list[dict[str, Any]], per_document: dict[str, Any]) -> dict[str, Any]:
    def count(values):
        out: dict[str, int] = {}
        for v in values:
            out[str(v)] = out.get(str(v), 0) + 1
        return dict(sorted(out.items()))

    documents = {c["document_id"]: c["source_type"] for c in chunks}
    small = [c for c in chunks if c["body_chars"] < 100]
    large = [c for c in chunks if c["body_chars"] > CHUNK_SIZE]
    return {
        "config": {"chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP, "length_function": "len",
                   "separators": SEPARATORS, "status": "TEMPORARY BASELINE / TO BE EVALUATED"},
        "documents": {"total": len(documents), "pdf": sum(t == "pdf" for t in documents.values()),
                      "web_page": sum(t == "web_page" for t in documents.values())},
        "chunks": {"total": len(chunks), "pdf": sum(c["source_type"] == "pdf" for c in chunks),
                   "web_page": sum(c["source_type"] == "web_page" for c in chunks)},
        "chunks_per_document": {d: per_document[d]["chunks"] for d in sorted(per_document)},
        "chunks_per_category": count(c["primary_category"] for c in chunks),
        "chunks_per_unit_role": count(c["unit_role"] for c in chunks),
        "body_chars": _percentiles([c["body_chars"] for c in chunks]),
        "rendered_text_chars": _percentiles([len(c["text"]) for c in chunks]),
        "body_under_100_chars": len(small),
        "body_over_chunk_size": len(large),
        "rendered_over_chunk_size": sum(len(c["text"]) > CHUNK_SIZE for c in chunks),
        "split_units_chunks": sum(c["unit_chunk_count"] > 1 for c in chunks),
        "chunks_with_overlap": sum(c["overlap_chars"] > 0 for c in chunks),
        "multi_page_chunks": sum(bool(c["source_pages"]) and len(c["source_pages"]) > 1 for c in chunks),
        "chunks_without_section": sum(c["section"] is None for c in chunks),
        "chunks_with_subsection": sum(c["subsection"] is not None for c in chunks),
        "chunks_with_conflict_notes": sum(bool(c["conflict_notes"]) for c in chunks),
        "page_number_lines_skipped": sum(d["page_number_lines_skipped"] for d in per_document.values()),
        "label_pages": {d: v["label_pages"] for d, v in per_document.items() if v["label_pages"]},
        "section_resets": {d: v["section_resets"] for d, v in per_document.items() if v["section_resets"]},
        "small_chunks": [{"chunk_id": c["chunk_id"], "unit_role": c["unit_role"], "section": c["section"],
                          "body": chunk_body(c)} for c in small],
        "large_chunks": [{"chunk_id": c["chunk_id"], "body_chars": c["body_chars"]} for c in large],
        "duplicates": duplicate_analysis(chunks),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Structure-aware chunking of the processed corpus.")
    parser.add_argument("--documents", nargs="+", metavar="DOCUMENT_ID",
                        help="chunk only these documents and print them (no files written)")
    args = parser.parse_args(argv)

    records = load_records(args.documents)
    chunks, per_document = chunk_corpus(records)
    if args.documents:
        for chunk in chunks:
            print(json.dumps({k: v for k, v in chunk.items() if k not in ("text", "heading_context")}, ensure_ascii=False))
            print(chunk["text"], end="\n\n" + "-" * 80 + "\n")
        return 0

    problems = validate_chunks(chunks)
    if problems:
        for problem in problems:
            print(f"INVALID {problem}", file=sys.stderr)
        return 1
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    with (CHUNKS_DIR / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    stats = corpus_stats(chunks, per_document)
    (CHUNKS_DIR / "chunk_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    stale = CHUNKS_DIR / "chunk_documents.json"
    if stale.exists():
        stale.unlink()
    print(f"{len(records)} documents -> {len(chunks)} chunks (validated) -> {CHUNKS_DIR / 'chunks.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
