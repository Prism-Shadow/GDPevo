## Referral batch audit

### Objective

Produce a normalized batch audit for a set of referrals in a given service line. Identify invalid diagnosis codes, laterality/narrative mismatches, duplicate groups, insurance anomalies, follow-up queues, and tiered action plans with summary counts.

### Step-by-step

#### 1. Fetch the referral batch

`GET /api/referrals`

Filter the returned bundle for referrals matching the target `batchId`. Count total referral rows and unique patient IDs for the batch summary.

#### 2. For each referral, fetch supporting records

For every referral in the batch, fetch:
- `GET /api/patients/{patient_id}` — patient demographics and insurance ID
- `GET /api/icd10/{diagnosis_code}` — ICD-10 code validation
- `GET /api/providers/{provider_id}` — receiving provider info

Cache ICD-10 lookups to avoid redundant calls for the same code.

#### 3. Classify invalid or out-of-range diagnosis codes

A referral diagnosis is invalid/out-of-range when:
- The ICD-10 code's `chapter` does not match the expected chapter for the service line
- For orthopedics, the expected chapter is **Musculoskeletal**
- For cardiology, the expected chapter is **Circulatory**

Injury codes (S/T prefix) map to the Injury chapter and are out-of-range for both orthopedic and cardiology referrals.

Each flagged referral records: `referral_id`, `patient_id`, `diagnosis_code`, `actual_chapter`, `expected_chapter`, `issue_type` (`out_of_range_chapter`).

Sort this array by `referral_id` ascending.

#### 4. Detect laterality or narrative mismatches

For every referral, compare the `diagnosis_narrative` (referral's human-readable reason) with the ICD-10 code's `description` and `laterality`:

- **laterality_mismatch**: the ICD-10 code specifies left/right/bilateral but the narrative indicates a different side. Example: code `M17.12` (left knee OA) with narrative "right knee osteoarthritis".
- **narrative_mismatch**: the narrative describes a different condition or body site than the ICD-10 code. Example: code `S83.241A` (right medial meniscus tear) with narrative "lumbar radiculopathy".
- **missing_laterality**: the ICD-10 code requires laterality but the narrative omits it. Example: code `S83.242A` with narrative "meniscus tear" (no side specified).

Populate `expected_terms` with the terms from the ICD-10 directory that match the code's clinical meaning (the `description` field and any laterality cues).

Sort this array by `referral_id` ascending.

#### 5. Group duplicate referrals by patient

Identify referrals that share the same `patient_id` and have the same or substantially similar clinical intent. These are same-patient resubmissions.

Create a `duplicate_group` entry with:
- `group_id`: a stable ID derived from the patient (e.g., `DUP-REF-MAR-P{patient_id}`)
- `patient_id`
- `referral_ids`: sorted ascending
- `duplicate_type`: `same_patient_resubmission`
- `recommended_disposition`: `consolidate_under_original` (keep the earlier referral, supersede the duplicate)

Sort duplicate groups by `group_id` ascending.

#### 6. Apply duplicate tiering policy

All referral IDs in a duplicate group are assigned to the duplicate-blocker tier. List them in `tier_1_duplicate_blocker_referral_ids`.

If there are separate same-patient referrals that are clinically distinct (not duplicates), list them in `separate_same_patient_referral_ids`.

#### 7. Detect insurance anomalies

Find cases where different patients share the same insurance ID. This may indicate:
- Family members on the same plan (verify, do not merge)
- True insurance data issues

Create an `insurance_patient_anomalies` entry with:
- `anomaly_id`: stable ID (e.g., `ANOM-MAR-INS-{insurance_id}`)
- `anomaly_type`: `shared_insurance_different_patients` or `same_patient_separate_clinical_referrals`
- `patient_ids`: sorted ascending
- `referral_ids`: sorted ascending
- `insurance_id`
- `recommended_disposition`

Sort anomalies by `anomaly_id` ascending.

#### 8. Build follow-up queues

Classify each referral into follow-up queues based on its status fields:

- **authorization_missing**: referral has no authorization on file
- **authorization_pending**: authorization status is "pending"
- **records_request**: office note is missing (`officeNoteMissing = true`)
- **imaging_follow_up**: imaging status is "missing" or "pending"

Sort each queue's referral IDs ascending.

#### 9. Assign Tier 1/2/3 action plans

**Tier 1 (immediate)**: Referrals with `urgent = true` OR referrals flagged as duplicate-blockers (in a duplicate group). Primary reason: `urgent_coding_or_duplicate_blocker`.

**Tier 2 (short-term)**: Routine referrals with coding issues, authorization gaps, or document gaps. Primary reason: `routine_coding_auth_or_document_blocker`. These are non-urgent referrals that have at least one follow-up queue entry.

**Tier 3 (administrative)**: Routine referrals with only administrative document completion needs (records or imaging but no code/auth issues). Primary reason: `administrative_document_completion`.

Assign an `owner_provider_id` to each action plan entry based on the referral's assigned provider.

Sort each tier array by `referral_id` ascending.

#### 10. Compute summary counts

Count:
- `total_referral_rows`: total referrals in batch
- `unique_patients`: distinct patient IDs
- `urgent_count`: referrals with urgent = true
- `routine_count`: referrals with urgent = false
- `invalid_or_out_of_range_count`: count of entries in the invalid/out-of-range array
- `mismatch_count`: count of entries in the laterality/narrative mismatch array
- `duplicate_group_count`: count of duplicate groups
- `insurance_patient_anomaly_count`: count of insurance anomalies
- `authorization_missing_count`, `authorization_pending_count`: from follow-up queues
- `records_request_count`, `imaging_follow_up_count`: from follow-up queues
- `tier_1_count`, `tier_2_count`, `tier_3_count`: from action plans
- `validated_ready_no_follow_up_count`: referrals with no issues flagged in any queue or plan

### Output shape

Top-level keys: `batch`, `invalid_or_out_of_range_code_referrals`, `laterality_or_narrative_mismatch_referrals`, `duplicate_groups`, `duplicate_tiering_policy`, `insurance_patient_anomalies`, `follow_up_queues`, `action_plan`, `summary_counts`.

All referral-object arrays must be sorted by `referral_id` ascending. ID arrays must be sorted ascending.
