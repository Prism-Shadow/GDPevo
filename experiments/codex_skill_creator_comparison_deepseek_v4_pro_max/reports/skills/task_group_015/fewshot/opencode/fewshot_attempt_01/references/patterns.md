# Common Patterns

These patterns recur across multiple workflow families. Use them whenever a
workflow's instructions say "build active key unions," "validate ICD-10 codes,"
"derive risk flags," or similar.

## Active List Reconciliation

Used when the template asks for unions of active clinical keys across two
patients (merge packets) or reconciliation between a duplicate-candidate preview
and live patient endpoints.

**Building a two-patient union:**

1. Fetch conditions, medications, and allergies for both patients.
2. Filter each list to active records only:
   - Conditions: `clinical_status: "active"`
   - Medications: `status: "active"`
   - Allergies: `clinical_status: "active"`
3. Extract `normalized_key` from each record.
4. Take the set union (deduplicate identical keys across patients).
5. Sort alphabetically.
6. If the template has parallel fields (e.g. `clinical_unions` and
   `active_key_unions`), populate both with the same sorted arrays.

**Reconciling against a duplicate candidate preview:**

When a duplicate candidate record also carries its own preview of active
condition/medication/allergy keys, compare those preview keys against the
keys you fetched directly from each patient's active endpoints. Any key
present in the live endpoint but missing from the duplicate candidate preview
must be recorded as "added from active endpoints." The `authoritative_source`
should be set to the template's expected value (typically
`patient_active_list_endpoints_over_duplicate_preview`).

## Identity Signal Analysis

Used in merge packets and ServiceRequest quality reviews that involve a
duplicate candidate.

**From duplicate candidate record:**

The candidate object directly provides `match_signals` and `conflict_signals`
as enum arrays. Copy them verbatim into the output after verifying they make
sense against the demographic data. Sort alphabetically.

**Demographic field-by-field comparison:**

Compare the two patient demographic objects on these fields:
- `dob` (date equality)
- `sex` (string equality)
- `given_name` (exact vs. variant -- "Thomas" vs. "Tom" is a name variant, not
  a mismatch)
- `family_name` (exact equality)
- `address_line` (exact vs. abbreviation -- "St." vs. "Street" is an
  abbreviation, not a different address)
- `phone` (exact equality)
- `email` (exact equality)
- `insurance_id` (exact equality)
- `primary_care_provider_id` (exact equality)

Record each matching field in `demographic_matches` and each conflicting field
in `demographic_conflicts`. Name variants and abbreviation differences are
conflicts, not matches, but they are weaker conflicts than completely different
values.

**Shared-document signals:**

A document whose `subject_patient_id` is patient A but appears in patient B's
document list (or vice versa) is a strong identity continuity signal. Note it
as a match signal (e.g. `shared_external_cardiology_document`).

## ICD-10 Validation

Used in referral coordination, ServiceRequest quality review, and batch audits.

**Basic code lookup:**

Call `GET /api/icd10/{code}`. The response gives `description` and `chapter`.
Always validate that the code returns a real entry; 404 or missing means
`invalid_code`.

**Chapter vs. service-line validation:**

Each service line expects codes from specific ICD-10 chapters:

| Service line | Expected chapter(s) |
|---|---|
| orthopedics | Musculoskeletal |
| cardiology | Circulatory |
| pulmonology | Respiratory |
| neurology | Nervous System |
| oncology | Neoplasms |
| skilled_nursing | Various (per-nursing-assessment) |

A code whose chapter does not match the service line's expected chapter is an
`out_of_range_chapter` issue. Injury codes (chapter "Injury") on an orthopedics
referral are out of range because orthopedics expects "Musculoskeletal" codes.

**Narrative match check:**

Compare the ICD-10 code's `description` text against the referral's
`diagnosis_narrative`. This is a semantic comparison, not a string match:
- If the description and narrative describe the same condition (even in
  different words), they match.
- If the description is about one body region/condition and the narrative is
  about a completely different one, they do not match.
- If the description has a laterality (left/right/bilateral) and the narrative
  explicitly names the opposite side, flag as `laterality_mismatch`.
- If the description has a laterality but the narrative omits it, flag as
  `missing_laterality`.

**Expected terms for mismatch records:**

When flagging a laterality or narrative mismatch, populate `expected_terms`
with the key descriptors from the ICD-10 description that would correctly
describe the code. For example, a code S83.241A (right medial meniscus tear)
whose narrative says "lumbar radiculopathy" should have `expected_terms` like
`["right medial meniscus tear"]`.

## Encounter Selection

Used in care transition packets and referral coordination.

**Filtering for relevance:**

Start with all encounters for the patient. Apply these filters in order:

1. Remove encounters with `signed_status` other than `signed` unless there
   are fewer than the required count, in which case include `amended`.
2. Remove encounters that are clearly unrelated to the service line (e.g. a
   dermatology visit for an orthopedic handoff) unless the count is too low.
3. Remove encounters outside the time window. The window is typically 90 days
   before the transition date for care transitions, or before the referral date
   for referral coordination. Stale encounters (>6 months back) are always
   excluded.
4. Remove encounters with `type` values that are not clinical visits (e.g.
   administrative or billing-only encounters).
5. Take the N most recent by `date`, newest first, where N is the count
   specified in the template (commonly 4).

**Documenting exclusions:**

Every encounter you reviewed but excluded must be listed in
`excluded_encounter_ids`, sorted ascending. Every included encounter goes in
`selected_encounter_ids` in newest-to-oldest order. The `selection_basis` should
describe the filtering rule (e.g. `orthopedic_surgical_handoff_window`).

## Risk Flag Derivation

Used in care transition packets.

The template defines an allowed set of risk flag codes. Derive them from the
active clinical data, not from a pre-existing risk-flag endpoint. Each flag
needs supporting evidence.

**Derivation table:**

| Risk flag | Triggered when |
|---|---|
| `cognitive_memory_loss` | Any active condition whose `normalized_key` or `description` indicates cognitive impairment or memory loss |
| `fall_risk_note_required` | Active lower-extremity OA conditions (hip_oa, knee_oa) PLUS pain-management medications |
| `hypertension` | Active condition with `normalized_key: "hypertension"` |
| `insulin_dependent_diabetes` | Active condition with `normalized_key: "diabetes_type_2"` (or type_1) PLUS active insulin medication |
| `latex_allergy` | Active allergy with allergen matching latex |
| `perioperative_glucose_plan_needed` | Diabetes condition + insulin medication AND the transition is surgical |

For each triggered flag, populate the evidence object:
- `condition_keys`: alphabetically sorted active condition `normalized_key` values that contributed.
- `medication_keys`: alphabetically sorted active medication `normalized_key` values that contributed.
- `encounter_ids`: alphabetically sorted IDs of encounters that mention the relevant conditions or medications.

If a flag is triggered purely by allergy data (no conditions or encounters),
the `condition_keys` and `encounter_ids` arrays should be empty.

## Distractor Exclusion

Used in every workflow. The template may or may not have explicit
`excluded_distractors` sections -- read it to know.

Records to exclude from the output:

- Conditions with `clinical_status` other than `active` (unless the template
  explicitly asks for broader status).
- Medications with `status` other than `active`.
- Allergies with `clinical_status` other than `active` (unless the template
  asks for a broader scan).
- Encounters outside the relevant window, unsigned/draft, or unrelated to the
  service line.
- Documents with `type: "chart_summary"` (for merge packets).
- Documents unrelated to either patient in a merge pair.
- Referrals whose `service_line` does not match the batch service line.
- Referrals whose `diagnosis_code` chapter does not match the expected chapter.

When the template requires `excluded_distractors`, list the excluded
`normalized_key` values sorted alphabetically, and the excluded document and
audit IDs sorted alphabetically.

## Readiness Assessment

Used in every workflow.

**Readiness logic:**

1. Check that every required data source was successfully fetched and is
   non-empty where the template demands it.
2. Check authorization status (for referrals): `approved` or `not_required`
   means no authorization blocker.
3. Check required documents against received documents.
4. Check that disclosure/consent is `permitted`.
5. Check for clinical conflicts (duplicate signals, code mismatches, allergy
   gaps).

**Readiness output:**

- `ready_to_send: true` / `ready_for_merge_packet: true` / `ready_to_send: true`:
  all checks pass, no blockers.
- Status `ready` / `ready_with_risk_flags`: packet is sendable but risk flags
  are noted (for care transitions).
- Status `ready_with_review_note`: minor issues exist that should be noted but
  do not block sending.
- Status `not_ready` / `blocked`: a hard blocker exists. List the blocking
  issue codes using only the template's allowed values.

Never set readiness to `ready` when there are missing required data, denied
authorizations, or unpermitted disclosures.
