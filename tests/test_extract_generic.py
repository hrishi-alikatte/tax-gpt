"""Generic unknown-document extraction. NO live network."""
from __future__ import annotations

import pytest

from TaxAI2025.core.documents import DocumentRecord
from TaxAI2025.extraction.ocr import PageText


def _unknown_record() -> DocumentRecord:
    return DocumentRecord(
        doc_id="doc-unknown",
        filename="opaque.pdf",
        file_path="<test>/opaque.pdf",
        document_type="unknown",
        classifier_confidence=0.0,
        classifier_method="unknown",
        pdf_page_count=1,
    )


def test_generic_extraction_returns_pending_unconfirmed_facts(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from TaxAI2025.ai import model_router
    from TaxAI2025.extraction.generic import extract_generic_facts

    monkeypatch.setattr(
        model_router,
        "generate_json",
        lambda *a, **k: {
            "facts": [
                {
                    "label_en": "Professional membership fee",
                    "label_fr": "Cotisation professionnelle",
                    "value": 240.0,
                    "currency": "CHF",
                    "source_page": 1,
                    "confidence": 0.74,
                }
            ]
        },
    )

    facts = extract_generic_facts(
        _unknown_record(),
        [PageText(pdf_page=1, text="Cotisation professionnelle CHF 240.00")],
    )

    assert len(facts) == 1
    assert facts[0].label_en == "Professional membership fee"
    assert facts[0].source_doc == "opaque.pdf"
    assert facts[0].source_page == 1
    assert facts[0].confirmed_by_user is False
    assert facts[0].pending_user_review is True


def test_generic_extraction_drops_invalid_pages(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from TaxAI2025.ai import model_router
    from TaxAI2025.extraction.generic import extract_generic_facts

    monkeypatch.setattr(
        model_router,
        "generate_json",
        lambda *a, **k: {
            "facts": [
                {
                    "label_en": "Bad page",
                    "label_fr": None,
                    "value": 1,
                    "currency": "CHF",
                    "source_page": 99,
                    "confidence": 0.9,
                }
            ]
        },
    )

    assert extract_generic_facts(_unknown_record(), [PageText(pdf_page=1, text="x")]) == []


def test_generic_extraction_skips_known_document_types(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from TaxAI2025.extraction.generic import extract_generic_facts

    record = _unknown_record().model_copy(update={"document_type": "salary_certificate"})
    assert extract_generic_facts(record, [PageText(pdf_page=1, text="x")]) == []
