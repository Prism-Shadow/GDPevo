---
name: ehr-quality-governance
description: Build normalized EHR quality-governance JSON packets by querying a shared read-only FHIR-style REST API. Use this skill whenever the task involves duplicate-chart merge readiness, referral coordination, care-transition packets, quality-governance case review, or batch referral audits against an EHR environment. Trigger on mentions of EHR, FHIR, duplicate candidates, referral packets, care transitions, quality governance, clinical data reconciliation, ICD-10 validation, provider lookup, or answer_template.json with clinical/administrative keys.
---

# EHR Quality-Governance Packet Builder

Produce normalized JSON packets for healthcare quality-governance workflows by
querying a shared read-only EHR REST API.  Every task provides a concrete
answer template (often named `answer_template.json` or embedded in the prompt)
and points at a task-environment base URL.  The solver's job is to gather
evidence through the API, reconcile it against the template's controlled
vocabularies, and emit strictly conformant JSON.

## API orientation

The task environment provides these endpoint families at `<TASK_ENV_BASE_URL>`.
All are read-only GETs.  Replace `{id}` placeholders with real identifiers
found in upstream responses.

| Scope | Endpoints |
|---|---|
| Patients | `/api/patients`, `/api/patients/{id}`, `/api/patients/{id}/conditions`, `/api/patients/{id}/medications`, `/api/patients/{id}/allergies`, `/api/patients/{id}/encounters`, `/api/patients/{id}/immunizations`, `/api/patients/{id}/documents`, `/api/patients/{id}/service-requests`, `/api/patients/{id}/disclosures` |
| Duplicates | `/api/duplicates/candidates`, `/api/duplicates/{candidate_id}` |
| Referrals | `/api/referrals`, `/api/referrals/{referral_id}` |
| Audit | `/api/audit-logs` |
| Coding | `/api/icd10`, `/api/icd10/{code}` |
| Providers | `/api/providers`, `/api/providers/{provider_id}` |
| Service codes | `/api/service-codes`, `/api/service-codes/{code}` |

**Retrieval pattern**: Start with the primary object (patient, duplicate
candidate, referral, or referral batch).  Every response contains IDs that
branch into further endpoints: a patient record yields a `provider_id` you look
up; a duplicate candidate yields two `patient_id` values to cross-reference; a
referral carries `diagnosis_code` strings to validate against ICD-10.  Follow
these chains until every required field in the answer template has endpoint
evidence behind it.

When the task names a family of endpoints as "relevant" or "available", treat
that as the authority list.  Endpoints outside the listed families are not part
of the task environment for that run, even if they appear in other examples.

## Core conventions that apply across all packet types

### Normalized keys

Conditions, medications, and allergies each carry a `normalized_key` field in
their endpoint records.  This key is the canonical, stable identifier used
throughout the answer template for:

- clinical union arrays (`active_condition_keys`, `active_medication_keys`,
  `active_allergy_keys`),
- active-list reconciliation deltas,
- risk-flag evidence mapping,
- excluded-distractor arrays.

Always use the `normalized_key` value, never the display name or code, when the
answer template asks for a condition/medication/allergy key.

### Active vs. inactive records

Most endpoints return a `status` field.  When the template calls for "active"
lists, filter to records whose `status` is `"active"`.  Records with other
statuses (inactive, entered-in-error, resolved, etc.) are stale records;
include them only in explicit "excluded" or "distractor" arrays when the
template has that slot.  If the template does not have an excluded/distractor
section, stale records are simply omitted.

### Alphabetical sorting

Arrays described as "sets", "sorted alphabetically", or "sorted ascending"
must be ordered by their string values using standard lexicographic sort
(case-sensitive, ASCII order).  This applies to:

- `condition_keys`, `medication_keys`, `allergy_keys`,
- `reason_codes`, `match_signals`, `conflict_signals`,
- `document_ids`, `audit_ids`, `referral_ids`,
- `blocking_issue_codes`, `missing_sections`, `sections_present`,
- `risk_flags` and nested evidence arrays.

Object arrays of referrals are sorted by `referral_id` ascending.  Encounter
arrays are sorted newest-to-oldest by date unless the template says otherwise.

### Controlled vocabulary (enums)

Most decision fields use fixed enum values defined in the answer template.
Never invent a value outside the template's allowed list.  When the template
provides `allowed_values` for a field, pick only from that list.  Common
recurring enums include:

- **Disposition / decision**: `ready_to_merge`, `merge`, `do_not_merge`,
  `review_hold`, `needs_review`, `confirmed_duplicate`, `not_duplicate`.
- **Service lines**: `cardiology`, `orthopedics`, `pulmonology`,
  `neurology`, `skilled_nursing`, `oncology`, `primary_care`.
- **Readiness**: `ready`, `ready_with_review_note`, `ready_with_risk_flags`,
  `blocked`, `not_ready`, `ready_to_send`, `hold_for_*`.
- **Risk flags**: the six canonical values `cognitive_memory_loss`,
  `fall_risk_note_required`, `hypertension`, `insulin_dependent_diabetes`,
  `latex_allergy`, `perioperative_glucose_plan_needed`.
- **ICD-10 validation**: `valid_matches_narrative`,
  `valid_but_narrative_mismatch`, `invalid_code`, `wrong_service_chapter`.
- **Mismatch types**: `laterality_mismatch`, `narrative_mismatch`,
  `missing_laterality`.
- **Tier reasons**: `urgent_coding_or_duplicate_blocker`,
  `routine_coding_auth_or_document_blocker`,
  `administrative_document_completion`.

### Evidence citation

Every decision in the packet must be traceable to an endpoint response.  Cite
specific IDs: document IDs for required documents, audit IDs for audit history,
encounter IDs for handoff encounters, provider IDs for contacts, immunization
IDs for latest immunization.  If a field like `document_ids` or `audit_ids` is
empty in the evidence, emit an empty array `[]` rather than omitting the key.

### Answer template conformance

The answer template (whether a standalone JSON file or inlined in the prompt)
is the authoritative output schema.  Rules for working with it:

- Emit every top-level key the template marks as `required_top_level_keys` or
  lists at the top level.
- Do not add extra top-level keys the template does not define.
- When the template says `"required_value": "train_NNN"`, emit that exact
  literal string for the `task_id` field.
- Use the types, enums, and ordering rules exactly as stated.
- When a field allows `null`, use `null` (not a string `"null"`) when there is
  genuinely no value from the evidence.
- Emit only the JSON object.  Do not wrap it in markdown fences unless the
  output channel requires them.

## Workflow-specific patterns

### Duplicate-chart merge readiness

1. Fetch the duplicate candidate via `/api/duplicates/{candidate_id}`.  Note
   the two patient IDs and any pre-computed match/conflict signals the
   candidate record provides.
2. Fetch each patient's demographics, conditions, medications, allergies,
   documents, and service-requests from the patient-scoped endpoints.
3. Build the active-key unions by taking the union of both patients' active
   `normalized_key` values for conditions, medications, and allergies.
4. Reconcile against the duplicate candidate's own clinical preview (if one
   exists): keys present in the patient endpoints but absent from the
   duplicate preview go into `*_added_from_active_endpoints` arrays.  The
   authoritative source is the patient active-list endpoints over the
   duplicate preview.
5. Identity signals: collect match signals and conflict signals from the
   duplicate candidate record, from demographic comparison, and from external
   document evidence (e.g., a shared cardiology document on one patient's
   record that ties the identities together).  Use the template's
   `allowed_values` for signal labels.
6. Document/audit evidence: include documents that relate to identity
   matching or external continuity (not routine chart summaries).  Include
   audit log entries that reference the duplicate candidate.  Exclude
   document types that the task's selection policy excludes.
7. Determine the canonical target (the patient with the longer or more
   complete active record, or the one the duplicate record already points to)
   and source (the shell or less-complete record).
8. Set disposition based on signal strength: strong match + few conflicts
   means `ready_to_merge`; significant conflicts mean `needs_review`; clear
   mismatch means `do_not_merge`.
9. Provider contacts: look up the specialist tied to the key external
   evidence document, plus the primary care provider from the target patient
   record.

### Referral coordination

1. Fetch the referral via `/api/referrals/{referral_id}`.  Extract the
   patient ID, diagnosis code(s), batch ID, service line, and status.
2. Fetch the patient's conditions, medications, allergies, encounters, and
   documents.
3. Build the active-diagnosis list from active conditions, marking each
   `referral_relevant` based on whether its code matches the referral's
   primary/supporting codes or narrative.
4. Validate the primary diagnosis code against `/api/icd10/{code}`.  Check:
   - validity (does the code exist?)
   - chapter match (is the chapter appropriate for the service line?
     Cardiology means Circulatory; Orthopedics means Musculoskeletal)
   - narrative match (does the ICD-10 description align with the referral's
     written narrative or the patient's active conditions?)
5. Allergy readiness: gather active allergies.  `complete_documented` if
   allergy records exist and are consistent; `incomplete_needs_clarification`
   if the referral form and patient chart disagree; `no_known_allergies` if
   records explicitly state none.
6. Recent encounter evidence: pick the encounter whose date, diagnosis codes,
   medications, and care-plan tag best align with the referral's purpose.
   The signed status must be `signed` for the encounter to count as ready
   evidence.
7. Required documents: check for an echocardiogram (cardiology) or relevant
   imaging report, plus an office note.  A document is "received" when a
   record with matching type exists at the patient's document endpoint and
   has `status: "final"`.
8. Receiving provider: identify by matching the referral's target provider or
   the service line's specialist from `/api/providers`.
9. Authorization: check the referral's authorization status (from the
   referral detail or an authorization sub-record).  Overall readiness is
   `ready_to_send` only when authorization is approved, all required
   documents are present, allergies are documented, and codes are valid.
10. Referral letter fields: each `*_choice` is a single string selected from
    the template's allowed values.  The choice must be the one that most
    accurately reflects the evidence gathered in the steps above.

### Care transition packet

1. Fetch the patient and verify the recipient provider exists via
   `/api/providers/{provider_id}`.
2. Gather active conditions, medications, and allergies; emit their
   `normalized_key` values sorted alphabetically.
3. Handoff encounters: fetch all encounters, then select exactly four.
   Selection: prioritize encounters with types like `care_transition` or
   `office_visit` within a 90-day lookback window, signed, and related to
   the transition's service line.  Sort selected encounters newest-to-oldest
   by date.  Track excluded encounters (stale, outside-window, or unrelated)
   in the `excluded_encounter_ids` array.
4. Latest immunization: the immunization with the most recent date from the
   patient's immunization endpoint.
5. Applicable disclosure: fetch disclosures, filter to the one whose
   `recipient_provider_id` matches the recipient provider.  It must be
   `permitted` for the packet to be ready.
6. Risk flags: derive from the allowed_values list.  For each flag, collect
   supporting evidence from active conditions, active medications, and
   encounters.  A flag is present when the evidence supports it:
   - `cognitive_memory_loss` means a condition with `normalized_key`
     `memory_loss` or equivalent.
   - `fall_risk_note_required` means bilateral lower-extremity OA conditions
     or recent fall-related encounters.
   - `hypertension` means active `hypertension` condition.
   - `insulin_dependent_diabetes` means `diabetes_type_2` condition plus an
     active insulin medication.
   - `latex_allergy` means active `latex` allergy.
   - `perioperative_glucose_plan_needed` means `diabetes_type_2` condition in
     a surgical handoff context.
7. Packet readiness: `ready` when all required sections have evidence and the
   disclosure is permitted; `ready_with_risk_flags` when risk flags are
   present but nothing blocks sending; `not_ready` when a required piece is
   missing.

### Quality-governance case review (duplicate + ServiceRequest)

1. Fetch the duplicate candidate via `/api/duplicates/{candidate_id}`.
   Determine candidate_status (`confirmed_duplicate`, `needs_review`, or
   `not_duplicate`) and decision (`merge`, `review_hold`, `do_not_merge`)
   from the match/conflict signal balance.
   - Strong identity match with no conflicting laterality problems means lean
     merge.  Conflicting laterality (one patient has left-knee problems, the
     other right-knee) is a strong `review_hold` signal even when
     demographics match.
   - When decision is `review_hold`, `merge_target_patient_id` and
     `merge_source_patient_id` are `null`.
2. Fetch the ServiceRequest via the patient's service-request endpoint.
   Validate every field against the template's allowed enums.  Pay special
   attention to `service_code_valid` (validate against
   `/api/service-codes/{code}`) and `reason_code_validation` (validate each
   diagnosis code against `/api/icd10/{code}`, checking validity, chapter,
   and whether the code's description matches patient evidence).
3. SBAR coverage: check whether the ServiceRequest includes Situation,
   Background, Assessment, and Recommendation sections.  `complete` is true
   only when all four are present.

### Batch referral audit

1. Fetch the referral batch via `/api/referrals` with appropriate query
   parameters to isolate the named batch.  Count rows and unique patients.
2. Validate every referral's diagnosis code against `/api/icd10/{code}`:
   - Codes whose chapter is not the expected chapter for the service line
     (e.g., `Injury` instead of `Musculoskeletal` for orthopedics) are
     `out_of_range_chapter`.
   - Codes not found in the ICD-10 directory are `unknown_code`.
3. Laterality and narrative mismatch: for each referral, compare the ICD-10
   description to the referral's `diagnosis_narrative`.
   - `laterality_mismatch`: the ICD-10 code specifies one side (e.g., left
     medial meniscus tear) but the narrative mentions the opposite side or
     a different joint.
   - `narrative_mismatch`: the narrative describes a condition unrelated to
     the code (e.g., "lumbar radiculopathy" for a knee meniscus tear code).
   - `missing_laterality`: the narrative omits a laterality marker present
     in the code description.
   A referral can carry multiple mismatch types.
4. Duplicate detection: group referrals by `patient_id`.  When the same
   patient has multiple referrals in the batch with the same diagnosis code
   or overlapping clinical intent, they form a duplicate group of type
   `same_patient_resubmission`.  The tiering policy assigns all rows in the
   group as `tier_1_duplicate_blockers`.  Same-patient referrals that are
   genuinely separate clinical reviews (different body parts or conditions)
   go in `separate_same_patient_referral_ids`.
5. Insurance anomalies: when two different patients share the same
   `insurance_id` and both appear in the batch, flag as
   `shared_insurance_different_patients`.  This is a verification item, not
   a merge recommendation.
6. Follow-up queues: classify each referral by what it lacks:
   - `authorization_missing`: no authorization record at all.
   - `authorization_pending`: authorization exists but not yet approved.
   - `records_request`: office-note document missing.
   - `imaging_follow_up`: imaging report missing or not final.
   A referral can appear in multiple queues.
7. Action plan tiers:
   - **Tier 1 (immediate)**: duplicate-blocker rows or referrals with both
     coding errors and missing critical documents or authorizations.  Assign
     to the batch's primary ortho provider.
   - **Tier 2 (short-term)**: referrals with coding mismatches, missing
     authorizations, or missing documents that are not duplicates.  Spread
     across available ortho providers.
   - **Tier 3 (administrative)**: referrals that only need document completion
     with no coding or authorization issues.
8. Summary counts: compute each integer from the arrays populated above.  The
   `validated_ready_no_follow_up_count` is the number of referrals with no
   coding issues, no mismatches, complete documents, and approved
   authorization -- the ones that need no action at all.

## ICD-10 chapter mapping for service lines

When validating whether a diagnosis code belongs to the right service line,
use this mapping:

| Service line | Expected ICD-10 chapter |
|---|---|
| `orthopedics` | Musculoskeletal |
| `cardiology` | Circulatory |
| `pulmonology` | Respiratory |
| `neurology` | Nervous System |
| `oncology` | Neoplasms |

The ICD-10 endpoint's `chapter` field gives the actual chapter for a code.
Compare it against the expected chapter above.  A mismatch means the code
is out of range for that service line.

## Document selection policy

Not every document belongs in a packet.  When a packet needs document
evidence, include only documents that:

- relate to identity matching or external continuity (for merge packets),
- are clinically required for the referral or transition (echo for
  cardiology, office note for any referral, imaging for orthopedics),
- have status `final` (preliminary or cancelled documents are not
  ready evidence).

Exclude: chart summaries, generic administrative documents, and documents
whose type is listed in `excluded_document_types` by the template.

## General troubleshooting

- **Missing patient data**: If a patient endpoint returns fewer records than
  expected, do not fabricate.  The answer reflects only what the API returns.
- **Null fields**: When an optional field has no value in the API evidence,
  emit `null` only if the template explicitly types the field as
  `["string", "null"]` or similar.  Otherwise omit or use an empty array.
- **Ambiguous identities**: When duplicate-candidate signals are mixed (some
  match, some conflict), lean toward `needs_review` / `review_hold`.  Cite
  the specific conflict signals that prevent a clean merge.
- **Enum not found**: If the evidence doesn't cleanly fit any allowed enum
  value, re-read the evidence more carefully -- the design intent is that
  exactly one value applies.  Do not invent new values.
