---
name: ehr-governance
description: Prepare normalized EHR clinical governance packets using a read-only quality API. Use this skill whenever the task involves duplicate-chart merge packets, referral coordination/audit packets, care transition handoffs, service-request quality validation, or any clinical governance workflow that requires querying patient, referral, provider, ICD-10, or audit-log endpoints and producing structured JSON output conforming to an answer template. Trigger on phrases like "merge readiness packet," "referral coordination packet," "care transition packet," "referral audit," "duplicate review," "ServiceRequest quality signals," "EHR quality-governance," or any task that mentions API endpoints like /api/patients, /api/duplicates, /api/referrals, /api/icd10, /api/providers.
---

# EHR Governance Packet Builder

This skill covers building normalized clinical governance packets by querying a read-only EHR quality API. The solver's job is to gather evidence from the API, cross-reference records, apply governance rules, and produce structured JSON that conforms to a provided answer template.

## API Environment

The task environment provides a read-only EHR API at the URL given in the prompt as `<TASK_ENV_BASE_URL>`. Substitute this placeholder with the actual base URL before making requests. All endpoints return JSON.

Use `curl -s --connect-timeout 10 --max-time 30` for every API call. Prefer the helper script at [scripts/fetch.sh](scripts/fetch.sh) which wraps curl with retry logic and error handling; invoke it as `bash /work/skill/scripts/fetch.sh <endpoint-path>` and it writes the JSON body to stdout. Read its source for usage details if needed, but the basic invocation is: pass only the path portion (e.g., `/api/patients/P-31014`), not the full URL.

## Endpoint Catalog

Every endpoint is a GET that returns a JSON object or array. Parentheses show which governance packets typically need each endpoint.

### Patient
- `GET /api/patients` — list of all patients (audits, batch work)
- `GET /api/patients/{patient_id}` — demographics, enterprise MRN, display name, DOB, sex, insurance, address, phone, primary care provider ID (all packet types)

### Clinical Lists (per patient)
- `GET /api/patients/{patient_id}/conditions` — condition/problem list records with `code` (ICD-10), `description`, `normalized_key`, `status` (active/inactive/etc.), `source` (all clinical packets)
- `GET /api/patients/{patient_id}/medications` — medication records with `medication` name, `dose`, `route`, `frequency`, `normalized_key`, `status` (all clinical packets)
- `GET /api/patients/{patient_id}/allergies` — allergy records with `allergen`, `reaction`, `severity`, `status`, `source` (all clinical packets)

### Encounters, Immunizations, Disclosures, Documents, Service Requests (per patient)
- `GET /api/patients/{patient_id}/encounters` — encounter records with `encounter_id`, `date`, `type`, `provider_id`, `signed_status`, `diagnosis_codes`, `medications_mentioned` (care transitions, referral packets)
- `GET /api/patients/{patient_id}/immunizations` — immunization records with `immunization_id`, `date`, `vaccine` (care transitions)
- `GET /api/patients/{patient_id}/disclosures` — disclosure records with `disclosure_id`, `date`, `status`, `purpose`, `recipient_provider_id` (care transitions)
- `GET /api/patients/{patient_id}/documents` — document records with `document_id`, `type`, `date`, `status`, `patient_id` (merge packets, referral packets, care transitions)
- `GET /api/patients/{patient_id}/service-requests` — ServiceRequest records with `service_request_id`, `status`, `intent`, `priority`, `service_code`, `requester_provider_id`, `performer_provider_id`, `authored_on`, `occurrence_date`, `reason_codes` (duplicate review + SR quality)

### Duplicates and Audit
- `GET /api/duplicates/candidates` — list of duplicate candidates (merge packets)
- `GET /api/duplicates/{candidate_id}` — single duplicate candidate detail with `candidate_id`, `status`, `primary_patient_id`, `possible_duplicate_patient_id`, `match_signals`, `conflict_signals`, `merge_target_patient_id`, `merge_source_patient_id` (merge packets, duplicate review)
- `GET /api/audit-logs` — audit log entries with `audit_id`, `patient_id`, `action`, `timestamp`, `entity_type` (merge packets)

### Referrals
- `GET /api/referrals` — list of all referrals, each with `referral_id`, `patient_id`, `batch_id`, `service_line`, `requested_date`, `diagnosis_code`, `diagnosis_narrative`, `urgency`, `referral_status`, `authorization_status`, `receiving_provider_id` (referral packets, referral audits)
- `GET /api/referrals/{referral_id}` — single referral detail with same fields plus `referral_form` data (allergy info, intake notes)

### ICD-10 and Service Codes
- `GET /api/icd10` — list of ICD-10 codes (or search)
- `GET /api/icd10/{code}` — single ICD-10 code detail with `code`, `description`, `chapter` (referral packets, SR quality, audits)
- `GET /api/service-codes` — list of service codes (SR quality)
- `GET /api/service-codes/{code}` — single service code detail with `code`, `description`, `service_line` (SR quality)

### Providers
- `GET /api/providers` — list of all providers (provider lookups, cross-referencing)
- `GET /api/providers/{provider_id}` — single provider detail with `provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax` (all contact-requiring packets)

## Workflow Pattern

Every task follows the same four-phase structure. Use it as your execution scaffold:

**Phase 1 — Orient.** Read the prompt, the answer template from `input/payloads/answer_template.json`, and the environment access file. Identify the task type (merge-packet, referral-coordination, care-transition, duplicate+SR review, referral-audit) and map which endpoints you will need. Note any template fields marked as `required_value` — their values are fixed by the template itself, not discovered from the API.

**Phase 2 — Gather.** Pull data from every endpoint identified in Phase 1. When the task involves exactly one or two known patient IDs, fetch patient-level endpoints directly by ID. When the task involves a batch (referral audit), first fetch the list endpoint to enumerate records, then fetch detail records for each item. Fetch provider, ICD-10, and service-code lookups as needed for each referenced ID or code.

Make API calls in parallel when they are independent (e.g., fetching two patients' conditions simultaneously). Serialize calls only when a second call depends on values from the first.

**Phase 3 — Cross-reference and decide.** This is where governance reasoning happens. The exact logic depends on the packet type, but the common thread is comparing data from multiple sources and surfacing matches, conflicts, and gaps.

Common patterns:
- **Duplicate merge disposition**: Compare duplicate candidate signals with actual patient demographics. If match signals are strong and conflict signals are minor (e.g., address abbreviations, name variants), the merge is ready. If conflicts include different DOB or insurance, flag for review. The canonical target is the patient with the richer active record.
- **Clinical unions**: Union the `normalized_key` values from active records across both patients, excluding inactive/resolved records. Distinguish active-key unions from the full clinical list.
- **Code validation**: For each ICD-10 code, look it up in `/api/icd10/{code}`. A code is valid when it exists in the directory. Its `chapter` tells you whether it belongs to the expected service line (e.g., orthopedic referrals expect Musculoskeletal chapter codes; Injury codes are out of range for orthopedic referral-only batches unless the task says otherwise). A code matches the patient when it appears in that patient's active conditions.
- **Laterality and narrative mismatch**: Compare the ICD-10 code's laterality (embedded in the code digit for many musculoskeletal codes, e.g., M17.11 = right knee, M17.12 = left knee) with the referral's `diagnosis_narrative`. Also compare the code description with the narrative text — a lumbar radiculopathy narrative with a knee-code is a narrative mismatch.
- **Document evidence selection**: For merge packets, include documents tied to identity matching (e.g., external continuity documents shared across patients) and exclude chart summaries unless the template says otherwise. For referral packets, verify echocardiogram and office-note presence.
- **Risk flag derivation**: Map active conditions, medications, and encounter evidence to risk flags. For example: `diabetes_type_2` + `insulin_glargine` → `insulin_dependent_diabetes` + `perioperative_glucose_plan_needed`; `memory_loss` → `cognitive_memory_loss`; `latex` allergy → `latex_allergy`; osteoarthritis of hip/knee + pain medication → `fall_risk_note_required`.
- **Duplicate groups in audits**: When two referrals share the same patient_id and diagnosis_code, they form a duplicate group. Mark all group members as duplicate blockers in Tier 1 if coding or duplicate issues are urgent.
- **Insurance anomaly detection**: When two different patient records share the same `insurance_id`, flag as `shared_insurance_different_patients` with disposition `verify_insurance_membership_do_not_merge`.

**Phase 4 — Assemble and validate.** Populate the answer template with every field. Confirm:

1. All `required_top_level_keys` are present.
2. Arrays marked as sets are sorted alphabetically unless the template says otherwise.
3. Enum values match one of the `allowed_values` exactly.
4. Object arrays follow the template's sort order (usually by `referral_id` or `code`).
5. Count fields in `summary_counts` are accurate (use `wc -l` or `jq length` to verify).
6. Referenced IDs (document_ids, audit_ids, provider_ids) were actually observed in the API responses.
7. Boolean fields reflect real evidence, not defaults.

After assembly, do a final pass: read the answer template again and tick through every required key to confirm it exists and is well-typed.

## Answer Template Conformance

The answer template in `input/payloads/answer_template.json` is the authoritative schema. It may be expressed as a sample object with type annotations or as a `schema` object with `required_keys` and `fields` blocks. Either way, treat it as the contract.

Key template conventions:
- **`required_value`** on a field means you must emit exactly that string — do not look it up from the API.
- **`enum`** constraints list all legal values; your output must pick one exactly.
- **`set_semantics: true`** means the evaluator treats the array as a set; sort alphabetically unless told otherwise.
- **`ordering`** notes (e.g., "sort by referral_id ascending") are mandatory sort orders for that array.
- **`type: ["string", "null"]`** means a field can be a string or `null` — use `null` (not `"null"` or omission) when no value exists.

## Common Conventions

**Normalized keys** are snake_case identifiers (e.g., `diabetes_type_2`, `right_knee_oa`, `heart_failure_diastolic`) used across conditions, medications, and allergies to enable cross-patient comparison. Always filter to `status: "active"` for active-list unions unless the template requests a different filter.

**Sorting**: When a template says an array is a set or should be sorted, sort alphabetically using `LC_COLLATE=C sort`. For arrays of objects sorted by a key (e.g., `referral_id`), use `jq` with `sort_by(.referral_id)`.

**Deduplication**: When unioning normalized keys across patients or endpoints, remove duplicates after sorting.

**Evidence traceability**: Every ID placed in an evidence array (document_ids, audit_ids, encounter_ids) should be traceable to a specific API response. When excluding distractors, verify that excluded IDs are genuinely unrelated (wrong patient, inactive status, wrong document type) rather than just assuming.

**Provider contact selection**: When the task needs a specialist provider, prefer the one tied to the clinical context (e.g., the receiving provider on a referral, a cardiologist for a cardiology document). Fall back to the primary care provider only when the template explicitly calls for it or when no specialist is associated with the relevant evidence.

## Scripts

### fetch.sh

A reusable curl wrapper for the EHR API. Usage:

```bash
bash /work/skill/scripts/fetch.sh /api/patients/P-31014
```

It reads the base URL from the `TASK_ENV_BASE_URL` environment variable. Set that variable to the value from the prompt's `<TASK_ENV_BASE_URL>` before using the script. The script handles connection timeouts, retries once on transient failures, and outputs the raw JSON body to stdout for piping into `jq`.

Read [scripts/fetch.sh](scripts/fetch.sh) for the full implementation. Use it for every individual API call to avoid repetitive curl boilerplate.
