"""Optional cosmetic phrasing for interview questions."""
from __future__ import annotations

from TaxAI2025.interview.schema import OpenQuestion
from TaxAI2025.ui.state import UserProfile


def polish_question(question: OpenQuestion, profile: UserProfile, locale: str = "en") -> str:
    """Return a user-facing phrasing, falling back to deterministic text.

    The LLM is cosmetic only; it must never decide which questions are asked.
    """
    if locale != "en":
        return question.question_en
    try:
        from TaxAI2025.ai import model_router

        text = model_router.generate_text(
            [
                {
                    "role": "system",
                    "content": (
                        "Rewrite the tax interview question in plain, friendly English. "
                        "Do not add legal advice, tax facts, numbers, or requirements."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Name: {profile.first_name or 'the user'}\n"
                        f"Question: {question.question_en}\n"
                        "Return one question sentence only."
                    ),
                },
            ],
            purpose="completeness_explanation",
        ).strip()
        return text or question.question_en
    except Exception:  # noqa: BLE001
        return question.question_en


__all__ = ["polish_question"]
