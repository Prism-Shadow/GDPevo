# Cedar Ridge Portal — data model & vocabularies

SQLite database behind `POST /query`. Columns and observed value vocabularies
below are the reusable domain reference; verify against `/health` and
`sqlite_master` at task time in case a task's data differs.

## Tables (columns)

- **patients** (`patient_id` PK): first_name, last_name, dob, phone, email,
  language, address, `existing_chart` 0/1, preferred_contact,
  `emergency_contact_present` 0/1.
- **coverage** (medical insurance; many per patient): patient_id, payer,
  policy_number, group_number, effective_date, termination_date,
  network_status, `service_lines` (comma-joined list), status.
- **pbm** (prescription benefit): patient_id, payer, policy_number,
  `active` 0/1, formulary_status, `specialty_required` 0/1, status.
- **patient_pharmacy** (patient_id, pharmacy_id, preference_rank) — lower rank =
  more preferred; join to **pharmacies** (pharmacy_id PK: name, address, phone,
  network_status).
- **lifestyle** (patient_id PK): smoking_status, alcohol_use,
  exercise_frequency, sleep_hours.
- **intake_rosters** (PK roster_id+patient_id): requested_service_date,
  service_line, source_note.
- **referrals** (`referral_id` PK): batch_id, service_line, date_received,
  patient_id, payer, insurance_id, referring_physician/practice/phone/fax,
  icd10_code, diagnosis_description, referral_reason, urgency,
  `records_received` 0/1, `imaging_received` 0/1, `auth_required` 0/1,
  auth_status, `appointment_scheduled` 0/1, appointment_date,
  assigned_physician, notes.
- **icd_codes** (`code` PK): description, chapter, service_family, laterality.
- **documents** (`document_id` PK): patient_id, referral_id, transfer_id,
  doc_type, status, `finalized` 0/1, received_date, service_date, content_tag,
  notes.
- **transfer_requests** (`transfer_id` PK): batch_id, patient_id,
  referring_facility, requested_start_date, requested_end_date, modality,
  days_requested, chair_window, transportation, status_note.
- **facility_capacity** (PK location_id+date+modality): open_chairs (integer).
- **program_candidates** (PK program_code+patient_id): candidate_date, source,
  consent_status, preferred_outreach, adherence_score, target_condition.
- **chart_artifacts** (artifact_id PK): patient_id, artifact_type, status,
  last_updated, value_summary.
- **clinical_history** (patient_id PK): chronic_conditions, surgeries,
  medication_count, allergy_count, `recent_hospitalization` 0/1, risk_flags.

## Observed value vocabularies

- **coverage.status**: active, expired, pending.
  **coverage.network_status**: in_network, out_of_network.
  **service_lines** members seen: primary_care, chronic_care, cardiology,
  pulmonary, orthopedics, dialysis.
- **pbm.status**: approved, pending, rejected.
  **pbm.formulary_status**: covered, review, not_found. `active`/
  `specialty_required` 0/1.
- **pharmacies.network_status**: in_network, out_of_network (a patient with no
  pharmacy on file → treat as unknown per template).
- **lifestyle.smoking_status**: Current, Former, Never.
  **alcohol_use**: None, Occasional, Moderate, Heavy.
  **exercise_frequency**: None, "1-2", "3-4", "5+", null. (Note capitalization;
  normalize to the template's lowercase risk enums.)
- **referrals.urgency**: urgent, routine, admin.
  **auth_status**: approved, pending, denied, not_required.
- **icd_codes.service_family**: chronic_care, cardiology, pulmonary,
  orthopedics, dialysis. **chapter** examples: E00-E89, I00-I99, J00-J99,
  M00-M99, N00-N99, R00-R99, S00-T88, Z00-Z99.
  **laterality**: left, right, or null.
- **documents.doc_type**: allergy_list, face_sheet, flu_vaccine, hbsag,
  hep_b_antibody_core, history_physical, imaging_report, insurance_proof,
  medication_list, monthly_labs, physician_orders, pneumonia_vaccine,
  ppd_or_cxr, treatment_flowsheets, vascular_access_report.
  **status**: draft, final. **content_tag**: referral_packet, transfer_packet.
  A document counts as present only when it is finalized/final (a `draft` is not
  a completed packet item).
- **transfer_requests.modality**: in_center_hemodialysis.
- **chart_artifacts.artifact_type**: demographics, active_problems, medications,
  allergies, vitals, labs, consent, care_plan, outreach_preference.
  **status**: current, draft, stale. A `stale`/`draft` artifact is present in the
  chart but not "fresh/active".
- **program_candidates.consent_status**: signed, declined, missing.
  **target_condition**: diabetes_hypertension, renal_diabetes, cardiac, …
  **preferred_outreach**: phone, portal, sms, email. `adherence_score` integer.
- **clinical_history.risk_flags** (comma list): "", recent_ed_visit,
  complex_medication_reconciliation, fall_risk, …
  **chronic_conditions** (comma list): e.g. ckd, copd, hypertension, diabetes.

## Reliable joins

- Referral bundle: `referrals` → `patients` (patient_id) → `icd_codes`
  (icd10_code=code) → `documents` (referral_id). `GET /referrals/{id}` returns
  all four.
- Transfer packet: `transfer_requests` → `documents`
  (transfer_id, content_tag='transfer_packet') → `facility_capacity`
  (date=requested_start_date, modality).
- Program panel: `program_candidates` → `patients` → `chart_artifacts` /
  `clinical_history` (patient_id). `GET /chart/{patient_id}` returns the bundle.
- Access verification: `intake_rosters` (roster_id) → `patients` → `coverage`,
  `pbm`, `patient_pharmacy`+`pharmacies`, `lifestyle` (all by patient_id).
