"""Adaptive interview view.

Renders deterministic open questions from `TaxAI2025.interview.engine`.
Answers are stored on `AppState` for audit/replay; they do not become tax facts
without a later explicit extraction or user-labeling step.
"""
from __future__ import annotations

from typing import Any

import flet as ft

from TaxAI2025.interview import OpenQuestion, select_questions
from TaxAI2025.ui.components.footer import build_footer
from TaxAI2025.ui.navigation import Navigator, Screen
from TaxAI2025.ui.state import AppState, UserProfile


def _citation_text(question: OpenQuestion) -> str:
    return question.citation_token()


def _severity_badge(severity: str) -> ft.Control:
    colors = {
        "blocker": ("#FEE2E2", "#991B1B"),
        "likely_missing": ("#FEF3C7", "#92400E"),
        "nice_to_have": ("#E0E7FF", "#3730A3"),
    }
    bg, fg = colors.get(severity, ("#F1F5F9", "#334155"))
    return ft.Container(
        content=ft.Text(severity.replace("_", " ").upper(), size=10, weight="w700", color=fg),
        bgcolor=bg,
        padding=ft.padding.symmetric(vertical=3, horizontal=8),
        border_radius=10,
    )


def build_interview_view(state: AppState, navigator: Navigator, page: ft.Page) -> ft.Control:
    profile = state.profile or UserProfile()
    questions_column = ft.Column(spacing=10)
    status_text = ft.Text(size=13, color="#475569")

    def rerender() -> None:
        questions_column.controls.clear()
        questions = select_questions(
            profile,
            state.facts,
            answered_ids=state.answered_question_ids(),
            limit=10,
        )
        status_text.value = (
            f"{len(questions)} open question(s) selected from your profile and confirmed facts."
        )
        if not questions:
            questions_column.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.CHECK_CIRCLE, color="#16A34A"),
                            ft.Text(
                                "No interview questions left for now.",
                                size=13,
                                color="#1E293B",
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=12,
                    bgcolor="#ECFDF5",
                    border=ft.border.all(1, "#A7F3D0"),
                    border_radius=8,
                )
            )
        for q in questions:
            questions_column.controls.append(_question_card(q))
        page.update()

    def answer(question_id: str, value: str) -> None:
        state.record_interview_answer(question_id, value)
        rerender()

    def _question_card(question: OpenQuestion) -> ft.Control:
        answer_field = ft.TextField(
            label="Answer or note",
            hint_text="e.g. yes, no, amount paid, or document to upload",
            multiline=False,
            expand=True,
        )

        def save_text(_e: Any) -> None:
            value = (answer_field.value or "").strip()
            if value:
                answer(question.id, value)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(question.id, size=11, weight="w700", color="#4F46E5"),
                                    ft.Text(question.question_en, size=15, weight="w700", color="#0F172A"),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            _severity_badge(question.severity),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Text(question.why_en, size=13, color="#334155"),
                    ft.Text(_citation_text(question), size=11, color="#3730A3"),
                    ft.Row(
                        [
                            ft.OutlinedButton("No", on_click=lambda _e: answer(question.id, "no")),
                            ft.OutlinedButton("Yes", on_click=lambda _e: answer(question.id, "yes")),
                            answer_field,
                            ft.ElevatedButton(
                                "Save",
                                icon=ft.icons.SAVE_OUTLINED,
                                bgcolor="#4F46E5",
                                color="white",
                                on_click=save_text,
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=8,
            ),
            padding=14,
            bgcolor="#FFFFFF",
            border=ft.border.all(1, "#E2E8F0"),
            border_radius=10,
        )

    body = ft.Column(
        [
            ft.Text("Adaptive interview", size=26, weight="w800", color="#0F172A"),
            ft.Text(
                "Deterministic follow-up questions. We ask before guessing and keep answers auditable.",
                size=14,
                color="#475569",
            ),
            ft.Container(
                content=status_text,
                padding=10,
                bgcolor="#EEF2FF",
                border=ft.border.all(1, "#C7D2FE"),
                border_radius=8,
            ),
            questions_column,
            ft.Row(
                [
                    ft.OutlinedButton(
                        "Back",
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda _e: navigator.go(Screen.EXTRACTED),
                    ),
                    ft.ElevatedButton(
                        "Continue to missing things",
                        icon=ft.icons.ARROW_FORWARD,
                        bgcolor="#4F46E5",
                        color="white",
                        on_click=lambda _e: navigator.go(Screen.COMPLETENESS),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
    )
    rerender()
    return ft.Column(
        [
            ft.Container(content=body, padding=30, expand=True),
            build_footer(),
        ],
        expand=True,
        spacing=0,
    )


__all__ = ["build_interview_view"]
