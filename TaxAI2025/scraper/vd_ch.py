"""vd.ch web scraper for Vaud tax content.

Fetches official HTML content from vd.ch tax pages, converts to clean text,
and produces Chroma-compatible chunks for RAG ingestion.

All sources get authority_rank=1 (same as the PDF) with citation format:
[vd.ch — Article Title]
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Key vd.ch pages for employed C-permit residents in Vaud
# Sorted by priority (most relevant for our scope first)
DEFAULT_PAGES = [
    {
        "url": "https://www.vd.ch/etat-droit-finances/impots/impots-pour-les-individus/les-deductions",
        "title": "Les déductions",
        "topic": "deductions",
    },
    {
        "url": "https://www.vd.ch/etat-droit-finances/impots/impots-pour-les-individus",
        "title": "Impôts pour les individus",
        "topic": "overview",
    },
    {
        "url": "https://www.vd.ch/prestation/remplir-ma-declaration-dimpot-2025-avec-la-prestation-vaudtax-pour-les-individus-personnes-physiques",
        "title": "Remplir ma déclaration d'impôt 2025 avec la prestation VaudTax",
        "topic": "filling-guide",
    },
]

CHUNK_SIZE = 1100
CHUNK_OVERLAP = 200
SEPARATORS = ["\n\n", "\n", ". ", "•", " ", ""]


@dataclass(frozen=True)
class WebPageChunk:
    """A single chunk from a scraped web page."""

    chunk_id: str
    text: str
    source_url: str
    source_title: str
    topic: str
    language: str = "fr"


def _fetch_page(url: str) -> str:
    """Fetch raw HTML from a URL."""
    import urllib.request
    import urllib.error

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-CH,fr;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        logger.error("HTTP %d fetching %s: %s", e.code, url, e.reason)
        raise
    except Exception as e:
        logger.error("Failed to fetch %s: %s", url, e)
        raise


def _extract_text(html: str) -> str:
    """Extract readable text from HTML, stripping scripts/styles/nav."""
    # Remove script/style tags and their content
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Extract text from remaining HTML
    text = re.sub(r"<[^>]+>", " ", html)

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)

    return text.strip()


def _clean_vd_ch_text(text: str) -> str:
    """Clean vd.ch-specific artifacts from text."""
    # Remove cookie consent banners
    text = re.sub(
        r"En continuant.*?(?:cookies|politique).*?\.",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Remove navigation breadcrumbs
    text = re.sub(r"Accueil\s*›\s*.*?\s*›", "", text)
    # Remove social share prompts
    text = re.sub(r"Partager sur.*?\.", "", text)
    # Clean up multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_text(text: str) -> list[str]:
    """Split text into overlapping chunks."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
    )
    return splitter.split_text(text)


def scrape_page(
    url: str,
    title: str,
    topic: str,
    fetch_fn: Any | None = None,
) -> list[WebPageChunk]:
    """Scrape a single vd.ch page and return chunks.

    Args:
        url: Page URL
        title: Human-readable title for citations
        topic: Topic tag for filtering
        fetch_fn: Optional override for fetching (for testing)

    Returns:
        List of WebPageChunk objects
    """
    fetch = fetch_fn or _fetch_page
    logger.info("Scraping: %s", url)

    html = fetch(url)
    text = _extract_text(html)
    text = _clean_vd_ch_text(text)

    if not text or len(text) < 100:
        logger.warning("Page %s produced very little text (%d chars)", url, len(text))
        return []

    chunks = _split_text(text)
    result: list[WebPageChunk] = []
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]

    for i, chunk_text in enumerate(chunks):
        chunk_id = f"vd_ch_{url_hash}_c{i:03d}"
        result.append(
            WebPageChunk(
                chunk_id=chunk_id,
                text=chunk_text,
                source_url=url,
                source_title=title,
                topic=topic,
            )
        )

    logger.info("Scraped %s: %d chunks, ~%d chars total", url, len(result), len(text))
    return result


def scrape_all_pages(
    pages: list[dict[str, str]] | None = None,
    fetch_fn: Any | None = None,
) -> list[WebPageChunk]:
    """Scrape all configured vd.ch pages.

    Args:
        pages: List of page configs (defaults to DEFAULT_PAGES)
        fetch_fn: Optional override for fetching (for testing)

    Returns:
        Combined list of chunks from all pages
    """
    pages = pages or DEFAULT_PAGES
    all_chunks: list[WebPageChunk] = []

    for page in pages:
        try:
            chunks = scrape_page(
                url=page["url"],
                title=page["title"],
                topic=page["topic"],
                fetch_fn=fetch_fn,
            )
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error("Failed to scrape %s: %s", page["url"], e)
            # Continue with other pages — partial success is better than total failure

    logger.info(
        "Total scraped: %d chunks from %d pages",
        len(all_chunks),
        len(pages),
    )
    return all_chunks


def page_to_rag_source(
    url: str,
    title: str,
    content_hash: str,
) -> "RagSource":
    """Convert a scraped page config to a RagSource for the ingestion pipeline."""
    from TaxAI2025.rag.schema import RagSource

    return RagSource(
        source_id=f"vd_ch_{hashlib.sha256(url.encode()).hexdigest()[:8]}",
        title=title,
        authority="official_canton",
        authority_rank=1,
        canton="VD",
        tax_year=2025,
        language="fr",
        url=url,
        local_path="",
        source_hash=content_hash,
        source_type="html",
        allowed_use=[
            "Vaud filing explanations",
            "field meanings",
            "deduction definitions",
        ],
        forbidden_use=[
            "autonomous filing",
            "final legal advice",
            "tax optimization guarantee",
        ],
    )
