# EHR Quality-Governance API — Reusable Skill

## Overview

This skill teaches how to interact with a shared, read-only EHR (Electronic Health Record) quality-governance API to produce normalized JSON packets for clinical governance workflows. The workflows span duplicate-chart merge readiness, referral coordination, care transitions, duplicate review with service-request quality signals, and batch referral audits.

The API is a RESTful JSON service with ~24 GET endpoints covering patients, clinical lists, encounters, documents, audit logs, duplicate candidates, referrals, ICD-10 codes, providers, and service codes. Every task follows the same pattern: read the prompt, read the answer template, fetch evidence from the API, normalize the data, and return exactly the JSON shape the template demands.

## Quick-Start Pattern

For any new EHR governance task, follow this sequence:

1.  **Read the three inputs** — the user's prompt (in `prompt.txt` or inline), the answer template (`answer_template.json`), and any supporting payload files. The template defines the exact output shape and field-level constraints (enums, set semantics, sort orders).

2.  **Identify the domain objects** — extract every patient ID, referral ID, candidate ID, service request ID, provider ID, batch ID, and ICD-10 code mentioned in the prompt and payload. These are your API lookup keys.

3.  **Fetch from the API** — call the relevant endpoints at the configured `<TASK_ENV_BASE_URL>`. The endpoint families are documented below. Always fetch patient detail, active clinical lists (conditions, medications, allergies), and any domain-specific resources (referrals, duplicates, service requests, providers, ICD-10 codes). Do not skip endpoints just because a preview or summary endpoint returned partial data — always cross-check against the patient's own active-list endpoints for completeness.

4.  **Reconcile and normalize** — compare data from different sources (e.g., duplicate preview vs. patient active-list endpoints). Prefer the patient's own active-list endpoints as authoritative. Normalize clinical items to their `normalized_key` values. Exclude inactive, stale, or unrelated distractors.

5.  **Assemble the answer** — populate every required key in the template. Arrays with set semantics should be sorted alphabetically unless the template specifies date ordering. Use `YYYY-MM-DD` for all dates. Return **only** the JSON object with no surrounding prose, markdown fences, or commentary.

## API Reference

All endpoints are read-only GET requests. The base URL is provided as `<TASK_ENV_BASE_URL>` in the task prompt.

### Patient Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/patients` | List of all patients (id, name, dob, enterprise_mrn, sex, address, phone, insurance_id, primary_care_provider_id) |
| `GET /api/patients/{patient_id}` | Single patient detail including demographics, insurance, and primary care provider link |
| `GET /api/patients/{patient_id}/conditions` | Condition/problem list with `code`, `description`, `normalized_key`, `status` (active/inactive/resolved), `onset_date` |
| `GET /api/patients/{patient_id}/medications` | Medication list with `name`, `dose`, `route`, `frequency`, `normalized_key`, `status` (active/inactive) |
| `GET /api/patients/{patient_id}/allergies` | Allergy/intolerance list with `allergen`, `reaction`, `severity`, `normalized_key`, `status` (active/inactive) |
| `GET /api/patients/{patient_id}/encounters` | Encounter list with `id`, `date`, `type`, `provider_id`, `signed_status`, `diagnosis_codes`, `medications_mentioned` |
| `GET /api/patients/{patient_id}/immunizations` | Immunization records with `id`, `date`, `vaccine` |
| `GET /api/patients/{patient_id}/documents` | Clinical documents with `id`, `type`, `date`, `status` (final/preliminary/cancelled), `patient_id` |
| `GET /api/patients/{patient_id}/service-requests` | ServiceRequest (referral order) records |
| `GET /api/patients/{patient_id}/disclosures` | Disclosure/consent records with `id`, `date`, `status`, `purpose`, `recipient_provider_id` |

### Governance Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/audit-logs` | Audit trail entries with `id`, `patient_id`, `action`, `timestamp`, `detail` |
| `GET /api/duplicates/candidates` | List of duplicate candidate records with match/conflict signals |
| `GET /api/duplicates/{candidate_id}` | Single duplicate candidate detail including both patient IDs, match signals, conflict signals, and status |
| `GET /api/referrals` | List of all referrals |
| `GET /api/referrals/{referral_id}` | Single referral detail with patient_id, batch_id, service_line, diagnosis_code, diagnosis_narrative, status, urgency, authorization_status |

### Reference Data Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/icd10` | ICD-10 code directory |
| `GET /api/icd10/{code}` | Single ICD-10 code detail with `code`, `description`, `chapter` |
| `GET /api/providers` | Provider directory |
| `GET /api/providers/{provider_id}` | Single provider with `name`, `role`, `service_line`, `facility`, `phone`, `fax` |
| `GET /api/service-codes` | Service code directory |
| `GET /api/service-codes/{code}` | Single service code validation |

### Key API Integration Rules

- **Authoritative source for clinical lists**: When a duplicate-candidate preview or referral summary includes clinical keys, treat the patient's own `GET /api/patients/{id}/conditions` (etc.) endpoints as the authoritative source. Any keys present in the patient endpoints but absent from the duplicate/referral preview must be added to your output unions and noted in reconciliation fields.

- **Active vs. inactive**: Only include items with `status: "active"` in clinical key unions. Excluded (inactive, resolved, entered-in-error) items go into `excluded_distractors` arrays where the template provides them.

- **Distractor documents and audit logs**: Documents of type `chart_summary` and audit logs unrelated to the specific candidate/patient/referral are distractors. Include only documents and audit entries that are directly linked to the governance event being evaluated.

- **ICD-10 validation**: Look up every diagnosis code against `GET /api/icd10/{code}`. Verify the code exists (valid boolean), record its chapter, and check whether the chapter matches the expected service line (e.g., orthopedics expects "Musculoskeletal" chapter codes; cardiology expects "Circulatory"). Flag codes from wrong chapters as `out_of_range_chapter`.

- **Laterality and narrative matching**: When a diagnosis code implies a specific laterality (e.g., M17.11 = right knee, M17.12 = left knee), compare it against the diagnosis narrative text. Flag mismatches where the narrative describes the opposite side or an unrelated condition.

- **Provider lookup**: Always resolve provider IDs against `GET /api/providers/{provider_id}` to get full name, role, facility, phone, and fax. Never fabricate provider details.

## Normalization Rules

These rules apply across all EHR governance workflows:

### Clinical Keys
- Every condition, medication, and allergy record has a `normalized_key` field. Use this as the canonical identifier, not the raw description or code string.
- Sort normalized keys **alphabetically** (ascending) in all key-union arrays unless the template explicitly specifies date ordering.
- Arrays annotated with "set" semantics in the template are order-independent for evaluation, but you should still sort alphabetically for consistency.

### Dates
- All dates must be formatted as `YYYY-MM-DD`.
- When sorting encounters, sort from **newest to oldest** by date.

### Arrays of Objects
- Referral object arrays sort by `referral_id` ascending.
- Duplicate groups sort by `group_id` ascending; `referral_ids` inside each group sort ascending.
- ID-only arrays sort strings ascending.

### Enum Values
- When the template specifies an `enum` constraint, use the exact string values listed. Do not invent variant spellings.

### Exclusions
- Inactive/resolved/entered-in-error clinical items must be placed in `excluded_distractors` blocks, not in active unions.
- Encounters outside the relevant time window or unrelated to the workflow are excluded from handoff/evidence arrays.
- Documents of excluded types (e.g., `chart_summary`) are listed in exclusion arrays.

## Workflow-Specific Patterns

### Pattern A: Duplicate-Chart Merge Readiness (train_001 style)

1. Fetch the duplicate candidate (`GET /api/duplicates/{candidate_id}`).
2. Fetch full patient detail for both patients (`GET /api/patients/{id}`).
3. Fetch active conditions, medications, and allergies for both patients from their individual endpoints.
4. Reconcile: compare the duplicate candidate's preview data against the patient endpoints. Any keys found in patient endpoints but missing from the duplicate preview are additions (`*_keys_added_from_active_endpoints`). Set `authoritative_source` to `patient_active_list_endpoints_over_duplicate_preview`.
5. Build the merged clinical key unions — the deduplicated union of active keys from both patients.
6. Collect identity signals: compare demographic fields (dob, insurance_id, phone, sex, address, given_name, primary_care_provider_id). Fields that match go in `match_signals`/`demographic_matches`; fields that differ go in `conflict_signals`/`demographic_conflicts`.
7. Gather evidence: document IDs linked to the duplicate candidate or external continuity documents. Audit log IDs tied to the candidate.
8. Identify the specialist contact — look for an external document on either patient's record from a specialist provider (e.g., cardiology); that provider becomes the `specialist_provider` contact.
9. Identify the primary care provider from the target patient's `primary_care_provider_id`.
10. Determine merge disposition: `ready_to_merge` / `merge_ready` when identity signals are strong and conflicts are minor; `needs_review` when there are conflicting signals; `do_not_merge` when the records are clearly different people.

### Pattern B: Referral Coordination Packet (train_002 style)

1. Fetch the referral (`GET /api/referrals/{referral_id}`).
2. Fetch the patient (`GET /api/patients/{patient_id}`).
3. Fetch active conditions, medications, allergies, encounters, and documents for the patient.
4. Validate the referral's diagnosis codes against ICD-10 (`GET /api/icd10/{code}`). Check chapter alignment with the service line. Assess narrative match.
5. Assemble allergy readiness: determine if allergies are documented, conflicting, or missing.
6. Find recent encounter evidence — the most recent signed encounter whose diagnosis codes and care plan align with the referral reason.
7. Check required documents: echocardiogram for cardiology, office note, authorization, medication list, allergy confirmation. Flag missing ones.
8. Resolve the receiving provider from the provider directory.
9. Determine authorization readiness and overall send/hold status.
10. Highlight referral-relevant medications (e.g., diuretics for heart failure, antihypertensives).
11. Pick normalized referral-letter field values — these are controlled-choice enums derived from the assembled evidence.

### Pattern C: Care Transition Packet (train_003 style)

1. Fetch the patient (`GET /api/patients/{patient_id}`).
2. Fetch the recipient provider (`GET /api/providers/{provider_id}`).
3. Fetch active conditions, medications, allergies, encounters, immunizations, disclosures, and documents.
4. Select the four most recent relevant handoff encounters — for surgical transitions, prefer signed office visits and care-transition encounters within a recent surgical planning window. Exclude stale encounters and those clearly unrelated to the surgical service line.
5. Document the selection basis and list both selected and excluded encounter IDs.
6. Find the latest immunization record (most recent date).
7. Find the applicable disclosure for the recipient provider (status must be `permitted` for the packet to be ready).
8. Identify risk flags from active conditions and medications — common surgical risk flags include: insulin-dependent diabetes (from insulin medications + diabetes condition), cognitive/memory loss (from memory-loss condition), hypertension, latex allergy, fall risk (from OA conditions + pain medications), and perioperative glucose plan needed (diabetes condition + insulin medication).
9. Build risk-flag evidence: for each risk flag, cite the specific condition keys, medication keys, and encounter IDs that support it.
10. Determine packet readiness: `ready` if the disclosure is permitted and all sections are complete; `ready_with_risk_flags` if risk flags exist but nothing is blocked; `not_ready` if the disclosure is not permitted or critical sections are missing.

### Pattern D: Quality Governance with Duplicate Review + ServiceRequest (train_004 style)

1. Fetch the duplicate candidate (`GET /api/duplicates/{candidate_id}`).
2. Fetch both patients' demographics (`GET /api/patients/{id}`).
3. Fetch the ServiceRequest (`GET /api/patients/{patient_id}/service-requests` filtered to the given SR ID, or use the service request endpoint if available).
4. Fetch the performer provider and requester provider from the provider directory.
5. For the duplicate review: compare demographic signals between the two patients. Determine `candidate_status` (`confirmed_duplicate`, `needs_review`, `not_duplicate`) and `decision` (`merge`, `review_hold`, `do_not_merge`). When signals are mixed (some match, some conflict), default to `needs_review` / `review_hold`. When doing so, set `merge_target_patient_id` and `merge_source_patient_id` to `null`.
6. For the ServiceRequest: extract all fields directly from the SR record. Validate the `service_code` against `GET /api/service-codes/{code}`. Validate each `reason_code` against ICD-10 (valid boolean, chapter, and whether it matches patient evidence from their active conditions).
7. For SBAR coverage: check whether all four sections (situation, background, assessment, recommendation) are present. Set `complete` to `true` only when all four are present and none are missing.

### Pattern E: Batch Referral Audit (train_005 style)

1. Fetch all referrals (`GET /api/referrals`) and filter to the target batch by `batch_id`.
2. Fetch each referenced patient (`GET /api/patients/{id}`) — but only for patients whose referrals need verification.
3. For every diagnosis code in the batch, look it up against ICD-10 (`GET /api/icd10/{code}`).
4. **Invalid/out-of-range detection**: Flag any referral whose diagnosis code chapter is not the expected chapter for the service line (e.g., orthopedic referrals should have `Musculoskeletal` chapter codes; `Injury`, `Respiratory`, or other chapters are out of range). Also flag codes that don't exist in the ICD-10 directory.
5. **Laterality/narrative mismatch detection**: For each referral, compare the diagnosis code's ICD-10 description (which implies a specific body site and laterality) against the `diagnosis_narrative` text. Flag `laterality_mismatch` when the code says one side but the narrative says the opposite; `narrative_mismatch` when the narrative describes an unrelated condition; `missing_laterality` when the code implies a side but the narrative omits it.
6. **Duplicate group detection**: Scan for referrals with the same patient ID across the batch. When the same patient has two referrals with overlapping diagnosis codes and dates, group them as `same_patient_resubmission` duplicates. The original (lower referral_id number) is the canonical; the resubmission (suffixed `-DUP`) is the duplicate. Assign both to Tier 1 duplicate-blocker action.
7. **Insurance anomalies**: Flag cases where two different patients share the same insurance ID — this is a membership verification issue, not a merge candidate.
8. **Follow-up queues**: Categorize referrals into `authorization_missing`, `authorization_pending`, `records_request` (missing office notes), and `imaging_follow_up` (missing or pending imaging documents).
9. **Tiered action plan**:
   - **Tier 1 (immediate)**: Urgent coding issues and duplicate blockers. Assigned to `urgent_coding_or_duplicate_blocker`.
   - **Tier 2 (short-term)**: Routine coding, authorization, or document blockers. Assigned to `routine_coding_auth_or_document_blocker`.
   - **Tier 3 (administrative)**: Administrative document completion. Assigned to `administrative_document_completion`.
10. **Summary counts**: Populate all integer counts by counting the arrays built in the preceding sections. `validated_ready_no_follow_up_count` is the count of referrals that pass all checks with no follow-up needed.

## Error Handling and Edge Cases

- **Missing data**: When the API returns no records for a requested resource, use `null` for nullable fields and empty arrays for array fields — do not fabricate data.
- **Duplicate preview vs. patient endpoints diverge**: Always trust the patient's own active-list endpoints over a duplicate-candidate preview. Document the discrepancy.
- **Multiple encounters in the same window**: When selecting handoff encounters, prefer signed encounters over unsigned/draft ones. Within the same signed tier, prefer newer dates.
- **Unresolvable provider**: If a provider ID is referenced but not found in the directory, set provider fields to `null` and flag `provider_missing` as a blocking issue.
- **Empty batch sections**: When a section of the batch audit has no findings, emit an empty array (`[]`), not `null` or a missing key.
- **Task-level identity**: The `task_id` field (when present in the template) must be set to the literal value specified in the template's `required_value` constraint — it is a fixed string, not derived from API data.

## Delivery Checklist

Before returning the answer, verify:

- [ ] Every required top-level key from the answer template is present.
- [ ] All arrays with set semantics are sorted alphabetically (or by date where specified).
- [ ] All dates use `YYYY-MM-DD` format.
- [ ] All enum values match the template's allowed values exactly.
- [ ] Inactive/irrelevant records are in exclusion arrays, not in active unions.
- [ ] ICD-10 codes are validated and their chapters recorded.
- [ ] Provider details are resolved from the directory, not invented.
- [ ] The response is a single JSON object with no surrounding prose, markdown fencing, or commentary.
- [ ] No task-specific identifiers or values from training examples are copied — every value is derived from the API response for the current task.
