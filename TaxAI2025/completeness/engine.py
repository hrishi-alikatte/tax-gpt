"""Pure deterministic evaluator. NO LLM, NO network, NO I/O.

`evaluate(profile, facts) -> list[Finding]`

Contract:
  - `facts` is filtered to `confirmed_by_user is True` before any rule
    runs. Unconfirmed facts are invisible to the engine — this enforces
    `CLAUDE.md` §5 ("Downstream code must refuse unconfirmed values").
  - Rules are iterated in registry order; each rule's `trigger` is a pure
    function of `(profile, confirmed_facts)`.
  - Findings are sorted by (severity rank, rule_id) so the UI render
    order is stable.
"""
from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from TaxAI2025.completeness.rules import RULES
from TaxAI2025.completeness.schema import (
    SEVERITY_RANK,
    CompletenessRule,
    Finding,
)

if TYPE_CHECKING:
    from TaxAI2025.core.tax_facts import TaxFact
    from TaxAI2025.ui.state import UserProfile


def _confirmed_only(facts: "Iterable[TaxFact]") -> "list[TaxFact]":
    return [f for f in facts if f.confirmed_by_user]


def _to_finding(rule: CompletenessRule) -> Finding:
    return Finding(
        rule_id=rule.id,
        title_en=rule.title_en,
        message_en=rule.missing_message_en,
        asks_for=list(rule.asks_for),
        source_doc=rule.source_doc,
        pdf_page=rule.pdf_page,
        severity=rule.severity,
        verification_status=rule.verification_status,
    )


def evaluate(
    profile: "UserProfile",
    facts: "Iterable[TaxFact]",
    *,
    rules: "Iterable[CompletenessRule] | None" = None,
) -> list[Finding]:
    if profile is None:
        raise ValueError("evaluate requires a UserProfile (got None)")

    confirmed_facts = _confirmed_only(facts)
    active_rules = list(rules) if rules is not None else RULES

    findings: list[Finding] = []
    for rule in active_rules:
        if rule.trigger(profile, confirmed_facts):
            findings.append(_to_finding(rule))

    findings.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.rule_id))
    return findings


__all__ = ["evaluate"]
