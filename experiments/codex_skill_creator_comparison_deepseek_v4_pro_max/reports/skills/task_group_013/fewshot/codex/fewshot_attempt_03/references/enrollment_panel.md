# Chronic Care Enrollment Panel

## Trigger

Prompt mentions a program code (e.g. DMHTN-2026A), chronic care, enrollment panel, candidate eligibility, or program enrollment.

## Data Gathering

### 1. Fetch program candidates

Use the endpoint `GET /programs/{code}/candidates` or SQL:
```sql
SELECT * FROM program_candidates WHERE program_code = 'PROGRAM' ORDER BY patient_id
```

### 2. Fetch chart data for every candidate

For each candidate, call `GET /chart/{patient_id}` or use SQL:
```sql
SELECT ca.*, cl.* 
FROM chart_artifacts ca
JOIN clinical_history cl ON ca.patient_id = cl.patient_id
WHERE ca.patient_id IN ('P026','P027',...)
```

The chart endpoint returns: patient, clinical_history (chronic_conditions, surgeries, medication_count, allergy_count, recent_hospitalization, risk_flags), chart_artifacts (by type), meds_allergies, active_problems, recent_vitals_labs.

## Business Rules

### eligibility

A candidate is eligible (`eligible: true`) when ALL of these hold:
- target_condition = 'diabetes_hypertension' (matches program)
- clinical_history shows relevant chronic conditions (contains diabetes/hypertension codes or the patient has both conditions)
- chart_artifacts have reasonable coverage (not a completely empty chart)

Ineligible (`eligible: false`) when:
- `target_condition` does not match program (e.g. 'copd' for DMHTN)
- No active DM/HTN diagnosis in chart / active_problems
- Chart does not support the target condition

### enrollment_status

| Condition | Status |
|---|---|
| eligible AND consent_status = 'signed' AND chart is active (existing_chart=1, artifacts present) | enroll |
| eligible AND (consent_status = 'missing' OR chart has stale/missing artifacts) | hold |
| consent_status = 'declined' OR not eligible | reject |

### reason_codes

Assemble from analysis:

- `meets_dmhtn_criteria`: eligible, target_condition matches
- `recent_hospitalization_high_touch`: clinical_history.recent_hospitalization = 1
- `low_adherence_high_touch`: adherence_score < 50
- `ckd_biweekly_monitoring`: chronic_conditions includes renal/CKD indicators
- `recent_ed_high_touch`: risk_flags indicate recent ED visit
- `consent_declined`: consent_status = 'declined'
- `consent_missing`: consent_status = 'missing'
- `chart_not_active`: existing_chart = 0 or chart_artifacts essentially empty
- `stale_active_problems`: active_problems artifact stale or missing
- `missing_recent_vitals`: vitals artifact stale or missing
- `missing_recent_labs`: labs artifact stale or missing
- `missing_medication_list`: medications artifact stale or missing
- `wrong_target_condition`: target_condition does not match program
- `missing_active_dmhtn_diagnosis`: no DM/HTN diagnosis in chart / active_problems

### follow_up_cadence

| Condition | Cadence |
|---|---|
| recent_hospitalization_high_touch OR low_adherence_high_touch OR recent_ed_high_touch | weekly |
| ckd_biweekly_monitoring | biweekly |
| standard enrollment (meets criteria, no flags) | monthly |
| hold status | deferred |
| reject status | none |

### missing_chart_artifacts

List artifact types that are missing or stale from chart_artifacts. Possible values: chart_record, active_problems, vitals, labs, medications, consent. Treat as unordered set.

### outreach_channel

From program_candidates.preferred_outreach. Map:
- portal → 'portal'
- phone → 'phone'
- email → 'email'
- sms → 'sms'

If no preferred_outreach, default to 'none'.

### initial_monitoring_package

| Condition | Package |
|---|---|
| weekly follow_up (high touch) | high_touch_dm_htn |
| biweekly or monthly follow_up (standard) | standard_dm_htn |
| hold status | deferred |
| reject status | not_applicable |

Components:
- **high_touch_dm_htn**: bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup
- **standard_dm_htn**: bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation (add medication_reconciliation only if medication_count > 0 or medications artifact present)
- **deferred**: consent_packet, chart_update_request
- **not_applicable**: empty list

first_checkin_days:
- weekly → 7
- biweekly → 14
- monthly → 30
- deferred → null
- not_applicable → null

### as_of_date

Use the current date (from the task or system). Format YYYY-MM-DD.

### Summary

Count from patient results:
- total_candidates
- eligible_count (where eligible = true)
- ineligible_count (where eligible = false)
- status_counts: enroll, hold, reject
- follow_up_counts: weekly, biweekly, monthly, deferred, none
- outreach_counts: phone, portal, sms, email, none
- monitoring_package_counts: standard_dm_htn, high_touch_dm_htn, deferred, not_applicable

## Output Shape

Follow `input/payloads/answer_template.json` exactly. Required top-level keys: program_code, as_of_date, patients (sorted ascending by patient_id), summary.
