# EHR Data Governance and Clinical Record Quality Control

## API Usage Workflow

The shared EHR quality API exposes all data through RESTful GET endpoints.
Always start by fetching the top-level index (`GET /api`) to discover available
endpoints and any per-task index changes. Use the environment base URL provided
in the task instructions.

### Core Endpoints

| Endpoint | Purpose |
|---|---|
| `/api/patients` | List all patients |
| `/api/patients/<id>` | Full patient chart including embedded clinical lists |
| `/api/patients/<id>/problems` | Active and inactive problem list |
| `/api/patients/<id>/medications` | Medication list with status |
| `/api/patients/<id>/allergies` | Allergy list with status and reaction |
| `/api/patients/<id>/encounters` | Encounter history |
| `/api/patients/<id>/immunizations` | Immunization records |
| `/api/patients/<id>/disclosures` | Disclosure records |
| `/api/patients/<id>/documents` | Clinical documents |
| `/api/duplicate-candidates` | List duplicate candidate reviews |
| `/api/duplicate-candidates/<id>` | Single duplicate candidate with linked patient IDs |
| `/api/referrals` | All referrals across batches |
| `/api/referral-batches` | List batches |
| `/api/referral-batches/<id>` | Single batch with embedded referral rows |
| `/api/handoff-packets` | List handoff packets |
| `/api/handoff-packets/<id>` | Single packet with sections and notes |
| `/api/service-requests` | List service requests |
| `/api/service-requests/<id>` | Single request with SBAR note and linked encounters |
| `/api/providers` | Provider directory with IDs, names, specialties, fax numbers |
| `/api/codebook/icd10` | ICD-10 codebook with laterality, body site, tracking range flags |
| `/api/audit-log` | System audit events for merge/review actions |

### API Usage Pattern

1. Identify the task type and target IDs from the task instructions.
2. Fetch the primary resource (duplicate candidate, batch, handoff packet,
   service request, or referral).
3. Follow the linked patient IDs and encounter IDs to gather chart evidence.
4. Cross-reference diagnosis codes against the ICD-10 codebook.
5. Cross-reference provider IDs against the provider directory.
6. Check the audit log for any relevant system events.
7. Build the answer JSON conforming to the output schema provided.

---

## Output Conventions

### Enum Values

All enum values are SCREAMING_SNAKE_CASE. Never use lowercase, Title Case, or
camelCase variants. Always use the exact casing from the allowed_enums block in
the answer template.

### Date Format

- Dates: `YYYY-MM-DD`
- Timestamps: ISO 8601 (e.g., `2026-03-22T09:44:00Z`)

### Numeric Precision

- Counts are integers (never floats).
- Decimal scores or ratios, if any, round to 3 decimal places.

### List Ordering Rule

> Lists of stable identifiers must be sorted **ascending** unless a field
> explicitly represents a priority queue (e.g., `tier1_immediate`,
> `tier2_short_term`, `tier3_administrative`).

This applies to: problem codes, medication IDs, allergy labels, encounter IDs,
referral IDs, patient IDs, immunization IDs, risk flags, blocker codes, missing
section names, and safety flags. The only exception is priority queues, which
preserve their tiered order as defined by clinical urgency rules.

### Duplicate Groups Within Lists

When a field contains nested lists (e.g., `duplicate_groups` is a list of
lists), sort the inner lists by their first element ascending, and sort each
inner list ascending as well.

---

## Clinical List Filtering Rules

### Active vs. Inactive Status

When a field name includes "active" (e.g., `active_problem_codes`,
`active_medication_ids`, `active_allergy_labels`), include **only** items
whose `status` field equals `"active"`. Exclude items with `status: "inactive"`
or any other non-active status.

### "Recent" Encounter Cutoff

When a field asks for `recent_encounter_ids`, apply a recency filter. Encounters
older than approximately 90 days from the reference date (the packet creation
date, referral date, or current task date) are generally excluded. Check the
encounter dates against the relevant reference point and include only those
within the recent window.

### Most Recent Item Selection

For fields like `most_recent_immunization_id`, compare the `date` field of
all items and select the one with the latest calendar date. If two dates are
identical, prefer the item with the lower (alphabetically sorted) ID.

---

## Task-Specific Business Rules

### 1. Duplicate Patient Reconciliation

**Workflow:**
1. Fetch the duplicate candidate by ID.
2. Extract the linked `patient_ids`.
3. Fetch each patient's full chart (problems, medications, allergies,
   disclosures, documents).
4. Check the audit log for merge events involving those patient IDs.
5. Determine the canonical target (the record to keep) and source (to merge in).

**Merge Decision Rules:**
- The **canonical target** should be the patient record with the more complete
  clinical profile (more active problems, medications, allergies, and
  disclosures). If clinical depth is equal, prefer the record with disclosures
  present.
- The **source patient** is merged into the canonical target and subsequently
  deactivated.
- Disposition is `MERGE_READY` when the audit log event has status
  `ready_for_merge` and both patients share the same address (no address
  conflict), same name, and same DOB.
- `reason_code` should describe the basis for the merge decision.

**Clinical List Preservation:**
- `preserved_active_problem_codes`: union of all distinct active problem codes
  from both patients, sorted ascending.
- `preserved_active_medication_ids`: union of all distinct active medication
  IDs from both patients, sorted ascending.
- `preserved_active_allergy_labels`: union of all distinct active allergy
  labels from both patients, sorted ascending.
- No deduplication beyond distinctness — if two patients have the same
  medication ID, include it once.

**Contact Action:**
- When the canonical target has an active disclosure, determine whether the
  primary provider needs to be notified about the merge. Check if both patients
  share the same primary provider and whether the disclosure recipient matches
  a known provider.

**Audit Event Mapping:**
- Match the `merge_audit_event_id` from the audit log entry whose `patient_ids`
  contains both candidate patient IDs.
- Map the audit log's snake_case status to the SCREAMING_SNAKE_CASE enum:
  `ready_for_merge` → `READY_FOR_MERGE`.

### 2. Referral Batch Quality Audit

**Workflow:**
1. Fetch the referral batch by ID to get all referral rows.
2. Fetch the ICD-10 codebook (`/api/codebook/icd10`).
3. For each referral, validate the ICD-10 code against the codebook.
4. Identify duplicate referrals, laterality mismatches, narrative mismatches,
   out-of-range codes, missing items, and insurance anomalies.
5. Assign each referral with issues to a priority tier.
6. Suggest corrected ICD-10 codes where appropriate.

**Code Validation Rules:**

*Laterality Mismatch:* When the codebook entry has a `laterality` field
(right, left, bilateral) that contradicts the diagnosis description text.
Compare the laterality in the description (e.g., "left ankle") against the
codebook laterality. If they conflict, flag as a laterality mismatch.
The corrected code should preserve the same condition but with the correct
laterality suffix (e.g., M76.61 right → M76.62 left).

*Narrative Mismatch:* When the ICD-10 code description in the codebook
describes a completely different condition than the referral's
`diagnosis_description`. Example: M79.3 = "Panniculitis, unspecified" vs.
diagnosis "Olecranon bursitis right elbow" → narrative mismatch. The
corrected code is the best-matching code from the codebook.

*Out-of-Range Code:* When a referral's ICD-10 code has
`in_musculoskeletal_tracking_range: false` for a specialty referral
(e.g., a G-chapter pain code for an orthopedic referral). The code may
still be clinically valid but is flagged for review.

*Corrected Code Suggestions:* When suggesting corrected codes, use the
exact code string from the codebook, preserving the original decimal
placement and character case. Only include referrals that actually need
a correction; do not include referrals whose codes are already correct.

**Duplicate Detection:**
- Same patient (first name + last name + DOB), same diagnosis, same insurance
  → duplicate group. Note the notes field for confirmation text like
  "Second referral for same patient and condition."

**Insurance Anomalies:**
- When the same `insurance_id` appears across referrals for patients with
  different names and different DOBs, flag as an insurance anomaly.
- `related_duplicate_referral_ids`: referrals that are duplicates of each
  other under this insurance.
- `unrelated_referral_ids`: referrals for different patients sharing the
  same insurance ID.

**Missing Counts:**
- `auth_not_submitted`: count of referrals where `auth_required` is "Yes"
  AND `auth_status` is "Not Submitted". Referrals with `auth_required: "No"`
  and `auth_status: "N/A"` are excluded.
- `imaging_missing`: count of referrals where `imaging_received` is "No".
- `records_missing`: count of referrals where `records_received` is "No".

**Priority Queue Assignment:**

| Tier | Criteria | Examples |
|---|---|---|
| `TIER_1_IMMEDIATE` | Clinical safety risk: wrong diagnosis code, wrong laterality for serious condition | Narrative mismatch, pathological fracture laterality error |
| `TIER_2_SHORT_TERM` | Missing items that delay or compromise care quality | Missing auth, missing imaging, missing records |
| `TIER_3_ADMINISTRATIVE` | Administrative cleanup, non-urgent code review | Duplicate referrals, out-of-range codes needing review |

A single referral may appear in only one tier. If a referral has multiple
issues, classify it at the highest applicable tier.

### 3. Handoff Packet Completeness Review

**Workflow:**
1. Fetch the handoff packet by ID to get included sections and notes.
2. Fetch the linked patient's chart (problems, medications, allergies,
   immunizations, encounters, disclosures).
3. Compare included sections against the expected section set for the
   transfer type.
4. Review any notes about omitted or incomplete sections.
5. Assess clinical risk flags from the patient's chart.

**Expected Handoff Sections:**
A complete handoff packet for skilled nursing or post-acute transfer
should include:
- `demographics`
- `active_problems`
- `active_medications`
- `allergies`
- `recent_encounters`
- `immunizations`
- `functional_status`
- `cognitive_status`
- `transfer_plan`
- `disclosure`

**Readiness Determination:**
- `READY`: All expected sections present, no clinical gaps.
- `READY_WITH_WARNINGS`: Minor issues (e.g., optional section missing but
  core clinical data complete).
- `BLOCKED_INCOMPLETE_PACKET`: A required section is completely missing
  (e.g., `cognitive_status` omitted for a skilled nursing transfer).
- `NEEDS_CLARIFICATION`: Ambiguous or contradictory information that must
  be resolved before the transfer can proceed.

**Missing Sections:**
- When the packet notes or section list indicate a section is omitted,
  list it in `missing_packet_sections`. Use the exact section key name
  as it appears in the `included_sections` list (lowercase with
  underscores).

**Clinical Data Extraction from Chart:**
- `active_problem_codes`: only problems with `status: "active"`, sorted.
- `active_medication_ids`: only medications with `status: "active"`, sorted.
- `active_allergy_labels`: only allergies (no status filter needed if all
  are active, but check `status`), sorted.
- `most_recent_immunization_id`: immunization with the latest `date`.
- `recent_encounter_ids`: encounters within the recent window (~90 days
  from the packet creation date), sorted.
- `disclosure_status`: use the status value from the patient's disclosure
  record that matches the receiving facility or most recent care transition.

**Risk Flags:**
Derive from the patient's clinical profile. Common flags include:
- Anticoagulation use (patient on warfarin, apixaban, etc.)
- Fall risk (mobility limitations, age, functional status notes)
- Severe allergy (reaction severity "Severe" or anaphylaxis history)
- Polypharmacy (multiple active medications)
- Recent hospitalization (encounter diagnoses matching acute conditions)

### 4. Service Request / Order Validation

**Workflow:**
1. Fetch the service request by ID.
2. Fetch the linked patient chart and encounters.
3. Parse the SBAR note text into its four components.
4. Validate laterality consistency between the note, encounter diagnoses,
   and patient problem codes.
5. Validate the order fields (priority, service code, specialty, status).

**SBAR Parsing:**
The `note_text` field contains a structured SBAR note. Parse it by
identifying the four section prefixes:

| Section | Prefix | Required |
|---|---|---|
| `SITUATION` | `Situation:` | Yes |
| `BACKGROUND` | `Background:` | Yes |
| `ASSESSMENT` | `Assessment:` | Yes |
| `RECOMMENDATION` | `Recommendation:` | Yes |

A section is **present** (`true`) if the prefix is followed by non-empty
content. A section is **missing** (`false`) if the prefix is present but
the content after it is empty (only whitespace or end of string), or if
the prefix itself is absent.

**Ready to Sign:**
- `ready_to_sign: true` only when ALL four SBAR sections are present
  with non-empty content.
- Any missing section → `ready_to_sign: false`.
- Missing RECOMMENDATION is a blocker because it means no clinical
  decision or next step has been documented.

**Blocker Codes:**
- Use `MISSING_` prefix format for missing required content:
  `MISSING_RECOMMENDATION`, `MISSING_ASSESSMENT`, etc.
- Each missing SBAR section gets its own blocker code.

**Laterality Consistency:**
- Extract laterality keywords (left, right, bilateral) from the note text.
- Compare with the ICD-10 code's laterality from the codebook.
- Compare with encounter diagnosis codes and problem list codes.
- `laterality_consistent: true` only if ALL sources agree on the same side.

**Evidence Encounters:**
- Use the `linked_encounter_ids` from the service request as the
  `evidence_encounter_ids`. Sorted ascending.

**Order Validation Fields:**
- Mirror the request's own values for `priority`, `service_code`,
  `specialty`, and `status` unless the validation reveals a discrepancy
  requiring correction.

### 5. Referral Chart-Update Quality Decision

**Workflow:**
1. Fetch the referral by listing all referrals and finding the target ID.
2. Fetch the linked patient chart.
3. Compare referral notes against the patient's chart for undocumented
   clinical items.
4. Identify the appropriate referral target (specialist provider).
5. Determine whether the referral is ready to send or needs clarification.

**Referral Target:**
- Match the referral's clinical domain (e.g., cardiology, orthopedics) to
  a provider whose specialty aligns. Use the provider directory (`/api/providers`)
  and select the provider with the most specific matching specialty.
- `specialty` should reflect the provider's actual specialty as listed in
  the provider directory.

**Chart-vs-Referral Gap Detection:**
- When the referral `notes` mention a clinical item (e.g., an allergy,
  medication, or diagnosis) that is **not present** in the patient's chart,
  this is a quality gap.
- The `allergy_update` field should document the missing allergy that the
  referral references, with appropriate allergen name, reaction, severity,
  and status `"active"`.
- The `diagnosis_update` field should confirm the primary diagnosis code
  and its description as validated against both the chart and the codebook.

**Send Readiness:**
- `READY`: Chart and referral are consistent, no gaps.
- `NEEDS_CLARIFICATION`: A clinical item referenced in the referral
  (allergy, medication, diagnosis) is missing from or conflicts with the
  patient chart.
- `BLOCKED`: Critical safety information is absent or contradictory.

**Safety Flags:**
- Flag any clinical item mentioned in the referral that is not documented
  in the patient's chart.
- Use descriptive, uppercase flag names.

**Unresolved Quality Issues:**
- List quality gaps that must be resolved before the referral can proceed.
  Each entry should reference the specific item that needs attention.

---

## Source Precedence

When the same clinical fact appears in multiple sources, use this
precedence order:

1. **Patient chart** (authoritative for demographics, problem list,
   medications, allergies, encounters).
2. **Audit log** (authoritative for system-level events and merge status).
3. **ICD-10 codebook** (authoritative for code descriptions, laterality,
   and tracking range).
4. **Provider directory** (authoritative for provider names, specialties,
   and contact information).
5. **Referral/disclosure notes** (supplementary — must be verified against
   the chart before being treated as fact).

---

## Common Pitfalls

1. **Status filtering:** Always check the `status` field on problems,
   medications, and allergies. Including inactive items in an "active" list
   is a common error.

2. **Sort order:** Nearly every list field requires ascending sort. Forgetting
   to sort, or sorting by the wrong key (e.g., sorting by label instead of
   code), produces incorrect output.

3. **Enum casing:** Using `Ready` or `ready` instead of `READY`, or
   `blocked_incomplete_packet` instead of `BLOCKED_INCOMPLETE_PACKET`. Match
   the allowed_enums exactly.

4. **Laterality cross-check:** Always verify laterality across all three
   sources: note text, ICD-10 codebook laterality, and diagnosis description.
   Don't rely on just one.

5. **ICD-10 code correction format:** When suggesting corrected codes, copy
   the code string exactly from the codebook — including the decimal point
   placement and any letter suffixes. Do not invent codes that aren't in
   the codebook.

6. **"Recent" encounter cutoff:** Including encounters older than
   approximately 90 days from the reference date dilutes the recency
   signal. Apply a recency window.

7. **SBAR section detection:** A section prefix followed by only whitespace
   or end-of-string counts as MISSING, not as present-with-minimal-content.
   The colon after the prefix with nothing substantive after it is the key
   indicator.

8. **Duplicate referral detection:** Two referrals for the same patient
   (matched by name + DOB) with the same condition and insurance are
   duplicates, even if they come from different referring physicians.

9. **Insurance anomaly classification:** Same insurance ID on patients
   with different last names and different DOBs is an anomaly. But same
   insurance ID for the same patient (matching name + DOB) across duplicate
   referrals is a `related_duplicate`, not an unrelated anomaly.

10. **Missing items counting:** Only count auth as missing when
    `auth_required` is "Yes" AND `auth_status` is "Not Submitted".
    Referrals with `auth_required: "No"` and `auth_status: "N/A"` are
    NOT missing auth.

11. **Blocker code naming:** Use the `MISSING_` prefix pattern for blocker
    codes when an SBAR section is absent: `MISSING_RECOMMENDATION`,
    `MISSING_ASSESSMENT`, etc.

12. **Disclosure cross-referencing:** When evaluating a handoff packet,
    verify that the patient's active disclosure matches the receiving
    facility and transfer purpose. An active disclosure to the wrong
    facility or for the wrong purpose is a quality gap.
