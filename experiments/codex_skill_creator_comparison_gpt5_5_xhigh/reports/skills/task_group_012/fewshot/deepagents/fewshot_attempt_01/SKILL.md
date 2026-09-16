---
name: peopleops-console-case-workflow
description: Inspect and resolve PeopleOps Console lifecycle-control cases by querying the live API for employees, leave, payroll, recruitment, documents, messages, policies, and audit logs, then return JSON that matches the provided answer template. Use when a prompt asks for authoritative record selection, source precedence, folder readiness, notice quality, payroll readiness, recruiting handoff, audit scoping, or similar PeopleOps case analysis.
---

# PeopleOps Console Case Workflow

## Start

- Read the prompt and the answer template first.
- Use the live API before the UI unless the prompt clearly requires UI-only evidence.
- If the prompt names a case, employee, or opening, run `scripts/collect_peopleops_bundle.py` first to gather the linked records.
- Read `references/peopleops-evidence.md` before making the final decision.

## Decide

- Treat the template as authoritative for field names, types, and enum values.
- Prefer the current authoritative record for each module.
- Exclude drafts, stale profile summaries, superseded rows, and adjacent audit events outside the requested scope.
- Keep leave, payroll, recruitment, and folder/notice reasoning separate when a prompt spans multiple modules.

## Output

- Fill only the keys in the template.
- Copy enum labels verbatim.
- Preserve booleans, numbers, strings, and ID-only arrays exactly as requested.
- Return JSON only.
