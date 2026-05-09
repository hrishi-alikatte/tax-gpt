"""DocumentRecord + DocumentType for the extraction pipeline.

Known types come from `docs/DOMAIN_MODEL.md` §3. `unknown` is a sentinel
reserved for the case where neither heuristics nor LLM fallback can decide.
Downstream rules treat `unknown` as "ask the user".
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


DocumentType = Literal[
    "salary_certificate",
    "health_insurance_premium",
    "daycare_invoice",
    "pillar_3a_certificate",
    "transport_pass",
    "bank_year_end_statement",
    "mortgage_interest_statement",
    "alimony_paid_received",
    "donation_receipt",
    "parental_support_receipt",
    "medical_bills_unreimbursed",
    "education_invoice",
    "second_pillar_buyback_attestation",
    "foreign_income_attestation",
    "disability_proof",
    "unemployment_benefits_attestation",
    "unknown",
]


KNOWN_DOCUMENT_TYPES: tuple[DocumentType, ...] = (
    "salary_certificate",
    "health_insurance_premium",
    "daycare_invoice",
    "pillar_3a_certificate",
    "transport_pass",
    "bank_year_end_statement",
    "mortgage_interest_statement",
    "alimony_paid_received",
    "donation_receipt",
    "parental_support_receipt",
    "medical_bills_unreimbursed",
    "education_invoice",
    "second_pillar_buyback_attestation",
    "foreign_income_attestation",
    "disability_proof",
    "unemployment_benefits_attestation",
)


class DocumentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    filename: str
    file_path: str
    document_type: DocumentType = "unknown"
    classifier_confidence: float | None = None
    classifier_method: Literal["heuristic", "llm_structured", "unknown"] = "unknown"
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    pdf_page_count: int | None = None

    @field_validator("classifier_confidence")
    @classmethod
    def _confidence_in_unit_interval(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if not (0.0 <= v <= 1.0):
            raise ValueError("classifier_confidence must be in [0.0, 1.0]")
        return v

    @field_validator("filename")
    @classmethod
    def _filename_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("filename must be non-empty")
        return v
