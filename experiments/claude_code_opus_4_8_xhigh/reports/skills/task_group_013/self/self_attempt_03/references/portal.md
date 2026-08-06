# Portal reference — endpoints, SQL, schema, field sources

Base URL comes from `environment_access.md` (`GDPEVO_ENV_BASE_URL`). The prompt's
`<TASK_ENV_BASE_URL>` placeholder resolves to it. No credentials.

## Allowed endpoints (read-only)

REST (GET):
- `GET /` — HTML landing page (human UI; not needed programmatically).
- `GET /health` — DB readiness + per-table `record_counts` (sanity check).
- `GET /patients?q=<name|id>&limit=<n>` — patient search (paginated).
- `GET /patients/{patient_id}` — **aggregator**: `patient`, `coverage[]`,
  `pbm[]`, `pharmacies[]` (with `preference_rank`), `lifestyle`,
  `clinical_history`, `referrals[]`, `rosters[]`, `transfers[]`,
  `program_candidates[]`, `chart_artifacts[]`, `documents[]`.
- `GET /referrals?batch_id=<id>&service_line=<line>&limit=<n>`
- `GET /referrals/{referral_id}`
- `GET /transfers?batch_id=<id>&limit=<n>`
- `GET /transfers/{transfer_id}` — includes the transfer, its `documents[]`, the
  `patient`, and a `capacity[]` window for the requested date range.
- `GET /documents?transfer_id=<id>` / `?referral_id=<id>` / `?patient_id=<id>`
- `GET /chart/{patient_id}` — `patient`, `clinical_history`, `chart_artifacts`,
  and derived `active_problems` / `meds_allergies` / `recent_vitals_labs`.
- `GET /programs/{program_code}/candidates`
- `GET /icd/{code}` — ICD reference row.
- `GET /pharmacies`

SQL (POST): `POST /query` with JSON body `{"sql": "SELECT ..."}` — **read-only
SELECT**. Returns `{columns, row_count, rows, truncated}`. This is the reliable
way to pull *all* rows for a target (REST lists default to ~10). Example:

```
curl -s -X POST "$BASE/query" -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT * FROM referrals WHERE batch_id='ORTHO-JUN-01' ORDER BY referral_id"}'
```

Discover targets with `SELECT DISTINCT ...` (e.g. distinct `roster_id`,
`batch_id`, `program_code`) — the DB holds many work units; only the named one is
in scope.

## Table schema (SQLite)

- **patients**(patient_id PK, first_name, last_name, dob, phone, email, language,
  address, existing_chart 0/1, preferred_contact, emergency_contact_present 0/1)
- **coverage**(coverage_id, patient_id, payer, policy_number, group_number,
  effective_date, termination_date, network_status, service_lines (CSV), status)
  — `status` ∈ active | expired | pending | …; `service_lines` is a CSV of lines
  the policy covers (e.g. `primary_care,cardiology`).
- **pbm**(pbm_id, patient_id, payer, policy_number, active 0/1, formulary_status,
  specialty_required 0/1, status) — prescription-benefit record.
- **patient_pharmacy**(patient_id, pharmacy_id, preference_rank) — rank 1 = the
  preferred pharmacy.
- **pharmacies**(pharmacy_id PK, name, address, phone, network_status
  ∈ in_network | out_of_network)
- **lifestyle**(patient_id PK, smoking_status, alcohol_use, exercise_frequency,
  sleep_hours)
- **clinical_history**(patient_id PK, chronic_conditions (CSV), surgeries,
  medication_count, allergy_count, recent_hospitalization 0/1, risk_flags (CSV))
- **intake_rosters**(roster_id, patient_id, requested_service_date, service_line,
  source_note) — PK (roster_id, patient_id).
- **referrals**(referral_id PK, batch_id, service_line, date_received,
  patient_id, payer, insurance_id, referring_physician/practice/phone/fax,
  icd10_code, diagnosis_description, referral_reason, urgency ∈ urgent|routine,
  records_received 0/1, imaging_received 0/1, auth_required 0/1,
  auth_status ∈ approved|pending|denied, appointment_scheduled 0/1,
  appointment_date, assigned_physician, notes)
- **icd_codes**(code PK, description, chapter (e.g. `M00-M99`), service_family
  (e.g. orthopedics | pulmonary | cardiology | chronic_care | dialysis),
  laterality ∈ left|right|null)
- **documents**(document_id PK, patient_id, referral_id, transfer_id, doc_type,
  status, finalized 0/1, received_date, service_date, content_tag, notes) —
  `finalized=1` (status `final`) = a real received document; `finalized=0`
  (`draft`) does **not** count as received.
- **transfer_requests**(transfer_id PK, batch_id, patient_id, referring_facility,
  requested_start_date, requested_end_date, modality, days_requested,
  chair_window, transportation, status_note)
- **facility_capacity**(location_id, date, modality, open_chairs) — PK
  (location_id, date, modality). Cedar Ridge in-center HD locations: `CRIC-MAIN`,
  `CRIC-NORTH`. Rows exist only on clinic days.
- **program_candidates**(program_code, patient_id, candidate_date, source,
  consent_status ∈ signed|declined|missing, preferred_outreach, adherence_score,
  target_condition) — PK (program_code, patient_id).
- **chart_artifacts**(artifact_id, patient_id, artifact_type ∈ demographics |
  active_problems | vitals | labs | medications | allergies | consent |
  care_plan | outreach_preference, status ∈ current | stale | draft,
  last_updated, value_summary) — for program/chart readiness, an artifact
  "counts" only when `status = current`.

## Field → data-source quick map

- Insurance validity → `coverage` (status, effective/termination dates,
  service_lines, network_status).
- Prescription benefit → `pbm` (active, formulary_status, status, policy_number).
- Preferred pharmacy network → `patient_pharmacy` (rank 1) → `pharmacies.network_status`.
- Lifestyle risk → `lifestyle`; clinical/overall risk → `clinical_history`.
- Demographics/contactability → `patients` (address, phone, email,
  preferred_contact, emergency_contact_present, existing_chart).
- Referral clinical coding → `referrals.icd10_code` → `icd_codes`
  (service_family, chapter, laterality).
- Records/imaging/auth/scheduling → `referrals` flags.
- Packet documents → `documents` (by transfer_id/referral_id), `finalized` gate.
- Chair capacity → `facility_capacity` (sum `open_chairs` over locations on the date).
- Program candidates → `program_candidates`; chart readiness → `chart_artifacts`
  + `clinical_history`.
