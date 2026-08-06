# Cedar Ridge Intake Coordination Portal — environment reference

The task base URL is given in `environment_access.md` as `GDPEVO_ENV_BASE_URL`
(e.g. `http://task-env:9013/`). No credentials. Substitute it for every
`<TASK_ENV_BASE_URL>` placeholder in the task prompt. Treat all data as
**read-only** source-of-truth facts; every graded/derived field is computed by
*you* from these facts — the portal never returns a finished answer.

## How to query

Two equivalent access paths. The **read-only SQL endpoint is the most reliable**
because it exposes every column and lets you join tables.

```
POST <BASE>/query        body: {"sql": "SELECT ... "}      # read-only SQLite (SELECT only)
   -> {"columns":[...], "row_count":N, "rows":[{...}], "truncated":bool}
```

REST GETs (convenience; some add joined context):

```
GET /                              portal HTML (ignore)
GET /health                        liveness
GET /patients?q=&limit=            patient search
GET /patients/{patient_id}
GET /referrals?batch_id=&service_line=&limit=
GET /referrals/{referral_id}
GET /transfers?batch_id=&limit=
GET /transfers/{transfer_id}
GET /documents?patient_id=&referral_id=&transfer_id=
GET /chart/{patient_id}            AGGREGATE: {patient, clinical_history,
                                   chart_artifacts[], active_problems[],
                                   meds_allergies[], recent_vitals_labs[]}
GET /programs/{program_code}/candidates
GET /icd/{code}                    {icd:{code,description,chapter,service_family,laterality}}
GET /pharmacies
```

Curl pattern used throughout:
```
curl -s -X POST <BASE>/query -H 'Content-Type: application/json' \
     -d '{"sql":"SELECT * FROM referrals WHERE batch_id=\"ORTHO-JUN-01\""}'
```

## Tables (SQLite schema)

- **patients**(patient_id, first_name, last_name, dob, phone, email, language,
  address, existing_chart INT, preferred_contact, emergency_contact_present INT)
- **intake_rosters**(roster_id, patient_id, requested_service_date, service_line,
  source_note) — PK (roster_id, patient_id)
- **coverage**(coverage_id, patient_id, payer, policy_number, group_number,
  effective_date, termination_date, network_status, service_lines, status)
  — `service_lines` is a comma-joined string; `status ∈ {active, expired, pending}`
- **pbm**(pbm_id, patient_id, payer, policy_number, active INT, formulary_status,
  specialty_required INT, status) — pharmacy-benefit; `status ∈ {approved, pending,
  rejected}`, `formulary_status ∈ {covered, review, not_found}`
- **patient_pharmacy**(patient_id, pharmacy_id, preference_rank) +
  **pharmacies**(pharmacy_id, name, address, phone, network_status)
- **lifestyle**(patient_id, smoking_status, alcohol_use, exercise_frequency,
  sleep_hours REAL)
- **clinical_history**(patient_id, chronic_conditions, surgeries,
  medication_count INT, allergy_count INT, recent_hospitalization INT, risk_flags)
- **referrals**(referral_id, batch_id, service_line, date_received, patient_id,
  payer, insurance_id, referring_*, icd10_code, diagnosis_description,
  referral_reason, urgency, records_received INT, imaging_received INT,
  auth_required INT, auth_status, appointment_scheduled INT, appointment_date,
  assigned_physician, notes)
- **icd_codes**(code, description, chapter, service_family, laterality)
- **documents**(document_id, patient_id, referral_id, transfer_id, doc_type,
  status, finalized INT, received_date, service_date, content_tag, notes)
- **transfer_requests**(transfer_id, batch_id, patient_id, referring_facility,
  requested_start_date, requested_end_date, modality, days_requested,
  chair_window, transportation, status_note)
- **facility_capacity**(location_id, date, modality, open_chairs INT)
- **chart_artifacts**(artifact_id, patient_id, artifact_type, status,
  last_updated, value_summary)
- **program_candidates**(program_code, patient_id, candidate_date, source,
  consent_status, preferred_outreach, adherence_score INT, target_condition)

## Controlled vocabularies observed in data (for reference)

- coverage.status: `active`, `expired`, `pending`
- pbm (status/formulary): `approved/covered`, `pending/review`, `rejected/not_found`
- network_status (coverage, pharmacies): `in_network`, `out_of_network`
- referrals.urgency: `urgent`, `routine`, `admin`
- referrals.auth_status: `approved`, `pending`, `denied`, `not_required`
- icd_codes: service_family ∈ {orthopedics, pulmonary, cardiology, chronic_care,
  dialysis, ...}; chapter is an ICD-10 range like `M00-M99`, `J00-J99`, `S00-T88`,
  `R00-R99`, `I00-I99`, `E00-E89`, `N00-N99`, `Z00-Z99`.
- expected chapter per service line (canonical, code is "on-chapter" when it matches):
  orthopedics→`M00-M99`, pulmonary→`J00-J99`, cardiology→`I00-I99`.
- referrals.notes: `batch intake`, `possible duplicate` (dup-review flag),
  `distractor referral` (noise — such rows are outside the target batch).
- chart_artifacts.artifact_type: `demographics, active_problems, medications,
  allergies, vitals, labs, consent, care_plan, outreach_preference`;
  status ∈ {`current`, `stale`, `draft`}.
- documents.doc_type: allergy_list, face_sheet, flu_vaccine, hbsag,
  hep_b_antibody_core, history_physical, imaging_report, insurance_proof,
  medication_list, monthly_labs, physician_orders, pneumonia_vaccine, ppd_or_cxr,
  treatment_flowsheets, vascular_access_report; status ∈ {final, draft}, finalized INT.
- program_candidates.consent_status: `signed`, `declined`, `missing`;
  preferred_outreach: `phone`, `portal`, `sms`, `email`.
- facility_capacity.modality: `in_center_hemodialysis`; location_id: `CRIC-MAIN`,
  `CRIC-NORTH` (Cedar Ridge in-center locations).

## Distractors / scoping

The DB contains many sibling batches/rosters/programs and `distractor referral`
rows. **Always filter strictly to the target id** named in the prompt
(`batch_id`, `roster_id`, `program_code`). Never pull "all rows" into the answer.
