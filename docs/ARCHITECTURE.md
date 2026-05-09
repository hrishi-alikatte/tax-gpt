# VaudTaxAI — Target MVP Architecture

> Authoritative source for module boundaries, data flow, and the AI vs deterministic split. Read alongside `CLAUDE.md`.

---

## Goal

A bounded English-first Vaud-only tax filing copilot for **employed C-permit residents in Canton Vaud**. Five operations:

1. Profile intake.
2. Document ingestion → classification → extraction.
3. **User confirmation gate** for every extracted value.
4. Deterministic completeness detection (missing docs / missing deductions).
5. Source-grounded explanation (RAG over official Vaud guides).

Plus: VaudTax field mapping (English ↔ FR ↔ code) and an audit log.

---

## Module map

```
VaudTaxAI/
├── apps/
│   └── desktop/              # Flet UI (current Flet stack continues)
│       ├── main.py
│       └── views/
│           ├── intake_view.py
│           ├── upload_view.py
│           ├── extracted_view.py
│           ├── completeness_view.py
│           ├── mapping_view.py
│           └── explain_view.py
├── core/
│   ├── schema/
│   │   ├── profile.py            # canonical UserProfile
│   │   ├── tax_facts.py          # TaxFact (value, source, confidence, confirmed)
│   │   ├── documents.py          # DocumentRecord, DocumentType enum
│   │   └── vaudtax_fields.py     # VaudTax codes + EN/FR labels
│   ├── db/
│   │   ├── session.py
│   │   ├── audit.py              # every AI output + every user confirmation
│   │   └── repository.py
│   └── config.py                 # env loader
├── extraction/
│   ├── classify.py
│   ├── ocr.py
│   ├── extract.py
│   └── confidence.py
├── completeness/
│   ├── rules.py                  # rules-as-data
│   ├── engine.py                 # pure evaluator
│   └── tests/
├── rag/
│   ├── ingest.py
│   ├── retriever.py              # carries source metadata
│   └── explain.py                # answers carry inline citations
├── mapping/
│   └── vaudtax_map.py
├── demo/
│   ├── scenarios/
│   │   └── expat_c_permit_basic/ # synthetic profile + canned doc JSON
│   └── runner.py
├── data/
│   └── official/                 # committed Vaud guides only
└── tests/
```

The current `TaxAI2025/` package is the starting point. Refactor incrementally — **do not big-bang rewrite.**

---

## AI vs deterministic responsibility split

| Layer                      | Mode                                      | Rationale                                                                 |
| -------------------------- | ----------------------------------------- | ------------------------------------------------------------------------- |
| Document classification    | Heuristics first, LLM fallback            | Filename/header rules cover common cases; LLM only on ambiguity           |
| OCR / text extraction      | Deterministic (pdfplumber → tesseract)    | No hallucination tolerance                                                |
| Field extraction (numbers, dates, names) | LLM with **structured Pydantic output**     | Always carries `confidence` + `source_doc` + `source_page`                |
| User confirmation          | Deterministic UI                          | Every value boolean-gated by user before downstream use                   |
| Completeness rules         | **Deterministic only**                    | Rules-as-data, unit-tested, source-cited                                  |
| Rule explanation copy      | LLM                                       | Translates rule text + source quote to plain English; citation mandatory  |
| VaudTax field mapping      | Deterministic table                       | Static code table; PR-reviewed                                            |
| Source-grounded Q&A        | LLM with retrieval                        | Must cite chunk source; refuses if not in corpus                          |
| Tax computation / advice   | **Never**                                 | Out of scope (`CLAUDE.md` §2)                                             |
| Submission                 | **Never**                                 | Out of scope                                                              |

---

## Data flow

```
intake → UserProfile
            │
upload      ▼
   └─► classify ──► DocumentRecord(type)
                        │
                        ▼
                       ocr ──► RawText + page map
                        │
                        ▼
                     extract ──► list[TaxFact] (unconfirmed)
                        │
                        ▼
                  confidence scoring
                        │
                        ▼
            ┌──── audit log ◄────┐
            │                    │
            ▼                    │
   user_confirm gate (UI) ───────┘
            │
            ▼
list[TaxFact] (confirmed_by_user=True)
            │
   ┌────────┴────────┐
   ▼                 ▼
completeness    mapping.vaudtax_map
.engine               │
   │                  ▼
   ▼            VaudTax codes view
missing-list view
   │
   ▼
rag.explain (cite source) ──► explain view
```

Every step writes to `core/db/audit.py`.

---

## Key contracts

### `TaxFact`

```python
class TaxFact(BaseModel):
    canonical_field: str
    value: Any
    source_doc: str
    source_page: int
    source_bbox: tuple[int,int,int,int] | None
    confidence: float | None
    extraction_method: Literal["regex", "pdf_text", "ocr", "llm_structured"]
    model_name: str | None
    extracted_at: datetime
    confirmed_by_user: bool = False
```

### `CompletenessRule`

```python
@dataclass(frozen=True)
class CompletenessRule:
    id: str
    title_en: str
    trigger: Callable[[Profile, list[TaxFact]], bool]
    missing_message_en: str
    asks_for: list[str]
    source_doc: str
    source_page: int | str
    source_level: Literal["vaud_official", "federal", "inferred"]
    severity: Literal["blocker", "likely_missing", "nice_to_have"]
```

### `Finding` (engine output)

```python
class Finding(BaseModel):
    rule_id: str
    title_en: str
    message_en: str
    asks_for: list[str]
    source_doc: str
    source_page: int | str
    severity: Literal["blocker", "likely_missing", "nice_to_have"]
```

### RAG answer

```python
class GroundedAnswer(BaseModel):
    answer_en: str          # contains inline citations like "[Vaud Instructions p.42]"
    citations: list[Citation]
    refused: bool           # True when corpus did not contain a usable chunk
```

---

## Demo fallback strategy

- `DEMO_MODE=replay` env var. Each module honors it.
  - `extraction/*`: returns canned `TaxFact` list from `demo/scenarios/<scenario>/extracted.json`.
  - `rag/explain`: returns canned `GroundedAnswer` from `demo/scenarios/<scenario>/answers/*.json`.
  - `completeness/engine`: runs normally (deterministic, fast, deserves to be live in demo).
- One command: `python -m vaudtax.demo.runner --scenario expat_c_permit_basic` walks the full pipeline against fixtures and exits 0 if all stages produce expected outputs.

---

## Test strategy

- **Golden completeness tests** — one fixture profile per rule, positive + negative case.
- **Schema tests** — every Pydantic model round-trips and rejects malformed input.
- **Mapping tests** — every English label resolves to exactly one VaudTax code.
- **Demo runner smoke test** — runs in CI with stubbed LLM.
- **RAG citation test** — every `GroundedAnswer.answer_en` contains at least one `[Vaud Instructions p.` token.
- **No live LLM in CI.**

Tooling: `pytest` + `ruff` + `mypy` (lenient on UI).

---

## Privacy / security constraints

- Real tax documents never committed. `data/uploads/` always gitignored.
- Synthetic-only fixtures.
- API keys only via `.env`. `.env.example` is the template.
- `*.db` and `chroma_db_*/` gitignored; reproducible from fixtures.
- Audit logs are local-only by default.

---

## Migration plan (current → target)

The repo today is `TaxAI2025/` with `brain/`, `core/`, `ui/`. Don't tear it down. Phase the refactor:

1. **M1 — RAG with citations.** Stay in `TaxAI2025/brain/rag.py`. Fix the retriever bug, attach metadata, enforce inline citations in the prompt.
2. **M2 — extraction skeleton.** Add a new top-level `extraction/` module. Old `dashboard_view.py` upload path keeps working.
3. **M3 — confirmation UI.** Replace the chat-only dashboard with the six-screen flow under `apps/desktop/views/`. Old views deleted.
4. **M4 — completeness engine.** Replace `core/schema.py:get_missing_critical_fields` with `completeness/engine.py`.
5. **M5 — demo runner.** Bind it all together.

See `docs/ROADMAP.md`.
