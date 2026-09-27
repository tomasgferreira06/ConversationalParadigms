"""Acquire approved visitecoimbra.pt pages as raw HTML (D2 web corpus).

Acquisition only: reads the human-approved URL list, fetches each page once
(robots.txt respected, one request at a time, rate limited), stores the HTML
exactly as returned by the server, hashes it and records provenance in the
manifest. No preprocessing happens here; see preprocess_web_documents.py.

Raw files are immutable: an existing raw file is never overwritten.

Usage:
    uv run python d2_rag/scripts/acquire_web_corpus.py --all
    uv run python d2_rag/scripts/acquire_web_corpus.py --documents ID [ID ...]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, HTTPCrawlerConfig
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy


D2_ROOT = Path(__file__).resolve().parents[1]
APPROVED_PATH = D2_ROOT / "web_discovery" / "approved_urls.jsonl"
MANIFEST_PATH = D2_ROOT / "data" / "manifest.jsonl"
RAW_WEB_DIR = D2_ROOT / "data" / "raw" / "web"
PROCESSED_WEB_DIR = D2_ROOT / "data" / "processed" / "web"

SITE_HOST = "visitecoimbra.pt"
ROBOTS_URL = "https://visitecoimbra.pt/robots.txt"
USER_AGENT = "D2-RAG-discovery/0.1 (academic project; conservative crawl)"
# The portal is the municipality's official tourism site (CMC logo, contacts
# at cm-coimbra.pt); same organisation name as the municipal PDFs.
SOURCE_ORGANIZATION = "Câmara Municipal de Coimbra"
TITLE_SUFFIX = re.compile(r"\s+–\s+Website oficial Turismo de Coimbra$")

CONCURRENCY = 1
MEAN_DELAY_S = 1.5
DELAY_RANGE_S = 1.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def robots_allows(urls: list[str]) -> dict[str, bool]:
    request = urllib.request.Request(ROBOTS_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        parser = RobotFileParser()
        parser.parse(response.read().decode("utf-8", errors="replace").splitlines())
    return {url: parser.can_fetch(USER_AGENT, url) for url in urls}


def _html_attr(html: str, pattern: str) -> str | None:
    match = re.search(pattern, html, re.IGNORECASE)
    return match.group(1) if match else None


async def fetch(urls: list[str]) -> list[Any]:
    strategy = AsyncHTTPCrawlerStrategy(
        browser_config=HTTPCrawlerConfig(headers={"User-Agent": USER_AGENT})
    )
    config = CrawlerRunConfig(
        check_robots_txt=True,
        semaphore_count=CONCURRENCY,
        mean_delay=MEAN_DELAY_S,
        max_range=DELAY_RANGE_S,
        verbose=False,
    )
    async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
        return list(await crawler.arun_many(urls, config=config))


def check_response(approved: dict[str, Any], result: Any) -> list[str]:
    """Return the reasons why a response does not match the approved page."""

    problems = []
    html = result.html or ""
    headers = {k.lower(): v for k, v in (result.response_headers or {}).items()}
    if not result.success or result.status_code != 200:
        problems.append(f"HTTP {result.status_code}: {(result.error_message or '').strip()[:120]}")
        return problems
    final_host = urlsplit(result.redirected_url or result.url).netloc.lower().removeprefix("www.")
    if final_host != SITE_HOST:
        problems.append(f"left the domain: {result.redirected_url}")
    if "text/html" not in headers.get("content-type", ""):
        problems.append(f"unexpected content-type {headers.get('content-type')}")
    lang = _html_attr(html, r"<html[^>]*\blang=\"([^\"]+)\"") or ""
    if not lang.lower().startswith("pt"):
        problems.append(f"html lang is {lang!r}")
    canonical = _html_attr(html, r"<link[^>]+rel=\"canonical\"[^>]+href=\"([^\"]+)\"")
    if canonical and canonical.rstrip("/") + "/" != approved["canonical_url"]:
        problems.append(f"canonical changed to {canonical}")
    title = TITLE_SUFFIX.sub("", (result.metadata or {}).get("title") or "")
    if title != approved["title"]:
        problems.append(f"title changed to {title!r}")
    if "erro crítico" in html and "<error>" in html:
        problems.append("WordPress critical-error page")
    return problems


def manifest_record(approved: dict[str, Any], result: Any | None, checked_at: str,
                    raw_path: Path | None, raw_bytes: bytes | None, problems: list[str],
                    existing: dict[str, Any] | None) -> dict[str, Any]:
    html = (result.html or "") if result is not None else ""
    headers = {k.lower(): v for k, v in ((result.response_headers or {}) if result is not None else {}).items()}
    modified = _html_attr(html, r"<meta[^>]+property=\"article:modified_time\"[^>]+content=\"([^\"]+)\"")
    record = dict(existing or {})
    record.update({
        "document_id": approved["document_id"],
        "title": approved["title"],
        "source_organization": SOURCE_ORGANIZATION,
        "url": approved["canonical_url"],
        "canonical_url": approved["canonical_url"],
        "language": "pt",
        "primary_category": approved["proposed_category"],
        "source_type": "web_page",
        "access_checked_at": checked_at,
        "decision_reason": approved["decision_reason"],
    })
    if raw_bytes is not None:
        record.update({
            "status": "reviewing",
            "acquired_at": checked_at,
            "content_hash": _sha256(raw_bytes),
            "local_raw_path": raw_path.relative_to(D2_ROOT).as_posix(),
            "processed_path": (PROCESSED_WEB_DIR / f"{approved['document_id']}.md").relative_to(D2_ROOT).as_posix(),
            # Only content metadata counts as a revision date; the HTTP header
            # reflects the server cache, so it is kept under its own name.
            "source_last_modified_at": modified,
            "http_last_modified": headers.get("last-modified"),
            "http_status": result.status_code,
            "raw_representation": "server HTML response body, decoded by the HTTP fetcher and stored as UTF-8",
        })
    elif not (existing and existing.get("content_hash")):
        record.update({
            "status": "unavailable",
            "acquired_at": None,
            "content_hash": None,
            "local_raw_path": None,
            "processed_path": None,
            "decision_reason": approved["decision_reason"] + " Acquisition failed: " + "; ".join(problems),
        })
    record.setdefault("conflict_notes", None)
    record.setdefault("validity_notes", None)
    record.setdefault("extraction_notes", None)
    return record


def write_manifest(web_records: dict[str, dict[str, Any]]) -> None:
    """Keep every non-web line byte-identical; upsert web records sorted by id."""

    lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line.strip() and json.loads(line).get("source_type") != "web_page"]
    existing_web = {
        json.loads(line)["document_id"]: json.loads(line)
        for line in lines
        if line.strip() and json.loads(line).get("source_type") == "web_page"
    }
    existing_web.update(web_records)
    web_lines = [json.dumps(existing_web[i], ensure_ascii=False) for i in sorted(existing_web)]
    MANIFEST_PATH.write_text("\n".join(kept + web_lines) + "\n", encoding="utf-8", newline="\n")


def acquire(document_ids: list[str] | None) -> int:
    approved = load_jsonl(APPROVED_PATH)
    if document_ids:
        unknown = set(document_ids) - {a["document_id"] for a in approved}
        if unknown:
            raise SystemExit(f"Not in approved_urls.jsonl: {sorted(unknown)}")
        approved = [a for a in approved if a["document_id"] in document_ids]
    existing = {r["document_id"]: r for r in load_jsonl(MANIFEST_PATH) if r.get("source_type") == "web_page"}
    RAW_WEB_DIR.mkdir(parents=True, exist_ok=True)

    todo = [a for a in approved if not (RAW_WEB_DIR / f"{a['document_id']}.html").exists()]
    for a in approved:
        if a not in todo:
            print(f"SKIP {a['document_id']}: raw already acquired (raw files are immutable)")
    if not todo:
        return 0
    allowed = robots_allows([a["canonical_url"] for a in todo])
    blocked = [a["document_id"] for a in todo if not allowed[a["canonical_url"]]]
    if blocked:
        raise SystemExit(f"robots.txt disallows: {blocked}; stopping")

    checked_at = _now()
    results = {r.url.rstrip("/") + "/": r for r in asyncio.run(fetch([a["canonical_url"] for a in todo]))}
    records, failures = {}, 0
    for a in todo:
        result = results.get(a["canonical_url"])
        problems = ["no response"] if result is None else check_response(a, result)
        raw_path, raw_bytes = None, None
        if not problems:
            raw_path = RAW_WEB_DIR / f"{a['document_id']}.html"
            raw_bytes = result.html.encode("utf-8")
            raw_path.write_bytes(raw_bytes)
        else:
            failures += 1
        records[a["document_id"]] = manifest_record(a, result, checked_at, raw_path, raw_bytes, problems, existing.get(a["document_id"]))
        state = "OK  " if not problems else "FAIL"
        size = f"{len(raw_bytes)} bytes" if raw_bytes else "; ".join(problems)
        print(f"{state} {a['document_id']}: {size}")
    write_manifest(records)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Acquire approved web pages as raw HTML.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--documents", nargs="+", metavar="DOCUMENT_ID")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    return acquire(None if args.all else args.documents)


if __name__ == "__main__":
    raise SystemExit(main())
