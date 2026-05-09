# VaudTaxAI — Claude Code Operating Doc

This file is loaded into every Claude Code session in this repo. Read it before doing any work.

---

## 1. Mission

VaudTaxAI is an **English-first, Vaud-only tax filing copilot** for C-permit expat **employees** in Canton Vaud, Switzerland. It helps a taxpayer:

- understand the Vaud tax process,
- extract and **confirm** values from documents they upload,
- detect missing obvious declarations or deductions,
- map English concepts to **VaudTax / French** field names and codes,
- explain each step using **official Vaud (and where required, Federal) sources**.

The product is a **bounded copilot**, not an autonomous filer.

---

## 2. Non-goals (do not build, do not claim)

- ❌ Autonomous tax filing or submission to VaudTax.
- ❌ Tax optimization engine or strategy advice.
- ❌ Replacement for a fiduciary, accountant, or tax lawyer.
- ❌ Other cantons (no Geneva, Zurich, Federal-only flow). Vaud only.
- ❌ Self-employed, business, or non-resident regimes. Employed C-permit only for MVP.
- ❌ Final legal advice.
- ❌ Real user financial data in repo, in fixtures, or in commits.

---

## 3. Hackathon scope

- 36-hour live demo target.
- Demo reliability beats feature breadth and visual polish.
- Architecture must survive past the demo — no throwaway scripts in the main flow.
- Synthetic-only data unless the user explicitly says otherwise.

---

## 4. Architecture principles

1. **Vaud only** for now — domain logic must not leak in rules from other cantons.
2. **English UX, French/VaudTax backend** — every English label maps to a VaudTax code; storage is canonical.
3. **AI is bounded** — extraction, classification, translation, source-grounded Q&A. Nothing else.
4. **Deterministic rules own completeness** — never let the LLM decide what is missing.
5. **User confirms every extracted value** before it is used downstream.
6. **No hallucinated tax advice.** If the corpus does not contain the answer, refuse and say so.
7. **No autonomous submission.**
8. **No final legal/fiduciary claims.** The UI must always read "informational only".
9. **Synthetic / demo data only** unless explicitly told otherwise.
10. Build for the hackathon demo first, but with module boundaries that can survive beyond it.

---

## 5. AI safety constraints

- **Never invent tax law.** If unsure, say "I cannot find this in the official Vaud documents" and stop.
- **Always cite the official source** for any tax explanation: document name + page + (where possible) section/article.
- **Refuse if not in corpus.** Do not fall back on general training knowledge for Swiss tax content.
- **Never give final legal advice.** Always frame as informational, with a recommendation to consult an accredited fiduciary for filing.
- **Every AI output is auditable**: write to the audit log with prompt, retrieval IDs, model name, and timestamp.
- **Every extracted value carries** `value`, `source_doc`, `source_page`, `confidence`, `confirmed_by_user`. Downstream code must refuse unconfirmed values.

---

## 6. Source-of-truth hierarchy

When a tax statement must be made, prefer in this order:

1. **Official Vaud `Instructions Générales 2025`** (`vd_2025.pdf`, `source_id=vd_2025_instructions`). **Active corpus.**
2. **Official Federal AFC guidance** (Confédération suisse). Use only when Vaud is silent — and flag as Federal source explicitly. Allowed for next milestone; not required for M1.
3. **Product rules in `completeness/rules.py`** (deterministic, code-reviewed, citation-bearing).
4. Anything else must be marked **"inferred — open question"** and logged in `docs/DOMAIN_MODEL.md` as an open item.

If a claim cannot be backed by (1)–(3), the system must refuse rather than answer.

The 2024 Vaud Instructions (`Instructions_generales_2024.pdf`) are **historical fallback only** and must never override the 2025 source. See [docs/RAG_CORPUS.md](docs/RAG_CORPUS.md) for the full corpus policy.

---

## 7. Repo structure (current + target)

```
VaudTaxAI/
├── CLAUDE.md                  # this file
├── .claude/agents/            # specialized Claude Code agents
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── DOMAIN_MODEL.md
│   ├── DEMO_SCRIPT.md
│   ├── RAG_CORPUS.md          # corpus + citation policy
│   └── RAG_TOPICS.md          # topic catalogue + EN↔FR mapping
├── TaxAI2025/
│   ├── ai/
│   │   └── model_router.py    # provider-agnostic routing (Azure / Groq)
│   ├── brain/                 # legacy rag.py + agent_graph.py (still bootable)
│   ├── core/
│   │   ├── config.py          # env-only secrets loader
│   │   ├── schema.py
│   │   └── database.py
│   ├── rag/
│   │   ├── embedding_config.py # text-embedding-3-large @ 3072, cosine; index stamp
│   │   ├── schema.py           # RagSource, RagChunk, RagCitation, GroundedAnswer
│   │   ├── sources.py          # active source = vd_2025_instructions
│   │   └── explain.py          # answer_with_citations
│   └── ui/                    # Flet views (unchanged this milestone)
├── tests/                     # no live network; stubs only
├── scripts/
│   └── smoke_rag_azure.py     # manual one-shot live Azure check
├── vd_2025.pdf                # active Vaud 2025 corpus
├── main.py                    # Flet entrypoint
├── requirements.txt
├── .env.example
└── .gitignore
```

Future target modules (to be added during implementation phases — see `docs/ARCHITECTURE.md`):

- `extraction/` — classify, OCR, extract, confidence
- `completeness/` — rules-as-data, deterministic engine, golden tests
- `rag/` — ingest, retriever-with-citations, source-grounded explain
- `mapping/` — canonical ↔ VaudTax field codes
- `demo/` — synthetic scenarios + replay runner
- `data/official/` — Vaud official PDFs (committed)
- `data/uploads/` — user uploads (gitignored, never committed)

---

## 8. Common commands

First-time setup (after cloning):

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
cp .env.example .env  # then fill values
```

`pip install -e .` reads `pyproject.toml` and makes `TaxAI2025` and `demo`
importable from any directory — no more `PYTHONPATH=.`.

```bash
# Run the Flet app (six-screen confirmation flow)
python main.py
DEMO_MODE=replay python main.py     # walks Sarah end-to-end without live LLM at upload

# Tests (no live network; stubs only)
pytest

# One-shot live Azure smoke (manual; never runs in CI)
python scripts/smoke_rag_azure.py fixture
python scripts/smoke_rag_azure.py ingest
python scripts/smoke_rag_azure.py ask "What is Pillar 3a in VaudTax?"

# Lint / type-check (once configured)
ruff check .
mypy TaxAI2025

# Demo replay (deterministic; <3s)
python -m demo.runner --scenario expat_c_permit_basic
python -m demo.runner --scenario expat_c_permit_basic --strict-3s --verbose
```

`requirements.txt` was modernized for Azure: `langchain-classic` removed; `openai`, `groq`, `langchain-openai`, `langgraph`, `python-dotenv`, `pytest` added. Legacy HF embedding + `langchain-groq` packages remain so the old `brain/rag.py` path still imports.

---

## 9. Coding standards

- Type-hint everything at module boundaries.
- Pydantic for all data crossing a boundary (UI → core, AI → core, core → DB).
- No hardcoded secrets — load from `.env` via `core/config.py`.
- No LLM calls inside `completeness/` or `mapping/` — those layers are deterministic by contract.
- Each AI-touching function returns its full provenance (prompt, model, retrieval IDs, confidence) — never just a string.
- Default to no comments; only add when intent is non-obvious.
- Small modules. If a file passes ~250 LOC of logic, split it.

---

## 10. Documentation standards

- Every module under `extraction/`, `completeness/`, `rag/`, `mapping/` must have a short `README.md` answering three questions: **what is deterministic / what uses AI / what must never use AI**.
- `docs/DOMAIN_MODEL.md` is the single source of truth for canonical schema + English ↔ French/VaudTax mapping. PRs that change a code or label must update it.
- `docs/ROADMAP.md` is updated when a milestone moves.

---

## 11. Privacy & security rules

- **Never commit real tax documents.** `data/uploads/` is gitignored. Treat any uploaded file as PII.
- **Never commit secrets.** `.env` is gitignored. Use `.env.example` as the only template.
- **Never echo secrets** to chat, logs, or commits. The `tests/test_secret_scan.py` test fails the suite if API-key shapes appear in source.
- **Never commit local DBs or vector stores** (`*.db`, `chroma_db_*/`, `model_cache/`). They are reproducible from fixtures.
- Hardcoded keys were removed from `TaxAI2025/brain/rag.py` and `TaxAI2025/brain/agent_graph.py` (now via `core/config.py`). The Groq key that previously lived in source is **compromised** — rotate at console.groq.com. The Azure key shared in chat is also **compromised** — rotate at the Azure Portal.
- Audit logs may contain user-derived figures. They live on disk only, never in remote services unless explicitly enabled.
- Default retention: ephemeral (per-session). Persistence only with explicit user opt-in.

---

## 12. Workflow rules for Claude

These rules apply to every Claude Code session in this repo:

1. **Analyze before editing.** Read the relevant module + `docs/DOMAIN_MODEL.md` + this file before any edit that touches tax logic, schema, or RAG.
2. **Never invent tax law.** If a claim isn't backed by the source-of-truth hierarchy in §6, say "I cannot find this in the official Vaud documents" and stop.
3. **Cite official sources.** Any tax explanation produced (in code, in tests, in docs, in conversation) must reference the Vaud Instructions page or section, or an official Federal AFC source.
4. **Do not commit real tax documents.** If asked, refuse and explain.
5. **Use specialized agents** (in `.claude/agents/`) for the work they own. Don't do domain modeling without `vaud-tax-domain-analyst`. Don't design completeness rules without `completeness-engine-designer`. Don't review for privacy without `security-privacy-reviewer`.
6. **Confirmation gate is sacred.** Any code path that uses an extracted value without `confirmed_by_user == True` is a bug. Reject the diff.
7. **Demo reliability beats elegance.** Before refactors that touch the demo path, ensure `demo/runner.py` still passes (once it exists).
8. **Ask before scope creep.** If the task implies adding optimization, submission, multi-canton, or fiduciary features — stop and confirm with the user.
