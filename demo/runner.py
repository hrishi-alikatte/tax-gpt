"""Demo runner CLI — pre-demo dry-run and fragile-path tripwire.

Walks the full pipeline against a synthetic scenario:
  intake   (UserProfile from profile.json)
  upload   (DEMO_MODE=replay -> DocumentRecord + TaxFact list from extracted.json)
  confirm  (stub: programmatically mark every fact confirmed_by_user=True)
  complete (evaluate(profile, facts) -> list[Finding])
  mapping  (read confirmed facts; deterministic, no live anything)
  explain  (skipped by default; --include-explain runs canned answers from
            scenarios/<name>/answers/<question_hash>.json if present, or
            no-ops if not — never makes a live LLM call here)

Compares actual outputs to scenarios/<name>/expected.json and exits 0 iff
all checks pass. Otherwise prints a diff and exits 1.

Usage:
  python -m demo.runner --scenario expat_c_permit_basic
  python -m demo.runner --scenario expat_c_permit_basic --verbose
  python -m demo.runner --scenario expat_c_permit_basic --dump-audit
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = REPO_ROOT / "demo" / "scenarios"


@dataclass
class RunnerResult:
    scenario: str
    elapsed_seconds: float
    profile: dict[str, Any]
    document: dict[str, Any]
    facts_summary: list[dict[str, Any]]
    interview_summary: list[dict[str, Any]]
    findings_summary: list[dict[str, Any]]
    audit_log_size: int
    diffs: list[str]

    @property
    def ok(self) -> bool:
        return not self.diffs


def _load_expected(scenario_dir: Path) -> dict[str, Any] | None:
    p = scenario_dir / "expected.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _diff(label: str, expected: Any, actual: Any) -> list[str]:
    if expected == actual:
        return []
    return [f"{label}: expected={expected!r} actual={actual!r}"]


def _run(scenario: str) -> RunnerResult:
    os.environ["DEMO_MODE"] = "replay"
    os.environ["DEMO_SCENARIO"] = scenario

    import importlib

    from TaxAI2025.core import config as cfg

    importlib.reload(cfg)

    from TaxAI2025.completeness import evaluate
    from TaxAI2025.extraction import extract_from_upload
    from TaxAI2025.interview import select_questions
    from TaxAI2025.ui.state import AppState, UserProfile

    scenario_dir = SCENARIOS_DIR / scenario
    if not scenario_dir.is_dir():
        raise SystemExit(f"Scenario not found: {scenario_dir}")

    started = time.perf_counter()

    profile_path = scenario_dir / "profile.json"
    profile_payload = json.loads(profile_path.read_text(encoding="utf-8"))
    profile = UserProfile(
        **{k: v for k, v in profile_payload.items() if k in UserProfile.model_fields}
    )

    state = AppState()
    state.set_profile(profile)

    record, facts = extract_from_upload(scenario_dir / "_synthetic_doc.pdf")
    state.add_document(record, facts)
    state.confirm_document_type(record.doc_id)
    for f in facts:
        state.confirm_fact(f.canonical_field)

    if not state.is_extracted_complete():
        # The fixture should always be self-consistent; if it is not, that is
        # a fragile-demo-path defect and we want a loud failure.
        raise SystemExit(
            "is_extracted_complete() is False after stub-confirming all facts. "
            "Fixture or REQUIRED_FIELDS_BY_DOC_TYPE drift."
        )

    interview_questions = select_questions(
        state.profile,
        state.facts,
        answered_ids=state.answered_question_ids(),
        limit=10,
    )
    findings = evaluate(state.profile, state.facts)
    state.findings = findings

    elapsed = time.perf_counter() - started

    facts_summary = [
        {
            "canonical_field": f.canonical_field,
            "value": f.value,
            "source_page": f.source_page,
            "confirmed_by_user": f.confirmed_by_user,
        }
        for f in state.confirmed_facts()
    ]
    findings_summary = [
        {
            "rule_id": f.rule_id,
            "severity": f.severity,
            "pdf_page": f.pdf_page,
            "citation_token": f.citation_token(),
        }
        for f in findings
    ]
    interview_summary = [
        {
            "question_id": q.id,
            "severity": q.severity,
            "pdf_page": q.pdf_page,
            "citation_token": q.citation_token(),
        }
        for q in interview_questions
    ]

    diffs: list[str] = []
    expected = _load_expected(scenario_dir)
    if expected is not None:
        diffs.extend(
            _diff("facts_count", expected.get("facts_count"), len(facts_summary))
        )
        diffs.extend(
            _diff("findings_count", expected.get("findings_count"), len(findings))
        )
        exp_rule_ids = expected.get("findings_rule_ids")
        if exp_rule_ids is not None:
            actual_ids = [f.rule_id for f in findings]
            diffs.extend(_diff("findings_rule_ids", exp_rule_ids, actual_ids))
        exp_pages = expected.get("findings_pdf_pages")
        if exp_pages is not None:
            actual_pages = {f.rule_id: f.pdf_page for f in findings}
            diffs.extend(
                _diff("findings_pdf_pages", exp_pages, actual_pages)
            )
        exp_question_count = expected.get("interview_question_count")
        if exp_question_count is not None:
            diffs.extend(
                _diff(
                    "interview_question_count",
                    exp_question_count,
                    len(interview_summary),
                )
            )
        exp_question_ids = expected.get("interview_question_ids")
        if exp_question_ids is not None:
            actual_question_ids = [q["question_id"] for q in interview_summary]
            diffs.extend(
                _diff("interview_question_ids", exp_question_ids, actual_question_ids)
            )
        max_seconds = expected.get("max_elapsed_seconds")
        if max_seconds is not None and elapsed > max_seconds:
            diffs.append(
                f"elapsed_seconds: actual={elapsed:.3f} exceeds max={max_seconds}"
            )

    return RunnerResult(
        scenario=scenario,
        elapsed_seconds=elapsed,
        profile=profile.model_dump(mode="json", exclude_none=True),
        document=record.model_dump(mode="json", exclude_none=True),
        facts_summary=facts_summary,
        interview_summary=interview_summary,
        findings_summary=findings_summary,
        audit_log_size=len(state.audit_log),
        diffs=diffs,
    )


def _print_summary(result: RunnerResult, verbose: bool) -> None:
    status = "OK" if result.ok else "FAIL"
    print(f"[{status}] scenario={result.scenario} elapsed={result.elapsed_seconds:.3f}s")
    print(f"  facts confirmed: {len(result.facts_summary)}")
    print(f"  findings: {len(result.findings_summary)}")
    for f in result.findings_summary:
        print(f"    - {f['rule_id']} [{f['severity']}] {f['citation_token']}")
    if verbose:
        print("  profile:")
        for k, v in sorted(result.profile.items()):
            print(f"    {k}: {v}")
        print("  document:")
        print(f"    type={result.document.get('document_type')} filename={result.document.get('filename')}")
        print("  facts:")
        for f in result.facts_summary:
            print(
                f"    {f['canonical_field']}={f['value']} p.{f['source_page']} "
                f"confirmed={f['confirmed_by_user']}"
            )
        print("  interview questions:")
        for q in result.interview_summary:
            print(f"    {q['question_id']} [{q['severity']}] {q['citation_token']}")
    if result.diffs:
        print("  diffs:")
        for d in result.diffs:
            print(f"    - {d}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="demo.runner")
    parser.add_argument("--scenario", default="expat_c_permit_basic")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--dump-audit", action="store_true")
    parser.add_argument(
        "--strict-3s",
        action="store_true",
        help="Fail if elapsed > 3.0s even when expected.json sets no max.",
    )
    args = parser.parse_args(argv)

    result = _run(args.scenario)

    _print_summary(result, verbose=args.verbose)

    if args.dump_audit:
        print(f"  audit log size: {result.audit_log_size}")

    if args.strict_3s and result.elapsed_seconds > 3.0:
        result.diffs.append(
            f"--strict-3s violated: elapsed={result.elapsed_seconds:.3f} > 3.0"
        )

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
