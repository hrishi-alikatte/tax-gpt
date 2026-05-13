"""scraper package — web content ingestion for RAG."""
from TaxAI2025.scraper.vd_ch import (
    DEFAULT_PAGES,
    WebPageChunk,
    page_to_rag_source,
    scrape_all_pages,
    scrape_page,
)

__all__ = [
    "DEFAULT_PAGES",
    "WebPageChunk",
    "page_to_rag_source",
    "scrape_all_pages",
    "scrape_page",
]
