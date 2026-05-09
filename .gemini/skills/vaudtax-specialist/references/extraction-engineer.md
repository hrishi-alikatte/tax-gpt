# AI Extraction Engineer

Designs and implements document classification, OCR adapters, LLM extraction with structured output, confidence scoring, and source-pointer attachment.

## Mission

Turn raw PDFs/images into structured, confidence-scored JSON. Every extracted value must carry provenance (source doc, page, confidence).

## Hard Contracts

- Every `TaxFact` must have: `canonical_field`, `value`, `source_doc`, `source_page`, `confidence`, `extraction_method`, `extracted_at`, and `confirmed_by_user=False`.
- Downstream code **must refuse** any `TaxFact` with `confirmed_by_user == False`.
- **Deterministic first.** Use regex/templates for known doc types. LLM is residual.
- **Structured output only.** LLM must return Pydantic-validated JSON.
- **Always attach source pointer.** No fact without doc + page.

## When to Consult

- Adding support for a new document type.
- Designing or refactoring the OCR / extraction / classification pipeline.
- Adjusting the confidence model.
- Wiring `DEMO_MODE=replay` for a new scenario.
