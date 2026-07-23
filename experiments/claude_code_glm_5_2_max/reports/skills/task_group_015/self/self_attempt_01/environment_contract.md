# Environment Contract

The shared read-only EHR quality-governance environment. All field names and vocabularies below
are stable environment constants (not task answers) — reuse them across every task.

## Access

- **Base URL**: the value of `<TASK_ENV_BASE_URL>` / the base URL in `environment_access.md`
  (host `task-env`, default port `9015`). No authentication.
- **Method**: GET only. No mutations.
- **Source of truth**: the network API. Do not read local source files for environment data.
- **Allowed endpoints** (the only paths you may call):

| Path | Returns |
|---|---|
| `GET /api/patients` | patient list |
| `GET /api/patients/{patient_id}` | patient detail |
| `GET /api/patients/{patient_id}/conditions` | condition list |
| `GET /api/patients/{patient_id}/medications` | medication list |
| `GET /api/patients/{patient_id}/allergies` | allergy list |
| `GET /api/patients/{patient_id}/encounters` | encounter list |
| `GET /api/patients/{patient_id}/immunizations` | immunization list |
| `GET /api/patients/{patient_id}/documents` | document list |
| `GET /api/patients/{patient_id}/service-requests` | service-request list |
| `GET /api/patients/{patient_id}/disclosures` | disclosure list |
| `GET /api/audit-logs` | audit-log list (filter by `patient_id`) |
| `GET /api/duplicates/candidates` | duplicate-candidate list |
| `GET /api/duplicates/{candidate_id}` | candidate detail (includes `merge_preview`) |
| `GET /api/referrals` | referral list (filter by `batch_id` or scan for a `referral_id`) |
| `GET /api/referrals/{referral_id}` | referral detail |
| `GET /api/icd10` | ICD-10 directory |
| `GET /api/icd10/{code}` | ICD-10 code detail |
| `GET /api/providers` | provider directory |
| `GET /api/providers/{provider_id}` | provider detail |
| `GET /api/service-codes` | service-code directory |
| `GET /api/service-codes/{code}` | service-code detail |

List responses are wrapped: `{"patients":[...]}`, `{"conditions":[...]}`, `{"referrals":[...]}`,
`{"duplicate_candidates":[...]}`, `{"icd10":[...]}`, `{"providers":[...]}`, `{"service_codes":[...]}`,
`{"audit_logs":[...]}`, etc. Detail responses are the bare object.

## Record field shapes

### patient (`/api/patients/{id}`)
`patient_id`, `enterprise_mrn`, `display_name`, `given_name`, `family_name`, `suffix` (nullable),
`dob` (`YYYY-MM-DD`), `sex`, `phone`, `address`, `insurance_id`, `canonical_status`
(e.g. `active`), `canonical_patient_id` (nullable), `primary_care_provider_id`, and an embedded
`primary_care_provider` object (same shape as a provider record).

### condition (`/api/patients/{id}/conditions`)
`id`, `patient_id`, `code` (ICD-10), `description`, `normalized_key`, `onset_date`, `source`
(e.g. `problem_list`), `status` (`active` | `inactive` | …).

### medication (`/api/patients/{id}/medications`)
`id`, `patient_id`, `medication` (display name), `normalized_key`, `dose`, `route`, `frequency`,
`source` (e.g. `medication_reconciliation`), `status` (`active` | `inactive` | …).

### allergy (`/api/patients/{id}/allergies`)
`id`, `patient_id`, `allergen`, `reaction`, `severity` (`mild` | `moderate` | `severe` | `unknown`),
`source` (e.g. `patient_reported`), `normalized_key`, `status`
(`active` | `inactive` | `entered-in-error` | `unknown`).

### encounter (`/api/patients/{id}/encounters`)
`encounter_id`, `patient_id`, `date` (`YYYY-MM-DD`), `type`, `provider_id`, `signed_status`
(`signed` | `amended` | `draft` | `unsigned` | `unknown`), `diagnoses` (array of ICD-10 codes),
`medications_mentioned` (array of medication name strings), `care_plan_notes` (free text — scan
for risk/handoff signals).

### immunization (`/api/patients/{id}/immunizations`)
`id`, `patient_id`, `date` (`YYYY-MM-DD`), `vaccine`.

### document (`/api/patients/{id}/documents`)
`document_id`, `patient_id`, `date` (`YYYY-MM-DD`), `type`, `status`, `source`.

### service-request (`/api/patients/{id}/service-requests`)
`service_request_id`, `patient_id`, `status` (`draft` | `active` | `on-hold` | `revoked` |
`completed` | `entered-in-error`), `intent` (`proposal` | `plan` | `order` | `original-order` |
`reflex-order` | `filler-order` | `instance-order` | `option`), `priority` (`routine` | `urgent` |
`asap` | `stat`), `service_code`, `requester_id`, `performer_id`, `authored_on` (`YYYY-MM-DD`),
`occurrence_date` (`YYYY-MM-DD`), `reason_codes` (array of ICD-10 codes), `sbar` object with keys
`situation`, `background`, `assessment`, `recommendation` (each a string; absence ⇒ section
missing).

### disclosure (`/api/patients/{id}/disclosures`)
`disclosure_id`, `patient_id`, `date` (`YYYY-MM-DD`), `status` (`permitted` | `pending` | `denied`
| `expired`), `purpose`, `recipient` (display string), `recipient_provider_id`.

### referral (`/api/referrals/{id}` and list items)
`referral_id`, `batch_id`, `patient_id`, `service_line`, `requested_date` (`YYYY-MM-DD`),
`diagnosis_code` (ICD-10), `diagnosis_narrative` (free text), `receiving_provider_id`,
`authorization_status` (`approved` | `pending` | `denied` | `missing` | …), `urgency` (`routine` |
`urgent` | `stat`), `status` (`open` | `closed` | `cancelled` | `draft`), `coordination_note`,
`documents_received` (array of document-type strings, e.g. `mri`, `office_note`, `echo`,
`chest_xray`).

### duplicate candidate (`/api/duplicates/{id}` and list items)
`candidate_id`, `status` (`open` | `needs_review`), `patient_ids` (array of 2), `match_signals`
(array of strings), `conflict_signals` (array of strings), `merge_preview` object with
`preferred_target_patient_id`, `source_patient_id`, `active_condition_keys`,
`active_medication_keys`, `active_allergy_keys` (each an array of `normalized_key` values).

### provider (`/api/providers/{id}` and list items)
`provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax`.

### icd10 (`/api/icd10/{code}` and list items)
`code`, `chapter`, `expected_terms` (array of lowercase substrings to match against the
narrative), `requires_laterality` (boolean — narrative must name the side `left`/`right`).

### service-code (`/api/service-codes/{code}` and list items)
`code`, `display`, `order_kind` (e.g. `consultation`, `handoff`), `service_line`, `active`
(boolean).

### audit-log (`/api/audit-logs` list items)
`audit_id`, `patient_id`, `date` (`YYYY-MM-DD`), `actor`, `event` (e.g. `identity_review`),
`summary` (free text).

## Value vocabularies (environment constants)

- **Service lines**: `orthopedics`, `cardiology`, `pulmonology`, `neurology`, `skilled_nursing`,
  `oncology`, `primary_care`.
- **ICD-10 chapters seen**: `Endocrine`, `Nervous system`, `Circulatory`, `Respiratory`,
  `Musculoskeletal`, `Symptoms`.
- **Document types**: `chart_summary`, `chest_xray`, `echocardiogram`, `external_cardiology_note`,
  `external_pulmonology_note`, `identity_verification`.
- **Document sources**: `ehr_export`, `imaging_archive`, `registration`, `summit_heart_center`,
  `northgate_pulmonary`.
- **Encounter types**: `office_visit`, `telehealth`, `telephone`, `urgent_care`, `care_transition`.
- **Encounter signed_status**: `signed`, `amended` (templates also allow `draft`, `unsigned`,
  `unknown`).

## Service-line → expected ICD-10 chapter map

Use this to validate that a referral/service-request diagnosis code belongs to the right service
line. A code whose chapter differs from the expected chapter is `wrong_service_chapter` /
`out_of_range_chapter`.

| Service line | Expected ICD-10 chapter |
|---|---|
| `cardiology` | `Circulatory` |
| `orthopedics` | `Musculoskeletal` |
| `pulmonology` | `Respiratory` |
| `neurology` | `Nervous system` |

`Endocrine` and `Symptoms` (R-codes) chapters do not map to a consult service line; a referral to
a consult service line carrying one of these chapters is out-of-range.

## Duplicate signal vocabulary (API raw values)

The duplicate-candidate API emits these raw signal strings. **Templates may impose a controlled
subset** (their own `allowed_values`) — always map the raw signals onto the template's vocabulary
and emit only allowed values; translate where names overlap, omit a raw signal only if no allowed
label fits the evidence.

- **Raw match signals**: `same_dob`, `same_phone`, `same_insurance`, `same_address_normalized`,
  `similar_address`, `name_variant`, `shared_external_cardiology_document`.
- **Raw conflict signals**: `address_abbreviation`, `suffix_discrepancy`, `different_given_name`,
  `different_phone`, `opposite_laterality_problem`.

Serious identity conflicts that block a merge: `different_dob`, `different_insurance`,
`opposite_laterality_problem`. Minor conflicts that permit merge-with-review:
`address_abbreviation`, `suffix_discrepancy`, `name_variant`.

Note: a `shared_external_cardiology_document` match signal implies an `external_cardiology_note`
document exists for one of the patients — relevant identity/continuity evidence for a merge packet.
