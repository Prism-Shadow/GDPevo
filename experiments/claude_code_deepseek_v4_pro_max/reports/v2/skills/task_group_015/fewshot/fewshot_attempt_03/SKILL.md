# EHR Data Governance & Clinical Record Quality Control — Skill

## Environment

**Base URL:** `GDPEVO_ENV_BASE_URL` (value from `environment_access.md`).
Replace any `<TASK_ENV_BASE_URL>`, `localhost`, `127.0.0.1`, `API_BASE_URL`, or
`BASE_URL` placeholder with this remote URL. Do not start a local server or
source `env/setup.sh`.

All requests are unauthenticated HTTP GET. Return JSON.

## Output Format Rules

1. **Return only one JSON object** — no explanatory prose outside the JSON.
2. **Key casing** — use the exact keys and enum values from the answer template
   schema (all enums are `UPPER_SNAKE_CASE`).
3. **List ordering** — sort stable identifier lists **ascending** (lexicographic
   string sort). The only exceptions are fields explicitly named "queue" or
   "ranking", which preserve their own priority order.
4. **Dates** — `YYYY-MM-DD`. Timestamps — ISO 8601 (`2026-03-22T09:44:00Z`).
5. **Counts** — integers. Ratios/decimal scores — round to 3 decimal places.
6. **Empty values** — use `""` for missing string fields, `[]` for empty lists,
   `false` for missing booleans (unless the template allows `null`).

## Shared Enum Vocabulary

| Domain | Enum Values |
|--------|-------------|
| Audit status | `READY_FOR_MERGE`, `BLOCKED_ADDRESS_CONFLICT`, `NO_EVENT_FOUND` |
| Merge disposition | `MERGE_READY`, `NEEDS_CLARIFICATION`, `DO_NOT_MERGE` |
| Priority tiers | `TIER_1_IMMEDIATE`, `TIER_2_SHORT_TERM`, `TIER_3_ADMINISTRATIVE` |
| Packet readiness | `READY`, `READY_WITH_WARNINGS`, `BLOCKED_INCOMPLETE_PACKET`, `NEEDS_CLARIFICATION`, `BLOCKED_ORDER_SAFETY` |
| Send readiness | `READY`, `NEEDS_CLARIFICATION`, `BLOCKED` |
| Booleans | `true`, `false` |

## API Endpoint Reference

```
GET /health
GET /api
GET /api/patients
GET /api/patients/{patient_id}
GET /api/patients/{patient_id}/problems
GET /api/patients/{patient_id}/medications
GET /api/patients/{patient_id}/allergies
GET /api/patients/{patient_id}/encounters
GET /api/patients/{patient_id}/immunizations
GET /api/patients/{patient_id}/disclosures
GET /api/patients/{patient_id}/documents
GET /api/duplicate-candidates
GET /api/duplicate-candidates/{candidate_id}
GET /api/referrals
GET /api/referral-batches
GET /api/referral-batches/{batch_id}
GET /api/handoff-packets
GET /api/handoff-packets/{packet_id}
GET /api/service-requests
GET /api/service-requests/{request_id}
GET /api/providers
GET /api/codebook/icd10
GET /api/documents
GET /api/audit-log
```

---

## Task 1 — Duplicate Candidate Reconciliation

**Trigger:** Task provides a `DUP-*` candidate ID and asks for a merge decision.

### Workflow

1. `GET /api/duplicate-candidates/{candidate_id}` — returns `patient_ids[]`,
   `match_reasons[]`, `risk_flags[]`, `suggested_action`.
2. For each patient in `patient_ids`, `GET /api/patients/{id}` for the full
   chart. Also fetch `/{id}/problems`, `/{id}/medications`, `/{id}/allergies`,
   `/{id}/disclosures` if the parent object doesn't include them inline.
3. `GET /api/audit-log` — find the audit event whose `patient_ids` array
   matches the candidate's patient IDs. Use its `event_id` and `status`.

### Business Rules

**Audit status** — map the audit-log `status` field:
- `"ready_for_merge"` → `READY_FOR_MERGE`
- `"blocked_address_conflict"` → `BLOCKED_ADDRESS_CONFLICT`
- No matching event → `NO_EVENT_FOUND` (set `merge_audit_event_id: ""`)

**Merge disposition** — map `suggested_action`:
- `"review_for_merge"` → `MERGE_READY`
- `"clarify_before_merge"` → `NEEDS_CLARIFICATION`
- `"do_not_merge"` → `DO_NOT_MERGE`

**Reason code** — derived from disposition sources:
- `STABLE_MRN_MATCH` when merge is clean (no risk flags, audit ready)
- When the audit is blocked, the reason reflects the blocker (e.g. address
  conflict). When risk flags exist, the reason reflects the highest-severity
  flag.

**Canonical target vs source patient** — the patient with the more complete
chart becomes `canonical_target_patient_id`. Heuristic:
- Patient with active disclosures > patient without.
- Patient with more encounters > patient with fewer.
- Patient with more comprehensive clinical lists (problems, meds, allergies) >
  patient with fewer.
- The other patient becomes `source_patient_id`.

**Excluded patient IDs** — patients from the candidate's `patient_ids` that are
NOT included in the merge (e.g. `different DOB` flag means that patient is
excluded). Empty list `[]` if both are mergeable.

**Preserved active clinical lists** — union of active (`status: "active"`)
items from BOTH patients (canonical + source):
- `preserved_active_allergy_labels` — the `label` field of each active allergy.
- `preserved_active_medication_ids` — the `id` field of each active medication.
- `preserved_active_problem_codes` — the `code` field of each active problem.
- Filter out any medication/problem/allergy with `status` not equal to
  `"active"`. Sort each list ascending.

**Contact action:**
- `NONE_REQUIRED` / `action_required: false` / `target_provider_id: ""` when
  the disposition is `MERGE_READY` or `DO_NOT_MERGE` and there is no conflicting
  address.
- When risk flags include `conflicting_current_address`, contact may be
  required (use a code like `CONTACT_PRIMARY_PROVIDER` and set
  `action_required: true` with the relevant provider ID).

---

## Task 2 — Referral Batch Audit

**Trigger:** Task provides a `BATCH-*` ID and asks for issue sets, priority
queues, and summary counts.

### Workflow

1. `GET /api/referral-batches/{batch_id}` — returns a `batch` object and a
   `referrals[]` array.
2. `GET /api/codebook/icd10` — cross-reference every referral's `icd10_code`
   against the codebook.

### Issue Detection Rules

#### Laterality Mismatch
Compare referral's `diagnosis_description` body side (left/right) against the
codebook entry's `laterality` for that `icd10_code`.
- If the description says "left" but code laterality is `"right"` (or vice
  versa), it's a laterality mismatch.
- Find the correct code: same `body_site`, opposite `laterality`, from the
  codebook. The corrected code preserves the decimal/case style exactly as the
  codebook displays it.
- Record the corrected code in `corrected_code_suggestions` keyed by referral
  ID. Only include referrals that actually need correction — do not include
  clean referrals.

#### Narrative Mismatch
When the `diagnosis_description` describes a fundamentally different condition
than what the ICD-10 code maps to (not just a laterality flip — the body site
or condition type doesn't match). Cross-reference the description body site and
pathology against the codebook entry. If no codebook entry matches the
described condition, the referral likely has a narrative mismatch. Look up the
correct code in the codebook that matches the described condition.

#### Out-of-Range Codes
An ICD-10 code is out of range when `in_musculoskeletal_tracking_range` is
`false` in the codebook (for an orthopedic audit). Also, codes whose
description doesn't actually describe a musculoskeletal condition. List these
referral IDs in `out_of_range_code_referral_ids`.

#### Duplicate Groups
Two referrals are duplicates when they share the same patient (same
`patient_first_name` + `patient_last_name` + `patient_dob`) AND the same
clinical condition. Group duplicate referral IDs together. Sort each inner
group ascending, sort groups by their first element ascending.

#### Insurance Anomalies
When the same `insurance_id` appears on multiple referrals, check:
- If the referrals are for the same patient (a duplicate group) → list under
  `related_duplicate_referral_ids`.
- If the referrals are for different patients → list under
  `unrelated_referral_ids`.
- Sort both sub-lists ascending. Sort the `insurance_anomalies` array by
  `insurance_id` ascending.

#### Missing Counts
- `auth_not_submitted` — count referrals where `auth_required` is `"Yes"` and
  `auth_status` is `"Not Submitted"`.
- `imaging_missing` — count referrals where `imaging_received` is `"No"`.
- `records_missing` — count referrals where `records_received` is `"No"`.
- Count each referral only once per category; a single referral may contribute
  to multiple counts.

### Priority Queue Rules

- **tier1_immediate** — referrals flagged with urgent clinical risk:
  pathological fracture, oncology coordination, urgent + serious finding.
- **tier2_short_term** — referrals needing code correction (laterality or
  narrative mismatch), or referrals missing imaging/records that block
  processing.
- **tier3_administrative** — referrals with only administrative issues
  (auth not submitted, rescheduling requests) and no clinical or missing-data
  problems.
- A referral should appear in at most one tier. Higher tiers take precedence.
- Sort referral IDs ascending within each tier.

---

## Task 3 — Handoff Packet Review

**Trigger:** Task provides a `HANDOFF-*` packet ID and asks for a completeness
and readiness decision.

### Workflow

1. `GET /api/handoff-packets/{packet_id}` — get `patient_id`,
   `included_sections[]`, `receiving_provider_id`, `notes`.
2. `GET /api/patients/{patient_id}` — full chart. If clinical lists aren't
   inline, fetch `/problems`, `/medications`, `/allergies`,
   `/encounters`, `/immunizations`, `/disclosures`.

### Business Rules

**Active clinical lists** — from the patient, filter to `status: "active"`:
- `active_allergy_labels` — `label` of each active allergy.
- `active_medication_ids` — `id` of each active medication.
- `active_problem_codes` — `code` of each active problem.
  **Exclude inactive problems** (`status` ≠ `"active"`).
  Sort all lists ascending.

**Disclosure status** — check the patient's disclosures list. If there is a
disclosure with `status: "active"`, disclosure_status is `"ACTIVE"`. Otherwise
`"INACTIVE"` (or the actual status value). If the disclosures array is empty
and the packet is for a care transition, check if a disclosure was created for
this transition.

**Most recent immunization** — sort the patient's immunization list by `date`
descending. Pick the first entry's `id`. If the list is empty, use `""`.

**Recent encounters** — collect encounter IDs from encounters that are
clinically recent. The recency window is context-dependent:
- Handoff packet date or current date is the reference point.
- Encounters within roughly the last 6 months are "recent."
- Encounters older than ~6 months (e.g. the prior calendar year) are excluded.
- Sort the resulting IDs ascending.

**Missing packet sections** — compare `included_sections` against the full
expected section set. Common expected sections:
`demographics`, `active_problems`, `active_medications`, `allergies`,
`recent_encounters`, `immunizations`, `functional_status`,
`cognitive_status`, `transfer_plan`, `disclosure`.
Any expected section not in `included_sections` is missing. Sort the missing
list ascending. Also check the `notes` field — it may explicitly state which
section is omitted.

**Risk flags** — derive from missing sections. Pattern:
`MISSING_<SECTION_NAME_UPPER>`. Example: missing `cognitive_status` →
`MISSING_COGNITIVE_STATUS`. Sort flags ascending.

**Readiness:**
- If any expected section is missing → `BLOCKED_INCOMPLETE_PACKET`.
- If all sections present but with clinical concerns → `READY_WITH_WARNINGS`.
- If all sections present and clean → `READY`.

---

## Task 4 — Service Request Validation

**Trigger:** Task provides an `SR-*` request ID and asks for an order-quality
decision.

### Workflow

1. `GET /api/service-requests/{request_id}` — get `patient_id`,
   `linked_encounter_ids[]`, `note_text`, `service_code`, `specialty`,
   `priority`, `status`, `intent`.
2. `GET /api/patients/{patient_id}` and `/{patient_id}/encounters` — verify
   linked encounters exist and cross-reference diagnoses.
3. `GET /api/codebook/icd10` — validate `service_code` if needed.

### SBAR Parsing Rules

Parse the `note_text` field for four sections delimited by labels. Each section
begins with `<Label>:` and continues until the next label or end of string:

| Label | Key in `sbar_sections_present` |
|-------|-------------------------------|
| `Situation:` | `SITUATION` |
| `Background:` | `BACKGROUND` |
| `Assessment:` | `ASSESSMENT` |
| `Recommendation:` | `RECOMMENDATION` |

A section is **present** (`true`) if:
- The label appears in `note_text`, AND
- The text following the label (up to the next label or end of string) is
  **not empty** after trimming whitespace.

A section is **missing** (`false`) if the label is absent, OR the label is
present but the text after it is empty/whitespace-only.

**Missing SBAR sections** — list the SBAR section names (as they appear in the
sbar_sections_present keys, e.g. `RECOMMENDATION`) for any section that is
`false`. Sort ascending.

**Blocker codes** — derive from missing sections. Pattern:
`MISSING_<SECTION>`. Example: missing RECOMMENDATION → `MISSING_RECOMMENDATION`.
Sort ascending.

**Laterality consistency** — compare the body side mentioned in the linked
encounter's diagnosis (or the patient's active problem) against the laterality
implied by the referral specialty. If the encounter describes a left-side issue
and the specialty is the corresponding surgical specialty, it's consistent
(`true`). If the body sides don't match, `false`.

**Evidence encounters** — the `linked_encounter_ids` from the service request.
Verify each ID actually belongs to the patient's encounter list. Sort ascending.

**Ready to sign** — `true` only when ALL SBAR sections are present
(all four `true`) AND `laterality_consistent` is `true`. Otherwise `false`.

**Order validation** — copy directly from the service request's fields:
`priority`, `service_code`, `specialty`, `status`. Preserve the exact values
from the API response.

---

## Task 5 — Referral Chart-Update Decision

**Trigger:** Task provides a `REF-*` referral ID and a `PAT-*` patient ID, and
asks for a structured referral quality decision.

### Workflow

1. `GET /api/referrals` (or filter by the given referral ID) — get the
   referral row with `icd10_code`, `diagnosis_description`, `notes`,
   `referring_physician`, `referring_practice`, `urgency`, `referral_reason`.
2. `GET /api/patients/{patient_id}` — full chart.
3. `GET /api/patients/{patient_id}/encounters` — recent encounters.
4. `GET /api/providers` — find the target provider and specialty.
5. `GET /api/codebook/icd10` — verify the diagnosis code.

### Business Rules

**Allergy update** — if the referral notes mention an allergy that needs to be
added (e.g. "Add severe iodinated contrast allergy before sending"), populate
the `allergy_update` object with the allergen name, reaction, severity, and
`status: "active"`. Derive the reaction and severity from the context (e.g.
contrast allergy with a note of severity implies an anaphylactoid-type
reaction). If no allergy update is needed, omit or provide an empty object
(consult the template schema).

**Diagnosis update** — use the referral's `icd10_code` and
`diagnosis_description`. Cross-reference with the codebook for the correct
description.

**Letter merge fields** — fields that should be populated in a referral letter.
Common fields: `Patient_Name`, `DOB`, `Active_Problems`, `Allergies`,
`Referral_Reason`. Include fields relevant to the referral context. Sort the
list ascending.

**Recent encounter IDs** — collect encounter IDs that are clinically recent
(same recency rules as Task 3: roughly within 6 months, or encounters from
within the current clinical episode). Sort ascending.

**Referral target** — determine the appropriate provider and specialty. Check
the referral's diagnosis and look up which provider/specialty matches in
`/api/providers`. The target specialty should match the referral's clinical
domain (e.g., heart failure → Advanced Heart Failure, orthopedics →
Orthopedic Surgery).

**Safety flags** — derive from referral notes and patient data gaps. Pattern:
- Contrast allergy needed → `CONTRAST_ALLERGY_REQUIRED`
- Missing critical clinical data → context-dependent flag name.
Sort flags ascending.

**Send ready** — `READY` when all required fields can be populated and the
referral is complete enough to send. `NEEDS_CLARIFICATION` when some data is
ambiguous. `BLOCKED` when critical information is missing and cannot be
determined.

**Unresolved quality issues** — list any issues that couldn't be resolved.
Empty `[]` when everything is resolved. Sort ascending if they contain IDs.

---

## Common Pitfalls

1. **Sort direction** — always ascending for stable ID lists. Do NOT sort by
   clinical priority, creation date, or any other order unless the field name
   explicitly says "queue" or "ranking".
2. **Inactive items in clinical lists** — always filter by `status: "active"`.
   Inactive problems, resolved allergies, and discontinued medications must be
   excluded from preserved/active lists.
3. **Laterality vs narrative mismatch** — a laterality mismatch is a
   left/right flip for the SAME body site/condition. A narrative mismatch is a
   DIFFERENT condition entirely (different body site or pathology). Do not
   conflate them.
4. **Enum casing** — all enum values are `UPPER_SNAKE_CASE`. Never return
   `camelCase` or `Title Case` enum values even if the API returns them
   differently.
5. **Empty string vs null** — use `""` for missing scalar string fields (not
   `null` and not omitting the key), unless the template explicitly uses
   `null`.
6. **Codebook code style** — preserve the exact format from the codebook
   (decimal, suffix letter, etc.). Do not add or remove dots or suffix
   characters.
7. **Insurance anomalies** — same insurance ID on truly different patients is
   anomalous. Same insurance ID on duplicate referrals for the same patient is
   expected (list as `related_duplicate`).
8. **Priority queue assignment** — each referral goes in at most ONE tier
   (highest applicable). Tier 1 is clinical/safety urgency. Tier 2 is
   processing blockers. Tier 3 is administrative only.
9. **SBAR parsing** — a section label present with only whitespace after it
   counts as `false` (missing). The section is only present if it has
   substantive content.
10. **Recency for encounters** — use the packet/service/referral date as the
    reference point. Encounters more than ~6 months in the past (or from a
    clearly prior calendar year) are usually excluded from "recent" lists.
11. **Canonical patient selection** — the patient without disclosures is not
    automatically the source. Compare chart completeness holistically:
    disclosures > encounters > clinical list breadth > MRN recency.
