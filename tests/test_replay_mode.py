"""DEMO_MODE=replay path tests. NO live network. NO live OCR."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _activate_replay(monkeypatch: pytest.MonkeyPatch, scenario: str = "expat_c_permit_basic") -> None:
    monkeypatch.setenv("DEMO_MODE", "replay")
    monkeypatch.setenv("DEMO_SCENARIO", scenario)
    import importlib

    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)


def test_replay_returns_canned_extraction_for_default_scenario(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _activate_replay(monkeypatch)
    from TaxAI2025.extraction import extract_from_upload

    record, facts = extract_from_upload("any/path/synthetic_certificat.pdf")
    assert record.document_type in {
        "salary_certificate",
        "health_insurance_premium",
        "daycare_invoice",
        "pillar_3a_certificate",
        "transport_pass",
        "bank_year_end_statement",
    }
    assert len(facts) >= 3
    assert all(f.confirmed_by_user is False for f in facts)
    assert all(f.source_doc and f.source_page >= 1 for f in facts)


def test_replay_loads_demo_spec_three_doc_types(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per DEMO_SCRIPT.md, Sarah uploads 3 docs (salary, insurance, bank).
    childcare / pillar 3a / transport are intentionally omitted so the
    completeness engine surfaces them as findings."""
    _activate_replay(monkeypatch)
    from TaxAI2025.extraction import extract_from_upload

    _, facts = extract_from_upload("ignored.pdf")
    fields = {f.canonical_field for f in facts}
    assert "salary.gross_annual_chf" in fields
    assert "health_insurance.annual_premium_chf" in fields
    assert "bank.year_end_balance_chf" in fields
    # Intentionally absent — completeness engine flags these.
    assert "childcare.total_paid_chf" not in fields
    assert "pillar_3a.annual_contribution_chf" not in fields
    assert "transport.annual_cost_chf" not in fields


def test_replay_missing_scenario_raises(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _activate_replay(monkeypatch, scenario="does-not-exist")
    from TaxAI2025.extraction import extract_from_upload
    from TaxAI2025.extraction.replay import ReplayError

    with pytest.raises(ReplayError, match="Replay fixture missing"):
        extract_from_upload("ignored.pdf")


def test_replay_with_confirmed_fact_in_fixture_raises(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A fixture that pre-confirms a fact must be rejected."""
    scenario = "bad_scenario_confirmed_fact"
    scenario_dir = tmp_path / "demo" / "scenarios" / scenario
    scenario_dir.mkdir(parents=True)
    fixture = scenario_dir / "extracted.json"
    fixture.write_text(
        json.dumps(
            {
                "document": {
                    "doc_id": "x",
                    "filename": "x.pdf",
                    "file_path": "<replay>/x.pdf",
                    "document_type": "salary_certificate",
                    "classifier_confidence": 0.95,
                    "classifier_method": "heuristic",
                    "pdf_page_count": 1,
                },
                "facts": [
                    {
                        "canonical_field": "salary.gross_annual_chf",
                        "value": 1.0,
                        "source_doc": "x.pdf",
                        "source_page": 1,
                        "extraction_method": "regex",
                        "confirmed_by_user": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("DEMO_MODE", "replay")
    monkeypatch.setenv("DEMO_SCENARIO", scenario)
    import importlib

    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)
    monkeypatch.setattr(cfg, "REPO_ROOT", tmp_path, raising=False)

    from TaxAI2025.extraction import extract_from_upload
    from TaxAI2025.extraction.replay import ReplayError

    with pytest.raises(ReplayError, match="confirmed_by_user=True"):
        extract_from_upload("ignored.pdf")


def test_replay_invalid_json_raises(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenario = "bad_json_scenario"
    scenario_dir = tmp_path / "demo" / "scenarios" / scenario
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "extracted.json").write_text("{not json", encoding="utf-8")

    monkeypatch.setenv("DEMO_MODE", "replay")
    monkeypatch.setenv("DEMO_SCENARIO", scenario)
    import importlib

    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)
    monkeypatch.setattr(cfg, "REPO_ROOT", tmp_path, raising=False)

    from TaxAI2025.extraction import extract_from_upload
    from TaxAI2025.extraction.replay import ReplayError

    with pytest.raises(ReplayError, match="not valid JSON"):
        extract_from_upload("ignored.pdf")
