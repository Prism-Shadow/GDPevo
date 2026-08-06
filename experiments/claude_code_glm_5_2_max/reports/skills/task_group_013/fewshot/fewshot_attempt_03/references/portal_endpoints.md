# Portal Endpoint Reference

The Cedar Ridge Intake Coordination Portal is a shared, read-only data source for
intake, referral, transfer, chart, and program data. This reference documents the
endpoint contract so you can gather data efficiently and write reconciling SQL when
the list endpoints are unwieldy.

## Connection

- Resolve the base URL from `environment_access.md` (the `<TASK_ENV_BASE_URL>`
  placeholder in a task prompt points at this same portal). All requests are
  unauthenticated HTTP GET/POST.
- Use **only** the endpoints listed in `environment_access.md`. Never call
  `/health` or any reset/reseed endpoint.
- All responses are JSON. List endpoints return `{ "count": N, "<collection>": [ ... ] }`.
- Identifiers (patient, referral, transfer, document, pharmacy, insurance, batch,
  roster, program) are **uppercase** strings. Echo them back exactly as the portal
  returns them.

## GET endpoints

| Method / path | Returns | Use it for |
|---|---|---|
| `GET /` | HTML landing page | sanity check only |
| `GET /patients` | `patients[]` | patient identity (see fields below) |
| `GET /patients/{patient_id}` | single patient object | one patient's identity |
| `GET /referrals` | `referrals[]` | referral rows — **filter by `batch_id`** |
| `GET /referrals/{referral_id}` | single referral object | one referral |
| `GET /transfers` | `transfers[]` | transfer rows — **filter by `batch_id`** |
| `GET /transfers/{transfer_id}` | single transfer object | one transfer |
| `GET /documents` | `documents[]` | packet/chart docs — filter by `patient_id` / `transfer_id` / `referral_id` |
| `GET /chart/{patient_id}` | chart bundle | chart artifacts, active problems, clinical history, vitals/labs, meds/allergies |
| `GET /programs/{program_code}/candidates` | `candidates[]` | enrollment-panel candidate list |
| `GET /icd/{icd10_code}` | `icd` object | chapter, service_family, laterality, description |
| `GET /pharmacies` | `pharmacies[]` | pharmacy network_status lookup |

### Response field schemas (field names only — never assume row values)

- **patient**: `patient_id, first_name, last_name, dob, address, phone, email,
  language, preferred_contact, emergency_contact_present, existing_chart`
- **referral**: `referral_id, batch_id, service_line, date_received, patient_id,
  payer, insurance_id, referring_physician, referring_practice, referring_phone,
  referring_fax, icd10_code, diagnosis_description, referral_reason, urgency,
  records_received, imaging_received, auth_required, auth_status,
  appointment_scheduled, appointment_date, assigned_physician, notes`
- **transfer**: `transfer_id, batch_id, patient_id, modality, days_requested,
  chair_window, requested_start_date, requested_end_date, referring_facility,
  transportation, status_note`
- **document**: `document_id, patient_id, referral_id, transfer_id, doc_type,
  content_tag, status, finalized, received_date, service_date, notes`
- **chart bundle**: `patient` (identity), `active_problems[]`, `chart_artifacts[]`,
  `meds_allergies[]`, `recent_vitals_labs[]`, `clinical_history { patient_id,
  chronic_conditions, surgeries, risk_flags, recent_hospitalization, allergy_count,
  medication_count }`
- **program candidate**: `patient_id, program_code, target_condition, source,
  candidate_date, consent_status, existing_chart, adherence_score,
  preferred_outreach, first_name, last_name, dob, phone, email`
- **icd**: `code, chapter, description, laterality, service_family`
- **pharmacy**: `pharmacy_id, name, address, phone, network_status`

## POST /query — read-only SQL

For cross-table reconciliation (duplicate detection, shared-insurance joins,
capacity lookups, roster metadata, coverage/PBM/lifestyle joins), use the SQL
endpoint. Request body uses the **`sql`** field (not `query`):

```
POST /query
Content-Type: application/json
{"sql": "SELECT referral_id, patient_id FROM referrals WHERE batch_id = '<batch_id>' ORDER BY referral_id"}
```

Response: `{ "columns": [...], "row_count": N, "rows": [...], "truncated": bool }`.
If `truncated` is true, narrow your query (add `WHERE`/`LIMIT`) — you are missing
rows.

### Underlying tables (schema reference)

`chart_artifacts`, `clinical_history`, `coverage`, `documents`,
`facility_capacity`, `icd_codes`, `intake_rosters`, `lifestyle`,
`patient_pharmacy`, `patients`, `pbm`, `pharmacies`, `program_candidates`,
`referrals`, `transfer_requests`. (Plus `sqlite_sequence` — ignore.)

Inspect any table's columns with
`SELECT * FROM <table> LIMIT 1` before joining. Tables not exposed by a friendly
GET endpoint (e.g. `coverage`, `pbm`, `lifestyle`, `facility_capacity`,
`intake_rosters`, `patient_pharmacy`) are reachable **only** through `/query`.

## Critical gathering rules

1. **Filter to scope.** List endpoints return *every* record across all
   batches/rosters/programs, including distractor rows from unrelated batches.
   Always restrict to the task's `batch_id` / `roster_id` / `program_code`.
   Re-check your filtered count against the count the task implies.
2. **Pull every related record per in-scope entity.** A referral needs its
   patient, chart, ICD metadata, documents, coverage, and authorization. A
   transfer needs its patient, documents (packet), and facility capacity. A
   program candidate needs its chart and clinical history. Missing a related
   record is the most common cause of wrong blocker/issue codes.
3. **Prefer SQL for joins and set logic.** Duplicates, shared-insurance anomalies,
   and capacity-on-date lookups are far less error-prone as SQL than as
   client-side filtering of large list responses.
4. **Roster metadata is in the environment, not the prompt.** A new-patient
   access task's `requested_service_date` and `service_line` come from the
   `intake_rosters` record keyed by `roster_id` (fetch via `/query`), not from the
   prompt text.
