"""Source-cited adaptive interview question registry."""
from __future__ import annotations

from typing import TYPE_CHECKING

from TaxAI2025.interview.schema import OpenQuestion

if TYPE_CHECKING:
    from TaxAI2025.core.tax_facts import TaxFact
    from TaxAI2025.ui.state import UserProfile


SOURCE_DOC = "Vaud 2025 Instructions"


def _has_fact(facts: "list[TaxFact]", field: str) -> bool:
    return any(f.canonical_field == field and f.confirmed_by_user for f in facts)


def _employed(profile: "UserProfile") -> bool:
    return bool(profile.employer_name and profile.employer_name.strip())


def _has_children(profile: "UserProfile") -> bool:
    return profile.children_count > 0


def _commutes(profile: "UserProfile") -> bool:
    home = profile.commune_of_residence
    work = profile.work_commune
    return bool(home and work and home.strip().lower() != work.strip().lower())


QUESTIONS: list[OpenQuestion] = [
    OpenQuestion(
        id="IQ-INSURANCE-001",
        question_en="Did you pay Swiss health-insurance premiums during the tax year?",
        why_en="Vaud asks for insurance information under Code 300.",
        asks_for=("health_insurance.annual_premium_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=29,
        source_level="vaud_official",
        severity="blocker",
        ask_when=lambda p, f: not _has_fact(f, "health_insurance.annual_premium_chf"),
    ),
    OpenQuestion(
        id="IQ-BANK-001",
        question_en="Do you have bank or investment balances at 31 December?",
        why_en="Vaud wealth/securities reporting uses Code 410.",
        asks_for=("bank.year_end_balance_chf", "bank.annual_interest_chf"),
        source_doc=SOURCE_DOC,
        pdf_page=32,
        source_level="vaud_official",
        severity="blocker",
        ask_when=lambda p, f: not _has_fact(f, "bank.year_end_balance_chf"),
    ),
    OpenQuestion(
        id="IQ-CHILDCARE-001",
        question_en="Did you pay daycare, after-school care, or other childcare costs?",
        why_en="Parents may have childcare expenses to document.",
        asks_for=("childcare.total_paid_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=44,
        source_level="vaud_official",
        severity="likely_missing",
        ask_when=lambda p, f: _has_children(p) and not _has_fact(f, "childcare.total_paid_chf"),
    ),
    OpenQuestion(
        id="IQ-KIDS-MEDICAL-001",
        question_en="Did you pay unreimbursed medical, dental, or hospital bills for your children?",
        why_en="Medical costs can matter when documented and above the applicable threshold.",
        asks_for=("medical.unreimbursed_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="likely_missing",
        ask_when=lambda p, f: _has_children(p) and not _has_fact(f, "medical.unreimbursed_chf"),
    ),
    OpenQuestion(
        id="IQ-PILLAR3A-001",
        question_en="Did you contribute to a Pillar 3a account this year?",
        why_en="Vaud has a specific place for tied individual pension contributions.",
        asks_for=("pillar_3a.annual_contribution_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=31,
        source_level="vaud_official",
        severity="likely_missing",
        ask_when=lambda p, f: _employed(p) and not _has_fact(f, "pillar_3a.annual_contribution_chf"),
    ),
    OpenQuestion(
        id="IQ-COMMUTE-001",
        question_en="Did you pay public-transport or other commuting costs between home and work?",
        why_en="Vaud has commute/transport rules when home and work are not the same place.",
        asks_for=("transport.annual_cost_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=20,
        source_level="vaud_official",
        severity="likely_missing",
        ask_when=lambda p, f: _commutes(p) and not _has_fact(f, "transport.annual_cost_chf"),
    ),
    OpenQuestion(
        id="IQ-MEAL-001",
        question_en="Did your workplace provide a subsidized canteen or meal arrangement?",
        why_en="The meal method affects whether a meal-cost line should be considered.",
        asks_for=("meal_allowance.method",),
        source_doc=SOURCE_DOC,
        pdf_page=21,
        source_level="vaud_official",
        severity="nice_to_have",
        ask_when=lambda p, f: _employed(p) and p.has_workplace_canteen is not True and not _has_fact(f, "meal_allowance.method"),
    ),
    OpenQuestion(
        id="IQ-ALIMONY-001",
        question_en="Did you pay alimony or maintenance contributions?",
        why_en=(
            "Vaud Code 630 covers alimony and child maintenance contributions "
            "paid under the documented conditions."
        ),
        asks_for=("alimony.paid_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=42,
        source_level="vaud_official",
        severity="likely_missing",
        ask_when=lambda p, f: p.marital_status in {"divorced", "separated"} and not _has_fact(f, "alimony.paid_chf"),
    ),
    OpenQuestion(
        id="IQ-DONATION-001",
        question_en="Did you make charitable or political donations with receipts?",
        why_en=(
            "Vaud Code 720 covers donations to eligible public-interest "
            "institutions when the annual minimum and cap rules are met."
        ),
        asks_for=("donations.total_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=49,
        source_level="vaud_official",
        severity="nice_to_have",
        ask_when=lambda p, f: not _has_fact(f, "donations.total_chf"),
    ),
    OpenQuestion(
        id="IQ-PARENTAL-SUPPORT-001",
        question_en="Did you financially support parents or another dependent person?",
        why_en="Dependent-person support is tracked as a Phase B question.",
        asks_for=("parental_support.paid_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        ask_when=lambda p, f: not _has_fact(f, "parental_support.paid_chf"),
    ),
    OpenQuestion(
        id="IQ-MEDICAL-001",
        question_en="Did you pay unreimbursed medical or dental costs for yourself or your household?",
        why_en="Large unreimbursed medical costs may require documentation.",
        asks_for=("medical.unreimbursed_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        ask_when=lambda p, f: not _has_fact(f, "medical.unreimbursed_chf"),
    ),
    OpenQuestion(
        id="IQ-EDUCATION-001",
        question_en="Did you pay job-related training, education, or professional-development fees?",
        why_en=(
            "Vaud Code 618 covers qualifying professional training, continuing "
            "education, and reconversion fees."
        ),
        asks_for=("education.tuition_paid_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=42,
        source_level="vaud_official",
        severity="nice_to_have",
        ask_when=lambda p, f: _employed(p) and not _has_fact(f, "education.tuition_paid_chf"),
    ),
    OpenQuestion(
        id="IQ-PILLAR2-BUYBACK-001",
        question_en="Did you make a second-pillar pension-fund buyback?",
        why_en="Second-pillar buybacks are distinct from ordinary salary LPP contributions.",
        asks_for=("pillar2.buyback_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=31,
        source_level="vaud_official",
        severity="nice_to_have",
        ask_when=lambda p, f: _employed(p) and not _has_fact(f, "pillar2.buyback_chf"),
    ),
    OpenQuestion(
        id="IQ-MORTGAGE-001",
        question_en="Did you pay mortgage interest for a property?",
        why_en="Mortgage interest statements are part of the expanded document registry.",
        asks_for=("mortgage.annual_interest_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        ask_when=lambda p, f: not _has_fact(f, "mortgage.annual_interest_chf"),
    ),
    OpenQuestion(
        id="IQ-REAL-ESTATE-MAINT-001",
        question_en="Did you pay maintenance costs for Vaud real estate?",
        why_en=(
            "Vaud Code 540 covers private real-estate maintenance costs, with "
            "details handled in the property instructions."
        ),
        asks_for=("real_estate.maintenance_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=40,
        source_level="vaud_official",
        severity="nice_to_have",
        ask_when=lambda p, f: not _has_fact(f, "real_estate.maintenance_chf"),
    ),
    OpenQuestion(
        id="IQ-FOREIGN-INCOME-001",
        question_en="Did you receive salary, pension, or other income from outside Switzerland?",
        why_en="Foreign income attestations need explicit review before filing.",
        asks_for=("foreign_income.gross_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="likely_missing",
        ask_when=lambda p, f: not _has_fact(f, "foreign_income.gross_chf"),
    ),
    OpenQuestion(
        id="IQ-FOREIGN-ASSETS-001",
        question_en="Did you hold bank accounts, investments, or crypto assets outside Switzerland?",
        why_en="Foreign assets should be reviewed before filing a complete Vaud declaration.",
        asks_for=("foreign_assets.year_end_balance_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="likely_missing",
        ask_when=lambda p, f: not _has_fact(f, "foreign_assets.year_end_balance_chf"),
    ),
    OpenQuestion(
        id="IQ-UNEMPLOYMENT-001",
        question_en="Did you receive unemployment benefits during the year?",
        why_en="Unemployment attestations are income documents in the expanded registry.",
        asks_for=("unemployment.benefits_chf",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="likely_missing",
        ask_when=lambda p, f: not _has_fact(f, "unemployment.benefits_chf"),
    ),
    OpenQuestion(
        id="IQ-DISABILITY-001",
        question_en="Did you receive disability-related proof, allowances, or pension statements?",
        why_en="Disability proof is tracked for user review in Phase B.",
        asks_for=("disability.acknowledged",),
        source_doc=SOURCE_DOC,
        pdf_page=None,
        source_level="inferred",
        severity="nice_to_have",
        ask_when=lambda p, f: not _has_fact(f, "disability.acknowledged"),
    ),
]


__all__ = ["QUESTIONS", "SOURCE_DOC"]
