---
name: ehr-quality-governance
description: Solve EHR quality-governance packet tasks (merge readiness, referral coordination, care transitions, duplicate review, referral batch audit) by querying a shared read-only FHIR-like REST API, normalizing clinical keys, validating ICD-10 codes, reconciling active lists, and assembling structured JSON outputs from supplied templates.
---

# EHR Quality Governance Skill

This skill handles five healthcare quality-governance task types that query a shared read-only EHR API. The API base URL is provided inline as `<TASK_ENV_BASE_URL>` in each prompt. All endpoints return JSON; every response includes a top-level plural key matching the resource type.

## API Reference

The base URL is always provided in the prompt as `<TASK_ENV_BASE_URL>`. Substitute it in all calls below.

### Core resource endpoints

| Method | Path | Top-level key in response |
|--------|------|--------------------------|
| GET    | `/health` | `status`, `record_counts`, `state_mode` |
| GET    | `/api/patients` | `patients` |
| GET    | `/api/patients/{id}` | (single object) |
| GET    | `/api/patients/{id}/conditions` | `conditions` |
| GET    | `/api/patients/{id}/medications` | `medications` |
| GET    | `/api/patients/{id}/allergies` | `allergies` |
| GET    | `/api/patients/{id}/encounters` | `encounters` |
| GET    | `/api/patients/{id}/immunizations` | `immunizations` |
| GET    | `/api/patients/{id}/documents` | `documents` |
| GET    | `/api/patients/{id}/service-requests` | `service_requests` |
| GET    | `/api/patients/{id}/disclosures` | `disclosures` |
| GET    | `/api/duplicates/candidates` | `duplicate_candidates` |
| GET    | `/api/duplicates/{candidate_id}` | (single object) |
| GET    | `/api/referrals` | `referrals` |
| GET    | `/api/referrals/{referral_id}` | (single object) |
| GET    | `/api/icd10` | `icd10` |
| GET    | `/api/icd10/{code}` | (single object) |
| GET    | `/api/providers` | `providers` |
| GET    | `/api/providers/{provider_id}` | (single object) |
| GET    | `/api/service-codes` | `service_codes` |
| GET    | `/api/service-codes/{code}` | (single object) |
| GET    | `/api/audit-logs` | `audit_logs` |

There is no search by batch, patient, or referral from top-level lists. Filter client-side by comparing fields like `batch_id`, `patient_id`, or `candidate_id` in the returned arrays.

### Entity data shapes

**Patient** (`/api/patients`, `/api/patients/{id}`): `patient_id`, `enterprise_mrn`, `display_name`, `given_name`, `family_name`, `suffix`, `dob` (YYYY-MM-DD), `sex`, `address`, `phone`, `insurance_id`, `canonical_status` (one of: `active`, `duplicate`, `possible_duplicate`), `canonical_patient_id` (null or string id of the canonical record), `primary_care_provider_id`, `primary_care_provider` (embedded object with `provider_id`, `name`, `role`, `facility`, `phone`, `fax`, `service_line`).

**Condition** (`/api/patients/{id}/conditions`): `id`, `patient_id`, `code` (ICD-10), `description`, `normalized_key`, `status` (one of: `active`, `inactive`), `source`, `onset_date`. Only `active` conditions are relevant for clinical unions and packet contexts. Inactive conditions are distractors.

**Medication** (`/api/patients/{id}/medications`): `id`, `patient_id`, `medication` (display name), `normalized_key`, `dose`, `route`, `frequency`, `status` (one of: `active`, `inactive`), `source`. Only `active` medications belong in unions.

**Allergy** (`/api/patients/{id}/allergies`): `id`, `patient_id`, `allergen`, `normalized_key`, `reaction`, `severity` (one of: `mild`, `moderate`, `severe`), `status` (one of: `active`, `inactive`), `source`. Only `active` allergies belong in unions.

**Encounter** (`/api/patients/{id}/encounters`): `encounter_id`, `patient_id`, `date` (YYYY-MM-DD), `type`, `provider_id`, `diagnoses` (array of ICD-10 codes), `medications_mentioned` (array of medication names, not normalized keys), `care_plan_notes`, `signed_status` (one of: `signed`, `unsigned`, `amended`, `draft`).

**Immunization** (`/api/patients/{id}/immunizations`): `id`, `patient_id`, `vaccine`, `date` (YYYY-MM-DD).

**Disclosure** (`/api/patients/{id}/disclosures`): `disclosure_id`, `patient_id`, `date`, `status` (one of: `permitted`, `pending`, `denied`, `expired`), `purpose`, `recipient`, `recipient_provider_id`.

**Document** (`/api/patients/{id}/documents`): `document_id`, `patient_id`, `type`, `date` (YYYY-MM-DD), `status` (one of: `final`, `preliminary`, `cancelled`), `source`.

**ServiceRequest** (`/api/patients/{id}/service-requests`): `service_request_id`, `patient_id`, `status` (one of: `draft`, `active`, `on-hold`, `revoked`, `completed`, `entered-in-error`), `intent` (one of: `proposal`, `plan`, `order`, `original-order`, `reflex-order`, `filler-order`, `instance-order`, `option`), `priority` (one of: `routine`, `urgent`, `asap`, `stat`), `service_code`, `requester_id`, `performer_id`, `authored_on`, `occurrence_date`, `reason_codes` (array of ICD-10 strings), `sbar` (object with `situation`, `background`, `assessment`, `recommendation`).

**DuplicateCandidate** (`/api/duplicates/candidates`, `/api/duplicates/{id}`): `candidate_id`, `status` (one of: `open`, `needs_review`), `patient_ids` (array of two), `match_signals` (array of strings), `conflict_signals` (array of strings), `merge_preview` (object with `preferred_target_patient_id`, `source_patient_id`, `active_condition_keys`, `active_medication_keys`, `active_allergy_keys`).

**Referral** (`/api/referrals`, `/api/referrals/{id}`): `referral_id`, `patient_id`, `batch_id`, `service_line`, `requested_date`, `diagnosis_code` (ICD-10), `diagnosis_narrative`, `status` (one of: `open`, `closed`, `cancelled`, `draft`), `urgency` (one of: `routine`, `urgent`, `stat`), `authorization_status` (one of: `approved`, `pending`, `denied`, `missing`), `documents_received` (array of strings like `mri`, `office_note`, `xray`, `insurance_card`, `physical_therapy_note`), `coordination_note`, `receiving_provider_id`.

**ICD-10** (`/api/icd10`, `/api/icd10/{code}`): `code`, `chapter`, `expected_terms` (array of strings), `requires_laterality` (boolean).

**Provider** (`/api/providers`, `/api/providers/{id}`): `provider_id`, `name`, `role`, `facility`, `phone`, `fax`, `service_line`.

**ServiceCode** (`/api/service-codes`, `/api/service-codes/{code}`): `code`, `display`, `service_line`, `order_kind`, `active`.

**AuditLog** (`/api/audit-logs`): `audit_id`, `patient_id`, `date`, `event`, `actor`, `summary`.

### Normalized key conventions

The API uses `normalized_key` on conditions, medications, and allergies. Common keys include:

- Condition keys: `diabetes_type_2`, `hypertension`, `coronary_artery_disease`, `copd`, `right_knee_oa`, `left_knee_oa`, `right_hip_oa`, `left_hip_oa`, `right_medial_meniscus_tear`, `heart_failure_diastolic`, `dyspnea`, `memory_loss`.
- Medication keys: `aspirin`, `metformin`, `furosemide`, `lisinopril`, `insulin_glargine`, `acetaminophen`, `baseline_med`.
- Allergy keys: `penicillin`, `iodinated_contrast`, `latex`, `sulfa_antibiotics`, `baseline_allergy`.

The key `baseline_med` is a catch-all for non-distinctive active meds (e.g., atorvastatin, albuterol). Similarly `baseline_allergy` for non-distinctive allergies (e.g., sulfa, latex-rash at moderate-or-less severity). When constructing unions, include distinct keys and a single `baseline_med` / `baseline_allergy` if any baseline items exist, but do not duplicate them.

### Client-side query patterns

Parallelize independent endpoint calls. When a task involves two patients (merge, duplicate review), fetch both patients and all their sub-resources (conditions, medications, allergies, documents) in parallel. When a task involves a batch, fetch all referrals once, then filter client-side.

## Task Type 1: Duplicate-Chart Merge Readiness Packet

**Input signal**: Prompt names a duplicate candidate ID (like `DUP-CANDIDATE-01`) and two patient IDs. A `merge_packet_request.json` payload may be present.

**Output**: Normalized JSON conforming to the supplied `answer_template.json`. Key sections:

### Merge target/source and disposition

1. Fetch the duplicate candidate by ID. The `merge_preview.preferred_target_patient_id` points to the canonical target. The `source_patient_id` is the other. `disposition` is `ready_to_merge` when the candidate is `open` with strong match signals.
2. Fetch both patients. The target must have `canonical_status: "active"`. The source should have `canonical_status: "duplicate"` or `"possible_duplicate"`, and its `canonical_patient_id` should point to the target.
3. `canonical_reason_codes` are drawn from the evidence: `matching_identity_signals`, `source_marked_duplicate_to_target`, `target_active_canonical_record`.

### Clinical unions and active list reconciliation

1. Fetch conditions, medications, and allergies for both patients. Collect only records with `status: "active"`.
2. Union the `normalized_key` values from both patients, deduplicated and sorted alphabetically.
3. Compare against the `merge_preview` keys from the duplicate candidate endpoint. The merge_preview may miss keys that the patient endpoints expose. Any key present in patient active endpoints but missing from the merge_preview goes into `active_list_reconciliation` as "added from active endpoints."
4. The `authoritative_source` is always `patient_active_list_endpoints_over_duplicate_preview`.

### Identity signals

1. Match signals come from the duplicate candidate's `match_signals` array. Report them sorted.
2. Conflict signals come from `conflict_signals`. Report them sorted.
3. `demographic_matches` and `demographic_conflicts` are derived from comparing patient fields: `dob`, `sex`, `insurance_id`, `phone`, `primary_care_provider_id`, `address`, `given_name`. Exact matches are matches; differences (including nicknames like Sam/Samuel, abbreviations like St/Street) are conflicts.

### Evidence and excluded distractors

1. Fetch documents for both patients. Include only documents that support identity (`identity_verification`) or external continuity (`external_cardiology_note`) in the packet. Exclude `chart_summary` documents and any documents unrelated to identity or external continuity.
2. Fetch all audit logs. Include only audit entries that reference either patient ID in a merge-relevant event (`identity_review`, `external_import`).
3. `excluded_distractors` contains inactive conditions/medications, excluded document IDs, and audit IDs not related to the merge.

### Packet contact

1. Fetch providers to resolve the `primary_care_provider` (from the target patient's `primary_care_provider` field) and any `specialist_provider` noted in evidence. The specialist is typically the provider associated with an external continuity document on the source patient.
2. Include `contact_reason` on the specialist explaining their relevance.

## Task Type 2: Referral Coordination Packet

**Input signal**: Prompt names a referral ID and patient ID, a service line, and a batch ID.

**Output**: Normalized JSON conforming to the supplied `answer_template.json`.

### Patient referral header

Extract `patient_id`, `referral_id`, `batch_id`, `service_line`, `requested_date` from the referral object.

### Active diagnoses and referral code set

1. Fetch referral by ID. Fetch patient conditions. Fetch ICD-10 directory.
2. Build `active_diagnoses` from all active conditions plus the referral's intake diagnosis. For each: include `code`, `description`, `normalized_key`, `source`, `referral_relevant` (boolean). A diagnosis is referral-relevant if its code matches the referral's `diagnosis_code` or it was sourced from a referral intake.
3. The `referral_code_set.primary_code` is the referral's `diagnosis_code`. `supporting_codes` include any active condition codes that support the same clinical concern.
4. ICD validation: look up the primary code in the ICD-10 directory. If found and the chapter matches the service line's expected chapter, `icd_validation` is `valid_matches_narrative`. Validate `narrative_match` by checking the referral's `diagnosis_narrative` against the code's `expected_terms`.
5. `primary_code_chapter` comes from the ICD-10 lookup.

**ICD-10 chapter to service line mapping:**

- `orthopedics` expects `Musculoskeletal` chapter codes. Also accepts `Injury` chapter codes when they describe musculoskeletal injuries (e.g., meniscus tears). All codes outside `Musculoskeletal` for an orthopedic referral are out-of-range unless the referral has a specific clinical justification recorded.
- `cardiology` expects `Circulatory` chapter codes.
- `pulmonology` expects `Respiratory` chapter codes.
- `neurology` expects `Nervous system` chapter codes.

### Allergy readiness

Fetch patient allergies. Include all active allergies with `allergen`, `reaction`, `severity`, `status`, and `source`. `readiness_status` is:
- `complete_documented` when active allergies are clearly recorded.
- `incomplete_needs_clarification` when there is a coordination note suggesting allergy confirmation needed.
- `no_known_allergies` when the patient has no active allergy records.

### Recent encounter evidence

Fetch patient encounters. Select the most recent encounter whose `care_plan_notes` or `diagnoses` match the referral's clinical concern (the referral's `diagnosis_code` or related conditions). Report the encounter as the primary evidence with its diagnoses and medications mentioned. The `care_plan_tag` should reflect the referral purpose.

### Required document evidence

Fetch patient documents. Identify required documents for the referral type. For cardiology referrals, an echocardiogram is typically required. Check the referral's `documents_received` array for `"echocardiogram"`. An office note document with relevant diagnoses is also required.

### Receiving provider

Look up the referral's `receiving_provider_id` in the provider directory.

### Authorization readiness

From the referral: `authorization_status`, `status` (as `referral_status`), `urgency`. Overall readiness:
- `ready_to_send` when authorization is approved, referral is open, no blocking issues.
- `hold_for_authorization` when authorization is missing or pending.
- `hold_for_missing_documents` when required documents are absent.
- `hold_for_clinical_clarification` when coordination notes indicate unresolved concerns.

### Medication highlights

Fetch patient medications. Select active medications that are clinically relevant to the referral. Assign `highlight_reason` based on clinical relevance (e.g., `heart_failure_diuretic` for furosemide in cardiology, `blood_pressure_management` for lisinopril).

### Referral letter fields

These are enumerated-choices derived from the evidence above. Choose the enum value that best describes the assembled evidence for each section.

## Task Type 3: Care Transition Packet

**Input signal**: Prompt names a patient ID and a recipient provider ID, with a service line context.

**Output**: Normalized JSON conforming to the supplied `answer_template.json`.

### Patient and recipient

Fetch patient by ID. Report `patient_id`, `enterprise_mrn`, `display_name`, `dob`. Fetch provider by ID for `recipient`.

### Active clinical lists

Fetch patient conditions, medications, allergies. Collect only active records. Extract `normalized_key` values, deduplicate, sort alphabetically.

### Handoff encounters

Fetch patient encounters. Select encounters relevant to the transition's service line. Exclude encounters that are stale (too far outside the surgical/transition window) or unrelated (diagnoses not matching the service line's domain). Include the most relevant ones sorted newest to oldest. The number may vary but is typically 3-5; use the template's required count as guidance.

An encounter is relevant if its diagnoses include codes that map to the target service line (e.g., `M16.11`, `M17.11`, `S83.*` for orthopedics). The `care_transition` type encounter is particularly relevant.

### Source selection

Report which encounters were selected and which were excluded. `selection_basis` describes the rule (e.g., `orthopedic_surgical_handoff_window`). Excluded encounters are stale, outside the care window, or have diagnoses unrelated to the service line.

### Latest immunization

Fetch patient immunizations. Select the single most recent immunization.

### Disclosure

Fetch patient disclosures. Select the disclosure whose `recipient_provider_id` matches the packet recipient and whose `purpose` matches the transition context. The disclosure should have `status: "permitted"` for a ready packet.

### Risk flags and evidence

Derive from active conditions, medications, and encounter data:
- `cognitive_memory_loss`: when a `memory_loss` condition key is active.
- `fall_risk_note_required`: when lower-extremity OA conditions exist (hip/knee OA) plus analgesic medications.
- `hypertension`: when hypertension is active.
- `insulin_dependent_diabetes`: when diabetes is active and insulin is prescribed.
- `latex_allergy`: when a latex allergy is active.
- `perioperative_glucose_plan_needed`: when diabetes is active and insulin is prescribed, indicating perioperative glucose management.

For each risk flag, provide evidence: which condition keys, medication keys, and encounter IDs support it. Encounter evidence comes from encounters where the relevant diagnoses appear.

### Packet readiness

`ready_to_send: true` when all required components are present (patient, recipient, active lists, encounters, immunization, disclosure, and disclosure is `permitted`). `status` is `ready_with_risk_flags` when risk flags are present but no blocking issues exist. `status` is `not_ready` when a required component is missing. `blocking_issue_codes` lists applicable blockers.

## Task Type 4: Duplicate Review plus ServiceRequest Quality

**Input signal**: Prompt names a duplicate candidate ID, two patient IDs, and a ServiceRequest ID.

**Output**: Normalized JSON conforming to the supplied `answer_template.json`.

### Duplicate review

1. Fetch the duplicate candidate by ID. Report `candidate_id`, `candidate_status` (from the candidate's `status` field), and derive `decision`:
   - `merge` when `status` is `open` and match_signals clearly outweigh conflicts.
   - `review_hold` when `status` is `needs_review` -- especially when there is `opposite_laterality_problem` or significant identity conflicts.
   - `do_not_merge` when conflicts are definitive and evidence points to truly different patients.
2. When `decision` is `review_hold`, `merge_target` and `merge_source` are `null`.
3. Report `match_signals` and `conflict_signals` directly from the candidate.

**Identifying opposite laterality**: Compare the active condition keys of both patients. If one patient has `right_knee_oa` and the other has `left_knee_oa` (mirror-image), that is an `opposite_laterality_problem` -- they may be different people with mirror-image conditions rather than duplicates.

### ServiceRequest quality

1. Fetch the patient's service requests (filter for the specific ID).
2. Report all fields from the ServiceRequest object.
3. Validate `service_code` against the service-codes directory (`service_code_valid: true` if the code exists and is active).
4. Validate each `reason_code` against the ICD-10 directory. For each:
   - `valid`: whether the code exists.
   - `chapter`: from the ICD-10 lookup.
   - `matches_patient_evidence`: whether the code appears in the patient's active conditions or a recent encounter's diagnoses.

### SBAR coverage

Check the ServiceRequest's `sbar` object. It is `complete: true` if all four sections (`situation`, `background`, `assessment`, `recommendation`) are non-empty strings. Report which sections are present and which are missing.

## Task Type 5: Referral Batch Audit

**Input signal**: Prompt names a batch ID and service line.

**Output**: Normalized JSON conforming to the supplied `answer_template.json`.

### Batch header

Fetch all referrals, filter to the target `batch_id`. Count total rows and unique patients.

### Invalid or out-of-range code referrals

For each referral, look up its `diagnosis_code` in the ICD-10 directory. A referral's code is out-of-range for an orthopedic batch if its `chapter` is not `Musculoskeletal` (even valid `Injury` chapter codes like `S83.*` are out-of-range for an orthopedic referral audit -- the audit expects `Musculoskeletal` only). Report `actual_chapter` from ICD-10 and `expected_chapter: "Musculoskeletal"`.

### Laterality or narrative mismatch referrals

For each referral, check the `diagnosis_narrative` against the ICD-10 code's `expected_terms`. Mismatch types:
- `laterality_mismatch`: the code implies one side (e.g., `M17.12` = left knee) but the narrative describes the opposite side (right knee).
- `narrative_mismatch`: the narrative describes a body part, condition, or location that does not match the code's expected terms.
- `missing_laterality`: a code requiring laterality has a narrative lacking side specification (e.g., just "meniscus tear" for an `S83.242A` = left medial meniscus tear).

The `expected_terms` come from the ICD-10 directory's `expected_terms` for the referral's code.

**Laterality quick-reference for common codes:**
- `M17.11` -- right knee OA (expected: right knee terms)
- `M17.12` -- left knee OA (expected: left knee terms)
- `M16.11` -- right hip OA (expected: right hip terms)
- `M16.12` -- left hip OA (expected: left hip terms)
- `M25.561` -- right knee pain (expected: right knee pain)
- `M25.562` -- left knee pain (expected: left knee pain)
- `S83.241A` -- right medial meniscus tear (expected: right medial meniscus tear)
- `S83.242A` -- left medial meniscus tear (expected: left medial meniscus tear)

### Duplicate groups

Identify referrals for the same patient within the batch (same `patient_id` multiple times). For each duplicate group, the `duplicate_type` is `same_patient_resubmission`. The recommended disposition is `consolidate_under_original` (keep the first referral by ID ordering, mark the later one for consolidation). Record all referral IDs in the group.

### Duplicate tiering policy

All duplicate-group referral IDs are assigned to `tier_1_duplicate_blocker_referral_ids`. Any same-patient referrals that are separate clinical reviews (i.e., not the same clinical concern) go into `separate_same_patient_referral_ids`.

### Insurance anomalies

Identify referrals where the same `insurance_id` appears across different patient IDs. This is flagged as `shared_insurance_different_patients`. It does not itself indicate a duplicate -- it may be family plan membership. Also flag referrals where the insurance_id matches a known duplicate candidate's pair of patients.

### Follow-up queues

Based on each referral's state:
- `authorization_missing`: referrals with `authorization_status: "missing"`.
- `authorization_pending`: referrals with `authorization_status: "pending"`.
- `records_request`: referrals lacking `"office_note"` in `documents_received`.
- `imaging_follow_up`: referrals with "imaging pending" in `coordination_note` or missing expected imaging.

### Action plan tiers

- **Tier 1 (immediate)**: Urgent referrals with coding issues or duplicate blockers. Primary reason is `urgent_coding_or_duplicate_blocker`. Includes urgent referrals (`urgency: "urgent"`), duplicate-group referrals, and referrals with laterality/narrative mismatches that are marked urgent.
- **Tier 2 (short-term)**: Routine referrals with coding, authorization, or document blockers. Primary reason is `routine_coding_auth_or_document_blocker`. Includes any non-urgent referral with an out-of-range code, mismatch, missing authorization, or missing documents.
- **Tier 3 (administrative)**: Referrals that only need administrative document completion (no clinical or coding issues).

Assign `owner_provider_id` based on the referral's `receiving_provider_id`.

### Summary counts

Derive counts from the constructed arrays: total rows, unique patients, urgent/routine counts, invalid/mismatch counts, duplicate/insurance counts, queue counts, and tier counts.

## General Rules

### Sort ordering

Unless a template explicitly says otherwise:
- Arrays of string identifiers are sorted alphabetically (ascending).
- Arrays of objects in referral/audit contexts are sorted by `referral_id` ascending.
- Arrays of `normalized_key` values are sorted alphabetically.
- Encounters in handoff lists are sorted newest to oldest by date.

### Active vs. inactive filtering

Always filter conditions, medications, and allergies to `status: "active"` when building clinical unions, risk flags, and packet-relevant lists. Inactive records are distractors. Exception: when constructing `excluded_distractors`, list inactive records explicitly.

### Document filtering

For merge packets, include only identity-relevant (`identity_verification`) or external-continuity documents (`external_cardiology_note`). Exclude `chart_summary` and unrelated documents. For referral packets, include documents relevant to the referral's clinical domain.

### Encounter relevance

Not all patient encounters are relevant to every task. Filter encounters to those whose `diagnoses` or `care_plan_notes` relate to the packet's clinical purpose. Stale encounters (dates far outside the care window) or encounters with diagnoses in unrelated chapters are excluded.

### Deduplication of normalized keys

When unioning clinical keys across two patients, deduplicate by normalized_key. A key appearing for both patients is listed once.

### JSON output only

Produce clean JSON. No markdown fences, no prose outside the JSON object, no trailing commas. Follow the exact shape of the supplied `answer_template.json`.

### Task ID

When the template includes a `task_id` field, use the value required by the template instruction.
