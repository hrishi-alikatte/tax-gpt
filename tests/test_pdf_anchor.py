"""open_pdf_at_page must never raise and must no-op on bad input.

Real `webbrowser.open` is monkeypatched so tests don't pop a browser tab.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def test_open_pdf_at_page_returns_false_for_none(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from TaxAI2025.ui.components import citation_chip

    monkeypatch.setattr(citation_chip, "webbrowser", MagicMock())
    assert citation_chip.open_pdf_at_page(None) is False
    assert citation_chip.open_pdf_at_page(0) is False
    assert citation_chip.open_pdf_at_page(-3) is False


def test_open_pdf_at_page_returns_false_when_corpus_unresolvable(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """active_corpus_path() raises -> handler returns False (never crashes UI)."""
    from TaxAI2025.core import config
    from TaxAI2025.ui.components import citation_chip

    monkeypatch.setattr(citation_chip, "webbrowser", MagicMock())

    def _raise() -> None:
        raise config.ConfigError("corpus missing")

    monkeypatch.setattr(citation_chip.config, "active_corpus_path", _raise)
    assert citation_chip.open_pdf_at_page(42) is False


def test_open_pdf_at_page_invokes_browser_with_page_anchor(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from TaxAI2025.ui.components import citation_chip

    fake_browser = MagicMock()
    monkeypatch.setattr(citation_chip, "webbrowser", fake_browser)

    fake_path = MagicMock()
    fake_path.resolve.return_value = "/abs/data/official/vd_2025.pdf"
    monkeypatch.setattr(
        citation_chip.config, "active_corpus_path", lambda: fake_path
    )

    assert citation_chip.open_pdf_at_page(28) is True
    fake_browser.open.assert_called_once()
    args, _ = fake_browser.open.call_args
    assert args[0].endswith("vd_2025.pdf#page=28")


def test_open_pdf_at_page_swallows_browser_failures(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A misconfigured viewer must not crash the UI."""
    from TaxAI2025.ui.components import citation_chip

    fake_browser = MagicMock()
    fake_browser.open.side_effect = OSError("no display")
    monkeypatch.setattr(citation_chip, "webbrowser", fake_browser)

    fake_path = MagicMock()
    fake_path.resolve.return_value = "/abs/data/official/vd_2025.pdf"
    monkeypatch.setattr(
        citation_chip.config, "active_corpus_path", lambda: fake_path
    )

    assert citation_chip.open_pdf_at_page(28) is False
