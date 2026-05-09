"""Golden retrieval tests — RAG_CORPUS.md §13.

Five canonical questions form the M1 RAG acceptance bar:

  Q1 Pillar 3a              -> grounded, cited
  Q2 Salary certificate     -> grounded, cited
  Q3 Bank balances year-end -> grounded, cited
  Q4 C-permit ordinary tax  -> grounded, cited
  Q5 "Optimize my taxes"    -> refused by intent (no retrieval)

NO live network. Retriever + generator + active source are all stubbed.
"""
from __future__ import annotations

import pytest

from TaxAI2025.rag.schema import RagChunk


class FakeRetriever:
    def __init__(self, chunks: list[RagChunk]) -> None:
        self._chunks = chunks
        self.calls: list[str] = []

    def retrieve(self, query: str, *, k: int = 4) -> list[RagChunk]:  # noqa: ARG002
        self.calls.append(query)
        return list(self._chunks)


def _patch_router(monkeypatch: pytest.MonkeyPatch, returned_text: str) -> list[str]:
    calls: list[str] = []

    def fake_generate_text(messages, purpose, *, temperature=0.0):  # noqa: ANN001, ANN003, ARG001
        calls.append(returned_text)
        return returned_text

    from TaxAI2025.ai import model_router

    monkeypatch.setattr(model_router, "generate_text", fake_generate_text)
    return calls


def _chunk(
    *,
    chunk_id: str,
    text: str,
    pdf_page: int,
    section: str,
    topic: str,
    source_id: str = "vd_2025_instructions",
) -> RagChunk:
    return RagChunk(
        chunk_id=chunk_id,
        source_id=source_id,
        text=text,
        pdf_page=pdf_page,
        section_title=section,
        topic=topic,
        language="fr",
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
    )


# ---------------------------------------------------------------------------
# Q1 — Pillar 3a
# ---------------------------------------------------------------------------


def test_golden_q1_pillar_3a_grounded_with_citation(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunk = _chunk(
        chunk_id="q1-3a",
        text="Le 3e pilier A (3a) permet une déduction annuelle plafonnée pour les salariés.",
        pdf_page=42,
        section="3e pilier A",
        topic="pillar_3a",
    )
    answer = (
        "Pillar 3a (3e pilier A) is a private pension contribution that reduces "
        "your taxable income up to an annual cap [Vaud 2025 Instructions p.42]."
    )
    _patch_router(monkeypatch, answer)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What is Pillar 3a in VaudTax?",
        retriever=FakeRetriever([chunk]),
    )

    assert result.refused is False
    assert "[Vaud 2025 Instructions p.42]" in result.answer_en
    assert any(c.token == "[Vaud 2025 Instructions p.42]" for c in result.citations)


# ---------------------------------------------------------------------------
# Q2 — Salary certificate
# ---------------------------------------------------------------------------


def test_golden_q2_salary_certificate_grounded_with_citation(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunk = _chunk(
        chunk_id="q2-cs",
        text="Le certificat de salaire récapitule le revenu d'activité dépendante.",
        pdf_page=11,
        section="Certificat de salaire",
        topic="salary_certificate",
    )
    answer = (
        "The salary certificate (certificat de salaire) reports your employment "
        "income for the year [Vaud 2025 Instructions p.11]."
    )
    _patch_router(monkeypatch, answer)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "Why do I need a salary certificate?",
        retriever=FakeRetriever([chunk]),
    )

    assert result.refused is False
    assert "[Vaud 2025 Instructions p.11]" in result.answer_en


# ---------------------------------------------------------------------------
# Q3 — Bank balances at year end
# ---------------------------------------------------------------------------


def test_golden_q3_bank_balances_grounded_with_citation(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunk = _chunk(
        chunk_id="q3-wealth",
        text="Les avoirs au 31 décembre doivent être déclarés (état de la fortune).",
        pdf_page=23,
        section="État de la fortune",
        topic="bank_wealth",
    )
    answer = (
        "Year-end bank balances form part of the wealth declaration (état de "
        "la fortune) for tax year 2025 [Vaud 2025 Instructions p.23]."
    )
    _patch_router(monkeypatch, answer)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "Why do you ask for bank balances at year end?",
        retriever=FakeRetriever([chunk]),
    )

    assert result.refused is False
    assert "[Vaud 2025 Instructions p.23]" in result.answer_en


# ---------------------------------------------------------------------------
# Q4 — C-permit ordinary taxation
# ---------------------------------------------------------------------------


def test_golden_q4_c_permit_ordinary_taxation_grounded_with_citation(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunk = _chunk(
        chunk_id="q4-ord",
        text="Les titulaires d'un permis C sont soumis à l'imposition ordinaire.",
        pdf_page=5,
        section="Imposition ordinaire",
        topic="ordinary_taxation_c_permit",
    )
    answer = (
        "C-permit holders are subject to ordinary taxation (imposition ordinaire) "
        "in Canton de Vaud [Vaud 2025 Instructions p.5]."
    )
    _patch_router(monkeypatch, answer)
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations(
        "What does ordinary taxation mean for a C-permit employee?",
        retriever=FakeRetriever([chunk]),
    )

    assert result.refused is False
    assert "[Vaud 2025 Instructions p.5]" in result.answer_en


# ---------------------------------------------------------------------------
# Q5 — Optimize my taxes => refusal by intent (no retrieval)
# ---------------------------------------------------------------------------


def test_golden_q5_optimize_taxes_is_refused_by_intent(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    router_calls = _patch_router(monkeypatch, "should not be called")

    retriever = FakeRetriever(
        [
            _chunk(
                chunk_id="q5-noise",
                text="…",
                pdf_page=1,
                section="…",
                topic="…",
            )
        ]
    )
    from TaxAI2025.rag.explain import answer_with_citations

    result = answer_with_citations("Optimize my taxes.", retriever=retriever)

    assert result.refused is True
    assert result.refusal_reason == "refusal_by_intent"
    assert retriever.calls == []  # no retrieval performed
    assert router_calls == []  # no model invocation
