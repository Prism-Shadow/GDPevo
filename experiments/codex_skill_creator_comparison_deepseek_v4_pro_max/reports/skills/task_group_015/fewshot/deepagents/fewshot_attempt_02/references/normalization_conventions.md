# Normalization Conventions

## Normalized Keys

Every clinical record (condition, medication, allergy) exposed by the patient endpoints includes a `normalized_key` field. This is the canonical identifier used across all EHR quality-governance packets.

### Format

- Lowercase only
- Underscores replace spaces
- No ICD-10 codes, no UIDs
- Consistent across patients (e.g., `hypertension` always means the same thing)

### Common Examples

| Category | Normalized Keys Seen in Training |
|----------|----------------------------------|
| Conditions | `hypertension`, `diabetes_type_2`, `copd`, `coronary_artery_disease`, `right_knee_oa`, `left_knee_oa`, `right_hip_oa`, `heart_failure_diastolic`, `dyspnea`, `memory_loss` |
| Medications | `aspirin`, `metformin`, `insulin_glargine`, `acetaminophen`, `lisinopril`, `furosemide`, `naproxen`, `baseline_med` |
| Allergies | `penicillin`, `iodinated_contrast`, `sulfa_antibiotics`, `latex`, `baseline_allergy` |

## Active vs. Inactive Filtering

### Rule

For all clinical lists (conditions, medications, allergies):

- **Include** records with `status: "active"` in the active-key arrays and clinical unions.
- **Exclude** records with `status: "inactive"`, `status: "resolved"`, or `status: "entered-in-error"` from active-key arrays.

Inactive/excluded records go into distractor arrays (`excluded_distractors`) when the template asks for them.

### Edge Cases

- Medications with `status: "active"` but unrelated to the task's clinical focus are still active and belong in the active medication list. They may be tagged differently in medication highlights.
- `"unknown"` status on allergies: treat as active for safety (allergy readiness).

## Sorting Rules

### String Arrays

All arrays of simple strings (e.g., `active_condition_keys`, `match_signals`, `referral_id` lists) must be sorted alphabetically ascending unless the template overrides.

### Object Arrays

- **Referral objects**: Sort by `referral_id` ascending.
- **Diagnosis objects**: Sort by `code` ascending.
- **Duplicate groups**: Sort by `group_id` ascending; `referral_ids` within each group sorted ascending.
- **Insurance anomalies**: Sort by `anomaly_id` ascending; `patient_ids` and `referral_ids` sorted ascending within each anomaly.

### Date-Ordered Arrays

Encounters are sorted by `date` descending (newest first). Immunizations select the single most recent by `date`.

## Set Semantics

When a template says an array is treated as a set, it means the evaluator ignores the order of elements during comparison. You must still emit a deterministic order (usually alphabetical ascending).

## Distractor Handling

### What Is a Distractor

A distractor is a record that exists in the data but should not appear in a specific output array:

- Inactive clinical records that do not belong in active-key arrays
- Documents unrelated to the merge/referral/transition purpose
- Audit log entries from unrelated entities
- Encounters outside the relevant time window or clinical context

### Where They Go

When the template has dedicated distractor arrays (`excluded_distractors`), populate them. When the template has exclusion arrays (`excluded_encounter_ids`), populate those. Otherwise, simply omit distractors from the relevant output arrays.

## Identity Signal Conventions

### Match Signals (demographics agree)

These signals indicate the two patient records likely represent the same person:

- `same_dob` — identical date of birth
- `same_insurance` — identical insurance ID
- `same_phone` — identical phone number
- `same_given_name` — matching given/first name
- `same_address` — matching address
- `name_variant` — names differ slightly (e.g., full name vs. nickname) but core identity matches
- `shared_external_*` — a shared external provider document ties the records together

### Conflict Signals (demographics disagree)

- `different_given_name` — given/first names differ
- `different_dob` — dates of birth differ
- `different_phone` — phone numbers differ
- `different_insurance` — insurance IDs differ
- `different_address` — addresses differ
- `address_abbreviation` — same address but abbreviation differences (e.g., Street vs. St)
- `given_name_variant` — same person likely, but name format varies
- `opposite_laterality_problem` — one record has left-knee condition, the other has right-knee

### Decision Heuristics

- Multiple strong match signals + minor conflicts → `merge_ready`
- Mixed strong matches and strong conflicts → `needs_manual_review` / `review_hold`
- Strong conflicts outweighing matches → `do_not_merge`

## ICD-10 Validation Conventions

### Chapter Mapping for Service Lines

| Service Line | Expected ICD-10 Chapter |
|--------------|------------------------|
| orthopedics | Musculoskeletal (M00-M99) |
| cardiology | Circulatory (I00-I99) |
| pulmonology | Respiratory (J00-J99) |
| neurology | Nervous System (G00-G99) |
| oncology | Neoplasms (C00-D49) |
| skilled_nursing | Varies by patient condition |

Note: Injury codes (S00-T88) are not in the Musculoskeletal chapter even though they involve bones/joints. For orthopedics, S-codes are out_of_range_chapter.

### Laterality Detection

ICD-10 codes ending in specific digits encode laterality:
- `.1` = right side (e.g., M17.11 = right knee OA)
- `.2` = left side (e.g., M17.12 = left knee OA)
- `.3` or no laterality digit = bilateral or unspecified

Compare the code's laterality against the referral narrative. If the narrative mentions "left" but the code indicates right, flag as `laterality_mismatch`.
