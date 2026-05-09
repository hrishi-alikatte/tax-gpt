"""Expanded document registry guardrails for Phase B1."""
from __future__ import annotations

from typing import Any

import pytest

from TaxAI2025.core.documents import KNOWN_DOCUMENT_TYPES, DocumentRecord
from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.extraction.ocr import PageText
from TaxAI2025.ui.state import AppState


NEW_DOCUMENT_EXAMPLES: dict[str, tuple[str, str, str, Any]] = {
    "mortgage_interest_statement": (
        "interets-hypothecaires_2024.pdf",
        "Attestation intérêts hypothécaires\nIntérêts hypothécaires CHF 8'450.00",
        "mortgage.annual_interest_chf",
        8450.0,
    ),
    "alimony_paid_received": (
        "pension-alimentaire_2024.pdf",
        "Pension alimentaire payée CHF 12'000.00",
        "alimony.paid_chf",
        12000.0,
    ),
    "donation_receipt": (
        "attestation-don_2024.pdf",
        "Attestation de don\nMontant du don CHF 500.00",
        "donations.total_chf",
        500.0,
    ),
    "parental_support_receipt": (
        "soutien-parents_2024.pdf",
        "Soutien aux parents CHF 2'400.00",
        "parental_support.paid_chf",
        2400.0,
    ),
    "medical_bills_unreimbursed": (
        "facture-sante_non-rembourse_2024.pdf",
        "Frais médicaux non remboursés CHF 1'250.00",
        "medical.unreimbursed_chf",
        1250.0,
    ),
    "education_invoice": (
        "formation_continue_2024.pdf",
        "Frais de formation CHF 3'200.00",
        "education.tuition_paid_chf",
        3200.0,
    ),
    "second_pillar_buyback_attestation": (
        "rachat-2e-pilier_2024.pdf",
        "Rachat 2e pilier CHF 15'000.00",
        "pillar2.buyback_chf",
        15000.0,
    ),
    "foreign_income_attestation": (
        "revenu-etranger_2024.pdf",
        "Revenu étranger brut CHF 22'000.00",
        "foreign_income.gross_chf",
        22000.0,
    ),
    "disability_proof": (
        "rente-ai_2024.pdf",
        "Attestation invalidité - rente AI reconnue",
        "disability.acknowledged",
        True,
    ),
    "unemployment_benefits_attestation": (
        "indemnite-chomage_2024.pdf",
        "Indemnités de chômage CHF 9'800.00",
        "unemployment.benefits_chf",
        9800.0,
    ),
}


def _record(doc_type: str, filename: str) -> DocumentRecord:
    return DocumentRecord(
        doc_id=f"doc-{doc_type}",
        filename=filename,
        file_path=f"<test>/{filename}",
        document_type=doc_type,  # type: ignore[arg-type]
        classifier_confidence=0.95,
        classifier_method="heuristic",
        pdf_page_count=1,
    )


def _fact(field: str, value: Any = 100.0) -> TaxFact:
    return TaxFact(
        canonical_field=field,
        value=value,
        source_doc="synthetic.pdf",
        source_page=1,
        confidence=1.0,
        extraction_method="regex",
    )


def test_expanded_registry_is_16_known_types_plus_unknown() -> None:
    assert len(KNOWN_DOCUMENT_TYPES) == 16
    assert "unknown" not in KNOWN_DOCUMENT_TYPES


def test_document_type_registry_stays_aligned() -> None:
    from TaxAI2025.extraction import classify, extract
    from TaxAI2025.ui.state import REQUIRED_FIELDS_BY_DOC_TYPE
    from TaxAI2025.ui.views.upload_view import _DOC_TYPE_LABELS

    known = set(KNOWN_DOCUMENT_TYPES)
    assert set(classify._FILENAME_KEYWORDS) == known
    assert set(classify._HEADER_KEYWORDS) == known
    assert known.issubset(set(extract._RESIDUAL_FIELDS))
    assert known.issubset(set(REQUIRED_FIELDS_BY_DOC_TYPE))
    assert known.issubset(set(_DOC_TYPE_LABELS))
    assert REQUIRED_FIELDS_BY_DOC_TYPE["unknown"] == ()
    assert extract._RESIDUAL_FIELDS["unknown"] == []


@pytest.mark.parametrize(
    "doc_type,example",
    NEW_DOCUMENT_EXAMPLES.items(),
)
def test_new_document_types_classify_from_filename(
    azure_env: None,
    monkeypatch: pytest.MonkeyPatch,
    doc_type: str,
    example: tuple[str, str, str, Any],
) -> None:
    from TaxAI2025.extraction import classify

    filename, _text, _field, _value = example
    monkeypatch.setattr(classify, "_read_first_page_text", lambda p: "")
    monkeypatch.setattr(classify, "_safe_page_count", lambda p: None)
    record = classify.classify_document(filename)
    assert record.document_type == doc_type
    assert record.classifier_method == "heuristic"


@pytest.mark.parametrize(
    "doc_type,example",
    NEW_DOCUMENT_EXAMPLES.items(),
)
def test_new_document_types_extract_required_fact_from_synthetic_text(
    azure_and_groq_env: None,
    monkeypatch: pytest.MonkeyPatch,
    doc_type: str,
    example: tuple[str, str, str, Any],
) -> None:
    from TaxAI2025.ai import model_router
    from TaxAI2025.extraction.extract import extract_facts

    filename, text, field, expected_value = example
    monkeypatch.setattr(model_router, "generate_json", lambda *a, **k: {"facts": []})
    facts = extract_facts(_record(doc_type, filename), [PageText(pdf_page=1, text=text)])
    by_field = {f.canonical_field: f for f in facts}
    assert field in by_field
    assert by_field[field].value == expected_value
    assert by_field[field].confirmed_by_user is False


@pytest.mark.parametrize(
    "doc_type,example",
    NEW_DOCUMENT_EXAMPLES.items(),
)
def test_new_document_types_do_not_dead_end_confirmation(
    doc_type: str,
    example: tuple[str, str, str, Any],
) -> None:
    _filename, _text, field, value = example
    state = AppState()
    state.add_document(_record(doc_type, "synthetic.pdf"), [_fact(field, value)])
    assert state.is_extracted_complete() is False
    state.confirm_fact(field)
    assert state.is_extracted_complete() is True


def test_broad_document_keywords_do_not_match_common_unrelated_filenames(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from TaxAI2025.ai import model_router
    from TaxAI2025.extraction import classify

    monkeypatch.setattr(classify, "_read_first_page_text", lambda p: "")
    monkeypatch.setattr(classify, "_safe_page_count", lambda p: None)
    monkeypatch.setattr(
        model_router,
        "generate_json",
        lambda *a, **k: {"document_type": "unknown", "confidence": 0.0},
    )

    for filename in ("random-ai-notes.pdf", "done-list.pdf", "civil-status.pdf"):
        record = classify.classify_document(filename)
        assert record.document_type == "unknown"
