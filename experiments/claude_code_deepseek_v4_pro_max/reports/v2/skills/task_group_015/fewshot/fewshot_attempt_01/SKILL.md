# EHR Quality Governance & Clinical Record Quality Control — Reusable SKILL

## Environment

All API calls go to the remote base URL given in `environment_access.md`
(`GDPEVO_ENV_BASE_URL`).  Do **not** use `localhost`, `127.0.0.1`,
`<TASK_ENV_BASE_URL>`, `API_BASE_URL`, `BASE_URL`, or `env/setup.sh`.  The
health check endpoint is `GET /health`.

## Task-group overview

This skill covers five classes of EHR governance/quality-control task:

1. **Duplicate-patient reconciliation** — two patient records flagged as
   possible duplicates; decide merge vs. block vs. do-not-merge.
2. **Referral-batch audit** — audit a monthly specialty referral batch for
   duplicates, ICD-10 mismatches, missing items, and triage priority.
3. **Handoff-packet completeness review** — inspect a care-transition handoff
   packet for missing sections, readiness, and risk flags.
4. **Service-request (order) validation** — validate an SBAR-structured
   service-request draft for completeness, laterality, and sign-off readiness.
5. **Referral chart-update decision** — prepare a patient-chart update ahead
   of sending a referral letter (diagnosis, allergies, safety flags, merge
   fields).

## API usage workflow

### Step 0 — Confirm available endpoints
Start every task by fetching the index:
```
GET {BASE}/api
```
The index returns a flat list of top-level paths.  The endpoints used across
all tasks are:

| Endpoint | Returns |
|---|---|
| `GET /api/patients` | List of all patient summaries |
| `GET /api/patients/<id>` | Full patient record (includes nested allergies, medications, problems, encounters, immunizations, disclosures) |
| `GET /api/patients/<id>/problems` | Problems sub-list |
| `GET /api/patients/<id>/medications` | Medications sub-list |
| `GET /api/patients/<id>/allergies` | Allergies sub-list |
| `GET /api/patients/<id>/encounters` | Encounters sub-list |
| `GET /api/patients/<id>/immunizations` | Immunizations sub-list |
| `GET /api/patients/<id>/disclosures` | Disclosures sub-list |
| `GET /api/patients/<id>/documents` | Documents sub-list (usually empty) |
| `GET /api/duplicate-candidates` | List of all duplicate-candidate summaries |
| `GET /api/duplicate-candidates/<id>` | Single duplicate-candidate detail |
| `GET /api/referrals` | Flat list of all referral rows across batches |
| `GET /api/referral-batches` | List of batch summaries |
| `GET /api/referral-batches/<batch_id>` | Batch metadata + its referral rows |
| `GET /api/handoff-packets` | List of handoff-packet summaries |
| `GET /api/handoff-packets/<packet_id>` | Single handoff packet detail |
| `GET /api/service-requests` | List of all service-request summaries |
| `GET /api/service-requests/<request_id>` | Single service-request detail |
| `GET /api/providers` | Provider directory (id, name, fax, specialty) |
| `GET /api/codebook/icd10` | Flat list of ICD-10 code objects |
| `GET /api/documents` | Reference documents (authorization templates, referral forms, quality-queue extracts) |
| `GET /api/audit-log` | Chronological audit events |

### Step 1 — Read task_scope.json
Every task provides `task_scope.json` with `target_ids` that name the primary
resource(s) to fetch.  Use those IDs to navigate to the right endpoint.

### Step 2 — Fetch the primary resource
Use the target ID to `GET` the detail endpoint for that resource.

### Step 3 — Fetch related resources
- For **duplicate candidates**: fetch both patient records plus the audit log.
- For **referral batches**: fetch the batch detail (includes all referrals);
  also fetch the full ICD-10 codebook.
- For **handoff packets**: fetch the packet detail, then the linked patient
  record (including encounters, immunizations, disclosures).
- For **service requests**: fetch the request detail, then the linked patient's
  encounter(s) referenced in `linked_encounter_ids`.
- For **referral chart-update**: fetch the referral row and the named patient
  record; cross-check the codebook for ICD-10 codes.

### Step 4 — Apply business rules (see below)

### Step 5 — Return JSON conforming to answer_template.json
Every task ships an `answer_template.json` with the exact schema, allowed
enums, and output conventions.  Return **one JSON object** with the keys,
types, enum casing, and list ordering defined there.  Include `task_id` from
`task_scope.json`.

---

## Business rules by task class

### 1. Duplicate-patient reconciliation

**Input resources**: duplicate-candidate detail, both patient records, audit
log.

**Decision logic**:

- `merge_decision.disposition`:
  - `MERGE_READY` — same legal name, same DOB, same phone, no conflicting
    address, no blocking risk flags.
  - `NEEDS_CLARIFICATION` — conflicting current address OR any risk flag that
    requires human clarification (e.g. expired disclosure).
  - `DO_NOT_MERGE` — different DOB OR risk flags that make merge unsafe
    (e.g. only a "similar name" match).

- `merge_decision.canonical_target_patient_id`: the patient record with the
  **more complete** clinical data (more active problems + medications +
  allergies).  Prefer the record whose `enterprise_mrn` is lower/smaller if
  clinical counts tie.

- `merge_decision.source_patient_id`: the other patient record (the one being
  merged *into* the target).

- `merge_decision.reason_code`:
  - `STABLE_MRN_MATCH` — basic demographic match (same name, DOB, phone).
  - `CONFLICTING_ADDRESS` — addresses differ (use with `NEEDS_CLARIFICATION`).
  - `INSUFFICIENT_EVIDENCE` — only weak/similar-name match (use with
    `DO_NOT_MERGE`).

- `audit.audit_status`:
  - `READY_FOR_MERGE` — audit log shows `status: "ready_for_merge"` for this
    patient pair.
  - `BLOCKED_ADDRESS_CONFLICT` — audit log shows `status:
    "blocked_address_conflict"`.
  - `NO_EVENT_FOUND` — no matching audit event exists for this pair.

- `audit.merge_audit_event_id`: the `event_id` from the matching audit-log
  entry.  Use `""` (empty string) when `NO_EVENT_FOUND`.

- `preserved_active_allergy_labels`: union of `allergies[].label` from both
  patients where `status == "active"`.  **Sort ascending.**

- `preserved_active_medication_ids`: union of `medications[].id` from both
  patients where `status == "active"`.  **Sort ascending.**

- `preserved_active_problem_codes`: union of `problems[].code` from both
  patients (excluding `M54.50` / resolved back-pain-type codes when they are
  `inactive`).  **Filter to `status == "active"`**.  **Sort ascending.**

- `excluded_patient_ids`: IDs of any patient records excluded from
  consideration.  Usually `[]`.

- `contact_action.action_required`: `true` only when `NEEDS_CLARIFICATION` or
  `DO_NOT_MERGE` requires provider outreach.  Otherwise `false`.

- `contact_action.action_code`: a short enum-like code describing the action
  (e.g. `"NONE_REQUIRED"`, `"VERIFY_ADDRESS"`).

- `contact_action.target_provider_id`: the `primary_provider_id` to contact, or
  `""` if no action.

### 2. Referral-batch audit

**Input resources**: batch detail (`.batch` + `.referrals`), ICD-10 codebook.

**Decision logic**:

- **Duplicate detection** (`duplicate_groups`): Two or more referrals are
  duplicates when they share the same `patient_dob`, `patient_first_name`,
  `patient_last_name`, and `icd10_code` but differ in `referring_physician`
  and/or `referring_fax`.  Group duplicate referral IDs (sorted ascending) into
  a list, and collect all groups into a list sorted by the first ID in each
  group.

- **Laterality mismatch** (`laterality_mismatch_referral_ids`): When the
  ICD-10 code's `laterality` field (from the codebook) conflicts with the
  laterality word in `diagnosis_description`.  For example:
  - Code `M76.61` = right achilles but `diagnosis_description` says
    "left ankle" → mismatch.
  - Code `M84.451A` = right femur but description says "left femur" →
    mismatch.
  - Codes with `laterality: ""` (none) never produce a laterality mismatch unless
    the description explicitly names a side.

- **Narrative mismatch** (`narrative_mismatch_referral_ids`): When the
  ICD-10 code's body site or description (from codebook) does not match the
  `diagnosis_description` narrative.  Key examples:
  - Code `M79.3` = "Panniculitis, unspecified" but description says
    "Olecranon bursitis right elbow" → the code body site (`soft tissue`) does
    not match the narrative body site (`elbow`).
  - Code `G89.29` = "Other chronic pain" but description says "Chronic
    bilateral knee pain" → the code is generic; a more specific code like
    `M25.561`/`M25.562` would fit better.

- **Out-of-range codes** (`out_of_range_code_referral_ids`): ICD-10 codes whose
  `in_musculoskeletal_tracking_range` is `false` in the codebook.  For
  orthopedic batches, codes in chapters S (injury), G (neurological), C
  (oncology), I (circulatory), J (respiratory), N (genitourinary) fall
  outside the musculoskeletal tracking range.

- **Corrected code suggestions** (`corrected_code_suggestions`): A mapping of
  referral IDs to the corrected ICD-10 code.  Only include referrals that
  actually need a correction.
  - For **laterality mismatches**: flip the code to the matching laterality
    (e.g. `M76.61` → `M76.62`, or `M84.451A` → `M84.452A`).
  - For **narrative mismatches**: find the code in the codebook whose
    `description` and `body_site` best match the `diagnosis_description` text
    (e.g. `M79.3` → `M70.21` for "Olecranon bursitis right elbow").
  - Use **exact casing and format** from the codebook (preserve decimal
    points, suffix letters like `A`).

- **Missing counts** (`missing_counts`):
  - `auth_not_submitted`: count referrals where `auth_status == "Not Submitted"`.
  - `imaging_missing`: count referrals where `imaging_received == "No"`.
  - `records_missing`: count referrals where `records_received == "No"`.

- **Insurance anomalies** (`insurance_anomalies`): For each insurance ID that
  appears on multiple referrals, classify those referrals as:
  - `related_duplicate_referral_ids`: referrals sharing the same insurance
    that are also duplicates of each other (same patient).
  - `unrelated_referral_ids`: referrals sharing the same insurance that are
    for *different* patients (different DOB/name).

- **Priority queues** (`priority_queues`): Triage referrals into three tiers:
  - `tier1_immediate`: pathological fractures, oncology coordination
    requests, stat-priority items, or any referral whose `notes` contain
    "PRIORITY".
  - `tier2_short_term`: laterality mismatches, narrative mismatches, urgent
    referrals with missing imaging/records.
  - `tier3_administrative`: scheduling issues ("patient called to
    reschedule"), routine referrals that need only auth/paperwork follow-up.

  Each tier list is sorted ascending.

### 3. Handoff-packet completeness review

**Input resources**: handoff-packet detail, patient record (with encounters,
immunizations, disclosures).

**Required handoff-packet sections** (all ten):
`demographics`, `active_problems`, `active_medications`, `allergies`,
`recent_encounters`, `immunizations`, `functional_status`, `cognitive_status`,
`transfer_plan`, `disclosure`.

**Decision logic**:

- `readiness`:
  - `READY` — all ten required sections are in `included_sections` AND
    `disclosure_status == "active"` AND no risk flags.
  - `READY_WITH_WARNINGS` — all sections present but minor non-blocking
    warnings exist.
  - `BLOCKED_INCOMPLETE_PACKET` — one or more required sections are missing.
  - `NEEDS_CLARIFICATION` — disclosure is missing or expired.
  - `BLOCKED_ORDER_SAFETY` — a severe clinical risk flag (e.g.
    contraindicated medication, undocumented severe allergy).

- `missing_packet_sections`: required sections not present in
  `included_sections`.  **Sort ascending.**

- `disclosure_status`: Check `disclosures` on the patient record.  If at
  least one disclosure has `status == "active"` → `"ACTIVE"`.  Otherwise
  `"MISSING"` or `"EXPIRED"` as appropriate.

- `active_problem_codes`, `active_medication_ids`, `active_allergy_labels`:
  From the patient chart.  **Only `status == "active"` items.**  Use `code`
  for problems, `id` for medications, `label` for allergies.  **Sort
  ascending.**

- `most_recent_immunization_id`: The immunization with the most recent `date`
  (latest date).  If tie, pick lower ID.

- `recent_encounter_ids`: Encounter IDs from the patient record, filtered to
  encounters within approximately the last 3–12 months (use the most recent
  4–5 encounters for a typical chart; older encounters like >12 months with
  resolved diagnoses may be excluded).  **Sort ascending by ID.**

- `risk_flags`: Derive from missing sections or clinical issues:
  - `MISSING_COGNITIVE_STATUS` — `cognitive_status` section missing.
  - `MISSING_DISCLOSURE` — no active disclosure.
  - `MISSING_FUNCTIONAL_STATUS` — `functional_status` missing.
  - `MISSING_IMMUNIZATIONS` — immunizations section missing.
  - Flag names use `SCREAMING_SNAKE_CASE`.  **Sort ascending.**

### 4. Service-request (order) validation

**Input resources**: service-request detail, patient encounters (linked via
`linked_encounter_ids`).

**SBAR sections**: `SITUATION`, `BACKGROUND`, `ASSESSMENT`, `RECOMMENDATION`.

**Decision logic**:

- Parse the `note_text` for SBAR sections.  The text follows the pattern:
  ```
  Situation: <text> Background: <text> Assessment: <text> Recommendation: <text>
  ```
  A section is **present** if the keyword label exists AND is followed by
  non-empty content (not just trailing whitespace or the next section label).

- `sbar_sections_present`: Boolean map for each of the four sections.

- `missing_sbar_sections`: SBAR section names that are absent or have empty
  content.  **Sort ascending.**

- `laterality_consistent`: Compare the laterality word in `service_display`
  or `note_text` assessment with the diagnoses in the linked encounter(s).
  - If the encounter diagnosis code has a `laterality` field matching the
    narrative laterality → `true`.
  - If they conflict → `false`.

- `evidence_encounter_ids`: Copy from `linked_encounter_ids`.  **Sort
  ascending.**

- `order_validation`: Extract directly from the service-request fields:
  - `priority`: the request's `priority` field (lowercase as-is, e.g.
    `"routine"`, `"stat"`).
  - `service_code`: the request's `service_code`.
  - `specialty`: the request's `specialty` (title-case as-is).
  - `status`: the request's `status` (e.g. `"draft"`).

- `blocker_codes`: Derive from SBAR gaps or mismatches:
  - `MISSING_SITUATION`, `MISSING_BACKGROUND`, `MISSING_ASSESSMENT`,
    `MISSING_RECOMMENDATION` — one per missing SBAR section.
  - `LATERALITY_MISMATCH` — if `laterality_consistent == false`.
  - Use `SCREAMING_SNAKE_CASE`.  **Sort ascending.**

- `ready_to_sign`: `true` only when ALL SBAR sections are present AND
  `laterality_consistent == true` AND `blocker_codes` is empty.

### 5. Referral chart-update decision

**Input resources**: referral row, patient chart (with encounters, problems,
allergies, medications), ICD-10 codebook.

**Decision logic**:

- `diagnosis_update`: The primary active problem from the patient chart that
  matches the referral reason.  Includes:
  - `code`: ICD-10 code from the patient's active problems.
  - `description`: The `label` from that problem.

- `allergy_update`: When referral `notes` asks to add/verify an allergy:
  - `allergen`: the allergen name.
  - `reaction`: the reaction description (derive from note context).
  - `severity`: `"Severe"`, `"Moderate"`, or `"Mild"` based on clinical
    context (iodinated contrast → Severe).
  - `status`: `"active"`.

  If no allergy update is needed, omit or return an empty-default object.

- `referral_target`:
  - `provider_id`: the provider to whom the referral is directed (find in
    providers list by matching specialty to referral context).
  - `specialty`: the target specialty (from the referral context, e.g.
    "Advanced Heart Failure" for a cardiology referral).

- `send_ready`:
  - `READY` — diagnosis and allergies are complete, no unresolved safety
    flags block sending.
  - `NEEDS_CLARIFICATION` — some field is uncertain or missing.
  - `BLOCKED` — a safety flag blocks sending (e.g. undocumented severe
    allergy that must be added first).

- `letter_merge_fields`: Standard referral-letter merge field names.  Typical
  set: `["Active_Problems", "Allergies", "DOB", "Patient_Name",
  "Referral_Reason"]`.  **Sort ascending.**

- `safety_flags`: Safety concerns that must be addressed:
  - `CONTRAST_ALLERGY_REQUIRED` — patient needs contrast but allergy not yet
    documented.
  - `MEDICATION_INTERACTION` — potential drug interaction.
  - Use `SCREAMING_SNAKE_CASE`.  **Sort ascending.**

- `recent_encounter_ids`: All encounter IDs from the patient chart (or a
  filtered recent subset, typically the most recent 2–4).  **Sort ascending.**

- `unresolved_quality_issues`: Any issues that remain unresolved after
  completing the chart update.  Usually `[]` if all items are addressed.

---

## Output field conventions

### Enum casing
Every enum value is **case-exact** from `answer_template.json`'s
`allowed_enums`.  Common values and their exact casing:

| Enum | Values |
|---|---|
| `disposition` | `MERGE_READY`, `NEEDS_CLARIFICATION`, `DO_NOT_MERGE` |
| `audit_status` | `READY_FOR_MERGE`, `BLOCKED_ADDRESS_CONFLICT`, `NO_EVENT_FOUND` |
| `readiness` | `READY`, `READY_WITH_WARNINGS`, `BLOCKED_INCOMPLETE_PACKET`, `NEEDS_CLARIFICATION`, `BLOCKED_ORDER_SAFETY` |
| `send_ready` | `READY`, `NEEDS_CLARIFICATION`, `BLOCKED` |
| `priority_tier` | `TIER_1_IMMEDIATE`, `TIER_2_SHORT_TERM`, `TIER_3_ADMINISTRATIVE` |
| `boolean` | `true` / `false` (JSON booleans, not strings) |

### Identifier and list ordering
- **All lists of stable identifiers must be sorted ascending** (lexicographic
  string order).  This includes lists named `*_ids`, `*_codes`, `*_labels`,
  `*_sections`, `*_flags`, `*_referral_ids`, `*_encounter_ids`,
  `*_packet_sections`.
- **Exception**: lists whose field name explicitly represents a priority queue
  or ranking are NOT re-sorted (e.g. `priority_queues.tier1_immediate` keeps
  its insertion/priority order after dedup).

### Clinical list filtering rules
- For **allergies**: filter `status == "active"`.  Use `label` for label
  lists, `id` for ID lists.
- For **medications**: filter `status == "active"`.  Use `id` for ID lists.
- For **problems**: filter `status == "active"`.  Use `code` for code lists.
  Exclude codes/descriptions that represent resolved/incidental conditions
  (e.g. `M54.50` "Low back pain" marked inactive or explicitly noted as
  resolved).
- When combining two patients' data (merge scenario): **union** the active
  items; dedup by the output field (label/id/code).  Do not double-count.

### Numeric precision
- Counts are **integers**.
- Decimal scores or ratios are rounded to **3 decimal places**.

### Date formats
- Dates: `YYYY-MM-DD`.
- Timestamps: ISO 8601 (e.g. `2026-03-22T09:44:00Z`).

### Empty/missing values
- Empty lists: `[]` (never `null`).
- Absent string IDs: `""` (empty string, never `null` or omitted).
- Empty objects: `{}` when the schema expects an object with no fillable keys.

---

## Source precedence

1. **ICD-10 codebook** is authoritative for code validity, laterality,
   body_site, and `in_musculoskeletal_tracking_range`.
2. **Patient chart** (problems, medications, allergies, encounters) takes
   precedence over referral descriptions for clinical data.
3. **Audit log** is authoritative for merge-status events.
4. **Referral row** `notes` and `diagnosis_description` are hints, not
   authoritative clinical data.
5. **Provider directory** is authoritative for provider details (name,
   specialty, fax).

---

## Common pitfalls

1. **Including inactive items** — Always filter clinical lists to
   `status: "active"`.  Inactive/resolved problems, discontinued medications,
   and inactive allergies must be excluded from preserved/active lists.

2. **Laterality confusion** — An ICD-10 code may have a `laterality` field
   that doesn't match the narrative in `diagnosis_description`.  Always
   cross-check both.  Use the codebook's `laterality` field as the source of
   truth for the code; the narrative is the source of truth for what the
   clinician meant.

3. **Sort order** — Every list of identifiers must be sorted ascending unless
   the field name says "queue" or "ranking".  Forgetting to sort is a
   frequent evaluator trap.

4. **Enum casing** — Values like `READY_FOR_MERGE` or `BLOCKED_INCOMPLETE_PACKET`
   must match exactly.  `Ready_For_Merge`, `ready_for_merge`, or
   `ready-for-merge` are all wrong.

5. **Duplicate detection false positives** — Two referrals with the same ICD-10
   code are NOT necessarily duplicates.  You need same patient (DOB + name)
   AND same condition.  Different patients with the same code are legitimate
   separate referrals.

6. **M79.3 trap** — `M79.3` is "Panniculitis, unspecified" (soft tissue
   inflammation).  When the diagnosis says "Olecranon bursitis right elbow,"
   `M79.3` is both a narrative mismatch AND needs correction to `M70.21`
   (the code for olecranon bursitis, right elbow).

7. **SBAR parsing** — The `note_text` may have a section keyword followed by
   an empty value (e.g. `"Recommendation:"` with nothing after it).  That
   section counts as **missing**, not present.

8. **Older encounters** — When selecting `recent_encounter_ids`, exclude
   encounters that are clearly stale (e.g. > 12 months old) or relate to
   resolved/incidental conditions unrelated to the active clinical picture.

9. **Empty audit log matches** — When no audit event exists for the candidate
   pair, `audit_status` is `NO_EVENT_FOUND` and `merge_audit_event_id` is
   `""`.  Do not guess or fabricate an event ID.

10. **Enterprise MRN** — When two patient records are otherwise tied on
    clinical completeness, the lower/smaller `enterprise_mrn` (as a string
    or numeric comparison) is the canonical target.

11. **Disclosure status** — An `ACTIVE` disclosure on the patient record is
    required for a handoff packet to be `READY`.  Check both the
    `included_sections` list AND the actual patient disclosures.

12. **Insurance anomaly classification** — Two referrals sharing the same
    insurance ID but belonging to different patients (different DOB) are
    `unrelated_referral_ids`.  Those belonging to the same patient (matching
    DOB + name) that are also duplicates are `related_duplicate_referral_ids`.
