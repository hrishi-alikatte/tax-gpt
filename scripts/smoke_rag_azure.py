"""Manual smoke script for the live Azure path.

Modes (run only when explicitly invoked):

    # Build the Vaud 2025 ChromaDB index from the official PDF (one-time, ~$0.01).
    python scripts/smoke_rag_azure.py ingest

    # Ask one question through the real retriever + explain wrapper (live chat call).
    python scripts/smoke_rag_azure.py ask
    python scripts/smoke_rag_azure.py ask "What is Pillar 3a in VaudTax?"

    # Cheapest sanity: fixture-mode chunk + live chat call (no index needed).
    python scripts/smoke_rag_azure.py fixture

Behavior:
  - Loads `.env` via python-dotenv.
  - Validates required env. Fails clearly if anything missing.
  - Prints answers + citations. Never prints API keys or raw responses.

This script DOES make live network calls. It is not part of the test suite
and is not run automatically.
"""
from __future__ import annotations

import sys
from typing import Iterable

from TaxAI2025.rag.schema import RagChunk


DEFAULT_QUESTION = "What is Pillar 3a in VaudTax?"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        return
    load_dotenv()


def _check_config() -> int:
    try:
        from TaxAI2025.core import config

        config.azure_config()  # touches required env
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: configuration is incomplete — {e}", file=sys.stderr)
        return 2


class _DemoRetriever:
    """Fixture-mode retriever: a single hand-crafted chunk, no index needed."""

    def __init__(self, chunks: Iterable[RagChunk]):
        self._chunks = list(chunks)

    def retrieve(self, query: str, *, k: int = 4):  # noqa: ANN001, ARG002
        return list(self._chunks)


def _print_result(result) -> int:  # noqa: ANN001
    if result.refused:
        print(f"REFUSED: {result.refusal_reason}")
        print(result.answer_en)
        return 1
    print("\n--- Answer ---")
    print(result.answer_en)
    print("\n--- Citations ---")
    for c in result.citations:
        print(
            f"- {c.token}  source_id={c.source_id}  "
            f"chunk_id={c.chunk_id}  section={c.section_title}"
        )
    print("\n--- Retrieval ---")
    if result.retrieval is not None:
        for ch in result.retrieval.chunks:
            head = (ch.text[:80] + "…") if len(ch.text) > 80 else ch.text
            print(f"- p.{ch.pdf_page} chunk_id={ch.chunk_id} :: {head}")
    print(f"\nmodel_name={result.model_name}")
    return 0


def cmd_ingest() -> int:
    rc = _check_config()
    if rc:
        return rc
    from TaxAI2025.rag import ingest

    print("Building Vaud 2025 ChromaDB index…")
    result = ingest.build_index(force_rebuild=False)
    print(f"status={result['status']}  index_dir={result['index_dir']}")
    if result["status"] == "built":
        print(f"chunk_count={result['chunk_count']}  collection={result['collection']}")
    return 0


def cmd_ask(question: str) -> int:
    rc = _check_config()
    if rc:
        return rc
    from TaxAI2025.rag.explain import answer_with_citations
    from TaxAI2025.rag.retriever import get_default_retriever

    retriever = get_default_retriever()
    if retriever is None:
        print(
            "ERROR: no compatible Vaud 2025 index found. "
            "Run `python scripts/smoke_rag_azure.py ingest` first.",
            file=sys.stderr,
        )
        return 3

    print(f"Q: {question}")
    print("(routing through Azure deployment configured by AZURE_OPENAI_DEPLOYMENT_RAG)")
    result = answer_with_citations(question, retriever=retriever)
    return _print_result(result)


def cmd_fixture() -> int:
    rc = _check_config()
    if rc:
        return rc
    from TaxAI2025.core import config
    from TaxAI2025.rag.explain import answer_with_citations

    cfg = config.azure_config()
    chunk = RagChunk(
        chunk_id="demo-1",
        source_id="vd_2025_instructions",
        text=(
            "Le 3e pilier A est une forme de prévoyance individuelle liée. "
            "Pour les salariés, les cotisations annuelles sont déductibles "
            "jusqu'au plafond fixé par la loi fédérale."
        ),
        pdf_page=None,  # exercises the page-pending token path
        section_title="3e pilier A (smoke fixture)",
        topic="pillar_3a",
        language="fr",
        embedding_model=cfg.embedding_model,
        embedding_dimensions=cfg.embedding_dimensions,
    )
    print(f"Q: {DEFAULT_QUESTION}  (fixture mode)")
    result = answer_with_citations(
        DEFAULT_QUESTION, retriever=_DemoRetriever([chunk])
    )
    return _print_result(result)


def _print_help() -> int:
    print(__doc__)
    return 0


def main(argv: list[str]) -> int:
    _load_dotenv()
    if len(argv) < 2:
        return _print_help()
    cmd = argv[1]
    if cmd == "ingest":
        return cmd_ingest()
    if cmd == "ask":
        question = argv[2] if len(argv) >= 3 else DEFAULT_QUESTION
        return cmd_ask(question)
    if cmd == "fixture":
        return cmd_fixture()
    if cmd in ("-h", "--help", "help"):
        return _print_help()
    print(f"Unknown command: {cmd!r}", file=sys.stderr)
    return _print_help() or 64


if __name__ == "__main__":
    sys.exit(main(sys.argv))
