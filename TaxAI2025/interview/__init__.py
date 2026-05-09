"""Adaptive interview engine.

The engine is deterministic. It selects source-cited questions from profile
and confirmed facts; optional LLM phrasing lives separately in `phrasing.py`.
"""
from TaxAI2025.interview.engine import select_questions
from TaxAI2025.interview.registry import QUESTIONS
from TaxAI2025.interview.schema import OpenQuestion, QuestionSeverity

__all__ = ["QUESTIONS", "OpenQuestion", "QuestionSeverity", "select_questions"]
