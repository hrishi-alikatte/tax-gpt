"""DEMO_MODE=replay should prefill the intake form with Sarah's profile."""
from __future__ import annotations

import importlib

import pytest


def _activate_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "replay")
    monkeypatch.setenv("DEMO_SCENARIO", "expat_c_permit_basic")
    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)


def test_load_replay_profile_returns_sarah(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _activate_replay(monkeypatch)
    from TaxAI2025.ui.views.intake_view import load_replay_profile

    profile = load_replay_profile()
    assert profile is not None
    assert profile.first_name == "Sarah"
    assert profile.marital_status == "married"
    assert profile.children_count == 1
    assert profile.commune_of_residence == "Lausanne"
    assert profile.work_commune == "Renens"
    assert profile.permit_type == "C"


def test_load_replay_profile_returns_none_for_unknown_scenario(
    azure_env: None,
) -> None:
    from TaxAI2025.ui.views.intake_view import load_replay_profile

    assert load_replay_profile("does-not-exist") is None
