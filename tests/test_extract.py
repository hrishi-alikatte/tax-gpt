"""Field extractor tests. NO live network. generate_json + pages stubbed."""
from __future__ import annotations

from typing import Any

import pytest

from TaxAI2025.core.documents import DocumentRecord
from TaxAI2025.extraction.ocr import PageText


def _record(doc_type: str, filename: str = "synthetic.pdf") -> DocumentRecord:
    return DocumentRecord(
        doc_id="doc-1",
        filename=filename,
        file_path=f"<replay>/{filename}",
        document_type=doc_type,  # type: ignore[arg-type]
        classifier_confidence=0.95,
        classifier_method="heuristic",
        pdf_page_count=1,
    )


def test_regex_stage_extracts_salary_gross_with_full_provenance(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = [
        PageText(
            pdf_page=1,
            text="CERTIFICAT DE SALAIRE 2025\nSalaire brut annuel CHF 120'000.00\nSalaire net annuel CHF 96'000.00",
        )
    ]

    from TaxAI2025.ai import model_router

    monkeypatch.setattr(
        model_router,
        "generate_json",
        lambda *a, **k: {"facts": []},
    )

    from TaxAI2025.extraction.extract import extract_facts

    facts = extract_facts(_record("salary_certificate"), pages)
    by_field = {f.canonical_field: f for f in facts}

    assert "salary.gross_annual_chf" in by_field
    gross = by_field["salary.gross_annual_chf"]
    assert gross.value == pytest.approx(120000.0)
    assert gross.source_doc == "synthetic.pdf"
    assert gross.source_page == 1
    assert gross.extraction_method == "regex"
    assert gross.confidence == pytest.approx(1.0)
    assert gross.confirmed_by_user is False
    assert gross.model_name is None


def test_extractor_never_returns_confirmed_facts(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = [
        PageText(
            pdf_page=1,
            text="Solde au 31 décembre 2025: CHF 42'000.00\nIntérêts perçus: 12.50",
        )
    ]
    from TaxAI2025.ai import model_router

    monkeypatch.setattr(
        model_router,
        "generate_json",
        lambda *a, **k: {
            "facts": [
                {
                    "canonical_field": "bank.annual_interest_chf",
                    "value": 12.50,
                    "source_page": 1,
                    "confidence": 0.6,
                }
            ]
        },
    )

    from TaxAI2025.extraction.extract import extract_facts

    facts = extract_facts(_record("bank_year_end_statement"), pages)
    assert facts, "expected at least one fact from regex stage"
    assert all(f.confirmed_by_user is False for f in facts)


def test_llm_residual_only_runs_when_regex_misses_a_field(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = [
        PageText(
            pdf_page=1,
            text="Salaire brut annuel CHF 100'000.00\nSalaire net annuel CHF 80'000.00",
        )
    ]

    captured: list[dict[str, Any]] = []

    def fake_generate_json(messages, schema, purpose, *, temperature=0.0):  # noqa: ARG001
        captured.append({"schema": schema, "purpose": purpose})
        return {
            "facts": [
                {
                    "canonical_field": "salary.ahv_iv_eo_chf",
                    "value": 5300.0,
                    "source_page": 1,
                    "confidence": 0.7,
                }
            ]
        }

    from TaxAI2025.ai import model_router

    monkeypatch.setattr(model_router, "generate_json", fake_generate_json)

    from TaxAI2025.extraction.extract import extract_facts

    facts = extract_facts(_record("salary_certificate"), pages)
    assert any(f.canonical_field == "salary.gross_annual_chf" for f in facts)
    assert any(f.canonical_field == "salary.ahv_iv_eo_chf" for f in facts)
    ahv = next(f for f in facts if f.canonical_field == "salary.ahv_iv_eo_chf")
    assert ahv.extraction_method == "llm_structured"
    assert ahv.model_name is not None and "azure" in ahv.model_name
    assert ahv.confidence == pytest.approx(0.7)

    # The LLM must NOT be asked for fields the regex already matched.
    assert captured, "LLM should be invoked for residual fields"
    schema_fields = (
        captured[0]["schema"]["properties"]["facts"]["items"]["properties"][
            "canonical_field"
        ]["enum"]
    )
    assert "salary.gross_annual_chf" not in schema_fields
    assert "salary.ahv_iv_eo_chf" in schema_fields


def test_llm_residual_receives_full_page_text(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    long_text = "A" * 8000 + "TAIL_MARKER_AFTER_8000"
    pages = [PageText(pdf_page=1, text=long_text)]
    captured_user_messages: list[str] = []

    def fake_generate_json(messages, schema, purpose, *, temperature=0.0):  # noqa: ARG001
        captured_user_messages.append(messages[1]["content"])
        return {"facts": []}

    from TaxAI2025.ai import model_router

    monkeypatch.setattr(model_router, "generate_json", fake_generate_json)

    from TaxAI2025.extraction.extract import extract_facts

    assert extract_facts(_record("pillar_3a_certificate"), pages) == []
    assert "TAIL_MARKER_AFTER_8000" in captured_user_messages[0]


def test_llm_residual_schema_has_no_fact_item_cap() -> None:
    from TaxAI2025.extraction.extract import _llm_residual_schema

    schema = _llm_residual_schema(["pillar_3a.annual_contribution_chf"])
    facts_schema = schema["properties"]["facts"]
    assert "maxItems" not in facts_schema


def test_llm_facts_with_invalid_pages_are_dropped(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = [PageText(pdf_page=1, text="Some short text without any matchable pattern.")]
    from TaxAI2025.ai import model_router

    monkeypatch.setattr(
        model_router,
        "generate_json",
        lambda *a, **k: {
            "facts": [
                {
                    "canonical_field": "pillar_3a.annual_contribution_chf",
                    "value": 7056.0,
                    "source_page": 99,
                    "confidence": 0.8,
                }
            ]
        },
    )

    from TaxAI2025.extraction.extract import extract_facts

    facts = extract_facts(_record("pillar_3a_certificate"), pages)
    assert facts == []


def test_unknown_doc_type_returns_no_facts(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = [PageText(pdf_page=1, text="anything")]
    from TaxAI2025.ai import model_router

    monkeypatch.setattr(model_router, "generate_json", lambda *a, **k: {"facts": []})

    from TaxAI2025.extraction.extract import extract_facts

    assert extract_facts(_record("unknown"), pages) == []
