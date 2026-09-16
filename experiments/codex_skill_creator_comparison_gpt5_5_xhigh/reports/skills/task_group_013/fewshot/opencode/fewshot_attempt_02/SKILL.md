---
name: cedar-ridge-intake-audits
description: Use this skill whenever a task asks for Cedar Ridge Intake Coordination Portal or shared intake portal work that must return JSON for access verification, referral readiness or chart activation, dialysis transfer review, or chronic-care enrollment panels. It guides endpoint and SQL reconciliation, controlled-code normalization, deterministic ordering, summary counts, and validation against answer_template.json.
---

# Cedar Ridge Intake Audits

Use this skill for Cedar Ridge portal tasks where the final answer must be a
single JSON object shaped by `input/payloads/answer_template.json`.

The portal is the source of truth. Do not answer from memory or from example
values. Read the prompt, read the template, identify the roster, batch, transfer
batch, or program code, then fetch the matching portal records and supporting
tables.

## Fast Workflow

1. Read `input/prompt.txt` and `input/payloads/answer_template.json`.
2. Extract the task identifier from the prompt/template:
   - roster ID for primary-care access verification
   - referral batch ID for referral readiness or activation
   - transfer batch ID for dialysis transfer review
   - program code for chronic-care enrollment
3. Query the portal using the base URL in the prompt. Prefer `POST /query` for
   joins and use REST endpoints for spot checks.
4. Apply the rules in [references/decision-rules.md](references/decision-rules.md).
5. Build JSON using exactly the template keys, controlled values, scalar types,
   nulls, and ordering instructions.
6. Validate before final response: parse JSON, check required keys, sort required
   lists, verify every count from the emitted rows, and ensure no prose surrounds
   the JSON.

## Helper

This package includes a deterministic helper for data gathering and draft JSON:

```bash
python skill/scripts/cedar_intake_helper.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --prompt input/prompt.txt \
  --template input/payloads/answer_template.json \
  --output /tmp/cedar_draft.json
```

If `TASK_ENV_BASE_URL` is not set, pass the URL shown in the prompt. Review the
draft against the template before using it as the final answer, especially when
the prompt asks for a new schema variant.

For chronic-care templates that require `as_of_date`, use an explicit date from
the prompt, template, or portal metadata when available. If the environment does
not expose one, pass `--as-of YYYY-MM-DD` after deriving the correct operational
date from the task context.

## Portal Access Pattern

Use only the task environment URL supplied by the prompt. The SQL endpoint
accepts JSON like:

```json
{"sql": "select * from referrals where batch_id = '<BATCH_ID>' order by referral_id"}
```

Useful tables are:

- `patients`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`,
  and `clinical_history` for primary-care access verification.
- `referrals`, `icd_codes`, `documents`, `patients`, and `chart_artifacts` for
  referral readiness and chart activation.
- `transfer_requests`, `documents`, `facility_capacity`, and `patients` for
  dialysis transfer review.
- `program_candidates`, `patients`, `clinical_history`, and `chart_artifacts`
  for chronic-care enrollment panels.

## Output Discipline

Treat template arrays marked as unordered sets as sets while reasoning, then emit
a stable order. Prefer the template's enum order; use alphabetical order when
the template says alphabetical; use ID order for patient, referral, transfer,
duplicate group, and blocker lists.

When a summary count disagrees with the detailed rows, the detailed rows are
usually where the mistake is hiding. Recompute the count from the rows you will
emit, not from an earlier scratch query.

Never include task-specific example answers, cached IDs, or copied rows from
training material in the final output. The final JSON must be derived from the
current prompt, current template, and current portal data.
