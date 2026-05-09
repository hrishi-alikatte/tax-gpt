"""Document classification. Heuristics first, LLM fallback only on ambiguity.

Heuristic stages:
  1. Filename keywords (FR + DE + EN).
  2. First-page header keywords (read via pdfplumber).
  3. LLM fallback (`generate_json` with a strict Pydantic-derived schema).

When all three fail (or the LLM returns a non-typed answer), we return
DocumentType="unknown" with confidence 0.0. We never guess.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Iterable

from TaxAI2025.core.documents import (
    KNOWN_DOCUMENT_TYPES,
    DocumentRecord,
    DocumentType,
)
from TaxAI2025.extraction.confidence import (
    HEURISTIC_CLASSIFIER_CONFIDENCE,
    LLM_CLASSIFIER_DEFAULT_CONFIDENCE,
)


_FILENAME_KEYWORDS: dict[DocumentType, tuple[str, ...]] = {
    "salary_certificate": (
        "salaire",
        "certificat",
        "lohnausweis",
        "salary",
        "wage",
        "payslip",
    ),
    "health_insurance_premium": (
        "krankenkasse",
        "prime",
        "assurance maladie",
        "assurance-maladie",
        "health-insurance",
        "health_insurance",
        "kvg",
    ),
    "daycare_invoice": (
        "creche",
        "crèche",
        "garderie",
        "daycare",
        "childcare",
        "kita",
        "garde",
    ),
    "pillar_3a_certificate": (
        "3a",
        "3e pilier",
        "3eme pilier",
        "pillar3a",
        "pillar_3a",
        "pillar-3a",
        "saule3a",
        "saeule-3a",
        "saule-3a",
    ),
    "transport_pass": (
        "cff",
        "sbb",
        "abonnement",
        "ga ",
        "transport",
        "mobilis",
    ),
    "bank_year_end_statement": (
        "bank",
        "banque",
        "releve",
        "relevé",
        "year-end",
        "yearend",
        "fin-annee",
        "year_end",
        "ubs",
        "raiffeisen",
    ),
}


_HEADER_KEYWORDS: dict[DocumentType, tuple[str, ...]] = {
    "salary_certificate": (
        "certificat de salaire",
        "lohnausweis",
        "salary certificate",
    ),
    "health_insurance_premium": (
        "prime d'assurance maladie",
        "prime annuelle",
        "krankenkasse",
        "primes d'assurance",
    ),
    "daycare_invoice": (
        "facture de garde",
        "frais de garde",
        "creche",
        "garderie",
        "kita",
        "daycare invoice",
    ),
    "pillar_3a_certificate": (
        "attestation 3e pilier",
        "3e pilier a",
        "pilier 3a",
        "pillar 3a",
        "saule 3a",
    ),
    "transport_pass": (
        "abonnement de transport",
        "abonnement general",
        "abonnement général",
        "ga travelcard",
    ),
    "bank_year_end_statement": (
        "releve bancaire",
        "relevé bancaire",
        "year-end statement",
        "etat fin d'annee",
        "kontoauszug",
    ),
}


def _match_filename(filename: str) -> tuple[DocumentType, float] | None:
    lowered = filename.lower()
    for doc_type, keywords in _FILENAME_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                return doc_type, HEURISTIC_CLASSIFIER_CONFIDENCE
    return None


def _read_first_page_text(file_path: Path) -> str:
    try:
        import pdfplumber

        with pdfplumber.open(str(file_path)) as pdf:
            if not pdf.pages:
                return ""
            return (pdf.pages[0].extract_text() or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _match_header(header_text: str) -> tuple[DocumentType, float] | None:
    if not header_text:
        return None
    lowered = header_text.lower()
    for doc_type, keywords in _HEADER_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                return doc_type, HEURISTIC_CLASSIFIER_CONFIDENCE
    return None


def _llm_classify(filename: str, header_text: str) -> tuple[DocumentType, float] | None:
    """LLM fallback. Returns None if the model cannot decide."""
    from TaxAI2025.ai import model_router

    schema = {
        "title": "DocumentClassification",
        "type": "object",
        "additionalProperties": False,
        "required": ["document_type", "confidence"],
        "properties": {
            "document_type": {
                "type": "string",
                "enum": list(KNOWN_DOCUMENT_TYPES) + ["unknown"],
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
    }
    system = (
        "You classify Swiss Vaud tax documents into one of the allowed types. "
        "Reply with strict JSON. If you cannot tell, return document_type='unknown'. "
        "Never invent a type. Never invent confidence."
    )
    user = (
        f"Filename: {filename}\n"
        f"First-page text (truncated):\n{header_text[:1500]}\n\n"
        "Return JSON with document_type and confidence."
    )
    try:
        payload = model_router.generate_json(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            schema=schema,
            purpose="document_extraction",
        )
    except Exception:  # noqa: BLE001
        return None
    raw_type = payload.get("document_type") if isinstance(payload, dict) else None
    if raw_type not in KNOWN_DOCUMENT_TYPES:
        return None
    raw_conf = payload.get("confidence") if isinstance(payload, dict) else None
    confidence = (
        float(raw_conf)
        if isinstance(raw_conf, (int, float)) and 0.0 <= float(raw_conf) <= 1.0
        else LLM_CLASSIFIER_DEFAULT_CONFIDENCE
    )
    return raw_type, confidence  # type: ignore[return-value]


def _safe_page_count(file_path: Path) -> int | None:
    try:
        import pdfplumber

        with pdfplumber.open(str(file_path)) as pdf:
            return len(pdf.pages)
    except Exception:  # noqa: BLE001
        return None


def classify_document(file_path: Path | str) -> DocumentRecord:
    """Classify a document by filename, header, then LLM fallback."""
    path = Path(file_path)

    filename = path.name
    pdf_page_count = _safe_page_count(path)

    fn_match = _match_filename(filename)
    if fn_match is not None:
        doc_type, conf = fn_match
        return DocumentRecord(
            doc_id=str(uuid.uuid4()),
            filename=filename,
            file_path=str(path),
            document_type=doc_type,
            classifier_confidence=conf,
            classifier_method="heuristic",
            pdf_page_count=pdf_page_count,
        )

    header_text = _read_first_page_text(path) if path.is_file() else ""
    header_match = _match_header(header_text)
    if header_match is not None:
        doc_type, conf = header_match
        return DocumentRecord(
            doc_id=str(uuid.uuid4()),
            filename=filename,
            file_path=str(path),
            document_type=doc_type,
            classifier_confidence=conf,
            classifier_method="heuristic",
            pdf_page_count=pdf_page_count,
        )

    llm_match = _llm_classify(filename, header_text)
    if llm_match is not None:
        doc_type, conf = llm_match
        return DocumentRecord(
            doc_id=str(uuid.uuid4()),
            filename=filename,
            file_path=str(path),
            document_type=doc_type,
            classifier_confidence=conf,
            classifier_method="llm_structured",
            pdf_page_count=pdf_page_count,
        )

    return DocumentRecord(
        doc_id=str(uuid.uuid4()),
        filename=filename,
        file_path=str(path),
        document_type="unknown",
        classifier_confidence=0.0,
        classifier_method="unknown",
        pdf_page_count=pdf_page_count,
    )


__all__ = ["classify_document"]
