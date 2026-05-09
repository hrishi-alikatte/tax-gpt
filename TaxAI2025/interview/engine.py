"""Pure deterministic adaptive interview selector."""
from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from TaxAI2025.interview.registry import QUESTIONS
from TaxAI2025.interview.schema import OpenQuestion

if TYPE_CHECKING:
    from TaxAI2025.core.tax_facts import TaxFact
    from TaxAI2025.ui.state import UserProfile


_SEVERITY_RANK = {"blocker": 0, "likely_missing": 1, "nice_to_have": 2}


def _confirmed_only(facts: "Iterable[TaxFact]") -> "list[TaxFact]":
    return [f for f in facts if f.confirmed_by_user]


def select_questions(
    profile: "UserProfile",
    facts: "Iterable[TaxFact]",
    *,
    questions: "Iterable[OpenQuestion] | None" = None,
    answered_ids: "set[str] | None" = None,
    limit: int = 10,
) -> list[OpenQuestion]:
    if profile is None:
        raise ValueError("select_questions requires a UserProfile")
    answered = answered_ids or set()
    confirmed = _confirmed_only(facts)
    registry = list(questions) if questions is not None else QUESTIONS
    selected = [
        q
        for q in registry
        if q.id not in answered and q.ask_when(profile, confirmed)
    ]
    selected.sort(key=lambda q: (_SEVERITY_RANK[q.severity], q.id))
    return selected[:limit]


__all__ = ["select_questions"]
