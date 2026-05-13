"""Source registry. Resolves the active Vaud corpus and computes its hash.

Hard rules:
  - Active corpus is `vd_2025`. The 2024 PDF (if present) is historical fallback only
    and must never override 2025.
  - Only official sources are added. No unofficial blogs, no AI-generated summaries.
  - Web sources from vd.ch get authority_rank=1 (same as PDF) per project directive.
"""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

from TaxAI2025.core import config
from TaxAI2025.rag.schema import RagSource


def sha256_of_file(path: Path, *, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def sha256_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def active_source() -> RagSource:
    """The currently active Vaud corpus, resolved from config."""
    path = config.active_corpus_path()
    return RagSource(
        source_id="vd_2025_instructions",
        title="Instructions générales sur la déclaration d'impôt 2025 (Canton de Vaud)",
        authority="official_canton",
        authority_rank=1,
        canton="VD",
        tax_year=2025,
        language="fr",
        url=None,
        local_path=str(path),
        source_hash=sha256_of_file(path),
        source_type="pdf",
        allowed_use=[
            "Vaud filing explanations",
            "field meanings",
            "ordinary-taxation explanations",
            "deduction definitions",
            "wealth and declaration guidance",
        ],
        forbidden_use=[
            "autonomous filing",
            "final legal advice",
            "tax optimization guarantee",
        ],
    )


def _web_source_from_config(cfg: dict[str, str]) -> RagSource:
    """Build a RagSource for a scraped vd.ch page.

    Web sources share authority_rank=1 with the PDF per project directive.
    Citation format: [vd.ch — Article Title]
    """
    url = cfg["url"]
    title = cfg["title"]
    # Hash is computed from the live content at scrape time; here we use the URL
    # as a stable identifier. The actual content hash is stamped into the index.
    return RagSource(
        source_id=f"vd_ch_{hashlib.sha256(url.encode()).hexdigest()[:8]}",
        title=title,
        authority="official_canton_web",
        authority_rank=1,
        canton="VD",
        tax_year=2025,
        language="fr",
        url=url,
        local_path="",
        source_hash=sha256_of_text(f"{url}:{title}"),
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


def active_web_sources() -> list[RagSource]:
    """Return web sources if SCRAPE_VD_CH is enabled.

    Controlled by env var `SCRAPE_VD_CH=true`. Disabled by default to keep
    the build reproducible and offline-capable.
    """
    if os.environ.get("SCRAPE_VD_CH", "").lower() not in ("1", "true", "yes"):
        return []

    from TaxAI2025.scraper.vd_ch import DEFAULT_PAGES

    return [_web_source_from_config(page) for page in DEFAULT_PAGES]


def historical_2024_source() -> RagSource | None:
    """If the 2024 instructions are still present, return them as a *historical* source.

    This source is NEVER preferred over `active_source()`. It exists only so that
    deprecation references can resolve cleanly.
    """
    candidates = [
        Path(config.REPO_ROOT) / "TaxAI2025" / "Instructions_generales_2024.pdf",
        Path(config.REPO_ROOT) / "Instructions_generales_2024.pdf",
        Path(config.REPO_ROOT) / "data" / "official" / "Instructions_generales_2024.pdf",
    ]
    for p in candidates:
        if p.is_file():
            return RagSource(
                source_id="vd_2024_instructions",
                title="Instructions générales sur la déclaration d'impôt 2024 (Canton de Vaud) — historical",
                authority="official_canton",
                authority_rank=99,  # de-prioritised vs. active 2025
                canton="VD",
                tax_year=2024,
                language="fr",
                url=None,
                local_path=str(p),
                source_hash=sha256_of_file(p),
                source_type="pdf",
                allowed_use=["historical reference only"],
                forbidden_use=[
                    "active filing guidance",
                    "answering questions about tax year 2025",
                    "overriding the 2025 source",
                ],
            )
    return None


def all_active_sources() -> list[RagSource]:
    """Sources used at retrieval time. Active corpus only — no historical."""
    return [active_source()] + active_web_sources()
