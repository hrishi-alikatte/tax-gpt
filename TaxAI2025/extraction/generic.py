"""Generic structured extraction for documents the registry cannot classify.

This path intentionally does not promote values into canonical `TaxFact`
objects. Unknown documents can contain useful clues, but a human must label a
generic fact before it can become a confirmed canonical tax value.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from TaxAI2025.core.documents import DocumentRecord
from TaxAI2025.extraction.confidence import score_llm_extraction
from TaxAI2025.extraction.ocr import PageText


class GenericFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label_en: str
    label_fr: str | None = None
    value: Any
    currency: str | None = None
    source_doc: str
    source_page: int
    confidence: float | None = None
    extracted_at: datetime
    confirmed_by_user: bool = False
    pending_user_review: bool = True

    @field_validator("label_en")
    @classmethod
    def _label_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("label_en must be non-empty")
        return v

    @field_validator("source_doc")
    @classmethod
    def _source_doc_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source_doc must be non-empty")
        return v

    @field_validator("source_page")
    @classmethod
    def _source_page_one_indexed(cls, v: int) -> int:
        if v < 1:
            raise ValueError("source_page must be >= 1")
        return v


def _generic_schema(page_count: int) -> dict[str, Any]:
    fact_obj = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "label_en",
            "label_fr",
            "value",
            "currency",
            "source_page",
            "confidence",
        ],
        "properties": {
            "label_en": {"type": "string"},
            "label_fr": {"type": ["string", "null"]},
            "value": {"type": ["number", "string", "boolean", "null"]},
            "currency": {"type": ["string", "null"]},
            "source_page": {"type": "integer", "minimum": 1, "maximum": page_count},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
    }
    return {
        "title": "GenericDocumentFacts",
        "type": "object",
        "additionalProperties": False,
        "required": ["facts"],
        "properties": {"facts": {"type": "array", "items": fact_obj}},
    }


def extract_generic_facts(
    record: DocumentRecord,
    pages: list[PageText],
) -> list[GenericFact]:
    """Extract unlabeled facts from an unknown document via structured LLM.

    Returns pending, unconfirmed `GenericFact` rows. Callers may show them for
    user labeling and later promote known values through an explicit mapping.
    """
    if record.document_type != "unknown":
        return []
    if not pages:
        return []

    from TaxAI2025.ai import model_router

    page_count = max((p.pdf_page for p in pages), default=1)
    schema = _generic_schema(page_count)
    text_blob = "\n\n".join(f"[page {p.pdf_page}]\n{p.text}" for p in pages)
    system = (
        "Extract factual values from an unclassified Swiss tax document. "
        "Return strict JSON only. Do not map to canonical tax fields. "
        "Only include values explicitly present in the text with source pages. "
        "If unsure, omit the fact."
    )
    user = (
        f"Filename: {record.filename}\n"
        f"Document text:\n{text_blob}\n\n"
        "Return generic facts for user review."
    )
    try:
        payload = model_router.generate_json(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            schema=schema,
            purpose="document_extraction",
        )
    except Exception:  # noqa: BLE001
        return []

    raw_facts = payload.get("facts") if isinstance(payload, dict) else None
    if not isinstance(raw_facts, list):
        return []

    now = datetime.utcnow()
    valid_pages = {p.pdf_page for p in pages}
    facts: list[GenericFact] = []
    for raw in raw_facts:
        if not isinstance(raw, dict):
            continue
        page = raw.get("source_page")
        if not isinstance(page, int) or page not in valid_pages:
            continue
        value = raw.get("value")
        if value is None:
            continue
        try:
            facts.append(
                GenericFact(
                    label_en=raw.get("label_en"),
                    label_fr=raw.get("label_fr"),
                    value=value,
                    currency=raw.get("currency"),
                    source_doc=record.filename,
                    source_page=page,
                    confidence=score_llm_extraction(raw),
                    extracted_at=now,
                    confirmed_by_user=False,
                    pending_user_review=True,
                )
            )
        except ValueError:
            continue
    return facts


__all__ = ["GenericFact", "extract_generic_facts"]
