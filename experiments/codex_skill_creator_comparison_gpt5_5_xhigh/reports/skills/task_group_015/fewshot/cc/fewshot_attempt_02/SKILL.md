---
name: ehr-quality-json
description: Use this skill for EHR quality-governance tasks that require normalized JSON from a read-only healthcare API, including duplicate-chart merge packets, referral coordination, referral batch audits, care-transition packets, ServiceRequest validation, active clinical-list reconciliation, ICD-10 checks, provider lookups, and answers constrained by input/payloads/answer_template.json. Use whenever the prompt mentions an EHR/referral environment, <TASK_ENV_BASE_URL>, duplicate candidates, patient active lists, referral batches, ServiceRequests, or normalized packet JSON.
---

# EHR Quality JSON

Use this skill to turn EHR API evidence into the exact normalized JSON object requested by the task. The evaluator rewards evidence-backed field values, stable IDs, sorted sets, and strict adherence to the provided template.

## Required Workflow

1. Read the prompt and every file under `input/payloads/` before querying the API.
   - Treat `answer_template.json` as the output contract.
   - Preserve the required top-level keys, field names, enum spellings, booleans, nulls, and ordering rules from the template.
   - Do not emit prose, markdown, comments, or procedural notes outside the final JSON object.

2. Resolve the API base URL.
   - Use the prompt value, `TASK_ENV_BASE_URL`, or the staged environment access note.
   - Query only documented endpoints. Prefer direct ID endpoints when the prompt gives an ID.
   - Collection endpoints may return unrelated records; filter returned collections yourself by exact prompt IDs, batch IDs, patient IDs, service line, and dates.

3. Build an evidence bundle before composing the answer.
   - Query primary objects named in the prompt, then all supporting patient, active-list, encounter, document, disclosure, immunization, provider, ICD-10, service-code, duplicate, referral, audit, and ServiceRequest endpoints needed by the template.
   - Use `scripts/collect_ehr_context.py` when it would speed up collection or reduce missed endpoints.
   - Keep scratch evidence local; the final answer should contain only the requested normalized JSON.

4. Reconcile instead of echoing a single endpoint.
   - Active condition, medication, and allergy arrays come from patient active-list endpoints unless the template explicitly says otherwise.
   - Duplicate previews, referral rows, documents, and notes are useful hints, but the final answer should reflect the authoritative cross-endpoint evidence.
   - Validate diagnosis and service codes through directory endpoints when the template asks for validity, chapter, laterality, or service-line fit.
   - Resolve provider contact fields from the provider directory, not from narrative text.

5. Apply the relevant playbook in `references/ehr_quality_patterns.md`.
   - Read it for duplicate merge readiness, referral coordination, care-transition packets, ServiceRequest/SBAR validation, and referral batch audits.
   - Use the playbook as a reasoning checklist, not as a source of final values.

6. Normalize and validate the JSON.
   - Sort arrays marked as sets; otherwise follow the template's date or ID ordering.
   - Use empty arrays for no findings, and `null` only where the template permits null.
   - Recompute summary counts from the arrays actually emitted.
   - Run `scripts/check_json_shape.py <answer.json> <answer_template.json>` if you wrote the answer to a file while drafting.

## Evidence Priority

Use this priority when sources disagree:

1. The task prompt and answer template define scope and schema.
2. Direct detail endpoints for named IDs establish primary facts.
3. Patient active-list endpoints establish active clinical unions.
4. Directory endpoints validate code/provider/service metadata.
5. Encounter, document, disclosure, immunization, and audit endpoints provide supporting evidence and exclusions.
6. Collection previews and notes are hints that still need exact filtering and cross-checking.

## Final Answer Standard

Return one JSON object that parses cleanly. Every nontrivial value should be traceable to a specific endpoint response or to a deterministic rule in the prompt/template. Do not include training example IDs, solved values, or invented narrative.
