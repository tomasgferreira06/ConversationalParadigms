"""Conservative web-corpus DISCOVERY for visitecoimbra.pt (D2).

This is not ingestion: it maps the site, classifies URLs with transparent rules
and measures overlap with the existing PDF corpus. It keeps page text in memory
only; nothing is chunked, embedded or indexed, and no LLM is used.

Usage:
    uv run python d2_rag/scripts/discover_web_corpus.py --discover
    uv run python d2_rag/scripts/discover_web_corpus.py --extract-samples URL [URL ...]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from crawl4ai import (
    AsyncWebCrawler,
    BFSDeepCrawlStrategy,
    CrawlerRunConfig,
    DomainFilter,
    FilterChain,
    HTTPCrawlerConfig,
    URLPatternFilter,
)
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy


D2_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = D2_ROOT / "web_discovery"
MANIFEST_PATH = D2_ROOT / "data" / "manifest.jsonl"

ROOT_URL = "https://visitecoimbra.pt/"
SITE_HOST = "visitecoimbra.pt"
USER_AGENT = "D2-RAG-discovery/0.1 (academic project; conservative crawl)"

# Safety limits, not targets.
MAX_DEPTH = 3
MAX_PAGES = 300
CONCURRENCY = 2
MEAN_DELAY_S = 1.5  # per-domain delay drawn from [1.5, 2.5] s
DELAY_RANGE_S = 1.0
COMMERCIAL_SAMPLE_PER_TYPE = 2

TRACKING_PARAMS = re.compile(r"^(utm_\w+|fbclid|gclid|mc_cid|mc_eid|_ga)$", re.IGNORECASE)

# Never fetched: admin/login/account, feeds, uploads (PDFs are only listed),
# taxonomy listings, theme templates, and commercial listings (sampled apart).
NO_FETCH_PATTERNS = [
    re.compile(p)
    for p in (
        r"/wp-(admin|json|login|content|includes)",
        r"/feed/?$",
        r"[?&](s|p|replytocom)=",
        r"/(account|profile|register|registration|password-reset|lost-password|sem-acesso)/?$",
        r"/agentes-e-profissionais/(entrar|registo)/?$",
        r"/(estrela|preco|tipos-de-alojamento|tipo-de-restaurante|ova_framework_hf_el)/",
        r"/(alojamentos|restaurantes)/[^/]+/?$",
        r"\.(pdf|jpe?g|png|gif|webp|svg|zip|docx?|xlsx?|mp4)$",
    )
]

# Ordered classification rules on the canonical path:
# (regex, page_type, category, status, reason). First match wins.
RULES: list[tuple[str, str, str | None, str, str]] = [
    (r"^/wp-content/", "asset", None, "excluded", "media/upload file (image or other asset)"),
    (r"^/$", "home", None, "review", "homepage: navigation hub, mostly teasers"),
    (r"^/(error-page|coming-soon|sem-acesso)/$", "system", None, "excluded", "system/placeholder page"),
    (r"^/(account|profile|register|registration|password-reset|lost-password)/$", "account", None, "excluded", "login/account page"),
    (r"^/agentes-e-profissionais/", "institutional", None, "excluded", "professional/press area, no visitor knowledge"),
    (r"^/submissao-de-alojamentos/$", "institutional", None, "excluded", "business submission form"),
    (r"^/(estrela|preco|tipos-de-alojamento|tipo-de-restaurante)/", "taxonomy", None, "excluded", "taxonomy listing"),
    (r"^/ova_framework_hf_el/", "template", None, "excluded", "theme header/footer template"),
    (r"^/alojamentos/[^/]+/$", "listing_accommodation", None, "excluded", "commercial accommodation listing (volatile, operational)"),
    (r"^/restaurantes/[^/]+/$", "listing_restaurant", None, "excluded", "commercial restaurant listing (volatile, operational)"),
    (r"^/experiencias/[^/]+/$", "experience", None, "review", "bookable experience: may mix cultural content with operator/price info"),
    (r"^/o-que-fazer/agenda-de-eventos/$", "agenda", None, "excluded", "events agenda (future/temporary events)"),
    (r"^/(praxis-beer-fest|strauss)/$", "event", None, "excluded", "single event/promotion page"),
    (r"^/o-que-fazer/(natal-em-coimbra|bienal-anozero)/$", "event", None, "excluded", "seasonal/periodic event page"),
    (r"^/compras/(coimbra-magic-land|fim-de-ano-em-coimbra|guns-n-roses)/$", "event", None, "excluded", "seasonal event/promotion page"),
    (r"^/viver-coimbra/blog/$", "blog_index", None, "excluded", "blog index"),
    (r"^/viver-coimbra/nomadas-digitais/$", "topic", None, "review", "residency/remote-work info, weak tourism knowledge"),
    (r"^/viver-coimbra/estudar-em-coimbra/erasmus/$", "topic", None, "review", "student mobility info, weak tourism knowledge"),
    (r"^/o-que-visitar/a-universidade-de-coimbra/$", "topic", "university_heritage", "candidate", "University of Coimbra heritage"),
    (r"^/o-que-visitar/cidade-patrimonio-da-humanidade/$", "topic", "university_heritage", "candidate", "UNESCO World Heritage"),
    (r"^/o-que-visitar/heranca-cultural-e-religiosa/$", "topic", "built_heritage", "candidate", "churches, monasteries, monuments"),
    (r"^/o-que-visitar/heranca-(mocarabe|judaica)/$", "topic", "city_history", "candidate", "historical heritage of a community"),
    (r"^/o-que-visitar/museus/$", "topic", "museums_collections", "candidate", "museums"),
    (r"^/o-que-visitar/(rotas-e-percursos|visitas-guiadas)/$", "topic", "visitor_orientation", "candidate", "routes / guided visits"),
    (r"^/o-que-visitar/a-volta-de-coimbra/$", "topic", "visitor_orientation", "review", "region around Coimbra: outside core city scope"),
    (r"^/roteiros-tematicos/[^/]+/$", "route", "visitor_orientation", "candidate", "thematic route (web counterpart of a municipal PDF)"),
    (r"^/viver-coimbra/lendas-e-figuras-historicas/", "topic", "city_history", "candidate", "legends and historical figures"),
    (r"^/viver-coimbra/(cancao-de-coimbra|republicas)/$", "topic", "culture_traditions", "candidate", "Coimbra song / student republics"),
    (r"^/viver-coimbra/estudar-em-coimbra/coimbra-dos-estudantes/$", "topic", "culture_traditions", "candidate", "academic traditions"),
    (r"^/viver-coimbra/tradicoes/", "topic", "culture_traditions", "candidate", "local traditions and crafts"),
    (r"^/viver-coimbra/vida-de-bairro/", "topic", None, "review", "neighbourhood life: mixes history with current commerce"),
    (r"^/gastronomia/restauracao/$", "listing_index", "gastronomy", "review", "restaurant directory page"),
    (r"^/gastronomia/", "topic", "gastronomy", "candidate", "gastronomy"),
    (r"^/o-que-fazer/natureza-e-rio/$", "topic", "landscape_gardens", "candidate", "nature and river"),
    (r"^/guia-pratico/(como-chegar|mover-se-pela-cidade)/$", "topic", "transport_access", "review", "transport: useful but volatile"),
    (r"^/guia-pratico/postos-de-informacao-turistica/$", "topic", "visitor_orientation", "review", "tourist offices: contacts/hours"),
    (r"^/guia-pratico/onde-ficar/$", "listing_index", "visitor_orientation", "review", "accommodation overview"),
    (r"^/guia-pratico/", "topic", "visitor_orientation", "candidate", "practical guide"),
    (r"^/compras/(lojas-historicas|o-antigo-kasbah|a-renovacao-da-baixa)/$", "topic", None, "review", "shopping page with historical content"),
    (r"^/compras/", "topic", None, "review", "shopping"),
    (r"^/o-que-fazer/", "topic", None, "review", "activities: mixed cultural/leisure content"),
    (r"^/viver-coimbra/", "topic", None, "review", "viver coimbra section"),
    (r"^/(o-que-visitar|o-que-fazer|gastronomia|guia-pratico|compras|viver-coimbra|roteiros-tematicos|planeie-a-sua-visita)/$", "section_index", None, "review", "section index: mostly teasers/links"),
]

PT_STOPWORDS = set("de a o que e do da em um para com não uma os no se na por mais as dos como mas ao das à pela pelo são".split())
EN_STOPWORDS = set("the and of to in is for with on that this are from by at".split())

VOLATILE_PATTERNS = {
    "price": re.compile(r"\d+(?:[.,]\d+)?\s?€|€\s?\d"),
    "time": re.compile(r"\b\d{1,2}[h:]\d{2}\b"),
    "year_recent": re.compile(r"\b202[3-9]\b"),
    "operational_terms": re.compile(r"\b(horário|horários|bilhete|bilheteira|reserva|reservas|inscrições|preço|preços|marcação)\b", re.IGNORECASE),
}


# ---------------------------------------------------------------------------
# URL handling
# ---------------------------------------------------------------------------


def canonicalize(url: str) -> str:
    """https, no www, no fragment, no tracking params, trailing slash on paths."""

    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path or "/"
    if not re.search(r"\.[a-z0-9]{2,4}$", path, re.IGNORECASE) and not path.endswith("/"):
        path += "/"
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not TRACKING_PARAMS.match(k)])
    return urlunsplit(("https", host, path, query, ""))


def is_internal(url: str) -> bool:
    return urlsplit(url).netloc.lower().removeprefix("www.") == SITE_HOST


def is_no_fetch(url: str) -> bool:
    return any(pattern.search(url) for pattern in NO_FETCH_PATTERNS)


def classify_path(url: str) -> tuple[str, str | None, str, str]:
    path = urlsplit(url).path
    for pattern, page_type, category, status, reason in RULES:
        if re.search(pattern, path):
            return page_type, category, status, reason
    return "unknown", None, "review", "no rule matched"


# ---------------------------------------------------------------------------
# robots.txt and sitemap (plain HTTP, stdlib)
# ---------------------------------------------------------------------------


def _get(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


def read_robots_and_sitemaps() -> tuple[dict[str, Any], list[tuple[str, str]]]:
    """Return (robots report, [(url, sitemap_name)]) from the declared sitemaps."""

    status, robots_text = _get(ROOT_URL + "robots.txt")
    parser = RobotFileParser()
    parser.parse(robots_text.splitlines())
    sitemaps = parser.site_maps() or []
    report = {
        "robots_url": ROOT_URL + "robots.txt",
        "status": status,
        "content": robots_text,
        "root_allowed": parser.can_fetch(USER_AGENT, ROOT_URL),
        "sitemaps": sitemaps,
        "child_sitemaps": {},
    }
    urls: list[tuple[str, str]] = []
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for sitemap_url in sitemaps:
        _status, index_xml = _get(sitemap_url)
        children = [loc.text for loc in ET.fromstring(index_xml).findall("sm:sitemap/sm:loc", namespace)]
        for child in children:
            _status, child_xml = _get(child)
            name = re.sub(r"^.*wp-sitemap-|-\d+\.xml$", "", child)
            locs = [loc.text for loc in ET.fromstring(child_xml).findall("sm:url/sm:loc", namespace)]
            report["child_sitemaps"][name] = len(locs)
            urls.extend((loc, name) for loc in locs)
    return report, urls


# ---------------------------------------------------------------------------
# Crawling (Crawl4AI)
# ---------------------------------------------------------------------------


def _run_config(deep: bool) -> CrawlerRunConfig:
    strategy = None
    if deep:
        strategy = BFSDeepCrawlStrategy(
            max_depth=MAX_DEPTH,
            max_pages=MAX_PAGES,
            include_external=False,
            filter_chain=FilterChain(
                [
                    DomainFilter(allowed_domains=[SITE_HOST]),
                    URLPatternFilter(patterns=NO_FETCH_PATTERNS, reverse=True),
                ]
            ),
        )
    return CrawlerRunConfig(
        check_robots_txt=True,
        deep_crawl_strategy=strategy,
        semaphore_count=CONCURRENCY,
        mean_delay=MEAN_DELAY_S,
        max_range=DELAY_RANGE_S,
        verbose=False,
    )


def _crawler() -> AsyncWebCrawler:
    # Plain HTTP fetching: the site is server-rendered, so no browser is needed.
    strategy = AsyncHTTPCrawlerStrategy(
        browser_config=HTTPCrawlerConfig(headers={"User-Agent": USER_AGENT})
    )
    return AsyncWebCrawler(crawler_strategy=strategy)


async def crawl(sitemap_urls: list[tuple[str, str]]) -> list[Any]:
    """BFS from the root, then sitemap pages the BFS did not reach."""

    async with _crawler() as crawler:
        results = list(await crawler.arun(ROOT_URL, config=_run_config(deep=True)))
        if not results or not results[0].success:
            error = results[0].error_message if results else "no result"
            raise RuntimeError(f"Root page could not be crawled; stopping. {error}")

        seen = {canonicalize(r.url) for r in results}
        seen |= {canonicalize(r.redirected_url) for r in results if r.redirected_url}
        gaps = [canonicalize(u) for u, _ in sitemap_urls if not is_no_fetch(u)]
        gaps = list(dict.fromkeys(u for u in gaps if u not in seen))
        samples: list[str] = []
        for listing in ("alojamentos", "restaurantes"):
            listing_urls = sorted(canonicalize(u) for u, name in sitemap_urls if name == f"posts-{listing}")
            samples += listing_urls[:COMMERCIAL_SAMPLE_PER_TYPE]
        budget = MAX_PAGES - len(results)
        extra = (gaps + samples)[: max(0, budget)]
        if extra:
            results += list(await crawler.arun_many(extra, config=_run_config(deep=False)))
    return results


# ---------------------------------------------------------------------------
# Page analysis
# ---------------------------------------------------------------------------


def _html_attr(html: str, pattern: str) -> str | None:
    match = re.search(pattern, html or "", re.IGNORECASE)
    return match.group(1) if match else None


def detect_language(html: str, text: str) -> tuple[str | None, str | None]:
    declared = _html_attr(html, r"<html[^>]*\blang=\"([^\"]+)\"")
    words = re.findall(r"[a-záàâãéêíóôõúç]+", text.lower())
    pt = sum(w in PT_STOPWORDS for w in words)
    en = sum(w in EN_STOPWORDS for w in words)
    content = "pt" if pt > 2 * en and pt >= 5 else ("en" if en > 2 * pt and en >= 5 else None)
    return declared, content


def boilerplate_lines(markdowns: list[str], min_share: float = 0.4) -> set[str]:
    """Lines that repeat on at least min_share of the pages (menus, footer)."""

    counts: Counter[str] = Counter()
    for markdown in markdowns:
        counts.update({line.strip() for line in markdown.splitlines() if line.strip()})
    threshold = max(2, int(len(markdowns) * min_share))
    return {line for line, count in counts.items() if count >= threshold}


def main_text(markdown: str, boilerplate: set[str]) -> str:
    kept = [l for l in markdown.splitlines() if l.strip() and l.strip() not in boilerplate]
    text = "\n".join(kept)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # keep link text only
    return text


def _shingles(text: str, n: int = 5) -> set[tuple[str, ...]]:
    words = re.findall(r"[^\W_]+", text.lower())
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def load_pdf_corpus() -> dict[str, set]:
    corpus = {}
    for record in (json.loads(l) for l in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if l.strip()):
        markdown = (D2_ROOT / record["processed_path"]).read_text(encoding="utf-8")
        markdown = re.sub(r"<!--.*?-->", " ", markdown)
        corpus[record["document_id"]] = _shingles(markdown)
    return corpus


def pdf_overlap(text: str, corpus: dict[str, set]) -> tuple[str | None, float]:
    shingles = _shingles(text)
    if not shingles:
        return None, 0.0
    best = max(corpus, key=lambda doc: len(shingles & corpus[doc]))
    containment = round(len(shingles & corpus[best]) / len(shingles), 3)
    return (best if containment > 0 else None), containment


# Language tag as a filename token, e.g. _ESP_V1_1, _FR_compressed, -uk.pdf, .PT_.pdf
PDF_LANGUAGE_TOKEN = re.compile(r"[_.-](esp?|fr|uk|en|de|it|pt)(?=[_.-])", re.IGNORECASE)


def classify_pdf(url: str, manifest: list[dict[str, Any]]) -> tuple[str, str]:
    filename = urlsplit(url).path.rsplit("/", 1)[-1]
    known = {r["original_filename"].lower(): r["document_id"] for r in manifest}
    if filename.lower() in known:
        return "already_in_corpus", f"same filename as raw PDF of {known[filename.lower()]}"
    languages = {m.lower() for m in PDF_LANGUAGE_TOKEN.findall(filename)}
    if languages and "pt" not in languages:
        return "irrelevant", f"non-Portuguese edition (language token {sorted(languages)} in filename)"
    if "pt" in languages:
        return "new_candidate", "Portuguese edition not in the PDF corpus (filename); not downloaded"
    return "unknown", "no language token and not in the corpus; needs manual review"


def reclassify_pdfs() -> None:
    """Re-apply the filename-only PDF rule to discovered_urls.jsonl (no network)."""

    manifest = [json.loads(l) for l in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    path = OUTPUT_DIR / "discovered_urls.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        if row["page_type"] == "pdf":
            row["status"], row["reason"] = classify_pdf(row["url"], manifest)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary_path = OUTPUT_DIR / "crawl_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["by_status"] = dict(Counter(r["status"] for r in rows))
    summary["pdfs"] = [{"url": r["url"], "status": r["status"], "reason": r["reason"]} for r in rows if r["page_type"] == "pdf"]
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(Counter(p["status"] for p in summary["pdfs"]), ensure_ascii=False))


def volatility(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in VOLATILE_PATTERNS.items()}


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    crawled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    robots, sitemap_urls = read_robots_and_sitemaps()
    if not robots["root_allowed"]:
        raise RuntimeError("robots.txt disallows the root URL for this user agent; stopping.")
    results = asyncio.run(crawl(sitemap_urls))

    manifest = [json.loads(l) for l in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    corpus = load_pdf_corpus()
    ok_markdowns = [r.markdown.raw_markdown for r in results if r.success and r.markdown]
    boilerplate = boilerplate_lines(ok_markdowns)

    records: dict[str, dict[str, Any]] = {}
    link_sources: dict[str, dict[str, Any]] = {}

    for url, sitemap_name in sitemap_urls:
        link_sources.setdefault(canonicalize(url), {"sources": set(), "parent_url": None})["sources"].add(f"sitemap:{sitemap_name}")

    for result in results:
        requested = canonicalize(result.url)
        meta = result.metadata or {}
        for link in (result.links or {}).get("internal", []):
            href = link.get("href", "")
            if href.startswith("http") and is_internal(href):
                entry = link_sources.setdefault(canonicalize(href), {"sources": set(), "parent_url": requested})
                entry["sources"].add("link")
                entry["parent_url"] = entry["parent_url"] or requested

        html = result.html or ""
        final = canonicalize(result.redirected_url or result.url)
        declared_canonical = _html_attr(html, r"<link[^>]+rel=\"canonical\"[^>]+href=\"([^\"]+)\"")
        canonical = canonicalize(declared_canonical) if declared_canonical else final
        headers = {k.lower(): v for k, v in (result.response_headers or {}).items()}
        raw_markdown = result.markdown.raw_markdown if result.success and result.markdown else ""
        text = main_text(raw_markdown, boilerplate)
        declared_lang, content_lang = detect_language(html, text)
        best_doc, containment = pdf_overlap(text, corpus)
        records[requested] = {
            "url": requested,
            "final_url": final,
            "canonical_url": canonical,
            "fetched": True,
            "success": bool(result.success),
            "status_code": result.status_code,
            "error": None if result.success else (result.error_message or "")[:200],
            "content_type": headers.get("content-type"),
            "title": meta.get("title"),
            "description": meta.get("description"),
            "html_lang": declared_lang,
            "content_lang": content_lang,
            "crawl_depth": meta.get("depth"),
            "parent_url": meta.get("parent_url"),
            "raw_word_count": len(raw_markdown.split()),
            "main_word_count": len(text.split()),
            "headings": re.findall(r"^#{1,3} (.+)$", raw_markdown, re.MULTILINE)[:12],
            "volatility": volatility(text),
            "pdf_overlap_doc": best_doc,
            "pdf_overlap": containment,
            "_shingles": _shingles(text),
        }

    # Discovered but not fetched (filtered, PDFs, outside depth/budget).
    for url, source in link_sources.items():
        if url in records:
            records[url]["sources"] = sorted(source["sources"])
            continue
        records[url] = {
            "url": url, "final_url": None, "canonical_url": url, "fetched": False,
            "success": None, "status_code": None, "error": None, "content_type": None,
            "title": None, "description": None, "html_lang": None, "content_lang": None,
            "crawl_depth": None, "parent_url": source["parent_url"], "raw_word_count": None,
            "main_word_count": None, "headings": [], "volatility": None,
            "pdf_overlap_doc": None, "pdf_overlap": None, "_shingles": set(),
            "sources": sorted(source["sources"]),
        }
    for record in records.values():
        record.setdefault("sources", ["crawl"])
        record["crawled_at"] = crawled_at

    _apply_classification(records, manifest)
    _write_outputs(records, robots, results)


def _apply_classification(records: dict[str, dict[str, Any]], manifest: list[dict[str, Any]]) -> None:
    canonical_owner: dict[str, str] = {}
    for url in sorted(records):
        record = records[url]
        if urlsplit(url).path.lower().endswith(".pdf"):
            status, reason = classify_pdf(url, manifest)
            record.update(page_type="pdf", category=None, status=status, reason=reason)
            continue
        page_type, category, status, reason = classify_path(record["canonical_url"])
        record.update(page_type=page_type, category=category, status=status, reason=reason)
        if not record["fetched"]:
            if status in ("candidate", "review"):
                record["status"], record["reason"] = "review", f"{reason}; not fetched (outside depth/budget or filtered)"
            continue
        if not record["success"] or (record["status_code"] or 0) >= 400:
            error = record["error"] or ""
            http_status = re.search(r"HTTP (\d{3})", error)
            if http_status and record["status_code"] is None:
                record["status_code"] = int(http_status.group(1))
            record["status"] = "unavailable"
            if "O_NOFOLLOW" in error:
                record["reason"] = (
                    "non-HTML response (text/xml) that the HTTP fetcher tried to save as a "
                    "file and failed on Windows; manual check showed a WordPress critical-error page"
                )
            else:
                record["reason"] = f"fetch failed: HTTP {record['status_code']}"
            continue
        declared = (record["html_lang"] or "").lower()
        if (declared and not declared.startswith("pt")) or record["content_lang"] == "en":
            record["status"] = "excluded"
            record["reason"] = f"non-Portuguese page (html lang={record['html_lang']}, content={record['content_lang']})"
            continue
        owner = canonical_owner.setdefault(record["canonical_url"], url)
        if owner != url and record["status"] in ("candidate", "review"):
            record["status"], record["reason"] = "duplicate", f"same canonical URL as {owner}"
            continue
        if record["status"] in ("candidate", "review") and record["main_word_count"] < 80:
            if record["page_type"] == "experience":
                record["status"] = "review"
                record["reason"] = (
                    f"only {record['main_word_count']} words beyond the site template in the "
                    "server HTML; description is probably loaded dynamically (not assessed)"
                )
            else:
                record["status"] = "excluded"
                record["reason"] = f"near-empty main content ({record['main_word_count']} words after boilerplate removal)"
            continue
        if record["status"] == "candidate" and (record["pdf_overlap"] or 0) >= 0.6:
            record["status"] = "already_in_corpus"
            record["reason"] = f"{record['pdf_overlap']:.0%} of its 5-grams appear in PDF {record['pdf_overlap_doc']}"

    # Web-to-web near duplicates among the remaining candidate/review pages.
    live = [r for r in records.values() if r["status"] in ("candidate", "review") and r["_shingles"]]
    live.sort(key=lambda r: (-len(r["_shingles"]), r["url"]))
    for i, record in enumerate(live):
        for bigger in live[:i]:
            if bigger["status"] == "duplicate":
                continue
            overlap = len(record["_shingles"] & bigger["_shingles"]) / len(record["_shingles"])
            if overlap >= 0.8:
                record["status"], record["reason"] = "duplicate", f"{overlap:.0%} of its text is contained in {bigger['url']}"
                break


def _write_outputs(records: dict[str, dict[str, Any]], robots: dict[str, Any], results: list[Any]) -> None:
    rows = [{k: v for k, v in records[url].items() if not k.startswith("_")} for url in sorted(records)]
    with (OUTPUT_DIR / "discovered_urls.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (OUTPUT_DIR / "candidate_urls.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            if row["status"] in ("candidate", "review", "already_in_corpus") and row["page_type"] != "pdf":
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "config": {
            "root_url": ROOT_URL, "strategy": "BFSDeepCrawlStrategy + sitemap gaps",
            "fetcher": "AsyncHTTPCrawlerStrategy", "check_robots_txt": True,
            "max_depth": MAX_DEPTH, "max_pages": MAX_PAGES, "concurrency": CONCURRENCY,
            "delay_s": [MEAN_DELAY_S, MEAN_DELAY_S + DELAY_RANGE_S], "user_agent": USER_AGENT,
            "domain": SITE_HOST, "commercial_sample_per_type": COMMERCIAL_SAMPLE_PER_TYPE,
        },
        "robots": {k: v for k, v in robots.items() if k != "content"},
        "robots_txt": robots["content"],
        "fetched": len(results),
        "fetched_ok": sum(1 for r in results if r.success),
        "redirected": sum(1 for r in results if r.redirected_url and canonicalize(r.redirected_url) != canonicalize(r.url)),
        "discovered": len(rows),
        "by_status": dict(Counter(r["status"] for r in rows)),
        "by_page_type": dict(Counter(r["page_type"] for r in rows)),
        "by_category": dict(Counter(str(r["category"]) for r in rows if r["status"] in ("candidate", "already_in_corpus"))),
        "html_lang": dict(Counter(str(r["html_lang"]) for r in rows if r["fetched"])),
        "pdfs": [{"url": r["url"], "status": r["status"], "reason": r["reason"]} for r in rows if r["page_type"] == "pdf"],
    }
    (OUTPUT_DIR / "crawl_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    print(json.dumps({k: summary[k] for k in ("fetched", "fetched_ok", "redirected", "discovered", "by_status", "by_page_type", "by_category", "html_lang")}, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------------------
# Sample extraction (a handful of pages, for quality assessment only)
# ---------------------------------------------------------------------------


async def _extract(urls: list[str]) -> list[Any]:
    async with _crawler() as crawler:
        return list(await crawler.arun_many(urls, config=_run_config(deep=False)))


def extract_samples(urls: list[str]) -> None:
    sample_dir = OUTPUT_DIR / "sample_extractions"
    sample_dir.mkdir(parents=True, exist_ok=True)
    for result in asyncio.run(_extract([canonicalize(u) for u in urls])):
        slug = urlsplit(canonicalize(result.url)).path.strip("/").replace("/", "__") or "home"
        markdown = result.markdown.raw_markdown if result.success and result.markdown else ""
        header = (
            "<!-- sample extraction for quality assessment only; not corpus -->\n"
            f"<!-- url: {canonicalize(result.url)} | status: {result.status_code} | "
            f"title: {(result.metadata or {}).get('title')} | words: {len(markdown.split())} -->\n\n"
        )
        (sample_dir / f"{slug}.md").write_text(header + markdown, encoding="utf-8", newline="\n")
        print(f"{slug}: status={result.status_code} words={len(markdown.split())}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="visitecoimbra.pt corpus discovery (no ingestion).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--discover", action="store_true")
    group.add_argument("--extract-samples", nargs="+", metavar="URL")
    group.add_argument("--reclassify-pdfs", action="store_true", help="re-apply PDF filename rules offline")
    args = parser.parse_args(argv)
    if args.discover:
        discover()
    elif args.reclassify_pdfs:
        reclassify_pdfs()
    else:
        extract_samples(args.extract_samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
