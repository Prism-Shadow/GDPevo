# Portal Model — Endpoints & Data Model

`environment_access.md` is the **authoritative** source for the live base URL and the allowed endpoint set. The endpoint list below is derived from it; if the two ever disagree, follow `environment_access.md`. No authentication is required. Do not call `/health` or any reset/reseed endpoint.

Base URL example (from `environment_access.md`): `http://task-env:9013/` — replace `<TASK_ENV_BASE_URL>` with this in every request.

## REST endpoints

| Method + path | Purpose | Response shape |
|---|---|---|
| `GET /` | HTML landing page (browse only) | HTML |
| `GET /patients` | List/search patients (`?q=`, `?limit=`) | `{count, patients:[…]}` |
| `GET /patients/{patient_id}` | One patient, with joined coverage, pbm, chart_artifacts, clinical_history | single object (patient + `coverage[]`, `pbm`, `chart_artifacts[]`, `clinical_history`) |
| `GET /referrals` | List referrals (`?batch_id=`, `?service_line=`, `?limit=`) | `{count, referrals:[…]}` |
| `GET /referrals/{referral_id}` | One referral | single referral object |
| `GET /transfers` | List transfer requests (`?batch_id=`, `?limit=`) | `{count, transfers:[…]}` |
| `GET /transfers/{transfer_id}` | One transfer request | single transfer object |
| `GET /documents` | List documents (`?limit=`) | `{count, documents:[…]}` |
| `GET /chart/{patient_id}` | Aggregated chart: patient, clinical_history, chart_artifacts, active_problems, meds_allergies, recent_vitals_labs | single object with those keys |
| `GET /programs/{program_code}/candidates` | Program candidate list, joined with patient demographics | `{candidates:[…]}` |
| `GET /icd/{code}` | ICD-10 metadata for one code | `{icd:{code, description, chapter, service_family, laterality}}` |
| `GET /pharmacies` | List pharmacies | `{count, pharmacies:[…]}` |
| `POST /query` | Read-only SQL (`{"sql":"SELECT …"}`) | `{columns, row_count, rows:[…], truncated}` |

### Using `POST /query`

The SQL endpoint is the most efficient way to reconcile a whole batch. Submit `{"sql": "<SELECT statement>"}`. Only `SELECT` is permitted. Response `rows` is a list of objects keyed by `columns`; `truncated: true` means you hit a row cap — add a tighter `WHERE`/`LIMIT`.

## Underlying table/field model

These are the real tables behind the REST endpoints. Field names are the policy signals you map onto template tokens.

### `intake_rosters` — roster → patients + service date/line (access-verification tasks)
`roster_id, patient_id, requested_service_date, service_line, source_note`
- Gives the requested service date and service line for a roster's patients.

### `patients`
`patient_id, first_name, last_name, dob, phone, email, language, address, existing_chart, preferred_contact, emergency_contact_present`
- `existing_chart` (0/1) → chart active or not.
- `emergency_contact_present` (0/1) → emergency-contact completeness.
- `preferred_contact` ∈ {portal, email, phone, sms, …}; a chosen channel with a null contact value (e.g. `preferred_contact=email` but `email` is null) → contact unreachable.
- `address` null → missing address.

### `coverage` — insurance
`coverage_id, patient_id, payer, policy_number, group_number, effective_date, termination_date, network_status, service_lines, status`
- `service_lines` is a comma-separated list. `status` ∈ {active, …}. `network_status` ∈ {in_network, out_of_network}.
- Insurance validity = active **and** in-network **and** `effective_date ≤ service date ≤ termination_date` **and** service line ∈ `service_lines`.

### `pbm` — prescription benefit
`pbm_id, patient_id, payer, policy_number, active, formulary_status, specialty_required, status`
- `active` (0/1), `formulary_status` ∈ {covered, not_found, …}, `status` ∈ {approved, rejected, …}.

### `pharmacies` / `patient_pharmacy` — preferred pharmacy
- `pharmacies`: `pharmacy_id, name, address, phone, network_status` (in_network/out_of_network).
- `patient_pharmacy`: `patient_id, pharmacy_id, preference_rank`. Use `preference_rank = 1` as the preferred pharmacy; join to `pharmacies.network_status`.

### `lifestyle`
`patient_id, smoking_status, alcohol_use, exercise_frequency, sleep_hours`
- `smoking_status` ∈ {Current, Former, Never, …}; `exercise_frequency` ∈ {None, 1-2, 3-4, …}; `sleep_hours` real.

### `clinical_history`
`patient_id, chronic_conditions, surgeries, medication_count, allergy_count, recent_hospitalization, risk_flags`
- `chronic_conditions` comma-separated (e.g. `ckd,copd,hypertension`). `recent_hospitalization` (0/1). `risk_flags` comma-separated (e.g. `ed_visit`, `low_adherence`).

### `chart_artifacts`
`artifact_id, patient_id, artifact_type, status, last_updated, value_summary`
- `artifact_type` ∈ {chart_record, active_problems, vitals, labs, medications, consent, …}; `status` ∈ {current, stale, missing, …}; `last_updated` YYYY-MM-DD.
- Missing or stale artifacts drive `missing_chart_artifacts` and chart-action outputs.

### `referrals`
`referral_id, batch_id, service_line, date_received, patient_id, payer, insurance_id, referring_physician, referring_practice, referring_phone, referring_fax, icd10_code, diagnosis_description, referral_reason, urgency, records_received, imaging_received, auth_required, auth_status, appointment_scheduled, appointment_date, assigned_physician, notes`
- `urgency` ∈ {urgent, routine}. `records_received`/`imaging_received`/`auth_required`/`appointment_scheduled` are 0/1. `auth_status` ∈ {approved, pending, denied, not_submitted}. `insurance_id` is the shared-policy key for anomaly detection. `icd10_code` joins to `icd_codes`.

### `transfer_requests`
`transfer_id, batch_id, patient_id, referring_facility, requested_start_date, requested_end_date, modality, days_requested, chair_window, transportation, status_note`
- `modality` ∈ {in_center_hemodialysis, …}. `requested_start_date` joins to `facility_capacity.date`.

### `documents`
`document_id, patient_id, referral_id, transfer_id, doc_type, status, finalized, received_date, service_date, content_tag, notes`
- `doc_type` is the packet item code. `finalized` (0/1) and `status` ∈ {final, draft, …}. `received_date` drives freshness checks. `transfer_id`/`referral_id` link a doc to its batch row.

### `facility_capacity`
`location_id, date, modality, open_chairs`
- Sum `open_chairs` across `location_id` for a given `date` + `modality` to get total open chairs for a requested start date.

### `icd_codes`
`code, description, chapter, service_family, laterality`
- `chapter` (e.g. `M00-M99`, `S00-T88`), `service_family` (e.g. `orthopedics`), `laterality` ∈ {left, right, null}. Use to detect chapter / narrative / laterality discrepancies vs. a referral's `service_line` and narrative fields. (`GET /icd/{code}` returns the same row.)

### `program_candidates`
`program_code, patient_id, candidate_date, source, consent_status, preferred_outreach, adherence_score, target_condition`
- `consent_status` ∈ {signed, declined, missing, …}. `preferred_outreach` ∈ {phone, portal, sms, email, …}. `adherence_score` integer. `target_condition` (e.g. `diabetes_hypertension`) must match the program's target.
