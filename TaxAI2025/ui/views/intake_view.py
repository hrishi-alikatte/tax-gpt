"""Intake view: collect minimal Vaud-only profile (DOMAIN_MODEL §2).

Pure form. No AI. When DEMO_MODE=replay we pre-fill with Sarah's
synthetic profile from `demo/scenarios/expat_c_permit_basic/profile.json`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import flet as ft

from TaxAI2025.core import config
from TaxAI2025.ui.components.footer import build_footer
from TaxAI2025.ui.navigation import Navigator, Screen
from TaxAI2025.ui.state import AppState, UserProfile


def _scenario_profile_path(scenario: str | None = None) -> Path:
    name = scenario or "expat_c_permit_basic"
    return config.REPO_ROOT / "demo" / "scenarios" / name / "profile.json"


def load_replay_profile(scenario: str | None = None) -> UserProfile | None:
    path = _scenario_profile_path(scenario)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    cleaned = {k: v for k, v in raw.items() if not k.startswith("_") and k != "scenario_id" and k != "synthetic"}
    try:
        return UserProfile(**cleaned)
    except Exception:  # noqa: BLE001
        return None


def build_intake_view(state: AppState, navigator: Navigator) -> ft.Control:
    if state.profile is None and config.DEMO_MODE == "replay":
        prefilled = load_replay_profile()
        if prefilled is not None:
            state.profile = prefilled

    profile = state.profile or UserProfile()

    first_name = ft.TextField(
        label="First name",
        value=profile.first_name or "",
        width=280,
    )
    marital_status = ft.Dropdown(
        label="Marital status",
        value=profile.marital_status,
        width=280,
        options=[
            ft.dropdown.Option("single", "Single"),
            ft.dropdown.Option("married", "Married"),
            ft.dropdown.Option("divorced", "Divorced"),
            ft.dropdown.Option("widowed", "Widowed"),
            ft.dropdown.Option("registered_partnership", "Registered partnership"),
        ],
    )
    spouse_works = ft.Dropdown(
        label="Spouse works",
        width=280,
        value=(
            "yes" if profile.spouse_works is True
            else "no" if profile.spouse_works is False
            else None
        ),
        options=[
            ft.dropdown.Option("yes", "Yes"),
            ft.dropdown.Option("no", "No"),
        ],
    )
    children_count = ft.TextField(
        label="Number of children",
        value=str(profile.children_count or 0),
        width=180,
    )
    children_ages = ft.TextField(
        label="Children ages (comma-separated)",
        value=", ".join(str(a) for a in profile.children_ages),
        width=280,
    )
    commune = ft.TextField(
        label="Commune of residence (Vaud)",
        value=profile.commune_of_residence or "",
        width=280,
    )
    employer = ft.TextField(
        label="Employer name",
        value=profile.employer_name or "",
        width=280,
    )
    work_commune = ft.TextField(
        label="Work commune",
        value=profile.work_commune or "",
        width=280,
    )
    tax_year = ft.TextField(
        label="Tax year",
        value=str(profile.tax_year),
        width=180,
    )
    canteen = ft.Checkbox(
        label="I have a workplace canteen / employer-provided meals",
        value=profile.has_workplace_canteen is True,
    )

    error_text = ft.Text("", color="#B91C1C", size=13)
    permit_banner = ft.Text(
        "Permit type: C (settled). MVP is C-permit only.",
        size=12, italic=True, color="#64748B",
    )

    def _parse_children_ages(raw: str) -> list[int]:
        if not raw.strip():
            return []
        out: list[int] = []
        for tok in raw.split(","):
            tok = tok.strip()
            if not tok:
                continue
            out.append(int(tok))
        return out

    def on_continue(_e: Any) -> None:
        try:
            kids = int(children_count.value or "0")
            ages = _parse_children_ages(children_ages.value or "")
        except ValueError:
            error_text.value = "Children count and ages must be integers."
            error_text.update()
            return
        if marital_status.value is None:
            error_text.value = "Marital status is required."
            error_text.update()
            return
        if not commune.value or not commune.value.strip():
            error_text.value = "Commune of residence is required."
            error_text.update()
            return
        try:
            year = int(tax_year.value or "2024")
        except ValueError:
            error_text.value = "Tax year must be an integer."
            error_text.update()
            return

        new_profile = UserProfile(
            first_name=(first_name.value or "").strip() or None,
            marital_status=marital_status.value,  # type: ignore[arg-type]
            spouse_works=(
                True if spouse_works.value == "yes"
                else False if spouse_works.value == "no"
                else None
            ),
            children_count=kids,
            children_ages=ages,
            commune_of_residence=(commune.value or "").strip() or None,
            employer_name=(employer.value or "").strip() or None,
            work_commune=(work_commune.value or "").strip() or None,
            tax_year=year,
            has_workplace_canteen=bool(canteen.value),
        )
        state.set_profile(new_profile)
        navigator.go(Screen.UPLOAD)

    continue_btn = ft.ElevatedButton(
        "Continue",
        icon=ft.icons.ARROW_FORWARD,
        bgcolor="#4F46E5",
        color="white",
        on_click=on_continue,
    )

    body = ft.Column(
        [
            ft.Text("Tell us about you", size=26, weight="w800", color="#0F172A"),
            ft.Text(
                "Vaud-only, C-permit, employed. We use this to detect what's "
                "missing from your filing.",
                size=14, color="#475569",
            ),
            permit_banner,
            ft.Container(height=10),
            ft.Row(
                [first_name, marital_status, spouse_works],
                wrap=True, spacing=20, run_spacing=12,
            ),
            ft.Row(
                [children_count, children_ages],
                wrap=True, spacing=20, run_spacing=12,
            ),
            ft.Row(
                [commune, work_commune, employer],
                wrap=True, spacing=20, run_spacing=12,
            ),
            ft.Row([tax_year], spacing=20),
            ft.Row([canteen], spacing=20),
            ft.Container(height=10),
            error_text,
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


__all__ = ["build_intake_view", "load_replay_profile"]
