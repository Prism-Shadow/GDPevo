---
name: cedar-ridge-intake
description: Solve Cedar Ridge Intake Coordination Portal tasks that require reconciling patient intake rosters, referral batches, dialysis transfers, chronic-care program candidates, documents, chart artifacts, ICD metadata, insurance/PBM/pharmacy, and capacity data into strict JSON answer templates. Use when the task references the Cedar Ridge Intake Coordination Portal, TASK_ENV_BASE_URL, Cedar Ridge access verification, referral readiness, referral-to-chart activation, dialysis transfer review, or chronic-care enrollment panels.
---

# Cedar Ridge Intake

## Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before querying the portal. Treat the template as authoritative for field names, allowed values, required IDs, ordering, and count keys.
2. Resolve `<TASK_ENV_BASE_URL>` from the task environment instructions. Query only the target roster, batch, program, transfer, referral, or patient IDs named by the prompt/template.
3. Gather portal context with the bundled helper when useful:

```bash
python scripts/fetch_portal_context.py --base-url "$TASK_ENV_BASE_URL" --roster "<ROSTER_ID>"
python scripts/fetch_portal_context.py --base-url "$TASK_ENV_BASE_URL" --referral-batch "<BATCH_ID>"
python scripts/fetch_portal_context.py --base-url "$TASK_ENV_BASE_URL" --transfer-batch "<BATCH_ID>"
python scripts/fetch_portal_context.py --base-url "$TASK_ENV_BASE_URL" --program "<PROGRAM_CODE>"
```

4. Read [references/portal_schema.md](references/portal_schema.md) when writing custom SQL or when the helper output is not enough.
5. Read [references/decision_rules.md](references/decision_rules.md) for reusable normalization rules by workflow.
6. Build the JSON directly from the current portal records. Do not reuse example final values or invent free-form codes. Sort lists exactly as the template says; for unordered code sets, prefer the template's allowed-value order for stable output.
7. Before finalizing, verify the response is valid JSON, contains every required key, uses only allowed enum values, preserves required nulls as JSON `null`, and has cohort/summary counts recomputed from the patient/referral rows.

## Portal Habits

- Prefer `POST /query` for multi-table joins and `GET` endpoints for quick spot checks.
- Keep task data scoped: filter by the prompt's roster ID, batch ID, program code, transfer IDs, referral IDs, or patient IDs.
- If a template and inferred rule conflict, follow the template and include only fields it requests.
- Final answers for these tasks should be JSON only unless the prompt explicitly asks for prose.
