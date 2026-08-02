# Runtime environment: endpoints & retrieval strategy

Read the actual base URL, credentials, and allowed-endpoint list from the run's
`environment_access.md`. Do **not** assume a fixed host. Observed runs exposed a
synthetic FHIR-like clinic at `<TASK_ENV_BASE_URL>` with `credentials: none`.

## Endpoint catalog (GET unless noted)

| Endpoint | Returns | Use it for |
|---|---|---|
| `/api/patients` , `/api/patients/{patient_id}` | patient demographics | confirming a patient; list is full of distractors |
| `/api/cases` | all cases (targets **and** `CASE-D30xx` distractors) | locating a case type; note `case_type` |
| `/api/cases/{case_id}` | **full joined bundle** for one case | **primary source** — see below |
| `/api/observations` | global observation list | cross-check only; filter hard |
| `/api/medications` | global medication list | cross-check only |
| `/api/allergies` | global allergy list | cross-check only |
| `/api/problems` | global problem list | cross-check only |
| `/api/imaging` | global imaging list | cross-check only |
| `/api/care-registry` | care-management registry rows | cross-check only |
| `/api/sdoh` | social-determinants rows | cross-check only |
| `/api/protocols` | protocol index (id, title, version) | find the protocol id |
| `/api/protocols/{protocol_id}` | protocol `body` with thresholds & codes | **apply its rules** |
| `POST /api/query` | — | **unusable**: returns `invalid or missing clinic token` under `credentials: none`. Ignore it. |

## The one call that matters: `GET /api/cases/{case_id}`

It returns everything for the case, already joined:

```
{ case, patient, findings[], observations[], medications[],
  allergies[], problems[], imaging[], care_registry, sdoh[] }
```

- `findings[]` are `{finding_key, finding_value, source_id}` — a curated digest of the
  clinically relevant facts, each with a citable `source_id`.
- `patient.patient_id` is the answer's `patient_id`.
- The bundle is case-scoped but **still contains distractors**: rows tagged with the case
  yet belonging to another `patient_id`, non-target codes, and non-`final` statuses.
  Filter as described in SKILL.md.

## Global list endpoints support server-side filters

`/api/observations?patient_id=PAT-XXXX&code=K&status=final` narrows the global feed. Handy
to double-check the bundle, but the filters do **not** apply the time window or exclude
every distractor status by default — finish the filtering yourself. The lists are mostly
"generated distractor feed" rows; never answer from them without matching the target
`patient_id`.

## case_type → protocol_id (observed)

| `case.case_type` | `protocol_id` |
|---|---|
| `acute_respiratory` | `RESP-CAP-2026` |
| `pediatric_head_injury` | `PEDS-HEAD-2026` |
| `potassium_repletion` | `K-REPLETION-2026` |
| `observation_window` | `OBS-WINDOW-2026` |
| `care_management` | `CM-HIGH-RISK-2026` |

For an unseen `case_type`, list `/api/protocols` and match by scope/title, then apply that
protocol's `body` the same way.
