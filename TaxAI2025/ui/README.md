# UI layer (M3)

Six-screen Flet flow that wraps the deterministic core and AI layers.
Replaces the old chat-only `dashboard_view.py`.

## What is deterministic

- **Navigation** (`navigation.py`) — a finite state machine over the six
  screens. No I/O.
- **AppState** (`state.py`) — pure container. Enforces the
  confirmation gate (`is_extracted_complete`), exposes
  `confirm_fact` / `unconfirm_fact`, refuses pre-confirmed facts at
  `add_document`, and appends an `AuditEntry` for every state-changing
  call.
- **Footer** (`components/footer.py`) — fixed disclaimer string from
  CLAUDE.md §2.
- **Mapping view** (`views/mapping_view.py`) — read-only table, sourced
  from the static map mirroring `docs/DOMAIN_MODEL.md` §4.

## What uses AI

- **Upload view** — calls `TaxAI2025.extraction.extract_from_upload`.
  When `DEMO_MODE=replay`, that entrypoint serves canned facts; otherwise
  it runs the live LLM extractor. AI is only invoked on user click.
- **Explain view** — calls `TaxAI2025.rag.explain.answer_with_citations`.
  Renders the answer + citations exactly as returned. If `refused=True`,
  shows the refusal reason badge — never falls back to anything.

## What must NEVER use AI

- Confirmation gate (`AppState.is_extracted_complete`).
- Mapping view.
- Audit log.
- Footer text.
- Navigation transitions.
- Profile schema.

## Confirmation gate (sacred)

CLAUDE.md §4.5 + §12.6: every TaxFact must be confirmed by the user
before any downstream view consumes it. The gate is enforced in three
places:

1. `AppState.add_document` raises if any fact arrives with
   `confirmed_by_user=True` from extraction.
2. The Continue button on the extracted-values view is disabled until
   `AppState.is_extracted_complete()` returns True.
3. The mapping view consumes only `state.confirmed_facts()`.

Tests cover all three: `tests/test_app_state.py`,
`tests/test_replay_mode.py` (extraction layer can never emit a confirmed
fact), and `tests/test_tax_fact_schema.py`.

## Audit log (lightweight, in-memory)

`AppState.audit_log: list[AuditEntry]`. Each entry has
`{timestamp, event_type, payload}`. Events emitted today:

| event_type                  | when                                              |
| --------------------------- | ------------------------------------------------- |
| `profile_saved`             | intake form submitted                             |
| `document_uploaded`         | extraction returns a record + facts               |
| `document_type_confirmed`   | user confirms a classifier guess                  |
| `fact_confirmed`            | user ticks a Confirm checkbox                     |
| `fact_unconfirmed`          | user unticks a Confirm checkbox                   |
| `explain_asked`             | RAG returned a non-refused answer                 |
| `explain_refused`           | RAG returned `refused=True`                       |
| `navigated`                 | navigator switched screens                        |

Persistence to SQLite is deferred to M5 (`core/db/audit.py`). The buffer
is intentionally per-session today.

## DEMO_MODE banner

`main.py` shows a "DEMO MODE: replay" banner in the left rail when
`config.DEMO_MODE == "replay"`, and the upload view exposes a "Use
synthetic Sarah documents" shortcut. In that mode the intake form is
pre-filled with the synthetic `expat_c_permit_basic` profile.
