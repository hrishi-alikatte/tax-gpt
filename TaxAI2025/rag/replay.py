"""DEMO_MODE=replay loader for RAG: returns canned answers from disk.

The replay path bypasses retrieval and LLM generation. Canned answers are
stored in:
    demo/scenarios/<scenario>/answers/<question_hash>.json

If a question hash matches a file, it is loaded. Otherwise, a generic
refusal is returned (mimicking retrieval failure in demo mode).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from TaxAI2025.core import config
from TaxAI2025.rag.schema import GroundedAnswer


class ReplayError(RuntimeError):
    pass


def _scenarios_dir() -> Path:
    return config.REPO_ROOT / "demo" / "scenarios"


def _question_hash(question: str) -> str:
    """Deterministic hash of a normalized question."""
    normalized = question.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def load_replay_answer(question: str) -> GroundedAnswer | None:
    """Try to load a canned answer for the given question.

    Returns None if no fixture exists for this question in the active scenario.
    """
    scenario = config._optional("DEMO_SCENARIO", "expat_c_permit_basic") or "expat_c_permit_basic"
    h = _question_hash(question)
    fixture = _scenarios_dir() / scenario / "answers" / f"{h}.json"

    if not fixture.is_file():
        return None

    try:
        raw = json.loads(fixture.read_text(encoding="utf-8"))
        return GroundedAnswer(**raw)
    except Exception as e:
        # In replay mode we want to know if fixtures are broken.
        raise ReplayError(f"Failed to load RAG replay fixture {fixture}: {e}") from e
