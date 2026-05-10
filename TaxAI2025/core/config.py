"""Environment-driven configuration. Never hardcode secrets.

All accessors raise ConfigError with a remediation hint when a required
env var is missing. Lazy: nothing here makes a network call.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _require(name: str, hint: str = "") -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            f"{hint or 'Set it in .env (see .env.example).'}"
        )
    return value


def _optional(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


# ----- Active corpus / scope -----

ACTIVE_TAX_YEAR: int = int(_optional("ACTIVE_TAX_YEAR", "2025") or "2025")
ACTIVE_CANTON: str = _optional("ACTIVE_CANTON", "VD") or "VD"
ACTIVE_RAG_CORPUS: str = _optional("ACTIVE_RAG_CORPUS", "vd_2025") or "vd_2025"

# ----- Model provider routing -----

MODEL_PROVIDER: Literal["azure", "groq"] = (  # type: ignore[assignment]
    (_optional("MODEL_PROVIDER", "azure") or "azure").lower()
)

DEMO_MODE: str = (_optional("DEMO_MODE", "") or "").lower()


@dataclass(frozen=True)
class AzureConfig:
    api_key: str
    endpoint: str
    api_version: str
    deployment_rag: str
    deployment_extraction: str
    deployment_reasoning: str | None
    embedding_deployment: str
    embedding_model: str
    embedding_dimensions: int
    vector_similarity: str


def azure_config() -> AzureConfig:
    return AzureConfig(
        api_key=_require(
            "AZURE_OPENAI_API_KEY",
            "Get this from the Azure Portal -> AI Foundry resource -> Keys.",
        ),
        endpoint=_require("AZURE_OPENAI_ENDPOINT"),
        api_version=_optional("AZURE_OPENAI_API_VERSION", "2024-10-21")
        or "2024-10-21",
        deployment_rag=_require("AZURE_OPENAI_DEPLOYMENT_RAG"),
        deployment_extraction=_require("AZURE_OPENAI_DEPLOYMENT_EXTRACTION"),
        deployment_reasoning=_optional("AZURE_OPENAI_DEPLOYMENT_REASONING"),
        embedding_deployment=_require(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
            "Default expected: text-embedding-3-large",
        ),
        embedding_model=_optional(
            "AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"
        )
        or "text-embedding-3-large",
        embedding_dimensions=int(_optional("EMBEDDING_DIMENSIONS", "3072") or "3072"),
        vector_similarity=_optional("VECTOR_SIMILARITY", "cosine") or "cosine",
    )


@dataclass(frozen=True)
class GroqConfig:
    api_key: str
    model: str


def groq_config() -> GroqConfig:
    return GroqConfig(
        api_key=_require(
            "GROQ_API_KEY",
            "Get this from console.groq.com/keys. Rotate any value that ever appeared in source.",
        ),
        model=_optional("GROQ_MODEL", "llama-3.3-70b-versatile")
        or "llama-3.3-70b-versatile",
    )


# ----- RAG index path -----

def rag_index_dir() -> Path:
    """Index dir for the active corpus + embedding configuration.

    Different embedding models / dimensions / source hashes MUST not share an index.
    """
    explicit = _optional("RAG_INDEX_DIR")
    if explicit:
        return Path(explicit)
    # Default keyed by corpus + embedding family so a model swap forces a new dir.
    embed = _optional("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    suffix = "te3_large" if embed and "3-large" in embed else (embed or "unknown").replace("/", "_")
    return Path(f"./chroma_db_{ACTIVE_RAG_CORPUS}_{suffix}")


def rag_auto_build_index() -> bool:
    """Whether production may build the Chroma RAG index when it is absent.

    Tests and local offline runs default to false so they never make embedding
    calls unexpectedly. The deployed API container enables this explicitly.
    """
    raw = (_optional("RAG_AUTO_BUILD_INDEX", "false") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


# ----- Corpus path resolution -----

REPO_ROOT = Path(__file__).resolve().parents[2]


def active_corpus_path() -> Path:
    """Resolve path to the active Vaud corpus.

    Looks for `vd_2025.pdf` (or env override) at the repo root, then
    under `data/official/`.
    """
    explicit = _optional("ACTIVE_CORPUS_PATH")
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            REPO_ROOT / "data" / "official" / f"{ACTIVE_RAG_CORPUS}.pdf",
            REPO_ROOT / f"{ACTIVE_RAG_CORPUS}.pdf",
            REPO_ROOT / "TaxAI2025" / f"{ACTIVE_RAG_CORPUS}.pdf",
        ]
    )
    for p in candidates:
        if p.is_file():
            return p
    raise ConfigError(
        f"Could not find active corpus '{ACTIVE_RAG_CORPUS}'. "
        f"Looked in: {[str(c) for c in candidates]}"
    )
