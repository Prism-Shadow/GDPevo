# EHR Governance API Surface Reference

Base URL is always provided in the prompt as `<TASK_ENV_BASE_URL>`. All endpoints are read-only GET requests. This reference describes the typical response shape for each endpoint family, based on observed FHIR-like patterns.

---

## Patients

### `GET /api/patients`
Returns a list of patient summary objects.

### `GET /api/patients/{patient_id}`
Returns a single patient record with demographics:
- `patient_id` — string identifier (e.g., `"P-NNNNN"`)
- `enterprise_mrn` — string, enterprise master record number
- `display_name` — string, full name
- `dob` — date string `YYYY-MM-DD`
- `sex` — string
- `insurance_id` — string identifier
- `phone` — string
- `address` — string
- `primary_care_provider_id` — string, references a provider
- `given_name` — string, first name

---

## Clinical Lists

All three clinical-list endpoints return records with a common shape: each record has a `normalized_key` (stable identifier string), a `status` (enum: `active`, `inactive`, `entered-in-error`, `resolved`), and a `source` (string describing origin, e.g., `"problem_list"`, `"referral_intake"`).

### `GET /api/patients/{patient_id}/conditions`
Additional fields:
- `code` — ICD-10 code string
- `description` — human-readable description

### `GET /api/patients/{patient_id}/medications`
Additional fields:
- `medication` — drug name string
- `dose` — string (e.g., `"20 mg"`)
- `route` — string (e.g., `"oral"`)
- `frequency` — string (e.g., `"daily"`)

### `GET /api/patients/{patient_id}/allergies`
Additional fields:
- `allergen` — string (e.g., `"sulfa antibiotics"`, `"latex"`)
- `reaction` — string (e.g., `"rash"`)
- `severity` — enum: `mild`, `moderate`, `severe`, `unknown`

---

## Encounters

### `GET /api/patients/{patient_id}/encounters`
Returns a list of encounter objects:
- `encounter_id` — string
- `date` — `YYYY-MM-DD`
- `type` — string (e.g., `"office_visit"`, `"care_transition"`)
- `provider_id` — string, references a provider
- `signed_status` — enum: `signed`, `unsigned`, `amended`, `draft`
- `diagnosis_codes` — array of ICD-10 code strings
- `medications_mentioned` — array of medication name strings
- `care_plan_tag` — enum string indicating the clinical intent of the visit

When selecting encounters for a packet, prefer signed encounters that are recent (within the last 3-4 months) and whose diagnosis codes or care plan tag align with the packet's service line.

---

## Documents

### `GET /api/patients/{patient_id}/documents`
Returns a list:
- `document_id` — string
- `type` — string (e.g., `"echocardiogram"`, `"office_note"`, `"chart_summary"`, `"authorization"`, `"imaging"`)
- `date` — `YYYY-MM-DD`
- `status` — enum: `final`, `preliminary`, `cancelled`

For packet evidence, prefer documents with status `final`. Exclude `chart_summary` type documents unless the template explicitly requests all documents. Documents from external providers that appear on a duplicate record shell are strong identity-match signals.

---

## Immunizations

### `GET /api/patients/{patient_id}/immunizations`
Returns a list:
- `immunization_id` — string
- `date` — `YYYY-MM-DD`
- `vaccine` — string (e.g., `"influenza high-dose"`)

---

## Disclosures

### `GET /api/patients/{patient_id}/disclosures`
Returns a list:
- `disclosure_id` — string
- `date` — `YYYY-MM-DD`
- `status` — enum: `permitted`, `pending`, `denied`, `expired`
- `purpose` — string
- `recipient_provider_id` — string, references a provider

A disclosure with status `permitted` whose recipient matches the packet's target provider is required for transition/handoff packets to be ready.

---

## Duplicate Candidates

### `GET /api/duplicates/candidates`
Returns a list of duplicate candidate summaries.

### `GET /api/duplicates/{candidate_id}`
Returns full detail:
- `candidate_id` — string
- `status` — enum: `confirmed_duplicate`, `needs_review`, `not_duplicate`
- `primary_patient_id` — string
- `possible_duplicate_patient_id` — string
- `match_signals` — array of signal label strings (e.g., `"same_dob"`, `"same_insurance"`, `"similar_address"`, `"same_phone"`, `"same_given_name"`, `"name_variant"`, `"shared_external_cardiology_document"`)
- `conflict_signals` — array of signal label strings (e.g., `"different_given_name"`, `"different_phone"`, `"opposite_laterality_problem"`, `"different_dob"`, `"different_insurance"`, `"different_address"`, `"address_abbreviation"`)
- May also provide preview clinical-key lists — always cross-check these against the patient active-list endpoints, which are authoritative.

Match/conflict signals are hints, not definitive. Verify by fetching both patient records and comparing the actual fields. Document matches and conflicts in both the identity_signals and merge_decision sections.

---

## Referrals

### `GET /api/referrals`
Returns a list of referral summaries. Filter by batch ID or date range to find batch members.

### `GET /api/referrals/{referral_id}`
Returns a single referral:
- `referral_id` — string
- `patient_id` — string
- `batch_id` — string
- `service_line` — enum: `cardiology`, `orthopedics`, `pulmonology`, `neurology`, `skilled_nursing`, `oncology`
- `diagnosis_code` — ICD-10 code string
- `diagnosis_narrative` — free-text description of the clinical reason
- `urgency` — enum: `routine`, `urgent`, `stat`
- `authorization_status` — enum: `approved`, `pending`, `denied`, `not_required`, `unknown`
- `status` — enum: `open`, `closed`, `cancelled`, `draft`
- `requested_date` — `YYYY-MM-DD`

When auditing referrals, cross-reference the diagnosis_code against the ICD-10 directory. An orthopedic batch expects Musculoskeletal chapter codes. Check the diagnosis_narrative for laterality and body-site consistency with the ICD-10 code's official description.

---

## Service Requests

### `GET /api/patients/{patient_id}/service-requests`
Returns a list of service requests for that patient. Filter by `service_request_id` to find the target:
- `service_request_id` — string
- `patient_id` — string
- `status` — enum: `draft`, `active`, `on-hold`, `revoked`, `completed`, `entered-in-error`
- `intent` — enum: `proposal`, `plan`, `order`, `original-order`, `reflex-order`, `filler-order`, `instance-order`, `option`
- `priority` — enum: `routine`, `urgent`, `asap`, `stat`
- `service_code` — string, references the service-codes directory
- `requester_provider_id` — string
- `performer_provider_id` — string
- `authored_on` — `YYYY-MM-DD`
- `occurrence_date` — `YYYY-MM-DD`
- `reason_codes` — array of ICD-10 code strings

Validate service_code against `GET /api/service-codes/{code}` and reason_codes against `GET /api/icd10/{code}`. A service request with all codes valid, SBAR sections complete, and no duplicate review blockers is ready.

---

## ICD-10 Directory

### `GET /api/icd10`
Returns a list of ICD-10 code summaries.

### `GET /api/icd10/{code}`
Returns detail for one code:
- `code` — string
- `description` — official ICD-10 description string
- `chapter` — string (e.g., `"Musculoskeletal"`, `"Circulatory"`, `"Respiratory"`, `"Injury"`, `"Endocrine"`)

**Chapter mapping for common service lines:**
- Orthopedics → expects `Musculoskeletal`
- Cardiology → expects `Circulatory`
- Pulmonology → expects `Respiratory`
- Neurology → expects `Nervous System`

The `chapter` returned by the API is authoritative. Do not infer chapter from the code letter prefix — some codes starting with "M" are Musculoskeletal, but others may be in different chapters depending on the coding version. Injury codes (like S83.241A) are common distractors in orthopedic batches.

---

## Service Codes

### `GET /api/service-codes`
Returns a list of service code summaries.

### `GET /api/service-codes/{code}`
Returns detail for one code:
- `code` — string
- `description` — string
- `valid` — boolean

A service code is valid for a service request when `valid` is `true` and the description aligns with the performer's service line.

---

## Provider Directory

### `GET /api/providers`
Returns a list of provider summaries.

### `GET /api/providers/{provider_id}`
Returns a single provider:
- `provider_id` — string
- `name` — string (e.g., `"Dr. Example Provider"`)
- `role` — string (e.g., `"Cardiologist"`, `"Primary Care"`, `"Orthopedic Surgeon"`)
- `service_line` — enum matching the standard service-line values
- `facility` — string (e.g., `"Facility Name A"`, `"Facility Name B"`)
- `phone` — string
- `fax` — string

When a packet needs a provider contact, match by service line to the packet's purpose. If multiple providers share a service line, use the one referenced by the referral, service request, or external document.

---

## Audit Logs

### `GET /api/audit-logs`
Returns a list of audit log entries. Each entry typically has:
- `audit_id` — string
- `patient_id` — string (may be the primary patient affected)
- `action` — string describing what happened
- `timestamp` — datetime string

Filter audit logs to entries that relate to the packet's primary entity. For merge packets, look for entries documenting duplicate detection, record linking, or data reconciliation events. For referral packets, look for entries related to the referral's processing lifecycle.
