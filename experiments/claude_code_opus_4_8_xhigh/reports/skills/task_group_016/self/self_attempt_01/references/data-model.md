# Runtime data model & endpoints

Base URL and the allowed endpoints for a run are given in `environment_access.md`
(e.g. `GDPEVO_ENV_BASE_URL=http://.../`, `Credentials: none`). Use only the
endpoints listed there. All observed responses are JSON; list endpoints return
`{ "count": N, "items": [...] }`.

## Endpoints (GET unless noted)
- `/api/patients` , `/api/patients/{patient_id}` — patient demographics.
- `/api/cases` — all cases (real **and** distractors); `/api/cases/{case_id}` —
  **aggregated bundle** (see below). This is the primary retrieval per task.
- `/api/observations` — labs/vitals; supports `?case_id=` and `?patient_id=`
  filters. Large collection; heavily seeded with distractors.
- `/api/medications`, `/api/allergies`, `/api/problems`, `/api/imaging`,
  `/api/care-registry`, `/api/sdoh` — domain collections.
- `/api/protocols` , `/api/protocols/{protocol_id}` — protocol list and the
  machine-readable protocol `body`.
- `POST /api/query` — returns `{"error": "invalid or missing clinic token"}` when
  no credentials are supplied. Do **not** depend on it; the GET endpoints cover
  everything needed.

## Case bundle: `GET /api/cases/{case_id}`
Keys observed: `case`, `findings`, `allergies`, `medications`, `observations`,
`imaging`, `care_registry` (empty arrays / `null` when not applicable).
- `case`: `{case_id, case_type, patient_id, service_date, status, summary}`.
- `findings`: list of `{finding_key, finding_value, source_id}`. This is where
  non-lab facts live — notably `current_time` (source `TASK-CLOCK-*`), `symptoms`,
  `ecg`, `renal_contraindication`, exam notes. `source_id`s are valid evidence ids.
- `observations`: same shape as the collection endpoint (below), pre-scoped to the
  case — but still verify code/status/window yourself.

## Observation shape
```
{ observation_id, patient_id, case_id, category, code, display, status,
  effective_time (ISO-8601 …Z), value_number, unit, interpretation,
  value_text, source }
```
- `status`: `final` is authoritative; `preliminary` / `entered-in-error` /
  `canceled` are excluded by protocols.
- `code`: the discriminator. Real serum potassium uses code `K`; distractor
  potassium rows may use a LOINC like `6298-4`. Always match the protocol's
  `controlled_codes` value, not just the display text.

## Medication / allergy shapes
- Medication: `{medication_id, name, code (e.g. RXNORM-…), dose, route, frequency,
  status, start_date, end_date, patient_id, source}`.
- Use the allergy list to drive allergy-aware plans; if a class is present, avoid it
  and pick the protocol's alternative.

## Protocol shape
`{protocol_id, title, version, body}`. `body` is machine-readable and varies by
protocol but commonly includes: `authoritative_statuses`, `excluded_statuses`,
`controlled_codes`, `ordering`, target thresholds, urgent/red-flag trigger lists,
follow-up timing, and dosing rules. **Always read the live body**; treat any numbers
quoted elsewhere (including this skill) as illustrative of an older version.

## Distractor patterns (must be excluded)
- Case ids `CASE-D30xx`, patient ids `PAT-D20xx`, summaries containing
  "Synthetic distractor …", and `"source": "generated distractor feed"`.
- Same-family decoys share the `case_type` of the real case, so you cannot select by
  type alone — match the exact target `case_id`/`patient_id`.
- Within the correct patient, expect wrong-code, non-`final`-status, and
  out-of-window rows mixed in with the qualifying ones.
