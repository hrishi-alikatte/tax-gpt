"""TaxFact schema invariants. NO live network."""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from TaxAI2025.core.tax_facts import TaxFact, validate_provenance


def _valid_fact(**overrides) -> TaxFact:
    base = dict(
        canonical_field="salary.gross_annual_chf",
        value=120000.0,
        source_doc="synthetic_certificat.pdf",
        source_page=1,
        confidence=1.0,
        extraction_method="regex",
        model_name=None,
    )
    base.update(overrides)
    return TaxFact(**base)


def test_round_trip_via_model_dump_and_revalidate() -> None:
    fact = _valid_fact()
    dumped = fact.model_dump()
    again = TaxFact(**dumped)
    assert again == fact


def test_confirmed_by_user_defaults_to_false() -> None:
    fact = _valid_fact()
    assert fact.confirmed_by_user is False


def test_negative_source_page_rejected() -> None:
    with pytest.raises(ValidationError):
        _valid_fact(source_page=0)
    with pytest.raises(ValidationError):
        _valid_fact(source_page=-3)


def test_empty_source_doc_rejected() -> None:
    with pytest.raises(ValidationError):
        _valid_fact(source_doc="")
    with pytest.raises(ValidationError):
        _valid_fact(source_doc="   ")


def test_confidence_must_be_in_unit_interval() -> None:
    with pytest.raises(ValidationError):
        _valid_fact(confidence=1.01)
    with pytest.raises(ValidationError):
        _valid_fact(confidence=-0.01)


def test_extraction_method_literal_enforced() -> None:
    with pytest.raises(ValidationError):
        _valid_fact(extraction_method="guess")  # type: ignore[arg-type]


def test_extracted_at_defaults_to_utc_now() -> None:
    before = datetime.utcnow()
    fact = _valid_fact()
    after = datetime.utcnow()
    assert before <= fact.extracted_at <= after


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        TaxFact(  # type: ignore[call-arg]
            canonical_field="x.y",
            value=1,
            source_doc="d.pdf",
            source_page=1,
            extraction_method="regex",
            unknown_extra_field=True,
        )


def test_validate_provenance_passes_for_valid_fact() -> None:
    validate_provenance(_valid_fact())  # no raise


def test_canonical_field_must_be_nonempty() -> None:
    with pytest.raises(ValidationError):
        _valid_fact(canonical_field="")
