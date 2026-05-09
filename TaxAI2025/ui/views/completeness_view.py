"""Completeness view — STUB for M4.

The deterministic completeness engine arrives in M4 (see ROADMAP.md).
This screen is intentionally minimal: it exists so the demo flow walks
end-to-end today. In M4 it will render `Finding` objects from
`completeness.engine.evaluate(profile, confirmed_facts)`.
"""
from __future__ import annotations

from typing import Any

import flet as ft

from TaxAI2025.ui.components.footer import build_footer
from TaxAI2025.ui.navigation import Navigator, Screen
from TaxAI2025.ui.state import AppState


_PLANNED_RULES = (
    ("VD-CHILDCARE-001", "Childcare deduction (kids declared, no daycare invoice)"),
    ("VD-PILLAR3A-001", "Pillar 3a (employed, no 3a attestation)"),
    ("VD-COMMUTE-001", "Commute (residence ≠ work commune, no transport pass)"),
    ("VD-MEAL-001", "Meal allowance method"),
    ("VD-INSURANCE-001", "Health insurance premium"),
    ("VD-BANK-001", "Bank year-end balance"),
)


def build_completeness_view(state: AppState, navigator: Navigator) -> ft.Control:
    confirmed_count = sum(1 for f in state.facts if f.confirmed_by_user)

    def rule_card(rule_id: str, title: str) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.RULE, color="#4F46E5"),
                    ft.Column(
                        [
                            ft.Text(rule_id, size=12, weight="w700", color="#4F46E5"),
                            ft.Text(title, size=13, color="#1E293B"),
                            ft.Text(
                                "Source: Vaud 2025 Instructions (page pending verification)",
                                size=11, italic=True, color="#64748B",
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Text("M4", size=10, weight="w700", color="#92400E"),
                        bgcolor="#FEF3C7",
                        padding=ft.padding.symmetric(vertical=3, horizontal=8),
                        border_radius=10,
                    ),
                ],
                spacing=12,
            ),
            padding=14,
            bgcolor="#FFFFFF",
            border=ft.border.all(1, "#E2E8F0"),
            border_radius=10,
        )

    body = ft.Column(
        [
            ft.Text("Missing things", size=26, weight="w800", color="#0F172A"),
            ft.Text(
                "Deterministic completeness engine arrives in M4. Each finding "
                "below will surface as a card with a Vaud Instructions citation "
                "and a 'Provide info' CTA.",
                size=14, color="#475569",
            ),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.icons.INSIGHTS, color="#4F46E5"),
                        ft.Text(
                            f"You confirmed {confirmed_count} value(s). "
                            "M4 will compare them against the rule set below.",
                            size=12, color="#1E293B",
                        ),
                    ],
                    spacing=8,
                ),
                padding=10,
                bgcolor="#EEF2FF",
                border=ft.border.all(1, "#C7D2FE"),
                border_radius=8,
            ),
            ft.Container(height=6),
            *[rule_card(rid, title) for rid, title in _PLANNED_RULES],
            ft.Container(height=10),
            ft.Row(
                [
                    ft.OutlinedButton(
                        "Back",
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda _e: navigator.go(Screen.EXTRACTED),
                    ),
                    ft.ElevatedButton(
                        "Continue to mapping",
                        icon=ft.icons.ARROW_FORWARD,
                        bgcolor="#4F46E5",
                        color="white",
                        on_click=lambda _e: navigator.go(Screen.MAPPING),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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


__all__ = ["build_completeness_view"]
