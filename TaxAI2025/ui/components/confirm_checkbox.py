"""Per-field confirm checkbox with a confidence badge.

The checkbox starts unchecked. Toggling it calls `on_toggle(checked)` so
the parent view can flip `state.confirm_fact` / `state.unconfirm_fact`.
"""
from __future__ import annotations

from typing import Callable

import flet as ft


def confidence_badge(confidence: float | None) -> ft.Control:
    if confidence is None:
        label, bg, fg = "no score", "#E2E8F0", "#475569"
    elif confidence >= 0.9:
        label, bg, fg = f"high ({confidence:.2f})", "#DCFCE7", "#166534"
    elif confidence >= 0.7:
        label, bg, fg = f"medium ({confidence:.2f})", "#FEF3C7", "#92400E"
    else:
        label, bg, fg = f"low ({confidence:.2f})", "#FEE2E2", "#991B1B"

    return ft.Container(
        content=ft.Text(label, size=11, weight="w600", color=fg),
        padding=ft.padding.symmetric(vertical=3, horizontal=8),
        bgcolor=bg,
        border_radius=10,
    )


def build_confirm_checkbox(
    *,
    initial: bool = False,
    on_toggle: Callable[[bool], None],
    label: str = "Confirm",
) -> ft.Checkbox:
    def _handle_change(e: ft.ControlEvent) -> None:
        on_toggle(bool(e.control.value))

    return ft.Checkbox(
        value=initial,
        label=label,
        on_change=_handle_change,
        check_color="#FFFFFF",
        fill_color="#4F46E5",
    )


__all__ = ["build_confirm_checkbox", "confidence_badge"]
