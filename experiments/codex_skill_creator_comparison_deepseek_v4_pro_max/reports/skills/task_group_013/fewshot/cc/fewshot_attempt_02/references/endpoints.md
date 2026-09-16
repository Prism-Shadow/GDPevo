# Cedar Ridge Intake Coordination Portal — API Reference

All endpoints are served from `<TASK_ENV_BASE_URL>` as given in the prompt.
Replace this placeholder with the actual URL before making requests.
Authentication is not required.

## Endpoint catalog

### GET /

Returns a plain-text health/status response. Use for connectivity checks.

### GET /patients

Returns a JSON array of all patient records. Each record has at minimum:
`patient_id`, `name`, `dob`, `address`, `phone`, `email`, `insurance_id`,
`preferred_pharmacy`, and `emergency_contact`. Additional patient-specific
fields may appear depending on the batch.

### GET /patients/{patient_id}

Returns a single patient record. 404 when the patient does not exist.

### GET /referrals

Returns a JSON array of all referral records. Each record has at minimum:
`referral_id`, `patient_id`, `icd10_code`, `referral_date`, `referring_provider`,
`service_line`, `narrative`, `documents` (array of document IDs), `imaging`
(array of imaging IDs), `authorization` (object with `status` and
`auth_number`), and `insurance_id`.

### GET /referrals/{referral_id}

Returns a single referral record. 404 when the referral does not exist.

### GET /transfers

Returns a JSON array of all transfer records. Each record has at minimum:
`transfer_id`, `patient_id`, `requested_start_date`, `documents` (array of
document type strings, each with `doc_type` and `received_date`), and
`referring_facility`.

### GET /transfers/{transfer_id}

Returns a single transfer record. 404 when the transfer does not exist.

### GET /documents

Returns a JSON array of all document records. Each record has at minimum:
`document_id`, `doc_type`, `received_date`, and `patient_id`.

### GET /chart/{patient_id}

Returns a patient's chart record. The chart contains sections for
`active_problems`, `medications`, `allergies`, `vitals`, `labs`, `consent`,
`demographics`, and other clinical artifacts. Individual sections may
be absent (null or missing keys) when that artifact has not been created.
404 when the patient has no chart.

### GET /programs/{program_code}/candidates

Returns a JSON array of candidate patient records for the given program
code. Each record includes `patient_id` and program-specific eligibility
data. The list defines the universe of patients to evaluate for enrollment.

### GET /icd/{code}

Returns ICD-10 metadata for the given code, including `code`, `description`,
and `chapter`. The chapter is an ICD-10 range string like `M00-M99` or
`S00-T88`. 404 when the code is not recognized.

### GET /pharmacies

Returns a JSON array of pharmacy records. Each record has at minimum:
`pharmacy_id`, `name`, and `network_status` (`in_network` or `out_of_network`).
Use this to determine whether a patient's preferred pharmacy is in-network.

### POST /query

Accepts a JSON body: `{"query": "<SQL statement>"}`. Returns a JSON array
of row objects. The database schema mirrors the REST resources: tables
include `patients`, `referrals`, `transfers`, `documents`, `charts`, and
related join tables.

Use this endpoint when you need to cross-reference records in bulk — for
example, joining referrals to patients to find shared insurance IDs, or
joining transfers to documents to check packet completeness. Fetching
individual records and cross-referencing in memory is also valid, but
SQL is usually faster for batch operations.

## Response conventions

- All successful responses return HTTP 200 with a JSON body.
- Collection endpoints return JSON arrays; singleton endpoints return
  JSON objects.
- 404 responses indicate a missing resource — treat these as "missing data"
  rather than errors.
- Date strings use `YYYY-MM-DD` format.
