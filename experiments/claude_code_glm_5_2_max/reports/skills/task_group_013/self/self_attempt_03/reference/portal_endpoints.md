# Cedar Ridge Portal — Endpoint & SQL Reference

Reference for the Cedar Ridge Intake Coordination Portal. Verified against the live environment during skill creation; re-verify field presence on first use of any task, since the portal may evolve. All requests are read-only (GET, or `POST /query` with a `SELECT`).

## Base URL & access
- Resolve the base URL from `environment_access.md` (network-reachable, **no auth**).
- Use **only** the endpoints listed in `environment_access.md`. **Do not** call `/health` or any reset/reseed endpoint.
- The `<TASK_ENV_BASE_URL>` placeholder in a task prompt resolves to this base URL.

## Universal list-endpoint behavior (read this first)
- **Silent 100-row cap by default.** `GET /patients`, `/referrals`, `/transfers`, `/documents`, `/pharmacies` return at most 100 rows when called with no/small `limit`. There is **no `truncated` flag** on GET responses, and `count` is the number *returned*, not the total.
- **Override with `?limit=`** (e.g. `?limit=1000`) to retrieve the full set, **or** filter by `batch_id` / `patient_id` to stay under the cap.
- **Always cross-check with SQL:** `SELECT COUNT(*) FROM <table> WHERE <scope>='<value>'` must equal the number of records you pulled. Mismatch ⇒ you were capped or filtered wrong.
- **Filter params observed:** `/referrals?batch_id=`, `/referrals?service_line=`, `/transfers?batch_id=`, `/patients?q=` (name or id), all with optional `&limit=`.

## REST endpoints

### `GET /patients` → `{count, patients[]}`
Patient list. Item fields: `patient_id, first_name, last_name, dob, address, phone, email, language, preferred_contact, emergency_contact_present (0/1), existing_chart (0/1)`.

### `GET /patients/{patient_id}` — detail bundle
Top-level keys: `patient, coverage, pbm, pharmacies, lifestyle, clinical_history, chart_artifacts, documents, program_candidates, referrals`.
- `coverage[]`: `payer, policy_number, group_number, network_status, status, effective_date, termination_date, service_lines (csv)`. → **insurance_status** (active+in_network+not-terminated+service_line covered ⇒ valid; else invalid/missing).
- `pbm[]`: `payer, policy_number, status, formulary_status, active, specialty_required`. → **prescription_status** (approved+covered+active ⇒ valid; else invalid/missing) and PBM policy mismatch checks.
- `pharmacies[]`: `pharmacy_id, name, network_status, preference_rank`. → **pharmacy_status** (preferred pharmacy in_network / out_of_network / unknown).
- `lifestyle`: `smoking_status, alcohol_use, exercise_frequency, sleep_hours`. → **lifestyle_risk**.
- `clinical_history`: `chronic_conditions, medication_count, allergy_count, recent_hospitalization, surgeries, risk_flags`. → **overall_risk**.
- `patient`: contact fields for `emergency_contact_missing`, `missing_address`, `preferred_contact_unavailable`.

### `GET /chart/{patient_id}` — chart bundle
Top-level keys: `patient, active_problems[], chart_artifacts[], clinical_history, meds_allergies[], recent_vitals_labs[]`.
- Used by enrollment-panel tasks: presence/recency of `active_problems`, `recent_vitals_labs`, `meds_allergies`/medications, `consent` artifact ⇒ `missing_chart_artifacts`.
- `clinical_history.recent_hospitalization` and `risk_flags` feed high-touch triggers; `chart_artifacts` may include a `consent` artifact.

### `GET /referrals[?batch_id=&service_line=&limit=]` → `{count, referrals[]}`
Referral list. Item fields: `referral_id, patient_id, batch_id, service_line, urgency, icd10_code, diagnosis_description, referral_reason, date_received, assigned_physician, referring_physician/practice/phone/fax, payer, insurance_id, auth_required (0/1), auth_status (approved/pending/denied/not_required/not_submitted), records_received (0/1), imaging_received (0/1), appointment_scheduled (0/1), appointment_date, notes`.

### `GET /referrals/{referral_id}` — detail bundle
Top-level keys: `referral, patient, icd, documents`.
- `icd`: `code, description, chapter (e.g. "S00-T88"), service_family (e.g. orthopedics), laterality`. Compare `icd.service_family` vs `referral.service_line` (chapter mismatch), `icd.description`/`laterality` vs `referral.diagnosis_description`/`referral_reason` (narrative/laterality mismatch).
- `documents[]`: supporting records/imaging for this referral.

### `GET /transfers[?batch_id=&limit=]` → `{count, transfers[]}`
Transfer list. Item fields: `transfer_id, patient_id, batch_id, modality (e.g. in_center_hemodialysis), days_requested, chair_window, requested_start_date, requested_end_date, referring_facility, transportation, status_note`.

### `GET /transfers/{transfer_id}` — detail bundle
Top-level keys: `transfer, patient, documents, capacity`.
- `documents[]`: the transfer packet (`doc_type, status, finalized, received_date, service_date, content_tag`).
- `capacity[]`: chair-availability rows for the requested start (`location_id, date, modality, open_chairs`). Sum `open_chairs` for the `requested_start_date`+`modality` across locations ⇒ `open_chairs_total` and `capacity_status`.

### `GET /documents[?limit=]` → `{count, documents[]}`
Document list. Item fields: `document_id, patient_id, referral_id, transfer_id, doc_type, status, finalized (0/1), received_date, service_date, content_tag, notes`. `content_tag` distinguishes `transfer_packet` vs referral docs. **This table is large (>100 rows) — always pass `limit` or query via SQL by `transfer_id`/`referral_id`.**

### `GET /icd/{code}` → `{icd: {code, description, chapter, service_family, laterality}}`
ICD-10 metadata for a referral's `icd10_code`. Equivalent to a row of the `icd_codes` table.

### `GET /pharmacies[?limit=]` → `{count, pharmacies[]}`
Pharmacy directory: `pharmacy_id, name, address, phone, network_status (in_network/out_of_network)`.

### `GET /programs/{program_code}/candidates` → `{candidates[]}`
Enrollment candidates. Item fields: `patient_id, program_code, target_condition, source, candidate_date, consent_status (signed/declined/missing), adherence_score, existing_chart (0/1), preferred_outreach, dob, first_name, last_name, phone, email`.

### `POST /query` — read-only SQL
- **Body key is `sql`** (not `query`): `{"sql": "SELECT ..."}`. `{"query": ...}` ⇒ `{"error":"sql is required"}`.
- Response: `{columns[], row_count, rows[], truncated}`. `row_count` and `len(rows)` are the actual returned count; **`truncated`** is a real flag — if `true`, narrow the `WHERE` or split the query.
- The SQL endpoint does **not** impose the 100-cap (it returns full result sets), but watch `truncated` for very large queries.
- Supports `PRAGMA table_info(<table>)` and `sqlite_master` for schema discovery.

## REST ↔ SQL table map
| REST | SQL table | Notes |
|---|---|---|
| `/patients`, `/patients/{id}` | `patients` (+ `coverage`, `pbm`, `lifestyle`, `clinical_history`, `patient_pharmacy`, `chart_artifacts`, `documents`, `program_candidates`, `referrals` joined by `patient_id`) | detail endpoint pre-bundles these |
| `/referrals`, `/referrals/{id}` | `referrals` (+ `icd_codes` by `icd10_code`, `documents` by `referral_id`) | |
| `/transfers`, `/transfers/{id}` | **`transfer_requests`** (+ `documents` by `transfer_id`, `facility_capacity` by date+modality) | **name mismatch** |
| `/documents` | `documents` | large table — use SQL by `transfer_id`/`referral_id` |
| `/icd/{code}` | `icd_codes` | |
| `/pharmacies` | `pharmacies` (+ `patient_pharmacy` for the patient↔pharmacy link + `preference_rank`) | |
| `/chart/{id}` | `chart_artifacts`, `clinical_history`, (+ active_problems / meds_allergies / vitals_labs tables) | |
| `/programs/{code}/candidates` | `program_candidates` | |
| (no REST) | `intake_rosters` | roster rows: `roster_id, patient_id, requested_service_date, service_line, source_note` |
| (no REST) | `facility_capacity` | `location_id, date, modality, open_chairs` |

## Full table inventory (16)
`chart_artifacts, clinical_history, coverage, documents, facility_capacity, icd_codes, intake_rosters, lifestyle, patient_pharmacy, patients, pbm, pharmacies, program_candidates, referrals, sqlite_sequence, transfer_requests`.

Use `PRAGMA table_info(<table>)` to confirm exact columns before joining.

## Distractor records
The portal intentionally mixes multiple batches/rosters/programs and includes out-of-scope rows (sometimes literally flagged `"distractor ..."` in `notes`/`status_note`). **Always filter to your scope key** and exclude any record whose `batch_id`/`roster_id`/`program_code` does not match. Confirm the in-scope count via SQL `COUNT(*)` before classifying.
