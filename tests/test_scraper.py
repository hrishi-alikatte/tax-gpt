"""Tests for vd.ch web scraper.

All tests are fully offline — no live HTTP requests."""
from __future__ import annotations

import pytest

from TaxAI2025.scraper.vd_ch import (
    DEFAULT_PAGES,
    WebPageChunk,
    _clean_vd_ch_text,
    _extract_text,
    _split_text,
    page_to_rag_source,
    scrape_all_pages,
    scrape_page,
)

SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head><title>Les déductions | État de Vaud</title></head>
<body>
<nav>Accueil › Impôts › Individus › Les déductions</nav>
<main>
<h1>Les déductions</h1>
<p>En cas de télétravail, les règles fiscales n'ont pas été modifiées pour 2025.</p>
<p>Code 140 : Frais de déplacement — calculée pour 240 jours ouvrables.</p>
<p>Code 150 : Frais de repas. Les frais doivent être effectivement engagés.</p>
<p>Code 160 : Autres frais professionnels (3% du revenu net).</p>
</main>
<footer>Partager sur Facebook.</footer>
</body>
</html>
"""


def test_extract_text_strips_scripts_and_tags():
    text = _extract_text(SAMPLE_HTML)
    assert "<script>" not in text
    assert "<style>" not in text
    assert "<nav>" not in text
    assert "<footer>" not in text
    # Content should survive
    assert "Les déductions" in text
    assert "Code 140" in text
    assert "télétravail" in text


def test_clean_vd_ch_text_removes_cookie_boilerplate():
    raw = "En continuant à naviguer, vous acceptez les cookies.\n\nCode 140 text."
    cleaned = _clean_vd_ch_text(raw)
    assert "cookies" not in cleaned
    assert "Code 140" in cleaned


def test_split_text_produces_reasonable_chunks():
    long_text = "Word. " * 500  # ~3000 chars
    chunks = _split_text(long_text)
    assert len(chunks) > 1
    assert all(len(c) <= 1200 for c in chunks)


def test_scrape_page_with_mock_fetch():
    def fake_fetch(url: str) -> str:
        return SAMPLE_HTML

    chunks = scrape_page(
        url="https://vd.ch/test",
        title="Test Deductions",
        topic="deductions",
        fetch_fn=fake_fetch,
    )
    assert len(chunks) > 0
    first = chunks[0]
    assert isinstance(first, WebPageChunk)
    assert first.source_url == "https://vd.ch/test"
    assert first.source_title == "Test Deductions"
    assert first.topic == "deductions"
    assert first.text  # not empty
    # IDs should be stable
    assert all(c.chunk_id.startswith("vd_ch_") for c in chunks)


def test_scrape_all_pages_skips_failed_pages():
    pages = [
        {"url": "https://vd.ch/good", "title": "Good", "topic": "good"},
        {"url": "https://vd.ch/bad", "title": "Bad", "topic": "bad"},
    ]

    def fake_fetch(url: str) -> str:
        if "bad" in url:
            raise ConnectionError("timeout")
        return SAMPLE_HTML

    chunks = scrape_all_pages(pages=pages, fetch_fn=fake_fetch)
    assert len(chunks) > 0
    assert all(c.source_url == "https://vd.ch/good" for c in chunks)


def test_scrape_page_returns_empty_for_minimal_html():
    def fetch_minimal(url: str) -> str:
        return "<html><body></body></html>"

    chunks = scrape_page(
        url="https://vd.ch/empty",
        title="Empty",
        topic="empty",
        fetch_fn=fetch_minimal,
    )
    assert chunks == []


def test_default_pages_list_exists():
    assert len(DEFAULT_PAGES) > 0
    for page in DEFAULT_PAGES:
        assert "url" in page
        assert "title" in page
        assert "topic" in page
        assert page["url"].startswith("https://")


def test_page_to_rag_source():
    rs = page_to_rag_source(
        url="https://vd.ch/deductions",
        title="Les déductions",
        content_hash="abc123",
    )
    assert rs.source_id.startswith("vd_ch_")
    assert rs.title == "Les déductions"
    assert rs.authority_rank == 1
    assert rs.source_type == "html"
    assert rs.url == "https://vd.ch/deductions"
