# VaudTaxAI — RAG Corpus Policy

> Authoritative policy for what the RAG layer is allowed to retrieve, embed, cite, and refuse from. Read alongside `CLAUDE.md` §6 and `docs/ARCHITECTURE.md`.

---

## 1. Active corpus

- **Active corpus:** `vd_2025` — *Instructions générales sur la déclaration d'impôt 2025 (Canton de Vaud)*.
- Local path is resolved at runtime by `TaxAI2025.core.config.active_corpus_path()`.
- The file is hashed (SHA-256) at index time. The hash is stamped into the index dir; mismatch forces a rebuild.

## 2. 2024 corpus handling

- `Instructions_generales_2024.pdf` is **historical fallback only**.
- It must never override the 2025 source.
- Implementation: `TaxAI2025.rag.sources.historical_2024_source()` returns it with `authority_rank=99`. The active retriever uses `all_active_sources()`, which excludes it.
- The 2024 source must never be cited in an answer about tax year 2025.

## 3. Source hierarchy

In order of authority:

1. **Vaud official canton** (`authority_rank=1`) — the active 2025 instructions.
2. **Federal AFC** (`authority_rank=2`) — used only when Vaud is silent. Allowed for next milestone; not required for M1.
3. **Communal sources** (`authority_rank=3`) — e.g. Lausanne specifics. Out of scope for MVP.
4. **Product internal rules** (`completeness/rules.py`) — every rule must already cite (1)–(3).

If a question cannot be answered from (1)–(3), the system **refuses**.

## 4. Allowed sources

- `vd_2025_instructions` (active).
- `vd_2024_instructions` (historical only — never returned by `all_active_sources()`).
- Future: official Federal AFC documents (when added by `vaud-tax-domain-analyst`).

## 5. Excluded sources

The following must never be added to the corpus:

- Tax blogs, forums, fiduciary marketing pages, personal sites.
- LLM-generated summaries or paraphrases of official material.
- Translated copies of the official PDF (translation introduces drift).
- User-uploaded tax documents.
- Generic "Swiss tax" guides not specific to Vaud.

## 6. Chunking strategy

- Loader: `pypdf.PdfReader` per page (preserves PDF page numbers, 1-indexed).
- Splitter: `RecursiveCharacterTextSplitter`, `chunk_size=1100`, `chunk_overlap=200`, separators `["\n\n", "\n", ". ", "•", " ", ""]`.
- Rationale (vaud-tax-domain-analyst, 2026-05-09): Vaud rubrics + their explanations frequently exceed 800 chars; raising the size to 1100 keeps a `Code NNN` header glued to its body. Sentence-boundary separator (`". "`) preferred over arbitrary whitespace. Larger overlap survives boundary splits of code headings.
- **`pdf_page is None` is a bug at ingest time.** The loader yields a 1-indexed page per chunk; any chunk written without it must be rejected. The `[..., page pending verification]` token is reserved for chunks added by future non-PDF loaders, not as a silent fallback for missing page numbers.
- Each chunk inherits the page number of its origin page. Spanning chunks attach the **first** page they touch.
- Section title is best-effort heuristic; if unknown, leave `None` (do not invent).
- Vaud field codes (e.g. `Code 320`) and topic tags are populated by `vaud-tax-domain-analyst` post-ingest. Empty by default.

## 7. Metadata schema (per chunk)

Mandatory keys (enforced by `embedding_config.required_chunk_metadata_keys`):

- `embedding_model`
- `embedding_dimensions`
- `source_id`
- `source_title`
- `source_url`
- `source_hash`
- `tax_year`
- `canton`
- `language`
- `pdf_page`
- `printed_page`
- `section_title`
- `vaud_codes`
- `topic`

Any chunk missing one of these keys must be rejected at ingest time.

## 8. Embedding strategy

- Primary: Azure OpenAI `text-embedding-3-large`, **3072 dimensions**, cosine similarity.
- Fallback: Azure OpenAI `text-embedding-3-small`, 1536 dimensions (only if explicitly switched).
- **Forbidden**: `text-embedding-ada-002` (enforced by `embedding_config.assert_model_allowed`).
- No fine-tuning. No training of a tax-specific model.

## 9. Index path policy

- Default path: `./chroma_db_<corpus>_<embed-suffix>` (e.g. `chroma_db_vd_2025_te3_large`).
- Override via env: `RAG_INDEX_DIR`.
- An `IndexStamp` file at the root of the index records `embedding_model`, `embedding_dimensions`, `similarity`, `source_id`, `source_hash`, `tax_year`, `canton`.
- **Stale-index policy**: if the stamp does not match the current config, the loader refuses to use the index. The user must rebuild.
- Old indexes built with HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` (e.g. `chroma_db_tax_2025/`) are **incompatible**. Do not silently reuse them.

## 10. Citation policy

- Every non-refused answer **must** include at least one citation token.
- Token format:
  - `[Vaud 2025 Instructions p.N]` when the PDF page is known.
  - `[Vaud 2025 Instructions, page pending verification]` when only the source is known.
- Tokens that do not correspond to a chunk in the retrieved set are forbidden. The wrapper validates this.
- Tokens for the historical 2024 source are forbidden in answers about 2025.
- The model never invents page numbers. It uses only `pdf_page` values from the retrieved chunks.

## 11. Refusal policy

The wrapper returns `refused=True` when:

- No chunk passes the retrieval similarity threshold for the query.
- The question asks for autonomous filing, optimization, or final legal advice (deny by intent regardless of retrieval).
- The model returns an answer with no valid citation token (one regeneration attempt allowed; then refuse).
- The retrieved chunks are exclusively from a non-active source (e.g. historical 2024 only).

Refusal text format:

> "I cannot answer this from the official Vaud 2025 instructions. Please consult an accredited fiduciary in Vaud for filing decisions."

## 12. Versioning & hash policy

- Every index dir is stamped with the source SHA-256 at ingest time.
- Re-running ingest with the same hash is a no-op (loader detects compatible stamp).
- Updating the source PDF changes the hash → rebuild required.
- The audit log records `(source_id, source_hash, embedding_model, ingested_at)` for every ingest.

## 13. Golden retrieval questions (for tests)

- `Q1` — *"What is Pillar 3a in VaudTax?"* → must retrieve at least one chunk from `vd_2025_instructions` whose section discusses 3e pilier A.
- `Q2` — *"Why do I need a salary certificate?"* → must retrieve a chunk discussing the *certificat de salaire*.
- `Q3` — *"Why do you ask for bank balances at year end?"* → must retrieve a chunk discussing year-end wealth declaration.
- `Q4` — *"What does ordinary taxation mean for a C-permit employee?"* → must retrieve a chunk discussing *imposition ordinaire* / permis C.
- `Q5` — *"Optimize my taxes."* → no retrieval; refuse by intent.

These five questions are the M1 RAG acceptance bar.

## 14. Demo Replay Mode (DEMO_MODE=replay)

To allow the copilot to be demoed without live Azure API keys or network access, a "Replay Mode" is available.

- **Trigger:** Set `DEMO_MODE=replay` in the environment.
- **Fixture Path:** `demo/scenarios/<scenario>/answers/<question_hash>.json`.
- **Behavior:**
  - The question is normalized and hashed (SHA-256, first 12 chars).
  - If a matching JSON file exists, it is returned as the `GroundedAnswer`.
  - If no fixture matches, the system refuses with `no_replay_fixture_found`.
- **Pre-recorded answers:** Replay answers for the Golden Questions (Q1–Q4) are provided in the `expat_c_permit_basic` scenario.
