"""Active completeness rule set (rules-as-data).

Every rule cites the Vaud 2025 Instructions. Page numbers that have not
been confirmed by `vaud-tax-domain-analyst` against `data/official/vd_2025.pdf`
are recorded with `pdf_page=None` and `verification_status="pending"`.

To add a rule: append a `CompletenessRule` literal to `RULES` below.
DO NOT add new code paths to `engine.py`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from TaxAI2025.completeness.schema import CompletenessRule

if TYPE_CHECKING:
    from TaxAI2025.core.tax_facts import TaxFact
    from TaxAI2025.ui.state import UserProfile


SOURCE_DOC = "Vaud 2025 Instructions"


def _has_confirmed_fact(facts: "list[TaxFact]", canonical_field: str) -> bool:
    return any(
        f.canonical_field == canonical_field and f.confirmed_by_user
        for f in facts
    )


def _trigger_childcare(profile: "UserProfile", facts: "list[TaxFact]") -> bool:
    if profile.children_count <= 0:
        return False
    return not _has_confirmed_fact(facts, "childcare.total_paid_chf")


def _trigger_pillar3a(profile: "UserProfile", facts: "list[TaxFact]") -> bool:
    if not profile.employer_name or not profile.employer_name.strip():
        return False
    return not _has_confirmed_fact(facts, "pillar_3a.annual_contribution_chf")


def _trigger_commute(profile: "UserProfile", facts: "list[TaxFact]") -> bool:
    home = profile.commune_of_residence
    work = profile.work_commune
    if not home or not work:
        return False
    if home.strip().lower() == work.strip().lower():
        return False
    return not _has_confirmed_fact(facts, "transport.annual_cost_chf")


def _trigger_meal(profile: "UserProfile", facts: "list[TaxFact]") -> bool:
    if not profile.employer_name or not profile.employer_name.strip():
        return False
    if profile.has_workplace_canteen is True:
        return False
    return not _has_confirmed_fact(facts, "meal_allowance.method")


def _trigger_health_insurance(
    profile: "UserProfile", facts: "list[TaxFact]"
) -> bool:
    return not _has_confirmed_fact(facts, "health_insurance.annual_premium_chf")


def _trigger_bank_balance(
    profile: "UserProfile", facts: "list[TaxFact]"
) -> bool:
    return not _has_confirmed_fact(facts, "bank.year_end_balance_chf")


RULES: list[CompletenessRule] = [
    CompletenessRule(
        id="VD-CHILDCARE-001",
        title_en="Childcare deduction may apply",
        trigger=_trigger_childcare,
        missing_message_en=(
            "You declared at least one child but no childcare expense was "
            "confirmed. You may have a deduction to claim — please share any "
            "daycare or after-school invoices."
        ),
        asks_for=("childcare.total_paid_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="vaud_official",
        severity="likely_missing",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-PILLAR3A-001",
        title_en="Pillar 3a contribution may apply",
        trigger=_trigger_pillar3a,
        missing_message_en=(
            "You are employed but no pillar 3a contribution was confirmed. "
            "If you contributed to a 3rd pillar A this year, the annual "
            "statement may unlock a deduction."
        ),
        asks_for=("pillar_3a.annual_contribution_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="vaud_official",
        severity="likely_missing",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-COMMUTE-001",
        title_en="Commute / transport deduction may apply",
        trigger=_trigger_commute,
        missing_message_en=(
            "You live and work in different communes but no transport cost "
            "was confirmed. A public-transport pass or commute proof may "
            "support a deduction."
        ),
        asks_for=("transport.annual_cost_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="vaud_official",
        severity="likely_missing",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-MEAL-001",
        title_en="Meal allowance method not declared",
        trigger=_trigger_meal,
        missing_message_en=(
            "You are employed and did not indicate a workplace canteen. "
            "A meal-allowance method may be declarable — share how meals "
            "were taken on workdays."
        ),
        asks_for=("meal_allowance.method",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="vaud_official",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-INSURANCE-001",
        title_en="Health insurance premium missing",
        trigger=_trigger_health_insurance,
        missing_message_en=(
            "No annual health-insurance premium was confirmed. This is a "
            "required input for a complete Vaud filing — please share your "
            "year-end statement."
        ),
        asks_for=("health_insurance.annual_premium_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="vaud_official",
        severity="blocker",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-BANK-001",
        title_en="Bank year-end balance missing",
        trigger=_trigger_bank_balance,
        missing_message_en=(
            "No bank balance at 31 December was confirmed. The Vaud "
            "wealth declaration needs this — please share a year-end "
            "statement."
        ),
        asks_for=("bank.year_end_balance_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="vaud_official",
        severity="blocker",
        verification_status="pending",
    ),
]


__all__ = ["RULES", "SOURCE_DOC"]
