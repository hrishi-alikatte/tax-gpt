"""Retriever tests. NO live network. Fake collection injected directly.

Verifies:
  - reconstructed RagChunk carries provenance fields
  - 1-indexed pdf_page round-trips
  - chunks from a non-active source (e.g. vd_2024_instructions) are dropped
  - chromadb is NOT imported at retriever import time
"""
from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest


def _full_meta(*, source_id: str, pdf_page: int, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "embedding_model": "text-embedding-3-large",
        "embedding_dimensions": 3072,
        "source_id": source_id,
        "source_title": "Instructions générales 2025 (Canton de Vaud)",
        "source_url": "",
        "source_hash": "abc",
        "tax_year": 2025,
        "canton": "VD",
        "language": "fr",
        "pdf_page": pdf_page,
        "printed_page": "",
        "section_title": "3e pilier A",
        "vaud_codes": "320",
        "topic": "pillar_3a",
    }
    base.update(overrides)
    return base


def _stub_embedder(texts):
    return [[0.0] * 3072 for _ in list(texts)]


def test_retriever_reconstructs_required_provenance_fields(
    azure_env: None,
) -> None:
    fake_coll = MagicMock()
    fake_coll.query.return_value = {
        "ids": [["chunk-1"]],
        "documents": [["Le 3e pilier A permet une déduction."]],
        "metadatas": [[_full_meta(source_id="vd_2025_instructions", pdf_page=42)]],
    }

    from TaxAI2025.rag.retriever import ChromaRetriever

    r = ChromaRetriever(embedder=_stub_embedder, collection=fake_coll)
    chunks = r.retrieve("Pillar 3a", k=4)

    assert len(chunks) == 1
    c = chunks[0]
    assert c.chunk_id == "chunk-1"
    assert c.source_id == "vd_2025_instructions"
    assert c.pdf_page == 42
    assert c.embedding_model == "text-embedding-3-large"
    assert c.embedding_dimensions == 3072
    assert "320" in c.vaud_codes
    assert c.topic == "pillar_3a"
    assert c.section_title == "3e pilier A"


def test_retriever_drops_inactive_source_chunks(azure_env: None) -> None:
    """A 2024 chunk leaks into the result; the retriever must drop it before
    the explain wrapper ever sees it."""
    fake_coll = MagicMock()
    fake_coll.query.return_value = {
        "ids": [["chunk-2025", "chunk-2024"]],
        "documents": [["text 2025", "text 2024"]],
        "metadatas": [
            [
                _full_meta(source_id="vd_2025_instructions", pdf_page=42),
                _full_meta(source_id="vd_2024_instructions", pdf_page=10),
            ]
        ],
    }

    from TaxAI2025.rag.retriever import ChromaRetriever

    r = ChromaRetriever(embedder=_stub_embedder, collection=fake_coll)
    chunks = r.retrieve("Pillar 3a", k=4)

    assert len(chunks) == 1
    assert chunks[0].source_id == "vd_2025_instructions"


def test_retriever_handles_empty_query_result(azure_env: None) -> None:
    fake_coll = MagicMock()
    fake_coll.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
    }

    from TaxAI2025.rag.retriever import ChromaRetriever

    r = ChromaRetriever(embedder=_stub_embedder, collection=fake_coll)
    assert r.retrieve("anything", k=4) == []


def test_retriever_blank_string_metadata_reconstructs_to_none(
    azure_env: None,
) -> None:
    """Chroma stores '' for unknown optional strings; retriever reconstructs None."""
    fake_coll = MagicMock()
    fake_coll.query.return_value = {
        "ids": [["chunk-1"]],
        "documents": [["text"]],
        "metadatas": [
            [
                _full_meta(
                    source_id="vd_2025_instructions",
                    pdf_page=5,
                    printed_page="",
                    section_title="",
                    vaud_codes="",
                    topic="",
                )
            ]
        ],
    }

    from TaxAI2025.rag.retriever import ChromaRetriever

    r = ChromaRetriever(embedder=_stub_embedder, collection=fake_coll)
    chunks = r.retrieve("anything", k=4)

    assert len(chunks) == 1
    c = chunks[0]
    assert c.printed_page is None
    assert c.section_title is None
    assert c.topic is None
    assert c.vaud_codes == []


def test_retriever_module_does_not_import_chromadb_at_load(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mirror of test_no_model_call_at_import_time: chromadb must be lazy."""
    sys.modules.pop("chromadb", None)
    sys.modules.pop("TaxAI2025.rag.retriever", None)

    import TaxAI2025.rag.retriever  # noqa: F401

    assert "chromadb" not in sys.modules


def test_get_default_retriever_returns_none_when_index_missing(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """No stamp at the configured index_dir => None (caller falls back to refusal)."""
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "definitely-missing"))

    import importlib

    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)

    from TaxAI2025.rag.retriever import get_default_retriever

    assert get_default_retriever() is None


def test_get_default_retriever_lazy_builds_index_when_enabled(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Production containers can build the ephemeral Chroma index on first use."""
    from TaxAI2025.rag import ingest
    from TaxAI2025.rag import retriever as retriever_module

    index_dir = tmp_path / "rag-index"
    checks = iter([False, True])
    built: list[str] = []

    monkeypatch.setattr(retriever_module.config, "rag_index_dir", lambda: index_dir)
    monkeypatch.setattr(retriever_module.config, "rag_auto_build_index", lambda: True)
    monkeypatch.setattr(
        retriever_module,
        "index_is_compatible",
        lambda _index_dir, _stamp: next(checks),
    )

    def fake_build_index(*, force_rebuild, index_dir, **_kwargs):  # noqa: ANN001
        built.append(f"{force_rebuild}:{index_dir}")
        return {"status": "built"}

    monkeypatch.setattr(ingest, "build_index", fake_build_index)

    retriever = retriever_module.get_default_retriever()

    assert retriever is not None
    assert built == [f"False:{index_dir}"]
