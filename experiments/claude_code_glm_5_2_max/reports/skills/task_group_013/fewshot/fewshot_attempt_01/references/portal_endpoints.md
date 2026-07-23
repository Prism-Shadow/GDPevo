# Portal Endpoints & Field Map

Base URL and allowed endpoint list come from `environment_access.md`. This file documents the
response shape of each endpoint and which fields drive reconciliation. All field names are
exactly as returned by the portal. No authentication is required.

## Collections (list endpoints)

Each list returns `{ "count": N, "<collection>": [ ... ] }`.

### `GET /patients` → `{ count, patients[] }`
List rows (identity only): `patient_id, first_name, last_name, dob, address, phone, email,
language, preferred_contact, emergency_contact_present, existing_chart`.

### `GET /referrals` → `{ count, referrals[] }`
Row fields: `referral_id, patient_id, batch_id, service_line, icd10_code, diagnosis_description,
referral_reason, urgency, payer, insurance_id, auth_required, auth_status, records_received,
imaging_received, appointment_scheduled, appointment_date, date_received, assigned_physician,
referring_physician, referring_practice, referring_phone, referring_fax, notes`.

Filter by `batch_id` to scope a referral task.

### `GET /transfers` → `{ count, transfers[] }`
Row fields: `transfer_id, patient_id, batch_id, modality, days_requested, chair_window,
transportation, referring_facility, requested_start_date, requested_end_date, status_note`.

Filter by `batch_id` to scope a transfer task.

### `GET /documents` → `{ count, documents[] }`
Row fields: `document_id, patient_id, referral_id, transfer_id, doc_type, content_tag,
received_date, status, finalized, service_date, notes`.

`content_tag` separates document families (e.g. `transfer_packet`, `referral_packet`). Use the
`transfer_id` / `referral_id` link to attach documents to the right record. `status`/`finalized`
determine whether a required document counts as present.

### `GET /pharmacies` → `{ count, pharmacies[] }`
Row fields: `pharmacy_id, name, address, phone, network_status` (`in_network` / `out_of_network`).

## Per-record detail

### `GET /patients/{patient_id}`
Full patient bundle. Top-level keys: `patient, coverage[], pbm[], pharmacies[],
rosters[], referrals[], transfers[], documents[], chart_artifacts[], clinical_history,
lifestyle, program_candidates[]`. This is the primary endpoint for access-verification and
enrollment tasks — it joins most of the patient's data in one call.

Key sub-objects:

- `patient` — identity (same fields as the list row).
- `coverage[]` — `coverage_id, payer, policy_number, group_number, service_lines, network_status,
  status, effective_date, termination_date`. `service_lines` is a comma-separated list; check
  membership for the task's service line. `status` / `termination_date` / `effective_date` drive
  `insurance_status`.
- `pbm[]` — `pbm_id, payer, policy_number, active, status, formulary_status,
  specialty_required`. Drives `prescription_status`.
- `pharmacies[]` — preferred pharmacy rows with `network_status` and `preference_rank`. Drives
  `pharmacy_status`.
- `rosters[]` — `roster_id, patient_id, requested_service_date, service_line, source_note`. For a
  roster task, this is where the requested service date and service line come from.
- `clinical_history` — `chronic_conditions, surgeries, allergy_count, medication_count,
  recent_hospitalization, risk_flags`.
- `lifestyle` — `smoking_status, alcohol_use, exercise_frequency, sleep_hours`. Drives
  `lifestyle_risk`.
- `program_candidates[]` — any program candidate rows for this patient.

### `GET /referrals/{referral_id}`
Returns `{ referral, patient, icd, documents[] }`.

- `referral` — the same row fields as the list.
- `icd` — the ICD metadata for `referral.icd10_code` (same shape as `GET /icd/{code}`).
- `patient` — the referral's patient identity.
- `documents[]` — documents linked to this referral.

### `GET /transfers/{transfer_id}`
Returns the transfer row plus `capacity[]` — a list of `{ date, location_id, modality,
open_chairs }` rows giving chair availability across locations and dates around the requested
start. Sum `open_chairs` across locations for the requested start date to get
`open_chairs_total` and `capacity_status`.

### `GET /chart/{patient_id}`
Chart bundle: `patient, active_problems[], meds_allergies[], chart_artifacts[],
recent_vitals_labs[], clinical_history`. Use the presence/absence of these arrays (and their
contents) to find `missing_chart_artifacts` and to decide `chart_action` for ready referrals and
enrollment holds.

### `GET /programs/{program_code}/candidates` → `{ candidates[] }`
Candidate rows: `patient_id, program_code, target_condition, consent_status, existing_chart,
adherence_score, candidate_date, source, preferred_outreach, first_name, last_name, dob, phone,
email`. The number and order of rows here defines the enrollment panel scope — include a row for
every candidate returned.

### `GET /icd/{code}` → `{ icd }`
Fields: `code, description, chapter, laterality, service_family`. `chapter` is the ICD-10
chapter range (e.g. `M00-M99`, `S00-T88`); `service_family` is the clinical family the code
belongs to; `laterality` is `left`/`right`/`null`. This drives every clinical-code discrepancy
check.

### `GET /pharmacies` (see above)

## Read-only SQL

### `POST /query` with JSON body `{"sql": "..."}`
Returns `{ columns, row_count, rows, truncated }`. The database has these tables:
`patients, coverage, pbm, patient_pharmacy, pharmacies, lifestyle, clinical_history,
chart_artifacts, referrals, transfer_requests, documents, facility_capacity, icd_codes,
intake_rosters, program_candidates` (plus `sqlite_sequence`).

Use SQL when you need to:
- count records per batch/roster/program to confirm scope;
- group referrals by `insurance_id` or `patient_id` to find duplicates and shared-insurance
  anomalies in one pass;
- aggregate `facility_capacity` by date;
- cross-check that your per-record list length matches the collection total for the scope.

`truncated: true` means the result was cut off — re-issue with a narrower query or `LIMIT`.
