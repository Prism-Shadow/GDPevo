# Workflow Instructions

Each section below matches one workflow family from the dispatch table in
SKILL.md. Read the section that matches the task prompt, then follow its
step-by-step gathering and assembly instructions.

## Duplicate Merge Packet

Used when the prompt mentions a duplicate candidate, merge readiness, or
"duplicate-chart merge readiness packet."

### Step 1: Gather Records

Read the answer template to identify every required top-level key. Then fetch
in parallel:

- `GET /api/duplicates/{candidate_id}` for the candidate detail
- `GET /api/patients/{target_id}` and `GET /api/patients/{source_id}` for both
  patient demographics (the candidate object tells you which is the primary and
  which is the possible duplicate)
- For both patients: conditions, medications, allergies, documents, and audit
  logs
- `GET /api/providers/{primary_care_provider_id}` for the PCP
- If any document is an external continuity document owned by a specialist,
  fetch that specialist via `GET /api/providers/{specialist_id}`

### Step 2: Determine Merge Disposition

The duplicate candidate record provides `match_signals` and `conflict_signals`.
Use these rules:

- If the candidate `status` is `confirmed_duplicate` and conflict signals are
  absent or minor (e.g. only address-abbreviation differences), disposition is
  `ready_to_merge` / `merge_ready`.
- If there are substantive conflicts (different DOB, different insurance,
  opposite laterality problems), disposition is `needs_review` /
  `needs_manual_review`.
- If the candidate `status` is `not_duplicate`, disposition is `do_not_merge`.

The canonical target is the patient whose record is more active/complete
(the primary in the candidate record, or the one with an active rather than
shell record). The source is the other patient.

### Step 3: Build Active Key Unions

For each clinical domain (conditions, medications, allergies), gather
`normalized_key` values from active records on both patients, take the union,
and sort alphabetically.

Additionally reconcile the union against each patient's own active-list
endpoints: any key present in a patient endpoint but missing from the duplicate
candidate's preview should be recorded in `active_list_reconciliation` fields.

### Step 4: Identity Signals & Evidence

Copy `match_signals` and `conflict_signals` from the candidate record into the
output, sorted alphabetically. Derive `demographic_matches` and
`demographic_conflicts` from comparing the two patient demographic objects
field by field.

For documents: include only identity-relevant or external-continuity documents
(document IDs referenced by the duplicate candidate, plus documents where
`subject_patient_id` crosses between the two patients). Exclude chart summaries
and unrelated documents. Document the excluded documents in
`excluded_distractors`.

For audit records: include audit IDs from the candidate, plus any audits where
`subject_patient_id` matches either patient and the event relates to the merge
or identity work.

### Step 5: Provider Contact

Identify the specialist provider whose external document appears on the source
duplicate shell (if any). Look up their full details. Include the PCP from the
target patient's demographic record. The specialist `contact_reason` should
describe why their involvement is needed (e.g. external continuity document
ownership).

### Step 6: Readiness

Set `ready_to_send` / `ready_for_merge_packet` to `true` if the disposition is
`ready_to_merge`, identity signals are clear, and no blocking issues exist.
Otherwise set the appropriate `readiness_status` and list required review notes.

---

## Referral Coordination Packet

Used when the prompt mentions a single referral (by ID) and "referral
coordination packet" or "referral letter."

### Step 1: Gather Records

Read the answer template, then fetch in parallel:

- `GET /api/referrals/{referral_id}` for the referral detail
- `GET /api/patients/{patient_id}` for patient demographics
- Patient conditions, medications, allergies, encounters, and documents
- `GET /api/providers/{receiving_provider_id}` for the receiving provider
- `GET /api/icd10/{diagnosis_code}` and any supporting codes

### Step 2: Active Diagnoses

List every active condition from the patient's condition endpoint. For each,
include the ICD-10 `code`, `description`, `normalized_key`, `source` (use
`problem_list` for conditions from the patient endpoint, `referral_intake` for
any additional diagnosis mentioned only on the referral form), and
`referral_relevant` (true if the condition relates to the referral's service
line and diagnosis narrative). Sort by `code` ascending.

### Step 3: Referral Code Set

The primary code is the referral's `diagnosis_code`. Supporting codes are
additional ICD-10 codes from the referral or recent encounter that support the
referral reason. For each code, look up the ICD-10 entry and validate:

- `icd_validation`: `valid_matches_narrative` if the code description aligns
  with the referral narrative and the service line; `valid_but_narrative_mismatch`
  if the code exists but does not match the narrative; `invalid_code` if the
  code is not in the ICD-10 directory; `wrong_service_chapter` if the code's
  chapter does not match the referral service line.
- `primary_code_chapter`: the chapter string from the ICD-10 lookup.
- `narrative_match`: boolean judgment from comparing code description against
  the referral narrative.

### Step 4: Allergy Readiness

Collect active allergies from the patient endpoint and any allergies listed on
the referral form. Determine `readiness_status`:
- `complete_documented` if at least one allergy record exists with reaction and
  severity;
- `no_known_allergies` if the patient has a "No Known Allergies" entry;
- `incomplete_needs_clarification` if allergies are mentioned but reaction
  or severity is missing;
- `conflicting_allergy_records` if the patient and referral form disagree.

Set `ready_for_letter` true only when allergies are complete or explicitly NKA.

### Step 5: Recent Encounter Evidence

Scan encounters for the most recent one that has a care plan tag matching the
referral intent (e.g. `cardiology_referral_for_hfpef_dyspnea`). It should be
signed and dated within a reasonable pre-referral window (the most recent visit
before the referral date). Extract the encounter's diagnosis codes and
medications mentioned.

### Step 6: Required Document Evidence

From the referral's `required_documents` and `received_document_ids`, determine
which required documents are present and which are missing. Look up each
received document in the patient's document list to confirm type, date, and
status.

### Step 7: Receiving Provider, Authorization, Medications

- Look up the receiving provider from the referral's `receiving_provider_id`.
- Read `authorization_status`, `referral_status`, and `urgency` from the
  referral. Derive `overall_readiness` from the combination of authorization,
  documents, and allergy readiness. List any `blocking_issues`.
- Scan active medications for those relevant to the referral: diuretics for
  heart failure, antihypertensives for blood pressure management, etc. Each
  gets a `highlight_reason` from the template's enum.

### Step 8: Referral Letter Fields

Map each clinical finding to the appropriate template enum choice. These are
discrete choices, not free text. Match the diagnosis summary, allergy statement,
recent encounter, document packet, medication summary, recipient, authorization
statement, and readiness to the enum values defined in the template.

---

## Care Transition Packet

Used when the prompt mentions a single patient + recipient provider for a care
transition or handoff.

### Step 1: Gather Records

Read the answer template, then fetch in parallel:

- `GET /api/patients/{patient_id}` and all sub-resources: conditions,
  medications, allergies, encounters, immunizations, disclosures
- `GET /api/providers/{recipient_provider_id}`

### Step 2: Patient & Recipient

Populate the `patient` object from demographics. Populate `recipient` from the
provider lookup.

### Step 3: Active Clinical Lists

Filter conditions, medications, and allergies to active status only. Extract
`normalized_key` values and sort alphabetically.

### Step 4: Handoff Encounters

The template specifies a fixed count (e.g. 4) of handoff encounters. Select
encounters within a relevant pre-transition window (typically the most recent
signed encounters up to a few months back). Exclude encounters that are not
signed, are too old (beyond the window), or are unrelated to the service line.

Rules for selection:
- Prefer signed encounters over unsigned/draft.
- Prefer encounters whose type or care plan tag relates to the service line.
- Take the N most recent by date, newest first.
- Record the selection basis (e.g. `orthopedic_surgical_handoff_window`),
  selected IDs, and excluded IDs in `source_selection`.

### Step 5: Immunization & Disclosure

- Latest immunization: the most recent completed immunization by date.
- Disclosure: the disclosure record matching `recipient_provider_id`. If
  multiple exist, take the most recent. If `status` is not `permitted`, the
  packet readiness should reflect this.

### Step 6: Risk Flags

Derive risk flags from the active clinical lists using the allowed values in
the template. Common derivations:

- `cognitive_memory_loss`: triggered by conditions with `memory_loss` or
  cognitive-decline normalized keys.
- `fall_risk_note_required`: triggered by lower-extremity OA conditions (hip,
  knee) combined with relevant medications (e.g. acetaminophen for pain).
- `hypertension`: triggered by the hypertension condition key.
- `insulin_dependent_diabetes`: triggered by diabetes + insulin medication.
- `latex_allergy`: triggered by active latex allergy.
- `perioperative_glucose_plan_needed`: triggered by diabetes + insulin when
  the transition is surgical.

For each risk flag, populate `risk_flag_evidence` with the specific condition
keys, medication keys, and encounter IDs that support it. Sort both the
`risk_flags` array and the evidence array alphabetically by flag code.

### Step 7: Readiness

Set `status` to `ready` if no risk flags and all required data is present;
`ready_with_risk_flags` if risk flags exist but no hard blockers;
`not_ready` if the disclosure is not permitted or critical data is missing.
List any `blocking_issue_codes` from the template's allowed values.

---

## ServiceRequest Quality Review

Used when the prompt mentions a ServiceRequest ID, a duplicate candidate,
and asks for quality-governance review.

### Step 1: Gather Records

Read the answer template, then fetch in parallel:

- `GET /api/duplicates/{candidate_id}`
- `GET /api/patients/{primary_patient_id}` and `GET /api/patients/{possible_duplicate_id}`
- Service requests for the primary patient (find the specific SR by ID)
- Conditions for the primary patient
- `GET /api/service-codes/{service_code}`
- `GET /api/icd10/{reason_code}` for each reason code on the SR
- `GET /api/providers/{requester_id}` and `GET /api/providers/{performer_id}`

### Step 2: Duplicate Review

From the candidate record, copy the status, decision, patient IDs, match
signals, and conflict signals. If the candidate status is `needs_review` due to
conflicting signals, the decision is `review_hold` and merge targets are null.
If confirmed, the decision is `merge` with populated target/source.

### Step 3: ServiceRequest Validation

Populate every required SR field from the ServiceRequest record. For
`service_code_valid`, look up the code in the service-code endpoint.

For each `reason_code` on the SR, validate:
- `valid`: code exists in ICD-10 directory.
- `chapter`: from ICD-10 lookup.
- `matches_patient_evidence`: the code's description aligns with an active
  condition on the primary patient's problem list.

### Step 4: SBAR Coverage

Check whether the SR contains the Situation, Background, Assessment, and
Recommendation elements. The SR record typically has an `sbar_sections` field
or the narrative text can be scanned for these four section headers. Populate
`sections_present` and `missing_sections` accordingly. Set `complete` to true
only when all four sections are present.

---

## Referral Batch Audit

Used when the prompt mentions a referral batch ID and asks for a formal audit.

### Step 1: Gather Records

Read the answer template, then fetch:

- `GET /api/referrals` filtered by batch ID to get all referral rows
- For each unique patient: `GET /api/patients/{id}` (demographics only, unless
  deeper clinical data is needed for mismatch validation)
- For each unique diagnosis code: `GET /api/icd10/{code}`
- For each unique provider referenced: `GET /api/providers/{id}`
- Insurance and duplication analysis may need cross-patient lookups

**Important:** Do not fetch the same ICD-10 code or provider twice. Deduplicate
before fetching.

### Step 2: Batch Summary

Count total referral rows and unique patients. Read `batch_id`, `service_line`,
and `requested_date` from any referral record in the batch.

### Step 3: Invalid or Out-of-Range Code Referrals

For each referral in the batch, look up its `diagnosis_code` in ICD-10. If the
code's chapter does not match the expected chapter for the service line (e.g.
`Musculoskeletal` for orthopedics), flag it. The `issue_type` is
`out_of_range_chapter`. If the code is not found in ICD-10 at all, use
`unknown_code`.

Sort flagged referrals by `referral_id` ascending.

### Step 4: Laterality and Narrative Mismatches

For each referral, compare the `diagnosis_narrative` against the ICD-10 code's
description and laterality. Flag mismatches in three categories:

- `laterality_mismatch`: the code specifies one side (e.g. right knee,
  M17.11) but the narrative says the opposite side.
- `narrative_mismatch`: the code describes one condition (e.g. medial meniscus
  tear) but the narrative describes a different body region or condition
  entirely (e.g. lumbar radiculopathy).
- `missing_laterality`: the code implies a specific side but the narrative
  omits laterality.

For each flagged referral, populate `expected_terms` with the correct
descriptors from the ICD-10 directory entry that should match the narrative.

Sort flagged referrals by `referral_id` ascending.

### Step 5: Duplicate Groups

Scan the batch for multiple referrals sharing the same `patient_id`. When two
referrals for the same patient have the same or closely related diagnosis codes
and the later referral is a resubmission, group them. The `duplicate_type` is
`same_patient_resubmission` and disposition is `consolidate_under_original`.

Populate `duplicate_tiering_policy`: list the referral IDs from duplicate groups
in `tier_1_duplicate_blocker_referral_ids`, and list any same-patient referrals
that are genuinely separate clinical reviews (not duplicates) in
`separate_same_patient_referral_ids`.

### Step 6: Insurance Patient Anomalies

If two different patients share the same insurance ID, flag this as an anomaly
with type `shared_insurance_different_patients`. List the patient IDs and
referral IDs involved. Recommend `verify_insurance_membership_do_not_merge`.

### Step 7: Follow-Up Queues

Build four queues from the audit findings, each sorted by `referral_id`:

- `authorization_missing`: referrals with no authorization or authorization
  status other than `approved`.
- `authorization_pending`: referrals with authorization status `pending`.
- `records_request`: referrals missing office-note documents (check
  `required_documents` for `office_note` not in `received_document_ids`).
- `imaging_follow_up`: referrals missing imaging documents or where imaging
  status is pending.

### Step 8: Action Plan Tiers

Assign every referral to a tier based on findings:

- **Tier 1** (immediate): duplicate blockers or urgent coding issues that
  block the referral from proceeding. These are referrals in duplicate groups
  or with critical code mismatches on urgent referrals.
- **Tier 2** (short-term): routine coding, authorization, or document blockers.
  Most flagged referrals fall here.
- **Tier 3** (administrative): referrals that only need document completion
  without coding or clinical issues.

Each tier entry includes the `owner_provider_id` from the referral's receiving
provider.

Sort each tier's entries by `referral_id` ascending.

### Step 9: Summary Counts

Count everything: total rows, unique patients, urgent vs. routine counts,
and one count for every issue category and tier. The `summary_counts` keys in
the template are your checklist.
