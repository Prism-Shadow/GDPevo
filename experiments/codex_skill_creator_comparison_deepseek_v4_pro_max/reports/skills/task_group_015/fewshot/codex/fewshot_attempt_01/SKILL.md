---
name: ehr-quality-packet
description: Prepare normalized EHR quality-governance JSON packets using a read-only FHIR-aligned REST API. Use when the task requires gathering patient data, reconciling clinical lists, validating codes against ICD-10, comparing duplicate candidates, assembling referral coordination or care-transition packets, auditing referral batches, or producing any structured quality-governance output against a provided answer template. Triggers on tasks that mention EHR, FHIR, duplicate merge, referral coordination, care transition, quality governance, clinical reconciliation, or packet assembly with an answer_template.json payload.
---

# EHR Quality Packet

Prepare normalized quality-governance JSON packets from a read-only EHR REST API.

## Core Workflow

Every task follows the same three-stage pipeline:

1. **Read the answer template** from `input/payloads/answer_template.json`. The template defines every required key, allowed enum value, array ordering rule, and field type. Never deviate from the template shape.
2. **Gather evidence** from the API endpoints listed in [API Endpoints](references/api_endpoints.md). Start broad (patient/referral/duplicate detail), then narrow into sub-resources (conditions, medications, allergies, encounters, documents, immunizations, disclosures, audit logs, service requests). Cross-check relevant codes against ICD-10 and service-code directories. Look up providers by ID in the provider directory.
3. **Reconcile and output** normalized JSON matching the template exactly. Apply the reconciliation rules in the relevant packet pattern guide (see references/).

## API Usage Rules

- The API base URL is provided as `<TASK_ENV_BASE_URL>` in the prompt. Resolve it to a concrete value before making any request.
- All endpoints are **read-only GET**. No POST, PUT, or DELETE.
- Patient-scoped endpoints accept `{patient_id}` as a path parameter.
- Endpoint catalog: [API Endpoints](references/api_endpoints.md)

## Normalization Rules

Apply these rules to every packet, regardless of type:

### Active vs. Inactive Filtering

- **Conditions**: keep only items where `clinical_status` is `"active"`. Discard `"inactive"`, `"resolved"`, `"remission"`, and `"entered-in-error"`.
- **Medications**: keep only items where `status` is `"active"`. Discard `"inactive"`, `"completed"`, `"stopped"`, `"entered-in-error"`, `"unknown"`.
- **Allergies**: keep only items where `status` is `"active"`. Discard `"inactive"`, `"resolved"`, `"entered-in-error"`.
- **Immunizations**: take only the most recent by `date`.
- **Disclosures**: require `status` of `"permitted"` for the recipient.

### Key Set Operations

- Clinical records carry a `normalized_key` field. Use this key (not display text or code) for union, intersection, and set-difference operations.
- When computing clinical unions across two patients, take the **set union** of their active `normalized_key` values.
- Arrays described as "sets" in the template must be **sorted alphabetically** (ascending) unless the template specifies a different order.

### Date Formatting

- All dates use `YYYY-MM-DD` strings.

### Document Selection

- Select documents that are relevant to the packet purpose (identity/continuity, clinical evidence, referral requirements). Exclude `chart_summary`, `care_plan`, and other non-evidentiary types unless the template demands them.
- Document selection policy for merge packets: identity or external continuity documents only. For referral packets: echo, office notes, and required imaging.

### Encounter Selection

- Sort encounters by `date` descending (newest first).
- Select the most recent relevant encounters based on the packet window. For care transitions, select the four most recent surgical-handoff-relevant encounters. Exclude encounters outside the window, unsigned drafts, or clearly unrelated encounters.

### Code Validation

- Look up ICD-10 codes via `GET /api/icd10/{code}`. Validate that the code exists and its `chapter` matches the expected service line (e.g., Musculoskeletal for orthopedics, Circulatory for cardiology).
- Look up service codes via `GET /api/service-codes/{code}`.

### Demographic Comparison

- Compare patient demographic fields to derive match and conflict signals for duplicate candidates.
- Common match signals: `same_dob`, `same_insurance`, `same_phone`, `similar_address`, `same_given_name`, `name_variant`, `shared_external_cardiology_document`.
- Common conflict signals: `different_given_name`, `different_phone`, `different_dob`, `different_insurance`, `different_address`, `opposite_laterality_problem`, `address_abbreviation`.

### Provider Selection

- Fetch provider details from `GET /api/providers/{provider_id}`.
- The primary care provider is the one referenced in the patient's `primary_care_provider_id` field.
- Specialist providers are identified from document authors, referral performer fields, or service request performer fields.

## Packet Type Reference

Each packet type has a guide with task-specific reconciliation rules:

- **Duplicate Merge Readiness**: [Duplicate Merge Packet](references/duplicate_merge.md)
- **Referral Coordination**: [Referral Coordination Packet](references/referral_coordination.md)
- **Care Transition**: [Care Transition Packet](references/care_transition.md)
- **Duplicate + ServiceRequest Quality Review**: [Duplicate SR Review](references/duplicate_sr_review.md)
- **Referral Batch Audit**: [Referral Audit](references/referral_audit.md)

If the task does not clearly match one of these, combine the normalization rules above with the answer template to derive the correct output shape.

## Traps to Avoid

- Do not include inactive/resolved/entered-in-error clinical records in active key arrays.
- Do not include chart-summary or non-evidentiary documents in evidence arrays.
- Do not copy provider IDs from referral/duplicate fields without verifying them against the provider directory.
- Do not emit arrays unsorted when the template says they are sets.
- Do not emit null for required string fields unless the template explicitly permits null.
- When a duplicate candidate exists, always cross-check the duplicate preview data against the patient active-list endpoints. The patient endpoints are authoritative for active clinical keys.
