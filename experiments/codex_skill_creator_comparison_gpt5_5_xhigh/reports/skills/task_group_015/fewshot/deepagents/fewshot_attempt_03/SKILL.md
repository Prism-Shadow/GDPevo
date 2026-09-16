---
name: ehr-quality-packet
description: Build normalized JSON for read-only EHR quality-governance tasks from a prompt, answer_template.json, and a task environment. Use for duplicate-chart merge readiness, referral coordination and audits, care transition packets, ServiceRequest validation, ICD-10/service-code/provider checks, active clinical list reconciliation, document/audit evidence selection, and schema-conforming JSON-only outputs.
---

# EHR Quality Packet

## Core Workflow

1. Read the task prompt, every input payload, and the provided `answer_template.json` before querying anything. Treat the template as the output contract: preserve required keys, field names, allowed enum values, nullability, booleans, dates, and ordering rules.
2. Determine the base URL from the task environment instructions or the prompt placeholder. Use only the documented read-only endpoints.
3. Extract all stable IDs and scope terms from the prompt and payloads: patient IDs, duplicate candidate IDs, referral IDs, batch IDs, provider IDs, ServiceRequest IDs, diagnosis codes, service codes, and requested service line.
4. Fetch evidence from the API and reconcile it against the template. Use patient-scoped clinical endpoints as authoritative for current active conditions, medications, allergies, encounters, documents, immunizations, disclosures, and ServiceRequests.
5. Read [Decision Rules](references/decision_rules.md) before choosing merge dispositions, referral readiness, care-transition risks, ServiceRequest quality status, batch audit queues, tiers, or summary counts.
6. Return one JSON object only. Do not include Markdown, comments, procedural notes, citations, or keys copied from the template that are descriptive instructions rather than answer fields.

## Helpful Collection Script

Use `scripts/fetch_ehr.py` when it is faster than manual `curl` calls. It accepts a base URL plus optional IDs and prints a JSON evidence bundle:

```bash
python3 scripts/fetch_ehr.py --base-url "$TASK_ENV_BASE_URL" \
  --patient PATIENT_ID --duplicate CANDIDATE_ID --referral REFERRAL_ID \
  --batch BATCH_ID --provider PROVIDER_ID --icd ICD10_CODE
```

For ServiceRequests, pass `--service-request PATIENT_ID:SERVICE_REQUEST_ID`; ServiceRequests are fetched from the patient-scoped endpoint. For referral batches, the script fetches `/api/referrals` and filters locally by exact `batch_id`.

## Output Discipline

- Build the answer from live evidence, not from remembered examples.
- Sort arrays exactly as the template instructs. If it says a field is a set and gives no special order, sort strings alphabetically and objects by the stable ID or code field.
- Keep inactive, stale, unrelated, cancelled, preliminary, or distractor evidence out of primary answer fields unless the template asks for excluded or missing-evidence lists.
- Recompute all counts from the emitted arrays after final selection.
- Validate the final response with a JSON parser before returning it.
