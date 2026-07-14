# EHR Data Governance & Clinical Record Quality Control

## Environment

All API calls use the base URL provided in `environment_access.md` (the
`GDPEVO_ENV_BASE_URL` variable). Ignore any `localhost`, `127.0.0.1`,
`<TASK_ENV_BASE_URL>`, `API_BASE_URL`, or `BASE_URL` references in task
prompts — always substitute the remote URL from environment_access.md.

Start every task by reading `environment_access.md` to obtain the live base
URL, then use the public endpoints listed there.

---

## API Usage Workflow

Every task follows this general flow:

1. **Read** `environment_access.md` for the base URL.
2. **Read** `task_scope.json` for the target entity IDs, the response contract,
   and the answer template path.
3. **Read** `answer_template.json` for the exact output schema, allowed enums,
   list ordering rules, date format, and numeric precision.
4. **Fetch** the primary entity (duplicate-candidate, referral-batch,
   handoff-packet, service-request, or referral).
5. **Fetch** dependent entities (patients, encounters, disclosures, providers,
   audit-log, codebook, documents) as needed by the task type.
6. **Cross-reference** all sources, applying the business rules below.
7. **Produce** a single JSON object conforming exactly to the answer template
   schema — no explanatory prose outside the JSON.

### Key Endpoint Patterns

| Entity | List endpoint | Detail endpoint |
|---|---|---|
| Patients | `GET /api/patients` | `GET /api/patients/<patient_id>` |
| Duplicate candidates | `GET /api/duplicate-candidates` | `GET /api/duplicate-candidates/<candidate_id>` |
| Referrals | `GET /api/referrals` | `GET /api/referrals/<referral_id>` |
| Referral batches | `GET /api/referral-batches` | `GET /api/referral-batches/<batch_id>` |
| Handoff packets | `GET /api/handoff-packets` | `GET /api/handoff-packets/<packet_id>` |
| Service requests | `GET /api/service-requests` | `GET /api/service-requests/<request_id>` |
| Providers | `GET /api/providers` | — |
| ICD-10 codebook | `GET /api/codebook/icd10` | — |
| Documents | `GET /api/documents` | — |
| Audit log | `GET /api/audit-log` | — |

Patient sub-resources: append `/<patient_id>/problems`, `/medications`,
`/allergies`, `/encounters`, `/immunizations`, `/disclosures`, `/documents`.

---

## Output Field Conventions

### Identifier / List Ordering

**Default rule**: Sort all lists of stable identifiers (IDs, codes, labels)
in **ascending lexicographic order** (standard string sort). This applies to
fields like `patient_ids`, `referral_ids`, `encounter_ids`, `problem_codes`,
`medication_ids`, `allergy_labels`, `risk_flags`, `missing_packet_sections`,
`blocker_codes`, `safety_flags`, `letter_merge_fields`, and
`unresolved_quality_issues`.

**Exception**: Fields whose names explicitly describe a priority queue or
ranking (e.g. `priority_queues`, `tier1_immediate`, `tier2_short_term`,
`tier3_administrative`) are NOT sorted — preserve their semantic priority
ordering as described by the business rules for each tier.

**Duplicate groups** (lists of lists): Sort each inner list ascending, and
sort the outer list of groups by the first element of each inner list.

**Insurance anomaly objects**: Sort the outer array by `insurance_id`
ascending. Sort inner `related_duplicate_referral_ids` and
`unrelated_referral_ids` ascending.

### Enum Values

Use exact UPPER_SNAKE_CASE as defined in the answer template's
`allowed_enums`. Never invent enum values; pick only from the template.

Common enums across tasks:
- **disposition**: `MERGE_READY`, `NEEDS_CLARIFICATION`, `DO_NOT_MERGE`
- **readiness**: `READY`, `READY_WITH_WARNINGS`, `BLOCKED_INCOMPLETE_PACKET`, `NEEDS_CLARIFICATION`, `BLOCKED_ORDER_SAFETY`
- **send_ready**: `READY`, `NEEDS_CLARIFICATION`, `BLOCKED`
- **audit_status**: `READY_FOR_MERGE`, `BLOCKED_ADDRESS_CONFLICT`, `NO_EVENT_FOUND`
- **priority_tier**: `TIER_1_IMMEDIATE`, `TIER_2_SHORT_TERM`, `TIER_3_ADMINISTRATIVE`

### Dates and Numbers

- **Dates**: `YYYY-MM-DD` format.
- **Timestamps**: ISO 8601 (e.g. `2026-03-22T09:44:00Z`).
- **Counts**: Integers.
- **Decimal scores/ratios**: Round to 3 decimal places.

### Booleans

Use JSON `true` / `false` (not strings).

---

## Task-Specific Business Rules

### 1. Duplicate Patient Reconciliation

**Purpose**: Determine whether two patient records flagged as potential
duplicates should be merged, and if so, which clinical data to preserve.

**Data sources**: The duplicate candidate object, both patient charts
(problems, medications, allergies, disclosures, encounters, immunizations),
and the audit log.

**Merge decision logic**:

1. **Identify canonical (target) vs. source patient**. The canonical target
   is the more complete record — the one with more active clinical data
   (problems + medications + allergies), an active disclosure, and/or the
   lower enterprise MRN. The source is the record whose active data will be
   merged into the target before retirement.

2. **Check the audit log** for an event whose `patient_ids` array contains
   both patient IDs from the candidate. Match by `event_type:
   "duplicate_review"`. The audit `status` maps to `audit_status`:
   - `"ready_for_merge"` → `READY_FOR_MERGE`
   - `"blocked_address_conflict"` → `BLOCKED_ADDRESS_CONFLICT`
   - No matching event → `NO_EVENT_FOUND`

3. **Assess risk flags** from the candidate's `risk_flags` list:
   - `"conflicting_current_address"`: addresses differ between patients.
   - `"expired_disclosure_on_source"`: source patient has no active disclosure
     or has an expired disclosure.
   - `"different DOB"`: dates of birth don't match — do not merge.

4. **Determine disposition**:
   - `MERGE_READY`: no risk flags (or only minor ones), audit event found
     with ready_for_merge status, addresses match.
   - `NEEDS_CLARIFICATION`: risk flags present (e.g. address conflict,
     expired disclosure) but DOBs match; requires human review.
   - `DO_NOT_MERGE`: DOB mismatch or other hard blockers.

5. **Preserved clinical lists**: Collect any **active** (status `"active"`)
   problems, medications, and allergies from the **source** patient that do
   NOT already appear in the target patient's active lists. For problems,
   match by `code`; for medications, match by `id`; for allergies, match by
   `label`. Return the codes/IDs/labels (not the full objects) sorted
   ascending.

6. **Excluded patient IDs**: The source patient ID (the one being retired
   after merge) goes in this list. If merge is `DO_NOT_MERGE`, exclude both.

7. **Contact action**: If the audit status is `BLOCKED_ADDRESS_CONFLICT` or
   the candidate has `conflicting_current_address`, set `action_required:
   true` and `action_code` to a descriptive code. The `target_provider_id` is
   the primary provider of the target/canonical patient.

### 2. Referral Batch Quality Audit

**Purpose**: Audit a batch of referrals for ICD-10 coding errors,
duplicates, missing documentation, insurance anomalies, and priority
classification.

**Data sources**: The referral batch, all its referral rows, the ICD-10
codebook, and the providers list.

**ICD-10 codebook fields**: `code`, `description`, `body_site`, `laterality`
(`"left"`, `"right"`, or `""`), `in_musculoskeletal_tracking_range` (boolean),
`chapter_prefix`.

#### ICD-10 Correction Rules

Compare each referral's `icd10_code` and `diagnosis_description` against the
codebook:

**Laterality mismatch** (`laterality_mismatch_referral_ids`): The referral's
ICD-10 code has a specific laterality in the codebook, but the
`diagnosis_description` text describes the opposite side. For example, code
`M76.61` = "Achilles tendinitis, **right** leg" but description says "left
ankle". The correct code is the same body-site code with the matching
laterality (`M76.62`). Add the referral ID to this list AND add the corrected
code to `corrected_code_suggestions`.

**Narrative mismatch** (`narrative_mismatch_referral_ids`): The
`diagnosis_description` describes a different body site or condition than
what the ICD-10 code represents (e.g., "Olecranon bursitis right elbow"
mapped to `M79.3` "Panniculitis, unspecified"). Add to this list and provide
the correct code in `corrected_code_suggestions`. Match the diagnosis
description text to the closest codebook entry by description and body site
keywords.

**Out of range codes** (`out_of_range_code_referral_ids`): The ICD-10 code
exists in the codebook but has `in_musculoskeletal_tracking_range: false`.
These codes (S-chapter fracture codes, G-chapter pain codes, C-chapter
oncology codes, I-chapter cardiac codes, J-chapter respiratory codes,
N-chapter renal codes) are not in the orthopedic tracking range. Add to this
list. If the description clearly indicates a musculoskeletal condition, also
add a corrected code suggestion.

**Corrected code format**: Use the exact `code` string from the codebook,
preserving the decimal/case style (e.g., `M17.11`, `S82.001A`).

#### Duplicate Detection

Two referrals are duplicates when they share the same patient (first name +
last name + DOB) and the same ICD-10 code, but come from different referring
physicians or practices. Group duplicate referral IDs into inner lists. Sort
each inner list ascending, and sort outer groups by first element.

#### Insurance Anomalies

An insurance anomaly occurs when the same `insurance_id` appears on multiple
referrals for different patients. For each anomalous insurance ID:
- `related_duplicate_referral_ids`: referrals that are duplicates of each
  other (same patient + same code sharing this insurance).
- `unrelated_referral_ids`: referrals for different patients sharing this
  insurance ID.

#### Missing Counts

Count referrals where:
- `auth_not_submitted`: `auth_status` is `"Not Submitted"`.
- `imaging_missing`: `imaging_received` is `"No"`.
- `records_missing`: `records_received` is `"No"`.

#### Priority Queues

Classify referrals into three tiers (use referral IDs, sorted ascending
within each tier):

- **TIER_1_IMMEDIATE**: Oncology-related (codes with `C` chapter prefix,
  notes mentioning "oncology" or "malignancy"), pathological fractures with
  coordination needs, "PRIORITY" in notes.
- **TIER_2_SHORT_TERM**: Missing authorizations (auth `"Not Submitted"`),
  missing imaging or records, laterality or narrative mismatches, out-of-range
  codes.
- **TIER_3_ADMINISTRATIVE**: Duplicate referrals, scheduling delays (notes
  mentioning reschedule or future-month preference), routine referrals with
  no issues.

A referral appears in only ONE tier (the highest applicable).

### 3. Handoff Packet Completeness Review

**Purpose**: Validate that a care-transition handoff packet is complete,
accurate, and ready to send to the receiving facility.

**Data sources**: The handoff packet, the patient chart (problems,
medications, allergies, encounters, immunizations, disclosures), and the
providers list.

**Packet section validation**:

A complete handoff packet should include these sections:
`demographics`, `active_problems`, `active_medications`, `allergies`,
`recent_encounters`, `immunizations`, `functional_status`, `cognitive_status`,
`transfer_plan`, `disclosure`.

Compare the packet's `included_sections` against the expected set. Any
expected section not present is a `missing_packet_section`.

**Clinical list extraction from patient chart**:

- **Active problem codes**: All problems with status `"active"` — return the
  `code` field, sorted ascending.
- **Active medication IDs**: All medications with status `"active"` — return
  the `id` field, sorted ascending.
- **Active allergy labels**: All allergies with status `"active"` — return
  the `label` field, sorted ascending.
- **Recent encounter IDs**: Encounters sorted by `date` descending, take
  the most recent relevant ones (typically encounters with active diagnoses).
  Return `id` fields sorted ascending.
- **Most recent immunization ID**: The immunization with the latest `date`.
  If no immunizations exist, use an empty string `""`.

**Disclosure status**: Check the patient's disclosures for an active
disclosure matching the packet's receiving facility or purpose. If found and
`status` is `"active"`, use `"active"`. If missing or expired, use
appropriate status like `"missing"` or `"expired"`.

**Risk flags**: Identify quality concerns:
- Missing cognitive status in packet (check if `cognitive_status` is empty
  string).
- Missing functional status details.
- Any inactive problem/medication/allergy that shouldn't be in the packet.
- Missing disclosure for the receiving facility.
- Incorrect medication doses or labels vs. the patient chart.

**Readiness determination**:
- `READY`: All sections present, active disclosure exists, no risk flags.
- `READY_WITH_WARNINGS`: Minor issues (e.g., missing cognitive status but
  all clinical data present and disclosure is active).
- `BLOCKED_INCOMPLETE_PACKET`: Critical sections missing (e.g., no
  medications, no problems, no allergies section).
- `NEEDS_CLARIFICATION`: Conflicting data between packet and chart.
- `BLOCKED_ORDER_SAFETY`: Safety-critical issues (e.g., wrong medication,
  missing allergy that has severe reaction).

### 4. Service Request (Order) Validation

**Purpose**: Validate a draft service request for clinical correctness,
SBAR completeness, and readiness to sign.

**Data sources**: The service request, the patient chart (problems,
encounters), and the ICD-10 codebook.

**SBAR parsing**:

Parse the `note_text` field for the four SBAR components. The text uses
labeled sections:

```
Situation: <text> Background: <text> Assessment: <text> Recommendation: <text>
```

Each section (`SITUATION`, `BACKGROUND`, `ASSESSMENT`, `RECOMMENDATION`) is
`true` in `sbar_sections_present` if its label and non-empty content appear
in the note text. A section with an empty value after the colon (or missing
entirely) is `false`. Missing sections go in `missing_sbar_sections` sorted
ascending.

**Laterality consistency**:

Compare the laterality described in the service request (from `note_text`,
`specialty`, linked encounter diagnoses) against any laterality in the
patient's problem codes and encounter diagnoses. Check the codebook for
laterality of each ICD-10 code. If all sources agree on side (left/right),
`laterality_consistent` is `true`. If the request note says left but a
diagnosis code maps to right, it's `false`.

**Evidence encounter IDs**:

The encounter IDs from `linked_encounter_ids` that support the service
request. Match encounter diagnoses to the service request's clinical intent.
Return sorted ascending.

**Order validation object**:

- `priority`: The priority from the service request (`routine`, `urgent`,
  `stat`). Validate that it's appropriate for the clinical scenario.
- `service_code`: The `service_code` from the request.
- `specialty`: The `specialty` from the request. Validate it matches the
  clinical need.
- `status`: The `status` from the request (typically `"draft"`).

**Blocker codes**: Issues that prevent signing, sorted ascending:
- `"SBAR_INCOMPLETE"`: Missing SBAR sections.
- `"LATERALITY_MISMATCH"`: Conflicting laterality between request and chart.
- `"CODE_NOT_IN_TRACKING_RANGE"`: Service code or diagnosis code outside the
  relevant tracking range.
- `"MISSING_EVIDENCE"`: No linked encounters support the request.
- `"PRIORITY_MISMATCH"`: Priority doesn't match clinical urgency.

**Ready to sign**: `true` only when `blocker_codes` is empty.

### 5. Referral Chart Update & Send-Readiness

**Purpose**: Review a referral against the patient's chart, identify
required chart updates, determine the correct referral target, and assess
whether the referral is ready to send.

**Data sources**: The referral, the patient chart (problems, medications,
allergies, encounters, disclosures), the ICD-10 codebook, and the providers
list.

**Diagnosis update**:

Match the referral's `diagnosis_description` and `icd10_code` against the
codebook. If the referral's ICD-10 code doesn't match the diagnosis
description (laterality mismatch or narrative mismatch), provide the
corrected `code` and `description` from the codebook. The description should
be the codebook's `description` field, not the referral's free-text.

**Allergy update**:

Check the referral `notes` field for allergy-related instructions (e.g.,
"Add severe iodinated contrast allergy before sending"). Check the patient's
current allergy list. If the referral notes indicate an allergy that is
missing from the patient chart, populate `allergy_update` with `allergen`,
`reaction`, `severity`, and `status` (`"active"`).

**Recent encounter IDs**:

Encounters from the patient chart sorted by date descending. Take the most
recent encounters that are clinically relevant to the referral reason.
Return IDs sorted ascending.

**Referral target**:

Select the appropriate provider and specialty for this referral:
- Match the referral's clinical domain to the correct provider specialty.
- For orthopedics: Orthopedic Surgery providers.
- For cardiology/heart failure: Advanced Heart Failure providers.
- For oncology: Oncology providers.
- Use `provider_id` and `specialty` from the providers list.

**Letter merge fields**: Data elements needed for the referral cover letter
(sorted ascending). Typically includes: patient name fields, DOB, MRN,
referring physician, diagnosis, and other patient identifiers.

**Safety flags**: Clinical safety concerns discovered during review (sorted
ascending):
- Allergy missing from chart that is noted in referral.
- Incorrect laterality in diagnosis coding.
- Drug interactions between current medications and planned procedure.
- Missing critical lab/imaging results.
- Patient has no active disclosure for specialist sharing.

**Unresolved quality issues**: Any quality issues that need attention before
sending (sorted ascending). This includes code corrections, missing chart
data, and disclosure gaps.

**Send readiness**:
- `READY`: No quality issues, all chart data complete, correct target
  provider, disclosure active.
- `NEEDS_CLARIFICATION`: Minor issues that need confirmation but don't block
  sending (e.g., non-critical missing data).
- `BLOCKED`: Critical issues (missing required chart data, no disclosure,
  safety flags present, incorrect diagnosis coding).

---

## Clinical List Filtering Rules (Cross-Cutting)

When extracting clinical lists from patient records:

1. **Active only**: Filter all problems, medications, and allergies to
   `status: "active"`. Ignore items with any other status (e.g. `"inactive"`,
   `"resolved"`, `"completed"`).

2. **Source precedence for merges**: When merging duplicate patients, the
   canonical/target record's active data takes precedence. Only add items
   from the source that are NOT already present in the target (match problems
   by `code`, medications by `id`, allergies by `label`).

3. **Encounter recency**: When selecting recent encounters, sort by `date`
   descending. Prefer encounters whose diagnoses match the clinical context
   (e.g., for a cardiology referral, prefer encounters with cardiac
   diagnoses). Return only the encounter `id` fields.

4. **Immunization recency**: Select the single immunization with the latest
   `date` value. Return its `id`.

5. **Disclosure validity**: A disclosure is valid for a given purpose when
   its `status` is `"active"` and its `purpose` or `recipient` matches the
   clinical context (e.g., "Care Coordination", "Care Transition", a
   specific receiving facility name).

---

## Source Precedence

When data conflicts across sources, use this precedence (highest to lowest):

1. **ICD-10 codebook** — authoritative for code descriptions, laterality,
   body site, and tracking range. Always prefer codebook data over free-text
   descriptions in referrals.
2. **Patient chart** — authoritative for active clinical data (problems,
   medications, allergies). The chart overrides any packet or referral that
   references the same patient.
3. **Audit log** — authoritative for prior review decisions and merge
   readiness.
4. **Referral / packet / service request** — the entity being reviewed.
   Trust its metadata (IDs, dates, status) but verify clinical coding and
   completeness against sources 1–3.
5. **Documents** — supplementary reference material (form templates, quality
   queue extracts). Use for context but not as primary clinical data.

---

## Common Pitfalls

1. **Not reading answer_template.json first**: Every task has a specific
   output schema. Always read the template before building the response to
   avoid missing required fields or using wrong enum values.

2. **Sorting priority queues**: Priority queue tiers are NOT sorted
   alphabetically — they preserve clinical priority order. All other ID
   lists ARE sorted ascending.

3. **Laterality confusion**: When checking laterality, the codebook is the
   source of truth. A referral's `diagnosis_description` text may say "left"
   but the codebook entry for the given ICD-10 code determines actual
   laterality. A mismatch means the referral has the WRONG code, not that the
   codebook is wrong.

4. **Code corrections scope**: Only include a referral in
   `corrected_code_suggestions` when it actually needs a correction. If the
   code matches the description, do NOT add a spurious correction entry.

5. **Duplicate detection scope**: Two referrals are duplicates only when
   they share patient identity (name + DOB) AND the same ICD-10 code. Same
   patient with different conditions is NOT a duplicate.

6. **Insurance anomalies**: The same insurance ID appearing on referrals for
   the same patient is normal (the patient has that insurance). An anomaly
   is when DIFFERENT patients share the same insurance ID.

7. **Missing vs. empty**: An empty string `""` in a packet field (e.g.,
   `cognitive_status: ""`) means the section is present but content is
   missing — it counts as a quality gap, not a missing section. A section
   entirely absent from `included_sections` is a missing section.

8. **SBAR parsing**: Parse the note_text by looking for the section labels
   (`Situation:`, `Background:`, `Assessment:`, `Recommendation:`) followed
   by content before the next label or end of string. A section is present
   only if its label appears AND has non-empty content after the colon.

9. **Ready-to-sign requires zero blockers**: `ready_to_sign` is `true` only
   when `blocker_codes` is an empty list. Even one blocker means `false`.

10. **Disclosure checks for referrals**: Before marking a referral as
    `READY` to send, verify the patient has an active disclosure that permits
    sharing with the target specialist. Missing disclosure → `BLOCKED`.

11. **Pathological fracture with oncology notes**: A referral with
    `icd10_code` `M84.451A` (right femur) but description saying "left
    femur" is a laterality mismatch. The code and description must match;
    cross-check against codebook laterality.

12. **Return type discipline**: Return ONLY valid JSON. No markdown, no
    explanations, no code fences around the JSON output. The answer must
    parse as JSON directly.
