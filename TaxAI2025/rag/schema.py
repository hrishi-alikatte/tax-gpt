"""Pydantic models for the RAG layer.

All retrieval and generation crosses these boundary types. UI and audit log
must consume `GroundedAnswer`, never raw model output.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SourceAuthority = Literal[
    "official_canton",
    "official_federal",
    "official_commune",
    "product_internal",
]

SourceType = Literal["pdf", "html", "text", "json"]
Language = Literal["fr", "en", "de", "it"]


class RagSource(BaseModel):
    """Top-level descriptor of a corpus document."""

    source_id: str
    title: str
    authority: SourceAuthority
    authority_rank: int = Field(
        description="Lower = more authoritative. 1 = canonical Vaud, 2 = Federal, ..."
    )
    canton: str | None = None
    tax_year: int
    language: Language
    url: str | None = None
    local_path: str
    source_hash: str = Field(description="SHA-256 of the local file at index time.")
    source_type: SourceType
    allowed_use: list[str] = Field(default_factory=list)
    forbidden_use: list[str] = Field(default_factory=list)


class RagChunk(BaseModel):
    """A retrievable, embedded unit. Carries provenance for citation."""

    chunk_id: str
    source_id: str
    text: str
    pdf_page: int | None = None
    printed_page: str | None = Field(
        default=None,
        description="As printed on the PDF page (e.g. 'p.42'). None if unknown.",
    )
    section_title: str | None = None
    vaud_codes: list[str] = Field(default_factory=list)
    topic: str | None = None
    language: Language = "fr"
    embedding_model: str | None = None
    embedding_dimensions: int | None = None


class RagCitation(BaseModel):
    """A single citation referenced by a grounded answer."""

    source_id: str
    source_title: str
    pdf_page: int | None = None
    printed_page: str | None = None
    section_title: str | None = None
    chunk_id: str | None = None
    token: str = Field(
        description=(
            "Inline token rendered in the answer text, e.g. "
            "'[Vaud 2025 Instructions p.42]' or "
            "'[Vaud 2025 Instructions, page pending verification]'."
        )
    )


class RetrievalResult(BaseModel):
    """Output of the retriever step."""

    chunks: list[RagChunk]
    query: str
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_model: str | None = None


class GroundedAnswer(BaseModel):
    """Output of `answer_with_citations`. UI and audit consume this."""

    model_config = ConfigDict(protected_namespaces=())

    answer_en: str = Field(default="")
    citations: list[RagCitation] = Field(default_factory=list)
    refused: bool = False
    refusal_reason: str | None = None
    model_name: str | None = None
    retrieval: RetrievalResult | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    def has_any_citation(self) -> bool:
        return any(cit.token in self.answer_en for cit in self.citations)
