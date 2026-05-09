"""Lazy-import tripwires.

Mirror of test_no_model_call_at_import_time and the chromadb import test:
heavy SDKs (pdfplumber, openai client, etc.) must not load at module import.
"""
from __future__ import annotations

import sys

import pytest


def _purge(module_prefix: str) -> None:
    for name in list(sys.modules.keys()):
        if name == module_prefix or name.startswith(module_prefix + "."):
            sys.modules.pop(name, None)


def test_extraction_package_does_not_import_pdfplumber(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sys.modules.pop("pdfplumber", None)
    _purge("TaxAI2025.extraction")

    import TaxAI2025.extraction  # noqa: F401

    assert "pdfplumber" not in sys.modules


def test_classify_module_does_not_import_pdfplumber_at_load(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sys.modules.pop("pdfplumber", None)
    _purge("TaxAI2025.extraction")

    from TaxAI2025.extraction import classify  # noqa: F401

    assert "pdfplumber" not in sys.modules


def test_ocr_module_does_not_import_pdfplumber_at_load(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sys.modules.pop("pdfplumber", None)
    _purge("TaxAI2025.extraction")

    from TaxAI2025.extraction import ocr  # noqa: F401

    assert "pdfplumber" not in sys.modules


def test_extract_module_does_not_import_model_router_clients_at_load(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sys.modules.pop("openai", None)
    _purge("TaxAI2025.extraction")

    from TaxAI2025.extraction import extract  # noqa: F401

    assert "openai" not in sys.modules


def test_extract_from_upload_function_is_callable_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public entrypoint must import without requiring env vars."""
    for k in [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT_RAG",
        "AZURE_OPENAI_DEPLOYMENT_EXTRACTION",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "GROQ_API_KEY",
    ]:
        monkeypatch.delenv(k, raising=False)
    _purge("TaxAI2025.extraction")

    from TaxAI2025.extraction import extract_from_upload

    assert callable(extract_from_upload)
