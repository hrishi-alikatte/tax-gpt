"""Source-level secret scan: fail if obvious API keys land in source files."""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SCANNED_GLOBS = ("**/*.py", "**/*.md", "**/*.txt", "**/*.toml", "**/*.cfg")

# Skip vendored / generated / non-source dirs.
SKIP_DIR_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "chroma_db_tax_2025",
    "model_cache",
    ".claude",  # worktrees only; agents are policy text
}

# Patterns that look like real keys. We deliberately do NOT include the literal
# value of any leaked key here (don't echo secrets in the repo).
KEY_PATTERNS = (
    re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"),  # Groq
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),  # OpenAI-style
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----"),
    # Azure AI Foundry-style 80+ char alnum tokens with the ACi/AAAA tail seen
    # on Azure-issued keys. We match the structural shape, not the value.
    re.compile(r"\b[A-Za-z0-9]{60,}AAAA[A-Za-z0-9]{4,}\b"),
)


def _iter_source_files() -> list[Path]:
    files: list[Path] = []
    for pattern in SCANNED_GLOBS:
        for p in REPO_ROOT.glob(pattern):
            if not p.is_file():
                continue
            if any(part in SKIP_DIR_PARTS for part in p.parts):
                continue
            # Skip THIS test file (it contains the patterns themselves).
            if p.resolve() == Path(__file__).resolve():
                continue
            files.append(p)
    return files


def test_no_obvious_api_keys_in_source() -> None:
    offenders: list[tuple[str, int, str]] = []
    for path in _iter_source_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for pat in KEY_PATTERNS:
                if pat.search(line):
                    offenders.append((str(path.relative_to(REPO_ROOT)), lineno, "<redacted>"))
                    break
    assert not offenders, (
        "Possible secret(s) detected in source. Rotate at provider, then move to .env.\n"
        + "\n".join(f"  - {p}:{ln}" for p, ln, _ in offenders)
    )
