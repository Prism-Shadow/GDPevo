---
name: cedar-ridge-intake
description: Solve Cedar Ridge Intake Coordination Portal tasks that require reconciling portal patient, referral, dialysis transfer, program candidate, chart, coverage, PBM, pharmacy, document, capacity, or ICD data into strict answer_template.json outputs. Use for prompts mentioning Cedar Ridge, TASK_ENV_BASE_URL, access verification, referral readiness, pulmonary or orthopedic intake batches, dialysis transfer reviews, chronic-care enrollment panels, or JSON-only intake activation files.
---

# Cedar Ridge Intake

Use this skill to solve Cedar Ridge intake-coordination tasks against a running task portal. The portal data is authoritative; the answer template controls the output shape, allowed enum values, ordering, and whether null is permitted.

## Workflow

1. Read the task prompt and every local payload file, especially `answer_template.json`.
2. Resolve `<TASK_ENV_BASE_URL>` from the prompt or environment. Use only the task portal endpoints and keep queries scoped to the requested roster, batch, program, or explicit IDs.
3. Classify the task by template shape:
   - `patient_results` plus `cohort_summary`: new patient access verification.
   - `referral_reviews`, `readiness_by_referral`, blocker sets, duplicates, or correspondence queues: referral readiness or chart activation.
   - `batch_id` plus transfer `patients` with packet and capacity fields: dialysis transfer review.
   - `program_code` plus candidate `patients`: chronic-care enrollment panel.
4. Collect the records needed to derive every required field. Prefer the bundled snapshot helper for repeatable portal collection:

```bash
python skill/scripts/portal_snapshot.py --base-url "$TASK_ENV_BASE_URL" roster ROSTER_ID
python skill/scripts/portal_snapshot.py --base-url "$TASK_ENV_BASE_URL" referral-batch BATCH_ID --charts
python skill/scripts/portal_snapshot.py --base-url "$TASK_ENV_BASE_URL" transfer-batch BATCH_ID
python skill/scripts/portal_snapshot.py --base-url "$TASK_ENV_BASE_URL" program PROGRAM_CODE
```

If the skill directory is mounted elsewhere, replace `skill/scripts/portal_snapshot.py` with the path to this skill's script. If a task needs a one-off reconciliation, use `POST /query` with a narrow `where` clause rather than broad table dumps.

5. Apply the derivation rules in [references/cedar-ridge-rules.md](references/cedar-ridge-rules.md). Read that file whenever the task asks for statuses, risk levels, readiness, reason codes, missing artifacts, packet freshness, priority tiers, or summary counts.
6. Build the JSON from the template, not from memory. Include all required keys, use only allowed enum/code values, use empty arrays rather than omitting absent sets, and use JSON `null` only where the template permits it.
7. Sort arrays exactly as requested by the template. When a code array is defined as an unordered set, any order is semantically acceptable, but a stable template or alphabetical order is safest.
8. Recompute summaries from the completed rows. Do not hand-enter counts before the rows are final.
9. Return the single JSON object only. Do not add prose, comments, Markdown fences, or fields not requested by the template.

## Portal Notes

The REST wrappers are useful for individual records:

- `GET /patients/{patient_id}` includes patient demographics, coverage, PBM rows, preferred pharmacies, rosters, chart artifacts, clinical history, referrals, transfers, and program candidates.
- `GET /referrals/{referral_id}` includes the referral, patient, ICD metadata, and referral documents.
- `GET /transfers/{transfer_id}` includes the transfer, patient, packet documents, and capacity rows.
- `GET /chart/{patient_id}` includes patient, clinical history, chart artifacts, and chart subsets.
- `GET /programs/{program_code}/candidates` returns current program candidates.
- `GET /icd/{code}` returns ICD chapter, service family, laterality, and description.
- `POST /query` accepts JSON like `{"sql":"select ... from ... where ..."}` for scoped joins and batch lookups.

For batch tasks, the SQL endpoint is usually faster and less error-prone than many individual GET calls. Keep SQL read-only and filtered to the requested task identifier.
