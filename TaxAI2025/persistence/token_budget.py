"""Simple per-session model-call budget guard."""
from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass


class TokenBudgetExceeded(RuntimeError):
    pass


@dataclass
class BudgetUsage:
    estimated_tokens: int = 0
    estimated_cost_chf: float = 0.0


_USAGE: dict[str, BudgetUsage] = defaultdict(BudgetUsage)


def _session_id() -> str:
    return os.environ.get("VAUDTAX_SESSION_UUID") or "local"


def _monthly_cap_chf() -> float:
    raw = os.environ.get("VAUDTAX_MONTHLY_TOKEN_BUDGET_CHF", "0.50")
    try:
        return float(raw)
    except ValueError:
        return 0.50


def _disabled() -> bool:
    return os.environ.get("VAUDTAX_DISABLE_TOKEN_BUDGET", "").lower() in {
        "1",
        "true",
        "yes",
    }


def assert_budget_available(purpose: str) -> None:
    if _disabled():
        return
    usage = _USAGE[_session_id()]
    if usage.estimated_cost_chf >= _monthly_cap_chf():
        raise TokenBudgetExceeded(
            "This session reached its model-call budget. "
            "Try again later or raise the configured monthly cap."
        )


def record_model_call(
    purpose: str,
    *,
    input_chars: int,
    output_chars: int,
) -> BudgetUsage:
    if _disabled():
        return _USAGE[_session_id()]
    tokens = max(1, (input_chars + output_chars) // 4)
    # Conservative MVP estimate; exact provider billing can replace this later.
    cost = tokens * 0.000002
    usage = _USAGE[_session_id()]
    usage.estimated_tokens += tokens
    usage.estimated_cost_chf += cost
    return usage


def reset_budget_state() -> None:
    _USAGE.clear()


__all__ = [
    "BudgetUsage",
    "TokenBudgetExceeded",
    "assert_budget_available",
    "record_model_call",
    "reset_budget_state",
]
