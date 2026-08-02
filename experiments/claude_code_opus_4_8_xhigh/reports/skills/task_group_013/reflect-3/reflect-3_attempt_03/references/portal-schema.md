# Portal data model

The Cedar Ridge Intake Coordination Portal is backed by a read-only relational store. Discover the
live schema from `sqlite_master` (`SELECT name, sql FROM sqlite_master WHERE type='table'`), then
join directly. The tables and the role each plays in reconciliation:

| Table | Key columns | Role |
|---|---|---|
| `patients` | `patient_id`, `existing_chart`, `preferred_contact`, `emergency_contact_present`, `address`, `phone`, `email`, `language` | Demographics; drives contact/address completeness and `existing_chart` for chart activation. |
| `coverage` | `patient_id`, `payer`, `policy_number`, `effective_date`, `termination_date`, `network_status`, `service_lines`, `status` | Insurance validity by service line + date. `service_lines` is a comma-separated list. |
| `pbm` | `patient_id`, `payer`, `policy_number`, `active`, `formulary_status`, `specialty_required`, `status` | Prescription-benefit validity; compare policy vs `coverage.policy_number`. |
| `pharmacies` | `pharmacy_id`, `network_status` | Network status of a pharmacy. |
| `patient_pharmacy` | `patient_id`, `pharmacy_id`, `preference_rank` | Patient→pharmacy preference; rank 1 is the preferred pharmacy. |
| `lifestyle` | `patient_id`, `smoking_status`, `alcohol_use`, `exercise_frequency`, `sleep_hours` | Lifestyle-risk scoring. |
| `clinical_history` | `patient_id`, `chronic_conditions`, `medication_count`, `allergy_count`, `recent_hospitalization`, `risk_flags` | Clinical acuity for overall risk / high-touch triggers. `chronic_conditions` is comma-separated. |
| `intake_rosters` | `roster_id`, `patient_id`, `requested_service_date`, `service_line` | New-patient roster; source of the roster's service date + service line. |
| `referrals` | `referral_id`, `batch_id`, `service_line`, `patient_id`, `payer`, `insurance_id`, `icd10_code`, `diagnosis_description`, `referral_reason`, `urgency`, `records_received`, `imaging_received`, `auth_required`, `auth_status`, `appointment_scheduled`, `appointment_date` | Referral batches; blockers, duplicates, shared insurance, coding checks, scheduling. |
| `icd_codes` | `code`, `description`, `chapter`, `service_family`, `laterality` | Authoritative ICD metadata; `service_family` is the check for chapter mismatch. |
| `transfer_requests` | `transfer_id`, `batch_id`, `patient_id`, `referring_facility`, `requested_start_date`, `modality`, `days_requested`, `chair_window`, `transportation` | Transfer/dialysis batches; requested start + modality for capacity. |
| `documents` | `document_id`, `patient_id`, `referral_id`, `transfer_id`, `doc_type`, `status`, `finalized`, `received_date`, `service_date`, `content_tag` | Packet/document completeness + freshness; a doc counts only when `finalized`. |
| `facility_capacity` | `location_id`, `date`, `modality`, `open_chairs` | Chair/appointment capacity; sum `open_chairs` across locations per date+modality. |
| `chart_artifacts` | `artifact_id`, `patient_id`, `artifact_type`, `status`, `last_updated`, `value_summary` | Chart artifacts present per patient; `status` may be `current`/`stale`. Absent type = not present. |
| `program_candidates` | `program_code`, `patient_id`, `candidate_date`, `source`, `consent_status`, `preferred_outreach`, `adherence_score`, `target_condition` | Program enrollment cohort + consent/adherence/target. |

## Access patterns

- **Members of a batch/roster/program**: filter the corresponding table by `batch_id` /
  `roster_id` / `program_code` (or use the REST list/candidates endpoint). Order members ascending
  by their id.
- **Detail endpoints** (`/<resource>/{id}`) return a record pre-joined with patient, ICD, and
  documents — convenient for spot checks; SQL joins are better for whole-cohort reconciliation.
- **Comma-separated columns** (`coverage.service_lines`, `clinical_history.chronic_conditions`)
  must be split before membership tests.
- Flags stored as integers (`0`/`1`): `existing_chart`, `records_received`, `imaging_received`,
  `auth_required`, `appointment_scheduled`, `emergency_contact_present`, `recent_hospitalization`,
  `pbm.active`, `documents.finalized`, `pbm.specialty_required`.
