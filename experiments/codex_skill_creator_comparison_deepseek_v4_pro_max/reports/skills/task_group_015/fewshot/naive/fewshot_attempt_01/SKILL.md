---
name: ehr-quality-governance
description: Build normalized JSON packets for EHR quality-governance tasks (duplicate merge, referral coordination, care transition, ServiceRequest review, batch audit) by calling a read-only healthcare REST API and producing template-conformant output.
---

# EHR Quality-Governance Packet Builder

Use this skill when the task requires calling a read-only EHR REST API and
producing a normalized JSON packet that conforms to an answer template. The
templates describe the required shape; your job is to collect the right evidence
from the endpoints and fill in the fields correctly.

## Environment Setup

A `<TASK_ENV_BASE_URL>` placeholder appears in the prompt. It resolves to a
base URL (default `http://task-env:9015/`). All endpoints are GET, read-only,
no authentication. Verify the base is reachable with `GET /health` before
collecting data.

### Available Endpoints

Every task environment exposes a subset of these endpoints. Use the ones the
prompt or template references; do not call endpoints that are absent from the
prompt's allowed list.

**Patient and clinical lists:**
- `GET /api/patients` — patient search and listing
- `GET /api/patients/{patient_id}` — single patient demographics
- `GET /api/patients/{patient_id}/conditions` — active/inactive problem-list conditions
- `GET /api/patients/{patient_id}/medications` — active/inactive medication orders
- `GET /api/patients/{patient_id}/allergies` — allergy/intolerance records
- `GET /api/patients/{patient_id}/encounters` — encounter history
- `GET /api/patients/{patient_id}/immunizations` — immunization records
- `GET /api/patients/{patient_id}/documents` — clinical documents
- `GET /api/patients/{patient_id}/service-requests` — ServiceRequest resources
- `GET /api/patients/{patient_id}/disclosures` — disclosure/consent records

**Quality-governance and operational:**
- `GET /api/audit-logs` — audit trail entries
- `GET /api/duplicates/candidates` — duplicate candidate listing
- `GET /api/duplicates/{candidate_id}` — single duplicate candidate detail
- `GET /api/referrals` — referral search/list
- `GET /api/referrals/{referral_id}` — single referral detail

**Code systems and directories:**
- `GET /api/icd10` — ICD-10 code directory
- `GET /api/icd10/{code}` — single ICD-10 code lookup (returns chapter, description)
- `GET /api/providers` — provider directory listing
- `GET /api/providers/{provider_id}` — single provider detail
- `GET /api/service-codes` — service/procedure code directory
- `GET /api/service-codes/{code}` — single service code validation

## Entity Model and Field Conventions

### Patients

A patient record has a `patient_id` (like `P-31014`), `enterprise_mrn`,
display name, date of birth, sex, insurance ID, phone, address, and
`primary_care_provider_id`. **Demographics** (dob, insurance_id, phone, sex,
address, given name) are the basis for identity-match and identity-conflict
signals in duplicate review.

### Conditions (Problem List)

Each condition has:
- `code` — ICD-10 code (e.g. `E11.9`, `I10`, `M17.11`)
- `description` — human-readable text
- `normalized_key` — a stable, lowercase, snake_case identifier (e.g.
  `diabetes_type_2`, `hypertension`, `right_knee_oa`, `memory_loss`)
- `status` — `active` or `inactive`
- `source` — `problem_list`, `referral_intake`, or other origin

Only **active** conditions belong in clinical union sets for merge and
transition packets. Inactive conditions are excluded or placed in distractor
lists. When the template asks for `active_condition_keys`, extract the
`normalized_key` from every active record, drop duplicates, and sort
alphabetically.

### Medications

Structure mirrors conditions: `medication` (name string), `normalized_key`
(snake_case, e.g. `aspirin`, `insulin_glargine`, `baseline_med`), `status`
(`active`/`inactive`), and optional `dose`, `route`, `frequency`. Only active
medications go into union sets; inactive ones are excluded.

### Allergies

Structure: `allergen`, `reaction`, `severity` (`mild`/`moderate`/`severe`/`unknown`),
`status` (`active`/`inactive`/`entered-in-error`/`unknown`), `source`,
and `normalized_key` (e.g. `penicillin`, `latex`, `iodinated_contrast`,
`baseline_allergy`). Active allergies only for packet-ready lists.

### Encounters

Each encounter has `encounter_id`, `date` (YYYY-MM-DD), `type` (e.g.
`office_visit`, `care_transition`), `provider_id`, `signed_status`
(`signed`/`unsigned`/`amended`/`draft`), `diagnosis_codes` (array of ICD-10
codes), `medications_mentioned`, and `care_plan_tag`.

For handoff/transition packets, select encounters from a defined window. Sort
selected encounters newest-to-oldest; excluded encounters are sorted ascending
by encounter_id.

### Documents

Fields: `document_id`, `type` (e.g. `echocardiogram`, `office_note`,
`chart_summary`), `date`, `status` (`final`/`preliminary`/`cancelled`).

When the packet documents a duplicate merge, include only identity-related or
external-continuity documents. Exclude `chart_summary` types unless the answer
template explicitly asks for them.

### Duplicate Candidates

A duplicate candidate record links two patients: a primary patient and a
possible duplicate. It contains `match_signals` (why they might be the same
person) and `conflict_signals` (why they might not be). Common match signals:
`same_dob`, `same_insurance`, `same_phone`, `similar_address`, `same_given_name`.
Common conflict signals: `different_given_name`, `different_phone`,
`different_dob`, `different_insurance`, `different_address`,
`opposite_laterality_problem`.

The candidate's `candidate_status` may be `confirmed_duplicate`, `needs_review`,
or `not_duplicate`.

### Referrals

A referral record connects a patient to a diagnosis code and a receiving
provider. Key fields: `referral_id`, `patient_id`, `batch_id`, `service_line`,
`requested_date`, `diagnosis_code`, `diagnosis_narrative`, `urgency`
(`routine`/`urgent`/`stat`), `referral_status`
(`open`/`closed`/`cancelled`/`draft`), `authorization_status`
(`approved`/`pending`/`denied`/`not_required`/`unknown`), `receiving_provider_id`.

### Service Requests

A ServiceRequest (FHIR-style) has: `service_request_id`, `patient_id`, `status`
(`draft`/`active`/`on-hold`/`revoked`/`completed`/`entered-in-error`), `intent`
(`order`/`plan`/`proposal`/etc.), `priority` (`routine`/`urgent`/`asap`/`stat`),
`service_code`, `requester_provider_id`, `performer_provider_id`,
`authored_on`, `occurrence_date`, `reason_codes` (array of ICD-10 codes).

### Providers

A provider record has: `provider_id` (e.g. `PRV-PCP-001`, `PRV-CARD-020`,
`PRV-ORTHO-010`), `name`, `role`, `service_line`, `facility`, `phone`, `fax`.

### ICD-10 Codes

ICD-10 lookup returns a `code`, `description`, and `chapter` (e.g.
`Musculoskeletal`, `Circulatory`, `Endocrine`, `Injury`, `Respiratory`). Codes
have laterality encoded in specific digits (e.g. `M17.11` vs `M17.12` for right
vs left knee osteoarthritis; `S83.241A` vs `S83.242A` for right vs left medial
meniscus tear). The chapter tells you whether a code belongs to the expected
service line.

## General Methodology

Follow this order for every task:

1. **Read the answer template first.** Understand every required top-level key,
   every enum, and every array ordering rule. The template is the contract.

2. **Read the prompt's task-specific instructions.** Note the case objects
   (patient IDs, candidate IDs, referral IDs, provider IDs, ServiceRequest IDs)
   the task gives you.

3. **Call the API endpoints to collect evidence.** Start with the entity the
   task names (patient, duplicate candidate, referral, batch) then fan out to
   related resources. Use parallel calls when endpoints are independent.

4. **Validate codes and cross-reference.** For every ICD-10 code, look it up
   in `/api/icd10/{code}` to confirm it exists and belongs to the expected
   chapter. For every service code, validate against `/api/service-codes/{code}`.
   For every provider reference, confirm the provider exists via
   `/api/providers/{provider_id}`.

5. **Produce the normalized JSON.** Fill in every required field. Use the
   `normalized_key` field from API responses for condition/medication/allergy
   lists. Sort arrays marked as sets alphabetically. Use enum values exactly as
   the template spells them. When the template allows null for a field, use
   JSON `null` (not the string `"null"`).

6. **Return JSON only.** The output must be a single JSON object with no
   surrounding prose, markdown fences, or commentary.

## Task-Type Rules

### Duplicate Merge Readiness Packet

Given a `candidate_id` and two `patient_ids`, determine whether the duplicate
pair should merge and build the merge packet.

1. Call `GET /api/duplicates/{candidate_id}` to get match signals, conflict
   signals, and candidate status.

2. Call both patients' demographics endpoints, then their conditions,
   medications, allergies, documents, and encounters endpoints in parallel.

3. **Merge decision:** The target is the patient with the active canonical
   record. The source is the other patient. If the duplicate candidate record
   already points one patient as duplicate-of-the-other, that determines the
   direction. Disposition is `ready_to_merge` when identity signals outweigh
   conflicts and no blocker exists; `needs_review` when conflicts are present
   but mitigable; `do_not_merge` when conflicts dominate.

4. **Clinical unions:** Build the set-union of `normalized_key` values from
   active conditions, active medications, and active allergies across both
   patients. Sort each list alphabetically. Compare what the duplicate preview
   shows against what the individual patient active-list endpoints return; any
   key present in the patient endpoints but missing from the duplicate preview
   goes into `*_added_from_active_endpoints`.

5. **Identity signals:** Translate the duplicate candidate's match and conflict
   signals into the template's signal labels. Also check demographics:
   identical fields across both patients are demographic matches; differing
   fields are demographic conflicts.

6. **Documents:** Select only documents that establish identity linkage or
   represent external continuity-of-care records shared between the two shells.
   Exclude chart summaries and unrelated internal documents. List excluded
   documents in the distractor set.

7. **Audit logs:** Call `GET /api/audit-logs` and collect entries that trace
   the duplicate candidate or the merge review activity. List them as evidence.

8. **Provider contacts:** Identify the specialist referenced by any external
   continuity document on the source patient's shell. Also identify each
   patient's primary care provider.

9. **Packet readiness:** `ready` when all evidence is collected and no blocker
   remains. List blocker codes when issues exist.

### Referral Coordination Packet

Given a `referral_id` and `patient_id`, reconcile the referral against the
patient chart and produce the coordination packet.

1. Call `GET /api/referrals/{referral_id}` for referral detail. Call
   `/api/patients/{patient_id}` and all clinical-list endpoints for the patient.

2. **Active diagnoses:** List every active condition from the patient's problem
   list, plus any diagnosis code supplied directly by the referral intake.
   Mark each as `referral_relevant` when it maps to the referral's service line
   or matches the referral's own diagnosis codes.

3. **Referral code set:** The primary code is the referral's own diagnosis code.
   Supporting codes are additional codes relevant to the referral narrative.
   Validate every code against `/api/icd10/{code}`. The `icd_validation` field
   is `valid_matches_narrative` when the code exists, belongs to the expected
   service chapter, and its description matches the referral narrative;
   `valid_but_narrative_mismatch` when the code is valid but the narrative
   diverges; `invalid_code` when the code is not found; `wrong_service_chapter`
   when the code's chapter does not match the service line.

4. **Allergy readiness:** Collect active allergies. Status is
   `complete_documented` when allergy information is consistent and non-empty.
   Use `no_known_allergies` when the records explicitly state none.
   `conflicting_allergy_records` when sources disagree.

5. **Recent encounter evidence:** Pick the most recent signed encounter that
   references the referral's diagnosis codes or care plan. Include its
   encounter_id, date, type, provider, signed_status, diagnosis_codes, and
   medications_mentioned.

6. **Required documents:** Check whether the expected documents for this service
   line exist (echo for cardiology, imaging for orthopedics). List missing
   required document types.

7. **Receiving provider:** Look up the provider from the referral record via
   `/api/providers/{provider_id}`.

8. **Authorization:** Check the referral's authorization_status and referral_status.
   Overall readiness is `ready_to_send` when authorization is approved, documents
   are present, and no clinical mismatches block it.

9. **Medication highlights:** List active medications relevant to the referral's
   clinical context. Use the highlight_reason enum values to explain why each one
   matters.

10. **Referral letter fields:** Map each decision into the appropriate enum
    choice for the letter template. The choices should be consistent with the
    evidence above.

### Care Transition Packet

Given a `patient_id` and `recipient_provider_id`, produce a handoff packet for
a surgical or specialty transition.

1. Call `/api/patients/{patient_id}` for demographics. Call all clinical-list
   endpoints in parallel.

2. Call `/api/providers/{recipient_provider_id}` for recipient details.

3. **Active clinical lists:** Extract `normalized_key` values from active
   conditions, medications, and allergies. Sort alphabetically.

4. **Handoff encounters:** Filter encounters to signed encounters within a
   relevant window (typically 60-90 days preceding the transition). Select the
   four most recent. For orthopedic surgery transitions, `care_transition`
   encounters and recent `office_visit` encounters are preferred. Sort selected
   encounters newest-to-oldest by date. List any reviewed-but-excluded
   encounter IDs as stale/outside-window.

5. **Latest immunization:** Pick the most recent immunization by date.

6. **Disclosure:** Find the disclosure record that matches the recipient
   provider and purpose (`surgical handoff`, `care transition`). Confirm it is
   in `permitted` status.

7. **Risk flags:** Identify risks from the clinical evidence. Common flags:
   `cognitive_memory_loss` (from conditions like memory loss), `fall_risk_note_required`
   (from lower-extremity OA conditions), `hypertension` (from hypertension
   condition), `insulin_dependent_diabetes` (from diabetes with insulin),
   `latex_allergy` (from latex allergy record), `perioperative_glucose_plan_needed`
   (from diabetes plus surgical context). Each risk flag must have evidence:
   which conditions, medications, and encounter IDs support it.

8. **Packet readiness:** `ready` when all sections are populated and no blocker
   exists; `ready_with_risk_flags` when all sections are complete but risk flags
   are present; `not_ready` when a required section is missing.

### Quality-Governance Duplicate + ServiceRequest Review

Given a duplicate candidate, two patient IDs, and a ServiceRequest ID, produce
a combined review packet.

1. Call `/api/duplicates/{candidate_id}` for the duplicate review.

2. Call `/api/patients/{patient_id}/service-requests` and
   `/api/service-codes/{service_code}` to validate the ServiceRequest.

3. **Duplicate review section:** Extract match and conflict signals from the
   candidate record. When identity signals are weak (different names, different
   phones, opposing laterality in conditions) and no strong override exists, set
   `decision` to `review_hold` and `merge_target_patient_id` /
   `merge_source_patient_id` to `null`. Only set `merge` when the candidate is
   confirmed and identity evidence is strong.

4. **ServiceRequest section:** Validate every field from the SR record. Validate
   the service code against the directory. For each reason code, look it up with
   `/api/icd10/{code}` and record whether it is valid, which chapter it belongs to,
   and whether it matches the patient's clinical evidence (active conditions,
   recent encounters).

5. **SBAR coverage:** Determine whether the ServiceRequest contains Situation,
   Background, Assessment, and Recommendation sections. The `complete` field is
   `true` only when all four are present.

### Batch Referral Audit

Given a `batch_id` and `service_line`, audit every referral in the batch.

1. Call `/api/referrals` (with batch or date filters) to list all referrals in
   the batch. Count total rows and unique patients.

2. For every referral, call `/api/icd10/{diagnosis_code}` to get the ICD-10
   chapter. **Out-of-range detection:** The expected chapter for the service
   line is implied by the service line itself — e.g. `orthopedics` expects
   `Musculoskeletal` chapter codes. Codes from `Injury`, `Respiratory`,
   `Circulatory`, or other non-matching chapters are out-of-range. Codes not
   found in the ICD-10 directory are `unknown_code`.

3. **Laterality/narrative mismatch:** Compare the ICD-10 description
   (laterality, body site, condition) against the referral's `diagnosis_narrative`.
   Types of mismatch:
   - `laterality_mismatch`: the code implies one side (left/right) but the
     narrative describes the other side or a different body part.
   - `narrative_mismatch`: the code's condition (e.g. meniscus tear) does not
     match the narrative's condition (e.g. lumbar radiculopathy).
   - `missing_laterality`: the code encodes laterality but the narrative omits it.

   The `expected_terms` array should contain the ICD-10 description or known
   aliases from the code lookup that the narrative should have matched.

4. **Duplicate groups:** Scan for referrals that share the same patient_id in
   the same batch. Same-patient resubmissions form duplicate groups. The
   `tier_1_duplicate_blocker_referral_ids` includes all referrals in the
   duplicate group. Separate same-patient referrals that represent distinct
   clinical reviews go into `separate_same_patient_referral_ids`.

5. **Insurance anomalies:** When two different patients share the same
   insurance_id, flag as `shared_insurance_different_patients` with
   `recommended_disposition` of `verify_insurance_membership_do_not_merge`.

6. **Follow-up queues:** Build four arrays of referral_ids:
   - `authorization_missing`: referrals with no authorization or denied.
   - `authorization_pending`: referrals with pending authorization.
   - `records_request`: referrals missing required office-note documents.
   - `imaging_follow_up`: referrals missing or needing imaging.

7. **Action plan:** Assign every referral with an unresolved issue to one of
   three tiers:
   - **Tier 1**: Duplicate-blocker referrals and referrals with urgent coding
     issues. Primary reason: `urgent_coding_or_duplicate_blocker`.
   - **Tier 2**: Referrals with routine coding mismatches, missing
     authorization, or missing documents. Primary reason:
     `routine_coding_auth_or_document_blocker`.
   - **Tier 3**: Referrals that only need administrative document completion.
     Primary reason: `administrative_document_completion`.
   Assign an `owner_provider_id` for each tier entry. Use the batch's
   orthopedic providers (look them up via `/api/providers` if needed).

8. **Summary counts:** Compute each integer count from the audit data. The
   `validated_ready_no_follow_up_count` is the number of referrals with no issues
   in any category.

## Output Rules

- **JSON only.** No explanations, no markdown fences, no trailing text.

- **Alphabetically sorted arrays.** When the template says "sort alphabetically"
  or "set semantics", sort string arrays with standard ASCII ordering. Numeric
  ids prefixed by letters sort naturally. Exception: when the template orders by
  date newest-to-oldest.

- **Enums are exact.** Use the exact string values from the template. Never
  invent a new enum variant.

- **Booleans are `true` / `false`, not strings.** Same for `null` — use JSON
  `null`, not `"null"`.

- **Dates use YYYY-MM-DD format.**

- **Normalized keys** are always lowercase snake_case, pulled directly from the
  API response's `normalized_key` field. Never invent your own key name.

- **Exclude distractors.** When a record is inactive, stale, outside the window,
  or unrelated to the packet's clinical scope, exclude it from the active lists
  and (where the template calls for it) list it in the excluded/distractor
  arrays.

- **Cross-validate.** ICD-10 validation, service-code validation, provider
  lookups, and disclosure recipient checks are not optional. If the API returns
  data that contradicts the prompt's stated case objects, the API data is the
  authority.

- **Default selections.** When multiple choices are reasonable (e.g. which
  provider to assign in a tier), prefer the provider most closely connected to
  the referral or patient. When no connection is obvious, spread assignments
  across the relevant service-line providers.

## Common Pitfalls

- **Active vs inactive:** Always filter by `status: "active"` before building
  clinical union sets. Inactive records go to distractor lists or are omitted.

- **Baseline records:** The API may include records with `normalized_key` like
  `baseline_med` or `baseline_allergy`. These are real active records; include
  them in unions and exclude them from distractors.

- **Duplicate candidate direction:** The duplicate candidate's record tells you
  which patient is the primary and which is the possible duplicate. Do not
  reverse this in the merge decision. When the candidate status is
  `needs_review`, both merge target and source may remain `null`.

- **Chapter validation for orthopedics:** Orthopedic referrals expect
  `Musculoskeletal` chapter codes. ICD-10 `S` codes are in the `Injury` chapter,
  not `Musculoskeletal`. A referral with an `S` code for an orthopedic service
  line is an out-of-range chapter issue unless the context explicitly states
  otherwise.

- **Laterality encoding in ICD-10:** Know that the sixth character often encodes
  laterality: `1` = right, `2` = left in many musculoskeletal codes. Check the
  actual ICD-10 description from the API lookup; do not assume from the code
  digits alone.

- **Insurance anomalies are not duplicates.** Shared insurance across different
  patients is an anomaly to flag, not a duplicate to merge.

- **Document selection:** Do not include every document from a patient chart.
  Select only those that serve the packet's purpose (identity linkage, external
  continuity, required specialty evidence). Chart summaries are generally
  excluded unless the template explicitly requires them.
