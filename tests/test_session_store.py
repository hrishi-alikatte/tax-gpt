"""SessionStore and token-budget guard tests."""
from __future__ import annotations

import pytest


def test_in_memory_session_store_create_get_save_wipe() -> None:
    from TaxAI2025.persistence import InMemorySessionStore, SessionSnapshot

    store = InMemorySessionStore()
    snapshot = store.create("11111111-1111-1111-1111-111111111111")
    assert store.get(snapshot.session_uuid) is not None

    updated = SessionSnapshot(
        session_uuid=snapshot.session_uuid,
        profile={"first_name": "Alex"},
    )
    store.save(updated)
    assert store.get(snapshot.session_uuid).profile == {"first_name": "Alex"}  # type: ignore[union-attr]
    assert store.wipe(snapshot.session_uuid) is True
    assert store.get(snapshot.session_uuid) is None


def test_token_budget_blocks_when_cap_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    from TaxAI2025.persistence import token_budget

    token_budget.reset_budget_state()
    monkeypatch.setenv("VAUDTAX_SESSION_UUID", "s-1")
    monkeypatch.setenv("VAUDTAX_MONTHLY_TOKEN_BUDGET_CHF", "0.000001")
    token_budget.record_model_call(
        "document_extraction",
        input_chars=10_000,
        output_chars=10_000,
    )
    with pytest.raises(token_budget.TokenBudgetExceeded):
        token_budget.assert_budget_available("document_extraction")
    token_budget.reset_budget_state()


def test_model_router_records_budget_for_stubbed_text_call(
    azure_and_groq_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from TaxAI2025.ai import model_router
    from TaxAI2025.persistence import token_budget

    token_budget.reset_budget_state()
    monkeypatch.setenv("VAUDTAX_SESSION_UUID", "router-test")

    class StubChatCompletions:
        def create(self, **kwargs):  # noqa: ANN001, ANN003
            return {"choices": [{"message": {"content": "stubbed answer"}}]}

    class StubChat:
        completions = StubChatCompletions()

    class StubAzureClient:
        chat = StubChat()

    monkeypatch.setattr(model_router, "_azure_client", lambda: StubAzureClient())
    assert model_router.generate_text(
        [{"role": "user", "content": "hi"}],
        purpose="rag_explanation",
    ) == "stubbed answer"
    token_budget.assert_budget_available("rag_explanation")
    token_budget.reset_budget_state()
