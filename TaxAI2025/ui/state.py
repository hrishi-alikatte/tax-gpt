"""Application state for the M3 confirmation UI.

Holds the user profile, uploaded documents, extracted TaxFacts (with the
confirmation gate enforced by `is_extracted_complete`), placeholder
findings, and a lightweight audit log.

No business logic: this module knows nothing about extraction, RAG, or
completeness rules. It just stores values and enforces the
confirmed-by-user invariant so views cannot ship unconfirmed data
downstream.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from TaxAI2025.core.documents import DocumentRecord, DocumentType
from TaxAI2025.core.tax_facts import TaxFact


AuditEventType = Literal[
    "profile_saved",
    "document_uploaded",
    "document_type_confirmed",
    "fact_confirmed",
    "fact_unconfirmed",
    "explain_asked",
    "explain_refused",
    "navigated",
]


class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: AuditEventType
    payload: dict[str, Any] = Field(default_factory=dict)


class UserProfile(BaseModel):
    """Canonical Vaud-only profile (DOMAIN_MODEL §2)."""

    model_config = ConfigDict(extra="ignore")

    first_name: str | None = None
    permit_type: Literal["C"] = "C"
    marital_status: Literal[
        "single", "married", "divorced", "widowed", "registered_partnership"
    ] | None = None
    spouse_works: bool | None = None
    children_count: int = 0
    children_ages: list[int] = Field(default_factory=list)
    commune_of_residence: str | None = None
    employer_name: str | None = None
    work_commune: str | None = None
    tax_year: int = 2024


REQUIRED_FIELDS_BY_DOC_TYPE: dict[DocumentType, tuple[str, ...]] = {
    "salary_certificate": (
        "salary.gross_annual_chf",
        "salary.net_annual_chf",
    ),
    "health_insurance_premium": ("health_insurance.annual_premium_chf",),
    "daycare_invoice": ("childcare.total_paid_chf",),
    "pillar_3a_certificate": ("pillar_3a.annual_contribution_chf",),
    "transport_pass": ("transport.annual_cost_chf",),
    "bank_year_end_statement": ("bank.year_end_balance_chf",),
    "unknown": (),
}


class AppState:
    """Mutable runtime state. One instance per Flet session."""

    def __init__(self) -> None:
        self.profile: UserProfile | None = None
        self.documents: list[DocumentRecord] = []
        self.facts: list[TaxFact] = []
        self.findings: list[Any] = []
        self.audit_log: list[AuditEntry] = []

    # ----- audit ---------------------------------------------------------

    def record(self, event_type: AuditEventType, **payload: Any) -> AuditEntry:
        entry = AuditEntry(event_type=event_type, payload=payload)
        self.audit_log.append(entry)
        return entry

    # ----- profile -------------------------------------------------------

    def set_profile(self, profile: UserProfile) -> None:
        self.profile = profile
        self.record("profile_saved", first_name=profile.first_name)

    # ----- documents -----------------------------------------------------

    def add_document(self, record: DocumentRecord, facts: Iterable[TaxFact]) -> None:
        self.documents.append(record)
        for f in facts:
            if f.confirmed_by_user:
                raise ValueError(
                    "AppState.add_document refuses pre-confirmed facts: "
                    f"canonical_field={f.canonical_field!r}"
                )
            self.facts.append(f)
        self.record(
            "document_uploaded",
            doc_id=record.doc_id,
            filename=record.filename,
            document_type=record.document_type,
        )

    def confirm_document_type(self, doc_id: str) -> None:
        self.record("document_type_confirmed", doc_id=doc_id)

    # ----- facts ---------------------------------------------------------

    def required_fields_for_doc_type(self, doc_type: DocumentType) -> tuple[str, ...]:
        return REQUIRED_FIELDS_BY_DOC_TYPE.get(doc_type, ())

    def required_fields(self) -> set[str]:
        required: set[str] = set()
        for d in self.documents:
            for field in self.required_fields_for_doc_type(d.document_type):
                required.add(field)
        return required

    def confirm_fact(self, canonical_field: str) -> bool:
        for i, f in enumerate(self.facts):
            if f.canonical_field == canonical_field:
                self.facts[i] = f.model_copy(update={"confirmed_by_user": True})
                self.record(
                    "fact_confirmed",
                    canonical_field=canonical_field,
                    value=str(self.facts[i].value),
                )
                return True
        return False

    def unconfirm_fact(self, canonical_field: str) -> bool:
        for i, f in enumerate(self.facts):
            if f.canonical_field == canonical_field:
                self.facts[i] = f.model_copy(update={"confirmed_by_user": False})
                self.record("fact_unconfirmed", canonical_field=canonical_field)
                return True
        return False

    def is_extracted_complete(self) -> bool:
        if not self.facts:
            return False
        required = self.required_fields()
        if not required:
            return all(f.confirmed_by_user for f in self.facts)
        confirmed = {f.canonical_field for f in self.facts if f.confirmed_by_user}
        return required.issubset(confirmed)

    def confirmed_facts(self) -> list[TaxFact]:
        return [f for f in self.facts if f.confirmed_by_user]


__all__ = [
    "AppState",
    "AuditEntry",
    "AuditEventType",
    "REQUIRED_FIELDS_BY_DOC_TYPE",
    "UserProfile",
]
