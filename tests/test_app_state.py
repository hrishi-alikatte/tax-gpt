"""AppState invariants — the confirmation gate is sacred."""
from __future__ import annotations

from datetime import datetime

import pytest

from TaxAI2025.core.documents import DocumentRecord
from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.ui.state import AppState, AuditEntry, UserProfile


def _doc(filename: str = "salary.pdf", document_type: str = "salary_certificate") -> DocumentRecord:
    return DocumentRecord(
        doc_id="d-1",
        filename=filename,
        file_path=f"<test>/{filename}",
        document_type=document_type,  # type: ignore[arg-type]
        classifier_confidence=0.95,
        classifier_method="heuristic",
        pdf_page_count=1,
    )


def _fact(field: str, source_doc: str = "salary.pdf", value: float = 100.0) -> TaxFact:
    return TaxFact(
        canonical_field=field,
        value=value,
        source_doc=source_doc,
        source_page=1,
        confidence=0.9,
        extraction_method="regex",
    )


def test_set_profile_appends_audit_entry() -> None:
    state = AppState()
    profile = UserProfile(first_name="Sarah", marital_status="married")
    state.set_profile(profile)
    assert state.profile is profile
    assert state.audit_log[-1].event_type == "profile_saved"
    assert state.audit_log[-1].payload["first_name"] == "Sarah"


def test_add_document_refuses_pre_confirmed_facts() -> None:
    state = AppState()
    record = _doc()
    bad = _fact("salary.gross_annual_chf").model_copy(update={"confirmed_by_user": True})
    with pytest.raises(ValueError, match="pre-confirmed"):
        state.add_document(record, [bad])


def test_add_document_appends_facts_and_audit_entry() -> None:
    state = AppState()
    record = _doc()
    state.add_document(record, [
        _fact("salary.gross_annual_chf"),
        _fact("salary.net_annual_chf"),
    ])
    assert len(state.documents) == 1
    assert len(state.facts) == 2
    assert state.audit_log[-1].event_type == "document_uploaded"


def test_confirm_fact_only_toggles_matching_field() -> None:
    state = AppState()
    state.add_document(_doc(), [
        _fact("salary.gross_annual_chf"),
        _fact("salary.net_annual_chf"),
    ])
    assert state.confirm_fact("salary.gross_annual_chf") is True
    assert state.confirm_fact("does.not.exist") is False
    confirmed = {f.canonical_field for f in state.facts if f.confirmed_by_user}
    assert confirmed == {"salary.gross_annual_chf"}
    assert state.audit_log[-1].event_type == "fact_confirmed"


def test_unconfirm_fact_flips_back() -> None:
    state = AppState()
    state.add_document(_doc(), [_fact("salary.gross_annual_chf")])
    state.confirm_fact("salary.gross_annual_chf")
    assert state.unconfirm_fact("salary.gross_annual_chf") is True
    assert state.facts[0].confirmed_by_user is False
    assert state.audit_log[-1].event_type == "fact_unconfirmed"


def test_is_extracted_complete_requires_every_required_field() -> None:
    state = AppState()
    state.add_document(_doc(), [
        _fact("salary.gross_annual_chf"),
        _fact("salary.net_annual_chf"),
    ])
    assert state.is_extracted_complete() is False
    state.confirm_fact("salary.gross_annual_chf")
    assert state.is_extracted_complete() is False
    state.confirm_fact("salary.net_annual_chf")
    assert state.is_extracted_complete() is True


def test_required_fields_for_doc_type_uses_known_map() -> None:
    state = AppState()
    assert "salary.gross_annual_chf" in state.required_fields_for_doc_type("salary_certificate")
    assert state.required_fields_for_doc_type("unknown") == ()


def test_confirmed_facts_returns_only_confirmed() -> None:
    state = AppState()
    state.add_document(_doc(), [
        _fact("salary.gross_annual_chf"),
        _fact("salary.net_annual_chf"),
    ])
    state.confirm_fact("salary.gross_annual_chf")
    confirmed = state.confirmed_facts()
    assert len(confirmed) == 1
    assert confirmed[0].canonical_field == "salary.gross_annual_chf"


def test_audit_entry_has_required_keys() -> None:
    state = AppState()
    state.record("explain_asked", question="hello")
    entry = state.audit_log[-1]
    assert isinstance(entry, AuditEntry)
    assert isinstance(entry.timestamp, datetime)
    assert entry.event_type == "explain_asked"
    assert entry.payload == {"question": "hello"}


def test_is_extracted_complete_false_when_no_facts() -> None:
    state = AppState()
    assert state.is_extracted_complete() is False
