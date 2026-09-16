# Cedar Ridge Intake Coordination Portal — API Reference

## Base URL

Replace `<TASK_ENV_BASE_URL>` with the URL provided in the task prompt. No authentication required.

## Endpoints

### GET / — Portal Home

Returns an HTML dashboard page. Not used for data extraction.

### GET /patients — List Patients

Returns a paginated list of patients.

**Query parameters:** `q` (name or patient_id search), `limit` (integer)

**Response fields:** `patient_id`, `first_name`, `last_name`, `dob`, `address` (nullable), `phone` (nullable), `email` (nullable), `language`, `emergency_contact_present` (0/1), `existing_chart` (0/1), `preferred_contact` (portal|phone|sms|email).

### GET /patients/{patient_id} — Single Patient (Composite)

Returns a full composite view of one patient with all related records.

**Response sections:**

- `patient` — Same fields as list endpoint.
- `coverage[]` — Insurance records. Fields: `coverage_id`, `effective_date`, `group_number`, `network_status` (in_network|out_of_network), `patient_id`, `payer`, `policy_number`, `service_lines` (comma-separated string of service lines), `status` (active|expired|pending), `termination_date`.
- `pbm[]` — Pharmacy benefit manager records. Fields: `active` (0/1), `formulary_status` (covered|review|not_found), `patient_id`, `payer`, `pbm_id`, `policy_number`, `specialty_required` (0/1), `status` (approved|rejected|pending).
- `pharmacies[]` — Patient pharmacy preferences. Fields: `address`, `name`, `network_status` (in_network|out_of_network), `pharmacy_id`, `phone` (nullable), `preference_rank`.
- `lifestyle` — Fields: `alcohol_use` (None|Occasional|Moderate|Heavy), `exercise_frequency` (null or string), `patient_id`, `sleep_hours` (float), `smoking_status` (Never|Former|Current).
- `clinical_history` — Fields: `allergy_count`, `chronic_conditions` (comma-separated), `medication_count`, `patient_id`, `recent_hospitalization` (0/1), `risk_flags` (string), `surgeries`.
- `chart_artifacts[]` — Fields: `artifact_id`, `artifact_type` (vitals|active_problems|medications|demographics), `last_updated` (YYYY-MM-DD), `patient_id`, `status` (current|stale), `value_summary`.
- `documents[]` — Fields: `content_tag`, `doc_type`, `document_id`, `finalized` (0/1), `notes`, `patient_id`, `received_date` (YYYY-MM-DD), `referral_id` (nullable), `service_date` (nullable), `status` (draft|final), `transfer_id` (nullable).
- `referrals[]` — Fields: `appointment_date` (nullable), `appointment_scheduled` (0/1), `assigned_physician`, `auth_required` (0/1), `auth_status` (approved|denied|pending|not_required), `batch_id`, `date_received`, `diagnosis_description`, `icd10_code`, `imaging_received` (0/1), `insurance_id`, `notes`, `patient_id`, `payer`, `records_received` (0/1), `referral_id`, `referral_reason`, `referring_fax`, `referring_phone` (nullable), `referring_physician`, `referring_practice`, `service_line`, `urgency` (urgent|routine|admin).
- `transfers[]` — Fields: `batch_id`, `chair_window` (morning|midday|evening), `days_requested`, `modality`, `patient_id`, `referring_facility`, `requested_end_date`, `requested_start_date`, `status_note`, `transfer_id`, `transportation` (nullable).
- `rosters[]` — Fields: `patient_id`, `requested_service_date`, `roster_id`, `service_line`, `source_note`.
- `program_candidates[]` — Fields: `adherence_score`, `candidate_date`, `consent_status` (signed|missing|declined), `dob`, `email` (nullable), `existing_chart` (0/1), `first_name`, `last_name`, `patient_id`, `phone` (nullable), `preferred_outreach` (portal|phone|sms|email), `program_code`, `source`, `target_condition`.

### GET /chart/{patient_id} — Patient Chart

Returns chart-specific data.

**Response sections:**

- `active_problems[]` — Fields: `artifact_id`, `artifact_type`, `last_updated`, `patient_id`, `status` (current|stale), `value_summary`.
- `chart_artifacts[]` — Same shape as in composite patient endpoint.
- `clinical_history` — Same shape as in composite patient endpoint.
- `meds_allergies[]` — Same item shape as active_problems.
- `patient` — Same patient object.
- `recent_vitals_labs[]` — Same item shape as active_problems.

### GET /referrals — List Referrals

**Query parameters:** `batch_id`, `service_line` (orthopedics|pulmonary|cardiology), `limit`

Returned referrals use the same shape as in the composite patient response.

### GET /referrals/{referral_id} — Single Referral

Returns a single referral record.

### GET /transfers — List Transfers

**Query parameters:** `batch_id`, `limit`

Returned transfers use the same shape as in the composite patient response.

### GET /transfers/{transfer_id} — Single Transfer

Returns a single transfer record.

### GET /documents — List Documents

Returns all documents (up to 100). Filter client-side by `patient_id`, `transfer_id`, or `content_tag`.

**Document fields:** `content_tag` (transfer_packet|referral_document|chart_artifact), `doc_type`, `document_id`, `finalized` (0/1), `notes`, `patient_id`, `received_date`, `referral_id` (nullable), `service_date` (nullable), `status` (draft|final), `transfer_id` (nullable).

### GET /icd/{code} — ICD-10 Code Metadata

**Response fields:** `icd.code`, `icd.chapter`, `icd.description`, `icd.laterality` (nullable), `icd.service_family` (orthopedics|pulmonary|cardiology|chronic_care|dialysis|primary_care).

### GET /pharmacies — List Pharmacies

**Response fields per pharmacy:** `pharmacy_id`, `name`, `address`, `phone` (nullable), `network_status` (in_network|out_of_network).

### GET /programs/{program_code}/candidates — Program Candidates

**Response fields:** `count`, `program_code`, `candidates[]` — each with `adherence_score`, `candidate_date`, `consent_status` (signed|missing|declined), `dob`, `email` (nullable), `existing_chart` (0/1), `first_name`, `last_name`, `patient_id`, `phone` (nullable), `preferred_outreach` (portal|phone|sms|email), `program_code`, `source` (registry|payer_file|provider_panel), `target_condition`.

### POST /query — Read-Only SQL

Executes a read-only SELECT query. Only SELECT statements permitted.

**Request:** `{"sql": "SELECT ..."}`

**Response:** `{"columns": [...], "row_count": N, "rows": [...], "truncated": false}`

Known tables include `intake_rosters` (roster_id, patient_id, requested_service_date, service_line, source_note).

## Cross-Reference Notes

- For intake rosters: use SQL `SELECT * FROM intake_rosters WHERE roster_id = '...'` to get `requested_service_date` and `service_line`.
- For patient insurance/PBM/pharmacy: use `/patients/<patient_id>`.
- For chart completeness: use `/chart/<patient_id>`.
- For transfer documents: filter `/documents` by `transfer_id` or `patient_id`.
- For ICD chapter mismatch: compare `/icd/<code>` `service_family` against referral `service_line`.
