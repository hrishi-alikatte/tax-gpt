"""Engine behavior + the canonical demo-gate test.

The demo punchline: with Sarah's profile + the 5 confirmed facts, the
engine produces exactly three findings — VD-CHILDCARE-001,
VD-PILLAR3A-001, VD-COMMUTE-001. Anything else fails this test and
breaks the demo.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from TaxAI2025.completeness import RULES, evaluate
from TaxAI2025.completeness.schema import (
    SEVERITY_RANK,
    CompletenessRule,
    Finding,
)
from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.ui.state import UserProfile


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO_ROOT / "demo" / "scenarios" / "expat_c_permit_basic"


def _trigger_true(_profile, _facts) -> bool:
    return True


def _trigger_false(_profile, _facts) -> bool:
    return False


def _confirmed(canonical_field: str, value: Any = 100.0) -> TaxFact:
    return TaxFact(
        canonical_field=canonical_field,
        value=value,
        source_doc="synthetic.pdf",
        source_page=1,
        confidence=1.0,
        extraction_method="regex",
        confirmed_by_user=True,
    )


def _unconfirmed(canonical_field: str, value: Any = 100.0) -> TaxFact:
    return _confirmed(canonical_field, value).model_copy(
        update={"confirmed_by_user": False}
    )


def _profile(**overrides: Any) -> UserProfile:
    base: dict[str, Any] = {
        "first_name": "X",
        "marital_status": "single",
        "spouse_works": None,
        "children_count": 0,
        "children_ages": [],
        "commune_of_residence": "Lausanne",
        "employer_name": None,
        "work_commune": None,
        "tax_year": 2024,
        "has_workplace_canteen": True,
    }
    base.update(overrides)
    return UserProfile(**base)


# ----- engine invariants --------------------------------------------------


def test_evaluate_returns_findings_list() -> None:
    findings = evaluate(_profile(), [])
    assert isinstance(findings, list)
    assert all(isinstance(f, Finding) for f in findings)


def test_evaluate_filters_unconfirmed_facts_before_rules_run() -> None:
    """Even though VD-INSURANCE-001 has matching unconfirmed facts, it must
    still trigger because the engine refuses to count unconfirmed facts."""
    profile = _profile()
    unconfirmed_facts = [
        _unconfirmed("health_insurance.annual_premium_chf", 4_200.0),
        _unconfirmed("bank.year_end_balance_chf", 18_400.0),
    ]
    findings = evaluate(profile, unconfirmed_facts)
    rule_ids = {f.rule_id for f in findings}
    assert "VD-INSURANCE-001" in rule_ids
    assert "VD-BANK-001" in rule_ids


def test_evaluate_sorts_by_severity_then_rule_id() -> None:
    rule_a = CompletenessRule(
        id="VD-A-002",
        title_en="A",
        trigger=_trigger_true,
        missing_message_en="m",
        asks_for=("x.a",),
        source_doc="Vaud 2025 Instructions",
        pdf_page=None,
        source_level="vaud_official",
        severity="nice_to_have",
        verification_status="pending",
    )
    rule_b = CompletenessRule(
        id="VD-B-001",
        title_en="B",
        trigger=_trigger_true,
        missing_message_en="m",
        asks_for=("x.b",),
        source_doc="Vaud 2025 Instructions",
        pdf_page=None,
        source_level="vaud_official",
        severity="blocker",
        verification_status="pending",
    )
    rule_c = CompletenessRule(
        id="VD-C-001",
        title_en="C",
        trigger=_trigger_true,
        missing_message_en="m",
        asks_for=("x.c",),
        source_doc="Vaud 2025 Instructions",
        pdf_page=None,
        source_level="vaud_official",
        severity="likely_missing",
        verification_status="pending",
    )
    rule_d = CompletenessRule(
        id="VD-A-001",
        title_en="D",
        trigger=_trigger_true,
        missing_message_en="m",
        asks_for=("x.d",),
        source_doc="Vaud 2025 Instructions",
        pdf_page=None,
        source_level="vaud_official",
        severity="blocker",
        verification_status="pending",
    )
    findings = evaluate(_profile(), [], rules=[rule_a, rule_b, rule_c, rule_d])
    ranks = [SEVERITY_RANK[f.severity] for f in findings]
    assert ranks == sorted(ranks)
    assert [f.rule_id for f in findings] == [
        "VD-A-001",
        "VD-B-001",
        "VD-C-001",
        "VD-A-002",
    ]


def test_evaluate_skips_rules_whose_trigger_returns_false() -> None:
    rule_off = CompletenessRule(
        id="VD-OFF-001",
        title_en="Off",
        trigger=_trigger_false,
        missing_message_en="m",
        asks_for=("x.x",),
        source_doc="Vaud 2025 Instructions",
        pdf_page=None,
        source_level="vaud_official",
        severity="blocker",
        verification_status="pending",
    )
    rule_on = CompletenessRule(
        id="VD-ON-001",
        title_en="On",
        trigger=_trigger_true,
        missing_message_en="m",
        asks_for=("x.x",),
        source_doc="Vaud 2025 Instructions",
        pdf_page=None,
        source_level="vaud_official",
        severity="blocker",
        verification_status="pending",
    )
    findings = evaluate(_profile(), [], rules=[rule_off, rule_on])
    assert [f.rule_id for f in findings] == ["VD-ON-001"]


def test_evaluate_rejects_none_profile() -> None:
    with pytest.raises(ValueError, match="UserProfile"):
        evaluate(None, [])  # type: ignore[arg-type]


def test_finding_carries_rule_provenance() -> None:
    profile = _profile(employer_name="ACME SA")
    findings = evaluate(profile, [])
    pillar = next(f for f in findings if f.rule_id == "VD-PILLAR3A-001")
    assert pillar.source_doc == "Vaud 2025 Instructions"
    assert pillar.severity == "likely_missing"
    assert pillar.asks_for == ["pillar_3a.annual_contribution_chf"]


# ----- the demo-gate test (canonical) -------------------------------------


def _load_sarah_profile() -> UserProfile:
    raw = json.loads((SCENARIO_DIR / "profile.json").read_text(encoding="utf-8"))
    cleaned = {
        k: v
        for k, v in raw.items()
        if not k.startswith("_") and k not in ("scenario_id", "synthetic")
    }
    return UserProfile(**cleaned)


def _load_sarah_facts() -> list[TaxFact]:
    raw = json.loads((SCENARIO_DIR / "extracted.json").read_text(encoding="utf-8"))
    out: list[TaxFact] = []
    for f in raw["facts"]:
        fact = TaxFact(**f)
        out.append(fact.model_copy(update={"confirmed_by_user": True}))
    return out


def test_demo_gate_sarah_produces_exactly_three_findings() -> None:
    profile = _load_sarah_profile()
    facts = _load_sarah_facts()

    assert all(f.confirmed_by_user for f in facts)
    assert profile.has_workplace_canteen is True

    findings = evaluate(profile, facts)
    rule_ids = [f.rule_id for f in findings]

    assert len(findings) == 3, (
        f"demo gate broken: expected 3 findings, got {len(findings)} -> "
        f"{rule_ids}"
    )
    assert set(rule_ids) == {
        "VD-CHILDCARE-001",
        "VD-PILLAR3A-001",
        "VD-COMMUTE-001",
    }


def test_demo_gate_findings_all_cite_vaud_2025_instructions() -> None:
    profile = _load_sarah_profile()
    facts = _load_sarah_facts()
    findings = evaluate(profile, facts)
    for f in findings:
        assert f.source_doc == "Vaud 2025 Instructions"


def test_demo_gate_findings_sorted_by_severity_then_id() -> None:
    profile = _load_sarah_profile()
    facts = _load_sarah_facts()
    findings = evaluate(profile, facts)
    keys = [(SEVERITY_RANK[f.severity], f.rule_id) for f in findings]
    assert keys == sorted(keys)


def test_active_rule_set_has_six_rules() -> None:
    assert len(RULES) == 6
    assert {r.id for r in RULES} == {
        "VD-CHILDCARE-001",
        "VD-PILLAR3A-001",
        "VD-COMMUTE-001",
        "VD-MEAL-001",
        "VD-INSURANCE-001",
        "VD-BANK-001",
    }
