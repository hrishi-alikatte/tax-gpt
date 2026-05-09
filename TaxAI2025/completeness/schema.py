"""CompletenessRule + Finding contracts.

Verbatim shape from `docs/ARCHITECTURE.md` §Key contracts, extended with a
`verification_status` discriminator so a rule whose Vaud Instructions page
has not yet been confirmed by `vaud-tax-domain-analyst` is auditable
rather than silently shipping an invented page number.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, field_validator

if TYPE_CHECKING:
    from TaxAI2025.core.tax_facts import TaxFact
    from TaxAI2025.ui.state import UserProfile


Severity = Literal["blocker", "likely_missing", "nice_to_have"]
VerificationStatus = Literal["vaud_official", "pending", "inferred"]
SourceLevel = Literal["vaud_official", "federal", "inferred"]


SEVERITY_RANK: dict[Severity, int] = {
    "blocker": 0,
    "likely_missing": 1,
    "nice_to_have": 2,
}


Trigger = Callable[["UserProfile", "list[TaxFact]"], bool]


@dataclass(frozen=True)
class CompletenessRule:
    id: str
    title_en: str
    trigger: Trigger
    missing_message_en: str
    asks_for: tuple[str, ...]
    source_doc: str
    pdf_page: int | None
    source_level: SourceLevel
    severity: Severity
    verification_status: VerificationStatus

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("CompletenessRule.id must be non-empty")
        if not self.source_doc or not self.source_doc.strip():
            raise ValueError(
                f"CompletenessRule {self.id!r} requires a source_doc citation"
            )
        if self.verification_status == "vaud_official" and self.pdf_page is None:
            raise ValueError(
                f"CompletenessRule {self.id!r} marked vaud_official must "
                f"carry a concrete pdf_page (1-indexed)"
            )
        if self.pdf_page is not None and self.pdf_page < 1:
            raise ValueError(
                f"CompletenessRule {self.id!r}: pdf_page must be >= 1 "
                f"(PDF pages are 1-indexed)"
            )
        if self.severity not in SEVERITY_RANK:
            raise ValueError(
                f"CompletenessRule {self.id!r}: unknown severity {self.severity!r}"
            )


class Finding(BaseModel):
    """Engine output. Shape mirrors `docs/ARCHITECTURE.md` §Key contracts."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title_en: str
    message_en: str
    asks_for: list[str]
    source_doc: str
    pdf_page: int | None
    severity: Severity
    verification_status: VerificationStatus

    @field_validator("rule_id")
    @classmethod
    def _id_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("rule_id must be non-empty")
        return v

    @field_validator("source_doc")
    @classmethod
    def _source_doc_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source_doc must be non-empty")
        return v

    @field_validator("pdf_page")
    @classmethod
    def _page_one_indexed_or_none(cls, v: int | None) -> int | None:
        if v is None:
            return None
        if v < 1:
            raise ValueError("pdf_page must be >= 1 when present (PDF is 1-indexed)")
        return v

    def citation_token(self) -> str:
        """Render the citation in the same shape used by the explain layer."""
        if self.pdf_page is None:
            return "[Vaud 2025 Instructions, page pending verification]"
        return f"[Vaud 2025 Instructions p.{self.pdf_page}]"


__all__ = [
    "CompletenessRule",
    "Finding",
    "SEVERITY_RANK",
    "Severity",
    "SourceLevel",
    "Trigger",
    "VerificationStatus",
]
