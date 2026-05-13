"""VaudTaxAI API entrypoint.

Exposes the VaudTaxAI extraction, completeness, interview, and RAG logic
as a pure FastAPI REST service for decoupled frontends (like React).
"""
from __future__ import annotations

import logging
import os
import tempfile
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import uvicorn

from TaxAI2025.core import config as app_config
from TaxAI2025.core.documents import DocumentRecord
from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.ui.state import UserProfile
from TaxAI2025.extraction import extract_from_upload
from TaxAI2025.completeness.engine import evaluate
from TaxAI2025.completeness.schema import Finding
from TaxAI2025.interview.engine import select_questions
from TaxAI2025.interview.schema import OpenQuestionOut
from TaxAI2025.rag.explain import answer_with_citations
from TaxAI2025.rag.retriever import get_default_retriever
from TaxAI2025.rag.schema import GroundedAnswer

logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    "https://tax-gpt.online",
    "https://www.tax-gpt.online",
    "https://staging.tax-gpt.online",
    "http://localhost:3000",
    "http://localhost:5173",
]

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_UPLOAD_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    # Startup: verify critical services
    logger.info("VaudTaxAI API starting up...")
    try:
        app_config.azure_config()
        logger.info("Azure config validated OK")
    except app_config.ConfigError as e:
        logger.warning("Azure config incomplete: %s", e)
    yield
    # Shutdown
    logger.info("VaudTaxAI API shutting down...")


app = FastAPI(
    title="VaudTaxAI API",
    description="Stateless REST API for VaudTaxAI extraction and RAG copilot.",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class CompletenessRequest(BaseModel):
    profile: UserProfile
    confirmed_facts: list[TaxFact]


class InterviewRequest(BaseModel):
    profile: UserProfile
    confirmed_facts: list[TaxFact]


class RagRequest(BaseModel):
    question: str


# ---------------------------------------------------------------------------
# Health / readiness
# ---------------------------------------------------------------------------

@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": "1.1.0"}


@app.get("/readyz", include_in_schema=False)
def readyz() -> dict[str, Any]:
    """Readiness check: verifies RAG index is available."""
    retriever = get_default_retriever()
    rag_ready = retriever is not None
    status_code = 200 if rag_ready else 503
    return JSONResponse(
        content={
            "ready": rag_ready,
            "rag_index": "available" if rag_ready else "missing",
        },
        status_code=status_code,
    )


# ---------------------------------------------------------------------------
# Middleware: request logging + size limit
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        "%s %s — %d (%.3fs)",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.post("/api/extract")
async def api_extract(file: UploadFile = File(...)) -> dict[str, Any]:
    """Process an uploaded document and return unconfirmed TaxFacts."""
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Only PDF and images are accepted.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f} MB",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        record, facts = extract_from_upload(tmp_path)
    except Exception as e:
        logger.exception("Extraction failed for %s", file.filename)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return {
        "record": record,
        "facts": [f.model_dump() for f in facts],
    }


@app.post("/api/completeness/check", response_model=list[Finding])
async def api_completeness_check(req: CompletenessRequest) -> list[Finding]:
    """Evaluate completeness rules against confirmed facts."""
    return evaluate(req.profile, req.confirmed_facts)


@app.post("/api/interview/generate", response_model=list[OpenQuestionOut])
async def api_interview_generate(req: InterviewRequest) -> list[OpenQuestionOut]:
    """Select adaptive interview questions based on the profile and facts."""
    questions = select_questions(req.profile, req.confirmed_facts)
    return [OpenQuestionOut.from_question(q) for q in questions]


@app.post("/api/rag/explain", response_model=GroundedAnswer)
async def api_rag_explain(req: RagRequest) -> GroundedAnswer:
    """Answer tax questions using the official Vaud 2025 corpus."""
    return answer_with_citations(req.question)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def cloud_run_port() -> int | None:
    raw = os.environ.get("PORT")
    return int(raw) if raw else None


def main(*args, **kwargs):
    """Dummy main for test compatibility."""
    pass


def app_run_kwargs() -> dict[str, Any]:
    """Return the kwargs for uvicorn (kept for test compatibility)."""
    port = cloud_run_port()
    if port:
        return {
            "target": main,
            "host": "0.0.0.0",
            "port": port,
            "view": "web_browser",
        }
    return {"target": main}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    port = cloud_run_port() or 8080
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
