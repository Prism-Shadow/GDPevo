---
name: ehr-quality-json-packets
description: Solve read-only EHR quality-governance tasks by querying the allowed API endpoints and returning schema-conformant normalized JSON packets.
---

# EHR Quality JSON Packets

Use this skill when a task asks for a normalized JSON answer built from the shared read-only EHR quality environment, especially duplicate-chart review, referral coordination, care-transition packets, ServiceRequest quality checks, or referral-batch audits.

## Operating Rules

1. Read the task prompt and `input/payloads/answer_template.json` before querying the environment.
2. Treat the template as the contract. Emit exactly the requested top-level keys, nested keys, data types, enum values, nullability, and ordering rules.
3. Use only the base URL supplied in the task environment instructions and only documented HTTP GET endpoints. Do not POST, mutate state, call hidden endpoints, or rely on unstated evaluator behavior.
4. Extract all stable identifiers from the prompt and payloads first: patient IDs, duplicate candidate IDs, referral IDs, batch IDs, ServiceRequest IDs, provider IDs, service codes, and ICD-10 codes.
5. Build a source ledger while working. For every final field, know which API record supplied it. Include evidence IDs only when the template asks for them and the records are directly relevant.
6. Return JSON only. Do not include markdown, comments, narrative explanations, or procedural notes in the final answer.

Useful command pattern:

```bash
BASE="<TASK_ENV_BASE_URL>"
curl -s "$BASE/api/patients/<patient_id>" | jq .
```

If a collection endpoint supports filtering, use the filter. If not, fetch the documented collection endpoint and filter locally by IDs from the prompt.

## Normalization

- Dates must stay in `YYYY-MM-DD`.
- Use real booleans and `null`, not strings.
- Deduplicate arrays that behave like sets.
- Sort string sets alphabetically unless the template gives a different rule.
- Sort object arrays by the template rule, commonly by `referral_id`, by ICD code, by risk flag, or newest-to-oldest encounter date.
- For active clinical lists, use patient-specific `conditions`, `medications`, and `allergies` endpoints as authoritative. Include only active records unless the template explicitly asks for inactive or excluded records.
- For normalized condition, medication, and allergy arrays, emit `normalized_key` values rather than display text.
- Do not carry over unrelated records just because they are recent. Match the requested service line, recipient, purpose, status, and evidence type.

## Endpoint Workflow

Start from the task IDs and fetch only related records:

- Patient demographics: `GET /api/patients/{patient_id}`
- Active lists: `GET /api/patients/{patient_id}/conditions`, `/medications`, `/allergies`
- Clinical events and packet evidence: `/encounters`, `/immunizations`, `/documents`, `/disclosures`
- Duplicate candidates: `GET /api/duplicates/{candidate_id}` and, when needed, `/api/duplicates/candidates`
- Referrals: `GET /api/referrals/{referral_id}` or the referral collection filtered locally by batch
- Service requests: `GET /api/patients/{patient_id}/service-requests`, then filter locally by ServiceRequest ID
- Directories: `GET /api/providers/{provider_id}`, `GET /api/icd10/{code}`, `GET /api/service-codes/{code}`
- Audit evidence: `GET /api/audit-logs`, filtered locally to the candidate, patient IDs, or task-relevant event IDs

After each fetch, keep only records tied to the prompt IDs or to IDs referenced by already fetched records.

## Duplicate-Chart Review

For duplicate merge or review tasks:

1. Fetch the duplicate candidate, both patient demographics, active lists for both patients, relevant documents, audit logs, and any provider IDs referenced by packet evidence.
2. Use the candidate's explicit target/source or canonical-patient fields when present. If they are absent, choose a merge target only when the evidence clearly marks one record as canonical or active and the other as a duplicate shell.
3. A merge-ready disposition requires an active or confirmed duplicate candidate, strong identity matches, and no unresolved hard demographic or clinical conflict. Use review-hold/manual-review dispositions for conflicting given name, phone, insurance, DOB, address, or opposite-laterality clinical evidence. Use do-not-merge only for clear non-duplicate evidence.
4. Preserve active condition, medication, and allergy normalized-key unions from both patient active-list endpoints. If a candidate preview has active lists, reconcile it against the patient endpoints and report keys missing from the preview when the template asks.
5. Match/conflict signals should come from the candidate record plus direct demographic comparison. Compare DOB, sex, phone, insurance, address normalization, name variants, primary care provider, and shared external documents.
6. Select document evidence only when it supports identity, external continuity, merge governance, or a required packet item. Exclude general chart summaries and unrelated documents unless the template says otherwise.
7. Fetch provider directory details for packet contacts instead of copying partial provider data from another record.

## Referral Coordination Packets

For referral packet tasks:

1. Fetch referral detail, patient demographics, active diagnoses, active medications, active allergies, recent encounters, required documents, receiving provider details, and ICD-10 details for every diagnosis code in the referral or active chart.
2. The active diagnosis list should include active problem-list diagnoses and referral-intake diagnoses requested by the template. Mark referral relevance by service line, referral narrative, encounter plan, and ICD code.
3. Validate the primary diagnosis code with the ICD-10 directory. The primary code should match the referral narrative and service line; supporting codes should be clinically relevant symptoms or comorbid diagnoses requested by the template.
4. Allergy readiness is complete only when relevant allergies are active and documented without conflict. Missing, unknown, inactive, or conflicting records should produce the template's hold or follow-up status.
5. Required documents must be final or signed and must match the requested evidence type. Missing, preliminary, cancelled, stale, or unrelated documents belong in the appropriate missing-document or follow-up fields.
6. Medication highlights should include active medications that matter to the referral service line or diagnosis. Classify them using the template's controlled reasons; do not include every active medication unless the template asks.
7. Authorization/readiness is blocked by missing authorization, invalid or mismatched diagnosis code, missing provider, missing required documents, or incomplete allergy information. Pick letter-field enum values directly from the resolved facts.

## Care-Transition Packets

For care transition or handoff tasks:

1. Fetch the patient, recipient provider, active lists, encounters, immunizations, disclosures, documents if requested, and any provider records referenced by the prompt.
2. Select handoff encounters by relevance to the target service line and transition purpose, then order by the template rule. Prefer signed or amended encounters when the packet is meant to be sent; exclude stale, unrelated, draft-only, or outside-window encounters unless used solely as risk evidence.
3. Latest immunization means the most recent immunization by date unless the prompt narrows the vaccine type.
4. Disclosure must match the recipient, purpose, and permitted status. Missing or non-permitted disclosure is a readiness blocker.
5. Risk flags come from active conditions, active medications, active allergies, and relevant encounter content. Emit only allowed risk codes from the template and attach sorted evidence arrays for each emitted flag.
6. If all required packet components exist but risk flags are present, use the template's ready-with-risk-flags style status. Use not-ready status only when a required component or permission is missing.

## ServiceRequest Quality Checks

For ServiceRequest quality tasks:

1. Fetch the ServiceRequest, patient, requester provider, performer provider, service-code directory record, ICD-10 details for every reason code, active conditions, and relevant encounters.
2. Validate status, intent, priority, authored date, occurrence date, requester, performer, and performer service line directly from the ServiceRequest and provider directory.
3. `service_code_valid` is true only when the service-code directory recognizes the code and its service line matches the requested workflow.
4. For each reason code, report whether the ICD-10 lookup is valid, its chapter, and whether it matches patient evidence from active conditions, encounters, or referral narrative. Sort validation objects by code when requested.
5. For SBAR fields, inspect structured SBAR sections or text fields and mark each of situation, background, assessment, and recommendation as present only when substantive content exists.
6. If the task also includes duplicate review, solve the duplicate section independently using the duplicate-chart workflow.

## Referral-Batch Audits

For batch audit tasks:

1. Fetch all referrals for the named batch from `GET /api/referrals` and filter by `batch_id`. Count referral rows and distinct patient IDs from the filtered set.
2. For each referral, fetch or reuse ICD-10 details, patient detail when needed for duplicate or insurance checks, and provider details for action owners.
3. Invalid or out-of-range code findings are based on the expected service-line chapter in the template or prompt, not just ICD validity. A valid ICD code can still be out of range for the audit service line.
4. Narrative mismatch means the referral narrative does not align with ICD expected terms. Laterality mismatch means the code implies one side and the narrative or patient evidence implies the other. Missing laterality means the code's expected terms require a side and the narrative omits it.
5. Build duplicate groups from same-patient resubmissions for the same service line, clinical reason, and batch/time window. When the template says all duplicate rows are blockers, tier every referral in the duplicate group, including the original.
6. Shared insurance across different patients is an insurance anomaly, not a merge instruction, unless duplicate-candidate evidence independently supports merge. Same patient with separate clinical referrals should be treated as separate review when the records show distinct reasons or timing.
7. Follow-up queues:
   - authorization missing: no authorization record or required authorization absent
   - authorization pending: authorization exists but is pending
   - records request: required office note or clinical records are missing
   - imaging follow-up: required imaging is missing, pending, preliminary, or not final
8. Tiering:
   - Tier 1: urgent coding issues or duplicate blockers
   - Tier 2: routine coding, authorization, or clinical document blockers
   - Tier 3: administrative document completion only
9. Derive summary counts from the final emitted arrays and queues. Recompute counts after any edit so totals stay internally consistent.

## Final Validation

Before returning the answer:

1. Parse the JSON with `python -m json.tool` or `jq`.
2. Compare required keys and enum values against `answer_template.json`.
3. Verify every ID in evidence fields exists in a fetched source record.
4. Recheck sorted arrays, nullability, date formats, and summary counts.
5. Remove all prose outside the JSON object.
