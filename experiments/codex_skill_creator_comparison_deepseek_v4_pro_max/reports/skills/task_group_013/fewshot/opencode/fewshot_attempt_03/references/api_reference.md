# Cedar Ridge Intake Coordination Portal -- API Reference

Base URL provided in the task prompt as `<TASK_ENV_BASE_URL>`. All endpoints are
read-only HTTP GET except `/query` which is POST. No authentication is required.

## Endpoints

### GET /

Returns an HTML dashboard listing all available endpoints and query forms.

### GET /patients

Returns a paginated list of patients. Accepts query parameters:
- `q` -- search by name or patient ID
- `limit` -- max results (default 10)

Response fields per patient: `patient_id`, `first_name`, `last_name`, `dob`,
`address`, `email`, `phone`, `language`, `preferred_contact`,
`emergency_contact_present` (0 or 1), `existing_chart` (0 or 1).

### GET /patients/{patient_id}

Returns the complete patient composite record. This is the primary endpoint for
patient-level data across all operation types.

**Top-level keys:**
- `patient` -- demographics (same fields as the list endpoint)
- `coverage` -- array of insurance coverage records
- `pbm` -- array of prescription benefit manager records
- `pharmacies` -- array of patient's preferred pharmacies (ranked)
- `lifestyle` -- lifestyle risk factors
- `clinical_history` -- chronic conditions, surgeries, allergy/medication counts, risk flags, hospitalization flag
- `chart_artifacts` -- array of chart artifact records (vitals, labs, etc.)
- `documents` -- array of clinical document records
- `referrals` -- array of referrals for this patient
- `transfers` -- array of transfers for this patient
- `rosters` -- array of roster records for this patient
- `program_candidates` -- array of program candidate records

**Coverage fields:** `coverage_id`, `patient_id`, `payer`, `policy_number`,
`group_number`, `status` (active/expired/pending), `network_status`,
`service_lines` (comma-separated), `effective_date`, `termination_date`.

**PBM fields:** `pbm_id`, `patient_id`, `payer`, `policy_number`, `status`
(approved/rejected), `active` (0 or 1), `formulary_status`, `specialty_required`.

**Pharmacy fields:** `pharmacy_id`, `name`, `address`, `phone`,
`network_status` (in_network/out_of_network), `preference_rank`.

**Lifestyle fields:** `smoking_status` (Current/Former/Never),
`alcohol_use` (Heavy/Moderate/Occasional/None),
`exercise_frequency` (None/1-2/3-4/5+/null), `sleep_hours` (float or null).

**Clinical history fields:** `chronic_conditions` (comma-separated),
`allergy_count`, `medication_count`, `surgeries`, `risk_flags`,
`recent_hospitalization` (0 or 1).

### GET /referrals

Returns a paginated list of referrals. Query parameters:
- `batch_id` -- filter by batch ID (exact match)
- `service_line` -- filter by service line
- `limit` -- max results (default 10)

Response fields per referral: `referral_id`, `batch_id`, `patient_id`,
`service_line`, `icd10_code`, `diagnosis_description`, `referral_reason`,
`urgency` (urgent/routine/admin), `auth_required` (0/1), `auth_status`
(approved/denied/pending/not_required), `records_received` (0/1),
`imaging_received` (0/1), `appointment_scheduled` (0/1), `appointment_date`
(null or date), `insurance_id`, `payer`, `assigned_physician`,
`referring_physician`, `referring_practice`, `referring_phone`,
`referring_fax`, `date_received`, `notes`.

### GET /referrals/{referral_id}

Returns a single referral record with the same shape as the list items.

### GET /transfers

Returns a paginated list of dialysis transfers. Query parameters:
- `batch_id` -- filter by batch ID
- `limit` -- max results (default 10)

Response fields per transfer: `transfer_id`, `batch_id`, `patient_id`,
`modality`, `days_requested`, `chair_window`,
`requested_start_date`, `requested_end_date`,
`referring_facility`, `transportation`, `status_note`.

### GET /transfers/{transfer_id}

Returns a single transfer record.

### GET /documents

Returns documents in the system. Each document has a `doc_type` field
(see controlled vocabulary in business rules).

### GET /chart/{patient_id}

Returns the chart view for a patient. This is a separate view from the
patient composite endpoint and focuses on clinical artifacts.

**Top-level keys:**
- `patient` -- demographics
- `active_problems` -- array of active problem records
- `clinical_history` -- same shape as patient endpoint's clinical_history
- `meds_allergies` -- medications and allergies
- `recent_vitals_labs` -- recent vitals and lab results
- `chart_artifacts` -- same shape as patient endpoint's chart_artifacts

### GET /programs/{program_code}/candidates

Returns all current candidates for a chronic-care program. Response fields:
`program_code`, `count`, `candidates` (array).

Candidate fields: `patient_id`, `first_name`, `last_name`, `dob`, `email`,
`phone`, `preferred_outreach`, `consent_status` (signed/declined/missing),
`existing_chart` (0/1), `target_condition`, `adherence_score`, `source`,
`candidate_date`, `program_code`.

### GET /icd/{code}

Returns ICD-10 code metadata. Example: `GET /icd/S83.512A`.

Response fields: `icd.code`, `icd.chapter`, `icd.description`,
`icd.laterality` (left/right/bilateral/null), `icd.service_family`.

ICD chapters follow standard ICD-10-CM chapter ranges:
- M00-M99: musculoskeletal (orthopedics)
- J00-J99: respiratory (pulmonary)
- I00-I99: circulatory (cardiology)
- S00-T88: injury, poisoning, external causes
- R00-R99: symptoms, signs, abnormal findings

### GET /pharmacies

Returns the full pharmacy network directory. Each pharmacy has:
`pharmacy_id`, `name`, `address`, `phone`, `network_status`.

### POST /query

Read-only SQL endpoint. Accepts `{"sql": "<SELECT statement>"}` and returns
the result as JSON. Available tables include:
- `intake_rosters` (roster_id, patient_id, requested_service_date, service_line)
- `referrals` (all fields from the referrals list)
- `patients` (patient_id, first_name, last_name, dob, address, phone, email, language, preferred_contact, emergency_contact_present, existing_chart)
- `transfers` (all fields)
- `documents` (document_id, patient_id, transfer_id, doc_type, received_date, status)
- `chart_artifacts` (artifact_id, patient_id, artifact_type, last_updated, status, value_summary)
- `coverage` (coverage_id, patient_id, payer, policy_number, status, service_lines, network_status)
- `pbm` (pbm_id, patient_id, policy_number, payer, status, active, formulary_status)
- `pharmacies` (pharmacy_id, name, address, network_status)
- `patient_pharmacies` (patient_id, pharmacy_id, preference_rank)
- `lifestyle` (patient_id, smoking_status, alcohol_use, exercise_frequency, sleep_hours)
- `clinical_history` (patient_id, chronic_conditions, allergy_count, medication_count, risk_flags, recent_hospitalization)
- `icd_metadata` (code, chapter, description, laterality, service_family)

Use SQL when you need to join across tables or aggregate in ways the REST
endpoints do not support directly. Only SELECT is permitted.

## Parallel fetching

All GET endpoints are independent. Fetch patient records and ICD lookups in
parallel. The portal has no rate limiting on the training data.
