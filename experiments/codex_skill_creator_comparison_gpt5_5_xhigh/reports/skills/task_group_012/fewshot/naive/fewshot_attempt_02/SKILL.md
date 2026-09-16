---
name: peopleops-evidence-json
description: Resolve PeopleOps Console evidence tasks and produce strict JSON answers. Use when a task asks Codex to verify onboarding closeout, remote-work case readiness, leave source precedence, payroll/accrual readiness, recruitment reconciliation, folder/notice defects, audit scope, or normalized People Ops control labels from an answer_template.json file.
---

# PeopleOps Evidence JSON

Use this skill for PeopleOps Console tasks that require reading HR evidence and returning a single JSON object matching a provided `answer_template.json`.

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before collecting evidence.
2. Identify the target entity from the prompt: employee id, case id, opening id, candidate id, audit id, or policy area.
3. Collect evidence from the configured task environment. Prefer the read-only API when available, then use the UI only to inspect anything the API does not expose.
4. Resolve business facts by source precedence, not by case summary alone.
5. Fill every template key with the exact requested JSON type and exact enum labels from the template.
6. Validate the JSON against the template before final response. Return only JSON unless the prompt explicitly asks otherwise.

Do not call disabled judge endpoints. Do not create comments or mutate case state unless the task explicitly asks for that side effect.

## Evidence Collection

Use the base URL from the task prompt or environment instructions. The API is normally rooted at the same base URL as the web app.

Optional helper:

```bash
python skill/scripts/collect_evidence.py "$TASK_ENV_BASE_URL" --employee-id EMP-000 --case-id CASE-000 --opening-id REQ-000
```

The helper uses only read-only business endpoints and prints a JSON evidence bundle. Pass only the identifiers present in the current task. Add `--full` only when targeted collection does not find enough evidence.

If you collect manually, check these collections as relevant:

- `/api/employees` for employee profile summaries.
- `/api/cases` and `/api/cases/{case_id}` for case details, approvals, attachments, comments, policy refs, and linked audits.
- `/api/payroll-ledgers` for leave assignments, salary assignments, accrual batch ids, statuses, and excluded draft or superseded records.
- `/api/recruitment` for candidates, committee decisions, offers, recruiting costs, notice packets, and payroll precheck records.
- `/api/documents` for required files, actual files, required tags, actual tags, and folder readiness.
- `/api/messages` and `/api/notifications` for formal notice quality, defects, recipients, and status.
- `/api/audit` and `/api/audit/{audit_id}` for scope-specific QA results and adjacent audit events to include or exclude.
- `/api/policies` and `/api/policies/{policy_id}` for source precedence and control gate rules.

## Decision Rules

Read [references/decision_rules.md](references/decision_rules.md) when the task involves any of these areas:

- leave assignment precedence over employee profile summaries;
- submitted payroll assignment selection and draft exclusion;
- case folder readiness, required tags, or formal notice defects;
- recruitment candidate outcomes, cost totals, notice follow-up, or payroll handoff;
- audit event inclusion or exclusion by scope;
- closeout, remediation, or final control result labels.

## JSON Discipline

Use the answer template as the schema of record.

- Include every key from the template exactly once.
- Do not add keys.
- Use booleans and numbers as JSON values, not strings.
- Use `[]` when a list has no items.
- For arrays, preserve source/evidence order unless the prompt gives a different ordering rule.
- For enum fields, copy one of the template's `allowed_values` exactly.
- For list enum fields, every item must be one of the template's `allowed_values`.
- Output only the final JSON object.

Optional validation:

```bash
python skill/scripts/validate_answer.py input/payloads/answer_template.json answer.json
```

Fix every validation error before responding.
