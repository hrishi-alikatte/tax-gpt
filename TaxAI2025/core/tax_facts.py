"""TaxFact schema — every extracted value crosses this boundary.

Verbatim contract from `docs/ARCHITECTURE.md` §Key contracts. Downstream
code must refuse any TaxFact with `confirmed_by_user == False`. The
extraction layer must never set `confirmed_by_user = True`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ExtractionMethod = Literal["regex", "pdf_text", "ocr", "llm_structured"]


class TaxFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_field: str
    value: Any
    source_doc: str
    source_page: int
    snippet: str | None = None
    source_bbox: tuple[int, int, int, int] | None = None
    confidence: float | None = None
    extraction_method: ExtractionMethod
    model_name: str | None = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_by_user: bool = False

    @field_validator("source_doc")
    @classmethod
    def _source_doc_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source_doc must be a non-empty filename")
        return v

    @field_validator("source_page")
    @classmethod
    def _page_one_indexed(cls, v: int) -> int:
        if v < 1:
            raise ValueError("source_page must be >= 1 (PDF pages are 1-indexed)")
        return v

    @field_validator("confidence")
    @classmethod
    def _confidence_in_unit_interval(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be in [0.0, 1.0]")
        return v

    @field_validator("canonical_field")
    @classmethod
    def _canonical_field_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("canonical_field must be a non-empty string")
        return v


def validate_provenance(fact: TaxFact) -> None:
    """Raise if a TaxFact is missing the source pointer or method.

    Used by extractors as a final gate before returning facts upstream.
    """
    if not fact.source_doc:
        raise ValueError(f"TaxFact {fact.canonical_field!r} missing source_doc")
    if fact.source_page is None or fact.source_page < 1:
        raise ValueError(f"TaxFact {fact.canonical_field!r} missing source_page")
    if not fact.extraction_method:
        raise ValueError(
            f"TaxFact {fact.canonical_field!r} missing extraction_method"
        )
