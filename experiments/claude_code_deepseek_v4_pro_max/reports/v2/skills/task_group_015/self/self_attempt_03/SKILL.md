# EHR Data Governance & Clinical Record Quality Control

## Overview

This skill covers five EHR quality-control task types on a shared FHIR-like REST API:
duplicate-patient reconciliation, referral-batch audit, handoff-packet completeness
review, service-request (order) validation, and referral chart-update decisions.

**Base URL**: replace any `<TASK_ENV_BASE_URL>`, `localhost`, or `127.0.0.1`
reference with the value from `environment_access.md`.

---

## API Endpoint Index

| Endpoint | Purpose |
|---|---|
| `GET /api` | Endpoint directory |
| `GET /api/patients` | All patients (inline clinical lists) |
| `GET /api/patients/<id>` | Single patient with inline lists |
| `GET /api/patients/<id>/problems` | Problems list |
| `GET /api/patients/<id>/medications` | Medications list |
| `GET /api/patients/<id>/allergies` | Allergies list |
| `GET /api/patients/<id>/encounters` | Encounters list |
| `GET /api/patients/<id>/immunizations` | Immunizations list |
| `GET /api/patients/<id>/disclosures` | Disclosures list |
| `GET /api/duplicate-candidates` | All duplicate candidates |
| `GET /api/duplicate-candidates/<id>` | Single candidate |
| `GET /api/referrals` | All referrals (flat list) |
| `GET /api/referral-batches` | All batches |
| `GET /api/referral-batches/<id>` | Single batch with inline referrals |
| `GET /api/handoff-packets` | All handoff packets |
| `GET /api/handoff-packets/<id>` | Single packet |
| `GET /api/service-requests` | All service requests |
| `GET /api/service-requests/<id>` | Single request |
| `GET /api/providers` | Provider directory |
| `GET /api/codebook/icd10` | ICD-10 reference codes |
| `GET /api/documents` | Reference documents |
| `GET /api/audit-log` | Full audit log |

**API discovery workflow**: always start at `GET /api` to confirm available
endpoints. Then navigate to the specific resource by ID. For patient-centric
tasks, fetch the patient (which embeds clinical lists) and use sub-resource
endpoints for detail views.

---

## Data Models

### Patient

```
patient_id, first_name, last_name, dob (YYYY-MM-DD), address, phone, email,
enterprise_mrn, primary_provider_id
Inline lists: problems[], medications[], allergies[], encounters[],
              immunizations[], disclosures[], documents[]
```

Each clinical item carries:
- `id` — unique stable identifier
- `status` — `"active"` or `"inactive"`
- `code` — ICD-10 (problems), RxNorm-like (medications), allergy code (allergies)
- `label` / `description` — human-readable name
- Item-specific: `dose` (meds), `reaction` + `severity` (allergies), `date` (encounters, immunizations, disclosures)

### Duplicate Candidate

```
candidate_id, patient_ids[], match_reasons[], risk_flags[], suggested_action
```

Suggested actions: `"review_for_merge"`, `"clarify_before_merge"`, `"do_not_merge"`.

### Referral (inside a batch or flat list)

```
referral_id, batch_id, patient_first_name, patient_last_name, patient_dob,
diagnosis_description, icd10_code, insurance_id, insurance_provider,
auth_required, auth_status, imaging_received, records_received,
appointment_scheduled, urgency, notes, referring_physician, referring_fax,
referring_practice, referral_reason, date_received
```

### Referral Batch

```
batch_id, month (YYYY-MM), service_line
referrals[] — inline array of referral objects
```

### Handoff Packet

```
packet_id, patient_id, sending_provider_id, receiving_provider_id,
receiving_facility, created_date, transfer_reason,
included_sections[], cognitive_status, functional_status, notes
```

### Service Request

```
request_id, patient_id, status ("draft"), intent ("order"),
note_text (SBAR narrative), linked_encounter_ids[],
priority, service_code, service_display, specialty,
authored_on (ISO-8601), occurrence_datetime (ISO-8601)
```

### ICD-10 Codebook Entry

```
code, description, body_site, chapter_prefix, laterality ("left"/"right"/""),
in_musculoskeletal_tracking_range (boolean)
```

### Provider

```
provider_id, name, specialty, fax
```

### Audit Log Entry

```
event_id, event_type, patient_ids[], status, timestamp, user
```

---

## Universal Output Conventions

### Enum Values (exact casing — never alter)

| Enum set | Values |
|---|---|
| `audit_status` | `READY_FOR_MERGE`, `BLOCKED_ADDRESS_CONFLICT`, `NO_EVENT_FOUND` |
| `disposition` | `MERGE_READY`, `NEEDS_CLARIFICATION`, `DO_NOT_MERGE` |
| `priority_tier` | `TIER_1_IMMEDIATE`, `TIER_2_SHORT_TERM`, `TIER_3_ADMINISTRATIVE` |
| `readiness` | `READY`, `READY_WITH_WARNINGS`, `BLOCKED_INCOMPLETE_PACKET`, `NEEDS_CLARIFICATION`, `BLOCKED_ORDER_SAFETY` |
| `send_ready` | `READY`, `NEEDS_CLARIFICATION`, `BLOCKED` |
| `boolean` | `true`, `false` (JSON literals, not strings) |

### Identifier/List Ordering

**Default rule**: All lists of stable identifiers must be sorted **ascending**
(alphanumeric, lexicographic). This applies to:
- Patient ID lists
- Referral ID lists
- Problem code lists, medication ID lists, allergy label lists
- Encounter ID lists, immunization ID lists
- Duplicate group lists
- Any list field whose name does NOT contain "queue" or "ranking"

**Exception — priority queues**: Fields named `priority_queues`, `tier*`,
or explicitly labeled as a priority queue maintain their rank-group order
(Tier 1 first, Tier 2 second, Tier 3 third). Within each tier, IDs are
**still sorted ascending**.

### Numeric Precision
- Counts are integers.
- Decimal scores/ratios round to 3 decimal places.

### Date Formats
- Dates: `YYYY-MM-DD`
- Timestamps: ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`)

### Output Format
Return a single JSON object. No explanatory prose outside the JSON.

---

## Clinical List Filtering Rules

### Active-Only Filtering

When a field asks for **active** or **preserved active** items, filter strictly
by `"status": "active"`. Inactive items (`"status": "inactive"`) must never
appear in active lists.

This applies to:
- `preserved_active_problem_codes` — only codes where status is `"active"`
- `preserved_active_medication_ids` — only IDs where status is `"active"`
- `preserved_active_allergy_labels` — only labels where status is `"active"`
- `active_problem_codes` — same
- `active_medication_ids` — same
- `active_allergy_labels` — same

### Deduplication

When merging two patient records, deduplicate by code (for problems/allergies)
or by code/label (for medications). If both source and target share the same
code, include it once. The union of distinct active items from both records
is preserved.

### Recent Encounters

"Recent" encounters are determined by sorting the encounters list by `date`
descending. The task's lookback window or explicit count determines how many
to include. Unless specified otherwise, include encounters from the most
recent ~90 days.

### Most Recent Immunization

Sort immunizations by `date` descending; the first entry is the most recent.
Return its `id`.

---

## Task-Specific Workflows

### 1. Duplicate Candidate Reconciliation

**Goal**: Decide whether to merge two patient records flagged as potential duplicates.

**Workflow**:
1. `GET /api/duplicate-candidates/<candidate_id>` — get candidate with `patient_ids[]`
2. `GET /api/patients/<patient_id>` for each patient — compare demographics and clinical data
3. `GET /api/audit-log` — find the audit event whose `patient_ids` match the candidate
4. `GET /api/providers` — for contact-action provider lookup

**Business rules**:

- **Canonical target selection**: The patient record with richer clinical data
  (more active problems + medications + allergies, more encounters, active
  disclosures) is the canonical target. The other is the source.
- **Audit status**: Map the matching audit-log event's `status` field:
  - `"ready_for_merge"` → `READY_FOR_MERGE`
  - `"blocked_address_conflict"` → `BLOCKED_ADDRESS_CONFLICT`
  - No matching event found → `NO_EVENT_FOUND`
- **Disposition**:
  - Audit `ready_for_merge` + no risk flags → `MERGE_READY`
  - Audit `blocked_address_conflict` or risk flags present (e.g. `conflicting_current_address`, `expired_disclosure_on_source`) → `NEEDS_CLARIFICATION`
  - Candidate `suggested_action` is `"do_not_merge"` (e.g. `different DOB`, `similar name only`) → `DO_NOT_MERGE`
- **Preserved items**: Union of all active problems/medications/allergies from
  both patients, deduplicated by code, sorted ascending by code/ID/label.
- **Excluded patient IDs**: Empty list `[]` unless there is a patient that
  should NOT be merged (rare — only when a third patient is implicated or one
  record is definitively not a duplicate).
- **Merge audit event ID**: The `event_id` from the matching audit log entry.
- **Contact action**: If disposition requires clarification, identify the
  provider to contact (usually the primary provider of the canonical target).
  `target_provider_id` is a provider ID string. `action_code` describes the
  action category. `action_required` is boolean.

**Common pitfalls**:
- Including inactive problems/medications in preserved lists
- Picking the less-complete record as canonical target
- Missing the audit log event because the patient_ids order differs from the candidate
- Forgetting to sort preserved IDs ascending

---

### 2. Referral Batch Quality Audit

**Goal**: Audit a batch of referrals for coding errors, duplicates, missing
items, insurance anomalies, and triage priority.

**Workflow**:
1. `GET /api/referral-batches/<batch_id>` — get batch with all referrals
2. `GET /api/codebook/icd10` — load full codebook for validation
3. `GET /api/providers` — for reference (referring physician validation if needed)

**Business rules**:

- **Duplicate detection**: Two or more referrals are duplicates when they share
  the same patient (same first_name + last_name + dob) AND the same ICD-10
  code. Group their referral IDs into a sub-list. Sort groups ascending by
  first referral ID, and IDs within each group ascending.

- **Laterality mismatch**: Compare the laterality word in `diagnosis_description`
  ("left"/"right") against the codebook entry's `laterality` field for that code.
  If they differ, flag the referral ID. Common keywords: "left", "right",
  "bilateral". A code with `laterality: ""` (unspecified) is NOT a mismatch
  unless the description explicitly names a side.

- **Narrative mismatch**: The `notes` field explicitly indicates a code
  problem (e.g. "Narrative does not match code", "ICD code may need review").
  Also, when the `diagnosis_description` body site/condition clearly doesn't
  match the codebook `description` for that code. Flag the referral ID.

- **Out-of-range codes**: Any ICD-10 code where
  `in_musculoskeletal_tracking_range` is `false` for an orthopedic batch
  (or more generally, codes outside the service line's tracking range).
  Check the `chapter_prefix` and the boolean field.

- **Corrected code suggestions**: For each referral with a laterality mismatch
  or narrative mismatch, find the correct code from the codebook. Match by:
  same body site, correct laterality, matching description keywords. Return a
  map of `{referral_id: corrected_icd10_code}`. **Do not include** referrals
  that have no code correction needed. Preserve the code format exactly as
  it appears in the codebook (including decimal and any suffix letters).

- **Insurance anomalies**: An insurance_id is anomalous when it is used by
  **two or more different patients** (different name+DOB). For each anomalous
  insurance_id, report:
  - `insurance_id`: the shared ID
  - `related_duplicate_referral_ids`: referrals that are duplicates of each
    other (same patient) among those sharing this insurance — sorted ascending
  - `unrelated_referral_ids`: referrals for genuinely different patients
    sharing this insurance — sorted ascending
  Sort anomaly objects ascending by `insurance_id`.

- **Missing counts** (integers):
  - `auth_not_submitted`: count referrals where `auth_required == "Yes"` AND `auth_status == "Not Submitted"`
  - `imaging_missing`: count referrals where `imaging_received == "No"`
  - `records_missing`: count referrals where `records_received == "No"`

- **Priority queues**:
  - **Tier 1 (immediate)**: Referrals with `"PRIORITY"` in the `notes` field,
    or life/limb-threatening acute conditions (pathological fracture with
    oncology coordination, stat priority). Also referrals where urgency
    indicates imminent risk.
  - **Tier 2 (short-term)**: `urgency == "Urgent"` referrals that do NOT
    qualify for Tier 1.
  - **Tier 3 (administrative)**: `urgency == "Routine"` referrals with no
    special flags.
  - Within each tier, sort referral IDs ascending.

**Common pitfalls**:
- Not checking the codebook's `in_musculoskeletal_tracking_range` boolean for
  out-of-range detection (don't rely on chapter prefix alone)
- Missing the notes field hints ("Narrative does not match code", "ICD code
  may need review", "PRIORITY: ...")
- Treating same-patient duplicate referrals as an insurance anomaly
- Confusing left/right laterality direction
- Including referrals without corrections in `corrected_code_suggestions`
- Forgetting to sort IDs within each tier and each duplicate group

---

### 3. Handoff Packet Completeness Review

**Goal**: Evaluate a care-transition handoff packet for completeness and
determine readiness to send.

**Workflow**:
1. `GET /api/handoff-packets/<packet_id>` — get packet metadata
2. `GET /api/patients/<patient_id>` — get full patient chart
3. `GET /api/patients/<patient_id>/encounters` — encounters detail
4. `GET /api/patients/<patient_id>/immunizations` — immunizations detail
5. `GET /api/patients/<patient_id>/disclosures` — disclosures detail
6. `GET /api/providers` — provider directory

**Expected complete packet sections** (for skilled-nursing / post-acute transition):
`demographics`, `active_problems`, `active_medications`, `allergies`,
`recent_encounters`, `immunizations`, `functional_status`, `cognitive_status`,
`transfer_plan`, `disclosure`

**Business rules**:

- **Missing packet sections**: Sections expected but absent from
  `included_sections[]`. Also check the `notes` field — it often calls out
  specific omissions (e.g. "Cognitive status is omitted from the packet
  draft"). Report missing section names sorted ascending.

- **Active clinical lists**: Extract from patient chart, filtering by
  `status == "active"`:
  - `active_problem_codes`: ICD-10 codes, sorted ascending
  - `active_medication_ids`: medication IDs, sorted ascending
  - `active_allergy_labels`: allergy labels (not codes), sorted ascending

- **Patient ID**: The `patient_id` from the packet.

- **Most recent immunization ID**: Sort patient immunizations by `date`
  descending; return the `id` of the most recent.

- **Recent encounter IDs**: Sort patient encounters by `date` descending;
  return IDs for encounters within a reasonable recency window (typically
  the 3 most recent, or all within ~90 days). Sorted ascending.

- **Disclosure status**: Check if the patient has an active disclosure
  (`status == "active"`) matching the receiving facility/provider. If yes,
  report the status value. If multiple, note the most recent. If none,
  report accordingly (e.g. `"none"` or `"missing"`).

- **Readiness determination**:
  - All expected sections present, active disclosure exists, no issues → `READY`
  - Minor sections missing (e.g. cognitive_status), non-critical warnings in
    notes → `READY_WITH_WARNINGS`
  - Critical sections missing (demographics, active_problems, medications,
    allergies) → `BLOCKED_INCOMPLETE_PACKET`
  - Significant clinical gaps or conflicting information → `NEEDS_CLARIFICATION`
  - Safety-critical issue (wrong patient, wrong facility, medication safety) →
    `BLOCKED_ORDER_SAFETY`

- **Risk flags**: Identify clinical risk factors from the patient chart:
  anticoagulation therapy, severe allergies (severity: "Severe"), polypharmacy
  (≥5 active meds), advanced age (≥75), multiple chronic conditions,
  recent hospitalization. Report as descriptive strings sorted ascending.

**Common pitfalls**:
- Including inactive problems/medications in active lists
- Using allergy codes instead of labels for `active_allergy_labels`
- Not reading the packet's `notes` field for explicit omission hints
- Forgetting to sort encounter IDs ascending after selecting recent ones
- Overlooking that `cognitive_status` is an expected section even when the
  field in the packet JSON is empty

---

### 4. Service Request (Order) Validation

**Goal**: Validate a draft service request (referral order) for SBAR
completeness, laterality consistency, and readiness to sign.

**Workflow**:
1. `GET /api/service-requests/<request_id>` — get the draft
2. `GET /api/patients/<patient_id>` — get patient chart and linked encounters
3. `GET /api/codebook/icd10` — codebook for laterality/ICD-10 validation
4. `GET /api/providers` — provider reference

**Business rules**:

- **SBAR parsing**: Parse `note_text` for the four SBAR sections. The text
  typically uses labels like `Situation:`, `Background:`, `Assessment:`,
  `Recommendation:`. For each section, check whether substantive content
  follows the label:
  - `SITUATION`: true if non-empty content after label
  - `BACKGROUND`: true if non-empty content after label
  - `ASSESSMENT`: true if non-empty content after label
  - `RECOMMENDATION`: true if non-empty content after label
  - A section is **missing** if the label is absent OR present with no
    content after it (trailing label with empty/whitespace-only text).

- **Missing SBAR sections**: List the section names (SITUATION, BACKGROUND,
  ASSESSMENT, RECOMMENDATION) that are missing. Sorted ascending.

- **Laterality consistency**: Extract laterality from the `note_text`
  (look for "left"/"right" near anatomical terms) and from the service
  display/specialty context. Compare against the linked encounter diagnoses
  and the patient's active problem codes. Check codebook laterality for
  the encounter/problem ICD-10 codes.
  - `true` if all references agree on the side
  - `false` if there is a conflict (e.g. note says "left" but encounter
    code is for "right")

- **Evidence encounter IDs**: The `linked_encounter_ids[]` from the request
  that provide clinical evidence for the order. Sorted ascending.

- **Blocker codes**: Issues preventing the order from being signed:
  - Missing SBAR sections (especially RECOMMENDATION)
  - Laterality inconsistency
  - Missing required clinical evidence
  - Report as descriptive strings sorted ascending.

- **Ready to sign**: `true` only if all SBAR sections are present, laterality
  is consistent, and there are no blocking issues. `false` otherwise.

- **Order validation**: Derive validation fields from the request:
  - `priority`: from the request's `priority` field
  - `service_code`: from the request's `service_code`
  - `specialty`: from the request's `specialty`
  - `status`: from the request's `status`

- **Patient ID**: The `patient_id` from the request.

**Common pitfalls**:
- Not detecting a trailing section label with no content (e.g.
  "Recommendation:" at end of text with nothing after)
- Confusing left/right in laterality comparison
- Using the wrong encounter IDs (use `linked_encounter_ids`, not all
  patient encounters)

---

### 5. Referral Chart-Update Decision

**Goal**: Review a referral against the patient chart and determine what
chart updates are needed, whether the referral is ready to send, and what
quality issues remain.

**Workflow**:
1. `GET /api/referrals` — find the referral by ID (list endpoint if direct
   ID access returns 404)
2. `GET /api/patients/<patient_id>` — full patient chart
3. `GET /api/patients/<patient_id>/encounters` — recent encounters
4. `GET /api/patients/<patient_id>/allergies` — current allergies
5. `GET /api/providers` — provider directory for referral target
6. `GET /api/codebook/icd10` — for diagnosis code validation

**Business rules**:

- **Referral data**: Extract from the referral object. If the direct
  `GET /api/referrals/<id>` returns 404, find it in the
  `GET /api/referrals` list.

- **Allergy update**: Check the referral `notes` field for allergy-related
  instructions (e.g. "Add severe iodinated contrast allergy before sending").
  If the patient's allergy list does NOT contain the mentioned allergen,
  populate `allergy_update` with the required fields:
  - `allergen`: the allergen name from the note
  - `reaction`: the reaction type if specified, otherwise infer from context
  - `severity`: from the note or infer (e.g. "severe" → "Severe")
  - `status`: `"active"` (new allergy to be added)
  If no allergy update is needed, use an empty object or omit.

- **Diagnosis update**: Compare the referral's `icd10_code` and
  `diagnosis_description` against the patient's active problems. If the
  referral diagnosis is already an active problem, the update confirms it.
  If it's missing, the update provides the code and description to add.
  - `code`: the ICD-10 code
  - `description`: the codebook description matching that code

- **Referral target**: Identify the appropriate receiving provider:
  - `provider_id`: match by specialty to the referral reason (e.g.
    cardiology referral → provider with "Heart Failure" or "Cardiology"
    specialty)
  - `specialty`: the matched provider's specialty string

- **Recent encounter IDs**: Patient encounters sorted by date descending,
  take the most recent (typically 2-3). Return IDs sorted ascending.

- **Safety flags**: Quality/safety concerns derived from the chart and referral:
  - Missing allergies that the referral notes require
  - Medication-related risks (e.g. diuretics requiring electrolyte monitoring)
  - Missing documentation or auth
  - Report as descriptive strings sorted ascending.

- **Send ready**:
  - `READY`: all required chart updates are reflected, no safety flags remain,
    all documentation complete
  - `NEEDS_CLARIFICATION`: pending actions (e.g. allergy not yet added to
    chart, missing auth), or informational gaps
  - `BLOCKED`: safety-critical issue that must be resolved before sending

- **Letter merge fields**: Data elements that are missing or need to be
  populated for a complete referral letter. Report as field name strings
  sorted ascending.

- **Unresolved quality issues**: Remaining problems that need attention before
  the referral can be finalized. Report as descriptive strings sorted ascending.

**Common pitfalls**:
- Not checking the referral notes for explicit action items
- Assuming the referral's direct GET endpoint works — always fall back to the list
- Not matching the provider specialty correctly to the referral reason
- Missing the distinction between active chart problems and the referral diagnosis

---

## Source Precedence

When data from multiple sources conflicts, use this precedence order
(highest first):

1. **ICD-10 codebook** — authoritative for code validity, laterality, descriptions
2. **Patient chart** — authoritative for clinical data (problems, meds, allergies, encounters)
3. **Audit log** — authoritative for quality review history and merge status
4. **Referral / batch** — authoritative for referral-level administrative fields
5. **Handoff packet / service request** — authoritative for their own metadata

When clinical data conflicts between two duplicate patient records, the
**more complete record** (more active items, encounters, disclosures) takes
precedence for the canonical target selection. The source record's unique
active items are preserved in the merge.

---

## Common Cross-Task Pitfalls

1. **Not filtering by `status: "active"`** — This is the #1 error. Always
   check `status` before including any clinical item in an active list.
   Inactive items appear in patient charts but must be excluded.

2. **Identifier sort order** — Every list of IDs/codes/labels must be sorted
   ascending unless the field name explicitly signals a priority queue.
   Forgetting to sort is a common failure.

3. **Enum casing** — All enum values use `UPPER_SNAKE_CASE`. Using lowercase
   or mixed case will fail validation.

4. **Notes field blindness** — The `notes` field on referrals, handoff
   packets, and batches contains explicit quality flags (PRIORITY, code
   review hints, allergy instructions, omission notes). Always read it.

5. **Laterality confusion** — When comparing description laterality to
   codebook laterality, be precise about which side is named. "Left" in
   description + "right" in codebook = mismatch.

6. **Duplicate vs. insurance anomaly** — Same-patient, same-code referrals
   are duplicates, not insurance anomalies. Insurance anomalies require
   the same insurance_id used by DIFFERENT patients.

7. **Direct endpoint 404** — Some referral IDs may not be accessible via
   `GET /api/referrals/<id>` but are present in the list endpoint. Always
   fall back to `GET /api/referrals` and filter client-side.

8. **Empty vs. missing sections** — In SBAR parsing, a section label followed
   by no content is MISSING (not present). In handoff packets, check both
   `included_sections[]` AND the `notes` field for omissions.

9. **Disclosure matching** — When checking disclosure status for a handoff
   packet, match the disclosure `recipient` to the packet's
   `receiving_facility` or `receiving_provider_id`.

10. **Deduplication on merge** — When two patients share the same problem
    code or medication code, include it once. Don't double-count.

11. **Corrected code suggestions map** — Only include referral IDs that
    actually need a correction. An empty map `{}` is correct when no
    codes need changing. Never include referrals without corrections.

12. **Most-recent determination** — For encounters and immunizations, sort
    by date descending and take the first N or the first entry. Don't
    assume insertion order in the API response is chronological.
