# Referral Batch Audit Packet

Use when the task asks to audit a referral batch, typically with a batch ID and service line.

## Input Signals

- A batch ID and service line in the task prompt.
- An answer_template.json with keys: batch, invalid_or_out_of_range_code_referrals, laterality_or_narrative_mismatch_referrals, duplicate_groups, duplicate_tiering_policy, insurance_patient_anomalies, follow_up_queues, action_plan, summary_counts.

## Evidence Gathering Order

1. GET /api/referrals - search/filter by batch_id to get all referrals in the batch.
2. GET /api/icd10/{code} - for every referral diagnosis code.
3. GET /api/patients/{patient_id} - for every unique patient ID in the batch.
4. GET /api/providers/{provider_id} - for the receiving providers on the referrals.

## Reconciliation Rules

### Batch Summary

- record_count: total number of referrals in the batch.
- unique_patient_count: count of distinct patient_id values.

### Invalid or Out-of-Range Code Referrals

- For each referral, look up its diagnosis code in ICD-10.
- If the code chapter is not Musculoskeletal (for an orthopedics batch), flag as out_of_range_chapter.
- If the code is not found in ICD-10, flag as unknown_code.
- expected_chapter: the chapter matching the batch service line (e.g., Musculoskeletal for orthopedics).
- Sort output by referral_id ascending.

### Laterality or Narrative Mismatch Referrals

- Compare the diagnosis code ICD-10 description and laterality against the referral diagnosis_narrative.
- laterality_mismatch: when the ICD-10 description specifies laterality (left/right) that contradicts the narrative.
- narrative_mismatch: when the narrative describes a different condition than the ICD-10 code.
- missing_laterality: when the ICD-10 code implies laterality but the narrative omits it.
- expected_terms: the ICD-10 description terms that the narrative should contain.
- Sort output by referral_id ascending.

### Duplicate Groups

- Identify referrals for the same patient that appear more than once in the batch.
- duplicate_type: same_patient_resubmission.
- recommended_disposition: consolidate_under_original.
- group_id: a stable identifier derived from the shared patient ID.
- Sort duplicate groups by group_id ascending; referral_ids within each group sorted ascending.

### Duplicate Tiering Policy

- All rows in a duplicate group are classified as duplicate-blocker referrals.
- tier_1_duplicate_blocker_referral_ids: all referral IDs in duplicate groups.
- separate_same_patient_referral_ids: any same-patient referrals that are clinically distinct (not duplicate-grouped).

### Insurance Patient Anomalies

- When two different patients share the same insurance ID, flag as shared_insurance_different_patients.
- recommended_disposition: verify_insurance_membership_do_not_merge.
- Sort by anomaly_id ascending.

### Follow-Up Queues

- authorization_missing: referrals where authorization_status is missing or unknown and not not_required.
- authorization_pending: referrals where authorization_status is pending.
- records_request: referrals where office_note_received is false.
- imaging_follow_up: referrals where imaging_status indicates missing or pending imaging.
- Each queue sorted by referral_id ascending.

### Action Plan

- Tier 1 (Immediate): referrals with urgent coding issues (invalid code, laterality mismatch with impending surgery, duplicate blocker).
- Tier 2 (Short-term): referrals with routine coding/auth/document blockers.
- Tier 3 (Administrative): referrals needing document completion only.
- owner_provider_id: the receiving provider on the referral. When multiple providers exist in the batch, distribute evenly across them.
- Sort each tier by referral_id ascending.

### Summary Counts

- Derive each count from the arrays populated above.
- validated_ready_no_follow_up_count: count of referrals with no issues in any category.

## Output Shape

Follow answer_template.json exactly. All referral-object arrays sorted by referral_id ascending. All ID arrays sorted ascending.
