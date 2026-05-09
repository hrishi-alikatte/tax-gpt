"""The completeness layer is deterministic by contract.

Mirror of `test_no_model_call_at_import_time`: importing or evaluating
must not touch `model_router`, `openai`, `groq`, or any LLM client. Per
`CLAUDE.md` §9: *"No LLM calls inside `completeness/` or `mapping/` —
those layers are deterministic by contract."*
"""
from __future__ import annotations

import importlib
import importlib.util
import sys

import pytest

from TaxAI2025.core.tax_facts import TaxFact
from TaxAI2025.ui.state import UserProfile


COMPLETENESS_MODULES = (
    "TaxAI2025.completeness",
    "TaxAI2025.completeness.engine",
    "TaxAI2025.completeness.rules",
    "TaxAI2025.completeness.schema",
)


def _purge(prefix: str) -> None:
    for name in list(sys.modules.keys()):
        if name == prefix or name.startswith(prefix + "."):
            sys.modules.pop(name, None)


def _read_source(module_name: str) -> str:
    spec = importlib.util.find_spec(module_name)
    assert spec is not None and spec.origin is not None, module_name
    with open(spec.origin, "r", encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("module_name", COMPLETENESS_MODULES)
def test_completeness_module_source_does_not_reference_model_router(
    module_name: str,
) -> None:
    src = _read_source(module_name)
    assert "model_router" not in src, (
        f"{module_name} references model_router; the completeness layer "
        f"must be deterministic per CLAUDE.md §9"
    )
    assert "from TaxAI2025.ai" not in src, (
        f"{module_name} imports the AI package"
    )
    assert "import openai" not in src, f"{module_name} imports openai"
    assert "from openai" not in src, f"{module_name} imports openai"
    assert "import groq" not in src, f"{module_name} imports groq"


def test_importing_completeness_does_not_load_model_router() -> None:
    for prefix in ("TaxAI2025.completeness", "TaxAI2025.ai.model_router"):
        _purge(prefix)
    sys.modules.pop("TaxAI2025.ai", None)

    import TaxAI2025.completeness  # noqa: F401

    assert "TaxAI2025.ai.model_router" not in sys.modules
    assert "openai" not in sys.modules


def test_evaluate_does_not_load_model_router() -> None:
    for prefix in ("TaxAI2025.completeness", "TaxAI2025.ai.model_router"):
        _purge(prefix)
    sys.modules.pop("TaxAI2025.ai", None)

    from TaxAI2025.completeness import evaluate

    profile = UserProfile(
        first_name="X",
        marital_status="single",
        children_count=0,
        commune_of_residence="Lausanne",
        work_commune="Lausanne",
        tax_year=2025,
        has_workplace_canteen=True,
    )
    fact = TaxFact(
        canonical_field="health_insurance.annual_premium_chf",
        value=4_200.0,
        source_doc="x.pdf",
        source_page=1,
        confidence=1.0,
        extraction_method="regex",
        confirmed_by_user=True,
    )
    findings = evaluate(profile, [fact])
    assert isinstance(findings, list)
    assert "TaxAI2025.ai.model_router" not in sys.modules
    assert "openai" not in sys.modules
