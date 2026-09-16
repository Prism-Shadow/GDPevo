## Available endpoints

Base URL: `<TASK_ENV_BASE_URL>` (substituted from the task prompt)

All endpoints are read-only GET. No authentication is required.

### Patient

| Endpoint | Purpose |
|----------|---------|
| `GET /api/patients` | List all patients. Supports `?name=`, `?_id=` query params |
| `GET /api/patients/{patient_id}` | Single patient by ID |

### Clinical lists (per patient)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/patients/{patient_id}/conditions` | Active and inactive conditions |
| `GET /api/patients/{patient_id}/medications` | Active and inactive medications |
| `GET /api/patients/{patient_id}/allergies` | Active and inactive allergies |
| `GET /api/patients/{patient_id}/encounters` | Encounters (visits, transitions, etc.) |
| `GET /api/patients/{patient_id}/immunizations` | Immunization records |
| `GET /api/patients/{patient_id}/documents` | Clinical documents (echo, office notes, etc.) |
| `GET /api/patients/{patient_id}/service-requests` | ServiceRequest (orders, referrals, consults) |
| `GET /api/patients/{patient_id}/disclosures` | Disclosure records (privacy/consent for data sharing) |

### Duplicate candidates

| Endpoint | Purpose |
|----------|---------|
| `GET /api/duplicates/candidates` | List all duplicate candidate entries |
| `GET /api/duplicates/{candidate_id}` | Single duplicate candidate with match/conflict signals, linked patients, clinical previews |

### Referrals

| Endpoint | Purpose |
|----------|---------|
| `GET /api/referrals` | List all referrals |
| `GET /api/referrals/{referral_id}` | Single referral with diagnosis codes, narrative, status, authorization, dates |

### Audit logs

| Endpoint | Purpose |
|----------|---------|
| `GET /api/audit-logs` | List all audit log entries |

### ICD-10

| Endpoint | Purpose |
|----------|---------|
| `GET /api/icd10` | List all ICD-10 codes |
| `GET /api/icd10/{code}` | Single ICD-10 code with chapter, description |

### Providers

| Endpoint | Purpose |
|----------|---------|
| `GET /api/providers` | List all providers |
| `GET /api/providers/{provider_id}` | Single provider with name, role, service_line, facility, phone, fax |

### Service codes

| Endpoint | Purpose |
|----------|---------|
| `GET /api/service-codes` | List all service codes |
| `GET /api/service-codes/{code}` | Single service code validation |

### Query tips

- Use `?_id=` for exact patient ID lookup on `/api/patients`.
- Use `?name=` for substring patient name search.
- For `/api/referrals`, use a patient ID filter if the API supports it; otherwise fetch all and filter client-side.
- The `/api/audit-logs` endpoint returns all logs; filter by `candidate_id` or `patient_id` fields in the response.
