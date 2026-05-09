# VaudTaxAI — Hackathon Roadmap

> 36-hour live demo target. Demo reliability beats feature breadth. Each milestone ends with a green demo path.

---

## North star (demo punchline)

> *"Sarah uploaded her docs. We pulled out her values, she confirmed them, and we found three things she forgot to claim — each backed by a page in the official Vaud guide."*

Everything below serves that one moment.

---

## M0 — Scaffold (DONE in this commit)

- [x] `git init` at project root.
- [x] `CLAUDE.md`, `.gitignore`, `.env.example`.
- [x] `.claude/agents/*` — seven specialized agents.
- [x] `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/DOMAIN_MODEL.md`, `docs/DEMO_SCRIPT.md`.
- [x] Dead code removed (`flet_ui_webapp.py`, `my_*.py`, `streamlit_test.py`, `test_flet.py`, `tax_assistant.py`, `gemini.md`).

**Exit criterion:** fresh Claude Code session reads `CLAUDE.md` and operates within scope.

**To-do for the human (not Claude):**

- Rotate the leaked Groq API key at `console.groq.com`.
- Decide whether `MDM INDEX.pdf` and `Business Plan - taxai.pdf` stay in repo (move to `docs/` if yes, delete if not).

---

## M1 — RAG with citations (≈ 4h)

**Why first:** the demo's credibility depends on every answer carrying a Vaud source page.

- [ ] Fix `TaxAI2025/brain/rag.py` retriever typo: `search_kwags` → `search_kwargs`.
- [ ] Move hardcoded `GROQ_API_KEY` to `.env`. Add `core/config.py` (env loader).
- [ ] Extend retriever to attach `source_doc`, `source_page` to every chunk's metadata.
- [ ] Update prompt template to require `[Vaud Instructions p.N]` inline in every answer.
- [ ] Add `tests/test_rag_citations.py` — every answer string must contain at least one citation token.
- [ ] Add `rag/explain.py` returning a `GroundedAnswer` Pydantic model (text + citations list + `refused` flag).

**Demo gate:** open existing chat UI, ask "what is the deduction for childcare?" — answer renders with at least one `[Vaud Instructions p.X]`.

---

## M2 — Extraction skeleton (≈ 6h)

- [ ] `core/schema/tax_facts.py` — `TaxFact` Pydantic model (full provenance fields).
- [ ] `core/schema/documents.py` — `DocumentRecord`, `DocumentType` enum.
- [ ] `extraction/classify.py` — heuristic classifier for: Certificat de salaire, Krankenkasse, daycare invoice, pillar 3a. LLM fallback only on ambiguity.
- [ ] `extraction/ocr.py` — pdfplumber primary, tesseract fallback (deferred if time-poor).
- [ ] `extraction/extract.py` — per-doc-type regex/template parsers; LLM with structured Pydantic output for residual fields.
- [ ] `DEMO_MODE=replay` honored: returns canned `TaxFact` list from `demo/scenarios/expat_c_permit_basic/extracted.json`.

**Demo gate:** uploading the synthetic Certificat de salaire produces a `TaxFact` list with full provenance.

---

## M3 — Confirmation UI (≈ 6h)

Replace the chat-only dashboard with the six-screen flow.

- [ ] `apps/desktop/views/intake_view.py` — minimal profile form.
- [ ] `apps/desktop/views/upload_view.py` — file picker + classification confirm.
- [ ] `apps/desktop/views/extracted_view.py` — per-field confirm checkboxes; "Continue" disabled until all required confirmed.
- [ ] `apps/desktop/views/mapping_view.py` — read-only EN ↔ FR ↔ VaudTax code table.
- [ ] `apps/desktop/views/explain_view.py` — wraps RAG with clickable citations.
- [ ] Old `TaxAI2025/ui/views/dashboard_view.py` deleted once parity reached.

**Demo gate:** end-to-end flow walkable from intake → upload → confirm → mapping → explain.

---

## M4 — Completeness engine (≈ 5h)

The punchline.

- [ ] `completeness/rules.py` — `CompletenessRule` dataclass + initial rule set:
  - VD-CHILDCARE-001 (kids > 0 and no daycare fact → ask).
  - VD-PILLAR3A-001 (employed, working, no pillar 3a fact → ask).
  - VD-COMMUTE-001 (residence ≠ work commune, no transport fact → ask).
  - VD-MEAL-001 (employed, no canteen indicator, no meal-allowance fact → ask).
  - VD-INSURANCE-001 (no health insurance premium fact → ask).
  - (additional rules: see `docs/DOMAIN_MODEL.md`).
- [ ] `completeness/engine.py` — pure `evaluate(profile, facts) -> list[Finding]`.
- [ ] Golden tests for each rule (positive + negative).
- [ ] `apps/desktop/views/completeness_view.py` — render findings with citation badges.

**Demo gate:** with the synthetic profile, exactly three findings appear, each citing a Vaud Instructions page.

---

## M5 — Demo runner (≈ 3h)

- [ ] `demo/scenarios/expat_c_permit_basic/` — synthetic profile JSON + canned doc JSON + canned RAG answers.
- [ ] `demo/runner.py` — CLI walking the full pipeline; exits 0 with expected fixture outputs; otherwise diffs and exits 1.
- [ ] Smoke test in CI / local pre-demo dry run.
- [ ] Audit log table populated and inspectable from CLI.

**Demo gate:** `python -m vaudtax.demo.runner --scenario expat_c_permit_basic` exits 0 in under 3 seconds.

---

## Stretch (only if M0–M5 are all green)

- Second scenario: married-with-child, both employed.
- PDF preview anchor on click of citation badge.
- Export confirmed values as a draft JSON the user can copy-paste into VaudTax fields.
- Multilingual UI (English/French toggle for the field labels).

---

## Skip list (out of scope for hackathon)

- Authentication, user accounts, multi-user.
- Cloud sync, encrypted storage, SSO.
- Real submission to VaudTax.
- Tax optimization or strategy advice.
- Other cantons (Geneva, Zurich, etc.).
- Self-employed, business, non-resident regimes.
- B-permit / G-permit / quasi-resident logic.
- Anything that requires legal sign-off.

---

## Risks (track these)

- **Vaud doc parsing fidelity** — page numbers in the PDF may not map cleanly to logical sections. Mitigation: keep page-based citations; defer section refs to post-hackathon.
- **Live LLM availability** — Groq rate limits during demo. Mitigation: `DEMO_MODE=replay` ready and tested.
- **OCR for image-only PDFs** — drop tesseract from MVP if time-tight; require text-based PDFs for demo.
- **Schema churn** — every change to `TaxFact` ripples through extraction + UI + tests. Freeze schema after M2.
