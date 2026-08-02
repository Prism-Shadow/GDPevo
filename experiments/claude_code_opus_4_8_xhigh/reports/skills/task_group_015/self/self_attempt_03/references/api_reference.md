# EHR governance API — reference

Read-only HTTP GET API. Base URL and the allow-listed endpoints come from `environment_access.md`
(do not hardcode a URL). Credentials: none required. All responses are JSON.

## Response conventions (verify per-endpoint; both shapes occur)

- Collections are usually wrapped under a singular-ish key: `{"patients":[...]}`, `{"conditions":[...]}`,
  `{"medications":[...]}`, `{"allergies":[...]}`, `{"referrals":[...]}`, `{"duplicate_candidates":[...]}`,
  `{"service_requests":[...]}`, `{"icd10":[...]}`, `{"providers":[...]}`, `{"service_codes":[...]}`.
- Some collections return a **bare array** (e.g. audit-logs). Handle `.<key> // .` defensively.
- Unknown id → HTTP 404 `{"error":"... not found","status":404}`. Use this as evidence for
  "unknown/invalid code", not as a failure.
- **Query-string filters are IGNORED.** `?batch_id=`, `?given_name=`, etc. return the *entire* collection.
  Always fetch the full list and filter client-side on the relevant field.

## Endpoint families

| Endpoint | Returns / use |
|---|---|
| `GET /api/patients` | All patients (demographics). Filter client-side; duplicates share display_name. |
| `GET /api/patients/{id}` | Demographics: `given_name/family_name/suffix`, `dob`, `sex`, `address`, `phone`, `insurance_id`, `enterprise_mrn`, `canonical_status`, `canonical_patient_id`, embedded `primary_care_provider{...}`. |
| `GET /api/patients/{id}/conditions` | Problem list; each row has `status`, `normalized_key`, `code`, `description`, `source`, `id`, `onset_date`. |
| `GET /api/patients/{id}/medications` | `status`, `normalized_key`, `medication`, `dose`, `route`, `frequency`, `source`, `id`. |
| `GET /api/patients/{id}/allergies` | `status`, `normalized_key`, `allergen`, `reaction`, `severity`, `source`, `id`. |
| `GET /api/patients/{id}/encounters` | `encounter_id`, `date`, `type`, `provider_id`, `signed_status`, `diagnoses[]`, `medications_mentioned[]`, `care_plan_notes`. |
| `GET /api/patients/{id}/immunizations` | `id`, `date`, `vaccine`. |
| `GET /api/patients/{id}/documents` | `document_id`, `type`, `status`, `date`, `source`. Types seen: `chart_summary` (internal), `identity_verification`, `external_cardiology_note`/external notes, `echocardiogram`. |
| `GET /api/patients/{id}/disclosures` | `disclosure_id`, `date`, `status` (permitted/pending/denied/expired), `purpose`, `recipient`, `recipient_provider_id`. |
| `GET /api/patients/{id}/service-requests` | Per-patient ServiceRequests (see below). Top-level `/api/service-requests` is not a listing — go via the patient. |
| `GET /api/audit-logs` | Bare array: `audit_id`, `date`, `actor`, `event`, `patient_id`, `summary`. Match on patient_id and on ids inside `summary`. |
| `GET /api/duplicates/candidates` | All candidates. |
| `GET /api/duplicates/{candidate_id}` | `candidate_id`, `status` (open/needs_review/…), `patient_ids[]`, `match_signals[]`, `conflict_signals[]`, `merge_preview{preferred_target_patient_id, source_patient_id, active_condition_keys[], active_medication_keys[], active_allergy_keys[]}`. Target/source may be `null`. |
| `GET /api/referrals` | All referrals; filter client-side by `batch_id`. |
| `GET /api/referrals/{referral_id}` | `referral_id`, `patient_id`, `batch_id`, `service_line`, `requested_date`, `status`, `urgency`, `authorization_status` (approved/pending/missing), `diagnosis_code`, `diagnosis_narrative`, `documents_received[]`, `receiving_provider_id`, `coordination_note`. |
| `GET /api/icd10` / `GET /api/icd10/{code}` | `code`, `chapter`, `requires_laterality`, `expected_terms[]`. 404 = unknown code. |
| `GET /api/providers` / `GET /api/providers/{id}` | Directory: `provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax`. |
| `GET /api/service-codes` / `GET /api/service-codes/{code}` | `code`, `display`, `service_line`, `order_kind`, `active`. |

## ServiceRequest shape (from the patient endpoint)

`service_request_id`, `patient_id`, `status` (draft/active/…), `intent`, `priority`, `service_code`,
`requester_id`, `performer_id`, `authored_on`, `occurrence_date`, `reason_codes[]` (ICD-10 codes), and an
`sbar{situation, background, assessment, recommendation}` object. SBAR coverage = which of those four keys are
present/non-empty.

## Practical fetching notes

- Prefer `curl -s` + `jq`; guard for both the wrapped and bare shapes.
- For a merge/duplicate task, pull **both** patients' full active lists and union them — don't rely on the
  candidate's `merge_preview` alone.
- For a batch audit, fetch `/api/referrals` once, filter to the batch client-side, then iterate: icd10 lookups
  per distinct `diagnosis_code`, provider lookups per distinct `receiving_provider_id`.
