"""Cloud Run deployment prep tests."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_app_imports_without_live_model_credentials(monkeypatch) -> None:
    for name in (
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT_RAG",
        "AZURE_OPENAI_DEPLOYMENT_EXTRACTION",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "GROQ_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    # Verify that core AI modules import without crashing even if env vars are missing
    import TaxAI2025.ai.model_router
    import TaxAI2025.rag.explain
    import TaxAI2025.extraction.extract


def test_cloud_run_files_are_present_and_keep_official_corpus() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"
    ).read_text(encoding="utf-8")
    gcp_readme = (REPO_ROOT / "infra" / "gcp" / "README.md").read_text(
        encoding="utf-8"
    )
    cloud_requirements = (REPO_ROOT / "requirements-cloudrun.txt").read_text(
        encoding="utf-8"
    )

    assert "python:3.11-slim" in dockerfile
    assert "requirements-cloudrun.txt" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert 'CMD ["python", "main.py"]' in dockerfile
    assert "*.pdf" in dockerignore
    assert "!data/official/*.pdf" in dockerignore
    assert "google-github-actions/auth@v2" in workflow
    assert "gcloud run deploy" in workflow
    assert "tax-gpt.online" in gcp_readme
    assert "Secret Manager" in gcp_readme
    assert "sentence-transformers" not in cloud_requirements
    assert "langchain-huggingface" not in cloud_requirements
