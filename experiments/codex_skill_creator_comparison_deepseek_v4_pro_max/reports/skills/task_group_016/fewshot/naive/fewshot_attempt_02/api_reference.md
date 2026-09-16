## Harborview Synthetic Clinic API Reference

Base URL is provided via `<TASK_ENV_BASE_URL>` in the task environment config.
Credentials, when required, are listed separately for each run.

### GET /health

Returns `{"status":"ok","database_ready":true,"schema_version":"harborview-synthetic-clinic-v1","service":"harborview-synthetic-clinic"}`.
Use to confirm the environment is reachable before fetching case data.

### GET /api/cases/{case_id}

Composite case bundle. Returns a JSON object with up to ten sections:

| Section | Key | Description |
|---------|-----|-------------|
| Case metadata | `case` | `case_id`, `case_type`, `patient_id`, `service_date`, `status`, `summary` |
| Demographics | `patient` | `patient_id`, `name`, `age`, `birth_date`, `sex`, `fhir_id` |
| Clinical findings | `findings` | Array of `{"finding_key":..., "finding_value":..., "source_id":...}` triples |
| Observations | `observations` | Array of FHIR-like observation objects |
| Imaging | `imaging` | Array of imaging-study objects |
| Medications | `medications` | Array of medication-statement objects |
| Allergies | `allergies` | Array of allergy-intolerance objects |
| Problems | `problems` | Array of problem-list entries with ICD-10 codes |
| Care registry | `care_registry` | Object or null; risk score, dialysis schedule, etc. |
| Social determinants | `sdoh` | Array of SDOH domain/severity/source entries |

Observation object fields: `observation_id`, `patient_id`, `case_id`, `code`,
`display`, `category`, `status`, `effective_time` (ISO-8601 UTC), `value_number`,
`value_text`, `unit`, `interpretation`, `source`.

Imaging object fields: `imaging_id`, `patient_id`, `case_id`, `study`,
`impression`, `performed_at`, `status`.

Medication object fields: `medication_id`, `name`, `code` (RXNORM-like), `dose`,
`route`, `frequency`, `start_date`, `end_date`, `status`, `source`.

Allergy object fields: `id`, `allergen`, `reaction`, `status` (active/inactive).

Problem object fields: `id`, `code` (ICD-10), `name`, `onset_date`, `status`.

SDOH object fields: `id`, `domain`, `severity`, `evidence`, `source`.

### GET /api/protocols

Returns `{"count": N, "items": [...]}` where each item has `protocol_id`,
`title`, and `version`.

### GET /api/protocols/{protocol_id}

Returns `{"protocol_id":..., "title":..., "version":..., "body":{...}}` where
`body` contains the protocol's decision rules, thresholds, controlled codes,
and clinical pathway logic.

### GET /api/patients/{patient_id}

Returns the patient-demographics object for a single patient.

### GET /api/observations

Returns all observations across all patients. Prefer the scoped list inside
`/api/cases/{case_id}`.

### GET /api/medications, /api/allergies, /api/problems, /api/imaging, /api/care-registry, /api/sdoh

Collection endpoints returning all records. Prefer the case-scoped versions.

### POST /api/query

Structured query endpoint. May require `X-Clinic-Token` header. Payload format
varies by task.

