# extraction/

The pipeline that turns an uploaded document into a list of unconfirmed
`TaxFact`s with full provenance.

## What is deterministic

- `ocr.py` — pdfplumber text extraction. No model in the loop.
- `classify.py` Stage 1 + Stage 2 — filename keyword match and first-page
  header keyword match.
- `extract.py` Stage 2 — per-doc-type regex/template cross-check parsers for
  known high-confidence fields.
- `confidence.py` — pure helpers; regex matches always score 1.0,
  LLM-derived confidence reads what the model returned (defaulting to a
  fixed value, never invented).
- `replay.py` — loads canned JSON when `DEMO_MODE=replay`. No network.

## What uses AI

- `classify.py` Stage 3 — LLM fallback via
  `model_router.generate_json(purpose="document_extraction")` only when
  filename + header heuristics fail. Strict JSON Schema is enforced. If
  the model cannot decide, the document is marked `unknown`.
- `extract.py` Stage 1 — LLM-primary extraction, one structured call per
  page. Uses `model_router.generate_json` with a strict Pydantic-aligned
  JSON Schema. The model emits structured records with `canonical_field`,
  `value`, `source_page`, `snippet`, `confidence`. Pages are validated
  against the actual page set, and snippets must be literal substrings of
  the source page; otherwise the value is dropped. The full extracted page
  text is sent to the model without a local character cap, and the facts
  array schema has no item cap. Output `model_name` carries
  provider:deployment for audit. Regex cross-checks supplement missed
  fields and boost matching LLM values.

## What must never use AI

- The confirmation gate. The extraction layer **must never** set
  `confirmed_by_user = True`. Every emitted `TaxFact` defaults to
  `confirmed_by_user = False`. Tests enforce this. Downstream code that
  consumes a fact with `confirmed_by_user == False` is a bug.
- Tax computation, optimization, or advice — out of scope (see
  `CLAUDE.md` §2).

## Public entrypoint

```python
from TaxAI2025.extraction import extract_from_upload

record, facts = extract_from_upload(path)
# facts: list[TaxFact], each with source_doc, source_page, confidence,
# extraction_method, extracted_at, confirmed_by_user=False.
```

## DEMO_MODE=replay

When `config.DEMO_MODE == "replay"`, the entrypoint reads
`demo/scenarios/<DEMO_SCENARIO>/extracted.json` and returns the canned
record + facts. The fixture is validated against the same Pydantic
schemas as the live path. Schema mismatch raises `ReplayError`.

## Tesseract fallback

Deferred per `docs/ROADMAP.md` M2 risk-mitigation. Image-only PDFs are
out of scope for the hackathon demo. `ocr.py` raises
`OcrUnavailableError` with a clear message when a page yields no text.
The TODO marker in `ocr.py` shows where tesseract would slot in.
