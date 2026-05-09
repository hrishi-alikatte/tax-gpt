"""Source registry. Resolves the active Vaud corpus and computes its hash.

Hard rules:
  - Active corpus is `vd_2025`. The 2024 PDF (if present) is historical fallback only
    and must never override 2025.
  - Only official sources are added. No unofficial blogs, no AI-generated summaries.
"""
from __future__ import annotations

import hashlib
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
    return [active_source()]
