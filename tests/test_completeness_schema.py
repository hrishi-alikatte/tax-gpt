"""Schema invariants for the completeness contracts."""
from __future__ import annotations

import dataclasses

import pytest
from pydantic import ValidationError

from TaxAI2025.completeness.schema import (
    SEVERITY_RANK,
    CompletenessRule,
    Finding,
)


def _trigger_true(_profile, _facts) -> bool:
    return True


def _trigger_false(_profile, _facts) -> bool:
    return False


def test_completeness_rule_is_frozen() -> None:
    rule = CompletenessRule(
        id="VD-TEST-001",
        title_en="Test rule",
        trigger=_trigger_false,
        missing_message_en="Test message.",
        asks_for=("test.field",),
        source_doc="Vaud 2025 Instructions",
        pdf_page=None,
        source_level="vaud_official",
        severity="likely_missing",
        verification_status="pending",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        rule.id = "MUTATED"  # type: ignore[misc]


def test_completeness_rule_rejects_blank_id() -> None:
    with pytest.raises(ValueError, match="id"):
        CompletenessRule(
            id="",
            title_en="x",
            trigger=_trigger_true,
            missing_message_en="x",
            asks_for=(),
            source_doc="Vaud 2025 Instructions",
            pdf_page=None,
            source_level="vaud_official",
            severity="blocker",
            verification_status="pending",
        )


def test_completeness_rule_rejects_blank_source_doc() -> None:
    with pytest.raises(ValueError, match="source_doc"):
        CompletenessRule(
            id="VD-X-001",
            title_en="x",
            trigger=_trigger_true,
            missing_message_en="x",
            asks_for=(),
            source_doc="",
            pdf_page=1,
            source_level="vaud_official",
            severity="blocker",
            verification_status="pending",
        )


def test_completeness_rule_official_requires_pdf_page() -> None:
    with pytest.raises(ValueError, match="vaud_official"):
        CompletenessRule(
            id="VD-X-001",
            title_en="x",
            trigger=_trigger_true,
            missing_message_en="x",
            asks_for=(),
            source_doc="Vaud 2025 Instructions",
            pdf_page=None,
            source_level="vaud_official",
            severity="blocker",
            verification_status="vaud_official",
        )


def test_completeness_rule_rejects_zero_or_negative_page() -> None:
    with pytest.raises(ValueError, match="pdf_page"):
        CompletenessRule(
            id="VD-X-001",
            title_en="x",
            trigger=_trigger_true,
            missing_message_en="x",
            asks_for=(),
            source_doc="Vaud 2025 Instructions",
            pdf_page=0,
            source_level="vaud_official",
            severity="blocker",
            verification_status="vaud_official",
        )


def test_finding_round_trip() -> None:
    raw = {
        "rule_id": "VD-TEST-001",
        "title_en": "Title",
        "message_en": "Message.",
        "asks_for": ["a.b"],
        "source_doc": "Vaud 2025 Instructions",
        "pdf_page": 42,
        "severity": "blocker",
        "verification_status": "vaud_official",
    }
    finding = Finding(**raw)
    assert finding.model_dump() == raw


def test_finding_pending_citation_token() -> None:
    finding = Finding(
        rule_id="VD-TEST-001",
        title_en="t",
        message_en="m",
        asks_for=[],
        source_doc="Vaud 2025 Instructions",
        pdf_page=None,
        severity="likely_missing",
        verification_status="pending",
    )
    assert finding.citation_token() == "[Vaud 2025 Instructions, page pending verification]"


def test_finding_concrete_citation_token() -> None:
    finding = Finding(
        rule_id="VD-TEST-001",
        title_en="t",
        message_en="m",
        asks_for=[],
        source_doc="Vaud 2025 Instructions",
        pdf_page=12,
        severity="likely_missing",
        verification_status="vaud_official",
    )
    assert finding.citation_token() == "[Vaud 2025 Instructions p.12]"


def test_finding_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        Finding(
            rule_id="VD-TEST-001",
            title_en="t",
            message_en="m",
            asks_for=[],
            source_doc="Vaud 2025 Instructions",
            pdf_page=1,
            severity="critical",  # type: ignore[arg-type]
            verification_status="vaud_official",
        )


def test_finding_rejects_blank_rule_id() -> None:
    with pytest.raises(ValidationError):
        Finding(
            rule_id="",
            title_en="t",
            message_en="m",
            asks_for=[],
            source_doc="Vaud 2025 Instructions",
            pdf_page=1,
            severity="blocker",
            verification_status="vaud_official",
        )


def test_finding_rejects_zero_page() -> None:
    with pytest.raises(ValidationError):
        Finding(
            rule_id="VD-X-001",
            title_en="t",
            message_en="m",
            asks_for=[],
            source_doc="Vaud 2025 Instructions",
            pdf_page=0,
            severity="blocker",
            verification_status="vaud_official",
        )


def test_severity_rank_ordering() -> None:
    assert SEVERITY_RANK["blocker"] < SEVERITY_RANK["likely_missing"]
    assert SEVERITY_RANK["likely_missing"] < SEVERITY_RANK["nice_to_have"]
