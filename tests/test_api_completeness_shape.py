"""Lock the wire-shape of /api/completeness/check.

If the backend ever drifts away from `list[Finding]` with the
documented field names, the Stage 5 Dashboard adapter in
`Vaud Tax Guide/src/lib/api.ts` will silently produce empty columns
again. This test catches that at build time, not in the browser.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


REQUIRED_FINDING_FIELDS = {
    "rule_id",
    "title_en",
    "message_en",
    "asks_for",
    "source_doc",
    "pdf_page",
    "severity",
    "verification_status",
}

ALLOWED_SEVERITIES = {"blocker", "likely_missing", "nice_to_have"}


def _empty_payload() -> dict:
    """Profile that triggers at least one rule but provides no facts."""
    return {
        "profile": {
            "first_name": "Sarah",
            "permit_type": "C",
            "marital_status": "married",
            "spouse_works": True,
            "children_count": 1,
            "children_ages": [4],
            "commune_of_residence": "Lausanne",
            "employer_name": "Aurelius SA",
            "work_commune": "Renens",
            "tax_year": 2025,
            "has_workplace_canteen": True,
        },
        "confirmed_facts": [],
    }


def test_completeness_endpoint_returns_flat_list_of_findings() -> None:
    client = TestClient(app)
    res = client.post("/api/completeness/check", json=_empty_payload())
    assert res.status_code == 200, res.text

    body = res.json()
    assert isinstance(body, list), (
        "Expected a flat list[Finding] (canonical shape consumed by the "
        "UI adapter in api.ts). The UI partitions by severity client-side."
    )
    assert body, "engine should emit at least one Finding for an empty fact set"

    for finding in body:
        missing = REQUIRED_FINDING_FIELDS - finding.keys()
        assert not missing, f"Finding missing fields {missing}: {finding}"
        assert finding["severity"] in ALLOWED_SEVERITIES, finding


def test_completeness_severities_partition_into_three_ui_buckets() -> None:
    """Every Finding must be assignable to one of the UI columns."""
    client = TestClient(app)
    res = client.post("/api/completeness/check", json=_empty_payload())
    body = res.json()
    severities = {f["severity"] for f in body}
    assert severities <= ALLOWED_SEVERITIES, (
        f"Unrecognized severities: {severities - ALLOWED_SEVERITIES}. "
        "If a new bucket is introduced, update the UI adapter in "
        "Vaud Tax Guide/src/lib/api.ts:checkCompleteness."
    )


def test_completeness_endpoint_accepts_interview_synthetic_facts() -> None:
    """Stage 5 folds interview answers into confirmed_facts before posting."""
    client = TestClient(app)
    payload = _empty_payload()
    payload["confirmed_facts"] = [
        {
            "canonical_field": "meal_allowance.method",
            "value": "canteen",
            "source_doc": "interview",
            "source_page": 1,
            "confidence": 1,
            "extraction_method": "pdf_text",
            "confirmed_by_user": True,
        }
    ]

    res = client.post("/api/completeness/check", json=payload)
    assert res.status_code == 200, res.text
