"""Deterministic PDF-to-Markdown preprocessing for the D2 knowledge base.

This module preserves source wording and page provenance. It does not perform
RAG chunking, summarization, translation, or any LLM-backed transformation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import pymupdf


LOGGER = logging.getLogger("preprocess_documents")
SCRIPT_PATH = Path(__file__).resolve()
D2_ROOT = SCRIPT_PATH.parents[1]
MANIFEST_PATH = D2_ROOT / "data" / "manifest.jsonl"

ROUTE_DOCUMENT_IDS = {
    "coimbra-para-os-pequenitos",
    "coimbra-dos-escritores",
    "fado-e-tradicoes-academicas",
    "fundacao-da-nacionalidade",
    "jardins-historicos",
    "viver-o-patrimonio-em-coimbra",
}

WEB_NOISE_TOKENS = (
    "keyboard_arrow_left",
    "chevron_left",
    "chevron_right",
    "fiber_manual_record",
    "format_list_bulleted",
    "shopping_cart",
    "arrow_forward_ios",
    "accessibility_new",
)

# Exact repairs only. Inferring word boundaries for arbitrary letter sequences
# would risk changing legitimate text.
SAFE_SPACED_LETTER_REPAIRS = {
    "c a s a d a l i v r a r i a": "casa da livraria",
    "b i b l i o t e c a j o a n i n a": "biblioteca joanina",
    "O b r a í m p a r e r e c o n h e c i d a": "Obra ímpar e reconhecida",
}


@dataclass(frozen=True)
class DocumentConfig:
    route_layout: bool = False
    web_print: bool = False
    horizontal_blocks: bool = False
    stop_after: str | None = None
    skip_content_pages: frozenset[int] = frozenset()
    section_headings: frozenset[str] = frozenset()


DOCUMENT_CONFIG: dict[str, DocumentConfig] = {
    document_id: DocumentConfig(route_layout=True)
    for document_id in ROUTE_DOCUMENT_IDS
}
DOCUMENT_CONFIG["biblioteca-joanina-uctour"] = DocumentConfig(
    web_print=True,
    stop_after="Programas que incluem este espaço",
    skip_content_pages=frozenset({1}),
    section_headings=frozenset(
        {"Biblioteca Joanina", "Piso Nobre", "Piso Intermédio", "Prisão Académica"}
    ),
)
DOCUMENT_CONFIG["universidade-alta-sofia-patrimonio-mundial"] = DocumentConfig(
    horizontal_blocks=True
)


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProcessingStats:
    document_id: str
    pages: int
    extracted_characters: int
    processed_characters: int
    headings: int
    warnings: list[str]

    @property
    def removed_percent(self) -> float:
        if not self.extracted_characters:
            return 0.0
        removed = self.extracted_characters - self.processed_characters
        # Markdown heading syntax can make the structured representation a few
        # characters longer even though no source content was added.
        return round(max(0.0, 100 * removed / self.extracted_characters), 2)


def normalize_whitespace(text: str) -> str:
    """Normalize mechanical whitespace without changing words or punctuation."""

    normalized_lines: list[str] = []
    text = unicodedata.normalize("NFC", text).replace("\u00a0", " ").replace("\u00ad", "")
    for line in text.splitlines():
        line = re.sub(r"[\t\v\f ]+", " ", line).strip()
        normalized_lines.append(line)
    return "\n".join(normalized_lines).strip()


def remove_web_navigation_noise(text: str) -> str:
    """Remove browser-print chrome and known UCTour navigation tokens."""

    cleaned = text
    for token in WEB_NOISE_TOKENS:
        cleaned = cleaned.replace(token, " ")
    cleaned = re.sub(r"[\ue000-\uf8ff]", "", cleaned)

    kept: list[str] = []
    for raw_line in cleaned.splitlines():
        line = normalize_whitespace(raw_line)
        if not line:
            kept.append("")
            continue
        if re.fullmatch(r"\d{2}/\d{2}/\d{2},\s+\d{2}:\d{2}\s+UnivCoimbra\s+-\s+UCTour", line):
            continue
        if re.match(r"^https?://visit\.uc\.pt/.*\s+\d+/\d+$", line):
            continue
        if line == "BILHETES":
            continue
        line = line.replace("BILHETES", " ")
        line = normalize_whitespace(line)
        if "Jardim Botânico" in line and "Palácio" in line:
            continue
        if line:
            kept.append(line)
    return _collapse_blank_lines(kept)


def repair_spaced_letter_artifacts(text: str) -> str:
    """Repair only explicitly reviewed, exact spaced-letter artefacts."""

    result = text
    for artifact, replacement in SAFE_SPACED_LETTER_REPAIRS.items():
        result = re.sub(re.escape(artifact), replacement, result, flags=re.IGNORECASE)
    return result


def detect_route_heading(line: str) -> tuple[int, str] | None:
    match = re.fullmatch(r"(\d{1,2})\.\s+(.+)", normalize_whitespace(line))
    if not match:
        return None
    title = match.group(2).strip()
    letters = [char for char in title if char.isalpha()]
    if not letters or sum(char.isupper() for char in letters) / len(letters) < 0.8:
        return None
    return int(match.group(1)), title


def reconstruct_paragraphs(lines: Iterable[str]) -> list[str]:
    """Join PDF line wraps while retaining explicit paragraph boundaries."""

    output: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if not paragraph:
            return
        joined = paragraph[0]
        for continuation in paragraph[1:]:
            if joined.endswith("-") and continuation[:1].islower():
                joined = joined[:-1] + continuation
            else:
                joined += " " + continuation
        output.append(normalize_whitespace(joined))
        paragraph.clear()

    for raw_line in lines:
        line = normalize_whitespace(raw_line)
        if not line:
            flush()
            if output and output[-1] != "":
                output.append("")
            continue
        paragraph.append(line)
    flush()
    while output and output[-1] == "":
        output.pop()
    return output


def _collapse_blank_lines(lines: Iterable[str]) -> str:
    output: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        output.append(line.rstrip())
        previous_blank = blank
    return "\n".join(output).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
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


def _route_first_page_text(page: pymupdf.Page) -> str:
    """Read the body of a municipal route page column by column."""

    body_blocks: list[tuple[int, float, str]] = []
    width, height = page.rect.width, page.rect.height
    for block in page.get_text("blocks", sort=False):
        x0, y0, x1, y1, text = block[:5]
        normalized_text = normalize_whitespace(text)
        if x0 < width * 0.25 or y0 < height * 0.12 or y1 > height * 0.96:
            continue
        if re.fullmatch(r"[\d\s]+", normalized_text):
            continue
        column = min(2, max(0, int((x0 - width * 0.25) / (width * 0.24))))
        body_blocks.append((column, y0, text.strip()))
    body_blocks.sort(key=lambda item: (item[0], item[1]))
    return "\n\n".join(text for _, _, text in body_blocks if text)


def _route_map_page_text(page: pymupdf.Page) -> str:
    """Keep the editorial sidebar on route maps, omitting scattered map labels."""

    width, height = page.rect.width, page.rect.height
    blocks: list[tuple[float, str]] = []
    for block in page.get_text("blocks", sort=False):
        x0, y0, _x1, _y1, text = block[:5]
        if x0 >= width * 0.79 and y0 >= height * 0.50 and text.strip():
            blocks.append((y0, text.strip()))
    blocks.sort(key=lambda item: item[0])
    first_body = next(
        (index for index, (_y, text) in enumerate(blocks) if len(normalize_whitespace(text)) >= 120),
        0,
    )
    start = max(0, first_body - 1)
    return "\n\n".join(text for _, text in blocks[start:])


def _horizontal_block_text(page: pymupdf.Page) -> str:
    """Extract horizontal text blocks and ignore decorative rotated typography."""

    blocks: list[tuple[float, float, str]] = []
    page_dict = page.get_text("dict", sort=False)
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines: list[str] = []
        for line in block.get("lines", []):
            direction = line.get("dir", (1.0, 0.0))
            if abs(direction[0] - 1.0) > 0.01 or abs(direction[1]) > 0.01:
                continue
            text = "".join(span.get("text", "") for span in line.get("spans", []))
            if text.strip():
                lines.append(text.rstrip())
        if lines:
            x0, y0, _x1, _y1 = block["bbox"]
            blocks.append((y0, x0, "\n".join(lines)))
    blocks.sort(key=lambda item: (item[0], item[1]))
    return "\n\n".join(text for _, _, text in blocks)


def extract_pdf_pages(pdf_path: Path, config: DocumentConfig) -> list[ExtractedPage]:
    try:
        document = pymupdf.open(pdf_path)
    except Exception as exc:
        raise RuntimeError(f"Unable to open PDF {pdf_path}: {exc}") from exc

    pages: list[ExtractedPage] = []
    try:
        for index, page in enumerate(document):
            warnings: list[str] = []
            if config.route_layout and index == 0:
                text = _route_first_page_text(page)
            elif config.route_layout and index == 1:
                text = _route_map_page_text(page)
            elif config.horizontal_blocks:
                text = _horizontal_block_text(page)
            else:
                text = page.get_text("text", sort=True)
            if config.route_layout and index == 1:
                warnings.append("Map labels omitted; editorial sidebar retained.")
            if text.strip() and re.fullmatch(r"[\d\s]+", text):
                text = ""
                warnings.append("Page contained only map/index numbers; no prose retained.")
            if not text.strip():
                warnings.append("Page contains no extractable text.")
            pages.append(ExtractedPage(index + 1, text, warnings))
    finally:
        document.close()
    return pages


def _repeated_edge_lines(pages: list[ExtractedPage]) -> set[str]:
    counts: dict[str, int] = {}
    for page in pages:
        nonempty = [normalize_whitespace(line) for line in page.text.splitlines() if line.strip()]
        for line in set(nonempty[:2] + nonempty[-2:]):
            if 3 <= len(line) <= 160:
                counts[line] = counts.get(line, 0) + 1
    threshold = max(2, (len(pages) * 3 + 4) // 5)
    return {line for line, count in counts.items() if count >= threshold}


def remove_repeated_headers_footers(text: str, repeated_lines: set[str]) -> str:
    return "\n".join(
        line for line in text.splitlines() if normalize_whitespace(line) not in repeated_lines
    )


def _is_general_heading(line: str) -> bool:
    line = normalize_whitespace(line)
    if not line or len(line) > 120 or line.endswith(('.', ',', ';', ':')):
        return False
    letters = [char for char in line if char.isalpha()]
    return len(letters) >= 3 and sum(char.isupper() for char in letters) / len(letters) >= 0.9


def _merge_wrapped_headings(lines: list[str]) -> list[str]:
    merged: list[str] = []
    index = 0
    while index < len(lines):
        line = normalize_whitespace(lines[index])
        if not line:
            merged.append("")
            index += 1
            continue
        is_heading = detect_route_heading(line) is not None or _is_general_heading(line)
        if is_heading:
            parts = [line]
            lookahead = index + 1
            while lookahead < len(lines):
                candidate = normalize_whitespace(lines[lookahead])
                if not candidate or not _is_general_heading(candidate):
                    break
                parts.append(candidate)
                lookahead += 1
            merged.append(" ".join(parts))
            index = lookahead
            continue
        merged.append(line)
        index += 1
    return merged


def _render_page_body(text: str, config: DocumentConfig) -> tuple[str, int]:
    text = repair_spaced_letter_artifacts(text)
    if config.web_print:
        text = remove_web_navigation_noise(text)
    else:
        text = normalize_whitespace(text)

    lines = _merge_wrapped_headings(text.splitlines())
    output: list[str] = []
    paragraph: list[str] = []
    heading_count = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            output.extend(reconstruct_paragraphs(paragraph))
            output.append("")
            paragraph = []

    for line in lines:
        line = normalize_whitespace(line)
        if not line:
            flush_paragraph()
            continue
        if re.fullmatch(
            r"(?:\d+\s+)?Coimbra,\s*Património Mundial(?:\s+\d+)?",
            line,
            flags=re.IGNORECASE,
        ):
            flush_paragraph()
            continue
        route_heading = detect_route_heading(line)
        if route_heading:
            flush_paragraph()
            number, title = route_heading
            output.extend([f"## {number}. {title}", ""])
            heading_count += 1
            continue
        coordinate = re.fullmatch(
            r"coordenadas\s*:\s*([+-]?\d+(?:\.\d+)?\s*,\s*[+-]?\d+(?:\.\d+)?)",
            line,
            flags=re.IGNORECASE,
        )
        if coordinate:
            flush_paragraph()
            output.extend([f"**Coordenadas:** {coordinate.group(1)}", ""])
            continue
        if line in config.section_headings or _is_general_heading(line):
            flush_paragraph()
            level = "##" if line in config.section_headings else "###"
            output.extend([f"{level} {line}", ""])
            heading_count += 1
            continue
        if re.match(r"^(?:[-•]|\d+[.)])\s+", line):
            flush_paragraph()
            output.extend([line, ""])
            continue
        paragraph.append(line)

    flush_paragraph()
    return _collapse_blank_lines(output), heading_count


def render_markdown(
    record: dict[str, Any], pages: list[ExtractedPage], config: DocumentConfig
) -> tuple[str, ProcessingStats]:
    repeated_lines = _repeated_edge_lines(pages) if len(pages) > 2 else set()
    content_parts = [
        "---",
        f"document_id: {json.dumps(record['document_id'], ensure_ascii=False)}",
        f"title: {json.dumps(record['title'], ensure_ascii=False)}",
        f"source_organization: {json.dumps(record['source_organization'], ensure_ascii=False)}",
        f"source_file: {json.dumps(record['original_filename'], ensure_ascii=False)}",
        f"language: {json.dumps(record['language'], ensure_ascii=False)}",
        "---",
        "",
        f"# {record['title']}",
    ]
    total_headings = 1
    all_warnings: list[str] = []
    processed_body_chars = 0
    stopped = False

    for page in pages:
        page_text = remove_repeated_headers_footers(page.text, repeated_lines)
        if page.page_number in config.skip_content_pages:
            page_text = ""
        elif config.stop_after and config.stop_after in page_text:
            page_text = page_text.split(config.stop_after, 1)[0]
            stopped = True
        elif stopped:
            page_text = ""
        body, headings = _render_page_body(page_text, config)
        total_headings += headings
        processed_body_chars += len(body)
        all_warnings.extend(f"page {page.page_number}: {warning}" for warning in page.warnings)
        content_parts.extend(["", f"<!-- source_page: {page.page_number} -->", ""])
        if body:
            content_parts.append(body)

    markdown = "\n".join(content_parts).rstrip() + "\n"
    stats = ProcessingStats(
        document_id=record["document_id"],
        pages=len(pages),
        extracted_characters=sum(len(page.text) for page in pages),
        processed_characters=processed_body_chars,
        headings=total_headings,
        warnings=all_warnings,
    )
    return markdown, stats


def validate_processed_document(markdown: str, expected_pages: int) -> None:
    if not markdown.strip():
        raise ValueError("Processed Markdown is empty")
    markers = re.findall(r"<!-- source_page: (\d+) -->", markdown)
    expected = [str(number) for number in range(1, expected_pages + 1)]
    if markers != expected:
        raise ValueError(f"Page markers mismatch: expected {expected}, found {markers}")
    if "\ufffd" in markdown:
        raise ValueError("Unicode replacement character found in processed Markdown")
    if not markdown.startswith("---\n"):
        raise ValueError("YAML front matter is missing")


def process_document(record: dict[str, Any]) -> ProcessingStats:
    raw_path = D2_ROOT / record["local_raw_path"]
    output_path = D2_ROOT / record["processed_path"]
    if not raw_path.is_file():
        raise FileNotFoundError(f"Raw PDF not found for {record['document_id']}: {raw_path}")
    actual_hash = _sha256(raw_path)
    if actual_hash != record["content_hash"]:
        raise ValueError(
            f"Raw hash mismatch for {record['document_id']}: "
            f"manifest={record['content_hash']} actual={actual_hash}"
        )

    config = DOCUMENT_CONFIG.get(record["document_id"], DocumentConfig())
    pages = extract_pdf_pages(raw_path, config)
    markdown, stats = render_markdown(record, pages, config)
    validate_processed_document(markdown, len(pages))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8", newline="\n")
    return stats


def _select_records(
    records: list[dict[str, Any]], requested: list[str] | None, process_all: bool
) -> list[dict[str, Any]]:
    accepted = [record for record in records if record.get("status") == "accepted"]
    if process_all:
        return accepted
    if not requested:
        raise ValueError("Specify --documents <document_id> [...] or --all")
    by_id = {record["document_id"]: record for record in accepted}
    unknown = [document_id for document_id in requested if document_id not in by_id]
    if unknown:
        raise ValueError(f"Unknown or non-accepted document_id(s): {', '.join(unknown)}")
    return [by_id[document_id] for document_id in requested]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert accepted D2 raw PDFs into deterministic structured Markdown."
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--documents", nargs="+", metavar="DOCUMENT_ID")
    selection.add_argument("--all", action="store_true", help="Process every accepted document")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    try:
        records = load_manifest()
        selected = _select_records(records, args.documents, args.all)
        for record in selected:
            stats = process_document(record)
            LOGGER.info(
                "%s pages=%d extracted_chars=%d processed_chars=%d removed=%.2f%% headings=%d warnings=%d",
                stats.document_id,
                stats.pages,
                stats.extracted_characters,
                stats.processed_characters,
                stats.removed_percent,
                stats.headings,
                len(stats.warnings),
            )
            for warning in stats.warnings:
                LOGGER.warning("%s: %s", stats.document_id, warning)
    except (FileNotFoundError, RuntimeError, ValueError, KeyError) as exc:
        LOGGER.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
