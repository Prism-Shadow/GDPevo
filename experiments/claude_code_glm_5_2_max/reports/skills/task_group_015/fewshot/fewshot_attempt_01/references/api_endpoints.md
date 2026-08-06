# API Endpoints & Response Shapes

Base URL and the allowed endpoint list live in `environment_access.md`. No
authentication. `GET` only. The network API is the only source of truth for
environment data.

## Wrapper keys

Every list endpoint returns an object wrapping the array under a resource-named
key. Unwrap it:

| Endpoint | Wrapper key |
|---|---|
| `GET /api/patients` | `patients` |
| `GET /api/audit-logs` | `audit_logs` |
| `GET /api/duplicates/candidates` | `duplicate_candidates` |
| `GET /api/referrals` | `referrals` |
| `GET /api/icd10` | `icd10` |
| `GET /api/providers` | `providers` |
| `GET /api/service-codes` | `service_codes` |
| `GET /api/patients/{id}/conditions` | `conditions` |
| `GET /api/patients/{id}/medications` | `medications` |
| `GET /api/patients/{id}/allergies` | `allergies` |
| `GET /api/patients/{id}/encounters` | `encounters` |
| `GET /api/patients/{id}/documents` | `documents` |
| `GET /api/patients/{id}/immunizations` | `immunizations` |
| `GET /api/patients/{id}/disclosures` | `disclosures` |
| `GET /api/patients/{id}/service-requests` | `service_requests` |

Detail endpoints (`/api/patients/{id}`, `/api/duplicates/{id}`, `/api/referrals/{id}`,
`/api/icd10/{code}`, `/api/providers/{id}`, `/api/service-codes/{code}`) return the
single object directly (no wrapper).

## No server-side filtering

List endpoints **ignore query parameters** and return the full set. A request like
`/api/referrals?batch_id=…` returns every referral, not the filtered subset. Always
fetch the full list and filter client-side (by `batch_id`, `patient_id`,
`service_line`, etc.). `scripts/ehr_client.py` provides `referrals_for_batch`,
`referrals_for_patient`, and `audit_logs_for_patient` for this.

## Response shapes

### Patient
`GET /api/patients/{id}` →
`patient_id, display_name, given_name, family_name, suffix, dob, sex, phone, address,
enterprise_mrn, insurance_id, primary_care_provider, primary_care_provider_id,
canonical_patient_id, canonical_status`

`canonical_patient_id` / `canonical_status` identify the canonical record in a
duplicate pair. `primary_care_provider_id` feeds the PCP contact block.

### Conditions
`GET /api/patients/{id}/conditions` →
`id, code (ICD-10), description, normalized_key, status, source, onset_date, patient_id`

`status` ∈ `active` / inactive values. `normalized_key` is the canonical snake_case
clinical key — **read it, do not derive it**. `source` ∈ e.g. `problem_list`.

### Medications
`GET /api/patients/{id}/medications` →
`id, medication, normalized_key, dose, route, frequency, status, source, patient_id`

### Allergies
`GET /api/patients/{id}/allergies` →
`id, allergen, normalized_key, reaction, severity, status, source, patient_id`

`severity` ∈ `mild|moderate|severe|unknown`.

### Encounters
`GET /api/patients/{id}/encounters` →
`encounter_id, date, type, provider_id, signed_status, diagnoses[], medications_mentioned[],
care_plan_notes, patient_id`

`signed_status` ∈ `signed|unsigned|amended|draft`. `diagnoses` is a list of ICD-10
codes. `care_plan_notes` informs `care_plan_tag`.

### Documents
`GET /api/patients/{id}/documents` →
`document_id, date, type, status, source, patient_id`

`type` ∈ e.g. `echocardiogram`, `office_note`, `chart_summary`, `mri`. `status` ∈
`final|preliminary|cancelled`. `chart_summary` is an excluded distractor type for
merge packets.

### Immunizations
`GET /api/patients/{id}/immunizations` →
`id, date, vaccine, patient_id`

### Disclosures
`GET /api/patients/{id}/disclosures` →
`disclosure_id, date, status, purpose, recipient, recipient_provider_id, patient_id`

`status` ∈ `permitted|pending|denied|expired`.

### Service requests
`GET /api/patients/{id}/service-requests` →
`service_request_id, patient_id, status, intent, priority, service_code, requester_id,
performer_id, authored_on, occurrence_date, reason_codes[], sbar`

`status` ∈ `draft|active|on-hold|revoked|completed|entered-in-error`.
`intent` ∈ `proposal|plan|order|original-order|reflex-order|filler-order|instance-order|option`.
`priority` ∈ `routine|urgent|asap|stat`.
`sbar` is an object with keys `situation|background|assessment|recommendation` (each a
string, possibly empty) → drives `sbar_coverage`.

### Duplicate candidates
`GET /api/duplicates/{id}` →
`candidate_id, patient_ids[], status, match_signals[], conflict_signals[], merge_preview`

`status` ∈ `open|needs_review`. `merge_preview` =
`{preferred_target_patient_id, source_patient_id, active_condition_keys[],
active_medication_keys[], active_allergy_keys[]}` — a **hint** that may be a subset of
the patient active-list endpoints.

### Referrals
`GET /api/referrals/{id}` →
`referral_id, patient_id, batch_id, service_line, requested_date, status, urgency,
authorization_status, diagnosis_code, diagnosis_narrative, receiving_provider_id,
documents_received[], coordination_note`

`status` ∈ `open|closed|cancelled|draft`. `urgency` ∈ `routine|urgent|stat`.
`authorization_status` ∈ `approved|pending|missing` (map to the template enum; `missing`
→ authorization-missing queue). `documents_received` is a list of doc-type strings
(e.g. `office_note`, `mri`, `echo`) → drives records/imaging follow-up queues.

### ICD-10
`GET /api/icd10/{code}` →
`code, chapter, expected_terms[], requires_laterality`

`chapter` (e.g. `Musculoskeletal`, `Circulatory`, `Injury`, `Respiratory`,
`Endocrine`) drives out-of-range checks. `expected_terms` drives narrative matching.
`requires_laterality` drives laterality checks.

### Providers
`GET /api/providers/{id}` →
`provider_id, name, role, service_line, facility, phone, fax`

### Service codes
`GET /api/service-codes/{code}` →
`code, display, service_line, order_kind, active`

`active` drives `service_code_valid`.

### Audit logs
`GET /api/audit-logs` →
`audit_id, date, actor, event, patient_id, summary`

`event` ∈ `external_import|identity_review|merge_completed`. Filter by `patient_id`
for a merge packet; cite the relevant `audit_id`s.

## Stored vs derived fields

Some output fields are not stored directly and must be derived:

| Output field | Derived from |
|---|---|
| `performer_service_line` | `provider(performer_id).service_line` |
| `service_code_valid` | `service_code(code).active` |
| `reason_code_validation[].chapter` | `icd10_code(code).chapter` |
| `reason_code_validation[].valid` | code resolves in `/api/icd10` |
| `reason_code_validation[].matches_patient_evidence` | code appears in the patient's active conditions/encounter diagnoses |
| `sbar_coverage` | presence of non-empty `sbar` keys |
| `primary_code_chapter` / `narrative_match` | `icd10_code` lookup + `expected_terms` |
| clinical-key unions | active records from patient endpoints (authoritative) |
