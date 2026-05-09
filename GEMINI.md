# VaudTaxAI — Gemini CLI Foundational Mandates

This file provides the primary guidance for Gemini CLI in this workspace.

## 1. Mission

VaudTaxAI is an **English-first, Vaud-only tax filing copilot** for C-permit expat **employees** in Canton Vaud, Switzerland. It helps a taxpayer:

- Understand the Vaud tax process.
- Extract and **confirm** values from documents they upload.
- Detect missing obvious declarations or deductions.
- Map English concepts to **VaudTax / French** field names and codes.
- Explain each step using **official Vaud (and where required, Federal) sources**.

The product is a **bounded copilot**, not an autonomous filer.

## 2. Hard Product Fences

- **Vaud only.** No Geneva, Zurich, or other cantons.
- **C-permit resident employees only** for the MVP.
- **No autonomous tax filing** or submission.
- **No final legal, fiduciary, or optimization advice.**
- **No real user financial documents** or secrets in repo, fixtures, logs, or chat.
- **Synthetic demo data only** unless the user explicitly says otherwise.

## 3. Source-of-Truth Hierarchy

1. **Active source:** Official Vaud 2025 Instructions (`data/official/vd_2025.pdf`), cited as `[Vaud 2025 Instructions p.N]`.
2. **Official Federal AFC guidance** only when Vaud is silent, clearly labeled as Federal.
3. **Deterministic product rules** in `TaxAI2025/completeness/rules.py`, only when they carry a source citation.
4. Anything else is an **open question** and must not be presented as tax fact.

The 2024 Vaud instructions are historical fallback only.

## 4. Safety Contracts

- **Never invent tax law.** If the corpus doesn't contain the answer, refuse and say so.
- **Always cite the official source** for any tax explanation (page number is mandatory).
- **Every extracted value must be confirmed by the user** before being used downstream.
- **Completeness and mapping logic are deterministic**: No LLM calls in these layers.
- **AI is bounded**: Allowed for classification fallback, structured extraction fallback, optional interview phrasing, and source-grounded explanations only.

## 5. Gemini Role Playbooks

For specialized tasks, refer to the following roles (inspired by the Claude/Codex agents in `.claude/agents/`):

- **Domain/Modeling**: Follow `.claude/agents/vaud-tax-domain-analyst.md`.
- **Extraction/OCR**: Follow `.claude/agents/ai-extraction-engineer.md`.
- **Completeness Rules**: Follow `.claude/agents/completeness-engine-designer.md`.
- **UI/Demo Flow**: Follow `.claude/agents/frontend-demo-engineer.md`.
- **Tests/Quality**: Follow `.claude/agents/test-quality-reviewer.md`.
- **Security/Privacy**: Follow `.claude/agents/security-privacy-reviewer.md`.
- **Architecture Audits**: Follow `.claude/agents/repo-architect.md`.

Before edits touching tax logic, schema, RAG, extraction, completeness, or persistence, read the relevant role checklist plus `docs/DOMAIN_MODEL.md` and `docs/ARCHITECTURE.md`.

## 6. Common Commands

```bash
# Run the Flet app (desktop mode)
python main.py

# Run tests
pytest

# Demo replay (deterministic)
python -m demo.runner --scenario expat_c_permit_basic

# Lint / type-check
ruff check .
mypy TaxAI2025
```

## 7. Privacy & Repo Hygiene

- **Never commit .env** or secrets.
- **Never commit uploads**, local DBs, vector stores, or model caches.
- Treat audit logs and uploaded documents as sensitive tax data.
