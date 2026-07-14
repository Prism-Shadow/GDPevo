# EHR Quality Governance & Clinical Record Quality-Control Skill

## Overview

This skill covers five EHR data-governance and quality-control task types against a
FHIR-inspired REST API:

1. **Duplicate patient reconciliation** — review duplicate-candidate pairs,
   determine mergeability, designate canonical/source records, preserve active
   clinical data.
2. **Referral batch quality audit** — scan a batch of referrals for ICD-10
   coding issues, duplicates, insurance anomalies, missing items, and assign
   priority tiers.
3. **Handoff packet completeness review** — verify a care-transition handoff
   packet against the source patient chart for missing sections, clinical-list
   accuracy, disclosure status, and readiness.
4. **Service request (order) validation** — validate a draft service request for
   SBAR completeness, laterality consistency, evidence linkage, and
   sign-readiness.
5. **Referral chart-update decision** — cross-reference a referral with the
   patient chart, identify missing data and safety flags, and determine
   send-readiness.

---

## API Usage Workflow

### Base URL

All calls go to the environment base URL (provided in task scope as
`environment_base_url`). No localhost, no `env/setup.sh`.

### Discovery

1. `GET /api` — returns the list of available top-level endpoints. Always start here.
2. `GET /api/patients` — list all patients (useful to find patient IDs by name/DOB).
3. `GET /api/providers` — list all providers with specialty and fax.
4. `GET /api/codebook/icd10` — full ICD-10 codebook used as the authoritative coding reference.

### Resource drill-down

- **Patients**: `GET /api/patients/{id}` returns the full chart with nested
  `allergies`, `medications`, `problems`, `encounters`, `immunizations`,
  `disclosures`, and `documents`.
  - Sub-resources are also available directly: `GET /api/patients/{id}/problems`,
    `/medications`, `/allergies`, `/encounters`, `/immunizations`,
    `/disclosures`, `/documents`.

- **Duplicate candidates**: `GET /api/duplicate-candidates/{id}` returns the
  candidate record with `patient_ids`, `match_reasons`, `risk_flags`, and
  `suggested_action`.

- **Referrals**: `GET /api/referrals` lists all referrals. Individual referrals
  are available at `GET /api/referrals/{id}`. Referrals contain `batch_id`,
  `icd10_code`, `diagnosis_description`, `insurance_id`, `auth_status`,
  `imaging_received`, `records_received`, `urgency`, `notes`, and demography
  fields.

- **Referral batches**: `GET /api/referral-batches/{id}` returns the batch
  metadata plus the embedded `referrals` array.

- **Handoff packets**: `GET /api/handoff-packets/{id}` returns
  `included_sections`, `patient_id`, provider IDs, `transfer_reason`,
  `functional_status`, `cognitive_status`, and `notes`.

- **Service requests**: `GET /api/service-requests/{id}` returns `note_text`
  (SBAR-formatted), `linked_encounter_ids`, `service_code`, `specialty`,
  `priority`, `status`, and `intent`.

- **Audit log**: `GET /api/audit-log` lists all quality-review audit events.
  Events with `event_type: "duplicate_review"` carry a `status` field that maps
  to the duplicate-candidate `audit_status` enum.

- **Documents**: `GET /api/documents` lists document metadata (templates,
  referral forms, quality queue extracts). Some documents include a
  `related_ids` field for integrated queue extracts.

### Cross-referencing pattern

1. Read the target resource (candidate / batch / packet / request / referral).
2. Read each related patient chart (`GET /api/patients/{id}`).
3. Read the patient's sub-resources as needed (encounters, immunizations,
   disclosures).
4. Read the full ICD-10 codebook (`GET /api/codebook/icd10`).
5. Read the audit log (`GET /api/audit-log`) for any pre-existing review events.
6. Read the providers list (`GET /api/providers`) for contact and specialty
   resolution.

---

## Clinical List Filtering Rules

### Active-only principle

When a schema field refers to **active** problems, medications, or allergies,
**only include items where `status == "active"`**. Items with
`status == "inactive"`, `"expired"`, or any other non-active value must be
excluded.

| Resource | `status` field values seen | Active value |
|----------|--------------------------|--------------|
| `problems[]` | `"active"`, `"inactive"` | `"active"` |
| `medications[]` | `"active"`, `"inactive"` | `"active"` |
| `allergies[]` | `"active"`, `"inactive"` | `"active"` |
| `disclosures[]` | `"active"`, `"expired"` | `"active"` |

### Disclosure status determination

When a schema asks for `disclosure_status` (for a handoff packet or merge):
- Check if the patient has at least one disclosure with `status == "active"`.
- If yes → `"active"`; if none are active → `"expired"` or absent.
- For handoff packets, also verify the active disclosure's `recipient` matches
  the packet's receiving entity.

### Immunization recency

When asked for `most_recent_immunization_id`:
- Compare all immunizations by `date` (descending).
- The immunization with the latest date is most recent.
- If the patient has no immunizations, the field may be absent or null.

---

## ICD-10 Codebook & Coding Rules

### Codebook structure

Each entry has: `code`, `description`, `body_site`, `chapter_prefix`,
`laterality`, `in_musculoskeletal_tracking_range`.

### Laterality in ICD-10 codes

Musculoskeletal codes follow a laterality pattern in the final digit(s):
- `.xx1` suffix → **right** side (e.g., M17.11 = right knee OA)
- `.xx2` suffix → **left** side (e.g., M17.12 = left knee OA)
- Some codes have no laterality (empty `laterality` field), e.g., M48.062
  (spinal stenosis), M79.3 (panniculitis, unspecified)

### Coding issue categories

| Issue type | Detection rule | Example |
|-----------|---------------|---------|
| **Laterality mismatch** | `code.laterality` ≠ side mentioned in `diagnosis_description` | Code M76.61 (right Achilles) but diagnosis says "left ankle" |
| **Narrative mismatch** | `code.description` fundamentally disagrees with `diagnosis_description` | Code M79.3 (Panniculitis) but diagnosis says "Olecranon bursitis" |
| **Out-of-range code** | `in_musculoskeletal_tracking_range == false` for an orthopedic-batch referral, or code outside the relevant chapter | Code G89.29 (chronic pain, not MSK-tracked) for knee pain |

### Code correction logic

When correcting a code:
1. Find the `diagnosis_description`'s intended condition in the codebook.
2. Match the correct laterality from the description text.
3. Use the exact code and casing from the codebook (e.g., preserve the decimal
   and any letter suffixes like `A`).
4. Only include referrals that actually need a correction in
   `corrected_code_suggestions` — omit referrals whose codes are already correct.

---

## Duplicate Patient Reconciliation Rules

### Workflow

1. `GET /api/duplicate-candidates/{candidate_id}` → get `patient_ids`.
2. `GET /api/patients/{idA}` and `GET /api/patients/{idB}` → full charts.
3. `GET /api/audit-log` → find any event where `patient_ids` contains both
   patient IDs and `event_type == "duplicate_review"`.
4. Cross-reference addresses, disclosures, enterprise MRNs, and clinical data.

### Canonical target selection

The **canonical target** (patient that survives the merge) is typically:
- The patient with more complete clinical data (more active meds/problems).
- The patient with the lower/older `enterprise_mrn` (suggesting earlier
  enrollment).
- The patient with active disclosures (indicating active care relationships).
- The patient whose address matches the other (if one has an outdated address).

The **source patient** is the one being merged into the target.

### Audit status mapping

| Audit event `status` | Output `audit_status` enum |
|---------------------|---------------------------|
| `"ready_for_merge"` | `"READY_FOR_MERGE"` |
| `"blocked_address_conflict"` | `"BLOCKED_ADDRESS_CONFLICT"` |
| No matching audit event | `"NO_EVENT_FOUND"` |

### Disposition decision

| Conditions | `disposition` |
|-----------|--------------|
| Audit says ready, no risk flags, addresses match | `"MERGE_READY"` |
| Risk flags present (conflicting address, expired disclosure) or audit blocked | `"NEEDS_CLARIFICATION"` |
| `suggested_action == "do_not_merge"` | `"DO_NOT_MERGE"` |

### Preserved clinical data

- **preserved_active_allergy_labels**: Union of all `active` allergy `label`
  values from both patients, sorted ascending.
- **preserved_active_medication_ids**: Union of all `active` medication `id`
  values from both patients, sorted ascending.
- **preserved_active_problem_codes**: Union of all `active` problem `code`
  values from both patients, sorted ascending.

### Excluded patient IDs

The `excluded_patient_ids` list contains the `source_patient_id` (the record
being de-duplicated away).

### Contact action

- `target_provider_id`: The `primary_provider_id` shared by both patients, or
  the canonical target's provider if they differ.
- `action_required`: `true` if disposition is not `"MERGE_READY"` or if any risk
  flags exist.
- `action_code`: A short code describing the required action.

---

## Referral Batch Quality Audit Rules

### Duplicate detection

Two (or more) referrals are duplicates when they share:
- Same patient (matched by `patient_first_name` + `patient_last_name` +
  `patient_dob`)
- Same `icd10_code` and `diagnosis_description`

Group each set into a list of `referral_id`s, sorted ascending within the group.
The outer `duplicate_groups` list is also sorted by the first element of each
group.

### Insurance anomaly detection

An insurance anomaly exists when the same `insurance_id` appears across
referrals for **different** patients (different name or DOB).

For each anomalous `insurance_id`:
- `related_duplicate_referral_ids`: referral IDs that belong to the same patient
  (sorted ascending).
- `unrelated_referral_ids`: referral IDs that belong to different patients but
  share the same insurance ID (sorted ascending).

Sort the `insurance_anomalies` list by `insurance_id` ascending.

### Missing counts

Count referrals in the batch where:
- `auth_not_submitted`: `auth_required == "Yes"` AND `auth_status == "Not Submitted"`
- `imaging_missing`: `imaging_received == "No"`
- `records_missing`: `records_received == "No"`

### Priority queue classification

| Tier | Criteria |
|------|----------|
| `TIER_1_IMMEDIATE` | Pathological fractures requiring oncology coordination; STAT priority; any referral with notes containing "PRIORITY" for clinical safety reasons |
| `TIER_2_SHORT_TERM` | Urgent referrals; any referral with a laterality, narrative, or code-range issue; referrals missing imaging or records; referrals with auth not submitted and imaging missing simultaneously |
| `TIER_3_ADMINISTRATIVE` | Routine referrals with no coding issues, no missing items, and no urgency flag; known duplicates (keep one representative in this tier) |

Within each tier, referral IDs should be sorted ascending.

---

## Handoff Packet Review Rules

### Missing section detection

Compare the packet's `included_sections` against the expected complete set:
`demographics`, `active_problems`, `active_medications`, `allergies`,
`recent_encounters`, `immunizations`, `functional_status`, `cognitive_status`,
`transfer_plan`, `disclosure`.

Any expected section NOT in `included_sections` is a missing section. Also check
the packet's `notes` field — it often states what was intentionally or
unintentionally omitted.

### Clinical list extraction

- `active_allergy_labels`: All `active` allergy `label` values from the patient
  chart, sorted ascending.
- `active_medication_ids`: All `active` medication `id` values from the patient
  chart, sorted ascending.
- `active_problem_codes`: All `active` problem `code` values, sorted ascending.
  Exclude `inactive` problems.

### Recent encounter IDs

Include all encounter `id` values from the patient chart, sorted by `date`
descending (most recent first). If the question asks for "recent" with a
specific lookback or count, filter accordingly; otherwise include all.

### Most recent immunization

The immunization with the maximum `date` value. Return its `id`.

### Disclosure status

`"active"` if the patient has at least one active disclosure; otherwise report
the actual status.

### Readiness determination

| Condition | `readiness` |
|-----------|------------|
| All sections present, all clinical data matches, no issues found | `"READY"` |
| Minor sections missing (e.g., cognitive_status) or notes flag non-critical omissions | `"READY_WITH_WARNINGS"` |
| Critical sections missing (e.g., medications, allergies, problems) or no disclosure | `"BLOCKED_INCOMPLETE_PACKET"` |
| Data inconsistency between packet and chart requires clarification | `"NEEDS_CLARIFICATION"` |
| Safety-critical issue found (e.g., medication interaction, missing allergy) | `"BLOCKED_ORDER_SAFETY"` |

### Risk flags

Include string labels for any concerns: missing critical sections, inactive
items that might appear active, expired disclosures, mismatches between packet
and chart, clinical safety issues (e.g., anticoagulation + fall risk, severe
allergies).

---

## Service Request Validation Rules

### SBAR completeness

Parse the `note_text` field for four sections:

| Section | Detection pattern |
|---------|------------------|
| SITUATION | Line starting with `Situation:` |
| BACKGROUND | Line starting with `Background:` |
| ASSESSMENT | Line starting with `Assessment:` |
| RECOMMENDATION | Line starting with `Recommendation:` followed by substantive text |

A section is **missing** if the line is absent OR the value after the colon is
empty/whitespace-only.

`sbar_sections_present` is an object with keys `SITUATION`, `BACKGROUND`,
`ASSESSMENT`, `RECOMMENDATION` (exact casing) and boolean values.

`missing_sbar_sections` lists the section names (exact casing from the SBAR
keys) that are absent or empty, sorted ascending.

### Laterality consistency

1. Parse the `note_text` for anatomical laterality references (left/right).
2. Get the patient's active problems and linked encounter diagnoses.
3. Look up each diagnosis code in the ICD-10 codebook for `laterality`.
4. Compare: if the request's stated laterality matches the codebook laterality
   of the patient's active problem, it is consistent → `true`.
5. If there is a conflict (e.g., note says "left" but code is for right), it is
   inconsistent → `false`.

### Evidence encounters

`evidence_encounter_ids` = the `linked_encounter_ids` from the service request,
sorted ascending.

### Blocker codes

Any issues that prevent signing or sending:
- Missing SBAR section(s)
- Laterality inconsistency
- Code mismatch between request and chart
- Draft status with incomplete data

### Ready to sign

`true` only when ALL of:
- `status != "draft"` (or draft is complete enough)
- All four SBAR sections present and substantive
- Laterality is consistent
- No blocker codes

In practice, a draft missing any SBAR section is NOT ready to sign.

### Order validation object

| Field | Source |
|-------|--------|
| `priority` | From the service request's `priority` field |
| `service_code` | From the service request's `service_code` field |
| `specialty` | From the service request's `specialty` field |
| `status` | From the service request's `status` field |

---

## Referral Chart-Update Decision Rules

### Allergy update

When the referral `notes` indicate an allergy should be added before sending:
- `allergen`: The allergen name from the note
- `severity`: The severity mentioned in the note (e.g., "Severe")
- `reaction`: If specified in notes, use it; otherwise use a clinically
  reasonable default based on the allergen type
- `status`: `"active"`

If no allergy action is needed, the allergy_update object may still need fields
— check the schema's required keys.

### Diagnosis update

Cross-reference the referral's `diagnosis_description` and `icd10_code` against
the patient's active `problems` and most recent encounter `diagnoses`:
- If the referral code matches the patient's active problem code → no update
  needed (but the schema may still require values)
- If the most recent encounter has a more specific or different diagnosis than
  what's on the referral → suggest the encounter's code and description

### Letter merge fields

List of data elements to auto-populate in the referral letter. These are
typically the field names that need to be merged/included, sorted ascending.

### Recent encounter IDs

All encounter `id` values from the patient chart, sorted by date descending
(most recent first) — OR sorted ascending by ID if the schema says "sort stable
IDs ascending." Read the schema ordering directive carefully for each field.

### Referral target

| Field | Source |
|-------|--------|
| `provider_id` | From the referral's receiving context (may need provider list lookup by specialty) |
| `specialty` | The specialty the referral is directed to (may match the batch `service_line`) |

### Safety flags

String labels for safety concerns:
- Missing allergies that the referral destination needs to know about
- Drug-disease interactions (e.g., NSAIDs with CKD)
- Missing critical clinical data for the referral context
- Notes in the referral that explicitly call out a required action

### Send readiness

| Condition | `send_ready` |
|-----------|-------------|
| All required data present, no unresolved issues | `"READY"` |
| Ambiguity or missing information that needs clarification | `"NEEDS_CLARIFICATION"` |
| Required action not taken (e.g., missing allergy noted in referral) or safety-critical gap | `"BLOCKED"` |

---

## Output Field Conventions (Universal)

### Enum casing

All enum values use `UPPER_SNAKE_CASE` exactly as specified in the answer
template's `allowed_enums`. Never lowercase or title-case.

### List ordering

**Default rule**: Lists of stable identifiers (IDs, codes) MUST be sorted
ascending (lexicographic/alphanumeric). This applies unless the field name
explicitly references "priority", "queue", or "ranking".

**Priority queues**: Sort IDs ascending within each tier. The tiers themselves
are ordered by priority (Tier 1, Tier 2, Tier 3) — not alphabetically.

**Date-ordered lists**: When a field like `recent_encounter_ids` implies
recency, sort by date descending unless the schema directive explicitly says
"sort stable IDs ascending."

### Date and timestamp formats

- Dates: `YYYY-MM-DD` (e.g., `2026-03-10`)
- Timestamps: ISO 8601 (e.g., `2026-03-18T14:20:00Z`)
- Do NOT reformat dates from the API; pass them through as-is.

### Numeric precision

- Counts are integers.
- Decimal scores or ratios: round to 3 decimal places.

### Empty collections

- Empty lists: `[]` (not `null`, not absent).
- Empty objects/maps: `{}`.

### Required fields

Every key listed in the schema's `required_keys` must be present in the output,
even if the value is an empty list, empty string, or `false`. Do not omit
required keys.

---

## Source Precedence

When data sources conflict, use this precedence (highest first):

1. **Answer template schema** — defines required shape, enums, ordering rules.
2. **ICD-10 codebook** — authoritative for code descriptions, laterality, and
   tracking-range membership.
3. **Patient chart** — authoritative for clinical data (active problems, meds,
   allergies, encounters, immunizations).
4. **Audit log** — authoritative for pre-existing quality review decisions.
5. **Referral/handoff/service-request notes** — supplementary guidance that may
   override assumptions but never contradicts structured clinical data.
6. **Task scope** — provides target IDs and endpoint base URL.

---

## Common Pitfalls

1. **Including inactive items**: Forgetting to filter `problems`, `medications`,
   and `allergies` by `status == "active"` when the schema says "active."
2. **Not sorting IDs**: Default sort is ascending — forgetting this produces
   wrong output even if the values are correct.
3. **Wrong enum casing**: Using `"Ready"` instead of `"READY"`, or
   `"ready_for_merge"` instead of `"READY_FOR_MERGE"`.
4. **Laterality confusion**: Checking only the code description text without
   cross-referencing the codebook's `laterality` field. The codebook laterality
   is authoritative.
5. **Missing insurance anomalies**: An insurance anomaly is per `insurance_id`,
   not per referral. Multiple referrals for the same patient with the same
   insurance ID is NOT an anomaly — it only counts when the same
   `insurance_id` spans different patients.
6. **Overlooking audit log**: Failure to check the audit log for
   pre-existing merge/review events leads to incorrect `audit_status`.
7. **Omitting required keys**: Every `required_keys` entry in the schema must
   appear in the output object, even if the value would be empty/zero/false.
8. **Empty Recommendation detection**: An SBAR "Recommendation:" line followed
   by nothing or whitespace counts as MISSING — do not mark it present.
9. **Duplicate referral grouping**: Same patient + same condition = duplicate,
   even if referring physician differs. The notes field often confirms this
   (e.g., "Second referral for same patient and condition").
10. **Disclosure expiration**: Disclosures with `status == "expired"` are NOT
    active. Only `status == "active"` disclosures count for `disclosure_status`.
11. **Canonical target selection**: Do not reverse target/source — the target is
    the record that remains (usually the more complete one), and the source is
    the one being merged away.
12. **Priority classification**: A referral can qualify for multiple tiers. The
    HIGHEST-priority tier takes precedence (Tier 1 beats Tier 2 beats Tier 3).

---

## Quick Reference: Endpoint Map

| Resource | List endpoint | Detail endpoint |
|----------|-------------|-----------------|
| Patients | `GET /api/patients` | `GET /api/patients/{id}` |
| Duplicate candidates | `GET /api/duplicate-candidates` | `GET /api/duplicate-candidates/{id}` |
| Referrals | `GET /api/referrals` | `GET /api/referrals/{id}` |
| Referral batches | `GET /api/referral-batches` | `GET /api/referral-batches/{id}` |
| Handoff packets | `GET /api/handoff-packets` | `GET /api/handoff-packets/{id}` |
| Service requests | `GET /api/service-requests` | `GET /api/service-requests/{id}` |
| Providers | `GET /api/providers` | — |
| ICD-10 codebook | `GET /api/codebook/icd10` | — |
| Audit log | `GET /api/audit-log` | — |
| Documents | `GET /api/documents` | — |
| Health | `GET /health` | — |
