# EHR API Endpoint Inventory

Base URL: `<TASK_ENV_BASE_URL>` (replace with actual URL from task environment).

## Patient Endpoints

### GET /api/patients
List all patients. Response: array of patient summary objects with `patient_id`, `display_name`, `dob`, `enterprise_mrn`, `sex`, `insurance_id`, `primary_care_provider_id`, `phone`, `address_line_1`, `address_city`, `address_state`, `address_zip`.

### GET /api/patients/{patient_id}
Single patient detail. Response: single patient object with all fields above.

### GET /api/patients/{patient_id}/conditions
All condition records for a patient. Each record: `condition_id`, `code` (ICD-10), `description`, `normalized_key`, `status` (active|inactive|resolved|entered-in-error), `category` (problem_list|encounter_diagnosis|referral_intake), `onset_date`, `recorded_date`.

### GET /api/patients/{patient_id}/medications
All medication records. Each record: `medication_id`, `medication` (name), `normalized_key`, `status` (active|inactive|entered-in-error), `dose`, `route`, `frequency`, `start_date`.

### GET /api/patients/{patient_id}/allergies
All allergy records. Each record: `allergy_id`, `allergen`, `normalized_key`, `reaction`, `severity` (mild|moderate|severe|unknown), `status` (active|inactive|entered-in-error|unknown), `source` (patient_reported|referral_form|problem_list).

### GET /api/patients/{patient_id}/encounters
All encounter records. Each record: `encounter_id`, `date`, `type` (office_visit|care_transition|virtual|inpatient|emergency), `provider_id`, `signed_status` (signed|unsigned|amended|draft), `diagnosis_codes` (array of ICD-10 strings), `medications_mentioned` (array of medication name strings).

### GET /api/patients/{patient_id}/immunizations
All immunization records. Each record: `immunization_id`, `date`, `vaccine`, `status`.

### GET /api/patients/{patient_id}/documents
All document records. Each record: `document_id`, `type` (echocardiogram|office_note|chart_summary|authorization|medication_list|external_consult|imaging_report), `date`, `status` (final|preliminary|cancelled), `associated_provider_id`, `associated_encounter_id`.

### GET /api/patients/{patient_id}/service-requests
All service requests for a patient. Each record: `service_request_id`, `status` (draft|active|on-hold|revoked|completed|entered-in-error), `intent`, `priority`, `service_code`, `requester_provider_id`, `performer_provider_id`, `authored_on`, `occurrence_date`, `reason_codes` (array of ICD-10 strings), `narrative_body` (SBAR-structured text).

### GET /api/patients/{patient_id}/disclosures
All disclosure records. Each record: `disclosure_id`, `date`, `status` (permitted|pending|denied|expired), `purpose`, `recipient_provider_id`.

## Duplicate Candidate Endpoints

### GET /api/duplicates/candidates
List all duplicate candidates. Response: array of candidate summary objects with `candidate_id`, `candidate_status` (confirmed_duplicate|needs_review|not_duplicate), `primary_patient_id`, `possible_duplicate_patient_id`, `match_signals`, `conflict_signals`.

### GET /api/duplicates/{candidate_id}
Single duplicate candidate detail. Includes `candidate_status`, both patient IDs, `match_signals` (array of labels), `conflict_signals` (array of labels), `demographic_comparison` (object with field-by-field match/conflict data), `preview_active_condition_keys`, `preview_active_medication_keys`, `preview_active_allergy_keys`, `recommended_target_patient_id`, `recommended_disposition`.

## Referral Endpoints

### GET /api/referrals
List all referrals. Response: array of referral objects with `referral_id`, `batch_id`, `patient_id`, `service_line`, `diagnosis_code`, `diagnosis_narrative`, `requested_date`, `authorization_status` (approved|pending|denied|not_required|unknown), `referral_status` (open|closed|cancelled|draft), `urgency` (routine|urgent|stat), `performer_provider_id`, `requester_provider_id`, `office_note_received` (boolean), `echo_received` (boolean for cardiology), `imaging_received` (boolean for orthopedics), `documents` (array of document reference objects with document_id, type, status).

### GET /api/referrals/{referral_id}
Single referral detail. Includes all fields above plus `allergy_statement` (object with allergen, reaction, severity, status), `medication_highlights` (array of medication reference objects), `sbar_sections_present` (array of sbar section names).

## ICD-10 Endpoints

### GET /api/icd10
List/search ICD-10 codes. Response: array of code objects with `code`, `description`, `chapter`, `laterality` (left|right|bilateral|null).

### GET /api/icd10/{code}
Single ICD-10 code lookup. Response includes `code`, `description`, `chapter`, `laterality`, `valid` (boolean), `category`.

## Provider Endpoints

### GET /api/providers
List all providers. Response: array of provider objects with `provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax`.

### GET /api/providers/{provider_id}
Single provider detail. Same fields as list.

## Audit Endpoints

### GET /api/audit-logs
List all audit log entries. Response: array of audit objects with `audit_id`, `timestamp`, `action`, `entity_type`, `entity_id`, `user_id`, `details`.

## Service Code Endpoints

### GET /api/service-codes
List all service codes. Response: array with `code`, `description`, `service_line`, `valid` (boolean).

### GET /api/service-codes/{code}
Single service code lookup. Response includes `code`, `description`, `service_line`, `valid`.

## Parallel Fetch Strategy

When building a packet, fetch independent resources simultaneously:

- Patient demographics + conditions + medications + allergies — parallel per patient
- Duplicate candidate + both patients' clinical lists — parallel
- Batch referrals + provider directory — parallel
- ICD-10 validations for a batch — all codes in parallel

Only serialize when one fetch depends on the result of another (e.g., fetch the duplicate candidate first to learn the patient IDs, then fetch both patients in parallel).
