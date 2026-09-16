# Harborview Synthetic Clinic API Reference

## Base URL

Read `environment_access.md` from the task workspace to discover the current
`<TASK_ENV_BASE_URL>` and the exact list of allowed endpoints. Every run
receives a task-specific copy of that file. Use its values verbatim.

## Endpoints

### Patient and Case Lookup

- `GET /api/patients` — list all patients
- `GET /api/patients/{patient_id}` — single patient record
- `GET /api/cases` — list all cases
- `GET /api/cases/{case_id}` — single case record; provides the linked `patient_id`

### Clinical Data (related through patient or case)

- `GET /api/observations` — lab and vital-sign observations
- `GET /api/medications` — active and historical medication orders
- `GET /api/allergies` — documented allergy/intolerance records
- `GET /api/problems` — active problem-list entries
- `GET /api/imaging` — imaging studies and reports
- `GET /api/care-registry` — risk scores and enrollment data
- `GET /api/sdoh` — social determinants of health flags

### Protocol and Query

- `GET /api/protocols` — list protocol identifiers
- `GET /api/protocols/{protocol_id}` — single protocol content
- `POST /api/query` — structured query endpoint for FHIR-like searches

## Observation Fields

Observations returned by the API typically include:

- `id` — stable observation identifier
- `code` — LOINC or local code (e.g., `"K"` for potassium, `"SpO2"`, `"GCS"`)
- `status` — `"final"`, `"preliminary"`, or `"corrected"`; only `"final"` is reliable for clinical decisions
- `valueQuantity.value` — numeric result
- `effectiveDateTime` — ISO-8601 UTC timestamp

When selecting observations, filter by case-linked patient, correct code, `"final"` status, and the applicable time window.

## Medication Fields

- `ndc` — NDC code when available
- `medicationCodeableConcept.text` — human-readable medication name
- `dosageInstruction.route` — route (PO, IV, IM)
- `dosageInstruction.timing` — frequency

## Allergy Fields

- `code.text` — allergen name (e.g., "penicillin", "sulfonamide")
- Look for "penicillin", "sulfa"/"sulfonamide", "macrolide", "tetracycline" classes.

## Care Registry Fields

- `riskScore` — numeric probability (0.00–1.00)
- `programEnrollment` — current program status

## SDoH Fields

Flag-like boolean or coded entries for transportation, financial-medication, financial-food, and dialysis-fatigue barriers.

## Error Handling

- If an endpoint returns 404 for a specific resource id, it means that resource does not exist in this task environment. Treat it as missing data, not a connectivity problem.
- If the base URL is unreachable, confirm the value from `environment_access.md` before concluding unavailability.
