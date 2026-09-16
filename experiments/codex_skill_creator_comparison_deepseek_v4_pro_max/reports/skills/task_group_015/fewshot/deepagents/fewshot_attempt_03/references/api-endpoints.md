# EHR Governance API Endpoints

Base URL: `http://task-env:9015`

All endpoints are GET-only and return JSON. Use `curl -s` followed by a JSON formatter.

## Patient Endpoints

### GET /api/patients

Returns a list of patients. Each patient object has:
- `patient_id` — canonical ID (e.g. `P-NNNNN`)
- `enterprise_mrn` — enterprise-level MRN
- `given_name`, `family_name`, `display_name`
- `dob` — date of birth (YYYY-MM-DD)
- `sex`
- `address_line`, `city`, `state`, `zip`
- `phone`
- `insurance_id`
- `primary_care_provider_id`

### GET /api/patients/{patient_id}

Returns a single patient object with the same fields as above.

### GET /api/patients/{patient_id}/conditions

Returns an array of condition records. Each record has:
- `condition_id`
- `code` — ICD-10 code
- `description`
- `normalized_key` — stable key for comparison/sorting (e.g. `hypertension`, `diabetes_type_2`)
- `status` — `active`, `inactive`, `entered-in-error`, `resolved`
- `onset_date`
- `source` — `problem_list`, `referral_intake`, `encounter_diagnosis`

### GET /api/patients/{patient_id}/medications

Returns an array of medication records. Each has:
- `medication_id`
- `medication` — medication name
- `dose`, `route`, `frequency`
- `normalized_key` — stable key (e.g. `aspirin`, `metformin`)
- `status` — `active`, `inactive`, `entered-in-error`
- `start_date`

### GET /api/patients/{patient_id}/allergies

Returns an array of allergy records. Each has:
- `allergy_id`
- `allergen` — substance name
- `reaction` — observed reaction
- `severity` — `mild`, `moderate`, `severe`, `unknown`
- `normalized_key` — stable key (e.g. `penicillin`, `latex`, `iodinated_contrast`)
- `status` — `active`, `inactive`, `entered-in-error`
- `source`

### GET /api/patients/{patient_id}/encounters

Returns an array of encounter records. Each has:
- `encounter_id`
- `date` — YYYY-MM-DD
- `type` — `office_visit`, `care_transition`, `emergency`, `telehealth`, `inpatient`
- `provider_id`
- `signed_status` — `signed`, `unsigned`, `amended`, `draft`
- `diagnosis_codes` — array of ICD-10 codes from the encounter
- `medications_mentioned` — array of medication names
- `care_plan_tag` — normalized tag for the encounter purpose

### GET /api/patients/{patient_id}/documents

Returns an array of document records. Each has:
- `document_id`
- `type` — `echocardiogram`, `office_note`, `chart_summary`, `referral_letter`, `imaging_report`, `discharge_summary`, `cardiology_consult`
- `date` — YYYY-MM-DD
- `status` — `final`, `preliminary`, `cancelled`
- `patient_id`
- `provider_id`

### GET /api/patients/{patient_id}/immunizations

Returns an array of immunization records. Each has:
- `immunization_id`
- `date` — YYYY-MM-DD
- `vaccine` — vaccine name
- `status` — `completed`, `entered-in-error`

### GET /api/patients/{patient_id}/disclosures

Returns an array of disclosure records. Each has:
- `disclosure_id`
- `date` — YYYY-MM-DD
- `status` — `permitted`, `pending`, `denied`, `expired`
- `purpose` — narrative purpose
- `recipient_provider_id`

### GET /api/patients/{patient_id}/service-requests

Returns an array of ServiceRequest records. Each has:
- `service_request_id`
- `patient_id`
- `status` — `draft`, `active`, `on-hold`, `revoked`, `completed`, `entered-in-error`
- `intent` — `proposal`, `plan`, `order`, `original-order`, `reflex-order`, `filler-order`, `instance-order`, `option`
- `priority` — `routine`, `urgent`, `asap`, `stat`
- `service_code`
- `requester_provider_id`
- `performer_provider_id`
- `performer_service_line` — `orthopedics`, `cardiology`, `pulmonology`, `neurology`, `skilled_nursing`, `oncology`, `primary_care`
- `authored_on` — YYYY-MM-DD
- `occurrence_date` — YYYY-MM-DD
- `reason_codes` — array of ICD-10 codes

## Duplicate Candidate Endpoints

### GET /api/duplicates/candidates

Returns a list of duplicate candidate records. Each has:
- `candidate_id` — e.g. `DUP-TR-NNN`
- `primary_patient_id`
- `possible_duplicate_patient_id`
- `status` — `confirmed_duplicate`, `needs_review`, `not_duplicate`
- `match_signals` — array of signal labels
- `conflict_signals` — array of conflict labels
- `preview_conditions`, `preview_medications`, `preview_allergies` — arrays of clinical records from the candidate preview

### GET /api/duplicates/{candidate_id}

Returns a single duplicate candidate with the same fields as above.

## Referral Endpoints

### GET /api/referrals

Returns a list of referral records. Each has:
- `referral_id` — e.g. `REF-NNN-NNN`
- `patient_id`
- `batch_id`
- `service_line` — `cardiology`, `orthopedics`, `pulmonology`, `neurology`, `skilled_nursing`, `oncology`
- `requested_date` — YYYY-MM-DD
- `diagnosis_code` — ICD-10 code
- `diagnosis_narrative` — free-text description from the referral form
- `status` — `open`, `closed`, `cancelled`, `draft`
- `urgency` — `routine`, `urgent`, `stat`
- `authorization_status` — `approved`, `pending`, `denied`, `not_required`
- `receiving_provider_id`
- `referring_provider_id`

### GET /api/referrals/{referral_id}

Returns a single referral with the same fields.

## ICD-10 Endpoints

### GET /api/icd10

Returns the full ICD-10 directory used by the environment.

### GET /api/icd10/{code}

Returns a single ICD-10 code record:
- `code`
- `description`
- `chapter` — e.g. `Musculoskeletal`, `Circulatory`, `Injury`, `Respiratory`, `Endocrine`
- `laterality` — `left`, `right`, `bilateral`, `unspecified`, or absent
- `terms` — array of associated search terms

## Provider Endpoints

### GET /api/providers

Returns the provider directory. Each provider has:
- `provider_id` — e.g. `PRV-CARD-NNN`, `PRV-ORTHO-NNN`, `PRV-PCP-NNN`
- `name` — full display name
- `role` — `Cardiologist`, `Orthopedic Surgeon`, `Primary Care`
- `service_line` — `cardiology`, `orthopedics`, `primary_care`, `pulmonology`, `neurology`, `skilled_nursing`, `oncology`
- `facility` — facility name
- `phone`
- `fax`

### GET /api/providers/{provider_id}

Returns a single provider with the same fields.

## Audit and Service Code Endpoints

### GET /api/audit-logs

Returns audit log records. Each has:
- `audit_id`
- `event_type`
- `patient_id`
- `timestamp`
- `description`

### GET /api/service-codes

Returns a list of service code records. Each has:
- `code` — e.g. `ORTHO-CONSULT`
- `description`

### GET /api/service-codes/{code}

Returns a single service code record.
