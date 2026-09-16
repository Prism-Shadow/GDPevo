---
name: ehr-quality-governance
description: >
  Use this skill whenever the user asks you to prepare EHR quality-governance
  packets, merge-readiness assessments, referral coordination packets,
  care-transition summaries, duplicate-chart reviews, or referral batch audits
  against a FHIR-like read-only REST API. These tasks always involve fetching
  patient clinical data, reconciling active lists, validating ICD-10 codes,
  identifying identity signals, and building a single normalized JSON output
  that conforms strictly to a supplied answer template. Trigger this skill for
  any prompt that mentions duplicate-chart merge, referral coordination, care
  transition, quality governance, referral audit, or that references patients
  together with conditions, medications, allergies, encounters, documents,
  service-requests, duplicates, referrals, ICD-10, providers, or disclosures
  against a shared EHR API. Even if the user does not use the exact phrase
  "quality governance," trigger this skill when they describe a clinical-data
  reconciliation or packet-preparation workflow that fits these patterns.
---

# EHR Quality Governance

## Overview

This skill covers EHR quality-governance tasks against a read-only FHIR-like
REST API. Every task has the same core shape: fetch records from the API,
apply clinical reconciliation and validation rules, and return a single
normalized JSON object that conforms to a provided answer template. Never
include explanatory prose, markdown fences, or commentary outside that JSON
object.

## API Reference

The base URL is supplied as `<TASK_ENV_BASE_URL>` in the prompt. Replace that
placeholder with the real URL from `environment_access.md` before making any
requests. All endpoints are GET only.

| Endpoint | Returns |
|---|---|
| `/api/patients` | Patient list/search |
| `/api/patients/{id}` | Demographics: name, DOB, MRN, sex, address, phone, insurance_id, primary_care_provider_id |
| `/api/patients/{id}/conditions` | Condition list: code, description, normalized_key, status, source |
| `/api/patients/{id}/medications` | Medication list: name, dose, route, frequency, normalized_key, status |
| `/api/patients/{id}/allergies` | Allergy list: allergen, reaction, severity, normalized_key, status |
| `/api/patients/{id}/encounters` | Encounters: date, type, signed_status, provider_id, diagnosis_codes, medications_mentioned |
| `/api/patients/{id}/immunizations` | Immunizations: vaccine, date, immunization_id |
| `/api/patients/{id}/documents` | Documents: type, date, status, document_id |
| `/api/patients/{id}/service-requests` | Service requests for the patient |
| `/api/patients/{id}/disclosures` | Disclosures: purpose, status, date, recipient_provider_id |
| `/api/audit-logs` | Audit log entries |
| `/api/duplicates/candidates` | Duplicate candidate listing |
| `/api/duplicates/{candidate_id}` | Candidate detail: status, patient_ids, match/conflict signals |
| `/api/referrals` | Referral search/list |
| `/api/referrals/{referral_id}` | Referral detail: patient, diagnosis_code, diagnosis_narrative, service_line, authorization, status, urgency, batch_id |
| `/api/icd10` | ICD-10 code directory |
| `/api/icd10/{code}` | Code detail: chapter, description, laterality, terms |
| `/api/providers` | Provider search |
| `/api/providers/{provider_id}` | Provider detail: name, role, service_line, facility, phone, fax |
| `/api/service-codes` | Service code listing |
| `/api/service-codes/{code}` | Service code detail |

### API Interaction Rules

- Use GET for every request. Parallelize independent fetches in a single
  tool-call batch (e.g., fetch conditions for two patients at once).
- Validate that every response is JSON before using it.
- A 404 means the resource does not exist — do not retry or invent data.

## Answer Template Protocol

Every task supplies an answer template at `input/payloads/answer_template.json`.
Follow these rules without exception.

### Strict Conformance

- Return exactly one JSON object with every required top-level key.
- Use the exact key names, enum values, and types declared in the template.
  Do not invent extra keys or variant enum strings.
- If the template says a field is `"string"`, emit a string (or null when
  null is allowed). If it says `"integer"`, emit an integer. If it says
  `"boolean"`, emit `true` or `false`.
- The final output is the JSON object itself — no surrounding text.

### Array Sorting

Unless the template explicitly overrides sorting for a specific field:

- String arrays (set semantics): sort alphabetically ascending.
- Patient IDs, document IDs, audit IDs: sort alphabetically ascending.
- Object arrays with a declared key ordering (e.g., "sort by referral_id
  ascending"): follow that rule.
- Encounter arrays ordered by date: newest to oldest.
- When uncertain, default to alphabetical ascending.

### Normalized Keys

Clinical records carry a `normalized_key` — a machine-friendly canonical
identifier such as `hypertension`, `right_knee_oa`, `metformin`, `penicillin`.

- Extract `normalized_key` values, not codes or display descriptions.
- Include only records with `status: "active"` in active lists, unless
  the template explicitly says otherwise.
- Exclude `inactive`, `resolved`, and `entered-in-error` records from
  active-key lists.
- Sort keys alphabetically ascending.

## Clinical Reconciliation

### Active List Union (Merge Packets)

When merging two patients:

1. Fetch conditions, medications, and allergies from each patient's
   dedicated endpoints (filter for active status).
2. Collect all `normalized_key` values across both patients into a set
   (deduplicate — each key appears once).
3. Sort alphabetically.
4. Cross-check against the duplicate candidate's preview lists. If an
   active key appears in a patient endpoint but is absent from the
   duplicate preview, report it in a reconciliation field such as
   `keys_added_from_active_endpoints`.

### Condition Relevance

A condition is "referral-relevant" when its code matches the referral's
primary or supporting diagnosis codes, or when its clinical domain aligns
with the referral's service line. Conditions unrelated to the referral
reason should be marked `referral_relevant: false`.

### Medication Relevance for Referrals

Map medication highlights to the referral's clinical context. Common
patterns and their highlight reasons include:

- Diuretics (furosemide) for heart failure → `heart_failure_diuretic`
- ACE inhibitors (lisinopril) for hypertension → `blood_pressure_management`
- Insulin/metformin for diabetes → `diabetes_management`
- Statins for hyperlipidemia → `lipid_management`
- Other active medications → `other_active_medication`

Use the exact `highlight_reason` enum values from the template.

## Identity and Duplicate Analysis

### Match Signals

Conditions that suggest two patients are the same person:

- `same_dob` — identical date of birth
- `same_insurance` — identical insurance ID
- `same_phone` — identical phone number
- `same_given_name` — name matches exactly or is a recognized variant (e.g., Bob/Robert)
- `similar_address` — addresses match within minor formatting differences
- `shared_external_*_document` — an external document references both records
- `name_variant` — names are recognizably the same person

### Conflict Signals

Conditions that suggest two patients are different people:

- `different_given_name` — names differ substantively
- `different_dob` — dates of birth differ
- `different_phone` — phone numbers differ
- `different_insurance` — insurance IDs differ
- `different_address` — addresses differ substantively
- `opposite_laterality_problem` — one patient has a left-side condition while the other has a right-side condition of the same type

### Demographic Comparison

Compare these fields individually between two patient records: sex,
insurance_id, phone, address, given_name, family_name, DOB,
primary_care_provider_id. Report each as a match (identical or trivially
variant) or a conflict (substantively different). Abbreviations and
missing secondary address elements are minor, not substantive.

### Merge Target Selection

- **Target** (canonical record to keep): the patient with the richer
  active clinical data, or the one the duplicate candidate identifies
  as the primary. Usually the earlier-created record.
- **Source** (record to absorb): the duplicate or less-complete record.
- Prefer the duplicate candidate's own signal orientation when it
  indicates which patient is the duplicate of which.

### Merge Disposition

- `ready_to_merge` / `merge_ready`: strong identity match, no blocking
  conflicts, duplicate candidate confirms the relationship.
- `needs_review` / `merge_ready_with_conflict_review`: mixed signals
  with some conflicts that warrant human review.
- `do_not_merge` / `needs_manual_review`: conflicts dominate or the
  candidate status is `not_duplicate`.

## ICD-10 Code Validation

### Chapter Validation

Each ICD-10 code belongs to a chapter. For service-line-specific tasks:

- **Orthopedics referrals**: codes must be in "Musculoskeletal". Codes
  in "Injury", "Respiratory", or any other chapter are `out_of_range_chapter`.
- **Cardiology referrals**: codes should be in "Circulatory" or a closely
  related chapter for symptoms tied to cardiac conditions.
- Codes absent from the ICD-10 directory are `unknown_code`.

### Laterality and Narrative Matching

ICD-10 codes encode laterality (M17.11 = right knee OA, M17.12 = left knee OA,
S83.241A = right medial meniscus tear, S83.242A = left medial meniscus tear).
Always verify against the ICD-10 directory entry, never from memory.

- **Laterality mismatch**: the code's side (left/right) contradicts the
  referral narrative or patient evidence.
- **Narrative mismatch**: the code's official description does not match
  the referral's diagnosis narrative text. Compare the ICD-10 entry's
  description and associated terms against the referral narrative.
- **Missing laterality**: the referral narrative omits the side when the
  code encodes it (e.g., narrative says "meniscus tear" for S83.242A,
  which is specifically "left medial meniscus tear").

For each mismatch referral, populate `expected_terms` from the ICD-10
directory entry's description and terms fields.

### Reason Code Validation (Service Requests)

For each reason code on a ServiceRequest:
1. Look up the code in `/api/icd10/{code}`.
2. `valid`: `true` if found, `false` if not found.
3. `chapter`: from the ICD-10 entry (null if not found).
4. `matches_patient_evidence`: `true` when the patient has an active
   condition whose domain matches the code's clinical area.

## Referral Batch Audit Patterns

### Process

1. Retrieve all referrals in the target batch.
2. For each referral, look up its diagnosis code, patient, and provider.
3. Classify every referral into zero or more issue categories.
4. Build follow-up queues and tier-based action plans.
5. Compute summary counts that match the emitted arrays.

### Classification Categories

**Invalid or out-of-range codes**: the diagnosis code's ICD-10 chapter
does not match the expected chapter for the referral's service line.
For orthopedics the expected chapter is "Musculoskeletal". Record the
`actual_chapter` from the ICD-10 lookup and `issue_type` of either
`out_of_range_chapter` or `unknown_code`.

**Laterality or narrative mismatches**: the code does not match the
referral's narrative in laterality, description, or completeness.
Record each mismatch type in `mismatch_types` and include the
`expected_terms` from the ICD-10 directory.

**Duplicate groups**: same patient with multiple referrals for the same
clinical issue. Group them with type `same_patient_resubmission` and
recommend `consolidate_under_original`. Sort referral_ids within each
group ascending.

**Insurance anomalies**: different patients sharing the same insurance
ID. This may indicate a duplicate or a membership anomaly. Do not merge
based on insurance alone; recommend `verify_insurance_membership_do_not_merge`.

### Follow-Up Queues

Build four queues, each as an array of referral IDs sorted ascending:

- `authorization_missing`: no authorization record found.
- `authorization_pending`: authorization is in a pending state.
- `records_request`: missing required office-note documents.
- `imaging_follow_up`: missing or pending imaging documents.

### Action Plan Tiers

- **Tier 1 (Immediate)**: `urgent_coding_or_duplicate_blocker`. Urgent
  referrals with code issues, or duplicate-blocker referrals.
- **Tier 2 (Short-term)**: `routine_coding_auth_or_document_blocker`.
  Routine referrals with coding, authorization, or document issues.
- **Tier 3 (Administrative)**: `administrative_document_completion`.
  Referrals that only need document follow-up.

Distribute `owner_provider_id` across the available providers in the
relevant service line. A single referral can appear in at most one tier.
When a referral qualifies for multiple tiers, assign the highest
priority tier.

### Duplicate Tiering Policy

When duplicate groups exist in a batch, the policy
`tier_all_duplicate_group_rows_as_duplicate_blockers` means every
referral in the duplicate group is a Tier 1 blocker. List all
duplicate-group referral IDs in `tier_1_duplicate_blocker_referral_ids`.
Same-patient referrals that are separate clinical reviews (different
body parts, different clinical questions) go in
`separate_same_patient_referral_ids` and are not duplicates.

### Summary Counts

Every count must match the length of its corresponding array. Include
`validated_ready_no_follow_up_count` for referrals that appear in none
of the classification or follow-up arrays. Verify the total referral
row count, unique patient count, urgent count, and routine count against
the raw batch data.

## Encounter Selection for Handoff Packets

1. Fetch all encounters for the patient.
2. Filter to clinical encounters (`care_transition`, `office_visit`, and
   similar). Exclude purely administrative encounters.
3. Select the N most recent by date (the template specifies N; 4 is common).
4. Sort selected encounters newest to oldest.
5. Track excluded encounters separately: list their IDs sorted ascending
   in `excluded_encounter_ids`.
6. The `selection_basis` field carries a code describing the rule applied
   (e.g., `orthopedic_surgical_handoff_window`).

## Immunization and Disclosure Selection

- **Immunization**: fetch all, select the single most recent by date.
  Include its immunization_id, date, and vaccine name.
- **Disclosure**: fetch all, find the one matching the recipient provider
  and the workflow purpose (e.g., `surgical handoff` for orthopedics).
  Report its status as `permitted`, `pending`, `denied`, or `expired`.
  A missing or non-permitted disclosure is a blocking issue.

## Risk Flag Derivation

For care transition packets, derive risk flags from clinical evidence.
Each flag needs an evidence entry linking the specific condition_keys,
medication_keys, and encounter_ids that support it. Evidence arrays sort
ascending. The overall `risk_flag_evidence` array sorts by `risk_flag`
ascending. Evidence encounters may include both selected handoff
encounters and excluded encounters.

Common risk-flag derivation patterns:

| Risk Flag | Evidence to look for |
|---|---|
| `cognitive_memory_loss` | Active condition with normalized_key `memory_loss` or similar cognitive condition |
| `fall_risk_note_required` | Orthopedic conditions (hip/knee OA) combined with pain medications; encounters documenting mobility or fall concerns |
| `hypertension` | Active condition `hypertension` |
| `insulin_dependent_diabetes` | Active condition `diabetes_type_2` with active medication `insulin_glargine` (or similar insulin preparation) |
| `latex_allergy` | Active allergy with allergen `latex` |
| `perioperative_glucose_plan_needed` | Diabetes condition with insulin medication in a surgical handoff context |

Only emit a flag when there is affirmative evidence from the patient's
records. Do not emit flags that have no supporting clinical data.

## Provider Lookups

Fetch `/api/providers/{provider_id}` for each provider the packet needs.
Extract: name, role, service_line, facility, phone, fax. For specialist
contact reasons, describe why this specific provider is relevant to the
workflow. Service lines imply roles:

- `cardiology` → Cardiologist
- `orthopedics` → Orthopedic Surgeon
- `primary_care` → Primary Care
- `pulmonology` → Pulmonologist
- `neurology` → Neurologist
- `oncology` → Oncologist
- `skilled_nursing` → Skilled Nursing Facility

## Document Evidence

When selecting documents for a packet:

- Fetch documents for each relevant patient.
- Prefer documents with status `final`. Include `preliminary` only if
  no final version exists. Exclude `cancelled`.
- Include only documents that support the specific workflow: identity or
  external continuity documents for merge packets; echocardiograms and
  office notes for cardiology referrals; surgical or handoff documents
  for care transitions.
- Exclude `chart_summary` documents from evidence arrays — they are
  internal summaries, not external continuity evidence.
- Sort document IDs alphabetically.

### Required Document Gaps

For referral coordination, check for these common required documents and
report any that are missing in `missing_required_documents`:

- `echocardiogram` — for cardiology referrals
- `office_note` — documenting the referral reason
- `authorization` — the referral authorization
- `medication_list` — for medication reconciliation
- `allergy_confirmation` — for allergy readiness

## Service Request Quality Signals

When a task involves a ServiceRequest:

1. Fetch the SR by ID.
2. Extract: status, intent, priority, service_code, requester_provider_id,
   performer_provider_id, authored_on, occurrence_date, reason_codes.
3. Validate the service_code against `/api/service-codes/{code}`.
4. Validate each reason_code against `/api/icd10/{code}` (see Reason
   Code Validation above).
5. Confirm the performer's service_line matches the expected specialty.

## SBAR Coverage

For tasks checking SBAR (Situation, Background, Assessment, Recommendation)
coverage: examine the service request or referral documentation for all
four sections. `complete` is `true` only when all four are present. List
any missing sections explicitly in `missing_sections`.

## Audit Logs

For merge packets, look for audit entries that document duplicate
candidate lifecycle events, patient record merges, or identity reviews.
Sort audit IDs alphabetically in evidence arrays.

## Exclusion of Distractors

The environment includes distractor records. Exclude these from output:

- **Inactive clinical records**: conditions, medications, or allergies
  with status `inactive`, `resolved`, or `entered-in-error` stay out of
  active lists.
- **Unrelated documents**: generic chart summaries and documents for
  unrelated patients or workflows.
- **Stale encounters**: encounters outside the relevant time window or
  purely administrative encounters.
- **Irrelevant audit logs**: entries for unrelated operations.

When the template has an `excluded_distractors` section, populate it with
the specific keys or IDs that were reviewed and excluded.

## Packet Readiness Assessment

Every packet concludes with a readiness assessment:

- `ready` / `ready_to_send`: all required data is present, valid, and
  permits the action. No blocking issues.
- `ready_with_risk_flags` / `ready_with_review_note`: substantially
  complete but with noted risks the recipient should see. Still safe
  to send.
- `not_ready` / `blocked` / `hold_for_*`: one or more blocking issues
  prevent sending. Report the specific issue codes from the template's
  allowed values.

A packet is ready only when all required entities exist, all required
documents are received in final status, authorizations are approved
(or not required), disclosures are permitted, and provider assignments
are resolved.

## Overall Workflow

For any EHR quality-governance task, follow this sequence:

1. **Read the answer template** fully. Note every field, type, enum
   constraint, and sorting rule.

2. **Identify the task type** from the prompt (merge packet, referral
   coordination, care transition, duplicate review, or referral audit).

3. **Fetch core entities** in parallel where possible: patients, the
   primary business object (duplicate candidate, referral, service
   request), and relevant providers.

4. **Fetch clinical data** for every involved patient: conditions,
   medications, allergies — filtered to active status.

5. **Fetch supporting data** as needed: encounters, documents,
   immunizations, disclosures, audit logs, ICD-10 codes, service codes.

6. **Validate and reconcile**: check ICD-10 chapters against service
   lines, compare laterality and narrative, cross-reference identity
   signals with demographics, verify document statuses, confirm
   authorization states, and validate provider service lines.

7. **Build the output JSON** field by field following the template
   exactly. Apply sorting. Respect enum constraints. Exclude distractors.

8. **Verify before returning**: every required key is present, every
   array that should be sorted is sorted, every enum matches the
   allowed values, no explanatory text appears outside the JSON, and
   every summary count matches its source array length.

## Common Pitfalls

- **Not filtering by status**: always check for `status: "active"` when
  gathering active clinical lists; inactive records are distractors.
- **Including chart summaries as evidence**: `chart_summary` documents are
  internal — exclude them from packet evidence.
- **Wrong laterality**: verify every ICD-10 code's laterality against the
  directory entry; do not guess from memory.
- **Swapping target and source in merges**: target is the canonical record
  to preserve; source is the duplicate to absorb.
- **Skipping duplicate-preview reconciliation**: always cross-check the
  duplicate candidate's preview lists against individual patient endpoints.
- **Omitting duplicate rows from Tier 1**: when duplicate-tiering policy says
  to block all duplicate rows, both the original and resubmission must appear.
- **Empty arrays vs. omitted keys**: emit `[]` for empty array fields; never
  omit the key or use `null`.
- **Inconsistent summary counts**: every count must equal the length of the
  corresponding array elsewhere in the output.
