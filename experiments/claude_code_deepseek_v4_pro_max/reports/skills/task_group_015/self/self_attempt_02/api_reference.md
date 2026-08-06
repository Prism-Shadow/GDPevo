# EHR API Reference

Base URL: from `environment_access.md` (default `http://task-env:9015/`). All endpoints are read-only GET.

## Patient endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/patients` | Patient directory (searchable) |
| `GET /api/patients/{patient_id}` | Patient demographics: `patient_id`, `enterprise_mrn`, `display_name`, `dob`, `gender`, `address`, `phone`, `insurance_id` |
| `GET /api/patients/{patient_id}/conditions` | Condition list. Each: `condition_id`, `code` (ICD-10), `description`, `normalized_key`, `status` (active\|inactive\|resolved\|entered-in-error), `onset_date`, `recorded_date` |
| `GET /api/patients/{patient_id}/medications` | Medication list. Each: `medication_id`, `medication` (name), `dose`, `route`, `frequency`, `normalized_key`, `status` (active\|inactive\|entered-in-error), `start_date` |
| `GET /api/patients/{patient_id}/allergies` | Allergy list. Each: `allergy_id`, `allergen`, `reaction`, `severity` (mild\|moderate\|severe\|unknown), `status` (active\|inactive\|entered-in-error\|unknown), `recorded_date` |
| `GET /api/patients/{patient_id}/encounters` | Encounter history. Each: `encounter_id`, `date`, `type`, `provider_id`, `signed_status` (signed\|unsigned\|amended\|draft), `diagnosis_codes[]`, `medications_mentioned[]`, `care_plan_tag`, `service_line` |
| `GET /api/patients/{patient_id}/immunizations` | Immunization records. Each: `immunization_id`, `date`, `vaccine`, `status` |
| `GET /api/patients/{patient_id}/documents` | Document index. Each: `document_id`, `type`, `date`, `status` (final\|preliminary\|cancelled), `patient_id` |
| `GET /api/patients/{patient_id}/disclosures` | Disclosure/consent records. Each: `disclosure_id`, `date`, `status` (permitted\|pending\|denied\|expired), `purpose`, `recipient_provider_id` |
| `GET /api/patients/{patient_id}/service-requests` | ServiceRequest (order/referral request) records. Each: `service_request_id`, `patient_id`, `status` (draft\|active\|on-hold\|revoked\|completed\|entered-in-error), `intent`, `priority` (routine\|urgent\|asap\|stat), `service_code`, `requester_provider_id`, `performer_provider_id`, `authored_on`, `occurrence_date`, `reason_codes[]` |

## Duplicate endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/duplicates/candidates` | List of duplicate candidate summaries |
| `GET /api/duplicates/{candidate_id}` | Duplicate candidate detail: `candidate_id`, `status` (confirmed_duplicate\|needs_review\|not_duplicate), `primary_patient_id`, `possible_duplicate_patient_id`, `match_signals[]`, `conflict_signals[]`, `preview` (may include partial clinical list excerpts) |

## Referral endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/referrals` | Referral index (filter/search by batch_id, patient_id, service_line) |
| `GET /api/referrals/{referral_id}` | Referral detail: `referral_id`, `batch_id`, `patient_id`, `service_line`, `requested_date`, `status` (open\|closed\|cancelled\|draft), `diagnosis_code`, `diagnosis_narrative`, `receiving_provider_id`, `authorization_status` (approved\|pending\|denied\|not_required\|unknown), `urgency` (routine\|urgent\|stat) |

## Reference endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/audit-logs` | Audit log entries. Each: `audit_id`, `patient_id`, `entity_type`, `entity_id`, `action`, `timestamp` |
| `GET /api/icd10` | ICD-10 code directory (searchable) |
| `GET /api/icd10/{code}` | ICD-10 code detail: `code`, `description`, `chapter`, `laterality` (if applicable) |
| `GET /api/providers` | Provider directory (searchable by service_line, name) |
| `GET /api/providers/{provider_id}` | Provider detail: `provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax` |
| `GET /api/service-codes` | Service code directory |
| `GET /api/service-codes/{code}` | Service code detail: `code`, `description`, `service_line` |

## API usage notes

- **Pagination**: list endpoints may return paginated results. Use query parameters or iterate as needed to collect all records.
- **Empty results**: an endpoint returning `[]` or `null` for a valid ID means no records exist for that resource — this is normal (e.g., a patient with no allergies).
- **Search semantics**: list endpoints (`/api/patients`, `/api/referrals`, `/api/icd10`, `/api/providers`, `/api/service-codes`) accept query parameters for filtering. The exact query interface may vary; when in doubt, fetch the full list and filter client-side by the fields documented above.
- **Cross-referencing**: Providers, ICD-10 codes, and service codes referenced in patient/referral records should be validated by fetching their respective detail endpoints. Never assume a referenced code or provider ID is valid without verification.
