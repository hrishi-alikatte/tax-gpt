"""Lock the demo PDF generators to the extractor's regex contract.

If either side drifts (PDF wording changes OR regex tightens) one of
these assertions will fail, surfacing the mismatch in CI rather than
on demo day. Skips automatically if reportlab is not installed (it's a
dev-only dep, not in requirements.txt).
"""
from __future__ import annotations

from pathlib import Path

import pytest

reportlab = pytest.importorskip("reportlab")  # noqa: F841

from scripts import generate_custom_pdfs as gen  # noqa: E402
from TaxAI2025.extraction import extract_from_upload  # noqa: E402


# (filename, expected doc_type, set of canonical fields the extractor MUST produce)
CASES = [
    ("01_certificat_salaire.pdf", "salary_certificate",
     {"salary.gross_annual_chf", "salary.net_annual_chf"}),
    ("02_prime_assurance_maladie.pdf", "health_insurance_premium",
     {"health_insurance.annual_premium_chf"}),
    ("03_pilier_3a.pdf", "pillar_3a_certificate",
     {"pillar_3a.annual_contribution_chf"}),
    ("04_garderie.pdf", "daycare_invoice",
     {"childcare.total_paid_chf"}),
    ("05_releve_bcv.pdf", "bank_year_end_statement",
     {"bank.year_end_balance_chf", "bank.annual_interest_chf"}),
    ("06_abonnement_cff.pdf", "transport_pass",
     {"transport.annual_cost_chf"}),
    ("07_attestation-don.pdf", "donation_receipt",
     {"donations.total_chf"}),
]


@pytest.fixture(scope="module")
def generated_pdfs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate all 8 PDFs into a tmp dir for the test session."""
    out = tmp_path_factory.mktemp("custom_tests")
    builder_by_filename = {fname: builder for fname, builder in gen.SPEC}
    for fname in builder_by_filename:
        builder_by_filename[fname](out / fname)
    return out


@pytest.fixture
def disable_replay_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Earlier tests in the suite (test_replay_mode.py) may have left
    `config.DEMO_MODE == "replay"` after `importlib.reload(cfg)`. That makes
    `extract_from_upload` short-circuit to canned scenario fixtures
    regardless of the file we hand it. Force a config reload with the env
    cleared so this test exercises the real classifier + extractor.
    """
    monkeypatch.delenv("DEMO_MODE", raising=False)
    import importlib

    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)


@pytest.mark.parametrize("filename, expected_doc_type, expected_fields", CASES)
def test_synthetic_pdf_extracts_expected_fields(
    disable_replay_mode: None,
    generated_pdfs: Path,
    filename: str,
    expected_doc_type: str,
    expected_fields: set[str],
) -> None:
    record, facts = extract_from_upload(generated_pdfs / filename)
    assert record.document_type == expected_doc_type, (
        f"{filename}: classified as {record.document_type!r}, expected {expected_doc_type!r}"
    )
    actual_fields = {f.canonical_field for f in facts}
    missing = expected_fields - actual_fields
    assert not missing, (
        f"{filename}: extractor missed fields {missing}. "
        f"Likely the PDF wording no longer matches the regex in "
        f"TaxAI2025/extraction/extract.py. Actual fields: {actual_fields}"
    )
