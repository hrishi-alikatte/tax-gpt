"""Provider-agnostic model router.

Public API:
    generate_text(messages, purpose, *, temperature=0.0) -> str
    generate_json(messages, schema, purpose, *, temperature=0.0) -> dict
    embed_texts(texts) -> list[list[float]]

Routing is driven by `Purpose` and the active provider env (`MODEL_PROVIDER`).
Clients are instantiated lazily per call so that:
  - import is side-effect free,
  - missing env only fails when that provider is actually used,
  - tests can patch `_azure_client()` / `_groq_client()` cleanly.
"""
from __future__ import annotations

import json
from typing import Any, Iterable, Literal, Sequence

from TaxAI2025.core import config
from TaxAI2025.persistence import token_budget

Purpose = Literal[
    "rag_explanation",
    "document_extraction",
    "completeness_explanation",
    "hard_domain_reasoning",
    "demo_fallback",
]

Message = dict[str, str]  # {"role": "system|user|assistant", "content": "..."}


# ---------------------------------------------------------------------------
# Routing table: purpose -> (provider, deployment-resolver)
# ---------------------------------------------------------------------------

def _resolve_azure_deployment(purpose: Purpose) -> str:
    cfg = config.azure_config()
    if purpose == "rag_explanation":
        return cfg.deployment_rag
    if purpose == "completeness_explanation":
        return cfg.deployment_rag
    if purpose == "document_extraction":
        return cfg.deployment_extraction
    if purpose == "hard_domain_reasoning":
        if not cfg.deployment_reasoning:
            raise config.ConfigError(
                "AZURE_OPENAI_DEPLOYMENT_REASONING is not configured. "
                "Set it or pick another purpose."
            )
        return cfg.deployment_reasoning
    raise ValueError(f"Azure routing has no entry for purpose={purpose!r}")


def route(purpose: Purpose) -> dict[str, str]:
    """Return {'provider': 'azure'|'groq', 'deployment': '<name>'} for a purpose.

    Demo fallback is always Groq regardless of MODEL_PROVIDER.
    """
    if purpose == "demo_fallback":
        return {"provider": "groq", "deployment": config.groq_config().model}

    if config.MODEL_PROVIDER == "groq":
        return {"provider": "groq", "deployment": config.groq_config().model}

    if config.MODEL_PROVIDER == "azure":
        return {"provider": "azure", "deployment": _resolve_azure_deployment(purpose)}

    raise config.ConfigError(
        f"Unknown MODEL_PROVIDER={config.MODEL_PROVIDER!r}. Use 'azure' or 'groq'."
    )


# ---------------------------------------------------------------------------
# Lazy client factories
# ---------------------------------------------------------------------------

def _azure_client():  # pragma: no cover - exercised via patching in tests
    from openai import AzureOpenAI

    cfg = config.azure_config()
    return AzureOpenAI(
        api_key=cfg.api_key,
        azure_endpoint=cfg.endpoint,
        api_version=cfg.api_version,
    )


def _groq_client():  # pragma: no cover
    from groq import Groq

    return Groq(api_key=config.groq_config().api_key)


# ---------------------------------------------------------------------------
# generate_text
# ---------------------------------------------------------------------------

def generate_text(
    messages: Sequence[Message],
    purpose: Purpose,
    *,
    temperature: float = 0.0,
) -> str:
    routing = route(purpose)
    token_budget.assert_budget_available(purpose)
    input_chars = sum(len(m.get("content", "")) for m in messages)
    if routing["provider"] == "azure":
        client = _azure_client()
        resp = client.chat.completions.create(
            model=routing["deployment"],
            messages=list(messages),
            temperature=temperature,
        )
        text = _extract_text_from_chat(resp)
        token_budget.record_model_call(
            purpose, input_chars=input_chars, output_chars=len(text)
        )
        return text
    if routing["provider"] == "groq":
        client = _groq_client()
        resp = client.chat.completions.create(
            model=routing["deployment"],
            messages=list(messages),
            temperature=temperature,
        )
        text = _extract_text_from_chat(resp)
        token_budget.record_model_call(
            purpose, input_chars=input_chars, output_chars=len(text)
        )
        return text
    raise RuntimeError(f"Unhandled provider: {routing['provider']}")


# ---------------------------------------------------------------------------
# generate_json
# ---------------------------------------------------------------------------

def generate_json(
    messages: Sequence[Message],
    schema: dict[str, Any],
    purpose: Purpose,
    *,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Generate JSON constrained by `schema` (a JSON Schema dict).

    Azure path uses response_format=json_schema. Groq path uses json_object
    (looser; caller validates).
    """
    routing = route(purpose)
    token_budget.assert_budget_available(purpose)
    input_chars = sum(len(m.get("content", "")) for m in messages)
    if routing["provider"] == "azure":
        client = _azure_client()
        resp = client.chat.completions.create(
            model=routing["deployment"],
            messages=list(messages),
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.get("title", "Response"),
                    "schema": schema,
                    "strict": True,
                },
            },
        )
        text = _extract_text_from_chat(resp)
        token_budget.record_model_call(
            purpose, input_chars=input_chars, output_chars=len(text)
        )
        return json.loads(text)
    if routing["provider"] == "groq":
        client = _groq_client()
        resp = client.chat.completions.create(
            model=routing["deployment"],
            messages=list(messages),
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        text = _extract_text_from_chat(resp)
        token_budget.record_model_call(
            purpose, input_chars=input_chars, output_chars=len(text)
        )
        return json.loads(text)
    raise RuntimeError(f"Unhandled provider: {routing['provider']}")


# ---------------------------------------------------------------------------
# embed_texts
# ---------------------------------------------------------------------------

def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    token_budget.assert_budget_available("rag_explanation")
    text_list = list(texts)
    cfg = config.azure_config()
    client = _azure_client()
    resp = client.embeddings.create(
        model=cfg.embedding_deployment,
        input=text_list,
    )
    token_budget.record_model_call(
        "rag_explanation",
        input_chars=sum(len(t) for t in text_list),
        output_chars=0,
    )
    return [item.embedding for item in resp.data]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _extract_text_from_chat(resp: Any) -> str:
    """Pull text from an OpenAI/Groq chat-completion response.

    Tolerates the SDK object and a dict-like stub used in tests.
    """
    try:
        choice = resp.choices[0]  # type: ignore[index]
        message = choice.message  # type: ignore[attr-defined]
        return message.content  # type: ignore[attr-defined,no-any-return]
    except AttributeError:
        return resp["choices"][0]["message"]["content"]
