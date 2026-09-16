# Clinical Quality Rules

These rules cover the domain judgments needed when API data must be interpreted
rather than directly copied into the answer template.

## Merge Disposition Rules

### ready_to_merge / merge_ready
Declare when:
- The duplicate candidate status is `confirmed_duplicate`
- Identity match signals are strong (same DOB, same insurance, shared phone,
  shared external clinical documents)
- Conflict signals are minor (address abbreviation, given name variant —
  things consistent with data entry differences rather than different people)
- One patient record is clearly the canonical target (richer clinical history,
  marked as merge target by the duplicate system)

### needs_review / merge_ready_with_conflict_review / needs_manual_review
Declare when:
- The duplicate candidate status is `needs_review`
- Conflicts involve DOB, insurance ID, or opposite-laterality clinical problems
  (e.g. one patient has right knee OA, the other has left knee OA — unlikely
  to be the same person's records if both are active)
- Identity signals are mixed: some strong matches but at least one fundamental
  conflict

### do_not_merge
Declare when:
- The candidate is explicitly marked `not_duplicate`
- Core identity signals (DOB, insurance) conflict with no resolution
- The candidate system recommends against merging

## Active List Reconciliation

The duplicate candidate preview may include `active_condition_preview_keys`,
`active_medication_preview_keys`, and `active_allergy_preview_keys`. These are
the system's precomputed union from both patient shells.

You must also fetch each patient's own active-list endpoints. Any key present
in a patient endpoint but missing from the duplicate preview represents a record
the preview missed. These go into `*_keys_added_from_active_endpoints`.

The `authoritative_source` for reconciliation is always
`patient_active_list_endpoints_over_duplicate_preview` — the patient endpoints
are the ground truth.

## Risk Flag Derivation (Orthopedic Surgery Transitions)

Derive risk flags from patient active clinical lists and encounters. The
following are common trigger patterns:

| Risk flag | Trigger |
|---|---|
| `cognitive_memory_loss` | Active condition key `memory_loss` or equivalent |
| `fall_risk_note_required` | Active bilateral lower-extremity OA conditions (hip and knee OA together), especially with pain medication |
| `hypertension` | Active condition key `hypertension` |
| `insulin_dependent_diabetes` | Active condition `diabetes_type_2` plus active insulin medication |
| `latex_allergy` | Active allergy `latex` |
| `perioperative_glucose_plan_needed` | `insulin_dependent_diabetes` is already flagged; this is always co-present |

## Referral Code Validation

### Chapter Validation
Orthopedic referrals should map to Musculoskeletal chapter codes. Codes in
Injury (S codes), Respiratory (J codes), Circulatory (I codes), or other
non-MSK chapters are out-of-range for an orthopedic referral.

### Laterality Validation
Compare the ICD-10 descriptor's laterality to the referral narrative:
- If the code description says "left knee" but the narrative says "right knee,"
  that is a `laterality_mismatch`.
- If the code encodes laterality (by ICD-10 convention) but the narrative omits
  it ("meniscus tear" vs "left medial meniscus tear"), that is `missing_laterality`.
- If the code description is anatomically inconsistent with the narrative
  (code is for knee, narrative describes lumbar spine), that is a `narrative_mismatch`.

### Narrative Match
Even when chapters and laterality align, check whether the narrative description
is consistent with the ICD-10 code's clinical meaning. "Lumbar radiculopathy"
does not match a meniscus tear code regardless of chapter.

## Duplicate Referral Detection

Two referrals form a duplicate group when:
- Same patient
- Same service line
- Same or overlapping diagnosis
- One appears to be a resubmission of the other (e.g. `REF-XYZ-019-DUP` is a
  variant of `REF-XYZ-004`)

When a duplicate group exists, assign both referrals to Tier 1 as duplicate
blockers and recommend `consolidate_under_original`.

## Insurance Anomaly Handling

When two different patients share the same insurance ID, flag as
`shared_insurance_different_patients`. Do not merge the referrals — this is an
insurance membership verification issue, not a duplicate patient issue.

When the same patient has two referrals that are clearly separate clinical
reviews (different body parts, different dates, different providers), flag as
`same_patient_separate_clinical_referrals` — these are not duplicates.

## Authorization and Document Follow-Up

### Authorization Queue Assignment
- `authorization_missing`: referral has no authorization record and
  authorization status is not `approved` or `not_required`
- `authorization_pending`: referral authorization status is `pending`

### Records Request Queue
Include referrals where `office_note_received` is false.

### Imaging Follow-Up Queue
Include referrals where imaging (echo for cardiology, MRI/X-ray for orthopedics)
is missing or pending.

## Tier Assignment

| Tier | Criteria |
|---|---|
| Tier 1 | Urgent coding issues (unknown codes, codes on wrong-service-line referrals that are also marked urgent) and duplicate blockers |
| Tier 2 | Routine coding mismatches, missing authorization, missing documents — non-urgent referrals with quality issues that block processing |
| Tier 3 | Administrative document completion only — referrals that are otherwise valid but need paperwork follow-up |

Referrals with no issues go into the `validated_ready_no_follow_up` count.

## Packet Readiness

| Status | When to use |
|---|---|
| `ready` | All required data is present, all validations pass, no blockers |
| `ready_with_review_note` / `ready_with_risk_flags` | Packet is sendable but contains flags the recipient should review |
| `blocked` / `not_ready` | Missing required data, disclosure not permitted, or an unresolvable quality issue |

## Service Request Quality

### Service Code Validation
Validate the service code against `/api/service-codes/{code}`. The code is valid
if the endpoint returns a match with a service_line appropriate to the request.

### SBAR Coverage
Parse the service request's narrative/text body for:
- **Situation**: A statement of the current clinical situation
- **Background**: Relevant patient history
- **Assessment**: Clinical findings or diagnosis
- **Recommendation**: The requested action

A section is present if the text contains a recognizable header or content
matching that SBAR component. The `complete` flag is true only when all four
are present.

### Reason Code Validation
For each reason code on a service request:
1. Validate it against `/api/icd10/{code}` — the code must exist
2. Check the chapter is appropriate for the service line
3. Check whether the code matches the patient's active conditions or encounter
   diagnoses (cross-reference patient evidence)
