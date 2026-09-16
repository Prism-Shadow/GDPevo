# EHR API Catalog

Base URL is provided in each task prompt as `<TASK_ENV_BASE_URL>`.

## Endpoint Index

### Patient Resources

| Endpoint | Key response fields |
|---|---|
| `GET /api/patients` | `[{patient_id, enterprise_mrn, display_name, given_name, family_name, dob, sex, insurance_id, phone, address_line1, address_city, address_state, address_zip, primary_care_provider_id, marital_status, language, deceased_boolean}]` |
| `GET /api/patients/{patient_id}` | Single patient object with fields above |
| `GET /api/patients/{patient_id}/conditions` | `[{condition_id, code, description, normalized_key, clinical_status, verification_status, category, onset_date, recorded_date, source, patient_id}]` |
| `GET /api/patients/{patient_id}/medications` | `[{medication_id, medication, dose, route, frequency, normalized_key, status, category, start_date, patient_id}]` |
| `GET /api/patients/{patient_id}/allergies` | `[{allergy_id, allergen, reaction, severity, normalized_key, clinical_status, verification_status, category, recorded_date, patient_id, source}]` |
| `GET /api/patients/{patient_id}/encounters` | `[{encounter_id, date, type, signed_status, provider_id, diagnosis_codes, medications_mentioned, care_plan_tag, patient_id, reason}]` |
| `GET /api/patients/{patient_id}/immunizations` | `[{immunization_id, vaccine, date, status, patient_id}]` |
| `GET /api/patients/{patient_id}/documents` | `[{document_id, type, date, status, patient_id, source_provider_id, description}]` |
| `GET /api/patients/{patient_id}/disclosures` | `[{disclosure_id, date, status, purpose, recipient_provider_id, patient_id}]` |
| `GET /api/patients/{patient_id}/service-requests` | `[{service_request_id, patient_id, status, intent, priority, service_code, requester_provider_id, performer_provider_id, authored_on, occurrence_date, reason_codes, sbar_text}]` |

### Duplicate Resources

| Endpoint | Key response fields |
|---|---|
| `GET /api/duplicates/candidates` | `[{candidate_id, primary_patient_id, possible_duplicate_patient_id, status, match_signals, conflict_signals, merge_target_patient_id, merge_source_patient_id}]` |
| `GET /api/duplicates/{candidate_id}` | Single duplicate candidate with fields above, plus `[{candidate_id, primary_patient_id, possible_duplicate_patient_id, status, match_signals, conflict_signals, decision, merge_target_patient_id, merge_source_patient_id, demographic_matches, demographic_conflicts, evidence_document_ids, evidence_audit_ids, active_condition_preview_keys, active_medication_preview_keys, active_allergy_preview_keys}]` |

### Referral Resources

| Endpoint | Key response fields |
|---|---|
| `GET /api/referrals` | `[{referral_id, patient_id, batch_id, service_line, diagnosis_code, diagnosis_narrative, requested_date, status, urgency, authorization_status, receiving_provider_id, referring_provider_id, office_note_received, echo_received, echo_document_id}]` |
| `GET /api/referrals/{referral_id}` | Single referral with fields above, plus `[{referral_id, patient_id, ... , allergy_form, sbar_coverage}]` |

### Audit Resources

| Endpoint | Key response fields |
|---|---|
| `GET /api/audit-logs` | `[{audit_id, timestamp, action, entity_type, entity_id, user, detail}]` |

### Provider Resources

| Endpoint | Key response fields |
|---|---|
| `GET /api/providers` | `[{provider_id, name, role, service_line, facility, phone, fax}]` |
| `GET /api/providers/{provider_id}` | Single provider with fields above |

### ICD-10 Resources

| Endpoint | Key response fields |
|---|---|
| `GET /api/icd10` | `[{code, description, chapter}]` |
| `GET /api/icd10/{code}` | Single code with `{code, description, chapter}` |

### Service Code Resources

| Endpoint | Key response fields |
|---|---|
| `GET /api/service-codes` | `[{code, description, service_line}]` |
| `GET /api/service-codes/{code}` | Single service code with fields above |

## Parallel Query Strategy

All GET endpoints are read-only. Fetch patient detail, conditions, medications,
allergies, encounters, immunizations, documents, and disclosures in a single
parallel batch for each patient. Do the same for duplicate candidates, referrals,
and supporting lookups. The API can handle concurrent requests.

## Normalized Key Convention

Many clinical records include a `normalized_key` field. This is a stable string
identifier that normalizes display-text variations (e.g. "Diabetes Type 2" and
"Type 2 DM" both map to `diabetes_type_2`). Always prefer the `normalized_key`
when building union sets or comparing records across patients.
