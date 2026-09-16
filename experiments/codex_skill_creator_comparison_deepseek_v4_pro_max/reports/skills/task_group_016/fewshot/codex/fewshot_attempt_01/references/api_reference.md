# Clinic API Reference

## Base URL

```
{TASK_ENV_BASE_URL}
```

The exact URL is provided in the task's environment access document. No credentials
are required; all endpoints are read-only.

## Endpoints

### GET /api/cases

List all cases. Each entry has case_id, case_type, patient_id, service_date, status,
and summary.

Query parameters:
- `case_type` — filter by type
- `patient_id` — filter by patient
- `status` — filter by status

Response: `{"count": N, "items": [...]}`

### GET /api/cases/{case_id}

The primary endpoint for protocol assessment tasks. Returns a complete case bundle.

| Section | Type | Description |
|---|---|---|
| `case` | object | case_id, case_type, patient_id, service_date, status, summary |
| `patient` | object | patient_id, name, age, birth_date, sex, fhir_id |
| `findings` | array | Each entry: finding_key, finding_value, source_id |
| `observations` | array | observation_id, patient_id, case_id, code, display, category, status, effective_time, interpretation, value_number, value_text, unit, source |
| `imaging` | array | imaging_id, patient_id, case_id, study, impression, performed_at, status |
| `medications` | array | medication_id, patient_id, name, code, dose, route, frequency, status, start_date, end_date, source |
| `allergies` | array | id, patient_id, allergen, reaction, status |
| `problems` | array | id, patient_id, code, name, onset_date, status |
| `sdoh` | array | id, patient_id, domain, severity, evidence, source |
| `care_registry` | object or null | risk_score, medication_count, chronic_condition_count, dialysis_schedule, recent_admission_date, program_hint, patient_id, case_id |

### GET /api/patients

List all patients. Query: `?patient_id=PAT-NNNN`

### GET /api/patients/{patient_id}

Get a single patient record.

### GET /api/observations

List observations. Query parameters:
- `patient_id` — filter by patient
- `case_id` — filter by case
- `code` — filter by LOINC or custom code
- `status` — filter by status

Response: `{"count": N, "items": [...]}`

### GET /api/medications

List medications. Query: `?patient_id=PAT-NNNN`

### GET /api/allergies

List allergies. Query: `?patient_id=PAT-NNNN`

### GET /api/problems

List problems. Query: `?patient_id=PAT-NNNN`

### GET /api/imaging

List imaging studies. Query: `?patient_id=PAT-NNNN` or `?case_id=CASE-NNNN`

### GET /api/care-registry

List care registry entries. Query: `?patient_id=PAT-NNNN`

### GET /api/sdoh

List SDOH entries. Query: `?patient_id=PAT-NNNN`

### GET /api/protocols

List all available protocols. Each entry: protocol_id, title, version.

### GET /api/protocols/{protocol_id}

Get a specific protocol body. Returns decision rules, thresholds, controlled codes, and scope.

### POST /api/query

Advanced query endpoint. Use only when the case bundle endpoint is insufficient.

## Observation Status Values

- `final` — Authoritative result; the only status accepted for protocol decisions.
- `preliminary` — Not final; exclude from protocol gates.
- `entered-in-error` — Disregard entirely.
- `canceled` — Disregard entirely.

## Common Observation Codes

| Code | Display | Used In |
|---|---|---|
| `K` | Serum potassium | potassium_repletion, observation_window |
| `59408-5` | Oxygen saturation | acute_respiratory |
| `9279-1` | Respiratory rate | acute_respiratory |
| `8310-5` | Body temperature | acute_respiratory |
| `33914-3` | eGFR | potassium_repletion |
| `2823-3` | Follow-up potassium | potassium_repletion |
| `4548-4` | HbA1c | care_management |
| `2777-1` | Phosphate/Phosphorus | care_management |
| `8480-6` | Systolic BP | care_management, acute_respiratory |
| `8462-4` | Diastolic BP | care_management |
| `6298-4` | Whole blood potassium | potassium_repletion (exclude from serum K decisions) |
| `9269-2` | Glasgow coma score | pediatric_head_injury |

## Observation Categories

- `vital-sign` — Vitals (SpO2, BP, temp, RR, pulse)
- `laboratory` — Lab results (potassium, HbA1c, eGFR, phosphorus)
- `exam` — Physical exam findings (GCS, neuro exam, coordination)
- `imaging` — Radiology impression observations
- `procedure` — Procedure results (ECG)
- `survey` — Questionnaire scores (PHQ-9)
