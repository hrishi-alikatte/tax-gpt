"""Active completeness rule set (rules-as-data).

Every rule cites a verified Vaud 2025 Instructions page (1-indexed),
confirmed by `vaud-tax-domain-analyst` against `data/official/vd_2025.pdf`.
Open questions about VaudTax declaration code numbers (childcare, pillar
3a, transport) live in `docs/DOMAIN_MODEL.md` §7.

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


def _trigger_if_employed_missing(field: str):
    def _trigger(profile: "UserProfile", facts: "list[TaxFact]") -> bool:
        if not profile.employer_name or not profile.employer_name.strip():
            return False
        return not _has_confirmed_fact(facts, field)

    return _trigger


def _trigger_if_children_missing(field: str):
    def _trigger(profile: "UserProfile", facts: "list[TaxFact]") -> bool:
        if profile.children_count <= 0:
            return False
        return not _has_confirmed_fact(facts, field)

    return _trigger


def _trigger_if_divorced_missing(field: str):
    def _trigger(profile: "UserProfile", facts: "list[TaxFact]") -> bool:
        if profile.marital_status != "divorced":
            return False
        return not _has_confirmed_fact(facts, field)

    return _trigger


def _trigger_missing_for_all(field: str):
    def _trigger(profile: "UserProfile", facts: "list[TaxFact]") -> bool:
        return not _has_confirmed_fact(facts, field)

    return _trigger


RULES: list[CompletenessRule] = [
    # Vaud Instr. 2025 p.44: rule home — "Maximum déterminant... déduction
    # peut être demandée lorsque les frais de garde sont supportés". p.45
    # extends with third-party-care + documented-expense conditions.
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
        pdf_page=44,
        source_level="vaud_official",
        severity="likely_missing",
        verification_status="vaud_official",
    ),
    # Vaud Instr. 2025 p.31: pillar 3a eligibility for employed +
    # 2nd-pillar-affiliated. NOTE: code 235 (p.62) is double-activity-spouse,
    # NOT pillar 3a — do not conflate. CHF 9'900 figure on p.30 belongs to
    # CODE 300 insurance section, not pillar 3a (open question §7).
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
        pdf_page=31,
        source_level="vaud_official",
        severity="likely_missing",
        verification_status="vaud_official",
    ),
    # Vaud Instr. 2025 p.20: kilometric deduction scale — "Distance en KM
    # entre le domicile [et] le lieu de travail". p.18-19 hold the
    # applicability prefatory rules and the no-cumul-with-actual-costs rule.
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
        pdf_page=20,
        source_level="vaud_official",
        severity="likely_missing",
        verification_status="vaud_official",
    ),
    # Vaud Instr. 2025 p.21: "REPAS POUR TRAVAIL PAR ÉQUIPE OU DE NUIT
    # CODE 150" + the canteen-no-deduction rule that mirrors the
    # has_workplace_canteen short-circuit. p.22 has CODE 150 second variant
    # (REPAS POUR RÉSIDENCE HORS DU DOMICILE).
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
        pdf_page=21,
        source_level="vaud_official",
        severity="nice_to_have",
        verification_status="vaud_official",
    ),
    # Vaud Instr. 2025 p.29: "ASSURANCES-MALADIE ET ACCIDENTS, ASSURANCES
    # SUR LA VIE CODE 300" — rule home. p.30 continues with the family-
    # status cap (CHF 9'900 married/partnership).
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
        pdf_page=29,
        source_level="vaud_official",
        severity="blocker",
        verification_status="vaud_official",
    ),
    # Vaud Instr. 2025 p.32: "ÉTAT DES TITRES CODE 410 / REVENU ET FORTUNE
    # DE TITRES ET AUTRES PLACEMENTS DE CAPITAUX CODE 410". Bank/securities
    # wealth declaration is filed under code 410, NOT code 800 (which is
    # taxable income, see p.51). p.33 continues; p.38 covers insurance
    # cash values at 31-Dec.
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
        pdf_page=32,
        source_level="vaud_official",
        severity="blocker",
        verification_status="vaud_official",
    ),
    CompletenessRule(
        id="VD-MEDICAL-001",
        title_en="Unreimbursed medical costs not checked",
        trigger=_trigger_missing_for_all("medical.unreimbursed_chf"),
        missing_message_en=(
            "No unreimbursed medical or dental costs were confirmed. If you "
            "paid significant out-of-pocket health costs, keep the bills for review."
        ),
        asks_for=("medical.unreimbursed_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-CHILD-MEDICAL-001",
        title_en="Children's medical costs not checked",
        trigger=_trigger_if_children_missing("medical.unreimbursed_chf"),
        missing_message_en=(
            "You declared children but no unreimbursed household medical costs "
            "were confirmed. Child medical or dental bills may be worth reviewing."
        ),
        asks_for=("medical.unreimbursed_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-DONATION-001",
        title_en="Donation receipts not checked",
        trigger=_trigger_missing_for_all("donations.total_chf"),
        missing_message_en=(
            "No donation receipts were confirmed. If you donated to eligible "
            "organizations or parties, gather the annual receipts for review."
        ),
        asks_for=("donations.total_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=49,
        source_level="vaud_official",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-PARENTAL-SUPPORT-001",
        title_en="Dependent support not checked",
        trigger=_trigger_missing_for_all("parental_support.paid_chf"),
        missing_message_en=(
            "No support paid to parents or dependents was confirmed. If this "
            "applies, collect proof before mapping values into VaudTax."
        ),
        asks_for=("parental_support.paid_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-EDUCATION-001",
        title_en="Training or education fees not checked",
        trigger=_trigger_if_employed_missing("education.tuition_paid_chf"),
        missing_message_en=(
            "You are employed but no training or professional-development fees "
            "were confirmed. If you paid work-related education costs, keep invoices."
        ),
        asks_for=("education.tuition_paid_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=42,
        source_level="vaud_official",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-PILLAR2-BUYBACK-001",
        title_en="Second-pillar buyback not checked",
        trigger=_trigger_if_employed_missing("pillar2.buyback_chf"),
        missing_message_en=(
            "No second-pillar buyback attestation was confirmed. If you made a "
            "pension-fund buyback, collect the annual attestation."
        ),
        asks_for=("pillar2.buyback_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=31,
        source_level="vaud_official",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-ALIMONY-001",
        title_en="Alimony paid not checked",
        trigger=_trigger_if_divorced_missing("alimony.paid_chf"),
        missing_message_en=(
            "Your marital status is divorced but no alimony paid was confirmed. "
            "If you paid maintenance contributions, collect the attestation."
        ),
        asks_for=("alimony.paid_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=42,
        source_level="vaud_official",
        severity="likely_missing",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-MORTGAGE-001",
        title_en="Mortgage interest not checked",
        trigger=_trigger_missing_for_all("mortgage.annual_interest_chf"),
        missing_message_en=(
            "No mortgage interest statement was confirmed. If you own property "
            "with a mortgage, gather the annual interest statement."
        ),
        asks_for=("mortgage.annual_interest_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-FOREIGN-INCOME-001",
        title_en="Foreign income not checked",
        trigger=_trigger_missing_for_all("foreign_income.gross_chf"),
        missing_message_en=(
            "No foreign income attestation was confirmed. If you received "
            "income outside Switzerland, keep the source documents for review."
        ),
        asks_for=("foreign_income.gross_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="likely_missing",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-UNEMPLOYMENT-001",
        title_en="Unemployment benefits not checked",
        trigger=_trigger_missing_for_all("unemployment.benefits_chf"),
        missing_message_en=(
            "No unemployment-benefits attestation was confirmed. If you received "
            "benefits, add the annual statement."
        ),
        asks_for=("unemployment.benefits_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="likely_missing",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-DISABILITY-001",
        title_en="Disability proof not checked",
        trigger=_trigger_missing_for_all("disability.acknowledged"),
        missing_message_en=(
            "No disability-related proof was confirmed. If you received a "
            "disability statement or allowance document, keep it for review."
        ),
        asks_for=("disability.acknowledged",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-LIFE-INSURANCE-001",
        title_en="Life-insurance documents not checked",
        trigger=_trigger_missing_for_all("life_insurance.cash_value_chf"),
        missing_message_en=(
            "No life-insurance cash-value document was confirmed. If you hold "
            "life-insurance policies, gather the annual statement."
        ),
        asks_for=("life_insurance.cash_value_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=29,
        source_level="vaud_official",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-REAL-ESTATE-MAINT-001",
        title_en="Real-estate maintenance not checked",
        trigger=_trigger_missing_for_all("real_estate.maintenance_chf"),
        missing_message_en=(
            "No real-estate maintenance costs were confirmed. If you own Vaud "
            "property, maintenance documents may need review."
        ),
        asks_for=("real_estate.maintenance_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=40,
        source_level="vaud_official",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-FOREIGN-ASSETS-001",
        title_en="Foreign assets not checked",
        trigger=_trigger_missing_for_all("foreign_assets.year_end_balance_chf"),
        missing_message_en=(
            "No foreign asset balance was confirmed. If you hold accounts or "
            "investments abroad, gather year-end statements."
        ),
        asks_for=("foreign_assets.year_end_balance_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="likely_missing",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-SECONDARY-ACTIVITY-001",
        title_en="Secondary activity income not checked",
        trigger=_trigger_if_employed_missing("secondary_activity.gross_chf"),
        missing_message_en=(
            "No secondary-activity income was confirmed. If you had another "
            "paid activity, collect the annual documents."
        ),
        asks_for=("secondary_activity.gross_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-OTHER-REVENUE-001",
        title_en="Other revenue not checked",
        trigger=_trigger_missing_for_all("other_revenue.gross_chf"),
        missing_message_en=(
            "No other revenue was confirmed. If you received taxable income "
            "outside salary, bank interest, or unemployment benefits, collect proof."
        ),
        asks_for=("other_revenue.gross_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        verification_status="pending",
    ),
    CompletenessRule(
        id="VD-RENTAL-VALUE-001",
        title_en="Rental value / rent not checked",
        trigger=_trigger_missing_for_all("housing.rent_or_rental_value_chf"),
        missing_message_en=(
            "No rent or rental-value information was confirmed. If your housing "
            "situation affects the declaration, keep the supporting documents."
        ),
        asks_for=("housing.rent_or_rental_value_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        verification_status="pending",
    ),
]


__all__ = ["RULES", "SOURCE_DOC"]
