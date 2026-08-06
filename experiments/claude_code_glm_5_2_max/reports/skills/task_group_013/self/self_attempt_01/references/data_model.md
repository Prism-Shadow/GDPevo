# Portal Data Model

The REST detail endpoints and the SQL tables expose the same underlying data. Use this
map to know which field drives each decision and to write reconciliation SQL. Table and
column names are the real ones returned by `sqlite_master`.

## Tables

| Table | Key columns | Drives |
|---|---|---|
| `patients` | `patient_id`, `existing_chart`, `emergency_contact_present`, `address`, `preferred_contact`, `language` | demographics, chart-action input, demographic blockers |
| `intake_rosters` | `roster_id`, `patient_id`, `requested_service_date`, `service_line`, `source_note` | roster scope, requested date + service line (access verification) |
| `coverage` | `patient_id`, `payer`, `policy_number`, `effective_date`, `termination_date`, `network_status`, `service_lines`, `status` | `insurance_status` + coverage blockers |
| `pbm` | `patient_id`, `payer`, `policy_number`, `active`, `formulary_status`, `specialty_required`, `status` | `prescription_status` + pbm blockers |
| `pharmacies` | `pharmacy_id`, `network_status` | pharmacy network lookup |
| `patient_pharmacy` | `patient_id`, `pharmacy_id`, `preference_rank` | preferred pharmacy (`preference_rank=1`) → `pharmacy_status` |
| `lifestyle` | `patient_id`, `smoking_status`, `alcohol_use`, `exercise_frequency`, `sleep_hours` | `lifestyle_risk` |
| `clinical_history` | `patient_id`, `chronic_conditions`, `medication_count`, `allergy_count`, `recent_hospitalization`, `risk_flags` | `overall_risk`, high-touch flags |
| `chart_artifacts` | `patient_id`, `artifact_type`, `status`, `last_updated`, `value_summary` | missing chart artifacts |
| `referrals` | `referral_id`, `batch_id`, `service_line`, `patient_id`, `icd10_code`, `diagnosis_description`, `referral_reason`, `urgency`, `records_received`, `imaging_received`, `auth_required`, `auth_status`, `appointment_scheduled`, `appointment_date`, `insurance_id`, `payer` | referral readiness, blockers, duplicates, shared insurance |
| `transfer_requests` | `transfer_id`, `batch_id`, `patient_id`, `requested_start_date`, `requested_end_date`, `modality`, `days_requested`, `chair_window`, `transportation` | transfer scope, requested start |
| `documents` | `document_id`, `patient_id`, `referral_id`, `transfer_id`, `doc_type`, `status`, `finalized`, `received_date`, `content_tag` | packet completeness, freshness/staleness, missing records |
| `facility_capacity` | `location_id`, `date`, `modality`, `open_chairs` | chair capacity / feasibility for a requested start |
| `icd_codes` | `code`, `description`, `chapter`, `service_family`, `laterality` | ICD chapter/narrative/laterality discrepancies |
| `program_candidates` | `program_code`, `patient_id`, `candidate_date`, `source`, `consent_status`, `preferred_outreach`, `adherence_score`, `target_condition` | enrollment eligibility + outreach |

`sqlite_sequence` is internal — ignore it.

## Field → concept map (quick)

- **Insurance**: `coverage.status` + `effective_date`/`termination_date` + `service_lines` contains the roster `service_line`.
- **Prescription benefit**: `pbm.active` + `pbm.status` + `pbm.formulary_status` (+ `specialty_required` for policy mismatch).
- **Pharmacy**: `patient_pharmacy` (`preference_rank=1`) → `pharmacies.network_status`.
- **Lifestyle risk**: `lifestyle` row scored from smoking/alcohol/exercise/sleep.
- **Overall risk**: `lifestyle_risk` combined with `clinical_history.recent_hospitalization` / `risk_flags`.
- **ICD discrepancy**: `referrals.service_line` vs `icd_codes.service_family` (chapter mismatch); `referrals.diagnosis_description` vs `icd_codes.description` (narrative); `icd_codes.laterality` (laterality).
- **Referral blockers**: `records_received=0`, `imaging_received=0`, `auth_required=1 AND auth_status IN (pending,denied,not_submitted)`, `appointment_scheduled=1`.
- **Duplicates**: group `referrals` by `patient_id` + `service_line` (+ icd/reason) within a batch.
- **Shared insurance**: group `referrals` by `insurance_id`; compare distinct `patient_id`s.
- **Transfer packet**: `documents` where `transfer_id` matches, `status='final'`/`finalized=1`, `doc_type` in the required set.
- **Stale docs**: `documents.received_date` vs a per-`doc_type` freshness limit.
- **Capacity**: sum `facility_capacity.open_chairs` for the `requested_start_date` + `modality`.
- **Chart action**: `patients.existing_chart` + presence of `active_problems`/`meds_allergies`/`recent_vitals_labs`/`chart_artifacts` on `GET /chart/{id}`.
- **Enrollment**: `program_candidates.target_condition` + `consent_status` + `existing_chart` + `adherence_score` + active DM/HTN diagnosis in chart.
