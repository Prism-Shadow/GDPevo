# Clinic Runtime API Contract

The synthetic clinic runtime is a read-only HTTP JSON API. The exact base URL,
allowed endpoints, and auth header for a given run are in that run's
`environment_access.md` — this file documents the general contract. Always defer
to `environment_access.md` when it restricts the endpoint list or changes the
auth header.

## Transport

- Base URL: from `environment_access.md` (substitute for `<TASK_ENV_BASE_URL>`).
- All GET `/api/*` endpoints are open.
- `POST /api/query` requires the run's auth header (e.g.
  `X-Clinic-Token: <value>`). A missing/incorrect header returns `401`.
- All responses are JSON. List responses are shaped
  `{ "count": N, "items": [...] }`; some cap the page size, so filter server-side
  rather than paging through everything.

## GET endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/patients` / `GET /api/patients/{patient_id}` | Patient demographics and stable identifiers. |
| `GET /api/cases` / `GET /api/cases/{case_id}` | Case list, or a full **case bundle** for one case. |
| `GET /api/observations` | Observation resources (labs + vitals). Filter by `patient_id`/`case_id`, `code`, `status`, `effective_time`. |
| `GET /api/medications` | Active and historical medications. |
| `GET /api/allergies` | Allergies with `status` (`active`/`inactive`). |
| `GET /api/problems` | Problem list. |
| `GET /api/imaging` | Imaging studies and reads. |
| `GET /api/care-registry` | Care-management registry entries. |
| `GET /api/sdoh` | Social-determinants data. |
| `GET /api/protocols` / `GET /api/protocols/{protocol_id}` | Protocol metadata, or the full protocol body with decision rules. |

## Case bundle shape

`GET /api/cases/{case_id}` returns a bundle that nests the relevant resources for
that case. Typical top-level keys:

- `case` — `{ case_id, case_type, patient_id, service_date, status, summary }`.
- `findings` — list of `{ finding_key, finding_value, source_id }`. `source_id`
  is the evidence id to cite (visit id, observation id, imaging id, …).
- `allergies` — list of `{ id, patient_id, allergen, reaction, status }`.
- `medications`, `problems`, `observations`, `imaging`, `care_registry`, `sdoh`
  — resource lists scoped to the case. `care_registry` may be `null` when the
  case is not enrolled.

## Observation resource shape

```json
{
  "observation_id": "OBS-…",
  "patient_id": "PAT-…",
  "case_id": "CASE-…",
  "category": "laboratory" | "vital_signs" | ...,
  "code": "<LOINC or local code>",
  "display": "<human-readable name>",
  "value_number": 3.0,
  "value_text": null,
  "unit": "mmol/L",
  "interpretation": "low" | "borderline" | "normal" | "high" | ...,
  "status": "final" | "preliminary" | "corrected" | ...,
  "effective_time": "2026-0…-…T…:…:…Z",
  "source": "generated distractor feed" | <case source>
}
```

Notes that drive lab-window tasks:

- `status: "final"` is the authoritative status for protocol gates; preliminary
  and other statuses are excluded.
- `code` distinguishes the target analyte (e.g. serum potassium). Map via the
  protocol's `controlled_codes` when present.
- `source: "generated distractor feed"` and ids matching `*-D…` mark distractor
  records — exclude them by scoping to the target patient/case.
- `effective_time` is ISO-8601 UTC with a trailing `Z`; use it for window
  membership and for sort ordering.

## Protocol resource shape

```json
{
  "protocol_id": "…-2026",
  "title": "…",
  "version": "2026.1",
  "body": { ... structured decision rules ... }
}
```

The `body` is protocol-specific but commonly contains: `scope`,
`authoritative_statuses`, `controlled_codes` (concept → code/enum mapping),
threshold objects (e.g. `ed_escalation` with numeric cutoffs), red-flag and
return-precaution code lists, follow-up timing (`outpatient_follow_up_hours`),
and gate definitions. Read the body fully and apply its rules literally rather
than substituting clinical judgment.

## POST /api/query

SQL-style read query. Body:

```json
{ "sql": "select <cols> from <table> where <col> = ? order by ...", "params": ["..."] }
```

- Header from `environment_access.md` is required.
- `sql` must be a non-empty string; `params` is the bind list for `?`
  placeholders. Always bind values via `params` rather than string-interpolating.
- Response: `{ "columns": [...], "rows": [...], "count": N, "truncated": bool }`.
- `truncated: true` means the result was capped — narrow the `where` clause
  (add `patient_id`/`case_id`/time bounds) instead of assuming completeness.
- Read-only: do not issue `insert`/`update`/`delete`. These tasks never mutate.
