"""Per-doc-type field extraction.

Stage 1: deterministic regex/template parsers for high-confidence fields.
Stage 2: LLM residual via `model_router.generate_json` with strict schemas.

Every TaxFact returned carries source_doc, source_page, extraction_method,
extracted_at, and `confirmed_by_user=False`. The extraction layer is
forbidden from setting `confirmed_by_user=True` — that bit belongs to the
UI confirmation gate.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable

from TaxAI2025.core.documents import DocumentRecord, DocumentType
from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.extraction.confidence import (
    LLM_DEFAULT_CONFIDENCE,
    score_llm_extraction,
    score_regex_match,
)
from TaxAI2025.extraction.ocr import PageText


_NUMBER = r"(?P<num>[0-9]{1,3}(?:[' ,.][0-9]{3})*(?:[.,][0-9]{2})?)"


def _parse_chf(num_text: str) -> float | None:
    """Parse Swiss-formatted numbers: 1'234.50 / 1 234,50 / 1234.5 / 1,234.50."""
    s = num_text.strip().replace("'", "").replace(" ", "")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


_REGEX_TEMPLATES: dict[DocumentType, list[tuple[str, re.Pattern[str]]]] = {
    "salary_certificate": [
        (
            "salary.gross_annual_chf",
            re.compile(
                r"(?:salaire\s+brut|gross\s+(?:annual\s+)?salary|bruttolohn)[^0-9]{0,40}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
        (
            "salary.net_annual_chf",
            re.compile(
                r"(?:salaire\s+net|net\s+(?:annual\s+)?salary|nettolohn)[^0-9]{0,40}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "health_insurance_premium": [
        (
            "health_insurance.annual_premium_chf",
            re.compile(
                r"(?:prime\s+annuelle|annual\s+premium|jahrespraemie|j[aä]hrliche\s+pr[aä]mie)"
                r"[^0-9]{0,40}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "daycare_invoice": [
        (
            "childcare.total_paid_chf",
            re.compile(
                r"(?:total\s+(?:pay[eé]|paid|du)|montant\s+total)[^0-9]{0,40}" + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "pillar_3a_certificate": [
        (
            "pillar_3a.annual_contribution_chf",
            re.compile(
                r"(?:cotisation\s+(?:annuelle|3e\s+pilier)|annual\s+contribution|jahresbeitrag)"
                r"[^0-9]{0,40}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "transport_pass": [
        (
            "transport.annual_cost_chf",
            re.compile(
                r"(?:co[uû]t\s+annuel|prix\s+annuel|annual\s+cost|jahreskosten)[^0-9]{0,40}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "bank_year_end_statement": [
        (
            "bank.year_end_balance_chf",
            re.compile(
                r"(?:solde\s+au\s+31|balance\s+(?:on|as\s+of)\s+(?:31|december)|jahresendsaldo)"
                r"[^0-9]{0,40}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
        (
            "bank.annual_interest_chf",
            re.compile(
                r"(?:int[eé]r[eê]ts?|interest(?:\s+income)?|zinsen)[^0-9]{0,40}" + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "mortgage_interest_statement": [
        (
            "mortgage.annual_interest_chf",
            re.compile(
                r"(?:int[eé]r[eê]ts?\s+hypoth[eé]caires?|mortgage\s+interest|hypothekarzins)"
                r"[^0-9]{0,60}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "alimony_paid_received": [
        (
            "alimony.paid_chf",
            re.compile(
                r"(?:pension\s+alimentaire\s+(?:pay[eé]e?|vers[eé]e?)|"
                r"contribution\s+d'entretien\s+(?:pay[eé]e?|vers[eé]e?)|alimony\s+paid)"
                r"[^0-9]{0,60}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "donation_receipt": [
        (
            "donations.total_chf",
            re.compile(
                r"(?:montant\s+(?:du\s+)?don|total\s+(?:donation|paid)|donation\s+amount|versement)"
                r"[^0-9]{0,60}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "parental_support_receipt": [
        (
            "parental_support.paid_chf",
            re.compile(
                r"(?:soutien\s+(?:aux\s+)?parents|aide\s+(?:aux\s+)?parents|"
                r"parental\s+support|dependent\s+support)"
                r"[^0-9]{0,60}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "medical_bills_unreimbursed": [
        (
            "medical.unreimbursed_chf",
            re.compile(
                r"(?:frais\s+m[eé]dicaux\s+non\s+rembours[eé]s?|"
                r"montant\s+non\s+rembours[eé]|unreimbursed\s+medical|dental\s+expenses)"
                r"[^0-9]{0,60}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "education_invoice": [
        (
            "education.tuition_paid_chf",
            re.compile(
                r"(?:frais\s+de\s+formation|formation\s+continue|perfectionnement|"
                r"[eé]colage|tuition(?:\s+paid|\s+fee)?)"
                r"[^0-9]{0,60}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "second_pillar_buyback_attestation": [
        (
            "pillar2.buyback_chf",
            re.compile(
                r"(?:rachat\s+(?:d'ann[eé]es\s+d'assurance|2e?\s+pilier|lpp)|"
                r"second\s+pillar\s+buyback|pension\s+fund\s+buyback)"
                r"[^0-9]{0,60}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "foreign_income_attestation": [
        (
            "foreign_income.gross_chf",
            re.compile(
                r"(?:revenu\s+[eé]tranger\s+brut|foreign\s+(?:gross\s+)?income|"
                r"income\s+abroad)"
                r"[^0-9]{0,60}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
    "unemployment_benefits_attestation": [
        (
            "unemployment.benefits_chf",
            re.compile(
                r"(?:indemnit[eé]s?\s+de\s+ch[oô]mage|allocations?\s+ch[oô]mage|"
                r"unemployment\s+benefits|alv\s+leistungen)"
                r"[^0-9]{0,60}"
                + _NUMBER,
                re.IGNORECASE,
            ),
        ),
    ],
}

_BOOLEAN_TEMPLATES: dict[DocumentType, list[tuple[str, re.Pattern[str], bool]]] = {
    "disability_proof": [
        (
            "disability.acknowledged",
            re.compile(
                r"(?:rente\s+(?:ai|iv)|attestation\s+invalidit[eé]|"
                r"assurance-invalidit[eé]|disability\s+statement)",
                re.IGNORECASE,
            ),
            True,
        ),
    ],
}


def _stage_one_regex(
    record: DocumentRecord, pages: list[PageText]
) -> tuple[list[TaxFact], set[str]]:
    facts: list[TaxFact] = []
    matched_fields: set[str] = set()
    templates = _REGEX_TEMPLATES.get(record.document_type, [])
    bool_templates = _BOOLEAN_TEMPLATES.get(record.document_type, [])
    if not templates and not bool_templates:
        return facts, matched_fields
    now = datetime.utcnow()
    for page in pages:
        for canonical_field, pattern in templates:
            if canonical_field in matched_fields:
                continue
            m = pattern.search(page.text)
            if not m:
                continue
            value = _parse_chf(m.group("num"))
            if value is None:
                continue
            facts.append(
                TaxFact(
                    canonical_field=canonical_field,
                    value=value,
                    source_doc=record.filename,
                    source_page=page.pdf_page,
                    confidence=score_regex_match(),
                    extraction_method="regex",
                    model_name=None,
                    extracted_at=now,
                    confirmed_by_user=False,
                )
            )
            matched_fields.add(canonical_field)
        for canonical_field, pattern, value in bool_templates:
            if canonical_field in matched_fields:
                continue
            if not pattern.search(page.text):
                continue
            facts.append(
                TaxFact(
                    canonical_field=canonical_field,
                    value=value,
                    source_doc=record.filename,
                    source_page=page.pdf_page,
                    confidence=score_regex_match(),
                    extraction_method="regex",
                    model_name=None,
                    extracted_at=now,
                    confirmed_by_user=False,
                )
            )
            matched_fields.add(canonical_field)
    return facts, matched_fields


_RESIDUAL_FIELDS: dict[DocumentType, list[str]] = {
    "salary_certificate": [
        "salary.gross_annual_chf",
        "salary.net_annual_chf",
        "salary.ahv_iv_eo_chf",
        "salary.unemployment_chf",
        "salary.pension_2nd_pillar_chf",
    ],
    "health_insurance_premium": ["health_insurance.annual_premium_chf"],
    "daycare_invoice": ["childcare.total_paid_chf"],
    "pillar_3a_certificate": ["pillar_3a.annual_contribution_chf"],
    "transport_pass": ["transport.annual_cost_chf"],
    "bank_year_end_statement": [
        "bank.year_end_balance_chf",
        "bank.annual_interest_chf",
    ],
    "mortgage_interest_statement": ["mortgage.annual_interest_chf"],
    "alimony_paid_received": ["alimony.paid_chf"],
    "donation_receipt": ["donations.total_chf"],
    "parental_support_receipt": ["parental_support.paid_chf"],
    "medical_bills_unreimbursed": ["medical.unreimbursed_chf"],
    "education_invoice": ["education.tuition_paid_chf"],
    "second_pillar_buyback_attestation": ["pillar2.buyback_chf"],
    "foreign_income_attestation": ["foreign_income.gross_chf"],
    "disability_proof": ["disability.acknowledged"],
    "unemployment_benefits_attestation": ["unemployment.benefits_chf"],
    "unknown": [],
}


def _llm_residual_schema(target_fields: list[str]) -> dict[str, Any]:
    field_obj = {
        "type": "object",
        "additionalProperties": False,
        "required": ["canonical_field", "value", "source_page", "confidence"],
        "properties": {
            "canonical_field": {"type": "string", "enum": target_fields},
            "value": {"type": ["number", "string", "null"]},
            "source_page": {"type": "integer", "minimum": 1},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
    }
    return {
        "title": "ResidualExtraction",
        "type": "object",
        "additionalProperties": False,
        "required": ["facts"],
        "properties": {
            "facts": {"type": "array", "items": field_obj},
        },
    }


def _stage_two_llm(
    record: DocumentRecord,
    pages: list[PageText],
    already_matched: set[str],
) -> list[TaxFact]:
    target_fields = [
        f for f in _RESIDUAL_FIELDS.get(record.document_type, []) if f not in already_matched
    ]
    if not target_fields:
        return []

    from TaxAI2025.ai import model_router

    page_count = max((p.pdf_page for p in pages), default=1)

    schema = _llm_residual_schema(target_fields)
    system = (
        "You extract Swiss Vaud tax fields from one document. "
        "Return strict JSON matching the provided schema. "
        "Only include fields you can locate in the source text. "
        "source_page must be the 1-indexed PDF page where the value appears. "
        f"Valid pages: 1..{page_count}. "
        "Never invent values. Never invent pages. If unsure, omit the field."
    )
    text_blob = "\n\n".join(f"[page {p.pdf_page}]\n{p.text}" for p in pages)
    user = (
        f"Document type: {record.document_type}\n"
        f"Target fields: {', '.join(target_fields)}\n\n"
        f"Document text:\n{text_blob}"
    )
    try:
        payload = model_router.generate_json(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            schema=schema,
            purpose="document_extraction",
        )
    except Exception:  # noqa: BLE001
        return []

    routing = model_router.route("document_extraction")
    model_name = f"{routing['provider']}:{routing['deployment']}"

    raw_facts = payload.get("facts") if isinstance(payload, dict) else None
    if not isinstance(raw_facts, list):
        return []

    now = datetime.utcnow()
    valid_pages = {p.pdf_page for p in pages}
    out: list[TaxFact] = []
    for raw in raw_facts:
        if not isinstance(raw, dict):
            continue
        canonical_field = raw.get("canonical_field")
        if canonical_field not in target_fields:
            continue
        value = raw.get("value")
        if value is None:
            continue
        page_no = raw.get("source_page")
        if not isinstance(page_no, int) or page_no not in valid_pages:
            continue
        out.append(
            TaxFact(
                canonical_field=canonical_field,
                value=value,
                source_doc=record.filename,
                source_page=page_no,
                confidence=score_llm_extraction(raw),
                extraction_method="llm_structured",
                model_name=model_name,
                extracted_at=now,
                confirmed_by_user=False,
            )
        )
    return out


def extract_facts(
    record: DocumentRecord, pages: list[PageText]
) -> list[TaxFact]:
    if record.document_type == "unknown":
        return []
    stage1, matched = _stage_one_regex(record, pages)
    stage2 = _stage_two_llm(record, pages, matched)
    return [*stage1, *stage2]


__all__ = ["extract_facts"]
