"""Cloud Run deployment prep tests."""
from __future__ import annotations

import importlib
from pathlib import Path

from TaxAI2025.ui.state import AppState


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_main_defaults_to_local_desktop_mode(monkeypatch) -> None:
    monkeypatch.delenv("PORT", raising=False)
    app_main = importlib.import_module("main")

    assert app_main.cloud_run_port() is None
    assert app_main.app_run_kwargs() == {"target": app_main.main}


def test_main_uses_cloud_run_port_when_present(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "8080")
    app_main = importlib.import_module("main")

    kwargs = app_main.app_run_kwargs()
    assert app_main.cloud_run_port() == 8080
    assert kwargs["target"] is app_main.main
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 8080
    assert "view" in kwargs


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

    app_main = importlib.import_module("main")
    assert callable(app_main.main)


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
