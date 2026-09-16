---
name: ehr-governance
description: "FHIR EHR quality-governance workflows: duplicate-chart merge readiness, referral coordination packets, care-transition handoff summaries, ServiceRequest quality review, and referral batch audits. Navigates a read-only FHIR API (patients, conditions, medications, allergies, encounters, immunizations, documents, disclosures, service requests, audit logs, duplicate candidates, referrals, ICD-10 codes, providers, service codes) and produces normalized JSON packets. Use when the task involves EHR data quality, merge packets, referral audits, care transitions, FHIR resource reconciliation, or clinical governance reporting against a structured quality-governance FHIR environment."
license: MIT
compatibility: designed for deepagents-code
---

# EHR Governance

## Quick start

This skill targets a read-only FHIR EHR quality-governance API. Every endpoint is a GET. All responses are FHIR-style JSON bundles or individual resources.

Base URL is provided by the task prompt as `<TASK_ENV_BASE_URL>`. Replace the token in every URL before calling.

### Fetching and exploring

Start every task by fetching the core objects named in the prompt:

- Patient detail: `GET /api/patients/{patient_id}`
- Active clinical lists: `GET /api/patients/{patient_id}/conditions`, `.../medications`, `.../allergies`
- Referrals: `GET /api/referrals/{referral_id}` or `GET /api/referrals`
- Duplicate candidates: `GET /api/duplicates/{candidate_id}` or `GET /api/duplicates/candidates`
- Service requests: `GET /api/patients/{patient_id}/service-requests`

Fetch all related resources the prompt references **before** building the answer JSON. The answer template in `input/payloads/answer_template.json` defines the output shape; use it to drive which endpoints to call.

### Resource shape reference

Every FHIR resource type and its key fields are documented in [references/fhir_resources.md](references/fhir_resources.md). Read that file when you need field-level detail for any resource.

### API map

All endpoints and their query parameters are listed in [references/api_endpoints.md](references/api_endpoints.md). Use it to discover available endpoints and verify you are hitting the right URL for each resource type.

## Core workflows

### Duplicate-chart merge readiness

Read [references/workflow_duplicate_merge.md](references/workflow_duplicate_merge.md) for the full step-by-step. Summary:

1. Fetch the duplicate candidate (`/api/duplicates/{candidate_id}`) to get match/conflict signals and the linked patient IDs.
2. Fetch both patients' demographics, active conditions, active medications, and active allergies.
3. Fetch audit logs and documents linked to the candidate's evidence.
4. Determine the merge target and source: the target is the active canonical record; the source is the one marked duplicate.
5. Union active clinical keys from both patients, removing inactive or stale items.
6. Reconcile the duplicate candidate's preview lists against the authoritative patient-active endpoints.
7. Classify identity match and conflict signals.
8. Identify the specialist contact if an external continuity document exists.
9. Evaluate packet readiness: ready, ready_with_review_note, or blocked.

### Referral coordination packet

Read [references/workflow_referral_coordination.md](references/workflow_referral_coordination.md) for the full step-by-step. Summary:

1. Fetch the referral detail (`/api/referrals/{referral_id}`).
2. Fetch the patient, their active conditions/medications/allergies, encounters, and documents.
3. Validate the referral's primary diagnosis code against the ICD-10 directory.
4. Check for narrative/laterality mismatches between the referral narrative and the ICD-10 description.
5. Assess allergy readiness: check for documented allergies, completeness, and conflicts.
6. Identify the most recent relevant encounter related to the referral reason.
7. Verify required documents (e.g., echocardiogram for cardiology, office notes).
8. Determine authorization status and overall readiness.
9. Highlight referral-relevant medications.
10. Choose normalized referral-letter field values from the enumerated choices.

### Care transition packet

Read [references/workflow_care_transition.md](references/workflow_care_transition.md) for the full step-by-step. Summary:

1. Fetch the patient detail, active conditions/medications/allergies, encounters, immunizations, disclosures, and documents.
2. Identify the recipient provider from the provider directory.
3. Select the four most recent handoff-relevant encounters within the transition window, excluding stale or unrelated encounters.
4. Find the latest immunization record.
5. Find the applicable disclosure for the recipient.
6. Derive risk flags from active conditions, medications, and allergies.
7. Build risk-flag evidence linking each flag to its supporting condition keys, medication keys, and encounter IDs.
8. Assess packet readiness.

### ServiceRequest quality review

Read [references/workflow_service_request_quality.md](references/workflow_service_request_quality.md) for the full step-by-step. Summary:

1. Fetch the ServiceRequest, patient, duplicate candidate, and provider records.
2. Validate the ServiceRequest service code against the service-codes directory.
3. Validate each FHIR reasonCode against the ICD-10 directory.
4. Check that each reason code matches patient evidence (conditions or encounter diagnoses).
5. Determine the performer's service line from the provider directory.
6. Evaluate SBAR coverage: situation, background, assessment, recommendation.

### Referral batch audit

Read [references/workflow_referral_audit.md](references/workflow_referral_audit.md) for the full step-by-step. Summary:

1. Fetch the full referral list and filter for the target batch.
2. For each referral, fetch the patient, ICD-10 code detail, and provider.
3. Classify invalid/out-of-range diagnosis codes (wrong ICD-10 chapter for the service line).
4. Detect laterality or narrative mismatches between the referral narrative and ICD-10 terms.
5. Group duplicate referrals by patient (same patient resubmissions).
6. Detect insurance anomalies (shared insurance across different patients).
7. Build follow-up queues: authorization missing/pending, records requests, imaging follow-up.
8. Assign Tier 1/2/3 action plans.
9. Compute summary counts.

## General rules

### Normalized keys

Many outputs use `normalized_key` values. Derive them by lowercasing the name, replacing spaces/dashes with underscores, and stripping punctuation. The API responses include these keys directly. Prefer the API's `normalized_key` field when present. If absent, derive the key from the resource's `code.text` or `name` field.

### ICD-10 validation

ICD-10 codes are validated via `GET /api/icd10/{code}`. Each resource has `code`, `chapter`, and `description`. For orthopedic referrals the expected chapter is "Musculoskeletal"; for cardiology, "Circulatory". Injury codes (S/T prefix) usually map to the "Injury" chapter and are out-of-range for orthopedic and cardiology service lines.

### Set semantics

Arrays described as sets should be sorted alphabetically ascending unless the template explicitly states otherwise. Use the template's `ordering` guidance when present.

### Null handling

When a field accepts `null` (e.g., `merge_target_patient_id` when no merge is recommended), emit JSON `null`, not the string `"null"` or an empty string.

### Enum values

Always use the exact enum string values from the answer template. Do not invent new enum values or paraphrase existing ones.
