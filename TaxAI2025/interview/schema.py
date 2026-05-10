"""Contracts for deterministic adaptive interview questions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from TaxAI2025.core.tax_facts import TaxFact
    from TaxAI2025.ui.state import UserProfile


QuestionSeverity = Literal["blocker", "likely_missing", "nice_to_have"]
QuestionTrigger = Callable[["UserProfile", "list[TaxFact]"], bool]
SourceLevel = Literal["vaud_official", "federal", "inferred"]


@dataclass(frozen=True)
class OpenQuestion:
    id: str
    question_en: str
    why_en: str
    asks_for: tuple[str, ...]
    source_doc: str
    pdf_page: int | None
    source_level: SourceLevel
    severity: QuestionSeverity
    ask_when: QuestionTrigger

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("OpenQuestion.id must be non-empty")
        if not self.question_en or not self.question_en.strip():
            raise ValueError(f"OpenQuestion {self.id!r} requires question text")
        if not self.asks_for:
            raise ValueError(f"OpenQuestion {self.id!r} requires asks_for")
        if self.pdf_page is not None and self.pdf_page < 1:
            raise ValueError(f"OpenQuestion {self.id!r}: pdf_page must be >= 1")

    def citation_token(self) -> str:
        if self.pdf_page is None:
            return "[Vaud 2025 Instructions, page pending verification]"
        return f"[Vaud 2025 Instructions p.{self.pdf_page}]"


class OpenQuestionOut(BaseModel):
    """Serializable wire-format of OpenQuestion for the HTTP API.

    Drops the non-serializable `ask_when` Callable. Engine code keeps using
    OpenQuestion (dataclass with trigger). The route layer converts via
    `OpenQuestionOut.from_question`.
    """

    id: str
    question_en: str
    why_en: str
    asks_for: list[str]
    source_doc: str
    pdf_page: int | None
    source_level: SourceLevel
    severity: QuestionSeverity

    @classmethod
    def from_question(cls, q: "OpenQuestion") -> "OpenQuestionOut":
        return cls(
            id=q.id,
            question_en=q.question_en,
            why_en=q.why_en,
            asks_for=list(q.asks_for),
            source_doc=q.source_doc,
            pdf_page=q.pdf_page,
            source_level=q.source_level,
            severity=q.severity,
        )


__all__ = [
    "OpenQuestion",
    "OpenQuestionOut",
    "QuestionSeverity",
    "QuestionTrigger",
    "SourceLevel",
]
