"""Test-wide fixtures.

We isolate every test from real env vars and from any real provider client.
No live network calls are allowed in this suite.
"""
from __future__ import annotations

import os
from typing import Iterator

import pytest


REQUIRED_ENV_FOR_AZURE = {
    "AZURE_OPENAI_API_KEY": "test-key",
    "AZURE_OPENAI_ENDPOINT": "https://test.example.com",
    "AZURE_OPENAI_API_VERSION": "2024-10-21",
    "AZURE_OPENAI_DEPLOYMENT_RAG": "gpt-5-4-mini-rag",
    "AZURE_OPENAI_DEPLOYMENT_EXTRACTION": "gpt-5-4-mini-extract",
    "AZURE_OPENAI_DEPLOYMENT_REASONING": "gpt-5-4-mini-reason",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-large",
    "AZURE_OPENAI_EMBEDDING_MODEL": "text-embedding-3-large",
    "EMBEDDING_DIMENSIONS": "3072",
    "VECTOR_SIMILARITY": "cosine",
    "MODEL_PROVIDER": "azure",
    "ACTIVE_TAX_YEAR": "2025",
    "ACTIVE_CANTON": "VD",
    "ACTIVE_RAG_CORPUS": "vd_2025",
}

REQUIRED_ENV_FOR_GROQ = {
    "GROQ_API_KEY": "test-groq-key",
    "GROQ_MODEL": "llama-3.3-70b-versatile",
}


def _clear_caches() -> None:
    """Clear cross-test caches that could leak state under reordering."""
    try:
        from TaxAI2025.rag import sources

        sources.active_source.cache_clear()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture
def azure_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for k, v in REQUIRED_ENV_FOR_AZURE.items():
        monkeypatch.setenv(k, v)
    # Reload the config module so its module-level constants pick up the new env.
    import importlib

    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)
    _clear_caches()
    yield
    importlib.reload(cfg)
    _clear_caches()


@pytest.fixture
def azure_and_groq_env(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    for k, v in REQUIRED_ENV_FOR_AZURE.items():
        monkeypatch.setenv(k, v)
    for k, v in REQUIRED_ENV_FOR_GROQ.items():
        monkeypatch.setenv(k, v)
    import importlib

    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)
    _clear_caches()
    yield
    importlib.reload(cfg)
    _clear_caches()


@pytest.fixture
def empty_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip every Azure/Groq variable so missing-env tests are deterministic."""
    for k in list(REQUIRED_ENV_FOR_AZURE.keys()) + list(REQUIRED_ENV_FOR_GROQ.keys()):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    import importlib

    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)
    _clear_caches()
    yield
    importlib.reload(cfg)
    _clear_caches()


@pytest.fixture(autouse=True)
def _block_openai(monkeypatch):
    """Robustly block all AI network calls by patching the SDK classes."""
    import sys
    from unittest.mock import MagicMock
    
    mock_instance = MagicMock()
    # Mock both OpenAI and Groq patterns. Return a string for content to avoid regex failures.
    mock_content = "Stubbed AI response [Vaud 2025 Instructions p.1]."
    mock_instance.chat.completions.create.return_value.choices[0].message.content = mock_content
    mock_instance.embeddings.create.return_value.data = [MagicMock(embedding=[0.1]*3072)]
    
    # Patch the constructors in the modules where they are imported
    # We patch them in model_router specifically as that's our gateway
    monkeypatch.setattr("TaxAI2025.ai.model_router._azure_client", lambda: mock_instance)
    monkeypatch.setattr("TaxAI2025.ai.model_router._groq_client", lambda: mock_instance)
    
    # ONLY patch global SDKs if they are already in sys.modules to avoid 
    # breaking "no-llm-import" tests that check sys.modules.
    if "openai" in sys.modules:
        import openai
        monkeypatch.setattr(openai, "AzureOpenAI", MagicMock(return_value=mock_instance))
    if "groq" in sys.modules:
        import groq
        monkeypatch.setattr(groq, "Groq", MagicMock(return_value=mock_instance))
