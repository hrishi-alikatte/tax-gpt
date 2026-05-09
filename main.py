"""VaudTaxAI desktop entrypoint (M3).

Replaces the legacy chat-only dashboard with the six-screen confirmation
flow. No agent/RAG calls happen at startup — every AI call is triggered
by a user click in the upload or explain view.
"""
from __future__ import annotations

import os

import flet as ft

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from TaxAI2025.core import config
from TaxAI2025.ui.components.footer import DISCLAIMER_TEXT
from TaxAI2025.ui.navigation import (
    Navigator,
    Screen,
    SCREEN_LABELS,
    SCREEN_ORDER,
)
from TaxAI2025.ui.state import AppState
from TaxAI2025.ui.views.completeness_view import build_completeness_view
from TaxAI2025.ui.views.explain_view import build_explain_view
from TaxAI2025.ui.views.extracted_view import build_extracted_view
from TaxAI2025.ui.views.interview_view import build_interview_view
from TaxAI2025.ui.views.intake_view import build_intake_view
from TaxAI2025.ui.views.mapping_view import build_mapping_view
from TaxAI2025.ui.views.upload_view import build_upload_view


def _render_left_rail(
    navigator: Navigator,
    state: AppState,
) -> ft.Control:
    is_replay = config.DEMO_MODE == "replay"

    def rail_item(screen: Screen) -> ft.Control:
        active = screen == navigator.current
        bg = "#EEF2FF" if active else "#FFFFFF"
        fg = "#4F46E5" if active else "#1E293B"
        border = ft.border.all(1, "#C7D2FE") if active else ft.border.all(1, "#E2E8F0")

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=4, height=22,
                        bgcolor="#4F46E5" if active else "#E2E8F0",
                        border_radius=2,
                    ),
                    ft.Text(
                        SCREEN_LABELS[screen],
                        size=13,
                        weight="w700" if active else "w500",
                        color=fg,
                    ),
                ],
                spacing=10,
            ),
            padding=ft.padding.symmetric(vertical=10, horizontal=10),
            bgcolor=bg,
            border=border,
            border_radius=8,
            on_click=lambda _e, s=screen: navigator.go(s),
            ink=True,
        )

    demo_banner: ft.Control
    if is_replay:
        demo_banner = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.PLAY_CIRCLE_OUTLINE, color="#92400E", size=16),
                    ft.Text(
                        "DEMO MODE: replay",
                        size=12, weight="w800", color="#92400E",
                    ),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(vertical=6, horizontal=10),
            bgcolor="#FEF3C7",
            border=ft.border.all(1, "#FCD34D"),
            border_radius=6,
        )
    else:
        demo_banner = ft.Container(
            content=ft.Text(
                "Live mode",
                size=11, italic=True, color="#94A3B8",
            ),
            padding=ft.padding.symmetric(vertical=6, horizontal=10),
        )

    confirmed_count = sum(1 for f in state.facts if f.confirmed_by_user)
    profile_summary: ft.Control
    if state.profile is None:
        profile_summary = ft.Text(
            "Profile not yet captured.",
            size=12, italic=True, color="#94A3B8",
        )
    else:
        p = state.profile
        profile_summary = ft.Column(
            [
                ft.Text(
                    f"{p.first_name or '—'} • {p.permit_type}",
                    size=12, weight="w700", color="#0F172A",
                ),
                ft.Text(
                    f"{p.commune_of_residence or '—'} → {p.work_commune or '—'}",
                    size=11, color="#475569",
                ),
                ft.Text(
                    f"Children: {p.children_count}, "
                    f"facts confirmed: {confirmed_count}/{len(state.facts)}",
                    size=11, color="#475569",
                ),
            ],
            spacing=2,
        )

    return ft.Container(
        width=260,
        bgcolor="#FFFFFF",
        padding=20,
        border=ft.border.only(right=ft.BorderSide(1, "#E2E8F0")),
        content=ft.Column(
            [
                ft.Text(
                    "VaudTaxAI",
                    size=22, weight="w900", color="#0F172A",
                ),
                ft.Text(
                    "Vaud-only • C-permit • EN",
                    size=11, italic=True, color="#64748B",
                ),
                demo_banner,
                ft.Divider(color="#E2E8F0", height=20),
                ft.Column(
                    [rail_item(s) for s in SCREEN_ORDER],
                    spacing=6,
                ),
                ft.Divider(color="#E2E8F0", height=20),
                ft.Text("Profile", size=11, weight="w800", color="#64748B"),
                profile_summary,
                ft.Container(expand=True),
                ft.Text(
                    DISCLAIMER_TEXT,
                    size=10, italic=True, color="#94A3B8",
                ),
            ],
            spacing=10,
            expand=True,
        ),
    )


def main(page: ft.Page) -> None:
    page.title = "VaudTaxAI — Vaud Tax Copilot"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F8FAFC"
    page.window_width = 1200
    page.window_height = 820
    page.padding = 0

    state = AppState()
    navigator = Navigator(current=Screen.INTAKE)

    content_container = ft.Container(expand=True)
    rail_container = ft.Container()

    def view_for(screen: Screen) -> ft.Control:
        if screen == Screen.INTAKE:
            return build_intake_view(state, navigator)
        if screen == Screen.UPLOAD:
            return build_upload_view(state, navigator, page)
        if screen == Screen.EXTRACTED:
            return build_extracted_view(state, navigator, page)
        if screen == Screen.INTERVIEW:
            return build_interview_view(state, navigator, page)
        if screen == Screen.COMPLETENESS:
            return build_completeness_view(state, navigator)
        if screen == Screen.MAPPING:
            return build_mapping_view(state, navigator)
        if screen == Screen.EXPLAIN:
            return build_explain_view(state, navigator, page)
        return ft.Text(f"Unknown screen: {screen}")

    def render() -> None:
        content_container.content = view_for(navigator.current)
        rail_container.content = _render_left_rail(navigator, state)
        page.update()

    def on_change(target: Screen) -> None:
        state.record("navigated", screen=target.value)
        render()

    navigator.on_change = on_change

    rail_container.content = _render_left_rail(navigator, state)
    content_container.content = view_for(navigator.current)

    page.add(
        ft.Row(
            [rail_container, content_container],
            spacing=0,
            expand=True,
        )
    )

    if config.DEMO_MODE == "replay":
        print("DEMO MODE: replay  — extraction will load canned facts.")
    else:
        print("Live mode — extraction and RAG will hit the configured providers.")


def cloud_run_port() -> int | None:
    """Return the Cloud Run port when the app is running as a web service."""
    value = os.environ.get("PORT")
    if value is None or not value.strip():
        return None
    return int(value)


def app_run_kwargs() -> dict[str, object]:
    """Build Flet startup kwargs for local desktop or Cloud Run web mode."""
    port = cloud_run_port()
    if port is None:
        return {"target": main}
    return {
        "target": main,
        "view": ft.AppView.WEB_BROWSER,
        "host": "0.0.0.0",
        "port": port,
    }


def run_app() -> None:
    ft.app(**app_run_kwargs())


if __name__ == "__main__":
    run_app()
