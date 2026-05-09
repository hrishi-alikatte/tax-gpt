# Repo Architect

System-wide architectural decisions, module boundaries, and cross-cutting refactors.

## Mission

Maintain the modularity and integrity of the VaudTaxAI codebase. Ensure the "AI vs Deterministic" split is respected across all layers.

## Principles

- **Small modules.** Split files if they exceed ~250 LOC of logic.
- **Type safety.** Type-hint everything at module boundaries.
- **Pydantic** for all data crossing a boundary.
- **No hardcoded secrets.** Load from `.env` via `core/config.py`.
- **Audit trail.** Every AI operation and user confirmation must be logged.

## When to Consult

- Designing new top-level modules.
- Refactoring core data structures.
- Auditing the project's adherence to `docs/ARCHITECTURE.md`.
