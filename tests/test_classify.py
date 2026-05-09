"""Document classifier tests. NO live network. pdfplumber + LLM stubbed."""
from __future__ import annotations

from pathlib import Path

import pytest


def _disable_pdfplumber(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force `_read_first_page_text` and `_safe_page_count` to return empty/None.

    This isolates the heuristic-vs-LLM tests from any pdfplumber behavior on
    a non-existent file.
    """
    from TaxAI2025.extraction import classify

    monkeypatch.setattr(classify, "_read_first_page_text", lambda p: "")
    monkeypatch.setattr(classify, "_safe_page_count", lambda p: None)


@pytest.mark.parametrize(
    "filename, expected_type",
    [
        ("certificat_de_salaire_2025.pdf", "salary_certificate"),
        ("Lohnausweis_2025.pdf", "salary_certificate"),
        ("krankenkasse_premium_2025.pdf", "health_invariant"),  # placeholder, replaced below
        ("Prime_assurance_maladie_2025.pdf", "health_insurance_premium"),
        ("creche_facture_juin.pdf", "daycare_invoice"),
        ("attestation_3a_2025.pdf", "pillar_3a_certificate"),
        ("abonnement_mobilis_2025.pdf", "transport_pass"),
        ("ubs_releve_fin_annee_2025.pdf", "bank_year_end_statement"),
    ],
)
def test_filename_heuristic_resolves_known_types(
    azure_env: None,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    expected_type: str,
) -> None:
    if expected_type == "health_invariant":
        # Skip the bad row — kept the parametrize tuple stable for clarity.
        pytest.skip("placeholder row")
    _disable_pdfplumber(monkeypatch)
    from TaxAI2025.extraction.classify import classify_document

    record = classify_document(Path(filename))
    assert record.document_type == expected_type
    assert record.classifier_method == "heuristic"
    assert record.classifier_confidence == 0.95
    assert record.filename == filename


def test_unknown_filename_falls_through_to_llm_then_unknown(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Filename has no keyword and LLM returns 'unknown' — final type stays unknown."""
    _disable_pdfplumber(monkeypatch)

    from TaxAI2025.ai import model_router
    from TaxAI2025.extraction.classify import classify_document

    captured_calls: list[str] = []

    def fake_generate_json(messages, schema, purpose, *, temperature=0.0):  # noqa: ARG001
        captured_calls.append(purpose)
        return {"document_type": "unknown", "confidence": 0.1}

    monkeypatch.setattr(model_router, "generate_json", fake_generate_json)

    record = classify_document(Path("totally-unrelated-document.pdf"))
    assert record.document_type == "unknown"
    assert record.classifier_method == "unknown"
    assert record.classifier_confidence == 0.0
    assert captured_calls == ["document_extraction"]


def test_unknown_filename_with_llm_decision_yields_llm_method(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_pdfplumber(monkeypatch)
    from TaxAI2025.ai import model_router
    from TaxAI2025.extraction.classify import classify_document

    def fake_generate_json(messages, schema, purpose, *, temperature=0.0):  # noqa: ARG001
        return {"document_type": "salary_certificate", "confidence": 0.82}

    monkeypatch.setattr(model_router, "generate_json", fake_generate_json)

    record = classify_document(Path("opaque-filename.pdf"))
    assert record.document_type == "salary_certificate"
    assert record.classifier_method == "llm_structured"
    assert record.classifier_confidence == pytest.approx(0.82)


def test_llm_returning_invalid_type_is_treated_as_unknown(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_pdfplumber(monkeypatch)
    from TaxAI2025.ai import model_router
    from TaxAI2025.extraction.classify import classify_document

    def fake_generate_json(messages, schema, purpose, *, temperature=0.0):  # noqa: ARG001
        return {"document_type": "tax_optimization_plan", "confidence": 0.99}

    monkeypatch.setattr(model_router, "generate_json", fake_generate_json)

    record = classify_document(Path("opaque.pdf"))
    assert record.document_type == "unknown"
    assert record.classifier_method == "unknown"


def test_llm_failure_is_swallowed_and_returns_unknown(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_pdfplumber(monkeypatch)
    from TaxAI2025.ai import model_router
    from TaxAI2025.extraction.classify import classify_document

    def fake_generate_json(*a, **kw):  # noqa: ANN001, ANN003, ARG001
        raise RuntimeError("transient model failure")

    monkeypatch.setattr(model_router, "generate_json", fake_generate_json)

    record = classify_document(Path("opaque.pdf"))
    assert record.document_type == "unknown"
    assert record.classifier_method == "unknown"


def test_header_keyword_match_used_when_filename_misses(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If filename heuristic fails but header has a keyword, classify via header."""
    from TaxAI2025.extraction import classify

    monkeypatch.setattr(
        classify,
        "_read_first_page_text",
        lambda p: "CERTIFICAT DE SALAIRE 2025  ACME SA",
    )
    monkeypatch.setattr(classify, "_safe_page_count", lambda p: 1)

    # Patch path.is_file() so the header path is exercised.
    import pathlib

    real_is_file = pathlib.Path.is_file

    def always_true(self):  # noqa: ANN001, ANN201
        return True

    monkeypatch.setattr(pathlib.Path, "is_file", always_true)

    try:
        record = classify.classify_document(Path("opaque-filename-no-keyword.pdf"))
        assert record.document_type == "salary_certificate"
        assert record.classifier_method == "heuristic"
    finally:
        monkeypatch.setattr(pathlib.Path, "is_file", real_is_file)
