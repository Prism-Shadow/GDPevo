# EHR API Endpoint Map

Base URL: `<TASK_ENV_BASE_URL>` (replace at solve time)

## Patient endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/patients` | List/search patients |
| GET | `/api/patients/{patient_id}` | Patient demographics, PCP, insurance, canonical status |
| GET | `/api/patients/{patient_id}/conditions` | Active/inactive conditions with `normalized_key`, ICD code, source |
| GET | `/api/patients/{patient_id}/medications` | Active/inactive medications with `normalized_key`, dose, route |
| GET | `/api/patients/{patient_id}/allergies` | Allergies with `normalized_key`, allergen, reaction, severity |
| GET | `/api/patients/{patient_id}/encounters` | Encounters with date, type, diagnoses, signed_status, care_plan_notes |
| GET | `/api/patients/{patient_id}/immunizations` | Immunization records with date and vaccine |
| GET | `/api/patients/{patient_id}/documents` | Documents with type, status, date, source |
| GET | `/api/patients/{patient_id}/service-requests` | ServiceRequest records with reason_codes, SBAR |
| GET | `/api/patients/{patient_id}/disclosures` | Disclosure records with status, purpose, recipient |

## Duplicate-candidate endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/duplicates/candidates` | List duplicate candidates |
| GET | `/api/duplicates/{candidate_id}` | Match/conflict signals, merge preview with clinical key unions |

## Referral endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/referrals` | List all referrals (filter client-side by batch_id) |
| GET | `/api/referrals/{referral_id}` | Referral detail: diagnosis, auth status, documents received, urgency |

## Code-validation endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/icd10` | ICD-10 code directory |
| GET | `/api/icd10/{code}` | Code chapter, expected_terms, requires_laterality |
| GET | `/api/service-codes` | Service-code directory |
| GET | `/api/service-codes/{code}` | Service code detail with service_line |

## Provider directory

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/providers` | List all providers |
| GET | `/api/providers/{provider_id}` | Provider name, role, facility, phone, fax, service_line |

## Audit logs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/audit-logs` | All audit log entries (filter client-side by patient_id) |

## Key field conventions

- `normalized_key`: Canonical identifier for a clinical item (condition, medication, allergy). Use this for set operations and sorting, not free-text descriptions.
- `status` on conditions/medications/allergies: Only `active` records count toward clinical unions. Inactive/entered-in-error records go to `excluded_distractors`.
- `canonical_status` on patients: `active` is the canonical/primary; `duplicate` or `possible_duplicate` is the secondary/source.
- `signed_status` on encounters: `signed` and `amended` are valid for evidence; `draft` and `unsigned` may need follow-up.
