# Runtime Endpoints (generalized reference)

This file describes the clinic runtime API shape shared across runs. The **per-run** specifics — base URL, the exact allowed-endpoint list, and any auth header/token — live in that run's `environment_access.md`. Always read that file first and treat it as authoritative; the lists below describe the shape and semantics observed in the training run so you know what each endpoint returns.

## Base URL
Provided in `environment_access.md` (training run: `http://task-env:9016/`). Substitute it wherever a prompt writes `<TASK_ENV_BASE_URL>`. Do not hardcode it in any response or skill output.

## GET endpoints (read-only)

All return JSON. List endpoints return `{count, items}`; detail endpoints return a single object or a bundled object.

| Endpoint | Returns | Notes |
|---|---|---|
| `GET /api/patients` | `{count, items[]}` of patient records | Fields: `patient_id`, `fhir_id`, `name`, `sex`, `birth_date`, `age`. |
| `GET /api/patients/{patient_id}` | single patient record | Use to confirm demographics (e.g. pediatric vs adult). |
| `GET /api/cases` | `{count, items[]}` of case summaries | Fields: `case_id`, `case_type`, `patient_id`, `service_date`, `status`, `summary`. **Contains distractor cases** (summaries say "Synthetic distractor"); never select by type/summary alone. |
| `GET /api/cases/{case_id}` | **case bundle** — the primary source | Bundles `case`, `findings[]` (each `finding_key`/`finding_value`/`source_id`), `imaging[]`, `medications[]`, `allergies[]`, `problems[]`, `care_registry`, `sdoh`, etc. `findings[].source_id` are your evidence identifiers. |
| `GET /api/observations` | `{count, items[]}` of FHIR-like observations | Supports a `patient_id` query param. Row fields: `observation_id`, `patient_id`, `case_id`, `code` (LOINC), `display`, `category`, `effective_time`, `status`, `value_number`, `value_text`, `unit`, `interpretation`, `source`. Filter on `status:"final"` and on the protocol's authoritative code. |
| `GET /api/medications` | list of medication records | Cross-check against allergies before recommending. |
| `GET /api/allergies` | list of allergy records | Each has `allergen`, `reaction`, `status` (`active`/`inactive`). Only `active` allergies constrain the plan. |
| `GET /api/problems` | problem list | Used by care-management routing for priority problem codes. |
| `GET /api/imaging` | imaging studies | Fields: `imaging_id`, `study`, `impression`, `status`, `performed_at`. Use the impression text for red-flag / safety reasoning. |
| `GET /api/care-registry` | care-management registry entries | Feeds risk tier / program routing. |
| `GET /api/sdoh` | social determinants | Transportation, financial, food, medication-access barriers; member-disclosure items. |
| `GET /api/protocols` | `{count, items[]}` of protocol summaries | Fields: `protocol_id`, `title`, `version`. |
| `GET /api/protocols/{protocol_id}` | **protocol body** — decision logic | Carries `controlled_codes` (LOINC/NDC), thresholds, `urgent_branch` criteria, gates, and repletion/follow-up rules. Treat as source of truth for the enum outcomes. |

## POST /api/query (read-only SQL)

- Requires the auth header from `environment_access.md` (training run: `X-Clinic-Token: synclinic-readonly`). Without it the call returns `401`.
- Body: `{"sql": "SELECT ... FROM <table> WHERE ..."}`. The `sql` field must be a non-empty string.
- Response: `{columns, rows, count, truncated}`. If `truncated` is true, narrow the query (date/code filters) or page.
- Use for precise joins/filters the list endpoints make awkward, e.g. "final serum-potassium observations for patient P within [from, to)".

## Naming conventions to rely on
- Case ids: `CASE-<DOMAIN>-<NNN>`; distractor cases use `CASE-D<NNNN>` and "Synthetic distractor" summaries. Match the prompt's case id exactly.
- Patient ids: `PAT-<NNNN>`.
- Observation ids: `OBS-<...>`; imaging ids: `IMG-<...>`; visit/finding source ids: `VISIT-<...>`, `OBS-<...>`, `ALG-<...>`.
- Protocol ids: `<DOMAIN>-<YEAR>` (e.g. `RESP-CAP-2026`, `K-REPLETION-2026`).

## Read-only discipline
No endpoint writes state. `POST /api/query` is the only non-GET and it is read-only SQL. Never attempt to create/update/delete a resource or "place an order"; emit recommendations in JSON only.
