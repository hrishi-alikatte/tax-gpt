"""Explain view: source-grounded Q&A.

Calls `TaxAI2025.rag.explain.answer_with_citations` directly. The pure
`handle_explain` helper is split out so tests can drive it without a
Flet page.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable

import flet as ft

from TaxAI2025.rag.schema import GroundedAnswer, RagCitation
from TaxAI2025.ui.components.citation_chip import build_citation_chip
from TaxAI2025.ui.components.footer import build_footer
from TaxAI2025.ui.navigation import Navigator, Screen
from TaxAI2025.ui.state import AppState


SUGGESTED_QUESTIONS: tuple[str, ...] = (
    "What is Pillar 3a in VaudTax?",
    "What does ordinary taxation mean for a C-permit employee?",
    "Why do you ask for bank balances at year end?",
)


@dataclass
class ExplainOutcome:
    answer: GroundedAnswer
    refused: bool
    citations: list[RagCitation]
    refusal_reason: str | None


def handle_explain(
    question: str,
    answerer: Callable[[str], GroundedAnswer],
) -> ExplainOutcome:
    """Pure handler, no Flet objects.

    Tests inject a stub `answerer` to avoid touching the live LLM.
    """
    if not question or not question.strip():
        raise ValueError("Question must be non-empty.")
    answer = answerer(question.strip())
    return ExplainOutcome(
        answer=answer,
        refused=answer.refused,
        citations=list(answer.citations),
        refusal_reason=answer.refusal_reason,
    )


def _refusal_badge(reason: str | None) -> ft.Control:
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.icons.BLOCK, color="#B91C1C", size=14),
                ft.Text(
                    f"Refused: {reason or 'unspecified'}",
                    size=12, weight="w700", color="#B91C1C",
                ),
            ],
            spacing=6,
        ),
        padding=ft.padding.symmetric(vertical=4, horizontal=8),
        bgcolor="#FEE2E2",
        border_radius=8,
    )


def build_explain_view(
    state: AppState,
    navigator: Navigator,
    page: ft.Page,
) -> ft.Control:
    question_field = ft.TextField(
        label="Ask about Vaud taxes (English)",
        hint_text="e.g. What is Pillar 3a in VaudTax?",
        multiline=False,
        expand=True,
    )
    answer_panel = ft.Column(spacing=10)
    loading_row = ft.Row(
        [
            ft.ProgressRing(width=18, height=18, stroke_width=2, color="#4F46E5"),
            ft.Text("Thinking…", size=13, color="#475569"),
        ],
        spacing=10,
        visible=False,
    )

    def render_answer(outcome: ExplainOutcome) -> None:
        answer_panel.controls.clear()
        if outcome.refused:
            answer_panel.controls.append(_refusal_badge(outcome.refusal_reason))
            answer_panel.controls.append(
                ft.Text(outcome.answer.answer_en, size=14, color="#1E293B"),
            )
        else:
            answer_panel.controls.append(
                ft.Container(
                    content=ft.Text(
                        outcome.answer.answer_en,
                        size=14, color="#0F172A", selectable=True,
                    ),
                    padding=14,
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, "#E2E8F0"),
                    border_radius=10,
                ),
            )
            if outcome.citations:
                answer_panel.controls.append(
                    ft.Text("Citations", size=12, weight="w700", color="#0F172A"),
                )
                answer_panel.controls.append(
                    ft.Row(
                        [build_citation_chip(c) for c in outcome.citations],
                        wrap=True, spacing=8, run_spacing=8,
                    ),
                )
        page.update()

    def render_error(ex: Exception) -> None:
        answer_panel.controls.clear()
        answer_panel.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "We couldn't get an answer.",
                            size=14, weight="w700", color="#B91C1C",
                        ),
                        ft.Text(
                            f"{type(ex).__name__}: {ex}",
                            size=12, color="#7F1D1D",
                        ),
                        ft.Text(
                            "Try again, or check your model provider configuration "
                            "in .env.",
                            size=12, color="#7F1D1D",
                        ),
                    ],
                    spacing=4,
                ),
                padding=12,
                bgcolor="#FEE2E2",
                border=ft.border.all(1, "#FCA5A5"),
                border_radius=8,
            )
        )
        page.update()

    def run_ask(question: str) -> None:
        from TaxAI2025.rag.explain import answer_with_citations

        try:
            outcome = handle_explain(question, answer_with_citations)
            state.record(
                "explain_refused" if outcome.refused else "explain_asked",
                question=question,
                refusal_reason=outcome.refusal_reason,
                citation_count=len(outcome.citations),
            )
            loading_row.visible = False
            render_answer(outcome)
        except Exception as ex:  # noqa: BLE001
            loading_row.visible = False
            render_error(ex)

    def on_ask(_e: Any) -> None:
        q = (question_field.value or "").strip()
        if not q:
            return
        loading_row.visible = True
        answer_panel.controls.clear()
        page.update()
        threading.Thread(target=run_ask, args=(q,), daemon=True).start()

    def fill_suggested(q: str) -> Callable[[Any], None]:
        def _handler(_e: Any) -> None:
            question_field.value = q
            page.update()
        return _handler

    suggested = ft.Row(
        [
            ft.OutlinedButton(q, on_click=fill_suggested(q))
            for q in SUGGESTED_QUESTIONS
        ],
        wrap=True,
        spacing=8,
        run_spacing=8,
    )

    ask_btn = ft.ElevatedButton(
        "Ask",
        icon=ft.icons.QUESTION_ANSWER,
        bgcolor="#4F46E5",
        color="white",
        on_click=on_ask,
    )

    body = ft.Column(
        [
            ft.Text("Explain", size=26, weight="w800", color="#0F172A"),
            ft.Text(
                "Every answer is grounded in the official Vaud 2025 Instructions. "
                "If the corpus does not contain the answer, the system refuses.",
                size=14, color="#475569",
            ),
            ft.Text("Suggested questions", size=12, weight="w700", color="#334155"),
            suggested,
            ft.Row([question_field, ask_btn], spacing=10),
            loading_row,
            answer_panel,
            ft.Container(height=10),
            ft.Row(
                [
                    ft.OutlinedButton(
                        "Back to mapping",
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda _e: navigator.go(Screen.MAPPING),
                    ),
                ],
            ),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Column(
        [
            ft.Container(content=body, padding=30, expand=True),
            build_footer(),
        ],
        expand=True,
        spacing=0,
    )


__all__ = [
    "ExplainOutcome",
    "SUGGESTED_QUESTIONS",
    "build_explain_view",
    "handle_explain",
]
