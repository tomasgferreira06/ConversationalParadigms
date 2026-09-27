"""Deterministic raw-HTML-to-Markdown preprocessing for the D2 web corpus.

Works offline on the raw HTML saved by acquire_web_corpus.py. It keeps the
source wording: it only selects the page's own content, drops template,
media, calls to action and clearly operational sentences, and normalises the
Elementor heading hierarchy. No summarisation, paraphrase or LLM.

Usage:
    uv run python d2_rag/scripts/preprocess_web_documents.py --all
    uv run python d2_rag/scripts/preprocess_web_documents.py --documents ID [ID ...]
    uv run python d2_rag/scripts/preprocess_web_documents.py --all --accept
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag


D2_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = D2_ROOT / "data" / "manifest.jsonl"

# ---- Template configuration (visitecoimbra.pt, WordPress + Elementor) -------
# Header, menus and footer are separate Elementor templates; the page's own
# content is the single wp-page document.
CONTENT_SELECTOR = '[data-elementor-type="wp-page"]'
# The desktop rendering is canonical; blocks hidden on desktop duplicate
# responsive variants of visible blocks.
HIDDEN_ON_DESKTOP = "elementor-hidden-desktop"
# Media, calls to action, embeds and the experiences carousel carry no text
# knowledge (the RAG is text-only; images are not downloaded). ova_heading is
# the theme's call-to-action banner ("Planeie a sua visita...").
DROP_WIDGETS = {
    "image", "image-carousel", "gallery", "button", "spacer", "divider", "html", "video",
    "nested-carousel", "social-icons", "share-buttons", "icon", "google_maps",
    "ova_heading",
}
# Site-wide call-to-action sections (promote the portal's own apps/pages).
SITE_CTA_SECTIONS = [
    "Não sabe por onde começar?",  # promotes the "Roteiros temáticos" webapp
    "Experiências",  # one-line teaser linking to a bookable experience
]
QUOTE_OPENERS = ('"', "“", "«", "‘")
# Real section headings in this corpus have 1-8 words; Elementor "headings"
# of 17+ words are highlighted sentences, kept as quotes instead.
HEADING_MAX_WORDS = 12
# Paragraphs with this many <br> are lists or verse and keep their lines;
# fewer <br> are visual wraps inside a sentence.
MIN_LINE_BREAKS_FOR_LINES = 3
# A sentence is operational only if it states an explicit opening-time range.
OPERATIONAL_SENTENCE = re.compile(r"\b\d{1,2}h\d{0,2}\s*(?:às|a|-|–)\s*\d{1,2}h", re.IGNORECASE)
MIN_WORDS = 80

# Sections that are commercial or event programming and cannot be told apart
# structurally; removed with everything below them down to the next heading of
# the same or higher level. Human-reviewed, per document.
DROP_SECTIONS: dict[str, list[str]] = {
    "web-visitecoimbra-cancao-de-coimbra": [
        "Casas para ouvir a Canção de Coimbra",  # cards of private fado houses
    ],
    "web-visitecoimbra-docaria-conventual-de-coimbra": [
        "Mostra de Doçaria Conventual e Contemporânea de Coimbra",  # event
    ],
    "web-visitecoimbra-ceramica-de-coimbra": [
        "Saber mais sobre a Louça de Coimbra",  # named shops and an artisan's gallery
    ],
    "web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira": [
        "BREW!", "Epicura", "Portuguese Pedro", "Praxis",  # brand/festival cards
    ],
    "web-visitecoimbra-heranca-judaica": [
        "APP - Exposição “Judeus em Coimbra”",  # app download promotion
    ],
}

# Known disagreements with the PDF corpus. Recorded, never corrected.
CONFLICT_NOTES: dict[str, str] = {
    "web-visitecoimbra-heranca-cultural-e-religiosa": (
        "Potential conflict with fundacao-da-nacionalidade regarding the foundation of "
        "Santa Clara-a-Velha: web says 'Fundado pela Rainha Santa Isabel'; the PDF says "
        "founded in 1283 by D. Mor Dias and later refounded by Rainha Santa Isabel."
    ),
    "web-visitecoimbra-museus": (
        "Potential conflict with fundacao-da-nacionalidade regarding the foundation of "
        "Santa Clara-a-Velha: web says 'mandado construir em 1314 por D. Isabel de Aragão'; "
        "the PDF says founded in 1283 by D. Mor Dias, refoundation from 1314."
    ),
}
# -----------------------------------------------------------------------------


@dataclass
class Block:
    kind: str  # heading | paragraph | list | quote
    text: str
    level: int = 0


@dataclass
class Stats:
    dropped_widgets: dict[str, int] = field(default_factory=dict)
    dropped_sections: list[str] = field(default_factory=list)
    empty_sections: list[str] = field(default_factory=list)
    operational_sentences: list[str] = field(default_factory=list)
    hidden_blocks: int = 0
    warnings: list[str] = field(default_factory=list)


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace(" ", " ").replace("­", "")
    return re.sub(r"\s+", " ", text).strip()


def _inline_text(tag: Tag) -> str:
    for br in tag.find_all("br"):
        br.replace_with(" ")
    return clean_text(tag.get_text(""))


def _paragraph_text(tag: Tag) -> str:
    """Like _inline_text, but list/verse paragraphs keep one line per <br>."""

    breaks = tag.find_all("br")
    if len(breaks) < MIN_LINE_BREAKS_FOR_LINES:
        return _inline_text(tag)
    for br in breaks:
        br.replace_with("\n")
    lines = [clean_text(line) for line in tag.get_text("").split("\n")]
    return "\n".join(line for line in lines if line)


def _widget_type(tag: Tag) -> str | None:
    value = tag.get("data-widget_type")
    return value.split(".")[0] if value else None


def _count(stats: Stats, widget: str) -> None:
    stats.dropped_widgets[widget] = stats.dropped_widgets.get(widget, 0) + 1


def _strip_operational(text: str, stats: Stats) -> str:
    lines = []
    for line in text.split("\n"):
        kept = []
        for sentence in re.split(r"(?<=[.!?])[ \t]+", line):
            if OPERATIONAL_SENTENCE.search(sentence):
                stats.operational_sentences.append(sentence)
            else:
                kept.append(sentence)
        if " ".join(kept).strip():
            lines.append(" ".join(kept).strip())
    return "\n".join(lines)


def _text_editor_blocks(widget: Tag, stats: Stats) -> list[Block]:
    container = widget.select_one(".elementor-widget-container") or widget
    elements = [c for c in container.children if isinstance(c, Tag)]
    loose = clean_text(" ".join(str(c) for c in container.children if isinstance(c, NavigableString)))
    if not elements or (loose and all(e.name in ("strong", "b", "em", "i", "a", "span", "br") for e in elements)):
        # Inline-only content: one paragraph.
        text = _strip_operational(_inline_text(container), stats)
        return [Block("paragraph", text)] if text else []
    blocks: list[Block] = []
    for element in elements:
        if element.name in ("ul", "ol"):
            items = [_inline_text(li) for li in element.find_all("li", recursive=False)]
            items = [i for i in items if i]
            if items:
                blocks.append(Block("list", "\n".join(f"- {i}" for i in items)))
            continue
        text = _strip_operational(_paragraph_text(element), stats)
        if text:
            blocks.append(Block("paragraph", text))
    return blocks


class Walker:
    """Walk the content DOM in document order and emit Markdown blocks."""

    def __init__(self, stats: Stats) -> None:
        self.stats = stats
        self.blocks: list[Block] = []

    def walk(self, node: Tag, scope_level: int, last_heading: int | None = None) -> int:
        """scope_level: level of the enclosing heading (page title = 1).

        Returns the level of the last section heading emitted in this scope, so
        cards and accordion items that follow a heading nest under it.
        """
        last = scope_level if last_heading is None else last_heading
        for child in node.children:
            if not isinstance(child, Tag):
                continue
            if HIDDEN_ON_DESKTOP in child.get("class", []):
                self.stats.hidden_blocks += 1
                continue
            widget = _widget_type(child)
            if widget is None:
                last = self.walk(child, scope_level, last)
            else:
                last = self._widget(child, widget, scope_level, last)
        return last

    def _widget(self, widget: Tag, kind: str, scope_level: int, last_heading: int) -> int:
        if kind in DROP_WIDGETS:
            _count(self.stats, kind)
            return last_heading
        if kind == "heading":
            text = _inline_text(widget)
            if not text:
                return last_heading
            if text.startswith(QUOTE_OPENERS) or len(text.split()) > HEADING_MAX_WORDS:
                self.blocks.append(Block("quote", text))
                return last_heading
            level = min(scope_level + 1, 6)
            self.blocks.append(Block("heading", text.rstrip(":").strip(), level))
            return level
        if kind == "text-editor":
            self.blocks.extend(_text_editor_blocks(widget, self.stats))
            return last_heading
        if kind == "flip-box":
            front = widget.select_one(".elementor-flip-box__front") or widget
            title = front.select_one(".elementor-flip-box__layer__title")
            description = front.select_one(".elementor-flip-box__layer__description")
            if title and _inline_text(title):
                self.blocks.append(Block("heading", _inline_text(title), min(last_heading + 1, 6)))
            if description:
                text = _strip_operational(_inline_text(description), self.stats)
                if text:
                    self.blocks.append(Block("paragraph", text))
            _count(self.stats, "flip-box back layer")
            return last_heading
        if kind == "nested-accordion":
            item_level = min(last_heading + 1, 6)
            for item in widget.find_all("details"):
                if item.find_parent("details") is not None:
                    continue
                summary = item.find("summary")
                title = re.sub(r"^[•·\-–]\s*", "", _inline_text(summary)) if summary else ""
                if summary is not None:
                    summary.extract()
                if title:
                    self.blocks.append(Block("heading", title, item_level))
                    self.walk(item, item_level)
                else:
                    # An untitled item is only a visual container.
                    self.walk(item, scope_level)
            return last_heading
        # Unknown widget: keep its text rather than lose content.
        text = _inline_text(widget)
        if text:
            self.stats.warnings.append(f"unhandled widget '{kind}' kept as text")
            self.blocks.append(Block("paragraph", text))
        return last_heading


def _drop_sections(blocks: list[Block], titles: list[str], stats: Stats) -> list[Block]:
    out, skip_level = [], None
    for block in blocks:
        if skip_level is not None:
            if block.kind == "heading" and block.level <= skip_level:
                skip_level = None
            else:
                continue
        if block.kind == "heading" and block.text in titles:
            stats.dropped_sections.append(block.text)
            skip_level = block.level
            continue
        out.append(block)
    return out


def _drop_empty_sections(blocks: list[Block], stats: Stats) -> list[Block]:
    """Remove headings with no content before the next same-or-higher heading.

    Repeated until stable, so a parent whose only children were empty is
    removed too.
    """

    while True:
        out = []
        for i, block in enumerate(blocks):
            if block.kind == "heading":
                nxt = blocks[i + 1] if i + 1 < len(blocks) else None
                if nxt is None or (nxt.kind == "heading" and nxt.level <= block.level):
                    stats.empty_sections.append(block.text)
                    continue
            out.append(block)
        if len(out) == len(blocks):
            return out
        blocks = out


def _close_level_gaps(blocks: list[Block]) -> list[Block]:
    """A heading is at most one level deeper than the previous heading."""

    previous = 1
    for block in blocks:
        if block.kind == "heading":
            block.level = min(block.level, previous + 1)
            previous = block.level
    return blocks


def _dedupe_consecutive(blocks: list[Block]) -> list[Block]:
    out: list[Block] = []
    for block in blocks:
        if out and out[-1].kind == block.kind and out[-1].text == block.text:
            continue
        out.append(block)
    return out


def html_to_blocks(html: str, document_id: str) -> tuple[list[Block], Stats]:
    stats = Stats()
    containers = BeautifulSoup(html, "lxml").select(CONTENT_SELECTOR)
    if len(containers) != 1:
        raise ValueError(f"{document_id}: expected 1 content container, found {len(containers)}")
    walker = Walker(stats)
    walker.walk(containers[0], scope_level=1)
    configured = DROP_SECTIONS.get(document_id, [])
    blocks = _drop_sections(walker.blocks, configured + SITE_CTA_SECTIONS, stats)
    blocks = _close_level_gaps(_drop_empty_sections(_dedupe_consecutive(blocks), stats))
    for title in configured:
        if title not in stats.dropped_sections:
            stats.warnings.append(f"configured section not found: {title!r}")
    _warn_repeated_sections(blocks, stats)
    return blocks, stats


def _warn_repeated_sections(blocks: list[Block], stats: Stats) -> None:
    """Flag entity sections the source page repeats verbatim (kept, not merged)."""

    seen: dict[tuple[str, str], int] = {}
    for i, block in enumerate(blocks[:-1]):
        if block.kind == "heading" and blocks[i + 1].kind != "heading":
            key = (block.text, blocks[i + 1].text)
            seen[key] = seen.get(key, 0) + 1
    for (title, _text), count in sorted(seen.items()):
        if count > 1:
            stats.warnings.append(f"section repeated {count}x in source (kept): {title!r}")


def render_markdown(record: dict[str, Any], blocks: list[Block]) -> str:
    front = [
        "---",
        f"document_id: {json.dumps(record['document_id'], ensure_ascii=False)}",
        f"title: {json.dumps(record['title'], ensure_ascii=False)}",
        f"source_organization: {json.dumps(record['source_organization'], ensure_ascii=False)}",
        f"url: {json.dumps(record['url'], ensure_ascii=False)}",
        f"language: {json.dumps(record['language'], ensure_ascii=False)}",
        'source_type: "web_page"',
        "---",
        "",
        f"# {record['title']}",
    ]
    body = []
    for block in blocks:
        if block.kind == "heading":
            body.append(f"{'#' * block.level} {block.text}")
        elif block.kind == "quote":
            body.append(f"> {block.text}")
        else:
            body.append(block.text)
    return "\n".join(front) + "\n\n" + "\n\n".join(body) + "\n"


def validate(markdown: str) -> list[str]:
    """Problems that block acceptance."""

    problems = []
    body = markdown.split("\n---\n", 1)[-1]
    if len(body.split()) < MIN_WORDS:
        problems.append(f"processed body has fewer than {MIN_WORDS} words")
    if "�" in markdown:
        problems.append("U+FFFD in output")
    # Template residue would mean the content selector failed.
    for marker in ("Agentes e profissionais", "© Página oficial Turismo de Coimbra", "turismo@cm-coimbra.pt"):
        if marker in body:
            problems.append(f"template residue: {marker!r}")
    return problems


def hidden_blocks_missing_from_output(html: str, markdown: str) -> list[str]:
    """Desktop-hidden blocks are skipped as duplicates; check they really are."""

    content = BeautifulSoup(html, "lxml").select_one(CONTENT_SELECTOR)
    flat = clean_text(markdown)
    missing = []
    for hidden in content.select(f".{HIDDEN_ON_DESKTOP}"):
        text = clean_text(hidden.get_text(""))
        if text and text not in flat:
            missing.append(text[:80])
    return missing


def load_manifest() -> list[dict[str, Any]]:
    return [json.loads(l) for l in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_web_records(updates: dict[str, dict[str, Any]]) -> None:
    """Rewrite web records only; every PDF line stays byte-identical."""

    out = []
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("source_type") == "web_page" and record["document_id"] in updates:
            out.append(json.dumps(updates[record["document_id"]], ensure_ascii=False))
        else:
            out.append(line)
    MANIFEST_PATH.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


def render_document(record: dict[str, Any]) -> tuple[str, Stats, list[str]]:
    """Raw HTML (hash-checked) -> Markdown, validation problems. No network."""

    raw = (D2_ROOT / record["local_raw_path"]).read_bytes()
    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual != record["content_hash"]:
        raise ValueError(f"{record['document_id']}: raw hash mismatch ({actual})")
    html = raw.decode("utf-8")
    blocks, stats = html_to_blocks(html, record["document_id"])
    markdown = render_markdown(record, blocks)
    for text in hidden_blocks_missing_from_output(html, markdown):
        stats.warnings.append(f"desktop-hidden block not found in output: {text!r}")
    return markdown, stats, validate(markdown)


def extraction_notes(stats: Stats) -> str:
    parts = [f"dropped widgets: {dict(sorted(stats.dropped_widgets.items()))}"]
    if stats.hidden_blocks:
        parts.append(f"{stats.hidden_blocks} desktop-hidden responsive duplicates skipped")
    if stats.dropped_sections:
        parts.append(f"dropped sections: {stats.dropped_sections}")
    if stats.empty_sections:
        parts.append(f"empty sections removed: {stats.empty_sections}")
    if stats.operational_sentences:
        parts.append(f"{len(stats.operational_sentences)} operational sentence(s) removed")
    return "; ".join(parts)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Preprocess raw web pages to Markdown.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--documents", nargs="+", metavar="DOCUMENT_ID")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--accept", action="store_true", help="mark validated documents as accepted")
    args = parser.parse_args(argv)

    records = [r for r in load_manifest() if r.get("source_type") == "web_page" and r.get("local_raw_path")]
    if args.documents:
        records = [r for r in records if r["document_id"] in args.documents]
    updates, failures = {}, 0
    for record in records:
        markdown, stats, problems = render_document(record)
        out_path = D2_ROOT / record["processed_path"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8", newline="\n")
        failures += bool(problems)
        print(f"{'OK  ' if not problems else 'FAIL'} {record['document_id']}: "
              f"{len(markdown.split())} words; {extraction_notes(stats)}")
        for item in problems + stats.warnings:
            print(f"     ! {item}")
        if args.accept:
            updated = dict(record)
            updated["extraction_notes"] = extraction_notes(stats)
            updated["conflict_notes"] = CONFLICT_NOTES.get(record["document_id"])
            if stats.operational_sentences:
                updated["validity_notes"] = (
                    "Opening hours present in the raw page were removed from the processed "
                    "Markdown; the portal may change schedules at any time."
                )
            updated["status"] = "accepted" if not problems else "reviewing"
            updates[record["document_id"]] = updated
    if args.accept:
        write_web_records(updates)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
