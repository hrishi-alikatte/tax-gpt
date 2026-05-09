"""Config tests: env-only secrets, clean failures, no defaults that leak."""
from __future__ import annotations

import pytest


def test_azure_config_loads_from_env(azure_env: None) -> None:
    from TaxAI2025.core import config

    cfg = config.azure_config()
    assert cfg.api_key == "test-key"
    assert cfg.endpoint.startswith("https://")
    assert cfg.deployment_rag == "gpt-5-4-mini-rag"
    assert cfg.deployment_extraction == "gpt-5-4-mini-extract"
    assert cfg.deployment_reasoning == "gpt-5-4-mini-reason"
    assert cfg.embedding_model == "text-embedding-3-large"
    assert cfg.embedding_dimensions == 3072
    assert cfg.vector_similarity == "cosine"


def test_missing_azure_key_fails_cleanly(empty_env: None) -> None:
    from TaxAI2025.core import config

    with pytest.raises(config.ConfigError) as ei:
        config.azure_config()
    assert "AZURE_OPENAI_API_KEY" in str(ei.value)


def test_missing_groq_key_fails_cleanly(empty_env: None) -> None:
    from TaxAI2025.core import config

    with pytest.raises(config.ConfigError) as ei:
        config.groq_config()
    assert "GROQ_API_KEY" in str(ei.value)


def test_index_dir_changes_with_embedding_family(
    azure_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    from TaxAI2025.core import config

    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    importlib.reload(config)
    p_large = config.rag_index_dir()
    assert "te3_large" in str(p_large) or "text-embedding-3-large" in str(p_large)

    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    importlib.reload(config)
    p_small = config.rag_index_dir()
    assert str(p_small) != str(p_large)


def test_active_corpus_path_resolves(azure_env: None) -> None:
    """Real-PDF happy path. Skipped when the corpus is not on disk (CI safety)."""
    from TaxAI2025.core import config

    try:
        p = config.active_corpus_path()
    except config.ConfigError:
        pytest.skip("vd_2025.pdf not present locally; integration-only assertion.")
    assert p.is_file()
    assert p.name.lower().endswith(".pdf")
    assert "vd_2025" in p.name.lower()


def test_active_corpus_path_resolves_under_tmp(
    azure_env: None, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CI-portable variant: build a fake repo root with the expected layout."""
    import importlib

    from TaxAI2025.core import config

    fake_corpus = tmp_path / "data" / "official" / "vd_2025.pdf"
    fake_corpus.parent.mkdir(parents=True)
    fake_corpus.write_bytes(b"%PDF-1.4\n%fake\n")

    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    importlib.reload(config)
    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)

    p = config.active_corpus_path()
    assert p == fake_corpus
