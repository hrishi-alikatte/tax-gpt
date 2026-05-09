"""Mapping view: read-only English ↔ French ↔ VaudTax-code ↔ value table.

Codes mirror DOMAIN_MODEL §4. Codes carrying `(?)` in the domain doc are
flagged here as `pending verification` so the demo doesn't leak unverified
guesses.
"""
from __future__ import annotations

from typing import Any

import flet as ft

from TaxAI2025.ui.components.footer import build_footer
from TaxAI2025.ui.navigation import Navigator, Screen
from TaxAI2025.ui.state import AppState


MAPPING_TABLE: list[tuple[str, str, str, str, bool]] = [
    ("salary.gross_annual_chf", "Gross annual salary", "Salaire brut annuel", "100", True),
    ("salary.net_annual_chf", "Net annual salary", "Salaire net annuel", "—", False),
    ("salary.ahv_iv_eo_chf", "AHV/IV/EO contributions", "Cotisations AVS/AI/APG", "—", False),
    ("salary.unemployment_chf", "Unemployment insurance", "Assurance chômage", "—", False),
    ("salary.pension_2nd_pillar_chf", "2nd pillar contributions", "Cotisations LPP", "—", False),
    ("health_insurance.annual_premium_chf", "Health insurance premium (annual)", "Prime d'assurance maladie", "320", True),
    ("childcare.total_paid_chf", "Childcare expenses", "Frais de garde des enfants", "350", True),
    ("pillar_3a.annual_contribution_chf", "Pillar 3a contribution", "Cotisation 3e pilier A", "380", True),
    ("transport.annual_cost_chf", "Commute / transport cost", "Frais de transport", "140", True),
    ("meal_allowance.method", "Meal allowance method", "Frais de repas", "150", True),
    ("bank.year_end_balance_chf", "Bank balance 31 December", "Solde bancaire au 31 décembre", "800", True),
    ("bank.annual_interest_chf", "Interest income", "Intérêts perçus", "810", True),
]


def _format_value(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def build_mapping_view(state: AppState, navigator: Navigator) -> ft.Control:
    by_field = {f.canonical_field: f for f in state.confirmed_facts()}

    def cell(text: str, weight: str = "w400", color: str = "#1E293B") -> ft.Control:
        return ft.Container(
            content=ft.Text(text, size=12, weight=weight, color=color, selectable=True),
            padding=ft.padding.symmetric(vertical=10, horizontal=10),
            expand=True,
        )

    header = ft.Container(
        content=ft.Row(
            [
                cell("Canonical field", "w800", "#0F172A"),
                cell("English label", "w800", "#0F172A"),
                cell("French label", "w800", "#0F172A"),
                cell("VaudTax code", "w800", "#0F172A"),
                cell("Confirmed value", "w800", "#0F172A"),
            ],
        ),
        bgcolor="#F1F5F9",
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=ft.border_radius.only(top_left=10, top_right=10),
    )

    rows: list[ft.Control] = []
    for canonical, en, fr, code, code_verified in MAPPING_TABLE:
        fact = by_field.get(canonical)
        value_text = _format_value(fact.value) if fact else "—"
        code_label = code if (code == "—" or not code_verified) else code
        code_suffix = "" if (code == "—" or code_verified) else " (pending)"

        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        cell(canonical, "w600", "#334155"),
                        cell(en),
                        cell(fr),
                        cell(f"{code_label}{code_suffix}"),
                        cell(value_text, "w700", "#0F172A"),
                    ],
                ),
                bgcolor="#FFFFFF" if fact is None else "#F0FDF4",
                border=ft.border.only(
                    left=ft.BorderSide(1, "#E2E8F0"),
                    right=ft.BorderSide(1, "#E2E8F0"),
                    bottom=ft.BorderSide(1, "#E2E8F0"),
                ),
            )
        )

    body = ft.Column(
        [
            ft.Text("VaudTax mapping", size=26, weight="w800", color="#0F172A"),
            ft.Text(
                "Read-only. Each English label maps to a French VaudTax label "
                "and a code from the official form. Codes flagged 'pending' are "
                "open questions in DOMAIN_MODEL.md §4.",
                size=14, color="#475569",
            ),
            ft.Container(height=6),
            ft.Column([header, *rows], spacing=0),
            ft.Container(height=10),
            ft.Row(
                [
                    ft.OutlinedButton(
                        "Back",
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda _e: navigator.go(Screen.EXTRACTED),
                    ),
                    ft.ElevatedButton(
                        "Continue to explain",
                        icon=ft.icons.ARROW_FORWARD,
                        bgcolor="#4F46E5",
                        color="white",
                        on_click=lambda _e: navigator.go(Screen.EXPLAIN),
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


__all__ = ["build_mapping_view", "MAPPING_TABLE"]
