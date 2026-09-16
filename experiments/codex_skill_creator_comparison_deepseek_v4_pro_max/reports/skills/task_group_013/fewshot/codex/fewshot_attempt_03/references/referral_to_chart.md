# Referral-to-Chart Activation

## Trigger

Prompt mentions combined referral + chart workflow (e.g. PULM-JUN-02), chart activation, correspondence queues, or a batch that needs both referral reconciliation and chart artifact preparation.

## Data Gathering

### 1. Fetch all referrals in the batch

```sql
SELECT * FROM referrals WHERE batch_id = 'BATCH-ID' ORDER BY referral_id
```

### 2. Fetch ICD metadata for each unique icd10_code

Use `/icd/{code}` endpoint or icd_codes SQL join.

### 3. Fetch patient charts for all referral patients

Call `GET /chart/{patient_id}` for each. The chart response includes:
- patient (existing_chart, address, preferred_contact, etc.)
- clinical_history (chronic_conditions, recent_hospitalization, etc.)
- chart_artifacts (list by type: demographics, active_problems, medications, allergies, vitals, labs, consent)
- meds_allergies
- active_problems
- recent_vitals_labs

### 4. Fetch documents linked to each referral

```sql
SELECT * FROM documents WHERE referral_id IN (...) AND content_tag = 'referral_document'
```

Or use `GET /referrals/{id}` which includes linked documents.

## Business Rules

### readiness_status and blocker_codes (per referral)

| Condition | readiness_status | blocker_codes |
|---|---|---|
| No issues at all | ready | [] |
| clinical_code_discrepancy only | under_review | ["clinical_code_discrepancy"] |
| authorization_blocked or records_missing | blocked | ["authorization_blocked" and/or "records_missing"] |
| duplicate_review (possible duplicate, same patient) | under_review | ["duplicate_review"] |
| scheduled_before_clearance | blocked | ["scheduled_before_clearance"] + any others |
| imaging_missing | blocked | ["imaging_missing"] + any others |

Detailed blocker derivation:

- **clinical_code_discrepancy**: ICD chapter does not match service_line's expected chapter, OR ICD service_family differs from referral.service_line. Check:
  - orthopedics ↔ M00-M99
  - pulmonary ↔ J00-J99, R00-R99 (some respiratory codes)
  - cardiology ↔ I00-I99
  - neurology ↔ G00-G99

  Also flag if referral_reason text contradicts the ICD description (e.g. "pain evaluation" for a code that's not pain-related).

- **records_missing**: records_received = 0
- **imaging_missing**: imaging_received = 0
- **authorization_blocked**: auth_required = 1 AND auth_status IN ('denied', 'pending')
- **duplicate_review**: notes contains 'possible duplicate' or same insurance_id across different referrals in batch
- **scheduled_before_clearance**: appointment_scheduled = 1 AND readiness would otherwise be blocked/under_review

### clinical_code_discrepancy_referrals

List referral_ids (ascending) flagged with clinical_code_discrepancy.

### blocker_sets

- **authorization**: referral_ids (ascending) where authorization_blocked
- **records**: referral_ids (ascending) where records_missing
- **imaging**: referral_ids (ascending) where imaging_missing

### duplicate_handling

- **duplicate_groups**: For referrals flagged as possible duplicates:
  - group_id: DUP-{BATCH}-{seq}
  - referral_ids: sorted ascending
  - keep_referral_id: the one that should be retained (earliest date_received, or first by referral_id)

- **cleared_duplicate_review_referrals**: Referrals that had duplicate notes but were determined NOT to be true duplicates (e.g., same insurance_id across different patients who are confirmed distinct). Include here any referral that was initially flagged for duplicate review but the review determined they are legitimate separate referrals.

### ready_referral_chart_needs

For each referral with readiness_status = 'ready':

| Condition | chart_action | artifacts_to_create |
|---|---|---|
| existing_chart = 0 | create_chart | All missing artifacts from the standard set |
| existing_chart = 1 but artifacts missing | update_chart | Only the missing artifacts |

Standard chart artifact set to check: demographics, active_problems, medications, allergies, vitals, labs, consent.

Check each artifact type in the chart. If the artifact is missing (not present in chart_artifacts or status = 'missing' or 'stale'), add to artifacts_to_create.

Sort artifacts_to_create alphabetically.

If no artifacts are needed, chart_action should still be 'update_chart' (or 'no_chart_action' only if the template allows it).

### correspondence_queue

For referrals that are NOT ready:

| Condition | template_type | reason_codes |
|---|---|---|
| clinical_code_discrepancy (service family mismatch) | clinical_code_clarification | ["wrong_service_family"] |
| clinical_code_discrepancy (reason/description mismatch) | clinical_code_clarification | ["clinical_reason_mismatch"] |
| authorization_blocked OR records_missing | auth_records_request | ["authorization_denied"] + ["records_missing"] (if applicable) |
| duplicate_review | duplicate_resolution | ["duplicate_review"] |
| appointment_scheduled before clearance | appointment_hold_notice | ["appointment_already_scheduled"] + any other applicable codes |

### priority_order

For non-ready referrals only, rank by priority:

1. Urgent referrals with any issues → tier_1_immediate (rank first)
2. Blocked referrals (non-urgent) → tier_2_short_term
3. Under_review referrals → tier_2_short_term

Within same tier, sort by referral_id ascending.

Assign rank starting from 1.

## Output Shape

Follow `input/payloads/answer_template.json` exactly. Required top-level keys: batch_id, readiness_by_referral, clinical_code_discrepancy_referrals, blocker_sets, duplicate_handling, ready_referral_chart_needs, correspondence_queue, priority_order.
