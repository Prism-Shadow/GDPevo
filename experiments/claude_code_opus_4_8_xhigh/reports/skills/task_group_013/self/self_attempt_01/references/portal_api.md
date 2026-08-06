# Cedar Ridge Portal — API reference

Base URL comes from `environment_access.md` (`GDPEVO_ENV_BASE_URL`, e.g.
`http://task-env:9013/`). No credentials. All data is read-only.

## Allowed endpoints (from environment_access.md)

| Method & path | Purpose | Notable params |
|---|---|---|
| `GET /` | HTML portal (human UI) | — |
| `GET /health` | readiness + `record_counts` per table | — |
| `GET /patients` | list/search patients | `q` (name or id), `limit` |
| `GET /patients/{patient_id}` | one patient | — |
| `GET /referrals` | list referrals | `batch_id`, `service_line`, `limit` |
| `GET /referrals/{referral_id}` | referral **pre-joined** with patient, icd, documents | — |
| `GET /transfers` | list transfer requests | `batch_id`, `limit` |
| `GET /transfers/{transfer_id}` | one transfer (+ related) | — |
| `GET /documents` | list documents | filters incl. `patient_id`; `limit` |
| `GET /chart/{patient_id}` | chart bundle: patient, clinical_history, chart_artifacts, active_problems, meds_allergies, recent_vitals_labs | — |
| `GET /programs/{program_code}/candidates` | program candidate roster | — |
| `GET /icd/{code}` | ICD metadata (chapter, service_family, laterality) | — |
| `GET /pharmacies` | pharmacy directory incl. `network_status` | — |
| `POST /query` | **read-only SQL** over the DB | JSON body `{"sql": "..."}` |

Default list `limit` is small (≈10). Always pass a `limit` large enough to cover
the whole batch/roster, or use `POST /query` (no implicit row cap in practice;
responses carry a `truncated` flag — widen/paginate if it is ever `true`).

## Response shapes

- List endpoints: `{"count": N, "<plural>": [ {row}, ... ]}` — e.g. `patients`,
  `referrals`, `transfers`, `documents`, `pharmacies`.
- `GET /referrals/{id}`: `{"referral": {...}, "patient": {...}, "icd": {...},
  "documents": [ {...} ]}` — one call gives everything for referral logic.
- `GET /chart/{patient_id}`: `{"patient", "clinical_history",
  "chart_artifacts", "active_problems", "meds_allergies",
  "recent_vitals_labs"}`.
- `GET /programs/{code}/candidates`: candidate rows (join to patients/chart for
  eligibility). Use the returned list as the authoritative membership.

## POST /query (read-only SQL)

Body `{"sql": "SELECT ..."}`. Success:
```json
{ "columns": ["c1","c2"], "row_count": 3, "rows": [ {...}, ... ], "truncated": false }
```
Errors:
- Non-SELECT: `{"error": "only SELECT and read-only PRAGMA statements are allowed"}`
- Bad SQL: `{"error": "database error", "detail": "no such table: nope"}`

Constraints & tips:
- Only `SELECT` and read-only `PRAGMA`. No INSERT/UPDATE/DELETE/DDL.
- Use SQLite dialect. `sqlite_master` lists tables:
  `SELECT name FROM sqlite_master WHERE type='table'`.
- `SELECT sql FROM sqlite_master WHERE name='<table>'` dumps a table's DDL.
- Integer boolean columns (`records_received`, `imaging_received`,
  `auth_required`, `appointment_scheduled`, `existing_chart`,
  `emergency_contact_present`, `finalized`, `active`, `specialty_required`,
  `recent_hospitalization`) are `0`/`1`.
- Prefer SQL for batch-wide reconciliation: duplicate detection
  (`GROUP BY patient_id, icd10_code`), shared-insurance detection
  (`GROUP BY insurance_id HAVING COUNT(DISTINCT patient_id) > 1`), capacity sums
  (`SUM(open_chairs) ... GROUP BY date`), and all summary counts.

## Reference / as-of date

There is no "clock" endpoint. When a task needs "today" (a free `as_of_date`,
document freshness, capacity vs. a future requested start), take the reference
date from, in order of preference: an explicit date in the prompt → the target's
own requested date (roster `requested_service_date`, transfer
`requested_start_date`) → the harness's current date. State the chosen date in
the corresponding output field and apply it consistently.
