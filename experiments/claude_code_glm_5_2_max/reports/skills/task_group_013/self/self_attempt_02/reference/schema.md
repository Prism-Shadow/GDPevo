# Cedar Ridge Portal — Schema & Access Reference

## SQL endpoint

`POST {BASE_URL}/query` with JSON body `{"sql":"<SELECT ...>"}`.
Response: `{"columns":[...], "rows":[{...}], "row_count":N, "truncated":bool}`.
- Read-only; only `SELECT`.
- Use **single-quoted** SQL string literals so inner quotes don't break the JSON.
- Discover tables: `SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name`.
- Discover a table's schema: `SELECT sql FROM sqlite_master WHERE type='table' AND name='<table>'`.

## Tables (15)

### patients
`patient_id` (PK), `first_name`, `last_name`, `dob`, `phone`, `email`, `language`, `address`, `existing_chart` (0/1), `preferred_contact` (portal/phone/sms/email/...), `emergency_contact_present` (0/1).
- `existing_chart=0` ⇒ no chart yet (chart creation needed; program enrollment may be blocked).
- `preferred_contact` channel must have a corresponding value (`phone`⇒`phone`, `email`⇒`email`, `sms`⇒`phone`); if missing, preferred contact is unavailable.

### intake_rosters
`roster_id`, `patient_id`, `requested_service_date` (YYYY-MM-DD), `service_line`, `source_note`. PK `(roster_id, patient_id)`.
- For patient-access verification: read `requested_service_date` and `service_line` from here (the prompt only names the roster id).

### coverage  (medical insurance)
`coverage_id`, `patient_id`, `payer`, `policy_number`, `group_number`, `effective_date`, `termination_date`, `network_status` (in_network/out_of_network), `service_lines` (comma-separated), `status` (active/expired/pending/...).
- A patient may have one row. `service_lines` is a comma-joined list; check the roster's `service_line` is present for "covered service line".

### pbm  (prescription benefit manager)
`pbm_id`, `patient_id`, `payer`, `policy_number`, `active` (0/1), `formulary_status` (covered/review/not_found/...), `specialty_required` (0/1), `status` (approved/pending/rejected/...).
- `policy_number` should match `coverage.policy_number`; a mismatch is a policy mismatch.

### pharmacies
`pharmacy_id` (PK), `name`, `address`, `phone`, `network_status` (in_network/out_of_network).

### patient_pharmacy
`patient_id`, `pharmacy_id`, `preference_rank` (1 = preferred). PK `(patient_id, pharmacy_id)`.
- Pharmacy network status is taken from the preferred (`preference_rank=1`) pharmacy.

### lifestyle
`patient_id` (PK), `smoking_status` (Current/Former/Never), `alcohol_use` (None/Occasional/Moderate/Heavy), `exercise_frequency` (None/1-2/3-4/5+/null), `sleep_hours` (real).

### clinical_history
`patient_id` (PK), `chronic_conditions` (comma-separated: diabetes, hypertension, ckd, copd, cad, asthma, osteoarthritis, ...), `surgeries`, `medication_count`, `allergy_count`, `recent_hospitalization` (0/1), `risk_flags` (e.g. `recent_ed_visit`, `complex_medication_reconciliation`, `''`).

### chart_artifacts
`artifact_id`, `patient_id`, `artifact_type` (demographics/active_problems/medications/allergies/vitals/labs/consent/care_plan/...), `status` (current/stale), `last_updated`, `value_summary`.
- An artifact is usable only when `status='current'`. Absent or stale ⇒ missing for enrollment/chart-activation purposes.

### referrals
`referral_id` (PK), `batch_id`, `service_line` (orthopedics/pulmonary/cardiology/...), `date_received`, `patient_id`, `payer`, `insurance_id`, `referring_physician`, `referring_practice`, `referring_phone`, `referring_fax`, `icd10_code`, `diagnosis_description`, `referral_reason`, `urgency` (urgent/routine), `records_received` (0/1), `imaging_received` (0/1), `auth_required` (0/1), `auth_status` (approved/pending/denied/not_submitted), `appointment_scheduled` (0/1), `appointment_date`, `assigned_physician`, `notes`.
- `notes` may say `distractor referral` / `possible duplicate` / `batch intake` — hints, not determinative.

### icd_codes
`code` (PK), `description`, `chapter` (e.g. M00-M99, S00-T88, J00-J99, I00-I99, R00-R99), `service_family` (orthopedics/pulmonary/cardiology/...), `laterality` (left/right/null).
- `service_family` vs `referrals.service_line` drives clinical code discrepancy.

### transfer_requests
`transfer_id` (PK), `batch_id`, `patient_id`, `referring_facility`, `requested_start_date`, `requested_end_date`, `modality` (in_center_hemodialysis/...), `days_requested`, `chair_window` (morning/midday/evening), `transportation` (family/ride_share/medical_transport/null), `status_note`.
- `transportation` null ⇒ the "transportation" packet item is missing.

### documents
`document_id` (PK), `patient_id`, `referral_id`, `transfer_id`, `doc_type`, `status` (final/draft/...), `finalized` (0/1), `received_date`, `service_date`, `content_tag` (transfer_packet/...), `notes`.
- For transfer packets: a required doc is satisfied only if a row exists with `finalized=1`. Draft (finalized=0) or absent ⇒ missing.
- Doc types seen: allergy_list, face_sheet, flu_vaccine, hbsag, hep_b_antibody_core, history_physical, insurance_proof, medication_list, monthly_labs, physician_orders, pneumonia_vaccine, ppd_or_cxr, treatment_flowsheets, vascular_access_report.

### facility_capacity
`location_id`, `date`, `modality`, `open_chairs`. PK `(location_id, date, modality)`.
- `open_chairs_total` for a transfer's requested start = `SUM(open_chairs)` across all locations for that `date`+`modality`. If no row exists for that date ⇒ 0 (unavailable).

### program_candidates
`program_code`, `patient_id`, `candidate_date`, `source`, `consent_status` (signed/declined/missing), `preferred_outreach` (phone/portal/email/...), `adherence_score` (0–100), `target_condition` (diabetes_hypertension/copd/...). PK `(program_code, patient_id)`.
- Program code implies the required target condition and required chronic diagnoses (e.g. DMHTN ⇒ `diabetes_hypertension` ⇒ chronic_conditions must include `diabetes` and `hypertension`).

## REST convenience endpoints (alternative to SQL)

- `GET /patients/{id}` returns an assembled bundle: `patient`, `coverage[]`, `pbm[]`, `pharmacies[]` (with `preference_rank`), `lifestyle`, `clinical_history`, `chart_artifacts[]`, `documents[]`, `referrals[]`, `transfers[]`, `rosters[]`, `program_candidates[]`.
- `GET /chart/{id}` returns `patient`, `active_problems[]`, `meds_allergies[]`, `recent_vitals_labs[]`, `chart_artifacts[]`, `clinical_history`.
- `GET /programs/{code}/candidates` returns the candidate list for one program.
- `GET /icd/{code}` returns one ICD row.
- `GET /referrals?batch_id=...`, `GET /transfers?batch_id=...`, `GET /documents` support list filtering (otherwise pull all and filter client-side, or use SQL).

SQL is usually faster for cross-table joins (duplicates, shared insurance, capacity sums).
