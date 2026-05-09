"""Extracted-values view — the confirmation gate.

Every TaxFact is shown with: canonical_field, value, source_doc/page,
confidence badge, and a Confirm checkbox. The Continue button is
disabled until `state.is_extracted_complete()` returns True.
"""
from __future__ import annotations

from typing import Any

import flet as ft

from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.ui.components.confirm_checkbox import (
    build_confirm_checkbox,
    confidence_badge,
)
from TaxAI2025.ui.components.footer import build_footer
from TaxAI2025.ui.navigation import Navigator, Screen
from TaxAI2025.ui.state import AppState

NEXT_AFTER_EXTRACTION = Screen.INTERVIEW


def _format_value(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def build_extracted_view(
    state: AppState,
    navigator: Navigator,
    page: ft.Page,
) -> ft.Control:
    required_fields = state.required_fields()
    progress_text = ft.Text("", size=13, color="#475569")
    table_column = ft.Column(spacing=8)
    continue_btn = ft.ElevatedButton(
        "Continue",
        icon=ft.icons.ARROW_FORWARD,
        bgcolor="#4F46E5",
        color="white",
        disabled=True,
    )

    def on_continue(_e: Any) -> None:
        if state.is_extracted_complete():
            navigator.go(NEXT_AFTER_EXTRACTION)

    continue_btn.on_click = on_continue

    def update_progress() -> None:
        confirmed = sum(1 for f in state.facts if f.confirmed_by_user)
        total = len(state.facts)
        progress_text.value = (
            f"{confirmed} of {total} values confirmed."
            + (" Continue is enabled." if state.is_extracted_complete()
               else " Confirm every required value to continue.")
        )
        continue_btn.disabled = not state.is_extracted_complete()

    def fact_row(fact: TaxFact) -> ft.Control:
        is_required = fact.canonical_field in required_fields

        def on_toggle(checked: bool, field: str = fact.canonical_field) -> None:
            if checked:
                state.confirm_fact(field)
            else:
                state.unconfirm_fact(field)
            update_progress()
            page.update()

        checkbox = build_confirm_checkbox(
            initial=fact.confirmed_by_user,
            on_toggle=on_toggle,
        )

        required_pill = (
            ft.Container(
                content=ft.Text("required", size=10, weight="w700", color="#1E40AF"),
                padding=ft.padding.symmetric(vertical=2, horizontal=6),
                bgcolor="#DBEAFE",
                border_radius=6,
            )
            if is_required
            else ft.Container(width=0)
        )

        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        fact.canonical_field,
                                        size=13, weight="w700", color="#0F172A",
                                        selectable=True,
                                    ),
                                    required_pill,
                                ],
                                spacing=8,
                            ),
                            ft.Text(
                                _format_value(fact.value),
                                size=15, weight="w800", color="#1E293B",
                                selectable=True,
                            ),
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.SOURCE, size=12, color="#64748B"),
                                    ft.Text(
                                        f"{fact.source_doc} • page {fact.source_page}",
                                        size=11, color="#64748B",
                                        selectable=True,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Column(
                        [
                            confidence_badge(fact.confidence),
                            ft.Container(height=6),
                            checkbox,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=14,
            bgcolor="#FFFFFF",
            border=ft.border.all(1, "#E2E8F0"),
            border_radius=10,
        )

    if not state.facts:
        table_column.controls.append(
            ft.Text(
                "No values extracted yet. Upload at least one document.",
                size=13, italic=True, color="#94A3B8",
            )
        )
    else:
        for fact in state.facts:
            table_column.controls.append(fact_row(fact))

    update_progress()

    body = ft.Column(
        [
            ft.Text("Confirm each value", size=26, weight="w800", color="#0F172A"),
            ft.Text(
                "We never use a value until you tick its Confirm box. "
                "Source page is shown so you can cross-check the original PDF.",
                size=14, color="#475569",
            ),
            ft.Container(
                content=progress_text,
                padding=10,
                bgcolor="#EEF2FF",
                border=ft.border.all(1, "#C7D2FE"),
                border_radius=8,
            ),
            ft.Container(height=6),
            table_column,
            ft.Container(height=10),
            ft.Row([continue_btn], alignment=ft.MainAxisAlignment.END),
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


__all__ = ["NEXT_AFTER_EXTRACTION", "build_extracted_view"]
