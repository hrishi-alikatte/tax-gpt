# `completeness/` — deterministic missing-deduction detector

Required reading: `CLAUDE.md` §4 (architecture principles), §5 (AI safety),
§9 (coding standards), §10 (documentation standards). Per `CLAUDE.md` §4
principle 4: *"Deterministic rules own completeness — never let the LLM
decide what is missing."*

## What is deterministic

- `schema.py` — `CompletenessRule` (frozen dataclass) and `Finding`
  (pydantic model). Pure data contracts.
- `rules.py` — the rule set. Each rule is a literal `CompletenessRule`
  in module-level `RULES: list[CompletenessRule]`. Triggers are pure
  named functions of `(UserProfile, list[TaxFact])`. Adding a rule is a
  list append; **never a new code path in `engine.py`**.
- `engine.evaluate(profile, facts)` — pure evaluator. Filters facts to
  `confirmed_by_user is True`, iterates rules in registry order, sorts
  findings by `(severity_rank, rule_id)`. No I/O. No network.

## What uses AI

**Nothing in this layer.** The completeness engine never calls a model,
never embeds a query, never imports `model_router`. The
`tests/test_completeness_no_llm_imports.py` suite enforces this.

The downstream *explain panel* may take a `Finding` and ask the RAG
layer for a plain-English explanation of the cited Vaud Instructions
page — that is M5 work and lives in `TaxAI2025/rag/explain.py`, not
here.

## What must never use AI

- Deciding whether a rule fires.
- Computing `Finding.severity`.
- Choosing which Vaud page a rule cites (page numbers are set by
  `vaud-tax-domain-analyst` against `data/official/vd_2025.pdf`; an
  unverified rule ships with `pdf_page=None` and
  `verification_status="pending"`).
- Filtering unconfirmed `TaxFact`s. The engine filters by
  `confirmed_by_user is True` deterministically; the LLM never sees the
  unconfirmed set.

## Adding a rule

1. Get a Vaud 2025 Instructions citation from `vaud-tax-domain-analyst`.
2. Append a `CompletenessRule` literal to `RULES` in `rules.py`.
3. Add a positive + negative golden test in
   `tests/test_completeness_rules.py`.
4. Update `docs/DOMAIN_MODEL.md` §6.
