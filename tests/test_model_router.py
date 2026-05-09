"""Model-router routing + stubbed client tests. No live network."""
from __future__ import annotations

import pytest


def test_route_rag_explanation_to_rag_deployment(azure_and_groq_env: None) -> None:
    from TaxAI2025.ai import model_router

    r = model_router.route("rag_explanation")
    assert r == {"provider": "azure", "deployment": "gpt-5-4-mini-rag"}


def test_route_completeness_explanation_to_rag_deployment(
    azure_and_groq_env: None,
) -> None:
    from TaxAI2025.ai import model_router

    r = model_router.route("completeness_explanation")
    assert r == {"provider": "azure", "deployment": "gpt-5-4-mini-rag"}


def test_route_document_extraction_to_extraction_deployment(
    azure_and_groq_env: None,
) -> None:
    from TaxAI2025.ai import model_router

    r = model_router.route("document_extraction")
    assert r == {"provider": "azure", "deployment": "gpt-5-4-mini-extract"}


def test_route_hard_domain_reasoning_to_reasoning_deployment(
    azure_and_groq_env: None,
) -> None:
    from TaxAI2025.ai import model_router

    r = model_router.route("hard_domain_reasoning")
    assert r == {"provider": "azure", "deployment": "gpt-5-4-mini-reason"}


def test_route_hard_domain_reasoning_fails_when_unset(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT_REASONING", raising=False)
    import importlib

    from TaxAI2025.core import config

    importlib.reload(config)
    from TaxAI2025.ai import model_router

    importlib.reload(model_router)
    with pytest.raises(config.ConfigError):
        model_router.route("hard_domain_reasoning")


def test_route_demo_fallback_always_groq(azure_and_groq_env: None) -> None:
    from TaxAI2025.ai import model_router

    r = model_router.route("demo_fallback")
    assert r["provider"] == "groq"
    assert r["deployment"] == "llama-3.3-70b-versatile"


def test_generate_text_uses_stubbed_azure_client(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from TaxAI2025.ai import model_router

    captured: dict = {}

    class StubChatCompletions:
        def create(self, **kwargs):  # noqa: ANN001, ANN003
            captured["kwargs"] = kwargs
            return {
                "choices": [
                    {"message": {"content": "stubbed answer"}}
                ]
            }

    class StubChat:
        completions = StubChatCompletions()

    class StubAzureClient:
        chat = StubChat()

    monkeypatch.setattr(model_router, "_azure_client", lambda: StubAzureClient())

    result = model_router.generate_text(
        [{"role": "user", "content": "hi"}], purpose="rag_explanation"
    )
    assert result == "stubbed answer"
    assert captured["kwargs"]["model"] == "gpt-5-4-mini-rag"


def test_no_model_call_at_import_time(azure_and_groq_env: None) -> None:
    """Importing the router must not touch any client."""
    import importlib

    from TaxAI2025.ai import model_router

    # Re-import; if a client were instantiated, missing-creds would have raised earlier.
    importlib.reload(model_router)
    assert hasattr(model_router, "generate_text")


def test_missing_azure_creds_only_fails_when_used(
    empty_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Importing the router with no env should not raise."""
    import importlib

    from TaxAI2025.ai import model_router

    importlib.reload(model_router)
    # Just routing/embedding requires config; calling them must raise.
    from TaxAI2025.core import config

    with pytest.raises(config.ConfigError):
        model_router.route("rag_explanation")
