# EHR Data-Governance and Clinical-Record Quality-Control Skill

## Overview

This skill covers five healthcare EHR quality-control task types: duplicate
chart reconciliation, referral batch auditing, handoff packet review, service
request validation, and referral chart-update decisions. All tasks share a
common REST API, output conventions, and business rules.

## Environment

The shared EHR quality API is accessed at the base URL provided in the task
scope as `environment_base_url` (substituting `<TASK_ENV_BASE_URL>` with the
actual remote URL). Always start by inspecting the API index at `GET /api` to
confirm available endpoints. All data must be fetched from the API — never
assume values.

## API Endpoints Reference

| Endpoint | Use |
|---|---|
| `GET /api` | Discover available endpoints |
| `GET /api/patients` | List all patients |
| `GET /api/patients/<id>` | Full patient record (includes embedded problems, medications, allergies, encounters, immunizations, disclosures) |
| `GET /api/patients/<id>/problems` | Problem list for a patient |
| `GET /api/patients/<id>/medications` | Medication list for a patient |
| `GET /api/patients/<id>/allergies` | Allergy list for a patient |
| `GET /api/patients/<id>/encounters` | Encounter history for a patient |
| `GET /api/patients/<id>/immunizations` | Immunization records for a patient |
| `GET /api/patients/<id>/disclosures` | Disclosure/consent records for a patient |
| `GET /api/patients/<id>/documents` | Documents attached to a patient |
| `GET /api/duplicate-candidates` | List all duplicate candidates |
| `GET /api/duplicate-candidates/<id>` | Single duplicate candidate with patient IDs |
| `GET /api/referrals` | List all referrals |
| `GET /api/referral-batches` | List all referral batches |
| `GET /api/referral-batches/<id>` | Batch details with all referral rows |
| `GET /api/handoff-packets` | List all handoff packets |
| `GET /api/handoff-packets/<id>` | Single handoff packet with sections and notes |
| `GET /api/service-requests` | List all service requests |
| `GET /api/service-requests/<id>` | Single service request with SBAR note text |
| `GET /api/providers` | Provider directory (provider_id, name, specialty, fax) |
| `GET /api/codebook/icd10` | ICD-10 codebook with laterality, body site, tracking range |
| `GET /api/documents` | Document index |
| `GET /api/audit-log` | Audit event log (merge reviews, etc.) |

## General Output Conventions

Every answer must be a single JSON object conforming exactly to the
`answer_template.json` schema provided with the task. Follow these rules
strictly:

- **Enum values**: Use the exact UPPER_SNAKE_CASE string as listed in
  `allowed_enums`. Never invent or lowercase enum values.
- **Dates**: `YYYY-MM-DD` format (e.g., `2026-03-10`).
- **Timestamps**: ISO 8601 format (e.g., `2026-03-22T09:44:00Z`).
- **Counts**: Integers. Decimal scores or ratios round to 3 decimal places.
- **Booleans**: Lowercase `true` or `false`.
- **List ordering**: All lists of stable identifiers (IDs, codes, labels) MUST
  be sorted in ascending alphanumeric order. The ONLY exception is when a
  field name or description explicitly states it represents a priority queue or
  ranking — in that case the order represents priority and must not be
  re-sorted.
- **Empty lists**: Use `[]`, never `null` or omitted keys.
- **Empty objects**: Use `{}`, never `null`.
- **Output format**: Return only the JSON object. No explanatory prose, no
  markdown fences, no trailing text.

## Clinical List Filtering Rules

**Golden rule: only include items where `"status": "active"`.**

- For **problems**: include only codes where status is `"active"`. Exclude
  `"inactive"`, `"resolved"`, or any non-active status.
- For **medications**: include only IDs where status is `"active"`. Exclude
  discontinued, held, or completed medications.
- For **allergies**: include only labels where status is `"active"`. Exclude
  resolved or historical allergies.
- For **encounters**: include all, but when a field says "recent," include
  only encounters within approximately 90 days of the reference date
  (packet date, referral date, or current date).

**Field-type mapping for clinical lists:**

| Template field ending in | Use the record's | Example |
|---|---|---|
| `_problem_codes` | `code` field | `"J44.9"` |
| `_medication_ids` | `id` field | `"MED-TR001-01"` |
| `_allergy_labels` | `label` field | `"Penicillin"` |
| `_encounter_ids` | `id` field | `"ENC-TR003-01"` |

Do NOT mix these up. A field named `preserved_active_allergy_labels` expects
allergy display labels, not allergy IDs or codes. A field named
`preserved_active_medication_ids` expects medication IDs, not labels or codes.

## Task-Specific Business Rules

### 1. Duplicate Chart Reconciliation

**Goal**: Decide whether two patient records represent the same person and
should be merged, and what clinical data to preserve.

**Workflow**:
1. Fetch the duplicate candidate via `GET /api/duplicate-candidates/<id>`.
2. Note the `patient_ids` array, `match_reasons`, and `suggested_action`.
3. Fetch the full patient record for each patient ID
   (`GET /api/patients/<id>`). The record embeds problems, medications,
   allergies, encounters, immunizations, and disclosures.
4. Also fetch each patient's dedicated sub-resources (problems, medications,
   allergies, disclosures) via the individual endpoints — they may contain
   additional detail.
5. Check `GET /api/audit-log` for audit events whose `patient_ids` field
   matches both patients.

**Merge decision rules**:
- If both patients share identical name, DOB, address, and phone → they are
  the same person. Disposition is typically `MERGE_READY`.
- If addresses differ → check for `BLOCKED_ADDRESS_CONFLICT`.
- The `canonical_target_patient_id` should be the record with more complete
  clinical data (more active problems, medications, encounters).
- The `source_patient_id` is the other patient — the one whose data will be
  merged into the canonical target.

**Audit event mapping**:
- `"ready_for_merge"` in the audit log → `"READY_FOR_MERGE"` enum.
- `"blocked_address_conflict"` → `"BLOCKED_ADDRESS_CONFLICT"` enum.
- If no matching audit event exists → `"NO_EVENT_FOUND"`.
- The `merge_audit_event_id` is the `event_id` of the matching audit event.

**Preserved lists**: Include ALL active items from ALL patients being merged.
Do NOT filter to only the source patient or only new items. Sort ascending.

**Contact action**: If both patients share the same `primary_provider_id`, use
that provider as `target_provider_id`. Set `action_required: true` when the
provider should be notified of the merge.

### 2. Referral Batch Audit

**Goal**: Audit a batch of referrals for data quality issues: duplicates,
laterality mismatches, narrative mismatches, out-of-range codes, missing
documentation, insurance anomalies, and priority classification.

**Workflow**:
1. Fetch the batch via `GET /api/referral-batches/<batch_id>`. The response
   includes all referral rows in a `referrals` array.
2. Fetch `GET /api/codebook/icd10` for laterality and range validation.
3. Cross-reference referral data against the codebook for each validation.

**Duplicate detection**: Two or more referrals are duplicates if they share the
same patient (identical `patient_first_name`, `patient_last_name`, and
`patient_dob`) AND the same `icd10_code` and `diagnosis_description`. Group
their `referral_id` values into a sorted list within the `duplicate_groups`
array.

**Laterality mismatch**: Compare the laterality in the `diagnosis_description`
text (look for "left" or "right") against the codebook's `laterality` field
for the given `icd10_code`. If they disagree, flag the `referral_id`. If the
codebook has no laterality (empty string), it is NOT a laterality mismatch
(it may be a narrative mismatch instead). Example: diagnosis says "left ankle"
but code M76.61 maps to "right leg" in the codebook → laterality mismatch.

**Narrative mismatch**: The `icd10_code` description in the codebook describes
a fundamentally different condition than the `diagnosis_description`. This is
broader than laterality — the entire condition is wrong. Also flag any
referral where `notes` explicitly state "Narrative does not match code."

**Out-of-range codes**: Any `icd10_code` whose codebook entry has
`in_musculoskeletal_tracking_range: false` is out of range for the
musculoskeletal tracking domain.

**Corrected code suggestions**: For each referral with a laterality mismatch or
narrative mismatch, provide the corrected ICD-10 code. Use the codebook to
find the correct laterality variant (e.g., M76.61 → M76.62 for left leg) or
the correct condition code (e.g., M79.3 → M70.21 for right elbow olecranon
bursitis). Preserve the exact formatting from the codebook (decimal placement,
suffix letters). Only include referrals that need a correction — do not
include referrals with correct codes.

**Missing counts**:
- `auth_not_submitted`: count referrals where `auth_status` is `"Not Submitted"`.
- `imaging_missing`: count referrals where `imaging_received` is `"No"`.
- `records_missing`: count referrals where `records_received` is `"No"`.

**Insurance anomalies**: An insurance anomaly exists when the same
`insurance_id` appears on referrals for DIFFERENT patients (different name/DOB).
- `related_duplicate_referral_ids`: referrals that are duplicates of each
  other AND share this insurance ID.
- `unrelated_referral_ids`: referrals for a DIFFERENT patient that share the
  same insurance ID. Sort all ID lists ascending.
- If no anomalies exist, return an empty array `[]`.

**Priority queues**: Classify each referral_id into one of three tiers:
- `tier1_immediate`: Urgent referrals with safety-critical issues (fractures,
  pathological fractures, oncology coordination).
- `tier2_short_term`: Referrals with quality issues needing resolution
  (duplicates, missing auth/imaging/records, code mismatches).
- `tier3_administrative`: Routine referrals with complete data and no issues.
Sort IDs ascending within each tier list.

### 3. Handoff Packet Review

**Goal**: Assess a care-transition handoff packet for completeness and
readiness.

**Workflow**:
1. Fetch the packet via `GET /api/handoff-packets/<packet_id>`.
2. Note `patient_id`, `included_sections`, `notes`, and receiving/sending
   provider IDs.
3. Fetch the patient's full chart and sub-resources (problems, medications,
   allergies, encounters, immunizations, disclosures).

**Missing sections**: Compare the `included_sections` list against the full set
of expected sections for a complete handoff packet. The packet's `notes` field
may explicitly state what is omitted (e.g., "Cognitive status is omitted from
the packet draft"). Add the section name exactly as it appears in the notes
(e.g., `"cognitive_status"`) to `missing_packet_sections`. Also check for
commonly required sections like `advance_directives` or `code_status` if the
transfer context warrants them (skilled nursing, post-acute care).

**Readiness determination**:
- `READY`: All expected sections present with content. No blocking issues.
- `READY_WITH_WARNINGS`: Minor omissions or data gaps that don't block the
  transfer but should be noted.
- `BLOCKED_INCOMPLETE_PACKET`: A critical section is entirely missing from
  the packet (e.g., cognitive status for a skilled nursing transfer).
- `NEEDS_CLARIFICATION`: Ambiguous or conflicting information needs
  resolution.
- `BLOCKED_ORDER_SAFETY`: Medication or order safety concern blocks transfer.

**Disclosure status**: Check the patient's disclosures for an active disclosure
matching the receiving facility or transfer purpose. Use `"valid"` when an
active, matching disclosure exists. Use a different status when no disclosure
or an expired disclosure is found.

**Most recent immunization**: Select the immunization with the most recent
`date`. Return its `id`.

**Recent encounters**: Include encounters whose `date` falls within
approximately 90 days before the packet `created_date`. Sort by ID ascending.
Do NOT include encounters more than ~6 months old unless the task explicitly
asks for all encounters.

**Risk flags**: Derive from clinical data. Include:
- Severe allergies (especially those with anaphylaxis or angioedema).
- Anticoagulation therapy (bleeding/fall risk).
- Fall risk indicators (mobility limitations, assistive devices).
- Missing critical assessments (cognitive status, functional status gaps).
Use human-readable short phrases, sorted alphabetically.

**Active clinical lists**: Follow the standard filtering rules — only items
with `status: "active"`. Use problem codes, medication IDs, and allergy
labels as dictated by the field names.

### 4. Service Request Validation

**Goal**: Validate a draft service request order for completeness and clinical
consistency.

**Workflow**:
1. Fetch the service request via `GET /api/service-requests/<request_id>`.
2. Note `note_text`, `linked_encounter_ids`, `patient_id`, `status`,
   `priority`, `service_code`, `specialty`, `intent`.
3. Fetch the linked encounter(s) to verify clinical evidence.
4. Optionally check the ICD-10 codebook if the service code needs validation.

**SBAR section parsing**: Parse `note_text` for the four SBAR components:
`SITUATION`, `BACKGROUND`, `ASSESSMENT`, `RECOMMENDATION`. A section is
**present** (true) only if it has substantive content after its label. A
section label followed by nothing or whitespace is NOT present (false).

**Missing SBAR sections**: List the SBAR section names (in UPPERCASE) that
are not present (false). If all are present, return `[]`.

**Evidence encounters**: Populate `evidence_encounter_ids` with the
`linked_encounter_ids` from the service request. These are the encounters that
support the clinical justification.

**Laterality consistency**: Check that the anatomical laterality described in
the `note_text` (left/right) matches the laterality of the diagnoses in the
linked encounter(s). If both agree on left or right → `true`. If they
disagree or the note doesn't specify laterality → `false`. Codes without
laterality (empty laterality in codebook) do not create an inconsistency.

**Order validation**: Copy these fields directly from the service request
response:
- `priority`: as-is from the API (e.g., `"routine"`).
- `service_code`: as-is from the API (e.g., `"306181000000106"`).
- `specialty`: as-is from the API (e.g., `"Orthopedic Surgery"`).
- `status`: as-is from the API (e.g., `"draft"`).

**Ready to sign**: `true` only when ALL of these hold:
- All four SBAR sections are present with content.
- No blocker issues (missing evidence, clinical inconsistency).
- The status is `draft` and the request is otherwise complete.
Otherwise `false`.

**Blocker codes**: List codes for issues that prevent signing. Sort ascending.

### 5. Referral Chart-Update Decision

**Goal**: Review a referral against the patient's current chart and produce a
structured update decision including any changes needed before sending.

**Workflow**:
1. Fetch the referral from `GET /api/referrals` (search for the target
   `referral_id` in the list).
2. Fetch the patient chart via `GET /api/patients/<patient_id>` and
   sub-resources.
3. Compare the referral's requirements, notes, and clinical information
   against the patient's current chart.
4. Consult `GET /api/providers` to identify the appropriate receiving
   provider.

**Allergy update**: If the referral `notes` field instructs adding an allergy
(e.g., "Add severe iodinated contrast allergy before sending"), create an
allergy update object with:
- `allergen`: The allergen name extracted from the note.
- `reaction`: The specific reaction if stated; otherwise `"Unknown"`.
- `severity`: The severity mentioned (e.g., `"Severe"`).
- `status`: `"active"`.
If no allergy instruction exists in the referral, the allergy_update may
reflect the current state or be omitted per the template schema.

**Diagnosis update**: Provide the primary diagnosis from the referral:
- `code`: The `icd10_code` from the referral.
- `description`: The `diagnosis_description` from the referral.
This reflects the referral's clinical basis, whether or not it already exists
in the patient's active problem list.

**Referral target**: Identify the most clinically appropriate provider for the
referral's specialty from the provider directory. Match by specialty relevance
to the referral reason (e.g., a heart failure referral → provider with
"Advanced Heart Failure" or "Cardiology" specialty). Provide their
`provider_id` and exact `specialty` string as it appears in the provider
record.

**Recent encounters**: Include all encounter IDs from the patient's encounter
history, sorted ascending.

**Safety flags**: Derive from clinical risk factors evident in the chart and
referral. Include documentation gaps that affect patient safety (e.g.,
missing allergy documentation for a known allergen). Sort alphabetically.

**Send ready**:
- `READY`: All quality checks pass; the identified updates are documented in
  the response and the referral can proceed.
- `NEEDS_CLARIFICATION`: Ambiguous or incomplete information requires
  follow-up before sending.
- `BLOCKED`: A hard blocker prevents sending (missing required documentation,
  safety concern).

**Letter merge fields**: List the referral data fields that populate a
standard referral letter template. Use the field names as they appear in the
referral record (e.g., `date_received`, `diagnosis_description`,
`icd10_code`, `patient_dob`, `patient_first_name`, `patient_last_name`,
`referral_reason`, `referring_physician`, `urgency`). Sort alphabetically.

**Unresolved quality issues**: List issues identified during the review that
need resolution. These are gaps between the referral requirements/notes and
the current patient chart state. Use clear, human-readable descriptions.
Sort if the template specifies ID-based sorting.

## Source Precedence

1. **API data** is authoritative for all facts about patients, referrals,
   encounters, and clinical data.
2. **Codebook** (`/api/codebook/icd10`) is authoritative for ICD-10 code
   descriptions, laterality, body site, and tracking range. Always validate
   codes against the codebook, never from memory.
3. **Referral notes** contain actionable instructions (e.g., "Add severe
   iodinated contrast allergy before sending") that must be reflected in
   quality decisions.
4. **Audit log** is authoritative for prior review events and their statuses.
   Match by `patient_ids` when looking up duplicate review events.
5. **Provider directory** is authoritative for provider IDs, names,
   specialties, and contact information.

## Common Pitfalls

1. **Including inactive items in clinical lists**: Always filter by
   `"status": "active"`. An inactive problem, medication, or allergy must
   never appear in preserved/active lists.

2. **Mixing up field-type mappings**: A field named `_codes` expects ICD-10
   codes. A field named `_ids` expects record IDs. A field named `_labels`
   expects human-readable labels. Using the wrong field from the source data
   is a common error.

3. **Forgetting to sort lists ascending**: Every list of identifiers that is
   not a priority queue must be sorted alphanumerically ascending. The only
   exception is when the field name or description explicitly says it
   represents priority/ranking order.

4. **Using wrong enum casing**: All enum values must match the
   `allowed_enums` in the answer template exactly. `"ready_for_merge"` is not
   the same as `"READY_FOR_MERGE"`.

5. **Including stale encounters in "recent" lists**: When a field asks for
   "recent" encounters, apply a recency window (~90 days from the reference
   date). Encounters from 6+ months ago are generally not "recent."

6. **Misclassifying laterality vs. narrative mismatches**: A laterality
   mismatch means the condition is correct but the side is wrong. A narrative
   mismatch means the code describes an entirely different condition. A code
   without laterality cannot have a laterality mismatch — it may have a
   narrative mismatch instead.

7. **Not checking the codebook's `in_musculoskeletal_tracking_range`**: Codes
   in chapters S, G, C, I, J, N may be clinically valid but outside the
   musculoskeletal tracking range. Always verify against the codebook.

8. **Assuming SBAR sections are present just because a label exists**: A
   section like `"Recommendation:"` followed by nothing is NOT present. Check
   for substantive content after the colon.

9. **Overlooking packet notes about omitted sections**: The `notes` field in
   a handoff packet often explicitly states what is missing. Always read it.

10. **Using insurance_id as a patient identifier**: Insurance IDs can appear
    on multiple referrals for different patients. This is an anomaly to flag,
    not a reason to group them.

11. **Failing to check the audit log for matching events**: When doing
    duplicate reconciliation, always search the audit log for events whose
    `patient_ids` array matches the candidate patients.

12. **Provider-specialty mismatches**: Match referral targets to providers by
    clinical relevance of their specialty, not just by name. Check the
    provider directory for the specialty field.
