---
name: cedar-ridge-intake-reconciliation
description: Complete Cedar Ridge Intake Coordination Portal audit tasks that require strict JSON answers from an answer_template, including patient access verification, specialty referral readiness, referral-to-chart activation, dialysis transfer packet and capacity review, and chronic-care program enrollment reconciliation.
---

# Cedar Ridge Intake Reconciliation

## Core Workflow

Use this skill when a prompt points to the Cedar Ridge Intake Coordination Portal and asks for a JSON object matching an `answer_template.json`.

1. Read the prompt and every payload file first. Treat the template as the output contract: required keys, allowed enum values, ordering, constants, and count keys are authoritative.
2. Extract target identifiers from the prompt and payloads: roster IDs, batch IDs, program codes, patient IDs, referral IDs, transfer IDs, requested dates, and service lines.
3. Gather portal evidence from the task base URL. Use direct endpoints for individual records and `/query` for joins, rosters, coverage, PBM, capacity, and chart artifacts. The helper [scripts/portal_snapshot.py](scripts/portal_snapshot.py) can fetch allowed GET paths and common SQL-backed snapshots.
4. Filter out distractors before reasoning. Keep only records tied to the target roster, batch, program, or explicit IDs, then pull related patient, chart, ICD, document, pharmacy, coverage, PBM, lifestyle, capacity, and clinical-history rows.
5. Build a compact evidence table per patient/referral/transfer. Record source fields beside each normalized output value so every status, reason code, blocker, and summary count is traceable.
6. Apply the reusable Cedar Ridge rules in [references/cedar_ridge_rules.md](references/cedar_ridge_rules.md). Prefer direct portal fields and template wording over assumptions.
7. Assemble JSON only. Sort arrays exactly as the template says, use only controlled values, include empty arrays/zero counts where required, and compute summaries from the emitted rows.
8. Smoke-test the result with [scripts/check_json_shape.py](scripts/check_json_shape.py), then manually verify enum values, ordering, and business logic against the template.

## Data Gathering

Prefer SQL when several tables must be reconciled. The SQL endpoint expects a JSON body with an `sql` field.

Useful patterns:

```bash
python skill/scripts/portal_snapshot.py "$TASK_ENV_BASE_URL" --get /referrals/REF_ID
python skill/scripts/portal_snapshot.py "$TASK_ENV_BASE_URL" --batch BATCH_ID --include-related
python skill/scripts/portal_snapshot.py "$TASK_ENV_BASE_URL" --transfer-batch BATCH_ID --include-related
python skill/scripts/portal_snapshot.py "$TASK_ENV_BASE_URL" --roster ROSTER_ID --include-related
python skill/scripts/portal_snapshot.py "$TASK_ENV_BASE_URL" --program PROGRAM_CODE --include-related
python skill/scripts/portal_snapshot.py "$TASK_ENV_BASE_URL" --sql "select * from referrals where batch_id = 'BATCH_ID' order by referral_id"
```

If the helper is too broad for the task, use `curl` or a short one-off script. Stay within endpoints provided by the workspace environment note.

## Output Discipline

- Do not include prose, markdown fences, or comments in the final answer when the prompt asks for JSON only.
- Do not reuse any prior answer row, count, date, or identifier by memory. Recompute every value from the current prompt, template, and portal records.
- Treat reason-code and blocker-code arrays as unordered only when the template says so; otherwise sort as specified.
- Recalculate summaries from the final emitted records, not from intermediate query counts.
- Before finalizing, compare top-level keys and constants with the template and check that no free-form values slipped into enum fields.
