"""Embedding model configuration for the active RAG corpus.

A change to embedding model, dimensions, source hash, or tax year MUST force
the index to be rebuilt. The index dir is stamped with these values; the
loader refuses to use a directory whose stamp does not match.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from TaxAI2025.core import config

PRIMARY_EMBEDDING_MODEL = "text-embedding-3-large"
PRIMARY_DIMENSIONS = 3072
FALLBACK_EMBEDDING_MODEL = "text-embedding-3-small"
FALLBACK_DIMENSIONS = 1536
SIMILARITY: Literal["cosine"] = "cosine"

# DO NOT add `text-embedding-ada-002`. Forbidden by product spec.
FORBIDDEN_EMBEDDING_MODELS = {"text-embedding-ada-002"}

INDEX_STAMP_FILENAME = "_vaudtax_index_stamp.json"


@dataclass(frozen=True)
class IndexStamp:
    """Identity of an embedded index. Mismatch => rebuild required."""

    embedding_model: str
    embedding_dimensions: int
    similarity: str
    source_id: str
    source_hash: str
    tax_year: int
    canton: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def stamp_path(index_dir: Path) -> Path:
    return index_dir / INDEX_STAMP_FILENAME


def write_stamp(index_dir: Path, stamp: IndexStamp) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    stamp_path(index_dir).write_text(stamp.to_json(), encoding="utf-8")


def read_stamp(index_dir: Path) -> IndexStamp | None:
    p = stamp_path(index_dir)
    if not p.is_file():
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    return IndexStamp(**raw)


def index_is_compatible(index_dir: Path, expected: IndexStamp) -> bool:
    actual = read_stamp(index_dir)
    return actual == expected


def required_chunk_metadata_keys() -> tuple[str, ...]:
    """Mandatory metadata keys on every embedded chunk."""
    return (
        "embedding_model",
        "embedding_dimensions",
        "source_id",
        "source_title",
        "source_url",
        "source_hash",
        "tax_year",
        "canton",
        "language",
        "pdf_page",
        "printed_page",
        "section_title",
        "vaud_codes",
        "topic",
    )


def assert_model_allowed(model: str) -> None:
    if model in FORBIDDEN_EMBEDDING_MODELS:
        raise ValueError(
            f"Embedding model '{model}' is forbidden by product policy. "
            f"Use '{PRIMARY_EMBEDDING_MODEL}'."
        )


def expected_dimensions_for(model: str) -> int:
    if model == PRIMARY_EMBEDDING_MODEL:
        return PRIMARY_DIMENSIONS
    if model == FALLBACK_EMBEDDING_MODEL:
        return FALLBACK_DIMENSIONS
    # Unknown model => trust env-provided dimensions
    return config.azure_config().embedding_dimensions
