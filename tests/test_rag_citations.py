"""Citation/refusal behavior of the RAG explain wrapper."""
from __future__ import annotations

import pytest

from TaxAI2025.rag.schema import RagChunk


class FakeRetriever:
    def __init__(self, chunks: list[RagChunk]):
        self._chunks = chunks

    def retrieve(self, query: str, *, k: int = 4) -> list[RagChunk]:  # noqa: ARG002
        return list(self._chunks)


@pytest.fixture
def known_chunk() -> RagChunk:
    return RagChunk(
        chunk_id="chunk-1",
        source_id="vd_2025_instructions",
        text="Le 3e pilier A permet une déduction annuelle plafonnée pour salariés.",
        pdf_page=42,
        section_title="3e pilier A",
        topic="pillar_3a",
        language="fr",
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
    )


@pytest.fixture
def unknown_page_chunk() -> RagChunk:
    return RagChunk(
        chunk_id="chunk-2",
        source_id="vd_2025_instructions",
        text="Les avoirs au 31 décembre doivent être déclarés.",
        pdf_page=None,
        section_title=None,
        topic="bank_wealth",
        language="fr",
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
    )


def _patch_router(monkeypatch: pytest.MonkeyPatch, returned_text: str) -> list[str]:
    """Monkeypatch model_router.generate_text. Returns capture list of calls."""
    calls: list[str] = []

    def fake_generate_text(messages, purpose, *, temperature=0.0):  # noqa: ANN001, ANN003, ARG001
        calls.append(returned_text)
        return returned_text

    # Patch in both locations to be safe against import order issues
    monkeypatch.setattr("TaxAI2025.ai.model_router.generate_text", fake_generate_text)
    try:
        import TaxAI2025.rag.explain
        monkeypatch.setattr(TaxAI2025.rag.explain.model_router, "generate_text", fake_generate_text)
    except (ImportError, AttributeError):
        pass
    return calls


def test_no_chunks_retrieved_yields_refusal(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_router(monkeypatch, "should not be called")
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What is Pillar 3a?", retriever=FakeRetriever(chunks=[])
    )
    assert result.refused is True
    assert result.refusal_reason == "no_chunks_retrieved"


def test_supported_question_yields_grounded_answer_with_citation(
    azure_and_groq_env: None,
    monkeypatch: pytest.MonkeyPatch,
    known_chunk: RagChunk,
) -> None:
    answer = (
        "Pillar 3a (3e pilier A) is a private pension contribution that is "
        "tax-deductible up to an annual cap [Vaud 2025 Instructions p.42]."
    )
    _patch_router(monkeypatch, answer)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What is Pillar 3a in VaudTax?",
        retriever=FakeRetriever(chunks=[known_chunk]),
    )
    assert result.refused is False
    assert "[Vaud 2025 Instructions p.42]" in result.answer_en
    assert any(c.token == "[Vaud 2025 Instructions p.42]" for c in result.citations)


def test_missing_page_yields_pending_verification_token(
    azure_and_groq_env: None,
    monkeypatch: pytest.MonkeyPatch,
    unknown_page_chunk: RagChunk,
) -> None:
    answer = (
        "Year-end bank balances are part of the wealth declaration "
        "[Vaud 2025 Instructions, page pending verification]."
    )
    _patch_router(monkeypatch, answer)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "Why do you ask for bank balances at year end?",
        retriever=FakeRetriever(chunks=[unknown_page_chunk]),
    )
    assert result.refused is False
    assert "[Vaud 2025 Instructions, page pending verification]" in result.answer_en
    assert all(
        c.token == "[Vaud 2025 Instructions, page pending verification]"
        for c in result.citations
    )


def test_unsupported_advice_intent_is_refused_without_retrieval(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _patch_router(monkeypatch, "should not be called")
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations("Optimize my taxes")
    assert result.refused is True
    assert result.refusal_reason == "refusal_by_intent"
    assert calls == []  # router never invoked


def test_fabricated_page_token_is_rejected_then_refused(
    azure_and_groq_env: None,
    monkeypatch: pytest.MonkeyPatch,
    known_chunk: RagChunk,
) -> None:
    """Model returns a fake page (p.999); after one regen also fake; refuse."""
    bad = "Made-up answer [Vaud 2025 Instructions p.999]."
    _patch_router(monkeypatch, bad)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What is Pillar 3a?", retriever=FakeRetriever(chunks=[known_chunk])
    )
    assert result.refused is True
    assert result.refusal_reason == "citation_validation_failed"


def test_answer_without_citation_is_refused(
    azure_and_groq_env: None,
    monkeypatch: pytest.MonkeyPatch,
    known_chunk: RagChunk,
) -> None:
    _patch_router(monkeypatch, "Pillar 3a is something something.")
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What is Pillar 3a?", retriever=FakeRetriever(chunks=[known_chunk])
    )
    assert result.refused is True
    assert result.refusal_reason == "citation_validation_failed"


def test_mixed_valid_and_fabricated_tokens_are_rejected(
    azure_and_groq_env: None,
    monkeypatch: pytest.MonkeyPatch,
    known_chunk: RagChunk,
) -> None:
    """If ANY token is not in the allowed set, the answer is rejected even if a valid token is present."""
    answer = (
        "Pillar 3a is deductible up to a cap "
        "[Vaud 2025 Instructions p.42] but also see "
        "[Vaud 2025 Instructions p.999] for edge cases."
    )
    _patch_router(monkeypatch, answer)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What is Pillar 3a?", retriever=FakeRetriever(chunks=[known_chunk])
    )
    assert result.refused is True
    assert result.refusal_reason == "citation_validation_failed"


def test_chunk_from_inactive_source_is_dropped(
    azure_and_groq_env: None,
    monkeypatch: pytest.MonkeyPatch,
    known_chunk: RagChunk,
) -> None:
    """A 2024 chunk must not become a citation in a 2025 answer."""
    historical = RagChunk(
        chunk_id="chunk-2024",
        source_id="vd_2024_instructions",  # NOT in all_active_sources()
        text="Anciennes règles 2024.",
        pdf_page=10,
        topic="pillar_3a",
        language="fr",
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
    )
    answer = "Pillar 3a deductible cap [Vaud 2025 Instructions p.42]."
    _patch_router(monkeypatch, answer)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What is Pillar 3a?",
        retriever=FakeRetriever(chunks=[historical, known_chunk]),
    )
    assert result.refused is False
    # Only the active-source chunk produced a citation.
    assert len(result.citations) == 1
    assert result.citations[0].source_id == "vd_2025_instructions"


def test_only_inactive_source_chunks_yields_refusal(
    azure_and_groq_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If every retrieved chunk is from a non-active source, refuse with the dedicated reason."""
    historical_only = RagChunk(
        chunk_id="chunk-2024",
        source_id="vd_2024_instructions",
        text="Anciennes règles 2024.",
        pdf_page=10,
        topic="pillar_3a",
        language="fr",
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
    )
    _patch_router(monkeypatch, "should not be called")
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What is Pillar 3a?", retriever=FakeRetriever(chunks=[historical_only])
    )
    assert result.refused is True
    assert result.refusal_reason == "no_active_source_chunks"


def test_model_name_populated_on_grounded_answer(
    azure_and_groq_env: None,
    monkeypatch: pytest.MonkeyPatch,
    known_chunk: RagChunk,
) -> None:
    """Grounded answers must carry model identity for audit-log provenance."""
    answer = "Pillar 3a [Vaud 2025 Instructions p.42]."
    _patch_router(monkeypatch, answer)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What is Pillar 3a?", retriever=FakeRetriever(chunks=[known_chunk])
    )
    assert result.refused is False
    assert result.model_name is not None
    assert "azure" in result.model_name
    assert "rag" in result.model_name  # deployment name from conftest


def test_self_employed_question_is_refused_by_intent(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Out-of-permit-fence question refuses without retrieval."""
    calls = _patch_router(monkeypatch, "should not be called")
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations("How do self-employed people deduct expenses?")
    assert result.refused is True
    assert result.refusal_reason == "refusal_by_intent"
    assert calls == []


def test_other_canton_question_is_refused_by_intent(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _patch_router(monkeypatch, "should not be called")
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations("What's the deduction in Geneva?")
    assert result.refused is True
    assert result.refusal_reason == "refusal_by_intent"
    assert calls == []
