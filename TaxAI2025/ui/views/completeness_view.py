"""Completeness view — renders deterministic engine output.

`completeness.engine.evaluate(profile, facts)` is called fresh every
time the screen mounts. The engine is pure (no LLM) so this is cheap
and safe to recompute.
"""
from __future__ import annotations

import flet as ft

from TaxAI2025.completeness import Finding, evaluate
from TaxAI2025.completeness.schema import Severity
from TaxAI2025.ui.components.citation_chip import open_pdf_at_page
from TaxAI2025.ui.components.footer import build_footer
from TaxAI2025.ui.navigation import Navigator, Screen
from TaxAI2025.ui.state import AppState, UserProfile


SEVERITY_LABELS: dict[Severity, str] = {
    "blocker": "Blockers",
    "likely_missing": "Likely missing",
    "nice_to_have": "Nice to have",
}

SEVERITY_BADGE_COLORS: dict[Severity, tuple[str, str]] = {
    "blocker": ("#FEE2E2", "#991B1B"),
    "likely_missing": ("#FEF3C7", "#92400E"),
    "nice_to_have": ("#E0E7FF", "#3730A3"),
}


def _citation_text(finding: Finding) -> str:
    if finding.pdf_page is not None:
        return f"[Vaud 2025 Instructions p.{finding.pdf_page}]"
    return "[Vaud 2025 Instructions, page pending verification]"


def _severity_badge(severity: Severity) -> ft.Control:
    bg, fg = SEVERITY_BADGE_COLORS[severity]
    return ft.Container(
        content=ft.Text(
            severity.replace("_", " ").upper(),
            size=10, weight="w700", color=fg,
        ),
        bgcolor=bg,
        padding=ft.padding.symmetric(vertical=3, horizontal=8),
        border_radius=10,
    )


def _asks_for_chips(asks_for: list[str]) -> ft.Control:
    chips = [
        ft.Container(
            content=ft.Text(field, size=11, color="#1E293B"),
            bgcolor="#F1F5F9",
            padding=ft.padding.symmetric(vertical=3, horizontal=8),
            border_radius=8,
            border=ft.border.all(1, "#E2E8F0"),
        )
        for field in asks_for
    ]
    return ft.Row(chips, spacing=6, wrap=True)


def _citation_chip(finding: Finding, state: AppState) -> ft.Control:
    page = finding.pdf_page

    def _on_click(_e) -> None:  # noqa: ANN001
        if page is None:
            return
        open_pdf_at_page(page)
        state.record("navigated", target="pdf", pdf_page=page, rule_id=finding.rule_id)

    chip = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.icons.MENU_BOOK_OUTLINED, size=12, color="#3730A3"),
                ft.Text(_citation_text(finding), size=11, color="#3730A3"),
            ],
            spacing=4,
            tight=True,
        ),
        bgcolor="#EEF2FF",
        padding=ft.padding.symmetric(vertical=4, horizontal=8),
        border_radius=8,
        border=ft.border.all(1, "#C7D2FE"),
        tooltip=(
            f"Open Vaud 2025 Instructions at p.{page} in your PDF viewer"
            if page is not None
            else "Page pending verification"
        ),
    )
    if page is not None:
        chip.on_click = _on_click
        chip.ink = True
    return chip


def _finding_card(finding: Finding, state: AppState) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    finding.rule_id,
                                    size=11, weight="w700", color="#4F46E5",
                                ),
                                ft.Text(
                                    finding.title_en,
                                    size=15, weight="w700", color="#0F172A",
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        _severity_badge(finding.severity),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Text(finding.message_en, size=13, color="#334155"),
                ft.Row(
                    [
                        ft.Text("Asks for:", size=11, color="#64748B"),
                        _asks_for_chips(finding.asks_for),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                _citation_chip(finding, state),
            ],
            spacing=8,
        ),
        padding=14,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=10,
    )


def _section(title: str, findings: list[Finding], state: AppState) -> ft.Control:
    return ft.Column(
        [
            ft.Text(title, size=15, weight="w700", color="#475569"),
            *[_finding_card(f, state) for f in findings],
        ],
        spacing=10,
    )


def _group_by_severity(findings: list[Finding]) -> dict[Severity, list[Finding]]:
    grouped: dict[Severity, list[Finding]] = {
        "blocker": [],
        "likely_missing": [],
        "nice_to_have": [],
    }
    for f in findings:
        grouped[f.severity].append(f)
    return grouped


def build_completeness_view(state: AppState, navigator: Navigator) -> ft.Control:
    profile = state.profile or UserProfile()
    findings = evaluate(profile, state.facts)
    state.findings = list(findings)

    confirmed_count = sum(1 for f in state.facts if f.confirmed_by_user)
    grouped = _group_by_severity(findings)

    sections: list[ft.Control] = []
    for severity in ("blocker", "likely_missing", "nice_to_have"):
        bucket = grouped[severity]  # type: ignore[index]
        if bucket:
            sections.append(_section(SEVERITY_LABELS[severity], bucket, state))  # type: ignore[index]

    if not findings:
        sections.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.icons.CHECK_CIRCLE, color="#16A34A"),
                        ft.Text(
                            "Nothing obviously missing. Continue to the "
                            "VaudTax mapping view.",
                            size=13, color="#1E293B",
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

    body = ft.Column(
        [
            ft.Text("Missing things", size=26, weight="w800", color="#0F172A"),
            ft.Text(
                "Deterministic completeness engine. Each finding compares "
                "your profile and confirmed values against a rule cited in "
                "the Vaud 2025 Instructions.",
                size=14, color="#475569",
            ),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.icons.INSIGHTS, color="#4F46E5"),
                        ft.Text(
                            f"You confirmed {confirmed_count} value(s). "
                            f"Engine surfaced {len(findings)} finding(s).",
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
            *sections,
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
