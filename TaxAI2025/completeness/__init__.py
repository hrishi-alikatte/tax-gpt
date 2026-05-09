"""Deterministic completeness engine.

NEVER imports an LLM client. NEVER calls a model. Pure rules-as-data.
See `README.md` for the boundary contract.
"""
from __future__ import annotations

from TaxAI2025.completeness.engine import evaluate
from TaxAI2025.completeness.rules import RULES
from TaxAI2025.completeness.schema import (
    CompletenessRule,
    Finding,
    Severity,
    VerificationStatus,
)

__all__ = [
    "CompletenessRule",
    "Finding",
    "RULES",
    "Severity",
    "VerificationStatus",
    "evaluate",
]
