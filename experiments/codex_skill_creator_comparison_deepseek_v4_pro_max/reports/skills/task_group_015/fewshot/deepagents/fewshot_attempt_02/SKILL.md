---
name: ehr-quality-governance
description: Navigate a FHIR-style EHR quality-governance REST API to produce normalized clinical packets. Use when a task involves preparing merge-readiness packets, referral coordination documents, care-transition summaries, service-request quality reviews, or batch referral audits against a healthcare API. Covers duplicate-chart review, active clinical-list reconciliation, ICD-10 validation, identity-signal analysis, encounter selection for handoffs, allergy-readiness checks, authorization tracking, provider-directory lookup, document/audit evidence gathering, and risk-flag derivation. Recognize triggers like EHR quality governance, duplicate merge packet, referral coordination, care transition packet, orthopedic referral audit, or any prompt referencing a TASK_ENV_BASE_URL healthcare API with patient/condition/medication/allergy/encounter/document/ICD-10/provider endpoints.
---

# EHR Quality Governance

## Core Concepts

### Task Environment URL

Prompts use `TASK_ENV_BASE_URL` as a placeholder. Replace it with the actual base URL from `environment_access.md` or the task-provided value before making any API call.

### Normalized Keys

Every condition, medication, and allergy record returned by the patient endpoints carries a `normalized_key` field. This is a lowercase, underscore-delimited string (e.g. `hypertension`, `right_knee_oa`, `insulin_glargine`, `latex`). These keys are the primary identifiers for clinical list operations. Always sort arrays of normalized keys alphabetically.

### Active vs. Inactive Records

Clinical list endpoints return records with a `status` field. For conditions, medications, and allergies, filter to `"active"` status for current clinical context. Inactive, `"entered-in-error"`, and `"resolved"` records are distractors and go into excluded/distractor arrays when the template asks for them.

### Sorting and Set Semantics

Arrays that the template marks as sorted or as sets must be sorted alphabetically (ascending) unless the template explicitly states otherwise (e.g. encounter arrays sorted by date newest-first). For arrays of objects, sort by the designated sort key (typically `referral_id`, `code`, or `group_id`). Set semantics mean an array is treated as unordered at comparison time, but you must still emit a deterministic order.

### Controlled Enums

Many template fields use `enum:` with a fixed set of values. Choose exactly one value from the listed set. Do not invent new enum values.

### Template Conformance

Every task specifies an `answer_template.json` payload. The output JSON must use the exact top-level keys, field names, and types defined in the template. If a field is optional and no data exists, use `null` for nullable fields or an empty array `[]` for array fields.

---

## API Navigation

The EHR environment exposes these endpoint families. See [references/api_endpoints.md](references/api_endpoints.md) for the full endpoint inventory with paths, parameters, and response field notes.

### Primary Lookup Flow

For any task involving a patient, start with the patient detail endpoint, then pull clinical lists in parallel:

1. `GET /api/patients/{patient_id}` — demographics, MRN, name, DOB
2. `GET /api/patients/{patient_id}/conditions` — active/inactive conditions with ICD-10 codes and normalized_keys
3. `GET /api/patients/{patient_id}/medications` — drug records with normalized_keys
4. `GET /api/patients/{patient_id}/allergies` — allergen records with normalized_keys

For tasks involving encounters, documents, immunizations, or disclosures, also pull:

- `GET /api/patients/{patient_id}/encounters`
- `GET /api/patients/{patient_id}/documents`
- `GET /api/patients/{patient_id}/immunizations`
- `GET /api/patients/{patient_id}/disclosures`
- `GET /api/patients/{patient_id}/service-requests`

### Provider Lookup

Use `GET /api/providers` to list all providers and `GET /api/providers/{provider_id}` for a single provider. Each provider record includes `name`, `role`, `service_line`, `facility`, `phone`, `fax`.

### ICD-10 Validation

Use `GET /api/icd10/{code}` to look up a diagnosis code. The response includes `code`, `description`, `chapter`, and `laterality` fields. Validate that:

- The code exists and resolves (not unknown)
- Its chapter is appropriate for the service line (e.g. Musculoskeletal for orthopedics, Circulatory for cardiology)
- Its description and laterality match the referral narrative

### Duplicate and Referral Endpoints

- `GET /api/duplicates/candidates` and `GET /api/duplicates/{candidate_id}` for duplicate-chart review
- `GET /api/referrals` and `GET /api/referrals/{referral_id}` for referral detail
- `GET /api/audit-logs` for audit trail records
- `GET /api/service-codes` and `GET /api/service-codes/{code}` for service code validation

### Request Strategies

- Fetch all patient endpoints simultaneously — they are independent.
- Fetch all referral/search endpoints in parallel when auditing a batch.
- When validating a batch of referrals, batch ICD-10 lookups in parallel.
- Use the full response payloads; do not truncate or filter prematurely.

---

## Task-Type Workflows

### 1. Duplicate-Chart Merge Readiness

Steps:

1. Fetch the duplicate candidate from `/api/duplicates/{candidate_id}`. Note `match_signals`, `conflict_signals`, and the two `patient_ids`.
2. Fetch patient demographics for both patients in parallel.
3. Fetch conditions, medications, and allergies for both patients in parallel. Filter to `status: "active"`.
4. Compute the union of active normalized_keys across both patients for conditions, medications, and allergies.
5. Reconcile: compare the duplicate-candidate preview listed keys against the actual patient endpoint results. Any key present in a patient endpoint but absent from the duplicate preview goes into the `*_added_from_active_endpoints` arrays.
6. Identify identity signals: match which demographic fields agree vs. conflict, noting exact matches (same value) and surface-level mismatches (variant names, address abbreviations). Derive match_signals and conflict_signals from the evidence — prefer the duplicate candidate's own signal lists, then supplement with demographic field comparisons.
7. Pull documents and audit logs. Include only documents relevant to identity or external continuity (e.g. shared external specialist documents, merge-specific documents). Exclude unrelated chart summaries.
8. Select the canonical merge target: the record with active clinical data and identity primacy. The other record is the merge source.
9. Determine disposition: `merge_ready` (strong match, few/no conflicts), `merge_ready_with_conflict_review`, `needs_manual_review`, or `do_not_merge`.
10. Pick the specialist provider contact from the provider directory — typically the provider on the shared external continuity document or the primary care provider on the target record.

### 2. Referral Coordination Packet

Steps:

1. Fetch the referral from `/api/referrals/{referral_id}`. Extract `patient_id`, `service_line`, `diagnosis_code`, `narrative`, `authorization_status`, `urgency`, `referral_status`.
2. Fetch patient detail and active conditions, medications, and allergies in parallel.
3. Look up the primary diagnosis code via `/api/icd10/{code}`. Validate: code exists, chapter matches the service line, description matches the narrative.
4. Build the active diagnosis list from the patient conditions and the referral intake narrative. Mark referral-relevant diagnoses (those tied to the service line or the referral reason).
5. Assess allergy readiness: pull patient allergies, mark statuses, and check if a documented allergy statement exists in the referral form.
6. Find the most recent relevant encounter. Look for office visits near the referral date where diagnosis codes and medications mentioned align with the referral reason. Prefer signed encounters.
7. Check required documents: echocardiogram (for cardiology), office notes, authorization records, medication lists. Flag missing documents.
8. Identify the receiving provider from the referral `performer_provider_id` and the provider directory.
9. Build medication highlights: pull active medications, tag those relevant to the referral (e.g. diuretics for heart failure, antihypertensives for blood pressure).
10. Fill the `referral_letter_fields`: choose the single best enum value for each letter section based on the evidence gathered.

### 3. Care Transition Packet

Steps:

1. Fetch patient detail and the target recipient provider.
2. Fetch active conditions, medications, allergies in parallel. Extract normalized_keys, sort alphabetically.
3. Fetch all encounters. Select the four most recent handoff-relevant encounters by date, newest first. Exclude encounters that are stale, outside the surgical handoff window, or unrelated.
4. Fetch immunizations. Select the single most recent immunization by date.
5. Fetch disclosures. Check for one that matches the target provider ID and has `status: "permitted"` for the handoff purpose.
6. Derive risk flags from clinical evidence:
   - `cognitive_memory_loss`: condition key `memory_loss` present
   - `fall_risk_note_required`: lower-extremity OA conditions (hip, knee) plus relevant medications
   - `hypertension`: condition key `hypertension` present
   - `insulin_dependent_diabetes`: `diabetes_type_2` + insulin medication
   - `latex_allergy`: allergy key `latex` present
   - `perioperative_glucose_plan_needed`: diabetes + insulin, especially when a recent care-transition encounter exists
7. Build risk flag evidence objects: for each flag, populate condition_keys, medication_keys, and encounter_ids from the records that support the flag.
8. Determine packet readiness: `ready` if no blockers, `ready_with_risk_flags` if risk flags exist but no blockers, `not_ready` if critical data is missing or disclosure is not permitted.

### 4. Service-Request Quality Review

Steps:

1. Fetch the duplicate candidate to assess merge vs. no-merge for the underlying patients.
2. Fetch the ServiceRequest from `/api/patients/{patient_id}/service-requests` and filter for the given `SR-*` ID.
3. Validate service code via `/api/service-codes/{code}`.
4. Validate each reason code via `/api/icd10/{code}`: check validity, chapter, and whether it matches the patient active condition evidence.
5. Assess SBAR coverage: the ServiceRequest narrative body is expected to contain Situation, Background, Assessment, and Recommendation sections. Check which sections are present.
6. Output the duplicate review decision: `merge`, `review_hold`, or `do_not_merge` with match/conflict signals.

### 5. Batch Referral Audit

Steps:

1. Fetch all referrals via `GET /api/referrals`. Filter to the target batch by `batch_id`.
2. Count total rows and unique patients for the batch summary.
3. For each referral, look up its ICD-10 code in parallel. Flag as `out_of_range_chapter` if the ICD-10 chapter differs from the expected service-line chapter (e.g. non-Musculoskeletal codes in an orthopedics batch). Flag as `unknown_code` if the code does not resolve.
4. Detect laterality and narrative mismatches: compare the ICD-10 description (and laterality, if present) against the referral narrative. Flag `laterality_mismatch` when the ICD-10 code implies a different side than the narrative describes, `narrative_mismatch` when the code description does not match the narrative topic, and `missing_laterality` when the code carries laterality data but the narrative omits it. Do not flag codes already in the out-of-range list — each referral appears in at most one of the two mismatch lists.
5. Detect duplicates: referrals with the same patient_id and same diagnosis_code are candidate duplicates. Group under a `DUP-REF-*` group ID with type `same_patient_resubmission`.
6. Detect insurance anomalies: two different patients sharing the same insurance ID across referrals in the batch. Do not merge these; flag for insurance-membership verification with type `shared_insurance_different_patients`.
7. Build follow-up queues: sort referral IDs into `authorization_missing`, `authorization_pending`, `records_request` (missing office notes), and `imaging_follow_up` (missing or pending imaging).
8. Assign tiers:
   - **Tier 1**: urgent coding or duplicate-blocker referrals (duplicate primary, laterality mismatches on urgent referrals)
   - **Tier 2**: routine coding, authorization, or document blockers
   - **Tier 3**: administrative document-completion items with no clinical urgency
9. Assign owner providers from the provider directory — typically the orthopedic surgeon listed on the referral or the performer provider on the referral record.
10. Compute summary counts for all categories: total rows, unique patients, urgency counts, mismatch counts, queue sizes, and tier counts.

---

## Reference Files

- [api_endpoints.md](references/api_endpoints.md) — Complete inventory of available REST endpoints with paths, parameters, and response field notes.
- [normalization_conventions.md](references/normalization_conventions.md) — Detailed rules for normalized_keys, sorting, set semantics, and distractor handling.
