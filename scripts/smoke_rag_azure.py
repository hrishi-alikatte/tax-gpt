"""Manual smoke script: live Azure call, ONE supported question.

Run only when explicitly invoked:

    python scripts/smoke_rag_azure.py

Behavior:
  - Loads `.env` via python-dotenv if installed.
  - Validates required env. Fails clearly if anything missing.
  - Asks one supported question through `answer_with_citations`.
  - Prints the answer and the citations only.
  - Never prints API keys, endpoints, or raw model responses.

This script DOES make a live network call. It is not part of the test suite
and is not run automatically.
"""
from __future__ import annotations

import sys
from typing import Iterable

from TaxAI2025.rag.schema import RagChunk


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        return
    load_dotenv()


class _DemoRetriever:
    """Returns a single hand-crafted chunk so the smoke test exercises the live
    chat path without first requiring a fully-built ChromaDB index.

    Replace with the real retriever once Phase G+1 (ingest+retrieve) lands.
    """

    def __init__(self, chunks: Iterable[RagChunk]):
        self._chunks = list(chunks)

    def retrieve(self, query: str, *, k: int = 4):  # noqa: ANN001, ARG002
        return list(self._chunks)


def main() -> int:
    _load_dotenv()
    try:
        from TaxAI2025.core import config

        # Touch config so missing-env fails fast and clearly.
        cfg = config.azure_config()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: configuration is incomplete — {e}", file=sys.stderr)
        return 2

    # Build a minimal demo chunk. Page is intentionally None to exercise the
    # `page pending verification` token path; a real index will set pdf_page.
    chunk = RagChunk(
        chunk_id="demo-1",
        source_id="vd_2025_instructions",
        text=(
            "Le 3e pilier A est une forme de prévoyance individuelle liée. "
            "Pour les salariés, les cotisations annuelles sont déductibles "
            "jusqu'au plafond fixé par la loi fédérale."
        ),
        pdf_page=None,
        section_title="3e pilier A (smoke fixture)",
        topic="pillar_3a",
        language="fr",
        embedding_model=cfg.embedding_model,
        embedding_dimensions=cfg.embedding_dimensions,
    )

    from TaxAI2025.rag.explain import answer_with_citations

    question = "What is Pillar 3a in VaudTax?"
    print(f"Q: {question}")
    print("(routing through Azure deployment configured by AZURE_OPENAI_DEPLOYMENT_RAG)")

    result = answer_with_citations(question, retriever=_DemoRetriever([chunk]))

    if result.refused:
        print(f"REFUSED: {result.refusal_reason}")
        print(result.answer_en)
        return 1

    print("\n--- Answer ---")
    print(result.answer_en)
    print("\n--- Citations ---")
    for c in result.citations:
        print(f"- {c.token}  source_id={c.source_id}  chunk_id={c.chunk_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
