# Family B — Referral Readiness / Batch Audit

**Recognize it by:** prompt asks to *audit a referral batch* for scheduling
(e.g. `ORTHO-JUN-01`), covering coding discrepancies, duplicates, shared
insurance, missing records/imaging, authorization, ready-to-schedule, priority
tiers, action plan, summary counts. Template top-level keys include
`referral_reviews, icd_discrepancies, duplicate_groups,
shared_insurance_anomalies, blocker_sets, ready_to_schedule, action_plan,
summary`.

**Scope:** `referrals WHERE batch_id=<batch>`, ordered ascending `referral_id`.
Join `icd_codes` on `icd10_code`. `task_id`, `batch_id` echoed.
The batch's `service_line` (e.g. orthopedics) fixes the *expected ICD chapter*
(orthopedics→`M00-M99`, pulmonary→`J00-J99`, cardiology→`I00-I99`).

## Per-referral issue_codes (each an independent predicate; collect all)
- **icd_chapter_mismatch**: `icd_codes.chapter` of the referral's code ≠ the
  expected chapter for the batch service line. **Chapter-based, not
  service_family** (a code can have the right `service_family` but a wrong
  chapter, e.g. an injury `S00-T88` code on an orthopedics referral → mismatch).
- **narrative_mismatch** (INFERRED): `diagnosis_description` contradicts
  `icd_codes.description`. Does not fire when `diagnosis_description` is the
  generic `"specialty consultation"`.
- **laterality_mismatch** (INFERRED): a side stated in the narrative conflicts
  with `icd_codes.laterality`.
- **duplicate_referral**: referral is a member of a **structural duplicate
  group** = ≥2 in-batch referrals with the same `patient_id` AND same
  `icd10_code`. (Here the `notes='possible duplicate'` flag is a *distractor* —
  do not use it for grouping in this family; use structural matching.) All group
  members get the code.
- **shared_insurance_anomaly**: the referral's `insurance_id` appears on ≥2
  in-batch referrals belonging to **different** `patient_id`s.
- **missing_records**: `records_received == 0`.
- **missing_imaging**: `imaging_received == 0`.
- **auth_blocker**: `auth_required == 1` AND `auth_status != 'approved'`
  (i.e. in {pending, denied, not_submitted}). `not_required`/`approved` never block.
- **already_scheduled**: `appointment_scheduled == 1`.

## readiness_status (exactly one; first match wins)
- BLOCKING = {missing_records, missing_imaging, auth_blocker}
- REVIEW = {icd_chapter_mismatch, narrative_mismatch, laterality_mismatch,
  duplicate_referral, already_scheduled}
- ADMIN = {shared_insurance_anomaly}
1. `blocked` if issue ∩ BLOCKING ≠ ∅
2. else `under_review` if issue ∩ REVIEW ≠ ∅
3. else `admin_followup` if only shared_insurance_anomaly
4. else `ready`

## priority_tier
- `null` in `referral_reviews` iff `ready` (and such referrals are OMITTED from
  `action_plan`).
- `tier_3_administrative` if `readiness_status=='admin_followup'` (or `urgency=='admin'`).
- else `tier_1_immediate` if `urgency=='urgent'`.
- else `tier_2_short_term`.

## icd_discrepancies (ascending referral_id)
One row per referral with any of {icd_chapter_mismatch, narrative_mismatch,
laterality_mismatch}: `{referral_id, icd10_code, issue_types (subset that fired),
observed_chapter = icd_codes.chapter, expected_chapter = service-line chapter}`.

## duplicate_groups (ascending group_id)
Group in-batch referrals by (patient_id, icd10_code); groups of size ≥2:
- `group_id` = `"DUP-" + <batch_id> + "-" + NNN` (1-based, zero-padded to 3).
- `referral_ids` ascending; `patient_id` = shared patient.
- `primary_referral_id` = earliest `date_received`, tie-break lowest `referral_id`.
- `recommendation` = `consolidate_to_primary` when members share the clinical
  content (same code/reason); `keep_separate` otherwise (INFERRED).

## shared_insurance_anomalies (ascending insurance_id)
For each `insurance_id` on ≥2 in-batch referrals with ≥2 distinct patients:
`{insurance_id, referral_ids (asc), patient_ids (asc distinct),
disposition='verify_distinct_patient_policy_id'}`. Same-patient sharing →
`legitimate_duplicate_same_patient` and is generally not emitted / adds no issue
code (INFERRED).

## blocker_sets
- `missing_records`: referral_ids with `records_received==0` (asc).
- `missing_imaging`: referral_ids with `imaging_received==0` (asc).
- `auth_blockers`: `[{referral_id, auth_status(raw)}]` for auth_blocker referrals (asc).

## ready_to_schedule
referral_ids with empty issue set (`readiness_status=='ready'`), ascending.

## action_plan (ascending referral_id; referrals with ≥1 issue only)
`{referral_id, priority_tier(non-null), action_codes}` where each issue maps to:
- icd_chapter_mismatch→`request_corrected_icd`
- narrative_mismatch→`confirm_narrative`; laterality_mismatch→`confirm_laterality`
- duplicate_referral→`consolidate_duplicate`
- shared_insurance_anomaly→`verify_insurance_id`
- missing_records→`request_records`; missing_imaging→`request_imaging`
- auth_blocker→`resolve_authorization`
- already_scheduled→`review_existing_appointment`

## summary
- `total_referrals`; `ready_to_schedule_count`=len(ready_to_schedule);
  `follow_up_count`=total−ready.
- `counts_by_urgency`: **raw** tally of `referrals.urgency` over {urgent, routine,
  admin} (this is NOT the priority_tier — a routine admin-only referral still
  counts as routine here).
- `counts_by_readiness_status`: tally over {ready, blocked, under_review,
  admin_followup}.
- `counts_by_urgency_and_status`: one `{urgency, readiness_status, count}` per
  **occurring** (count≥1) pair, ordered by urgency then readiness_status
  (both alphabetical: admin<routine<urgent; admin_followup<blocked<ready<under_review).
- `issue_counts`: `icd_discrepancy_referrals`=len(icd_discrepancies),
  `duplicate_groups`=len(duplicate_groups),
  `shared_insurance_anomalies`=len(shared_insurance_anomalies),
  `missing_records_referrals`/`missing_imaging_referrals`/`auth_blocker_referrals`
  = len of the corresponding blocker_sets list.
