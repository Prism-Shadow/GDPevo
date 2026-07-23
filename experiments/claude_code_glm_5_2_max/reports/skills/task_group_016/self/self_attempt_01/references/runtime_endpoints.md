# Runtime Endpoints (distilled from environment_access.md)

The runtime is a synthetic clinic API. The exact base URL, allow-list, and token are **per-run** — always read the task's `environment_access.md` fresh and treat the values below as the shape, not as constants.

## Base URL
`http://task-env:9016/` — referred to in prompts as `<TASK_ENV_BASE_URL>`. Substitute the base URL from the current run's access file.

## Auth
- All `GET /api/*` endpoints are open.
- `POST /api/query` requires the header `X-Clinic-Token: <token-from-access-file>` (e.g. `synclinic-readonly`). Send the token only as a header; never as a query param.

## Endpoint inventory

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/patients` | List patients |
| GET | `/api/patients/{patient_id}` | One patient record |
| GET | `/api/cases` | List cases |
| GET | `/api/cases/{case_id}` | One case record — primary way to resolve case → patient |
| GET | `/api/observations` | Labs/vitals; filter by patient, code, status, time |
| GET | `/api/medications` | Active meds, NDC, dose/route/frequency |
| GET | `/api/allergies` | Allergens to avoid |
| GET | `/api/problems` | Problem codes |
| GET | `/api/imaging` | Imaging results (CXR, CT, etc.) |
| GET | `/api/care-registry` | Registry / risk anchors |
| GET | `/api/sdoh` | Social determinants |
| GET | `/api/protocols` | Protocol catalog |
| GET | `/api/protocols/{protocol_id}` | One protocol's logic |
| POST | `/api/query` | Filtered/joined query (needs token header) |

## Request patterns
- Resolve identifiers first: `GET /api/cases/{case_id}` → read `patient_id` from the response.
- For collection endpoints (`observations`, `medications`, …), prefer the targeted `{id}` form or a filtered `POST /api/query` body over fetching the full list.
- For observation-window tasks, filter observations by `patient_id`, target `code` (e.g. `K`), `status` (final), and the window `from`/`to`. The API surface for filtering is whatever the current run exposes; if a GET query param isn't honored, fall back to `POST /api/query` with a structured filter body.
- All timestamps returned by the runtime are ISO-8601 UTC with trailing `Z`. Echo them in the same format; do not re-interpret timezones.

## Read-only discipline
Only `GET` and the read-side `POST /api/query` are used. Never send a POST that creates, updates, or orders. If an endpoint outside the allow-list would be needed, stop and note it — do not improvise.
