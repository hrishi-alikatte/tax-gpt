"""Vaud 2025 corpus ingest pipeline.

Loads `data/official/vd_2025.pdf` page by page, chunks via
RecursiveCharacterTextSplitter, embeds each chunk via the model router, and
persists everything to ChromaDB with a full metadata payload + an IndexStamp.

Determinism / safety:
  - 1-indexed PDF pages (asserted; `pdf_page is None` is a bug).
  - Every chunk carries all 14 metadata keys from
    `embedding_config.required_chunk_metadata_keys()`.
  - Re-running with a compatible stamp is a no-op unless `force_rebuild=True`.
  - Active-source-only: 2024 PDF is never ingested by this entrypoint.
  - No live network in tests: the embedder and chromadb client are injectable.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from TaxAI2025.ai import model_router
from TaxAI2025.core import config
from TaxAI2025.rag import embedding_config, sources
from TaxAI2025.rag.embedding_config import (
    IndexStamp,
    index_is_compatible,
    write_stamp,
)
from TaxAI2025.rag.schema import RagSource

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1100
CHUNK_OVERLAP = 200
SEPARATORS = ["\n\n", "\n", ". ", "•", " ", ""]
EMBED_BATCH_SIZE = 32

Embedder = Callable[[Iterable[str]], list[list[float]]]


# ---------------------------------------------------------------------------
# Page loader / splitter
# ---------------------------------------------------------------------------


def _load_pages(pdf_path: Path) -> Iterator[tuple[int, str]]:
    """Yield (1-indexed pdf_page, text) per page using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        yield (i + 1, text)


def _splitter():
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
    )


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def _chunk_metadata(
    *,
    source: RagSource,
    pdf_page: int,
    embed_model: str,
    embed_dims: int,
) -> dict[str, Any]:
    """Build the per-chunk metadata payload.

    Chroma metadata only accepts str/int/float/bool. Optional fields use empty
    string sentinels; the retriever reconstructs `None` from "".
    `vaud_codes` is serialized as a comma-separated string and split back at
    retrieval time.
    """
    return {
        "embedding_model": embed_model,
        "embedding_dimensions": embed_dims,
        "source_id": source.source_id,
        "source_title": source.title,
        "source_url": source.url or "",
        "source_hash": source.source_hash,
        "tax_year": source.tax_year,
        "canton": source.canton or "",
        "language": source.language,
        "pdf_page": pdf_page,
        "printed_page": "",
        "section_title": "",
        "vaud_codes": "",
        "topic": "",
    }


def _expected_stamp(source: RagSource) -> IndexStamp:
    return IndexStamp(
        embedding_model=embedding_config.PRIMARY_EMBEDDING_MODEL,
        embedding_dimensions=embedding_config.PRIMARY_DIMENSIONS,
        similarity=embedding_config.SIMILARITY,
        source_id=source.source_id,
        source_hash=source.source_hash,
        tax_year=source.tax_year,
        canton=source.canton or "",
    )


def collection_name(source: RagSource) -> str:
    """Deterministic Chroma collection name for a (source, embedding) pair."""
    safe_model = embedding_config.PRIMARY_EMBEDDING_MODEL.replace("-", "_")
    return f"{source.source_id}__{safe_model}"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _validate_chunk_metadata(meta: dict[str, Any]) -> None:
    required = set(embedding_config.required_chunk_metadata_keys())
    missing = required - set(meta.keys())
    if missing:
        raise RuntimeError(f"Chunk metadata missing keys: {sorted(missing)}")
    if meta.get("pdf_page") is None or not isinstance(meta["pdf_page"], int):
        raise RuntimeError(
            "pdf_page must be a 1-indexed int at ingest. "
            "None or non-int is a bug per RAG_CORPUS.md §6."
        )


def _chroma_client(index_dir: Path):
    import chromadb

    index_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(index_dir))


def build_index(
    *,
    force_rebuild: bool = False,
    index_dir: Path | None = None,
    embedder: Embedder | None = None,
    chroma_client_factory: Callable[[Path], Any] | None = None,
) -> dict[str, Any]:
    """Embed the active corpus and persist to ChromaDB.

    No-op if a compatible stamp already exists at `index_dir` unless
    `force_rebuild=True`. Returns a result dict for inspection.
    """
    embed = embedder or model_router.embed_texts
    factory = chroma_client_factory or _chroma_client
    source = sources.active_source()
    pdf_path = Path(source.local_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Active corpus not found: {pdf_path}")

    expected = _expected_stamp(source)
    target_dir = index_dir or config.rag_index_dir()

    if not force_rebuild and index_is_compatible(target_dir, expected):
        logger.info("Index already compatible at %s — skipping rebuild.", target_dir)
        return {
            "status": "skipped",
            "index_dir": str(target_dir),
            "reason": "compatible_stamp_present",
        }

    splitter = _splitter()
    chunk_ids: list[str] = []
    chunk_texts: list[str] = []
    chunk_metas: list[dict[str, Any]] = []

    for pdf_page, page_text in _load_pages(pdf_path):
        if not page_text.strip():
            continue
        for piece in splitter.split_text(page_text):
            piece = piece.strip()
            if not piece:
                continue
            meta = _chunk_metadata(
                source=source,
                pdf_page=pdf_page,
                embed_model=embedding_config.PRIMARY_EMBEDDING_MODEL,
                embed_dims=embedding_config.PRIMARY_DIMENSIONS,
            )
            _validate_chunk_metadata(meta)
            chunk_ids.append(
                f"{source.source_id}-p{pdf_page}-{uuid.uuid4().hex[:8]}"
            )
            chunk_texts.append(piece)
            chunk_metas.append(meta)

    if not chunk_ids:
        raise RuntimeError(f"No usable text extracted from {pdf_path}")

    embeddings: list[list[float]] = []
    for start in range(0, len(chunk_texts), EMBED_BATCH_SIZE):
        batch = chunk_texts[start : start + EMBED_BATCH_SIZE]
        embeddings.extend(embed(batch))

    if len(embeddings) != len(chunk_ids):
        raise RuntimeError(
            f"Embedding count {len(embeddings)} != chunk count {len(chunk_ids)}"
        )

    client = factory(target_dir)
    coll_name = collection_name(source)
    try:
        client.delete_collection(coll_name)
    except Exception:  # noqa: BLE001 — first build or already absent
        pass
    coll = client.create_collection(
        name=coll_name,
        metadata={"hnsw:space": embedding_config.SIMILARITY},
    )
    coll.add(
        ids=chunk_ids,
        documents=chunk_texts,
        metadatas=chunk_metas,
        embeddings=embeddings,
    )

    write_stamp(target_dir, expected)
    logger.info("Indexed %d chunks at %s", len(chunk_ids), target_dir)
    return {
        "status": "built",
        "index_dir": str(target_dir),
        "chunk_count": len(chunk_ids),
        "collection": coll_name,
    }
