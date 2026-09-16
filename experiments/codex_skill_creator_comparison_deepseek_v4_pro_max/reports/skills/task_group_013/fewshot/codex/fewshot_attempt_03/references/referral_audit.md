# Referral Readiness Audit

## Trigger

Prompt mentions a batch ID with referrals (e.g. ORTHO-JUN-01, PULM-JUN-02), ICD review, duplicate handling, or referral readiness.

## Data Gathering

### 1. Fetch all referrals in the batch

```sql
SELECT * FROM referrals WHERE batch_id = 'BATCH-ID' ORDER BY referral_id
```

### 2. Fetch ICD metadata for every unique icd10_code in the batch

Use the `/icd/{code}` endpoint or:
```sql
SELECT * FROM icd_codes WHERE code IN ('CODE1','CODE2',...)
```

### 3. For duplicate and insurance checks, fetch patient data

Use `/referrals/{id}` for per-referral patient/ICD/docs detail, or SQL join:
```sql
SELECT r.*, p.*, i.* 
FROM referrals r
JOIN patients p ON r.patient_id = p.patient_id
JOIN icd_codes i ON r.icd10_code = i.code
WHERE r.batch_id = 'BATCH-ID'
ORDER BY r.referral_id
```

## Business Rules

### readiness_status

| Condition | Status |
|---|---|
| No issues at all | ready |
| Has `auth_blocker` or `missing_records` or `missing_imaging` | blocked |
| Has `shared_insurance_anomaly` (but not blocked reasons) | admin_followup |
| Has ICD/narrative/laterality issues (but not blocked reasons) | under_review |
| Has `duplicate_referral` or `already_scheduled` (but not blocked reasons) | under_review |

### issue_codes

Determine for each referral:

- **icd_chapter_mismatch**: The ICD code's `chapter` does not match the expected chapter for the referral's `service_line`:
  - orthopedics → M00-M99
  - pulmonary → J00-J99
  - cardiology → I00-I99
  (Check: if ICD chapter != service_line's expected chapter range, flag it.)

- **narrative_mismatch**: The `diagnosis_description` or `referral_reason` text conflicts with the ICD code's description. (Check text fields for inconsistency.)

- **laterality_mismatch**: ICD `laterality` is non-null and contradicts notes or referral data.

- **duplicate_referral**: Same `patient_id` appears more than once in the batch, or same `insurance_id` AND same `patient_id` across different referrals.

- **shared_insurance_anomaly**: Same `insurance_id` appears across different `patient_id` values. Flag both referrals.

- **missing_records**: `records_received` = 0.

- **missing_imaging**: `imaging_received` = 0.

- **auth_blocker**: `auth_required` = 1 AND `auth_status` IN ('denied', 'pending', 'not_submitted').

- **already_scheduled**: `appointment_scheduled` = 1 AND `appointment_date` is set.

### priority_tier

| Condition | Tier |
|---|---|
| urgency = 'urgent' AND has any issues | tier_1_immediate |
| readiness_status = 'blocked' (non-urgent) | tier_2_short_term |
| readiness_status = 'under_review' (non-urgent) | tier_2_short_term |
| readiness_status = 'admin_followup' | tier_3_administrative |
| readiness_status = 'ready' | null |

### ICD Discrepancies

For each referral flagged with `icd_chapter_mismatch`, record:
- referral_id
- icd10_code
- issue_types (at minimum ["icd_chapter_mismatch"])
- observed_chapter: the ICD's actual chapter
- expected_chapter: the expected chapter for the service_line

### Duplicate Groups

Group referrals by same `patient_id`, same `insurance_id`. For each group:
- group_id: `DUP-{BATCH}-{seq}` (three-digit padded)
- referral_ids: sorted list
- patient_id
- primary_referral_id: earliest by date_received, or first by referral_id
- recommendation: `consolidate_to_primary`

### Shared Insurance Anomalies

Group referrals by `insurance_id` where the same insurance_id has multiple different patient_ids:
- insurance_id
- referral_ids: sorted
- patient_ids: sorted
- disposition: `verify_distinct_patient_policy_id`

### Blocker Sets

- `missing_records`: list of referral_ids where records_received = 0, sorted
- `missing_imaging`: list of referral_ids where imaging_received = 0, sorted
- `auth_blockers`: list of { referral_id, auth_status } where auth_required=1 and auth_status in (denied, pending, not_submitted), sorted by referral_id

### ready_to_schedule

List of referral_ids where readiness_status = 'ready', sorted ascending.

### Action Plan

For each referral with issues, produce:
- referral_id
- priority_tier
- action_codes (unordered set):
  - icd_chapter_mismatch → `request_corrected_icd`
  - narrative_mismatch → `confirm_narrative`
  - laterality_mismatch → `confirm_laterality`
  - duplicate_referral → `consolidate_duplicate`
  - shared_insurance_anomaly → `verify_insurance_id`
  - missing_records → `request_records`
  - missing_imaging → `request_imaging`
  - auth_blocker → `resolve_authorization`
  - already_scheduled → `review_existing_appointment`

### Summary

- `total_referrals`: count
- `ready_to_schedule_count`: count of ready referrals
- `follow_up_count`: total - ready
- `counts_by_urgency`: count by urgent, routine, admin
- `counts_by_readiness_status`: count by ready, blocked, under_review, admin_followup
- `counts_by_urgency_and_status`: cross-tabulation list, sorted urgency then status; omit zero-count combos
- `issue_counts`:
  - icd_discrepancy_referrals: count distinct referrals with ICD issues
  - duplicate_groups: count of duplicate groups
  - shared_insurance_anomalies: count of anomaly groups
  - missing_records_referrals: count distinct referrals with missing records
  - missing_imaging_referrals: count distinct referrals with missing imaging
  - auth_blocker_referrals: count distinct referrals with auth blockers

## Output Shape

Follow `input/payloads/answer_template.json` exactly. Required top-level keys: task_id, batch_id, referral_reviews, icd_discrepancies, duplicate_groups, shared_insurance_anomalies, blocker_sets, ready_to_schedule, action_plan, summary.
