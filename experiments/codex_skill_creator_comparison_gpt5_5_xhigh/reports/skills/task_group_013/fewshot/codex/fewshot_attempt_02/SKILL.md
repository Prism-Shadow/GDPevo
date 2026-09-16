---
name: cedar-ridge-intake-json
description: Solve Cedar Ridge Intake Coordination Portal tasks that require reconciling healthcare intake data and returning a controlled JSON object. Use for new-patient access verification, referral readiness or chart activation, dialysis transfer review, chronic-care program enrollment, and similar portal tasks involving answer_template.json, patient/referral/transfer/program records, ICD metadata, documents, benefits, pharmacies, capacity, chart artifacts, or cohort summaries.
---

# Cedar Ridge Intake JSON

## Workflow

1. Read the task prompt and `input/payloads/answer_template.json` completely.
2. Identify the target identifier from the prompt: roster ID, referral batch ID, transfer batch ID, program code, or explicit patient/referral/transfer IDs.
3. Read any other payload files in `input/payloads/`; treat them as constraints, not as optional hints.
4. Collect portal data from the task environment. For the domain rules and endpoint/table map, read [domain_rules.md](references/domain_rules.md).
5. Build the answer against the template, using only allowed enum/code values and preserving required keys.
6. Recompute all summary counts from the final emitted rows.
7. Validate JSON syntax locally before final response. Return JSON only when the prompt asks for JSON only.

## Portal Snapshot Helper

Use [portal_snapshot.py](scripts/portal_snapshot.py) to gather a focused snapshot when the task uses the Cedar Ridge portal:

```bash
cd /path/to/this/skill
python3 scripts/portal_snapshot.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --schema \
  --roster-id ROSTER-ID \
  --referral-batch-id BATCH-ID \
  --transfer-batch-id TRANSFER-BATCH-ID \
  --program-code PROGRAM-CODE
```

Pass only the identifiers relevant to the current task. The script prints JSON containing the matching records, linked patients, chart data, documents, ICD metadata, pharmacy lookups, coverage/PBM/lifestyle rows, and capacity rows.

If the task gives a literal base URL instead of `TASK_ENV_BASE_URL`, pass that URL. If the prompt only contains `<TASK_ENV_BASE_URL>`, use the environment access instructions supplied with the task workspace.

## Reasoning Rules

Apply these invariants before assigning statuses:

- Filter to the target cohort first; ignore distractor batches and unrelated patients.
- Join records by stable IDs (`patient_id`, `referral_id`, `transfer_id`, `program_code`) rather than names.
- Treat integer booleans `0`/`1` as false/true.
- Distinguish missing data from invalid data when the template has separate values.
- Separate packet/document completeness from staleness when both are requested.
- Separate code discrepancies, administrative blockers, and chart artifact needs; templates often ask for each in a different section.
- Use the template vocabulary exactly, even if portal fields use different terms.

## Answer Construction

For each row-level object:

- Start from the required keys in the template.
- Populate direct identifiers and dates from the target records.
- Add normalized status fields from the portal evidence and domain rules.
- Add reason/blocker/action arrays as deduplicated sets in the requested ordering.
- Omit prose and free-form explanations unless the template has an explicit field for them.

For summaries:

- Count the emitted row objects, not the raw portal rows.
- Include every named count key from the template, including zeroes.
- For cross-tab summaries, emit only combinations required by the template or present in the final rows, following the specified sort order.

Before final output, parse the answer with `jq .` or `python3 -m json.tool`, compare top-level keys with the template, and verify that every enum value appears in the template's allowed values.
