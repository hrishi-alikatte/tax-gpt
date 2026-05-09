"""Ingest pipeline tests. NO live network.

Embedder + chromadb client are injected so tests never touch the network or
the filesystem beyond `tmp_path`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from TaxAI2025.rag import embedding_config


def _stub_embedder(texts):
    """Deterministic 3072-dim vectors keyed by index."""
    items = list(texts)
    return [
        [float(i) / 1000.0] * embedding_config.PRIMARY_DIMENSIONS
        for i, _ in enumerate(items)
    ]


def _make_fake_client_factory():
    """Return (factory, client_mock, collection_mock).

    factory(index_dir) -> client. delete_collection raises (simulating first
    build); create_collection returns the collection.
    """
    client = MagicMock()
    coll = MagicMock()
    client.create_collection.return_value = coll
    client.delete_collection.side_effect = Exception("not found")

    def factory(index_dir: Path) -> Any:
        index_dir.mkdir(parents=True, exist_ok=True)
        return client

    return factory, client, coll


def _patch_active_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Replace `sources.active_source()` with a fake source whose local_path is a writable file."""
    fake_pdf = tmp_path / "vd_2025.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\n%fake\n")

    from TaxAI2025.rag import sources
    from TaxAI2025.rag.schema import RagSource

    fake_source = RagSource(
        source_id="vd_2025_instructions",
        title="Instructions générales 2025 (Canton de Vaud)",
        authority="official_canton",
        authority_rank=1,
        canton="VD",
        tax_year=2025,
        language="fr",
        url=None,
        local_path=str(fake_pdf),
        source_hash="deadbeef" * 8,
        source_type="pdf",
        allowed_use=[],
        forbidden_use=[],
    )

    sources.active_source.cache_clear()  # type: ignore[attr-defined]
    monkeypatch.setattr(sources, "active_source", lambda: fake_source)


def test_ingest_writes_index_stamp_and_returns_built(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_active_source(monkeypatch, tmp_path)

    from TaxAI2025.rag import ingest

    monkeypatch.setattr(
        ingest,
        "_load_pages",
        lambda p: iter(
            [
                (1, "Le 3e pilier A permet une déduction annuelle plafonnée. Code 320."),
                (2, "Les avoirs au 31 décembre doivent être déclarés."),
            ]
        ),
    )
    factory, _client, _coll = _make_fake_client_factory()
    index_dir = tmp_path / "idx"

    result = ingest.build_index(
        force_rebuild=True,
        index_dir=index_dir,
        embedder=_stub_embedder,
        chroma_client_factory=factory,
    )

    assert result["status"] == "built"
    assert result["chunk_count"] >= 2
    stamp = embedding_config.read_stamp(index_dir)
    assert stamp is not None
    assert stamp.embedding_model == "text-embedding-3-large"
    assert stamp.embedding_dimensions == 3072
    assert stamp.source_id == "vd_2025_instructions"
    assert stamp.tax_year == 2025
    assert stamp.canton == "VD"


def test_ingest_chunks_carry_all_required_metadata_keys(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_active_source(monkeypatch, tmp_path)
    from TaxAI2025.rag import ingest

    monkeypatch.setattr(
        ingest,
        "_load_pages",
        lambda p: iter([(7, "Some Vaud rubric text. Code 100 explanation.")]),
    )
    factory, _client, coll = _make_fake_client_factory()

    ingest.build_index(
        force_rebuild=True,
        index_dir=tmp_path / "idx",
        embedder=_stub_embedder,
        chroma_client_factory=factory,
    )

    assert coll.add.called
    metas = coll.add.call_args.kwargs["metadatas"]
    required = set(embedding_config.required_chunk_metadata_keys())
    assert metas, "expected at least one chunk metadata"
    for m in metas:
        assert required.issubset(m.keys()), f"missing: {required - set(m.keys())}"


def test_ingest_pdf_pages_are_one_indexed(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_active_source(monkeypatch, tmp_path)
    from TaxAI2025.rag import ingest

    monkeypatch.setattr(
        ingest,
        "_load_pages",
        lambda p: iter([(1, "Page one text."), (42, "Page forty-two text.")]),
    )
    factory, _client, coll = _make_fake_client_factory()

    ingest.build_index(
        force_rebuild=True,
        index_dir=tmp_path / "idx",
        embedder=_stub_embedder,
        chroma_client_factory=factory,
    )

    metas = coll.add.call_args.kwargs["metadatas"]
    pages = {m["pdf_page"] for m in metas}
    assert 0 not in pages, "pages must be 1-indexed"
    assert pages.issubset({1, 42})


def test_ingest_rejects_chunk_with_pdf_page_none(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Per RAG_CORPUS.md §6: pdf_page None at ingest is a bug."""
    _patch_active_source(monkeypatch, tmp_path)
    from TaxAI2025.rag import ingest

    monkeypatch.setattr(
        ingest,
        "_chunk_metadata",
        lambda **kwargs: {
            **{
                k: ""
                for k in embedding_config.required_chunk_metadata_keys()
            },
            "pdf_page": None,
            "embedding_dimensions": 3072,
            "tax_year": 2025,
        },
    )
    monkeypatch.setattr(
        ingest, "_load_pages", lambda p: iter([(1, "text")])
    )
    factory, _client, _coll = _make_fake_client_factory()

    with pytest.raises(RuntimeError, match="pdf_page"):
        ingest.build_index(
            force_rebuild=True,
            index_dir=tmp_path / "idx",
            embedder=_stub_embedder,
            chroma_client_factory=factory,
        )


def test_ingest_skips_when_compatible_stamp_exists(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_active_source(monkeypatch, tmp_path)
    from TaxAI2025.rag import ingest, sources

    source = sources.active_source()
    expected = ingest._expected_stamp(source)
    index_dir = tmp_path / "idx"
    embedding_config.write_stamp(index_dir, expected)

    factory, _client, _coll = _make_fake_client_factory()

    embedder_calls: list[Any] = []

    def tracking_embedder(texts):
        embedder_calls.append(list(texts))
        return _stub_embedder(texts)

    result = ingest.build_index(
        force_rebuild=False,
        index_dir=index_dir,
        embedder=tracking_embedder,
        chroma_client_factory=factory,
    )

    assert result["status"] == "skipped"
    assert embedder_calls == []  # never embedded


def test_ingest_force_rebuild_overrides_existing_stamp(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_active_source(monkeypatch, tmp_path)
    from TaxAI2025.rag import ingest, sources

    source = sources.active_source()
    expected = ingest._expected_stamp(source)
    index_dir = tmp_path / "idx"
    embedding_config.write_stamp(index_dir, expected)

    monkeypatch.setattr(
        ingest, "_load_pages", lambda p: iter([(1, "text one")])
    )
    factory, _client, coll = _make_fake_client_factory()

    result = ingest.build_index(
        force_rebuild=True,
        index_dir=index_dir,
        embedder=_stub_embedder,
        chroma_client_factory=factory,
    )

    assert result["status"] == "built"
    assert coll.add.called


def test_ingest_embeds_in_batches(
    azure_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Embedder is called in batches of <= EMBED_BATCH_SIZE."""
    _patch_active_source(monkeypatch, tmp_path)
    from TaxAI2025.rag import ingest

    # Force ~50 chunks via long text + small chunk size effect: simpler to
    # stub the splitter to yield N pieces.
    monkeypatch.setattr(
        ingest, "_load_pages", lambda p: iter([(1, "x")])
    )

    class FakeSplitter:
        def split_text(self, _t):
            return [f"piece-{i}" for i in range(50)]

    monkeypatch.setattr(ingest, "_splitter", lambda: FakeSplitter())

    batch_sizes: list[int] = []

    def tracking_embedder(texts):
        items = list(texts)
        batch_sizes.append(len(items))
        return _stub_embedder(items)

    factory, _client, _coll = _make_fake_client_factory()

    ingest.build_index(
        force_rebuild=True,
        index_dir=tmp_path / "idx",
        embedder=tracking_embedder,
        chroma_client_factory=factory,
    )

    assert batch_sizes, "embedder must be invoked"
    assert all(size <= ingest.EMBED_BATCH_SIZE for size in batch_sizes)
    assert sum(batch_sizes) == 50
