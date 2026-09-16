# EHR API Endpoints

All endpoints are read-only GETs at `<TASK_ENV_BASE_URL>`, serialised as JSON.
Timestamps and dates use ISO-8601 / `YYYY-MM-DD`.

## Patient & Clinical Records

### GET /api/patients
Returns an array of patient summary objects. Use for searching or listing.
Each entry includes `patient_id`, `display_name`, `dob`, `sex`, `mrn`.

### GET /api/patients/{patient_id}
Full patient demographic record. Fields include:
`patient_id`, `enterprise_mrn`, `display_name`, `given_name`, `family_name`,
`dob`, `sex`, `address_line`, `city`, `state`, `zip`, `phone`, `email`,
`insurance_id`, `primary_care_provider_id`.

### GET /api/patients/{patient_id}/conditions
Array of condition/problem-list entries. Key fields per entry:
`code` (ICD-10), `description`, `normalized_key` (snake_case label),
`clinical_status` (active | inactive | resolved | remission),
`verification_status`, `onset_date`, `recorded_date`.

For active-list work, filter to `clinical_status: "active"`.

### GET /api/patients/{patient_id}/medications
Array of medication entries. Key fields:
`normalized_key` (snake_case), `name`, `dose`, `route`, `frequency`,
`status` (active | inactive | completed | stopped | unknown).

Filter to `status: "active"` for active medication lists.

### GET /api/patients/{patient_id}/allergies
Array of allergy/intolerance entries. Key fields:
`normalized_key`, `allergen` (display name), `reaction`, `severity`
(mild | moderate | severe | unknown), `clinical_status`
(active | inactive | resolved | entered-in-error | unknown).

Filter to `clinical_status: "active"` for active allergy lists unless the
template asks for a broader status scan.

### GET /api/patients/{patient_id}/encounters
Array of encounter records. Key fields:
`encounter_id`, `date` (YYYY-MM-DD), `type` (office_visit | care_transition |
emergency | inpatient | etc.), `signed_status` (signed | amended | draft |
unsigned), `diagnosis_codes` (array of ICD-10 strings), `medications_mentioned`
(array of drug name strings), `care_plan_tag` (enum),
`encounter_provider_id`.

Sort newest-to-oldest by `date` when the template requires a handoff window.

### GET /api/patients/{patient_id}/immunizations
Array of immunization records. Key fields:
`immunization_id`, `date`, `vaccine` (display name), `status`.

For "latest immunization," pick the most recent by date among records with
status `completed` or equivalent.

### GET /api/patients/{patient_id}/documents
Array of clinical documents. Key fields:
`document_id`, `type` (e.g. echocardiogram, office_note, chart_summary,
radiology_report, external_continuity_document), `status`
(final | preliminary | cancelled), `date`, `subject_patient_id`.

For merge packets, documents with `subject_patient_id` matching the other
patient in a duplicate pair are continuity evidence. General chart summaries
are usually excluded from merge packets.

### GET /api/patients/{patient_id}/disclosures
Array of disclosure/consent records. Key fields:
`disclosure_id`, `date`, `status` (permitted | pending | denied | expired),
`purpose`, `recipient_provider_id`.

Match disclosures by `recipient_provider_id` against the target provider.

### GET /api/patients/{patient_id}/service-requests
Array of ServiceRequest records for a patient. Key fields:
`service_request_id`, `status` (draft | active | on-hold | revoked | completed |
entered-in-error), `intent` (order | plan | proposal | etc.),
`priority` (routine | urgent | asap | stat), `service_code`,
`requester_provider_id`, `performer_provider_id`, `authored_on`,
`occurrence_date`, `reason_codes` (ICD-10 array), `patient_id`.

## Quality & Governance Endpoints

### GET /api/audit-logs
Array of audit trail entries. Key fields:
`audit_id`, `event_type`, `timestamp`, `subject_patient_id`,
`acting_provider_id`, `description`.

Filter by `subject_patient_id` to find relevant audit records for a specific
patient or duplicate candidate.

### GET /api/duplicates/candidates
Array of duplicate candidate summaries. Each includes `candidate_id`,
`patient_ids` array, `status` (confirmed_duplicate | needs_review |
not_duplicate), and basic match signal counts.

### GET /api/duplicates/{candidate_id}
Full duplicate candidate detail. Key fields:
`candidate_id`, `status`, `primary_patient_id`, `possible_duplicate_patient_id`,
`match_signals` (array of enum strings: same_dob | same_insurance |
similar_address | same_phone | same_given_name), `conflict_signals`
(array of enum strings: different_given_name | different_phone |
opposite_laterality_problem | different_dob | different_insurance |
different_address), `evidence_document_ids`, `audit_ids`, `review_notes`,
`created_date`.

### GET /api/referrals
Array of referral summaries. Key fields:
`referral_id`, `patient_id`, `batch_id`, `service_line`, `diagnosis_code`,
`diagnosis_narrative`, `status` (open | closed | cancelled | draft),
`requested_date`.

Use query parameters if available (e.g. `?batch_id=MARCH26-ORTHO-A`) to filter
by batch.

### GET /api/referrals/{referral_id}
Full referral detail. Key fields:
`referral_id`, `patient_id`, `batch_id`, `service_line`, `requested_date`,
`referral_status`, `urgency` (routine | urgent | stat),
`diagnosis_code` (primary ICD-10), `diagnosis_narrative` (free text reason),
`referring_provider_id`, `receiving_provider_id`,
`authorization_status` (approved | pending | denied | not_required),
`required_documents` (array of type strings),
`received_document_ids` (array), `care_plan_tag`.

### GET /api/icd10
Array of ICD-10 directory entries. Each includes `code`, `description`,
`chapter`.

### GET /api/icd10/{code}
Single ICD-10 code detail: `code`, `description`, `chapter` (string, e.g.
"Musculoskeletal", "Circulatory", "Injury", "Respiratory", "Endocrine"), plus
optional `laterality` hints and `includes`/`excludes` notes.

### GET /api/providers
Array of provider directory entries. Each includes `provider_id`, `name`,
`role`, `service_line`, `facility`.

### GET /api/providers/{provider_id}
Full provider detail: `provider_id`, `name`, `role`, `service_line`, `facility`,
`phone`, `fax`, `npi`, `specialties` (array).

### GET /api/service-codes
Array of service code entries.

### GET /api/service-codes/{code}
Single service code detail, including validity status against the code system.
