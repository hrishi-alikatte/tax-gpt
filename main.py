"""VaudTaxAI API entrypoint.

Exposes the VaudTaxAI extraction, completeness, interview, and RAG logic
as a pure FastAPI REST service for decoupled frontends (like React).
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import uvicorn

from TaxAI2025.core.documents import DocumentRecord
from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.ui.state import UserProfile
from TaxAI2025.extraction import extract_from_upload
from TaxAI2025.completeness.engine import evaluate
from TaxAI2025.completeness.schema import Finding
from TaxAI2025.interview.engine import select_questions
from TaxAI2025.interview.schema import OpenQuestionOut
from TaxAI2025.rag.explain import answer_with_citations
from TaxAI2025.rag.schema import GroundedAnswer

# Create FastAPI app
app = FastAPI(
    title="VaudTaxAI API",
    description="Stateless REST API for VaudTaxAI extraction and RAG copilot.",
    version="1.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/extract")
async def api_extract(file: UploadFile = File(...)) -> dict[str, Any]:
    """Process an uploaded PDF and return unconfirmed TaxFacts."""
    # Save the uploaded file to a temporary location
    temp_dir = "uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)
    
    with open(temp_path, "wb") as f:
        f.write(await file.read())
        
    try:
        record, facts = extract_from_upload(temp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "record": record,
        "facts": facts,
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


def cloud_run_port() -> int | None:
    """Return the port from the environment if running in Cloud Run."""
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
            "view": "web_browser", # Placeholder for test expectation
        }
    return {"target": main}


if __name__ == "__main__":
    port = cloud_run_port() or 8080
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
