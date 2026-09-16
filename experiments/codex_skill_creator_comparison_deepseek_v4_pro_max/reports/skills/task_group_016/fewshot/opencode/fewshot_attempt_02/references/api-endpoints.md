# Clinic REST API Endpoints

This reference describes the standard endpoints available in the synthetic clinic
runtime environment. Not all endpoints are available on every run — always read
the environment access document provided with the task to confirm which
endpoints are active.

## Patient and case lookup

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/patients` | GET | List all patients. |
| `/api/patients/{patient_id}` | GET | Full patient demographics record. |
| `/api/cases` | GET | List all cases. |
| `/api/cases/{case_id}` | GET | Case record linking patient to a clinical scenario. |

## Clinical data

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/observations` | GET | Lab results and observations. Contains LOINC-coded values, effective times, and status flags (`final`, `preliminary`, `corrected`). |
| `/api/medications` | GET | Active and past medication orders. |
| `/api/allergies` | GET | Allergy and intolerance records. Check for class allergies before recommending drugs. |
| `/api/imaging` | GET | Imaging study reports, findings, and impressions. |
| `/api/problems` | GET | Problem list entries (diagnoses). |

## Care management and social context

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/care-registry` | GET | Care management registry with risk scores, enrollment status, and program eligibility. |
| `/api/sdoh` | GET | Social determinants of health (transportation, food, financial barriers). |

## Protocol reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/protocols` | GET | List all clinical protocols by name and ID. |
| `/api/protocols/{protocol_id}` | GET | Full protocol definition with thresholds, decision gates, and recommendation rules. Always read the relevant protocol before making protocol-gated decisions. |

## Structured query

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/query` | POST | Submit a structured FHIR-like query to filter resources by patient, date range, code, status, or other parameters. |

## Key observation fields

- `code` — LOINC code (e.g. `2823-3` for serum potassium, `20565-8` for SpO2)
- `valueQuantity.value` — numeric result
- `valueQuantity.unit` — unit (`mmol/L`, `%`, `mg/dL`)
- `effectiveDateTime` — when the observation was taken (ISO-8601)
- `status` — `final`, `preliminary`, or `corrected`
- `subject.reference` — patient identifier (format: `Patient/{patient_id}`)

Only `final` status observations should be used for clinical decisions.
Preliminary results are excluded from most protocol gates.

## Typical query flow

1. `GET /api/cases/{case_id}` — get patient ID, clinical context
2. `GET /api/patients/{patient_id}` — verify patient identity
3. `POST /api/query` — filter observations by patient, code, and window
   (or `GET /api/observations` and filter client-side)
4. `GET /api/allergies` — check for contraindications
5. `GET /api/medications` — active meds for polypharmacy counts
6. `GET /api/imaging` — radiology findings
7. `GET /api/problems` — diagnosis list
8. `GET /api/protocols/{protocol_id}` — decision thresholds and gates
9. `GET /api/care-registry` — risk scores, program eligibility
10. `GET /api/sdoh` — social barriers for care management

This flow covers respiratory, head injury, electrolyte replacement, care
management routing, and lab-result gating protocol tasks.
