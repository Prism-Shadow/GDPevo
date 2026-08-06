# Endpoint Families

The allowed endpoints and the base URL live in `environment_access.md`; it is the
authority. This file maps each endpoint family to the record type it returns and to
the packet types that typically use it, so you can plan fetches. Do not hardcode the
base URL or endpoint paths — read them from `environment_access.md`.

Field names below are the typical shapes seen in this environment. Bind to the
fields actually present in each response rather than assuming.

| Family | Endpoint(s) | Returns | Used by |
|---|---|---|---|
| Patients | `/api/patients`, `/api/patients/{id}` | demographics: id, mrn, name, dob, sex, insurance, phone, address, pcp | all packet types |
| Conditions | `/api/patients/{id}/conditions` | conditions: code, description, status, normalized_key | merge, referral, transition, SR-review |
| Medications | `/api/patients/{id}/medications` | medications: name, dose, route, frequency, status | merge, referral, transition |
| Allergies | `/api/patients/{id}/allergies` | allergies: allergen, reaction, severity, status | merge, referral, transition |
| Encounters | `/api/patients/{id}/encounters` | encounters: id, date, type, provider, signed_status, dx codes, meds mentioned | referral, transition, SR-review |
| Immunizations | `/api/patients/{id}/immunizations` | immunizations: id, date, vaccine | transition |
| Documents | `/api/patients/{id}/documents` | documents: id, type, date, status, author/facility | merge, referral, transition |
| Disclosures | `/api/patients/{id}/disclosures` | disclosures: id, date, status, purpose, recipient | transition |
| Service-requests | `/api/patients/{id}/service-requests` | ServiceRequests: id, status, intent, priority, code, requester/performer, dates, reason codes | SR-review |
| Audit-logs | `/api/audit-logs` | audit entries: id, action, patient, timestamp | merge |
| Duplicates | `/api/duplicates/candidates`, `/api/duplicates/{id}` | duplicate candidates: id, status, patient_ids, match/conflict signals, target/source | merge, SR-review |
| Referrals | `/api/referrals`, `/api/referrals/{id}` | referrals: id, batch_id, service_line, patient, provider, urgency, auth status, narrative, reason codes | referral coordination, batch audit |
| ICD-10 | `/api/icd10`, `/api/icd10/{code}` | code → description, chapter, expected laterality/narrative terms | referral, SR-review, batch audit |
| Providers | `/api/providers`, `/api/providers/{id}` | provider directory: id, name, role, service_line, facility, phone, fax | all packet types |
| Service-codes | `/api/service-codes`, `/api/service-codes/{code}` | service code → validity, service_line | SR-review |

## Fetching discipline
- Resolve the in-scope IDs from the prompt first, then chase referenced IDs.
- Use list endpoints to discover members of a batch or candidate group when the
  prompt names a batch / candidate rather than a single id; use detail endpoints to
  resolve a single id. Filter client-side when the API does not filter for you.
- Treat the API as read-only. Never POST / PUT / PATCH / DELETE.
- If an endpoint returns a value the template needs but the record lacks it, leave
  the template field at its missing-state (null / empty array / blocking flag) — do
  not guess.
