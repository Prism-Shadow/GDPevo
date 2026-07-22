# Clinic API Surface

The synthetic clinic runtime exposes a REST API. The exact endpoints available for a given run are listed in the environment-access file, but the full surface that may appear includes:

## Authentication

All requests carry an `X-Clinic-Token` header. The token value is provided in the environment-access credentials block. Requests without a valid token are rejected.

## Endpoints

### Cases

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/cases` | List all cases. Supports query parameters for filtering by patient, status, or date range. |
| GET | `/api/cases/{case_id}` | Retrieve a single case by identifier. Returns the case record including `patient_id`, status, encounter details, and associated clinical context. |

### Patients

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/patients` | List all patients. Supports query parameters for demographic filtering. |
| GET | `/api/patients/{patient_id}` | Retrieve a single patient by identifier. Returns demographics, contact information, and summary clinical context. |

### Observations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/observations` | List observations. Supports query parameters for `patient`, `code` (LOINC or local code), `date` range, and `status`. Observations have `status` values including `final`, `preliminary`, `amended`, and `cancelled`. Each observation carries an `effective_time` (ISO-8601), a `value` (quantity or coded), and a `code` identifying the measurement type. |

### Medications

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/medications` | List medication orders. Supports query parameters for `patient`, `status` (active, completed, discontinued), and `date` range. Each medication record includes the drug name, NDC code, dose, route, frequency, and ordering context. |

### Allergies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/allergies` | List documented allergies and intolerances. Supports query parameters for `patient`. Each record includes the allergen (drug class or specific agent), reaction type, severity, and onset date. Common allergen classes include `penicillin`, `sulfonamide`, `macrolide`, and `tetracycline`. |

### Imaging

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/imaging` | List imaging studies. Supports query parameters for `patient`, `modality` (e.g., CXR, CT), and `date` range. Each record includes the study type, report text, impression, and study date. |

### Problems

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/problems` | List active and historical problems (diagnoses) for a patient. Supports query parameters for `patient` and `status`. |

### Care Registry

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/care-registry` | List care management registry entries. Supports query parameters for `patient`. Includes risk scores, program enrollment status, and care management flags. |

### Social Determinants (SDOH)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sdoh` | List social determinants of health screenings. Supports query parameters for `patient`. Includes transportation barriers, financial barriers (food, medication), housing status, and other social-context facts. |

### Protocols

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/protocols` | List available clinical protocols. Supports query parameters for `domain` (e.g., respiratory, head-injury, electrolyte, care-management). |
| GET | `/api/protocols/{protocol_id}` | Retrieve a specific protocol by identifier. Returns the full protocol text including decision thresholds, inclusion/exclusion criteria, recommended actions, and evidence citations. |

### Structured Query

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/query` | Submit a structured query with a JSON body containing filter criteria. Used when GET parameter filtering is insufficient or when cross-resource queries are needed. Request body format is endpoint-specific. |

## Response conventions

- All responses are JSON (`Content-Type: application/json`)
- Resource identifiers are stable strings (e.g., `case-abc123`, `obs-xyz789`)
- Timestamps use ISO-8601 UTC format with trailing `Z`
- Numeric values carry unit annotations inline (e.g., `"value": 3.8, "unit": "mmol/L"`)
- List endpoints return paginated results; use query parameters to narrow the result set
