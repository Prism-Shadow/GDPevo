# EHR Quality-Governance API Endpoints

All endpoints are read-only GET. The base URL is provided in the task prompt as `<TASK_ENV_BASE_URL>`.

## Patient Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/patients` | Search or list all patients |
| `GET /api/patients/{patient_id}` | Patient demographics and metadata |

Returns: `patient_id`, `enterprise_mrn`, `given_name`, `family_name`, `display_name`, `dob`, `sex`, `phone`, `address`, `insurance_id`, `primary_care_provider_id`.

## Clinical Lists (per patient)

| Endpoint | Description |
|----------|-------------|
| `GET /api/patients/{patient_id}/conditions` | All conditions (active + inactive) |
| `GET /api/patients/{patient_id}/medications` | All medications |
| `GET /api/patients/{patient_id}/allergies` | All allergies |
| `GET /api/patients/{patient_id}/encounters` | All encounters |
| `GET /api/patients/{patient_id}/immunizations` | All immunizations |
| `GET /api/patients/{patient_id}/documents` | All clinical documents |
| `GET /api/patients/{patient_id}/service-requests` | All service requests |
| `GET /api/patients/{patient_id}/disclosures` | All disclosures |

**Condition record fields**: `code` (ICD-10), `description`, `normalized_key`, `clinical_status` (active|inactive|resolved|remission|entered-in-error), category.

**Medication record fields**: `name`, `normalized_key`, `dose`, `route`, `frequency`, `status` (active|inactive|completed|stopped|entered-in-error|unknown).

**Allergy record fields**: `allergen`, `normalized_key`, `reaction`, `severity` (mild|moderate|severe|unknown), `status` (active|inactive|resolved|entered-in-error).

**Encounter record fields**: `encounter_id`, `date`, `type`, `provider_id`, `signed_status` (signed|unsigned|amended|draft), `diagnosis_codes`, `medications_mentioned`, `care_plan_tag`.

**Immunization record fields**: `immunization_id`, `date`, `vaccine`.

**Document record fields**: `document_id`, `type` (echocardiogram|office_note|chart_summary|care_plan|continuity_of_care|external_record|imaging_report|authorization), `date`, `status` (final|preliminary|cancelled|missing), `author_provider_id`, `patient_id`.

**ServiceRequest record fields**: `service_request_id`, `patient_id`, `status` (draft|active|on-hold|revoked|completed|entered-in-error), `intent` (proposal|plan|order), `priority` (routine|urgent|asap|stat), `service_code`, `requester_provider_id`, `performer_provider_id`, `authored_on`, `occurrence_date`, `reason_codes`, `sbar_sections`.

**Disclosure record fields**: `disclosure_id`, `date`, `status` (permitted|pending|denied|expired), `purpose`, `recipient_provider_id`.

## Duplicate Candidates

| Endpoint | Description |
|----------|-------------|
| `GET /api/duplicates/candidates` | List all duplicate candidates |
| `GET /api/duplicates/{candidate_id}` | Single duplicate candidate detail |

Returns: `candidate_id`, `status` (confirmed_duplicate|needs_review|not_duplicate), `primary_patient_id`, `duplicate_patient_id`, `match_signals`, `conflict_signals`, `documents`, `audit_logs`, `preview_clinical_keys`, `recommended_disposition`.

## Referrals

| Endpoint | Description |
|----------|-------------|
| `GET /api/referrals` | List or search all referrals |
| `GET /api/referrals/{referral_id}` | Single referral detail |

Returns: `referral_id`, `patient_id`, `batch_id`, `service_line`, `status`, `urgency`, `requested_date`, `diagnosis_code`, `diagnosis_narrative`, `referring_provider_id`, `receiving_provider_id`, `authorization_status` (approved|pending|denied|not_required|unknown), `documents_received`, `imaging_status`, `office_note_received`.

## Audit Logs

| Endpoint | Description |
|----------|-------------|
| `GET /api/audit-logs` | List all audit log entries |

Returns: `audit_id`, `entity_type` (duplicate_candidate|service_request|referral|merge), `entity_id`, `action`, `timestamp`, `user_id`, `details`.

## Directories

| Endpoint | Description |
|----------|-------------|
| `GET /api/icd10` | List all ICD-10 codes |
| `GET /api/icd10/{code}` | Single ICD-10 code detail |
| `GET /api/providers` | List all providers |
| `GET /api/providers/{provider_id}` | Single provider detail |
| `GET /api/service-codes` | List all service codes |
| `GET /api/service-codes/{code}` | Single service code detail |

**ICD-10 record fields**: `code`, `description`, `chapter` (Musculoskeletal|Circulatory|Respiratory|Injury|Endocrine|Nervous System|etc.), `laterality`.

**Provider record fields**: `provider_id`, `name`, `role`, `service_line` (orthopedics|cardiology|pulmonology|neurology|skilled_nursing|oncology|primary_care), `facility`, `phone`, `fax`.

**Service code record fields**: `code`, `description`, `service_line`.
