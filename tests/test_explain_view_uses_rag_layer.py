"""The explain view's pure helper passes results through unchanged.

We never want a wrapper that bypasses the citation layer (CLAUDE.md §5).
The view's `handle_explain` is intentionally thin: input question →
`answer_with_citations` → outcome. Refused answers must surface their
refusal reason so the UI can render the badge.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from TaxAI2025.rag.schema import GroundedAnswer, RagCitation


def _grounded_ok() -> GroundedAnswer:
    return GroundedAnswer(
        answer_en="Pillar 3a is voluntary [Vaud 2025 Instructions p.42].",
        citations=[
            RagCitation(
                source_id="vd_2025_instructions",
                source_title="Vaud 2025 Instructions",
                pdf_page=42,
                section_title=None,
                chunk_id="c-1",
                token="[Vaud 2025 Instructions p.42]",
            )
        ],
        refused=False,
        retrieval=None,
        generated_at=datetime.utcnow(),
    )


def _grounded_refused() -> GroundedAnswer:
    return GroundedAnswer(
        answer_en=(
            "I cannot answer this from the official Vaud 2025 instructions. "
            "Please consult an accredited fiduciary in Vaud for filing decisions."
        ),
        citations=[],
        refused=True,
        refusal_reason="refusal_by_intent",
        retrieval=None,
        generated_at=datetime.utcnow(),
    )


def test_handle_explain_passes_answer_through_unchanged() -> None:
    from TaxAI2025.ui.views.explain_view import handle_explain

    expected = _grounded_ok()
    outcome = handle_explain("What is Pillar 3a?", lambda _q: expected)

    assert outcome.refused is False
    assert outcome.answer is expected
    assert outcome.refusal_reason is None
    assert outcome.citations[0].token == "[Vaud 2025 Instructions p.42]"


def test_handle_explain_surfaces_refusal_reason_for_ui_badge() -> None:
    from TaxAI2025.ui.views.explain_view import handle_explain

    refused = _grounded_refused()
    outcome = handle_explain("Optimize my tax please", lambda _q: refused)

    assert outcome.refused is True
    assert outcome.refusal_reason == "refusal_by_intent"
    assert outcome.citations == []
    assert "I cannot answer this" in outcome.answer.answer_en


def test_handle_explain_rejects_empty_question() -> None:
    from TaxAI2025.ui.views.explain_view import handle_explain

    with pytest.raises(ValueError):
        handle_explain("   ", lambda _q: _grounded_ok())


def test_handle_explain_strips_question_before_dispatch() -> None:
    from TaxAI2025.ui.views.explain_view import handle_explain

    seen: list[str] = []

    def stub(q: str) -> GroundedAnswer:
        seen.append(q)
        return _grounded_ok()

    handle_explain("   What is Pillar 3a?   ", stub)
    assert seen == ["What is Pillar 3a?"]


def test_handle_explain_uses_real_rag_layer_via_monkeypatch(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The view is wired so that production calls
    `TaxAI2025.rag.explain.answer_with_citations` directly. We monkeypatch
    that symbol and assert the helper round-trips the result.
    """
    from TaxAI2025.rag import explain as explain_module
    from TaxAI2025.ui.views.explain_view import handle_explain

    captured: list[str] = []

    def fake(question: str, retriever=None) -> GroundedAnswer:  # noqa: ARG001
        captured.append(question)
        return _grounded_ok()

    monkeypatch.setattr(explain_module, "answer_with_citations", fake)

    outcome = handle_explain(
        "What is Pillar 3a?", explain_module.answer_with_citations
    )
    assert captured == ["What is Pillar 3a?"]
    assert outcome.refused is False
    assert outcome.citations[0].pdf_page == 42
