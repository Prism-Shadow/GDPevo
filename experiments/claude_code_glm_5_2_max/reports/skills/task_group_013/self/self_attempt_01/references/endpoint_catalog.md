# Portal Endpoint Catalog

Base URL is given in `environment_access.md` (a running HTTP service). No auth.
Use only these endpoints. Never call `/health` or any reset/reseed endpoint.

## REST GET endpoints

| Method & path | Purpose | Notes on params / response |
|---|---|---|
| `GET /` | HTML index | Lists panels; useful only to confirm the service is up and to see filter options. |
| `GET /patients` | Patient list | `q` (name or id), `limit` (default low — raise it). Returns `{"count", "patients":[…]}`. |
| `GET /patients/{patient_id}` | **Patient hub** | Aggregates `patient`, `coverage`, `pbm`, `pharmacies`, `lifestyle`, `clinical_history`, `rosters`, `referrals`, `transfers`, `documents`, `program_candidates`, `chart_artifacts`. Primary source for patient-scoped tasks. |
| `GET /referrals` | Referral list | `batch_id`, `service_line` (`orthopedics`/`pulmonary`/`cardiology`/…), `limit`. Returns `{"count","referrals":[…]}`. |
| `GET /referrals/{referral_id}` | Referral detail | Single referral row (same fields as the list item). |
| `GET /transfers` | Transfer list | `batch_id`, `limit`. Returns `{"count","transfers":[…]}`. |
| `GET /transfers/{transfer_id}` | Transfer detail | Single transfer row. |
| `GET /documents` | Document list | Filter client-side by `patient_id`/`referral_id`/`transfer_id`/`doc_type`. Returns `{"count","documents":[…]}`. Each doc has `status`, `finalized`, `received_date`, `content_tag`, `doc_type`. |
| `GET /chart/{patient_id}` | Chart record | `active_problems`, `meds_allergies`, `recent_vitals_labs`, `chart_artifacts`, `clinical_history`, `patient`. Used for chart-action and missing-artifact decisions. |
| `GET /programs/{program_code}/candidates` | Program candidates | Returns `{"candidates":[…]}` — one row per current candidate. Use the code from the prompt. |
| `GET /icd/{code}` | ICD-10 metadata | Returns `{"icd":{code, description, chapter, service_family, laterality}}`. `laterality` is `null` or a side. |
| `GET /pharmacies` | Pharmacy directory | Returns `{"count","pharmacies":[…]}` with `network_status` (`in_network`/`out_of_network`). Join on `pharmacy_id`. |

## Read-only SQL: `POST /query`

- **Body**: JSON `{"sql": "SELECT …"}`. Plain form-encoding returns `{"error":"invalid json"}`.
- **Response**: `{"columns":[…], "row_count":N, "rows":[{…}], "truncated":bool}`.
- **Read-only**: `SELECT` only. Use for joins, grouping, and counts across the full dataset.
- Check `truncated`; if `true`, narrow the query or fetch in pages.

## Working with list endpoints

List endpoints default to a small `limit`. For a scoped batch, pass the scope filter
(`?batch_id=…` or the program path) **and** a generous `limit`, then verify the returned
`count` matches the number of rows you actually received; if `count` > rows returned, keep
paging / raising `limit` until the set is complete. Distractor and out-of-scope rows appear
in unfiltered lists — always filter on the prompt's scope identifier.
