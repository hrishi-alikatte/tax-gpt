"""ChromaDB-backed retriever for the active Vaud corpus.

Implements the `Retriever` Protocol from `explain.py` so the explain wrapper
defaults to real retrieval when an index exists, and tests keep injecting
deterministic stubs.

Lazy: chromadb is NOT imported at module load. The first `retrieve()` call
triggers connection. The retriever filters out any chunk whose `source_id`
is not in `sources.all_active_sources()` (defense-in-depth: the explain
wrapper enforces the same fence).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterable

from TaxAI2025.ai import model_router
from TaxAI2025.core import config
from TaxAI2025.rag import embedding_config, sources
from TaxAI2025.rag.embedding_config import IndexStamp, index_is_compatible
from TaxAI2025.rag.ingest import collection_name
from TaxAI2025.rag.schema import RagChunk

logger = logging.getLogger(__name__)

Embedder = Callable[[Iterable[str]], list[list[float]]]


def _expected_stamp() -> IndexStamp:
    source = sources.active_source()
    return IndexStamp(
        embedding_model=embedding_config.PRIMARY_EMBEDDING_MODEL,
        embedding_dimensions=embedding_config.PRIMARY_DIMENSIONS,
        similarity=embedding_config.SIMILARITY,
        source_id=source.source_id,
        source_hash=source.source_hash,
        tax_year=source.tax_year,
        canton=source.canton or "",
    )


def _to_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_str_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _to_rag_chunk(chunk_id: str, text: str, meta: dict[str, Any]) -> RagChunk:
    raw_codes = meta.get("vaud_codes") or ""
    codes = [c.strip() for c in raw_codes.split(",") if c.strip()] if raw_codes else []
    return RagChunk(
        chunk_id=chunk_id,
        source_id=meta["source_id"],
        text=text,
        pdf_page=_to_int_or_none(meta.get("pdf_page")),
        printed_page=_to_str_or_none(meta.get("printed_page")),
        section_title=_to_str_or_none(meta.get("section_title")),
        vaud_codes=codes,
        topic=_to_str_or_none(meta.get("topic")),
        language=meta.get("language", "fr"),
        embedding_model=_to_str_or_none(meta.get("embedding_model")),
        embedding_dimensions=_to_int_or_none(meta.get("embedding_dimensions")),
    )


class ChromaRetriever:
    """Cosine similarity retriever backed by a persisted Chroma collection.

    Construction does NOT touch chromadb. The first `retrieve()` opens the
    persistent client, validates the index stamp, and caches the collection
    handle.
    """

    def __init__(
        self,
        *,
        embedder: Embedder | None = None,
        client: Any | None = None,
        collection: Any | None = None,
    ) -> None:
        self._embedder: Embedder = embedder or model_router.embed_texts
        self._client = client
        self._collection = collection

    def _ensure_collection(self) -> Any:
        if self._collection is not None:
            return self._collection
        if self._client is None:
            import chromadb

            index_dir = config.rag_index_dir()
            if not index_is_compatible(index_dir, _expected_stamp()):
                raise RuntimeError(
                    f"Index at {index_dir} is missing or stale. "
                    f"Run TaxAI2025.rag.ingest.build_index() first."
                )
            self._client = chromadb.PersistentClient(path=str(index_dir))
        self._collection = self._client.get_collection(
            collection_name(sources.active_source())
        )
        return self._collection

    def retrieve(self, query: str, *, k: int = 4) -> list[RagChunk]:
        coll = self._ensure_collection()
        query_embeddings = self._embedder([query])
        result = coll.query(query_embeddings=query_embeddings, n_results=k)

        active_ids = {s.source_id for s in sources.all_active_sources()}
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]

        chunks: list[RagChunk] = []
        for chunk_id, text, meta in zip(ids, docs, metas):
            if not meta or meta.get("source_id") not in active_ids:
                continue
            chunks.append(_to_rag_chunk(chunk_id, text, meta))
        return chunks


def get_default_retriever() -> "ChromaRetriever | None":
    """Return a ready ChromaRetriever, or None if no compatible index exists.

    Used by `explain.answer_with_citations` to default-wire production
    retrieval without breaking tests that have no index built.
    """
    try:
        index_dir = config.rag_index_dir()
        expected = _expected_stamp()
        if index_is_compatible(index_dir, expected):
            return ChromaRetriever()
        if config.rag_auto_build_index():
            from TaxAI2025.rag import ingest

            logger.info("RAG index missing or stale at %s; building it now.", index_dir)
            ingest.build_index(force_rebuild=False, index_dir=index_dir)
            if index_is_compatible(index_dir, expected):
                return ChromaRetriever()
            logger.warning("RAG index build finished but stamp is still incompatible.")
    except Exception as e:  # noqa: BLE001 — config or stamp unreadable
        logger.error(
            "CRITICAL: Default retriever unavailable. Check .env for "
            "AZURE_OPENAI_API_KEY and RAG_INDEX_DIR. Error: %s", e
        )
    return None
