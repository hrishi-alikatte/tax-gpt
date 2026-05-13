"""Per-doc-type field extraction.

Stage 1: LLM structured extraction per page.
Stage 2: deterministic regex/template cross-checks for high-confidence fields.

Every TaxFact returned carries source_doc, source_page, extraction_method,
extracted_at, and `confirmed_by_user=False`. The extraction layer is
forbidden from setting `confirmed_by_user=True` — that bit belongs to the
UI confirmation gate.
"""
from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

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
                    snippet=m.group(0).strip(),
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
            bool_match = pattern.search(page.text)
            if not bool_match:
                continue
            facts.append(
                TaxFact(
                    canonical_field=canonical_field,
                    value=value,
                    source_doc=record.filename,
                    source_page=page.pdf_page,
                    snippet=bool_match.group(0).strip(),
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
        "required": [
            "canonical_field",
            "value",
            "source_page",
            "snippet",
            "confidence",
        ],
        "properties": {
            "canonical_field": {"type": "string", "enum": target_fields},
            "value": {"type": ["number", "string", "null"]},
            "source_page": {"type": "integer", "minimum": 1},
            "snippet": {"type": "string"},
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


def _snippet_in_page(snippet: str, page_text: str) -> bool:
    normalized = snippet.strip().casefold()
    return bool(normalized) and normalized in page_text.casefold()


# ---------------------------------------------------------------------------
# Multi-page context extraction
# ---------------------------------------------------------------------------

MAX_PAGES_PER_BATCH = 3  # Swiss salary certs typically span 2–3 pages


def _build_context_window(
    pages: list[PageText], focus_page_idx: int
) -> tuple[list[PageText], str]:
    """Build a context window of adjacent pages around the focus page.

    Returns (context_pages, context_text) where context_pages are the pages
    included in the window (for provenance validation).
    """
    start = max(0, focus_page_idx - 1)
    end = min(len(pages), focus_page_idx + 2)  # exclusive
    context_pages = pages[start:end]
    context_text = ""
    for p in context_pages:
        context_text += f"\n--- PAGE {p.pdf_page} ---\n{p.text}\n"
    return context_pages, context_text


def _llm_extract_with_context(
    record: DocumentRecord,
    pages: list[PageText],
    target_fields: list[str],
) -> list[TaxFact]:
    """Extract fields using multi-page context windows.

    Instead of processing each page in isolation, we build sliding windows
    of adjacent pages. This is critical for Swiss documents where values
    like gross/net salary and deductions span multiple pages.
    """
    if not target_fields or not pages:
        return []

    from TaxAI2025.ai import model_router

    schema = _llm_residual_schema(target_fields)

    # Group pages into overlapping context windows
    windows: list[tuple[int, list[PageText], str]] = []
    if len(pages) <= MAX_PAGES_PER_BATCH:
        # Small doc: process all pages together
        all_text = ""
        for p in pages:
            all_text += f"\n--- PAGE {p.pdf_page} ---\n{p.text}\n"
        windows.append((0, pages, all_text))
    else:
        # Larger doc: use sliding windows with overlap
        for i in range(0, len(pages), MAX_PAGES_PER_BATCH - 1):
            window_pages = pages[i : i + MAX_PAGES_PER_BATCH]
            window_text = ""
            for p in window_pages:
                window_text += f"\n--- PAGE {p.pdf_page} ---\n{p.text}\n"
            windows.append((i, window_pages, window_text))

    now = datetime.utcnow()
    routing = model_router.route("document_extraction")
    model_name = f"{routing['provider']}:{routing['deployment']}"

    all_facts: list[TaxFact] = []
    seen_fields: set[str] = set()

    for window_idx, window_pages, window_text in windows:
        system = (
            "You extract Swiss Vaud tax fields from a tax document. "
            "Return strict JSON matching the provided schema. "
            "Only include fields you can locate in the source text. "
            "source_page must be the 1-indexed PDF page where the value appears. "
            "snippet must be copied literally from the source text and support the value. "
            "Never invent values. Never invent pages. If unsure, omit the field.\n\n"
            "The document may span multiple pages. Each page is marked with --- PAGE N ---. "
            "Use the page number where the value actually appears for source_page."
        )
        user = (
            f"Document type: {record.document_type}\n"
            f"Target fields: {', '.join(target_fields)}\n\n"
            f"{window_text}"
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
        except Exception as e:
            logger.warning("LLM extraction failed for window %d: %s", window_idx, e)
            continue

        raw_facts = payload.get("facts") if isinstance(payload, dict) else None
        if not isinstance(raw_facts, list):
            continue

        # Build set of valid page numbers for this window
        valid_pages = {p.pdf_page for p in window_pages}
        # Build text lookup for validation
        page_text_map = {p.pdf_page: p.text for p in window_pages}

        for raw in raw_facts:
            if not isinstance(raw, dict):
                continue
            canonical_field = raw.get("canonical_field")
            if canonical_field not in target_fields:
                continue
            if canonical_field in seen_fields:
                continue
            value = raw.get("value")
            if value is None:
                continue
            page_no = raw.get("source_page")
            if page_no not in valid_pages:
                continue
            snippet = raw.get("snippet")
            if not isinstance(snippet, str):
                continue
            # Validate snippet appears on claimed page
            page_text = page_text_map.get(page_no, "")
            if not _snippet_in_page(snippet, page_text):
                continue

            all_facts.append(
                TaxFact(
                    canonical_field=canonical_field,
                    value=value,
                    source_doc=record.filename,
                    source_page=page_no,
                    snippet=snippet,
                    confidence=score_llm_extraction(raw),
                    extraction_method="llm_structured",
                    model_name=model_name,
                    extracted_at=now,
                    confirmed_by_user=False,
                )
            )
            seen_fields.add(canonical_field)

    return all_facts


def _llm_extract_page(
    record: DocumentRecord,
    page: PageText,
    target_fields: list[str],
) -> list[TaxFact]:
    """DEPRECATED: Use _llm_extract_with_context for production.

    Kept for backward compatibility in tests.
    """
    if not target_fields:
        return []

    from TaxAI2025.ai import model_router

    schema = _llm_residual_schema(target_fields)
    system = (
        "You extract Swiss Vaud tax fields from one PDF page. "
        "Return strict JSON matching the provided schema. "
        "Only include fields you can locate in the source text. "
        "source_page must be the 1-indexed PDF page where the value appears. "
        f"The only valid source_page is {page.pdf_page}. "
        "snippet must be copied literally from the source text and support the value. "
        "Never invent values. Never invent pages. If unsure, omit the field."
    )
    user = (
        f"Document type: {record.document_type}\n"
        f"Target fields: {', '.join(target_fields)}\n\n"
        f"[page {page.pdf_page}]\n{page.text}"
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
        if page_no != page.pdf_page:
            continue
        snippet = raw.get("snippet")
        if not isinstance(snippet, str) or not _snippet_in_page(snippet, page.text):
            continue
        out.append(
            TaxFact(
                canonical_field=canonical_field,
                value=value,
                source_doc=record.filename,
                source_page=page.pdf_page,
                snippet=snippet,
                confidence=score_llm_extraction(raw),
                extraction_method="llm_structured",
                model_name=model_name,
                extracted_at=now,
                confirmed_by_user=False,
            )
        )
    return out


def _values_equivalent(left: Any, right: Any) -> bool:
    try:
        return abs(float(left) - float(right)) < 0.01
    except (TypeError, ValueError):
        return str(left).strip().casefold() == str(right).strip().casefold()


def _dedupe_by_field(facts: Iterable[TaxFact]) -> list[TaxFact]:
    by_field: dict[str, TaxFact] = {}
    for fact in facts:
        existing = by_field.get(fact.canonical_field)
        if existing is None:
            by_field[fact.canonical_field] = fact
            continue
        existing_conf = existing.confidence if existing.confidence is not None else -1.0
        fact_conf = fact.confidence if fact.confidence is not None else -1.0
        if fact_conf > existing_conf:
            by_field[fact.canonical_field] = fact
    return list(by_field.values())


def _llm_extract_document(record: DocumentRecord, pages: list[PageText]) -> list[TaxFact]:
    """Extract facts from document using multi-page context.

    For documents with ≤3 pages, processes all pages together.
    For longer documents, uses sliding windows.
    """
    target_fields = _RESIDUAL_FIELDS.get(record.document_type, [])
    if not target_fields:
        return []

    # Use multi-page context extraction
    facts = _llm_extract_with_context(record, pages, target_fields)
    return _dedupe_by_field(facts)


def _regex_cross_check(
    record: DocumentRecord, pages: list[PageText], llm_facts: list[TaxFact]
) -> list[TaxFact]:
    regex_facts, _matched = _stage_one_regex(record, pages)
    by_field = {fact.canonical_field: fact for fact in llm_facts}
    merged = list(llm_facts)
    for regex_fact in regex_facts:
        llm_fact = by_field.get(regex_fact.canonical_field)
        if llm_fact is None:
            merged.append(regex_fact)
            continue
        if _values_equivalent(llm_fact.value, regex_fact.value):
            base_confidence = (
                llm_fact.confidence
                if llm_fact.confidence is not None
                else LLM_DEFAULT_CONFIDENCE
            )
            llm_fact.confidence = min(base_confidence + 0.1, 1.0)
            if not llm_fact.snippet:
                llm_fact.snippet = regex_fact.snippet
    return _dedupe_by_field(merged)


def extract_facts(
    record: DocumentRecord, pages: list[PageText]
) -> list[TaxFact]:
    if record.document_type == "unknown":
        return []
    llm_facts = _llm_extract_document(record, pages)
    return _regex_cross_check(record, pages, llm_facts)


__all__ = ["extract_facts"]
