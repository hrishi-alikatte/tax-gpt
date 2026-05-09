"""Golden tests — one positive + one negative per rule.

Each rule must trigger on a profile that needs it, and stay silent on a
profile that does not. Rules without a citation slot (`source_doc`) cannot
ship — see `test_completeness_schema.py`.
"""
from __future__ import annotations

from typing import Any

import pytest

from TaxAI2025.completeness.rules import RULES
from TaxAI2025.completeness.schema import CompletenessRule
from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.ui.state import UserProfile


def _rule(rule_id: str) -> CompletenessRule:
    for r in RULES:
        if r.id == rule_id:
            return r
    raise AssertionError(f"Rule {rule_id!r} not found in RULES")


def _confirmed_fact(canonical_field: str, value: Any = 100.0) -> TaxFact:
    return TaxFact(
        canonical_field=canonical_field,
        value=value,
        source_doc="synthetic.pdf",
        source_page=1,
        confidence=1.0,
        extraction_method="regex",
        confirmed_by_user=True,
    )


def _base_profile(**overrides: Any) -> UserProfile:
    defaults: dict[str, Any] = {
        "first_name": "Sarah",
        "marital_status": "married",
        "spouse_works": True,
        "children_count": 0,
        "children_ages": [],
        "commune_of_residence": "Lausanne",
        "employer_name": "ACME SA",
        "work_commune": "Lausanne",
        "tax_year": 2025,
        "has_workplace_canteen": True,
    }
    defaults.update(overrides)
    return UserProfile(**defaults)


# ----- registry-wide invariants -------------------------------------------


def test_every_rule_has_a_citation() -> None:
    for rule in RULES:
        assert rule.source_doc, f"{rule.id} has no source_doc"


def test_every_rule_has_a_known_severity() -> None:
    valid = {"blocker", "likely_missing", "nice_to_have"}
    for rule in RULES:
        assert rule.severity in valid, f"{rule.id} severity {rule.severity!r}"


def test_every_rule_has_at_least_one_asks_for() -> None:
    for rule in RULES:
        assert len(rule.asks_for) >= 1, f"{rule.id} has empty asks_for"


def test_every_rule_message_is_informational_not_prescriptive() -> None:
    for rule in RULES:
        msg = rule.missing_message_en.lower()
        assert "you must" not in msg, (
            f"{rule.id} message is prescriptive: {rule.missing_message_en!r}"
        )


def test_rule_ids_are_unique() -> None:
    ids = [r.id for r in RULES]
    assert len(ids) == len(set(ids)), f"duplicate rule ids in RULES: {ids}"


# ----- VD-CHILDCARE-001 ---------------------------------------------------


def test_childcare_rule_triggers_when_kids_and_no_fact() -> None:
    rule = _rule("VD-CHILDCARE-001")
    profile = _base_profile(children_count=1, children_ages=[3])
    assert rule.trigger(profile, []) is True


def test_childcare_rule_silent_when_no_kids() -> None:
    rule = _rule("VD-CHILDCARE-001")
    profile = _base_profile(children_count=0, children_ages=[])
    assert rule.trigger(profile, []) is False


def test_childcare_rule_silent_when_confirmed_fact_present() -> None:
    rule = _rule("VD-CHILDCARE-001")
    profile = _base_profile(children_count=1, children_ages=[3])
    facts = [_confirmed_fact("childcare.total_paid_chf", 12_000.0)]
    assert rule.trigger(profile, facts) is False


def test_childcare_rule_ignores_unconfirmed_fact() -> None:
    rule = _rule("VD-CHILDCARE-001")
    profile = _base_profile(children_count=1, children_ages=[3])
    unconfirmed = _confirmed_fact("childcare.total_paid_chf", 12_000.0).model_copy(
        update={"confirmed_by_user": False}
    )
    assert rule.trigger(profile, [unconfirmed]) is True


# ----- VD-PILLAR3A-001 ----------------------------------------------------


def test_pillar3a_rule_triggers_when_employed_no_fact() -> None:
    rule = _rule("VD-PILLAR3A-001")
    profile = _base_profile(employer_name="ACME SA")
    assert rule.trigger(profile, []) is True


def test_pillar3a_rule_silent_when_no_employer() -> None:
    rule = _rule("VD-PILLAR3A-001")
    profile = _base_profile(employer_name=None)
    assert rule.trigger(profile, []) is False


def test_pillar3a_rule_silent_when_fact_confirmed() -> None:
    rule = _rule("VD-PILLAR3A-001")
    profile = _base_profile(employer_name="ACME SA")
    facts = [_confirmed_fact("pillar_3a.annual_contribution_chf", 7_056.0)]
    assert rule.trigger(profile, facts) is False


# ----- VD-COMMUTE-001 -----------------------------------------------------


def test_commute_rule_triggers_when_communes_differ() -> None:
    rule = _rule("VD-COMMUTE-001")
    profile = _base_profile(
        commune_of_residence="Lausanne", work_commune="Renens"
    )
    assert rule.trigger(profile, []) is True


def test_commute_rule_silent_when_same_commune() -> None:
    rule = _rule("VD-COMMUTE-001")
    profile = _base_profile(
        commune_of_residence="Lausanne", work_commune="Lausanne"
    )
    assert rule.trigger(profile, []) is False


def test_commute_rule_silent_when_fact_confirmed() -> None:
    rule = _rule("VD-COMMUTE-001")
    profile = _base_profile(
        commune_of_residence="Lausanne", work_commune="Renens"
    )
    facts = [_confirmed_fact("transport.annual_cost_chf", 850.0)]
    assert rule.trigger(profile, facts) is False


def test_commute_rule_silent_when_work_commune_missing() -> None:
    rule = _rule("VD-COMMUTE-001")
    profile = _base_profile(commune_of_residence="Lausanne", work_commune=None)
    assert rule.trigger(profile, []) is False


# ----- VD-MEAL-001 --------------------------------------------------------


def test_meal_rule_triggers_when_no_canteen_no_fact() -> None:
    rule = _rule("VD-MEAL-001")
    profile = _base_profile(employer_name="ACME SA", has_workplace_canteen=False)
    assert rule.trigger(profile, []) is True


def test_meal_rule_silent_when_canteen_true() -> None:
    rule = _rule("VD-MEAL-001")
    profile = _base_profile(employer_name="ACME SA", has_workplace_canteen=True)
    assert rule.trigger(profile, []) is False


def test_meal_rule_silent_when_fact_confirmed() -> None:
    rule = _rule("VD-MEAL-001")
    profile = _base_profile(employer_name="ACME SA", has_workplace_canteen=False)
    facts = [_confirmed_fact("meal_allowance.method", "none")]
    assert rule.trigger(profile, facts) is False


def test_meal_rule_silent_when_no_employer() -> None:
    rule = _rule("VD-MEAL-001")
    profile = _base_profile(employer_name=None, has_workplace_canteen=False)
    assert rule.trigger(profile, []) is False


# ----- VD-INSURANCE-001 ---------------------------------------------------


def test_insurance_rule_triggers_when_no_fact() -> None:
    rule = _rule("VD-INSURANCE-001")
    profile = _base_profile()
    assert rule.trigger(profile, []) is True


def test_insurance_rule_silent_when_fact_confirmed() -> None:
    rule = _rule("VD-INSURANCE-001")
    profile = _base_profile()
    facts = [_confirmed_fact("health_insurance.annual_premium_chf", 4_200.0)]
    assert rule.trigger(profile, facts) is False


# ----- VD-BANK-001 --------------------------------------------------------


def test_bank_rule_triggers_when_no_fact() -> None:
    rule = _rule("VD-BANK-001")
    profile = _base_profile()
    assert rule.trigger(profile, []) is True


def test_bank_rule_silent_when_fact_confirmed() -> None:
    rule = _rule("VD-BANK-001")
    profile = _base_profile()
    facts = [_confirmed_fact("bank.year_end_balance_chf", 18_400.0)]
    assert rule.trigger(profile, facts) is False
