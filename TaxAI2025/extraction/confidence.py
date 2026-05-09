"""Confidence scoring helpers.

Deterministic: regex/template matches always score 1.0 (the regex either
matched or did not). LLM extractions take the value the model returned
when present, else fall back to a configured default. We never invent
calibrated confidence — unknown stays None or the default.
"""
from __future__ import annotations

from typing import Any


LLM_DEFAULT_CONFIDENCE: float = 0.6
HEURISTIC_CLASSIFIER_CONFIDENCE: float = 0.95
LLM_CLASSIFIER_DEFAULT_CONFIDENCE: float = 0.7


def score_regex_match() -> float:
    """A regex either matched or it did not. Confidence is 1.0 by construction."""
    return 1.0


def score_pdf_text_match() -> float:
    """Direct pdf_text positional read — same hardness as a regex match."""
    return 1.0


def score_llm_extraction(model_payload: dict[str, Any] | None) -> float:
    """Pull the model-emitted confidence from a structured payload.

    The Pydantic schema asks the model to return a `confidence` float in
    [0,1]. Anything else falls back to LLM_DEFAULT_CONFIDENCE so we never
    invent a number.
    """
    if not isinstance(model_payload, dict):
        return LLM_DEFAULT_CONFIDENCE
    raw = model_payload.get("confidence")
    if isinstance(raw, (int, float)) and 0.0 <= float(raw) <= 1.0:
        return float(raw)
    return LLM_DEFAULT_CONFIDENCE
