# API reference — read-only EHR quality-governance environment

Base URL comes from `environment_access.md` (`GDPEVO_ENV_BASE_URL`, e.g.
`http://<host>:<port>/`). Substitute it for `<TASK_ENV_BASE_URL>` in the prompt.
No authentication. Every call is a `GET`. The environment_access file also lists
exactly which endpoints are allowed — treat that list as authoritative and do not
call anything outside it.

## General response conventions

- **List endpoints wrap their rows under a single key**, e.g.
  `{"patients":[...]}`, `{"conditions":[...]}`, `{"medications":[...]}`,
  `{"allergies":[...]}`, `{"encounters":[...]}`, `{"immunizations":[...]}`,
  `{"disclosures":[...]}`, `{"documents":[...]}`, `{"service_requests":[...]}`,
  `{"duplicate_candidates":[...]}`, `{"referrals":[...]}`, `{"audit_logs":[...]}`.
- **Detail endpoints** (`/api/.../{id}`) return the object directly.
- **Unknown id → HTTP 404.** Use this as a signal, e.g. a diagnosis code that 404s
  from `/api/icd10/{code}` is an unknown/invalid code.
- **Do not trust query-string filters.** Some list endpoints ignore them. Observed:
  `/api/referrals?batch_id=...` returns *all* referrals across every batch; you must
  filter client-side on the row's `batch_id`. `/api/audit-logs?patient_id=...` did
  appear to filter. Rule of thumb: fetch broadly, then filter in code on the actual
  field, and never assume a param narrowed the result.

## Endpoints and the fields that matter

### Patients
- `GET /api/patients` — roster rows: `patient_id`, `display_name`, `dob`,
  `enterprise_mrn`, `insurance_id`, `phone`, `canonical_status`.
- `GET /api/patients/{id}` — full demographics: `patient_id`, `given_name`,
  `family_name`, `display_name`, `dob`, `sex`, `address`, `phone`, `insurance_id`,
  `enterprise_mrn`, `canonical_status`, `canonical_patient_id`,
  `primary_care_provider_id`, and an embedded `primary_care_provider` object
  (`provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax`).

### Active clinical lists (per patient)
Each row carries a `normalized_key`, a `status` (`active` / `inactive` /
`entered-in-error` / ...), a human `id`, and a `source`.
- `GET /api/patients/{id}/conditions` → `conditions[]`: `code`, `description`,
  `normalized_key`, `status`, `onset_date`, `source`.
- `GET /api/patients/{id}/medications` → `medications[]`: `medication`, `dose`,
  `route`, `frequency`, `normalized_key`, `status`, `source`.
- `GET /api/patients/{id}/allergies` → `allergies[]`: `allergen`, `reaction`,
  `severity`, `normalized_key`, `status`, `source`.

### Encounters / immunizations / disclosures / documents (per patient)
- `GET /api/patients/{id}/encounters` → `encounters[]`: `encounter_id`, `date`,
  `type`, `signed_status`, `provider_id`, `diagnoses[]`, `medications_mentioned[]`,
  `care_plan_notes`. IDs come in two flavours: a structured handoff series
  (`ENC-<patient-suffix>-N`) and random-hex distractor visits (`ENC-<hex>`).
- `GET /api/patients/{id}/immunizations` → `immunizations[]`: `id`, `date`, `vaccine`.
- `GET /api/patients/{id}/disclosures` → `disclosures[]`: `disclosure_id`, `date`,
  `status` (`permitted`/`pending`/`denied`/`expired`), `purpose`, `recipient`,
  `recipient_provider_id`.
- `GET /api/patients/{id}/documents` → `documents[]`: `document_id`, `date`, `type`
  (e.g. `external_cardiology_note`, `echocardiogram`, `office_note`, `chart_summary`),
  `status` (`final`/`preliminary`/`cancelled`), `source`.
- `GET /api/patients/{id}/service-requests` → `service_requests[]`:
  `service_request_id`, `status`, `intent`, `priority`, `service_code`,
  `requester_id`, `performer_id`, `authored_on`, `occurrence_date`,
  `reason_codes[]`, and an `sbar` object (`situation`, `background`, `assessment`,
  `recommendation`).

### Duplicate candidates
- `GET /api/duplicates/candidates` → `duplicate_candidates[]`.
- `GET /api/duplicates/{candidate_id}` → `candidate_id`, `status`
  (`open`/`needs_review`/`confirmed_duplicate`/`not_duplicate`), `patient_ids[]`,
  `match_signals[]`, `conflict_signals[]`, and a `merge_preview`
  (`preferred_target_patient_id`, `source_patient_id`, `active_condition_keys[]`,
  `active_medication_keys[]`, `active_allergy_keys[]`). The `merge_preview` is a
  *hint only* — the per-patient active-list endpoints are authoritative.

### Referrals
- `GET /api/referrals` → `referrals[]` (all batches). `GET /api/referrals/{id}`.
  Fields: `referral_id`, `batch_id`, `patient_id`, `service_line`, `requested_date`,
  `diagnosis_code`, `diagnosis_narrative`, `documents_received[]`,
  `receiving_provider_id`, `authorization_status`
  (`approved`/`pending`/`missing`/...), `status` (`open`/`closed`/`cancelled`/`draft`),
  `urgency` (`routine`/`urgent`/`stat`), `coordination_note`.

### Audit logs
- `GET /api/audit-logs` (optionally `?patient_id=`) → `audit_logs[]`: `audit_id`,
  `patient_id`, `date`, `event` (`identity_review`, `external_import`,
  `merge_completed`, ...), `actor`, `summary`.

### Reference directories
- `GET /api/icd10` / `GET /api/icd10/{code}` → `code`, `chapter`
  (`Musculoskeletal`, `Injury`, `Circulatory`, `Respiratory`, ...), `expected_terms[]`,
  `requires_laterality` (bool). **404 = unknown code.**
- `GET /api/service-codes` / `GET /api/service-codes/{code}` → `code`, `display`,
  `service_line`, `order_kind`, `active` (bool).
- `GET /api/providers` / `GET /api/providers/{id}` → `provider_id`, `name`, `role`,
  `service_line`, `facility`, `phone`, `fax`.
