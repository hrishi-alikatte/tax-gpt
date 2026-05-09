"""DEMO_MODE=replay loader: returns canned TaxFacts from disk.

The replay path bypasses live OCR/LLM. Synthetic fixtures only — anything
that looks like real PII is a bug. The fixture path is:
    demo/scenarios/<scenario>/extracted.json

Schema: {"document": {<DocumentRecord>}, "facts": [<TaxFact>, ...]}
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from pydantic import ValidationError

from TaxAI2025.core import config
from TaxAI2025.core.documents import DocumentRecord
from TaxAI2025.core.tax_facts import TaxFact, validate_provenance


class ReplayError(RuntimeError):
    pass


def _scenarios_dir() -> Path:
    return config.REPO_ROOT / "demo" / "scenarios"


def load_replay_extraction(
    scenario: str, fallback_filename: str | None = None
) -> tuple[DocumentRecord, list[TaxFact]]:
    fixture = _scenarios_dir() / scenario / "extracted.json"
    if not fixture.is_file():
        raise ReplayError(f"Replay fixture missing: {fixture}")

    try:
        raw = json.loads(fixture.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ReplayError(f"Replay fixture not valid JSON: {fixture}: {e}") from e

    if not isinstance(raw, dict) or "facts" not in raw:
        raise ReplayError(
            f"Replay fixture must be an object with a 'facts' list: {fixture}"
        )

    doc_payload = raw.get("document") or {}
    if "doc_id" not in doc_payload:
        doc_payload["doc_id"] = str(uuid.uuid4())
    if "filename" not in doc_payload and fallback_filename:
        doc_payload["filename"] = fallback_filename
    if "file_path" not in doc_payload:
        doc_payload["file_path"] = doc_payload.get("filename", "<replay>")

    try:
        record = DocumentRecord(**doc_payload)
    except ValidationError as e:
        raise ReplayError(f"DocumentRecord schema mismatch in {fixture}: {e}") from e

    facts: list[TaxFact] = []
    for i, item in enumerate(raw["facts"]):
        try:
            fact = TaxFact(**item)
        except ValidationError as e:
            raise ReplayError(
                f"TaxFact #{i} schema mismatch in {fixture}: {e}"
            ) from e
        if fact.confirmed_by_user:
            raise ReplayError(
                f"Replay fixture #{i} has confirmed_by_user=True; "
                f"the extraction layer must never emit confirmed facts."
            )
        validate_provenance(fact)
        facts.append(fact)

    return record, facts


__all__ = ["load_replay_extraction", "ReplayError"]
