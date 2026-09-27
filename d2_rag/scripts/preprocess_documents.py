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


# Photo-caption panels on route pages: a marker block such as "a. b. c. d."
# next to the captions, under a large decorative panel title.
CAPTION_MARKERS_RE = re.compile(r"(?:[a-z]\.\s*){2,}")
CAPTION_PANEL_TITLE_MIN_SIZE = 14.0
CAPTION_PANEL_COMMENT = "<!-- caption_panel -->"

# On map pages, only blocks at least this long are treated as editorial prose;
# shorter blocks are map labels (same threshold as the route map sidebar).
MAP_EDITORIAL_MIN_CHARS = 120

# Line-break hyphens before these enclitic pronouns are part of the source
# word ("destaca-se") and are kept. Only applied after a vowel, 'r', 'm' or 'z',
# since 'se' after a consonant is ordinary hyphenation ("dis-se").
KEPT_HYPHEN_ENCLITICS = ("se",)


@dataclass(frozen=True)
class DocumentConfig:
    route_layout: bool = False
    web_print: bool = False
    horizontal_blocks: bool = False
    stop_after: str | None = None
    skip_content_pages: frozenset[int] = frozenset()
    section_headings: frozenset[str] = frozenset()
    # (font name, ((min, max), ...)): space glyphs in that font whose
    # width / font size falls in one of these half-open bands are
    # letter-spacing, not word boundaries.
    letter_spacing_fonts: tuple[tuple[str, tuple[tuple[float, float], ...]], ...] = ()
    # (font name, max span size in pt): small-caps fonts draw lowercase letters
    # as reduced-size spans, one word per span, with word gaps in separate
    # full-size spans; every space inside a reduced span is letter-spacing.
    letter_spacing_small_caps: tuple[tuple[str, float], ...] = ()
    caption_panel_to_page_end: bool = False
    map_pages: frozenset[int] = frozenset()


DOCUMENT_CONFIG: dict[str, DocumentConfig] = {
    document_id: DocumentConfig(route_layout=True)
    for document_id in ROUTE_DOCUMENT_IDS
}
# Every Montserrat-Light space glyph in this PDF falls in one of four width
# classes (width / font size): 0.15-0.19 letter-spacing (381), 0.27 word space
# (2306), 0.30 letter-spacing in one tracked name (10), and 0.42 word space in
# tracked republic names (33). The bands drop only the two letter-spacing
# classes. Headings use other fonts, whose word spaces can be narrower, so the
# rule is restricted to this font. Labels in Montserrat-Black-SC700 use
# reduced spans of 4.9-6.0 pt and full-size word gaps of 7.0-7.4 pt.
DOCUMENT_CONFIG["fado-e-tradicoes-academicas"] = DocumentConfig(
    route_layout=True,
    letter_spacing_fonts=(("Montserrat-Light", ((0.0, 0.23), (0.29, 0.33))),),
    letter_spacing_small_caps=(("Montserrat-Black-SC700", 6.5),),
)
for _document_id in ("coimbra-para-os-pequenitos", "fundacao-da-nacionalidade"):
    DOCUMENT_CONFIG[_document_id] = DocumentConfig(
        route_layout=True, caption_panel_to_page_end=True
    )
DOCUMENT_CONFIG["biblioteca-joanina-uctour"] = DocumentConfig(
    web_print=True,
    stop_after="Programas que incluem este espaço",
    skip_content_pages=frozenset({1}),
    section_headings=frozenset(
        {"Biblioteca Joanina", "Piso Nobre", "Piso Intermédio", "Prisão Académica"}
    ),
)
DOCUMENT_CONFIG["universidade-alta-sofia-patrimonio-mundial"] = DocumentConfig(
    horizontal_blocks=True,
    # City map (34-35), regional map with one editorial block (40), and
    # map of Portugal (41).
    map_pages=frozenset({34, 35, 40, 41}),
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


def _is_enclitic_line_break(before: str, continuation: str) -> bool:
    """True when 'verb-' + 'se ...' is an enclitic form split at its hyphen."""

    first_word = re.match(r"\w+", continuation)
    if not first_word or first_word.group(0) not in KEPT_HYPHEN_ENCLITICS:
        return False
    return re.search(r"[aeiouáéíóúâêôãõrmz]-$", before, flags=re.IGNORECASE) is not None


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
                if _is_enclitic_line_break(joined, continuation):
                    joined += continuation
                else:
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


def _text_blocks(page: pymupdf.Page, config: DocumentConfig) -> list[tuple[float, float, float, float, str]]:
    """Return (x0, y0, x1, y1, text) text blocks, as get_text("blocks") does.

    When the document configures letter-spacing fonts, blocks are rebuilt from
    individual glyphs so that narrow letter-spacing space glyphs can be dropped.
    """

    if not (config.letter_spacing_fonts or config.letter_spacing_small_caps):
        return [tuple(block[:5]) for block in page.get_text("blocks", sort=False)]
    bands_by_font = dict(config.letter_spacing_fonts)
    max_size_by_small_caps_font = dict(config.letter_spacing_small_caps)
    blocks = []
    for block in page.get_text("rawdict", sort=False)["blocks"]:
        if block.get("type") != 0:
            continue
        lines = []
        for line in block["lines"]:
            chars = []
            for span in line["spans"]:
                bands = bands_by_font.get(span["font"], ())
                max_size = max_size_by_small_caps_font.get(span["font"])
                reduced_small_caps = max_size is not None and span["size"] < max_size
                for char in span["chars"]:
                    if char["c"] == " " and reduced_small_caps:
                        continue
                    if char["c"] == " " and bands and span["size"] > 0:
                        ratio = (char["bbox"][2] - char["bbox"][0]) / span["size"]
                        if any(low <= ratio < high for low, high in bands):
                            continue
                    chars.append(char["c"])
            lines.append("".join(chars))
        blocks.append((*block["bbox"], "\n".join(lines) + "\n"))
    return blocks


def _route_column(x0: float, width: float) -> int:
    return min(2, max(0, int((x0 - width * 0.25) / (width * 0.24))))


def _caption_panel_tops(page: pymupdf.Page) -> dict[int, float]:
    """Top y of each column's photo-caption panel on a route page.

    The panel is anchored on its marker block ("a. b. c. ...") and starts at
    the nearest large panel title above it in the same column.
    """

    width = page.rect.width
    blocks = []
    for block in page.get_text("dict", sort=False)["blocks"]:
        if block.get("type") != 0:
            continue
        spans = [span for line in block["lines"] for span in line["spans"]]
        text = normalize_whitespace(
            " ".join("".join(span["text"] for span in line["spans"]) for line in block["lines"])
        )
        max_size = max((span["size"] for span in spans if span["text"].strip()), default=0.0)
        blocks.append((_route_column(block["bbox"][0], width), block["bbox"][1], max_size, text))

    tops: dict[int, float] = {}
    for column, marker_y0, _size, text in blocks:
        if not CAPTION_MARKERS_RE.fullmatch(text):
            continue
        titles = [
            y0
            for other_column, y0, size, _text in blocks
            if other_column == column and y0 <= marker_y0 and size >= CAPTION_PANEL_TITLE_MIN_SIZE
        ]
        top = max(titles) if titles else marker_y0
        tops[column] = min(top, tops.get(column, top))
    return tops


def _join_sentence_across_column_break(blocks: list[tuple[int, float, str]], column: int) -> None:
    """Rejoin the sentence that a caption panel separated at a column break.

    Only applied to the column that held the panel: if its last text block
    ends mid-sentence, the first block of the next column continues it.
    """

    last = max((i for i, block in enumerate(blocks) if block[0] == column), default=None)
    if last is None or last + 1 >= len(blocks) or blocks[last + 1][0] != column + 1:
        return
    if re.search(r"[.!?:;”»\"')]$", normalize_whitespace(blocks[last][2])):
        return
    column_index, y0, text = blocks[last]
    blocks[last] = (column_index, y0, text + "\n" + blocks[last + 1][2])
    del blocks[last + 1]


def _route_first_page_text(page: pymupdf.Page, config: DocumentConfig) -> str:
    """Read the body of a municipal route page column by column."""

    body_blocks: list[tuple[int, float, str]] = []
    caption_blocks: list[tuple[int, float, str]] = []
    width, height = page.rect.width, page.rect.height
    panel_tops = _caption_panel_tops(page) if config.caption_panel_to_page_end else {}
    for block in _text_blocks(page, config):
        x0, y0, x1, y1, text = block[:5]
        normalized_text = normalize_whitespace(text)
        if x0 < width * 0.25 or y0 < height * 0.12 or y1 > height * 0.96:
            continue
        if re.fullmatch(r"[\d\s]+", normalized_text):
            continue
        column = _route_column(x0, width)
        # Tolerance absorbs rounding differences between text extraction modes.
        if column in panel_tops and y0 >= panel_tops[column] - 1.0:
            caption_blocks.append((column, y0, text.strip()))
        else:
            body_blocks.append((column, y0, text.strip()))
    body_blocks.sort(key=lambda item: (item[0], item[1]))
    caption_blocks.sort(key=lambda item: (item[0], item[1]))
    for column in sorted(panel_tops, reverse=True):
        _join_sentence_across_column_break(body_blocks, column)
    body = "\n\n".join(text for _, _, text in body_blocks if text)
    if not caption_blocks:
        return body
    # The panel sits at the foot of a column while that column's last sentence
    # continues at the top of the next one, so it goes after the page's text.
    captions = "\n\n".join(text for _, _, text in caption_blocks if text)
    return f"{body}\n\n{CAPTION_PANEL_COMMENT}\n\n{captions}"


def _route_map_page_text(page: pymupdf.Page, config: DocumentConfig) -> str:
    """Keep the editorial sidebar on route maps, omitting scattered map labels."""

    width, height = page.rect.width, page.rect.height
    blocks: list[tuple[float, str]] = []
    for block in _text_blocks(page, config):
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


def _horizontal_block_text(page: pymupdf.Page, editorial_only: bool = False) -> str:
    """Extract horizontal text blocks and ignore decorative rotated typography.

    With editorial_only (map pages), short blocks are map labels and dropped.
    """

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
        if editorial_only and len(normalize_whitespace(" ".join(lines))) < MAP_EDITORIAL_MIN_CHARS:
            continue
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
                text = _route_first_page_text(page, config)
            elif config.route_layout and index == 1:
                text = _route_map_page_text(page, config)
            elif config.horizontal_blocks:
                text = _horizontal_block_text(page, editorial_only=index + 1 in config.map_pages)
            else:
                text = page.get_text("text", sort=True)
            if config.route_layout and index == 1:
                warnings.append("Map labels omitted; editorial sidebar retained.")
            if index + 1 in config.map_pages:
                warnings.append("Map labels omitted; editorial text blocks retained.")
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


def render_document(record: dict[str, Any]) -> tuple[str, ProcessingStats]:
    """Render a manifest record to validated Markdown without writing it."""

    raw_path = D2_ROOT / record["local_raw_path"]
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
    return markdown, stats


def process_document(record: dict[str, Any]) -> ProcessingStats:
    markdown, stats = render_document(record)
    output_path = D2_ROOT / record["processed_path"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8", newline="\n")
    return stats


def _select_records(
    records: list[dict[str, Any]], requested: list[str] | None, process_all: bool
) -> list[dict[str, Any]]:
    # The manifest also lists web pages; those have their own pipeline.
    accepted = [
        record
        for record in records
        if record.get("status") == "accepted" and record.get("source_type") == "pdf"
    ]
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
