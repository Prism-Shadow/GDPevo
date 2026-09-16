# New Patient Access Verification

## Trigger

Prompt mentions a roster ID (e.g. NPI-JUN-01), patient access verification, insurance/PBM/pharmacy checks, or the intake roster.

## Data Gathering

### 1. Get the roster records

```sql
SELECT * FROM intake_rosters WHERE roster_id = 'ROSTER-ID' ORDER BY patient_id
```

This gives `requested_service_date` and `service_line`. The roster drives which patients to evaluate.

### 2. Collect per-patient data for all roster patients

Gather coverage, PBM, pharmacy, patient demographics, and lifestyle in one batch:

```sql
SELECT p.*, c.*, pb.*, pp.pharmacy_id, ph.network_status as pharmacy_network, l.*
FROM patients p
LEFT JOIN coverage c ON p.patient_id = c.patient_id
LEFT JOIN pbm pb ON p.patient_id = pb.patient_id
LEFT JOIN patient_pharmacy pp ON p.patient_id = pp.patient_id AND pp.preference_rank = 1
LEFT JOIN pharmacies ph ON pp.pharmacy_id = ph.pharmacy_id
LEFT JOIN lifestyle l ON p.patient_id = l.patient_id
WHERE p.patient_id IN ('P001','P002',...)
```

## Business Rules

### insurance_status

| Condition | Value |
|---|---|
| coverage.status = 'active' | valid |
| coverage.status IN ('expired', 'pending') | invalid |
| No coverage row | missing |

If coverage exists but the `service_line` from the roster is not in coverage.service_lines (comma-split), add `excluded_service_line` to blocked reason codes.

### prescription_status

| Condition | Value |
|---|---|
| pbm.status = 'approved' AND pbm.active = 1 | valid |
| pbm.status = 'denied', 'missing', 'policy_mismatch' | invalid |
| pbm.active = 0 | invalid |
| No PBM row | missing |

Blocked reason code mapping:
- pbm.status = 'denied' or pbm.active = 0 → `pbm_invalid`
- pbm.status = 'missing' or no PBM row → `pbm_missing`
- pbm.status = 'policy_mismatch' → `pbm_policy_mismatch`

### pharmacy_status

| Condition | Value |
|---|---|
| Preferred pharmacy network_status = 'in_network' | in_network |
| Preferred pharmacy network_status = 'out_of_network' | out_of_network |
| No preferred pharmacy row | unknown |

Blocked: out_of_network → `pharmacy_out_of_network`, unknown → `pharmacy_unknown`.

### lifestyle_risk

Evaluate from lifestyle row:

| Combined conditions | Risk |
|---|---|
| smoking_status = 'Current' AND exercise_frequency = 'None' | high |
| smoking_status = 'Current' | high |
| alcohol_use = 'Heavy' | high |
| smoking_status = 'Former' AND exercise_frequency IN ('None','Light') | medium |
| alcohol_use = 'Moderate' AND exercise_frequency = 'None' | medium |
| All other combinations | low |

If no lifestyle row, default to low.

### overall_risk

`high` if any of these is true:
- lifestyle_risk = 'high'
- insurance_status IN ('invalid', 'missing')
- prescription_status IN ('invalid', 'missing')
- pharmacy_status IN ('out_of_network', 'unknown')
- patient.address IS NULL
- patient.emergency_contact_present = 0

`medium` if not high and lifestyle_risk = 'medium'.

Otherwise `low`.

### registration_status

| Condition | Status |
|---|---|
| insurance_status = 'valid' AND prescription_status = 'valid' AND pharmacy_status = 'in_network' AND overall_risk != 'high' AND no blocked codes | approved |
| insurance coverage has `excluded_service_line` (service_line not in coverage.service_lines) AND insurance_status = 'invalid' | rejected |
| insurance_status = 'invalid' AND coverage expired (termination_date < requested_service_date) but no excluded_service_line | clinical_review |
| Any non-rejection blocked codes present but no excluded_service_line | clinical_review |
| No data available | hold |

### blocked_reason_codes

Assemble all failure codes:
- `coverage_expired`: coverage.status = 'expired' or termination_date < requested_service_date
- `coverage_pending`: coverage.status = 'pending'
- `excluded_service_line`: service_line not in coverage.service_lines
- `missing_address`: patient.address IS NULL
- `emergency_contact_missing`: patient.emergency_contact_present = 0
- `pbm_invalid`: pbm.status = 'denied' or pbm.active = 0
- `pbm_missing`: no PBM row or pbm.status = 'missing'
- `pbm_policy_mismatch`: pbm.status = 'policy_mismatch'
- `pharmacy_out_of_network`: pharmacy network_status = 'out_of_network'
- `pharmacy_unknown`: no pharmacy row
- `preferred_contact_unavailable`: patient.preferred_contact channel's value is null (e.g. preferred_contact='email' but email IS NULL, or preferred_contact='phone' but phone IS NULL)
- `overall_risk_high`: overall_risk = 'high'

### Cohort Summary

Derive counts from patient results:
- `total_patients`: count of patients processed
- `counts_by_registration_status`: count each status (approved, hold, clinical_review, rejected)
- `counts_by_overall_risk`: count each level (low, medium, high)
- `counts_by_lifestyle_risk`: count each level (low, medium, high)

## Output Shape

Follow `input/payloads/answer_template.json` exactly. Required top-level keys: task_id, roster_id, requested_service_date, service_line, patient_results (sorted ascending by patient_id), cohort_summary.
