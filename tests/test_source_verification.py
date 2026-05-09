"""Source-verification guardrails for Phase B domain checks."""
from __future__ import annotations

from pathlib import Path

import pytest

from TaxAI2025.completeness import evaluate
from TaxAI2025.completeness.rules import RULES
from TaxAI2025.interview import QUESTIONS
from TaxAI2025.ui.state import UserProfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_MODEL = REPO_ROOT / "docs" / "DOMAIN_MODEL.md"


def _profile() -> UserProfile:
    return UserProfile(
        first_name="Rita",
        marital_status="divorced",
        spouse_works=None,
        children_count=0,
        children_ages=[],
        commune_of_residence="Lausanne",
        employer_name="ACME SA",
        work_commune="Renens",
        tax_year=2025,
        has_workplace_canteen=False,
    )


def _question(question_id: str):
    return next(q for q in QUESTIONS if q.id == question_id)


def _rule(rule_id: str):
    return next(r for r in RULES if r.id == rule_id)


def test_first_batch_interview_questions_have_verified_vaud_pages() -> None:
    expected_pages = {
        "IQ-PILLAR2-BUYBACK-001": 31,
        "IQ-EDUCATION-001": 42,
        "IQ-DONATION-001": 49,
        "IQ-ALIMONY-001": 42,
        "IQ-REAL-ESTATE-MAINT-001": 40,
    }
    for question_id, page in expected_pages.items():
        question = _question(question_id)
        assert question.source_level == "vaud_official"
        assert question.pdf_page == page


def test_first_batch_rule_metadata_has_verified_pages_but_stays_pending() -> None:
    expected_pages = {
        "VD-PILLAR2-BUYBACK-001": 31,
        "VD-EDUCATION-001": 42,
        "VD-DONATION-001": 49,
        "VD-ALIMONY-001": 42,
        "VD-REAL-ESTATE-MAINT-001": 40,
    }
    for rule_id, page in expected_pages.items():
        rule = _rule(rule_id)
        assert rule.source_level == "vaud_official"
        assert rule.pdf_page == page
        assert rule.verification_status == "pending"


def test_default_completeness_excludes_source_verified_pending_checks() -> None:
    default_ids = {f.rule_id for f in evaluate(_profile(), [])}
    all_ids = {f.rule_id for f in evaluate(_profile(), [], include_unverified=True)}

    pending_verified = {
        "VD-PILLAR2-BUYBACK-001",
        "VD-EDUCATION-001",
        "VD-DONATION-001",
        "VD-ALIMONY-001",
        "VD-REAL-ESTATE-MAINT-001",
    }
    assert pending_verified.isdisjoint(default_ids)
    assert pending_verified <= all_ids


def test_domain_model_covers_first_batch_verified_concepts() -> None:
    text = DOMAIN_MODEL.read_text(encoding="utf-8")
    for needle in (
        "`pillar2.buyback_chf`",
        "**Code 320** [verified vd_2025 p.31]",
        "`education.tuition_paid_chf`",
        "**Code 618** [verified vd_2025 p.42",
        "`donations.total_chf`",
        "**Code 720** [verified vd_2025 p.49",
        "`alimony.paid_chf`",
        "**Code 630** [verified vd_2025 p.42",
        "`real_estate.maintenance_chf`",
        "**Code 540** [verified vd_2025 p.40",
        "Dependent-support / person-in-need source split",
    ):
        assert needle in text


def test_all_vaud_official_interview_questions_have_concrete_pages() -> None:
    for question in QUESTIONS:
        if question.source_level == "vaud_official":
            assert question.pdf_page is not None, question.id


def test_all_vaud_official_findings_have_concrete_pages() -> None:
    for rule in RULES:
        if rule.verification_status == "vaud_official":
            assert rule.pdf_page is not None, rule.id
            assert rule.source_level == "vaud_official", rule.id


@pytest.mark.parametrize(
    ("question_id", "rule_id", "field", "page"),
    [
        (
            "IQ-PILLAR2-BUYBACK-001",
            "VD-PILLAR2-BUYBACK-001",
            "pillar2.buyback_chf",
            31,
        ),
        ("IQ-EDUCATION-001", "VD-EDUCATION-001", "education.tuition_paid_chf", 42),
        ("IQ-DONATION-001", "VD-DONATION-001", "donations.total_chf", 49),
        ("IQ-ALIMONY-001", "VD-ALIMONY-001", "alimony.paid_chf", 42),
        (
            "IQ-REAL-ESTATE-MAINT-001",
            "VD-REAL-ESTATE-MAINT-001",
            "real_estate.maintenance_chf",
            40,
        ),
    ],
)
def test_first_batch_question_and_rule_reference_same_field_and_page(
    question_id: str,
    rule_id: str,
    field: str,
    page: int,
) -> None:
    question = _question(question_id)
    rule = _rule(rule_id)

    assert question.asks_for == (field,)
    assert rule.asks_for == (field,)
    assert question.pdf_page == page
    assert rule.pdf_page == page
