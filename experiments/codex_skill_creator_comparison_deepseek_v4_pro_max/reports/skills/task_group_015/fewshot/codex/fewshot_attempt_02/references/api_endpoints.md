# EHR Quality Governance API Endpoints

Base URL: `<TASK_ENV_BASE_URL>` (provided in the task prompt).

All endpoints are read-only GET. No authentication required. Responses are JSON objects or arrays.

## Endpoint Catalog

### Patients

| Endpoint | Returns |
|---|---|
| `GET /api/patients` | Array of patient summary objects. Each has `patient_id`, `display_name`, `dob`, `sex`, `enterprise_mrn`, `insurance_id`, `primary_care_provider_id`, `address`, `phone`. |
| `GET /api/patients/{patient_id}` | Single patient detail object with all demographic fields plus `active` (boolean). |
| `GET /api/patients/{patient_id}/conditions` | Array of condition objects. Fields: `condition_id`, `code` (ICD-10), `description`, `normalized_key`, `clinical_status` (active/inactive/resolved), `verification_status`, `category`, `onset_date`, `recorded_date`. |
| `GET /api/patients/{patient_id}/medications` | Array of medication objects. Fields: `medication_id`, `medication` (name), `normalized_key`, `dose`, `route`, `frequency`, `status` (active/inactive/completed), `authored_on`. |
| `GET /api/patients/{patient_id}/allergies` | Array of allergy objects. Fields: `allergy_id`, `allergen`, `normalized_key`, `reaction`, `severity` (mild/moderate/severe/unknown), `clinical_status` (active/inactive/resolved). |
| `GET /api/patients/{patient_id}/encounters` | Array of encounter objects. Fields: `encounter_id`, `date`, `type` (office_visit/care_transition/emergency/etc.), `signed_status` (signed/unsigned/amended/draft), `provider_id`, `diagnosis_codes`, `medications_mentioned`, `care_plan_tag`. |
| `GET /api/patients/{patient_id}/immunizations` | Array of immunization objects. Fields: `immunization_id`, `date`, `vaccine`, `status`. |
| `GET /api/patients/{patient_id}/documents` | Array of document objects. Fields: `document_id`, `type` (echocardiogram/chart_summary/office_note/referral_letter/external_record/etc.), `date`, `status` (final/preliminary/cancelled), `author_provider_id`. |
| `GET /api/patients/{patient_id}/service-requests` | Array of ServiceRequest objects. Fields: `service_request_id`, `patient_id`, `status`, `intent`, `priority`, `service_code`, `requester_provider_id`, `performer_provider_id`, `authored_on`, `occurrence_date`, `reason_codes`, `sbar_sections`. |
| `GET /api/patients/{patient_id}/disclosures` | Array of disclosure objects. Fields: `disclosure_id`, `date`, `status` (permitted/pending/denied/expired), `purpose`, `recipient_provider_id`. |

### Duplicates

| Endpoint | Returns |
|---|---|
| `GET /api/duplicates/candidates` | Array of duplicate candidate summary objects. |
| `GET /api/duplicates/{candidate_id}` | Single duplicate candidate. Fields: `candidate_id`, `candidate_status` (confirmed_duplicate/needs_review/not_duplicate), `primary_patient_id`, `possible_duplicate_patient_id`, `match_signals`, `conflict_signals`, `merge_target_patient_id`, `merge_source_patient_id`. |

### Referrals

| Endpoint | Returns |
|---|---|
| `GET /api/referrals` | Array of referral objects. Fields: `referral_id`, `patient_id`, `batch_id`, `service_line`, `requested_date`, `status` (open/closed/cancelled/draft), `urgency`, `diagnosis_code`, `diagnosis_narrative`, `authorization_status` (approved/pending/denied/not_required/unknown), `receiving_provider_id`, `has_office_note`, `has_imaging`, `referral_form_allergies`. |
| `GET /api/referrals/{referral_id}` | Single referral detail (same fields as list, possibly richer). |

### ICD-10

| Endpoint | Returns |
|---|---|
| `GET /api/icd10` | Array of ICD-10 code objects. |
| `GET /api/icd10/{code}` | Single ICD-10 code. Fields: `code`, `description`, `chapter`. If invalid/unknown, returns 404. |

### Providers

| Endpoint | Returns |
|---|---|
| `GET /api/providers` | Array of provider objects. |
| `GET /api/providers/{provider_id}` | Single provider. Fields: `provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax`. |

### Audit Logs

| Endpoint | Returns |
|---|---|
| `GET /api/audit-logs` | Array of audit log objects. Fields: `audit_id`, `patient_id`, `action`, `timestamp`, `details`. Filter by `patient_id` query param in practice. |

### Service Codes

| Endpoint | Returns |
|---|---|
| `GET /api/service-codes` | Array of service code objects. |
| `GET /api/service-codes/{code}` | Single service code. Returns 404 if invalid. |

## Query Patterns

### Parallel fetch for a single patient

```bash
curl -s "$BASE/api/patients/P-XXXXX" &
curl -s "$BASE/api/patients/P-XXXXX/conditions" &
curl -s "$BASE/api/patients/P-XXXXX/medications" &
curl -s "$BASE/api/patients/P-XXXXX/allergies" &
curl -s "$BASE/api/patients/P-XXXXX/encounters" &
curl -s "$BASE/api/patients/P-XXXXX/documents" &
curl -s "$BASE/api/patients/P-XXXXX/immunizations" &
curl -s "$BASE/api/patients/P-XXXXX/disclosures" &
wait
```

### ICD-10 validation

```bash
# Check existence (404 = invalid)
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/icd10/I50.32"

# Get details
curl -s "$BASE/api/icd10/I50.32"
# Returns: {"code":"I50.32","description":"Chronic diastolic heart failure","chapter":"Circulatory"}
```

### Provider lookup

```bash
curl -s "$BASE/api/providers/PRV-CARD-020"
```

### Duplicate evaluation

Fetch the candidate, then fetch both patients' demographics in parallel. Compare fields:
- `dob` — exact match or not
- `insurance_id` — exact match or not
- `phone` — exact match or different
- `address` — compare for similarity (exact match vs abbreviation vs different)
- `name` / `given_name` — compare family and given names
- `sex` — match or not
- `primary_care_provider_id` — match or not

### Batch audit pattern

```bash
# Get all referrals
curl -s "$BASE/api/referrals" | jq '[.[] | select(.batch_id == "MAR26-ORTHO-A")]'
# Then for each referral, fetch patient and ICD-10 code in parallel batches
```

## Response Conventions

- Dates are ISO-8601 (YYYY-MM-DD format in practice).
- Missing or null fields are either omitted or returned as `null`.
- Status fields use lowercase snake_case.
- IDs are stable within the environment session.
