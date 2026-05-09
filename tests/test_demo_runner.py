"""Demo runner CLI tests. NO live network. NO live OCR (replay path)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from demo import runner


def test_runner_exits_zero_for_default_scenario(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    rc = runner.main(["--scenario", "expat_c_permit_basic"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "[OK]" in out
    # Demo punchline: 3 findings each with a real Vaud 2025 page.
    assert "VD-CHILDCARE-001" in out
    assert "VD-COMMUTE-001" in out
    assert "VD-PILLAR3A-001" in out
    assert "[Vaud 2025 Instructions p.44]" in out
    assert "[Vaud 2025 Instructions p.20]" in out
    assert "[Vaud 2025 Instructions p.31]" in out


def test_runner_completes_under_three_seconds(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    rc = runner.main(["--scenario", "expat_c_permit_basic", "--strict-3s"])
    assert rc == 0, capsys.readouterr().out


def test_runner_exits_one_when_expected_diverges(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Build a temporary scenario whose expected.json deliberately mismatches
    the runner output. Must exit 1 with a clear diff."""
    scenario = "diverging_expectations"
    scen_dir = tmp_path / "demo" / "scenarios" / scenario
    scen_dir.mkdir(parents=True)
    (scen_dir / "profile.json").write_text(
        json.dumps(
            {
                "first_name": "Test",
                "permit_type": "C",
                "marital_status": "single",
                "children_count": 0,
                "commune_of_residence": "Lausanne",
                "employer_name": "ACME",
                "work_commune": "Renens",
                "tax_year": 2024,
                "has_workplace_canteen": True,
            }
        ),
        encoding="utf-8",
    )
    (scen_dir / "extracted.json").write_text(
        json.dumps(
            {
                "document": {
                    "doc_id": "x",
                    "filename": "x.pdf",
                    "file_path": "<replay>/x.pdf",
                    "document_type": "health_insurance_premium",
                    "classifier_confidence": 0.95,
                    "classifier_method": "heuristic",
                    "pdf_page_count": 1,
                },
                "facts": [
                    {
                        "canonical_field": "health_insurance.annual_premium_chf",
                        "value": 4200.0,
                        "source_doc": "x.pdf",
                        "source_page": 1,
                        "extraction_method": "regex",
                        "confidence": 1.0,
                        "confirmed_by_user": False,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (scen_dir / "expected.json").write_text(
        json.dumps(
            {
                "facts_count": 99,
                "findings_count": 0,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(runner, "SCENARIOS_DIR", tmp_path / "demo" / "scenarios")
    # extract_from_upload's replay loader resolves fixtures via
    # replay._scenarios_dir() -> config.REPO_ROOT / "demo" / "scenarios".
    # Patch the helper directly so it returns our tmp scenarios dir
    # regardless of how the runner reloads config internally.
    from TaxAI2025.extraction import replay

    scenarios_root = tmp_path / "demo" / "scenarios"
    monkeypatch.setattr(replay, "_scenarios_dir", lambda: scenarios_root)

    rc = runner.main(["--scenario", scenario])
    assert rc == 1


def test_runner_dump_audit_prints_log_size(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    rc = runner.main(
        ["--scenario", "expat_c_permit_basic", "--dump-audit"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "audit log size:" in out


def test_runner_verbose_prints_facts_and_profile(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    rc = runner.main(
        ["--scenario", "expat_c_permit_basic", "--verbose"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "profile:" in out
    assert "facts:" in out
    assert "Sarah" in out  # Sarah's first_name is in the profile


def test_runner_unknown_scenario_raises_system_exit(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(SystemExit):
        runner.main(["--scenario", "definitely-does-not-exist"])
