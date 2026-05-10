"""Tests for the RAG replay mode (DEMO_MODE=replay)."""
from __future__ import annotations

import pytest
from TaxAI2025.core import config
from TaxAI2025.rag.explain import answer_with_citations


def test_rag_replay_returns_canned_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "replay")
    monkeypatch.setenv("DEMO_SCENARIO", "expat_c_permit_basic")
    
    # This matches the hash a5183878759c
    question = "What is Pillar 3a in VaudTax?"
    
    result = answer_with_citations(question)
    
    assert result.refused is False
    assert "Pillar 3a (3e pilier A)" in result.answer_en
    assert result.model_name == "replay:fixture"
    assert len(result.citations) == 1
    assert result.citations[0].pdf_page == 42


def test_rag_replay_refuses_unknown_question(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "replay")
    monkeypatch.setenv("DEMO_SCENARIO", "expat_c_permit_basic")
    
    # A question we don't have a fixture for
    question = "How much can I deduct for my cat?"
    
    result = answer_with_citations(question)
    
    # It should refuse since no fixture exists for this question.
    assert result.refused is True
    assert result.refusal_reason == "no_replay_fixture_found"
