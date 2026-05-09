"""Render a `RagCitation` as a clickable chip.

If the chip is clicked we fire `on_click(citation)` so the explain view
can decide whether to open a PDF preview, a URL, or just log the click.
We never hide the page reference — even when no click handler is wired,
the chip still shows the citation token.
"""
from __future__ import annotations

from typing import Callable

import flet as ft

from TaxAI2025.rag.schema import RagCitation


def build_citation_chip(
    citation: RagCitation,
    on_click: Callable[[RagCitation], None] | None = None,
) -> ft.Control:
    tooltip_lines = [citation.source_title]
    if citation.section_title:
        tooltip_lines.append(citation.section_title)
    if citation.pdf_page is not None:
        tooltip_lines.append(f"PDF page {citation.pdf_page}")

    chip = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.icons.MENU_BOOK_OUTLINED, size=14, color="#4F46E5"),
                ft.Text(
                    citation.token,
                    size=12,
                    weight="w600",
                    color="#1E293B",
                ),
            ],
            spacing=6,
            tight=True,
        ),
        padding=ft.padding.symmetric(vertical=6, horizontal=10),
        bgcolor="#EEF2FF",
        border=ft.border.all(1, "#C7D2FE"),
        border_radius=20,
        tooltip=" — ".join(tooltip_lines),
    )

    if on_click is not None:
        chip.on_click = lambda _e, c=citation: on_click(c)
        chip.ink = True

    return chip


__all__ = ["build_citation_chip"]
