# Portal Data Model — Cedar Ridge Intake Coordination

The portal is a read-only SQLite database exposed through the SQL interface listed in `environment_access.md`, plus per-resource GET endpoints. The schema below is the reference map discovered during skill development. **Always re-verify it** by re-running the introspection queries against the current portal before relying on specific columns — schemas can shift.

## Introspection queries (run first)

```sql
-- list every table
SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;

-- full CREATE TABLE for every table
SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;
```

## Table map (reference — verify)

| Table | Purpose | Key columns |
|---|---|---|
| `patients` | Patient identity & contact | `patient_id` (PK), `existing_chart`, `preferred_contact`, `phone`, `email`, `address`, `emergency_contact_present` |
| `intake_rosters` | Roster → patient + service date/line | `roster_id`, `patient_id`, `requested_service_date`, `service_line` |
| `coverage` | Insurance coverage | `patient_id`, `payer`, `policy_number`, `network_status`, `service_lines` (csv), `status` (active/expired/pending), `effective_date`, `termination_date` |
| `pbm` | Pharmacy benefit manager | `patient_id`, `policy_number`, `active`, `formulary_status`, `status` (approved/pending/rejected), `specialty_required` |
| `pharmacies` | Pharmacy directory | `pharmacy_id` (PK), `name`, `network_status` |
| `patient_pharmacy` | Patient → preferred pharmacies | `patient_id`, `pharmacy_id`, `preference_rank` (1 = top) |
| `lifestyle` | Lifestyle factors | `patient_id` (PK), `smoking_status`, `alcohol_use`, `exercise_frequency`, `sleep_hours` |
| `clinical_history` | Clinical acuity | `patient_id` (PK), `chronic_conditions` (csv), `medication_count`, `allergy_count`, `recent_hospitalization`, `risk_flags` (csv) |
| `chart_artifacts` | Chart artifact status | `patient_id`, `artifact_type`, `status` (current/stale), `last_updated` |
| `referrals` | Referral records | `referral_id` (PK), `batch_id`, `service_line`, `patient_id`, `icd10_code`, `diagnosis_description`, `referral_reason`, `urgency`, `records_received`, `imaging_received`, `auth_required`, `auth_status`, `appointment_scheduled`, `insurance_id`, `notes` |
| `icd_codes` | ICD-10 metadata | `code` (PK), `description`, `chapter`, `service_family`, `laterality` |
| `transfer_requests` | Transfer requests | `transfer_id` (PK), `batch_id`, `patient_id`, `referring_facility`, `requested_start_date`, `requested_end_date`, `modality`, `days_requested`, `chair_window`, `transportation` |
| `documents` | Packet documents | `document_id` (PK), `patient_id`, `referral_id`, `transfer_id`, `doc_type`, `status` (final/draft), `finalized`, `received_date`, `service_date`, `content_tag` |
| `facility_capacity` | Chair capacity by date/modality | `location_id`, `date`, `modality`, `open_chairs` (sum across locations for a date+modality) |
| `program_candidates` | Program enrollment candidates | `program_code`, `patient_id`, `candidate_date`, `consent_status` (signed/declined/missing), `preferred_outreach`, `adherence_score`, `target_condition`, `source` |

## How the tables connect

- **Access verification** (roster): `intake_rosters` → `patients` → `coverage`, `pbm`, `patient_pharmacy`+`pharmacies`, `lifestyle`, `clinical_history`.
- **Referral audit** (batch): `referrals` (by `batch_id`) → `patients`, `icd_codes` (by `icd10_code`). Detect duplicates within the batch (same patient+ICD) and shared `insurance_id` across patients; use `notes` for "possible duplicate" hints.
- **Transfer review** (batch): `transfer_requests` (by `batch_id`) → `documents` (by `transfer_id`) and `facility_capacity` (by `requested_start_date`+`modality`) and `clinical_history` (risk flags).
- **Enrollment panel** (program): `program_candidates` (by `program_code`) → `patients`, `chart_artifacts`, `clinical_history`.

## Useful query patterns

```sql
-- all referrals in a batch with ICD metadata
SELECT r.*, i.chapter, i.service_family, i.laterality, i.description AS icd_description
FROM referrals r LEFT JOIN icd_codes i ON r.icd10_code = i.code
WHERE r.batch_id = '<BATCH_ID>' ORDER BY r.referral_id;

-- shared insurance across different patients in a batch
SELECT insurance_id, GROUP_CONCAT(DISTINCT patient_id) AS pids, COUNT(DISTINCT patient_id) AS n
FROM referrals WHERE batch_id = '<BATCH_ID>' AND insurance_id IS NOT NULL
GROUP BY insurance_id HAVING n > 1;

-- documents for a transfer batch, with staleness inputs
SELECT t.transfer_id, t.patient_id, t.requested_start_date, d.doc_type, d.status, d.finalized, d.received_date
FROM transfer_requests t LEFT JOIN documents d ON d.transfer_id = t.transfer_id
WHERE t.batch_id = '<BATCH_ID>' ORDER BY t.transfer_id, d.doc_type;

-- open chairs summed across locations for a date+modality
SELECT date, SUM(open_chairs) AS total_open FROM facility_capacity
WHERE modality = '<MODALITY>' AND date BETWEEN '<start>' AND '<end>'
GROUP BY date ORDER BY date;
```

Replace `<BATCH_ID>`, `<MODALITY>`, and date bounds with the current task's values. Re-confirm column names against the live schema before running.
