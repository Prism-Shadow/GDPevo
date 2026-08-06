# EHR API Endpoints & Record Shapes

Source of truth for network access: `environment_access.md` (base URL + allowed
GET endpoints). The base URL placeholder `<TASK_ENV_BASE_URL>` in any prompt maps
to that base URL. No authentication. **Never read local source files for
environment data — the network API is the only source of truth.** Only call the
allowed GET endpoints listed there.

All list endpoints return an object keyed by the plural resource name
(e.g. `{"providers": [...]}`, `{"patients": [...]}`). Detail endpoints return
the bare object. Empty collections return `{"<resource>": []}`.

## Endpoint catalog

| Path | Returns | Use for |
|------|---------|---------|
| `GET /api/patients` | patient list | resolve IDs by demographic/insurance, find canonical vs duplicate shells |
| `GET /api/patients/{patient_id}` | patient detail | demographics, MRN, canonical_status |
| `GET /api/patients/{patient_id}/conditions` | condition list | active clinical keys, ICD-10 codes |
| `GET /api/patients/{patient_id}/medications` | medication list | active medication keys, highlights |
| `GET /api/patients/{patient_id}/allergies` | allergy list | active allergy keys, allergy readiness |
| `GET /api/patients/{patient_id}/encounters` | encounter list | handoff selection, recent-visit evidence |
| `GET /api/patients/{patient_id}/immunizations` | immunization list | latest immunization for transitions |
| `GET /api/patients/{patient_id}/documents` | document list | evidence selection, required-document checks |
| `GET /api/patients/{patient_id}/service-requests` | service-request list | SR quality validation |
| `GET /api/patients/{patient_id}/disclosures` | disclosure list | transition disclosure status |
| `GET /api/audit-logs` | audit log list | merge-packet evidence; filter to involved patients/events |
| `GET /api/duplicates/candidates` | candidate list | duplicate review, merge preview |
| `GET /api/duplicates/{candidate_id}` | candidate detail | same shape as list item |
| `GET /api/referrals` | referral list | batch audit, coordination packet |
| `GET /api/referrals/{referral_id}` | referral detail | same shape as list item |
| `GET /api/icd10` | ICD-10 directory | code validation (chapter, laterality, expected_terms) |
| `GET /api/icd10/{code}` | ICD-10 entry | single-code lookup |
| `GET /api/providers` | provider list | recipient/specialist/PCP contact |
| `GET /api/providers/{provider_id}` | provider detail | same shape as list item |
| `GET /api/service-codes` | service-code list | service-code validation |
| `GET /api/service-codes/{code}` | service-code entry | single-code lookup |

## Record field shapes

Field names are stable; emit them exactly as shown when the template requests them.

### patient
`patient_id`, `enterprise_mrn`, `display_name`, `dob` (YYYY-MM-DD),
`insurance_id`, `phone`, `canonical_status` (`active` | `duplicate` | ...).

### condition
`id`, `patient_id`, `code` (ICD-10), `description`, `normalized_key`,
`onset_date`, `source` (e.g. `problem_list`), `status` (`active` | `inactive` | ...).

### medication
`id`, `patient_id`, `medication` (display name), `normalized_key`, `dose`,
`route`, `frequency`, `source` (e.g. `medication_reconciliation`),
`status` (`active` | `inactive` | ...).

### allergy
`id`, `patient_id`, `allergen`, `normalized_key`, `reaction`, `severity`
(`mild` | `moderate` | `severe` | `unknown`), `source` (e.g. `patient_reported`),
`status` (`active` | `inactive` | `entered-in-error` | `unknown`).

### encounter
`encounter_id`, `patient_id`, `date` (YYYY-MM-DD), `type`, `provider_id`,
`signed_status` (`signed` | `unsigned` | `amended` | `draft`), `diagnoses`
(array of ICD-10 codes), `medications_mentioned` (array), `care_plan_notes`.

### document
`document_id`, `patient_id`, `date`, `type`, `source` (e.g. `ehr_export`,
`external_import`), `status` (`final` | `preliminary` | `cancelled` | ...).

### immunization
`id`, `patient_id`, `date`, `vaccine`.

### disclosure
`disclosure_id`, `patient_id`, `date`, `status`
(`permitted` | `pending` | `denied` | `expired`), `purpose`,
`recipient_provider_id`.

### service-request
`service_request_id`, `patient_id`, `status` (`draft` | `active` | `on-hold` |
`revoked` | `completed` | `entered-in-error`), `intent` (`proposal` | `plan` |
`order` | `original-order` | `reflex-order` | `filler-order` | `instance-order` |
`option`), `priority` (`routine` | `urgent` | `asap` | `stat`), `service_code`,
`requester_provider_id`, `performer_provider_id`, `authored_on`,
`occurrence_date`, `reason_codes` (array of ICD-10 codes).

### duplicate candidate
`candidate_id`, `patient_ids` (array of 2), `status` (`open` | `needs_review` |
...), `match_signals` (array), `conflict_signals` (array), `merge_preview`:
{ `preferred_target_patient_id` (nullable), `source_patient_id` (nullable),
`active_condition_keys`, `active_medication_keys`, `active_allergy_keys` }.

> The `merge_preview` is a **hint**, not authoritative. See
> `reasoning_playbooks.md` → "Duplicate merge readiness": the patient
> active-list endpoints override the preview.

### referral
`referral_id`, `patient_id`, `batch_id`, `service_line`, `requested_date`,
`status` (`open` | `closed` | `cancelled` | `draft`), `urgency` (`routine` |
`urgent` | `stat`), `authorization_status` (`approved` | `pending` | `denied` |
`missing` | `not_required` | `unknown`), `diagnosis_code` (ICD-10),
`diagnosis_narrative`, `documents_received` (array), `receiving_provider_id`,
`coordination_note`.

### audit log
`audit_id`, `patient_id`, `date`, `actor`, `event` (e.g. `identity_review`,
`external_import`, `merge_completed`), `summary`.

### icd10 entry
`code`, `chapter` (e.g. `Musculoskeletal`, `Circulatory`, `Endocrine`,
`Respiratory`, `Nervous system`, `Symptoms`), `expected_terms` (array of
lowercased narrative substrings), `requires_laterality` (boolean).

### service-code entry
`code`, `display`, `order_kind` (`consultation` | `handoff`), `service_line`,
`active` (boolean).

### provider
`provider_id`, `name`, `role`, `service_line`
(`primary_care` | `orthopedics` | `cardiology` | `pulmonology` | `neurology` |
`skilled_nursing` | `oncology`), `facility`, `phone`, `fax`.
