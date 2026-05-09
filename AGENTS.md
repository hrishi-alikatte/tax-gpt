# VaudTaxAI — Codex Operating Guide

This is the canonical operating guide for Codex in this repo. `CLAUDE.md`
remains for Claude continuity; when the two differ, prefer this file for Codex
workflow and `CLAUDE.md` for historical context.

## Mission

VaudTaxAI is an English-first, Vaud-only tax filing copilot for employed
C-permit residents in Canton Vaud. It helps users extract and confirm values
from documents, detect likely missing declarations or deductions, map English
concepts to VaudTax/French labels, and explain steps using official sources.

The product is a bounded copilot. It is not an autonomous filer, tax optimizer,
fiduciary, accountant, lawyer, or multi-canton system.

## Hard Product Fences

- Vaud only.
- C-permit resident employees only for the MVP.
- No autonomous tax filing or submission.
- No final legal, fiduciary, or optimization advice.
- No real user financial documents or secrets in repo, fixtures, logs, or chat.
- Synthetic demo data only unless the user explicitly says otherwise.

## Source Hierarchy

1. Active source: official Vaud 2025 Instructions, cited as
   `[Vaud 2025 Instructions p.N]`.
2. Official Federal AFC guidance only when Vaud is silent, clearly labeled as
   Federal.
3. Deterministic product rules in `TaxAI2025/completeness/rules.py`, only when
   they carry a source citation.
4. Anything else is an open question and must not be presented as tax fact.

The 2024 Vaud instructions are historical fallback only. They must not override
the 2025 source.

## Safety Contracts

- Never invent tax law. Refuse unsupported answers.
- Every tax explanation must cite an official source page or clearly say the
  source is missing.
- Every extracted value must include value, source document, source page,
  confidence, extraction method, extracted timestamp, and
  `confirmed_by_user=False`.
- Downstream layers must ignore or refuse unconfirmed facts.
- `completeness/` and mapping logic are deterministic: no LLM calls, no network,
  no I/O-driven decisions.
- AI is allowed for classification fallback, structured extraction fallback,
  optional interview phrasing, and source-grounded explanations only.

## Codex Role Playbooks

Use these local checklists instead of invoking Claude-specific agents:

- Domain/modeling: follow `.claude/agents/vaud-tax-domain-analyst.md`.
- Extraction/OCR: follow `.claude/agents/ai-extraction-engineer.md`.
- Completeness rules: follow `.claude/agents/completeness-engine-designer.md`.
- UI/demo flow: follow `.claude/agents/frontend-demo-engineer.md`.
- Tests/quality: follow `.claude/agents/test-quality-reviewer.md`.
- Security/privacy: follow `.claude/agents/security-privacy-reviewer.md`.
- Architecture audits: follow `.claude/agents/repo-architect.md`.

## Gemini Role Playbooks

Gemini CLI uses specialized **Skills** to activate these same roles. Use:

```bash
# In an interactive Gemini session:
/skills reload
# To activate the specialist guidance:
activate_skill vaudtax-specialist
```

The playbooks are located in `.gemini/skills/vaudtax-specialist/references/`.

Before edits touching tax logic, schema, RAG, extraction, completeness, or
persistence, read the relevant role checklist plus `docs/DOMAIN_MODEL.md` and
`docs/ARCHITECTURE.md`.

## Testing And Demo Discipline

- Automated tests must not call live LLMs or the network.
- Prefer `.venv/bin/python -m pytest tests/ -q`.
- Replay demo paths must stay offline and fast:
  `python -m demo.runner --scenario expat_c_permit_basic --strict-3s`.
- Manual Azure/Groq smoke scripts are allowed only as explicit live checks; they
  are not CI tests.
- Token budget guard is enabled by default. For local/manual smoke tests only,
  set `VAUDTAX_DISABLE_TOKEN_BUDGET=true` to bypass it.

## Privacy And Repo Hygiene

- Do not read, print, or commit `.env`.
- Do not commit uploads, local DBs, vector stores, model caches, or generated
  artifacts.
- Treat audit logs and uploaded documents as sensitive tax data.
- If a secret appears in source or chat, redact it in discussion and tell the
  user to rotate it at the provider.
