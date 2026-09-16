---
name: peopleops-evidence-reconciliation
description: Use for PeopleOps Console solver tasks that require reconciling employees, leave assignments, payroll assignments or accrual batches, recruitment openings, remote-work or policy cases, document folders, notices/messages, and audit evidence, then returning strict JSON from an answer_template.json. Trigger on prompts mentioning PeopleOps Console, onboarding closeout, leave source precedence, payroll readiness, recruitment reconciliation, policy-case folder or formal-notice quality, audit scope, normalized business labels, or final control results.
---

# PeopleOps Evidence Reconciliation

## Core Workflow

1. Read the task prompt and `input/payloads/answer_template.json` before querying the app. Treat the template as the output contract: required keys, JSON types, enum labels, and list element types come from it.
2. Identify the target entity from the prompt: employee, case, opening, candidate, payroll/accrual batch, audit event, policy, document folder, or notice packet.
3. Prefer the API over manual UI navigation when available. Use the base URL from the prompt or environment, then fetch the relevant endpoints. See [references/api_map.md](references/api_map.md).
4. Build an evidence table before filling JSON: field, candidate value, source record, status, scope, and exclusions. Summaries are hints, not controlling evidence when structured records conflict.
5. Apply the source-precedence and control rules in [references/evidence_rules.md](references/evidence_rules.md). The recurring pattern is to choose approved/submitted/current authoritative records and explicitly exclude drafts, superseded records, stale summaries, or adjacent-scope audit events.
6. Fill every template key exactly once. Use enum values exactly as written in the template, numbers as numbers, booleans as booleans, and lists as arrays of IDs or labels as requested.
7. Validate the JSON locally before final response. Return only the JSON object, with no markdown or explanation, when the prompt asks for JSON only.

## Bundled Helpers

- `scripts/fetch_peopleops_snapshot.py`: Crawl allowed PeopleOps API endpoints, case details, policy details, audit details, and attachment records into one JSON snapshot. Use `--filter` terms to produce a focused `matches` section without losing the full snapshot.
- `scripts/validate_answer.py`: Validate a proposed answer against an `answer_template.json` for required keys, extra keys, primitive types, enum values, and list element types.
- [references/api_map.md](references/api_map.md): Endpoint map and field hints.
- [references/evidence_rules.md](references/evidence_rules.md): Reusable PeopleOps precedence, exclusion, audit-scope, and final-control rules.

Example commands, adjusting paths to the current workspace:

```bash
python /path/to/skill/scripts/fetch_peopleops_snapshot.py "$TASK_ENV_BASE_URL" --out /tmp/peopleops_snapshot.json --filter "$TARGET_ID"
python /path/to/skill/scripts/validate_answer.py input/payloads/answer_template.json /tmp/proposed_answer.json
```

## Answer Discipline

- Do not invent normalized labels. If a field is an enum or list of enums, select only from that field's `allowed_values`.
- Do not use a case summary, employee profile summary, message body, or draft worksheet as the final source when a submitted/approved assignment, offer register, ledger, policy document, or scoped audit record provides the authoritative value.
- Do not collapse exclusions into prose. If the template asks for excluded IDs or excluded audit events, return the concrete IDs from the records that were rejected for draft/superseded/stale/adjacent-scope reasons.
- If evidence is ambiguous, keep querying related structured records before deciding. Good tie-breakers are status, effective period/date, audit scope, approval step, notice quality, and whether the record belongs to the requested employee/case/opening.
