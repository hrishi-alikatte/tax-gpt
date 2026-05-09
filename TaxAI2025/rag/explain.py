"""Source-grounded Q&A wrapper.

Public API:
    answer_with_citations(question: str, retriever=None) -> GroundedAnswer

Behaviour:
  1. Retrieve relevant chunks via the configured retriever.
  2. If no chunk is returned, refuse.
  3. If the question matches a refusal-by-intent pattern, refuse without retrieval.
  4. Generate via `model_router.generate_text(..., purpose='rag_explanation')`.
  5. Validate that the generated text contains at least one valid citation token
     that maps to a retrieved chunk.
  6. If validation fails, regenerate once. If still invalid, refuse.

The retriever is a Protocol so tests inject deterministic stubs without touching
chromadb or Azure.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Protocol, Sequence

from TaxAI2025.ai import model_router
from TaxAI2025.rag.schema import (
    GroundedAnswer,
    RagChunk,
    RagCitation,
    RetrievalResult,
)
from TaxAI2025.rag import sources as source_registry


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACTIVE_SOURCE_LABEL = "Vaud 2025 Instructions"
PAGE_PENDING_TOKEN = f"[{ACTIVE_SOURCE_LABEL}, page pending verification]"

REFUSAL_TEXT = (
    "I cannot answer this from the official Vaud 2025 instructions. "
    "Please consult an accredited fiduciary in Vaud for filing decisions."
)

# Refuse outright when the user asks for these regardless of retrieval.
# Patterns expanded per vaud-tax-domain-analyst review (2026-05-09).
REFUSAL_INTENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Optimization / advice / submission (out of bounded-copilot scope)
    re.compile(r"\boptimize my tax", re.IGNORECASE),
    re.compile(r"\bavoid declaring\b", re.IGNORECASE),
    re.compile(r"\bhide\b.*\b(account|asset|income)\b", re.IGNORECASE),
    re.compile(r"\bwill (vaud|the canton).*(definitely )?accept\b", re.IGNORECASE),
    re.compile(r"\bguarantee\b.*\b(refund|deduction|approval)\b", re.IGNORECASE),
    re.compile(r"\bfile (my )?tax(es)? for me\b", re.IGNORECASE),
    re.compile(r"\bsubmit (my )?(declaration|return)\b", re.IGNORECASE),
    # Out of permit/employment fence (employed C-permit only)
    re.compile(r"\b(self[- ]employed|ind[ée]pendant|raison individuelle)\b", re.IGNORECASE),
    re.compile(
        r"\b(B[- ]permit|L[- ]permit|G[- ]permit|quasi[- ]r[ée]sident|withholding tax|imp[oô]t [aà] la source)\b",
        re.IGNORECASE,
    ),
    # Other cantons (Vaud-only)
    re.compile(r"\b(geneva|gen[èe]ve|zurich|z[uü]rich|fribourg|valais|neuch[aâ]tel|basel|b[âa]le|bern|berne)\b", re.IGNORECASE),
    # Out of MVP doc types
    re.compile(r"\b(crypto|bitcoin|ethereum|nft)\b", re.IGNORECASE),
    re.compile(
        r"\b(rental income|loyer per[çc]u|real estate abroad|immeuble [aà] l'?[ée]tranger)\b",
        re.IGNORECASE,
    ),
    # Year fence (active = 2025)
    re.compile(r"\btax year (202[0-3]|2026|2027)\b", re.IGNORECASE),
    # Audit / amendment representation
    re.compile(r"\b(amend|rectifier).*(declaration|d[ée]claration)\b", re.IGNORECASE),
    re.compile(r"\b(audit|contr[oô]le fiscal)\b.*\b(represent|repr[ée]senter)\b", re.IGNORECASE),
)

# Match `[Vaud 2025 Instructions p.42]` and the page-pending variant.
CITATION_TOKEN_RE = re.compile(
    r"\[Vaud 2025 Instructions(?: p\.(\d+)|, page pending verification)\]"
)


# ---------------------------------------------------------------------------
# Retriever Protocol
# ---------------------------------------------------------------------------


class Retriever(Protocol):
    def retrieve(self, query: str, *, k: int = 4) -> list[RagChunk]: ...


class _NullRetriever:
    """Default retriever used when none is provided.

    Returns no chunks → wrapper refuses. Real retrieval is wired in M1 follow-up
    once the index is built; the explain layer is independent of that.
    """

    def retrieve(self, query: str, *, k: int = 4) -> list[RagChunk]:  # noqa: ARG002
        return []


# ---------------------------------------------------------------------------
# Citation helpers
# ---------------------------------------------------------------------------


def _citation_for(chunk: RagChunk, source_title: str) -> RagCitation:
    if chunk.pdf_page is not None:
        token = f"[{ACTIVE_SOURCE_LABEL} p.{chunk.pdf_page}]"
    else:
        token = PAGE_PENDING_TOKEN
    return RagCitation(
        source_id=chunk.source_id,
        source_title=source_title,
        pdf_page=chunk.pdf_page,
        printed_page=chunk.printed_page,
        section_title=chunk.section_title,
        chunk_id=chunk.chunk_id,
        token=token,
    )


def _allowed_tokens(citations: Sequence[RagCitation]) -> set[str]:
    return {cit.token for cit in citations}


def _validate_citations(answer: str, allowed: set[str]) -> bool:
    """The answer must contain at least one allowed token, and must not contain
    any citation token that is not allowed (no fabricated page numbers)."""
    found = CITATION_TOKEN_RE.findall(answer)
    if not found:
        return False
    raw_tokens = set(re.findall(CITATION_TOKEN_RE, answer))  # set of capture groups
    # Re-extract whole tokens (the regex captured groups, we need the whole match):
    whole_tokens = set(m.group(0) for m in CITATION_TOKEN_RE.finditer(answer))
    if not whole_tokens.issubset(allowed):
        return False
    return True


# ---------------------------------------------------------------------------
# Prompting
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are TaxPilot, an English-first explainer of the Canton of Vaud 2025 tax "
    "instructions for C-permit employed residents.\n"
    "RULES:\n"
    "1. Use ONLY the provided official excerpts. Do not use general knowledge.\n"
    "2. Every answer MUST contain at least one citation token in the EXACT form "
    "`[Vaud 2025 Instructions p.N]` where N is the PDF page from the excerpts. "
    "If no page is known for a chunk you used, use the literal token "
    "`[Vaud 2025 Instructions, page pending verification]`.\n"
    "3. Do NOT cite any source not in the excerpts. Do NOT invent page numbers.\n"
    "4. Refuse final legal advice, autonomous filing, and tax optimisation.\n"
    "5. Translate French terms into English; keep the French in parentheses on "
    "first mention.\n"
    "6. Be concise: 2–6 sentences.\n"
)


def _format_excerpts(chunks: Sequence[RagChunk]) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        page = f"p.{c.pdf_page}" if c.pdf_page is not None else "page pending verification"
        section = f" — {c.section_title}" if c.section_title else ""
        lines.append(f"[{i}] (Vaud 2025 Instructions {page}{section})\n{c.text}")
    return "\n\n".join(lines)


def _build_messages(question: str, chunks: Sequence[RagChunk]) -> list[dict[str, str]]:
    excerpts = _format_excerpts(chunks)
    user = (
        f"Question (English): {question}\n\n"
        f"Official excerpts (Vaud 2025 Instructions):\n{excerpts}\n\n"
        "Answer in English. Include at least one citation token. "
        "Refuse with the standard message if the excerpts do not actually answer the question."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def _is_refusal_by_intent(question: str) -> bool:
    return any(p.search(question) for p in REFUSAL_INTENT_PATTERNS)


def _refuse(reason: str, retrieval: RetrievalResult | None = None) -> GroundedAnswer:
    return GroundedAnswer(
        answer_en=REFUSAL_TEXT,
        citations=[],
        refused=True,
        refusal_reason=reason,
        retrieval=retrieval,
        generated_at=datetime.utcnow(),
    )


def _resolve_retriever(retriever: Retriever | None) -> Retriever:
    """Pick the retriever for this call.

    Order: explicit arg > production ChromaRetriever (if a compatible index
    exists) > _NullRetriever (refusal). Tests inject explicit stubs and so
    never load chromadb.
    """
    if retriever is not None:
        return retriever
    try:
        from TaxAI2025.rag.retriever import get_default_retriever

        real = get_default_retriever()
        if real is not None:
            return real
    except Exception:  # noqa: BLE001 — index missing is the expected case
        pass
    return _NullRetriever()


def answer_with_citations(
    question: str,
    retriever: Retriever | None = None,
) -> GroundedAnswer:
    if _is_refusal_by_intent(question):
        return _refuse(reason="refusal_by_intent")

    retr = _resolve_retriever(retriever)
    chunks = retr.retrieve(question, k=4)
    retrieval = RetrievalResult(chunks=list(chunks), query=question)

    if not chunks:
        return _refuse(reason="no_chunks_retrieved", retrieval=retrieval)

    # Active source enforcement: drop any chunk not from an active source.
    active_source_ids = {s.source_id for s in source_registry.all_active_sources()}
    chunks = [c for c in chunks if c.source_id in active_source_ids]
    if not chunks:
        return _refuse(reason="no_active_source_chunks", retrieval=retrieval)

    source_title = source_registry.active_source().title
    citations = [_citation_for(c, source_title) for c in chunks]
    allowed = _allowed_tokens(citations)
    messages = _build_messages(question, chunks)

    # Resolve model identity for audit-log provenance (CLAUDE.md §5).
    try:
        routing = model_router.route("rag_explanation")
        model_identity = f"{routing['provider']}:{routing['deployment']}"
    except Exception:  # noqa: BLE001 — provenance is best-effort
        model_identity = None

    text = model_router.generate_text(messages, purpose="rag_explanation")
    if not _validate_citations(text, allowed):
        # One regeneration with a stricter reminder.
        retry_messages = list(messages) + [
            {
                "role": "user",
                "content": (
                    "Your previous answer did not contain a valid citation token. "
                    "Regenerate. Use ONLY tokens from this allowed set, exactly: "
                    + ", ".join(sorted(allowed))
                    + ". Include at least one. Do not invent pages."
                ),
            }
        ]
        text = model_router.generate_text(retry_messages, purpose="rag_explanation")
        if not _validate_citations(text, allowed):
            return _refuse(reason="citation_validation_failed", retrieval=retrieval)

    return GroundedAnswer(
        answer_en=text,
        citations=citations,
        refused=False,
        retrieval=retrieval,
        model_name=model_identity,
    )
