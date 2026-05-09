"""Adaptive interview engine tests. Pure deterministic; no live LLM."""
from __future__ import annotations

from typing import Any

import pytest

from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.interview import QUESTIONS, select_questions
from TaxAI2025.ui.state import AppState, UserProfile


def _profile(**overrides: Any) -> UserProfile:
    data: dict[str, Any] = {
        "first_name": "Sarah",
        "marital_status": "married",
        "spouse_works": True,
        "children_count": 1,
        "children_ages": [4],
        "commune_of_residence": "Lausanne",
        "employer_name": "ACME SA",
        "work_commune": "Renens",
        "tax_year": 2024,
        "has_workplace_canteen": False,
    }
    data.update(overrides)
    return UserProfile(**data)


def _fact(field: str, confirmed: bool = True) -> TaxFact:
    return TaxFact(
        canonical_field=field,
        value=100.0,
        source_doc="synthetic.pdf",
        source_page=1,
        confidence=1.0,
        extraction_method="regex",
        confirmed_by_user=confirmed,
    )


def test_interview_registry_has_source_citations_and_unique_ids() -> None:
    ids = [q.id for q in QUESTIONS]
    assert len(ids) == len(set(ids))
    assert len(QUESTIONS) >= 12
    for question in QUESTIONS:
        assert question.source_doc
        assert question.asks_for
        assert question.citation_token().startswith("[Vaud 2025 Instructions")


def test_select_questions_is_contextual_and_sorted() -> None:
    questions = select_questions(_profile(), [])
    ids = [q.id for q in questions]
    assert "IQ-INSURANCE-001" in ids
    assert "IQ-CHILDCARE-001" in ids
    assert "IQ-COMMUTE-001" in ids
    assert ids[0] in {"IQ-BANK-001", "IQ-INSURANCE-001"}


def test_select_questions_ignores_confirmed_facts() -> None:
    questions = select_questions(
        _profile(),
        [
            _fact("health_insurance.annual_premium_chf"),
            _fact("bank.year_end_balance_chf"),
            _fact("childcare.total_paid_chf"),
        ],
    )
    ids = {q.id for q in questions}
    assert "IQ-INSURANCE-001" not in ids
    assert "IQ-BANK-001" not in ids
    assert "IQ-CHILDCARE-001" not in ids


def test_select_questions_does_not_count_unconfirmed_facts() -> None:
    questions = select_questions(_profile(), [_fact("bank.year_end_balance_chf", False)])
    assert "IQ-BANK-001" in {q.id for q in questions}


def test_select_questions_skips_answered_ids() -> None:
    questions = select_questions(_profile(), [], answered_ids={"IQ-INSURANCE-001"})
    assert "IQ-INSURANCE-001" not in {q.id for q in questions}


def test_app_state_records_interview_answers() -> None:
    state = AppState()
    answer = state.record_interview_answer("IQ-INSURANCE-001", "yes")
    assert answer.question_id == "IQ-INSURANCE-001"
    assert state.answered_question_ids() == {"IQ-INSURANCE-001"}
    assert state.audit_log[-1].event_type == "interview_answered"


def test_select_questions_rejects_missing_profile() -> None:
    with pytest.raises(ValueError, match="UserProfile"):
        select_questions(None, [])  # type: ignore[arg-type]
