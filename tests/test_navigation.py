"""Navigator transitions and on_change callback firing."""
from __future__ import annotations

from TaxAI2025.ui.navigation import Navigator, Screen, SCREEN_ORDER


def test_navigator_default_is_intake() -> None:
    nav = Navigator()
    assert nav.current is Screen.INTAKE


def test_go_changes_current_and_appends_history() -> None:
    nav = Navigator()
    nav.go(Screen.UPLOAD)
    assert nav.current is Screen.UPLOAD
    assert nav.history == [Screen.INTAKE]


def test_go_to_same_screen_is_noop() -> None:
    seen: list[Screen] = []
    nav = Navigator(on_change=seen.append)
    nav.go(Screen.INTAKE)
    assert seen == []
    assert nav.history == []


def test_on_change_fires() -> None:
    seen: list[Screen] = []
    nav = Navigator(on_change=seen.append)
    nav.go(Screen.UPLOAD)
    nav.go(Screen.EXTRACTED)
    assert seen == [Screen.UPLOAD, Screen.EXTRACTED]


def test_go_next_walks_screen_order() -> None:
    nav = Navigator()
    for expected in SCREEN_ORDER[1:]:
        actual = nav.go_next()
        assert actual is expected
        assert nav.current is expected


def test_go_next_returns_none_on_last_screen() -> None:
    nav = Navigator(current=SCREEN_ORDER[-1])
    assert nav.go_next() is None
    assert nav.current is SCREEN_ORDER[-1]


def test_screen_string_values_match_literals() -> None:
    assert Screen.INTAKE.value == "intake"
    assert Screen.UPLOAD.value == "upload"
    assert Screen.EXTRACTED.value == "extracted"
    assert Screen.INTERVIEW.value == "interview"
    assert Screen.COMPLETENESS.value == "completeness"
    assert Screen.MAPPING.value == "mapping"
    assert Screen.EXPLAIN.value == "explain"


def test_extracted_values_continue_to_interview_not_mapping() -> None:
    from TaxAI2025.ui.views.extracted_view import NEXT_AFTER_EXTRACTION

    assert NEXT_AFTER_EXTRACTION is Screen.INTERVIEW
