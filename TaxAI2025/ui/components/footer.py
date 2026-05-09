"""Disclaimer footer rendered on every screen.

Wording is mandated by CLAUDE.md §2 + §5 + §11 — informational only,
never legal advice.
"""
from __future__ import annotations

import flet as ft


DISCLAIMER_TEXT = (
    "Informational only — consult an accredited fiduciary in Vaud for "
    "filing decisions. Privacy: anonymous session data is intended for "
    "30-day retention and can be wiped on request."
)


def build_footer() -> ft.Control:
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.icons.INFO_OUTLINE, size=14, color="#64748B"),
                ft.Text(
                    DISCLAIMER_TEXT,
                    size=12,
                    italic=True,
                    color="#64748B",
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(vertical=10, horizontal=20),
        bgcolor="#F1F5F9",
        border=ft.border.only(top=ft.BorderSide(1, "#E2E8F0")),
    )


__all__ = ["DISCLAIMER_TEXT", "build_footer"]
