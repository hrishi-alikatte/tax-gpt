"""Extraction layer: classify -> ocr -> extract.

Public entrypoint:
    extract_from_upload(file_path) -> tuple[DocumentRecord, list[TaxFact]]

The entrypoint branches on `config.DEMO_MODE`:
  - "replay" -> load canned facts from demo/scenarios/<DEMO_SCENARIO>/extracted.json
  - otherwise -> live pipeline (pdfplumber + heuristics + LLM-primary extraction
    with regex cross-checks)

No extracted value ever leaves this layer with `confirmed_by_user=True`.
That bit is owned by the confirmation UI (M3).
"""
from __future__ import annotations

import os
from pathlib import Path

from TaxAI2025.core import config
from TaxAI2025.core.documents import DocumentRecord, DocumentType, KNOWN_DOCUMENT_TYPES
from TaxAI2025.core.tax_facts import TaxFact, validate_provenance
from TaxAI2025.extraction.generic import GenericFact


def extract_from_upload(file_path: Path | str) -> tuple[DocumentRecord, list[TaxFact]]:
    path = Path(file_path)

    if config.DEMO_MODE == "replay":
        from TaxAI2025.extraction.replay import load_replay_extraction

        scenario = os.environ.get("DEMO_SCENARIO", "expat_c_permit_basic")
        return load_replay_extraction(scenario, fallback_filename=path.name)

    from TaxAI2025.extraction.classify import classify_document
    from TaxAI2025.extraction.extract import extract_facts
    from TaxAI2025.extraction.ocr import extract_text

    record = classify_document(path)
    pages = extract_text(path)
    facts = extract_facts(record, pages)
    for f in facts:
        validate_provenance(f)
        if f.confirmed_by_user:
            raise RuntimeError(
                f"Extraction layer must never set confirmed_by_user=True "
                f"(canonical_field={f.canonical_field!r})."
            )
    return record, facts


__all__ = [
    "DocumentRecord",
    "DocumentType",
    "GenericFact",
    "KNOWN_DOCUMENT_TYPES",
    "TaxFact",
    "extract_from_upload",
]
