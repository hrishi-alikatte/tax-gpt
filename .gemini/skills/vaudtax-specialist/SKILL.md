---
name: vaudtax-specialist
description: Specialized expert roles for VaudTaxAI project. Use this skill when working on domain modeling, tax extraction, completeness rules, UI design, security audits, or architectural refactors.
---

# VaudTaxAI Specialist

This skill provides specialized role-based guidance for the VaudTaxAI project, ensuring consistency with the project's strict source-of-truth hierarchy, AI/deterministic split, and safety contracts.

## Role Playbooks

Refer to these specialized playbooks for detailed instructions and constraints:

- **Domain Analyst**: For EN↔FR↔Code mapping and schema design. [domain-analyst.md](references/domain-analyst.md)
- **Completeness Designer**: For deterministic rule logic and golden tests. [completeness-designer.md](references/completeness-designer.md)
- **Extraction Engineer**: For document classification, OCR, and structured extraction. [extraction-engineer.md](references/extraction-engineer.md)
- **Repo Architect**: For system-wide architectural decisions and module boundaries. [repo-architect.md](references/repo-architect.md)
- **Security Reviewer**: For PII protection, secret management, and audit logs. [security-reviewer.md](references/security-reviewer.md)
- **Quality Reviewer**: For CI/CD, demo reliability, and test coverage. [quality-reviewer.md](references/quality-reviewer.md)
- **Frontend Engineer**: For Flet UI components and the step-by-step user journey. [frontend-engineer.md](references/frontend-engineer.md)

## Core Workflow

1. **Identify Role**: Determine which specialized role applies to your current task.
2. **Read Playbook**: Load and read the corresponding reference file from the list above.
3. **Verify Compliance**: Ensure your proposed changes align with the "Hard Rules" and "Mission" of that role.
4. **Execute**: Perform the task using the project-specific guidelines.

## Foundational Mandates

Always respect the mandates in `GEMINI.md`, `docs/ARCHITECTURE.md`, and `docs/DOMAIN_MODEL.md`.
