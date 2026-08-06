# API Contract — EHR Quality-Governance Environment

Source of truth for endpoints and shapes. Base URL and the canonical endpoint list live in `environment_access.md`; this file records the **observed response shapes** so you unwrap and field-map correctly. Re-confirm by fetching if a task surfaces a field not listed here.

## Conventions
- **List endpoints** return `{ "<plural_resource>": [ ... ] }` (single wrapper key around an array). Always unwrap that key.
- **Detail endpoints** return a bare object (no wrapper).
- **Unknown id → HTTP 404** with body `{ "error": "<resource> record not found", "status": 404 }`. This is the validity signal.
- **No query-param filtering.** `?key=value` is ignored; lists always return the full collection. Filter client-side.
- A detail call and a filtered list call return the same object shape for one entity. Use detail calls to test existence (200 vs 404).

## Patients
`GET /api/patients` → `{ "patients": [...] }`. List item (lean): `patient_id, display_name, dob, enterprise_mrn, insurance_id, phone, canonical_status`.

`GET /api/patients/{patient_id}` → bare object (full): `patient_id, display_name, given_name, family_name, suffix, dob, sex, address, phone, insurance_id, enterprise_mrn, canonical_status, canonical_patient_id, primary_care_provider_id, primary_care_provider { provider_id, name, role, service_line, facility, phone, fax }`. 404 if unknown.

### Per-patient subresources (all `{ "<plural>": [...] }`, 404 if patient unknown, empty array if none)
| Path | Wrapper | Item fields |
|---|---|---|
| `/patients/{id}/conditions` | `conditions` | `code, description, id, normalized_key, onset_date, patient_id, source, status` |
| `/patients/{id}/medications` | `medications` | `dose, frequency, id, medication, normalized_key, patient_id, route, source, status` |
| `/patients/{id}/allergies` | `allergies` | `allergen, id, normalized_key, patient_id, reaction, severity, source, status` |
| `/patients/{id}/encounters` | `encounters` | `care_plan_notes, date, diagnoses[], encounter_id, medications_mentioned[], patient_id, provider_id, signed_status, type` |
| `/patients/{id}/immunizations` | `immunizations` | `date, id, patient_id, vaccine` |
| `/patients/{id}/documents` | `documents` | `date, document_id, patient_id, source, status, type` |
| `/patients/{id}/service-requests` | `service_requests` | `authored_on, intent, occurrence_date, patient_id, performer_id, priority, reason_codes[], requester_id, sbar{assessment,background,recommendation,situation}, service_code, service_request_id, status` |
| `/patients/{id}/disclosures` | `disclosures` | `date, disclosure_id, patient_id, purpose, recipient, recipient_provider_id, status` |

Field notes:
- `status` on conditions/medications/allergies is typically `active | inactive | entered-in-error | unknown`. Default to **active only** unless the template says otherwise.
- `signed_status` on encounters is typically `signed | unsigned | amended | draft`.
- `normalized_key` (snake_case) is the canonical set element for unions/diffs and the value to sort.
- The service-request `sbar` object's four keys map 1:1 to SBAR sections (situation/background/assessment/recommendation) — presence = non-empty string.

## Audit logs
`GET /api/audit-logs` → `{ "audit_logs": [...] }`. Item: `audit_id, date, actor, event, patient_id, summary`. **No detail endpoint** — filter client-side by `patient_id` and `event` relevance. Common `event` values: `identity_review`, `external_import`, `merge_completed` (and other merge-* events).

## Duplicate candidates
`GET /api/duplicates/candidates` → `{ "duplicate_candidates": [...] }`.
`GET /api/duplicates/{candidate_id}` → bare object: `candidate_id, status, patient_ids[], match_signals[], conflict_signals[], merge_preview { preferred_target_patient_id, source_patient_id, active_condition_keys[], active_medication_keys[], active_allergy_keys[] }`. 404 if unknown.
- `status` values observed: `open`, `needs_review` (also possible: `resolved`/`merged`).
- `merge_preview.active_*_keys` are a **preview**, not authoritative — reconcile against the patients' own active-list endpoints.

## Referrals
`GET /api/referrals` → `{ "referrals": [...] }`. Item: `referral_id, batch_id, patient_id, service_line, requested_date, urgency, status, authorization_status, diagnosis_code, diagnosis_narrative, documents_received[], receiving_provider_id, coordination_note`.
`GET /api/referrals/{referral_id}` → bare object (same fields). 404 if unknown.
- `authorization_status`: `approved | pending | denied | missing | not_required | unknown`.
- `documents_received` values seen: `echocardiogram, echo, office_note, mri, xray, physical_therapy_note, insurance_card, ...`.

## ICD-10
`GET /api/icd10` → `{ "icd10": [...] }`. Item: `code, chapter, expected_terms[], requires_laterality`.
`GET /api/icd10/{code}` → bare object (same fields). **404 if unknown** — this is the `unknown_code` / invalid-code signal.
- `chapter` examples: `Musculoskeletal, Circulatory, Endocrine, Respiratory, Nervous system, ...`.
- `requires_laterality == true` codes carry laterality inside `expected_terms` (e.g. `["right knee osteoarthritis", "right knee"]`). Compare against `diagnosis_narrative` to detect laterality mismatches.

## Providers
`GET /api/providers` → `{ "providers": [...] }`. Item: `provider_id, name, role, service_line, facility, phone, fax`.
`GET /api/providers/{provider_id}` → bare object (same fields). 404 if unknown.
- `service_line` values: `orthopedics, cardiology, pulmonology, neurology, skilled_nursing, oncology, primary_care`.
- The patient detail embeds the PCP under `primary_care_provider` (same shape).

## Service codes
`GET /api/service-codes` → `{ "service_codes": [...] }`. Item: `code, display, order_kind, service_line, active`.
`GET /api/service-codes/{code}` → bare object (same fields). 404 if unknown; also treat `active == false` as invalid.
- `service_line` matches the provider service-line enum above.
