# Environment Contract — Clinic Runtime Navigation

General shapes for the Harborview Synthetic Clinic runtime. **Always read the
run-specific `environment_access.md`** for the actual base URL, allowed
endpoints, and required headers/token — these vary per run and the values below
are illustrative, not authoritative.

## Connection
- Base URL is given in `environment_access.md` (e.g. `http://task-env:9016/`).
- All `GET /api/*` endpoints are open.
- `POST /api/query` requires a header (`X-Clinic-Token`), whose value is in
  `environment_access.md`. Requests without it return `401`.

## Endpoints (typical)

| Method + path | Returns | Notes |
|---|---|---|
| `GET /api/patients` | `{count, items:[patient]}` | flat list |
| `GET /api/patients/{patient_id}` | patient + bundled allergies, meds, etc. | |
| `GET /api/cases` | `{count, items:[case]}` | 50+ cases incl. distractors |
| `GET /api/cases/{case_id}` | case + bundled clinical context | **primary entry**; includes `patient_id`, allergies, observations, medications, imaging, problems, `care_registry`, SDOH |
| `GET /api/observations` | `{count, items:[obs]}` | flat list; filter by patient/case/code/status |
| `GET /api/medications` | list | active meds, NDC, route, frequency |
| `GET /api/allergies` | list | allergen, reaction, status (active/inactive) |
| `GET /api/problems` | list | problem list |
| `GET /api/imaging` | list | imaging studies + findings |
| `GET /api/care-registry` | list | care-management registry facts |
| `GET /api/sdoh` | list | social determinants (transport, food, finance) |
| `GET /api/protocols` | `{count, items:[{protocol_id,title,version}]}` | protocol index |
| `GET /api/protocols/{protocol_id}` | protocol body with rules | authoritative source for thresholds, controlled_codes, authoritative_statuses |
| `POST /api/query` | `{columns, rows, count, truncated}` | SQL over the data |

## `POST /api/query` mechanics
- Body is JSON: `{"sql": "<SELECT ...>"}`. The field is **`sql`**, not `query`.
  Sending `{"query": ...}` returns `{"error":"sql must be a non-empty string"}`.
- Always send the token header from `environment_access.md`.
- Response: `{columns:[...], rows:[{...}], count, truncated}`. Check `truncated`
  and widen/limit your query if true.
- Use it for precise multi-condition filters that the flat GET lists would force
  you to filter client-side, e.g. "final potassium observations for patient P
  between two ISO timestamps," or "all active medications for case C."

## Observation resource fields (typical)
`observation_id`, `case_id`, `patient_id`, `code` (LOINC), `display`, `category`
(`laboratory`, `vital-signs`, …), `value_number`, `value_text`, `unit`,
`interpretation` (`low`/`normal`/`high`/…), `status` (`final`/`preliminary`/…),
`effective_time` (ISO-8601 UTC), `source`.

## Status & date-window discipline
- Protocols declare `authoritative_statuses` (usually `["final"]`). When a
  protocol gate depends on a lab, count only observations whose `status` is in
  that set. Exclude `preliminary`, cancelled, or entered-in-error unless the
  protocol explicitly accepts them.
- For window tasks, the window is `[from, to)` inclusive start / exclusive end.
  Compare against `effective_time`. Distractor observations outside the window,
  with the wrong code, or non-final status go in the excluded list (with the
  ordering the template specifies), not the matched list.

## Identifiers are stable
`case_id`, `patient_id`, `observation_id`, imaging IDs, registry IDs, and
`protocol_id` are stable strings. Reuse them verbatim in `evidence_ids`,
`matched_observation_ids`, etc. Never synthesize an ID that did not come from the
runtime.

## Gotchas
- Distractor cases/observations are seeded in the runtime to test filtering.
  Always scope by the target `case_id`/`patient_id` and the protocol's
  `authoritative_statuses` rather than trusting the first match.
- Allergens in the chart may be phrased loosely ("sulfonamide antibiotics",
  "penicillin"). Map them to the template's controlled `avoid_allergens` classes
  (e.g. `penicillin`, `sulfonamide`, `macrolide`, `tetracycline`) per the
  protocol's allergy rule.
- Times are ISO-8601 UTC with a trailing `Z`. Preserve that format in any
  timestamp you emit.
