"""Embedding-config tests: dimensions, forbidden models, stale-index refusal."""
from __future__ import annotations

from pathlib import Path

import pytest

from TaxAI2025.rag import embedding_config as ec


def test_primary_model_and_dimensions() -> None:
    assert ec.PRIMARY_EMBEDDING_MODEL == "text-embedding-3-large"
    assert ec.PRIMARY_DIMENSIONS == 3072
    assert ec.SIMILARITY == "cosine"


def test_ada_002_is_forbidden() -> None:
    with pytest.raises(ValueError):
        ec.assert_model_allowed("text-embedding-ada-002")


def test_required_chunk_metadata_keys_includes_provenance() -> None:
    keys = ec.required_chunk_metadata_keys()
    for required in (
        "embedding_model",
        "embedding_dimensions",
        "source_id",
        "source_hash",
        "tax_year",
        "canton",
        "pdf_page",
        "printed_page",
        "language",
    ):
        assert required in keys


def test_index_stamp_round_trip(tmp_path: Path) -> None:
    stamp = ec.IndexStamp(
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
        similarity="cosine",
        source_id="vd_2025_instructions",
        source_hash="abc123",
        tax_year=2025,
        canton="VD",
    )
    ec.write_stamp(tmp_path, stamp)
    loaded = ec.read_stamp(tmp_path)
    assert loaded == stamp
    assert ec.index_is_compatible(tmp_path, stamp) is True


def test_index_stamp_mismatch_blocks_reuse(tmp_path: Path) -> None:
    old = ec.IndexStamp(
        embedding_model="paraphrase-multilingual-MiniLM-L12-v2",
        embedding_dimensions=384,
        similarity="cosine",
        source_id="vd_2024_instructions",
        source_hash="oldhash",
        tax_year=2024,
        canton="VD",
    )
    ec.write_stamp(tmp_path, old)

    expected = ec.IndexStamp(
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
        similarity="cosine",
        source_id="vd_2025_instructions",
        source_hash="newhash",
        tax_year=2025,
        canton="VD",
    )
    assert ec.index_is_compatible(tmp_path, expected) is False


def test_missing_stamp_blocks_reuse(tmp_path: Path) -> None:
    expected = ec.IndexStamp(
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
        similarity="cosine",
        source_id="vd_2025_instructions",
        source_hash="x",
        tax_year=2025,
        canton="VD",
    )
    assert ec.read_stamp(tmp_path) is None
    assert ec.index_is_compatible(tmp_path, expected) is False
