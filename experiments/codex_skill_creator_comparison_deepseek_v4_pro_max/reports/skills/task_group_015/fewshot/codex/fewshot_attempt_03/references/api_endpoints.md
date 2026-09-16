# EHR API Endpoint Reference

All endpoints are read-only GET at `{BASE_URL}/api/...`.

## Patients

| Endpoint | Returns |
|---|---|
| `/patients` | Array of patient summaries (id, enterprise_mrn, given_name, family_name, dob, sex, phone, address, insurance_id, primary_care_provider_id) |
| `/patients/{id}` | Single patient detail |
| `/patients/{id}/conditions` | Active conditions (code, description, normalized_key, clinical_status, onset_date) |
| `/patients/{id}/medications` | Active medications (name, dose, route, frequency, normalized_key, status) |
| `/patients/{id}/allergies` | Active allergies (allergen, reaction, severity, normalized_key, status, source) |
| `/patients/{id}/encounters` | Encounters (id, date, type, signed_status, provider_id, diagnosis_codes, medications_mentioned, care_plan_tag) |
| `/patients/{id}/immunizations` | Immunizations (id, date, vaccine) |
| `/patients/{id}/documents` | Documents (id, type, status, date, patient_id) |
| `/patients/{id}/disclosures` | Disclosures (id, date, status, purpose, recipient_provider_id) |
| `/patients/{id}/service-requests` | ServiceRequests (id, status, intent, priority, service_code, requester_provider_id, performer_provider_id, authored_on, occurrence_date, reason_codes) |

## Duplicates

| Endpoint | Returns |
|---|---|
| `/duplicates/candidates` | Array of duplicate candidate summaries |
| `/duplicates/{candidate_id}` | Single duplicate candidate (status, primary_patient_id, possible_duplicate_patient_id, match_signals, conflict_signals, duplicate_preview_conditions, duplicate_preview_medications, duplicate_preview_allergies, document_ids, audit_ids) |

## Referrals

| Endpoint | Returns |
|---|---|
| `/referrals` | Array of referral summaries; can filter by `?batch_id=` query param |
| `/referrals/{id}` | Single referral (id, patient_id, batch_id, service_line, diagnosis_code, diagnosis_narrative, status, authorization_status, urgency, requested_date, receiving_provider_id, document_statuses, allergy_info) |

## ICD-10

| Endpoint | Returns |
|---|---|
| `/icd10` | Array of ICD-10 code summaries (code, description, chapter) |
| `/icd10/{code}` | Single ICD-10 detail |

## Providers

| Endpoint | Returns |
|---|---|
| `/providers` | Array of provider summaries |
| `/providers/{id}` | Single provider (id, name, role, service_line, facility, phone, fax) |

## Audit & Service Codes

| Endpoint | Returns |
|---|---|
| `/audit-logs` | Audit log entries (id, patient_id, action, timestamp) |
| `/service-codes` | Array of service code summaries (code, description, service_line) |
| `/service-codes/{code}` | Single service code detail |

## Usage Conventions

- Use the base URL exactly as provided via `<TASK_ENV_BASE_URL>` in the prompt.
- Parallelize independent queries (e.g., fetch both patients' conditions at once).
- Duplicate preview fields (e.g., `duplicate_preview_conditions`) may be less complete than the active-list endpoints; always fetch the patient endpoints for the authoritative clinical union.
