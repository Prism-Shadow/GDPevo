# EHR Governance API — endpoint & field map

Base URL from `environment_access.md` (`GDPEVO_ENV_BASE_URL`). Read-only, no auth.
Only the endpoints below are allow-listed. **List endpoints ignore query params —
fetch all and filter client-side.** Detail endpoints 404 on unknown ids.
Field values shown are schematic placeholders, not answers.

## Patients
- `GET /api/patients` → `{"patients":[{patient_id, display_name, dob,
  enterprise_mrn, insurance_id, phone, canonical_status}]}` (trimmed list).
- `GET /api/patients/{id}` → full demographics:
  `{patient_id, given_name, family_name, display_name, suffix, dob, sex, address,
  phone, insurance_id, enterprise_mrn, canonical_patient_id, canonical_status,
  primary_care_provider_id, primary_care_provider:{provider_id, name, role,
  service_line, facility, phone, fax}}`.

## Clinical lists (per patient)
- `.../conditions` → `{"conditions":[{id, patient_id, code, description,
  normalized_key, status, onset_date, source}]}`
- `.../medications` → `{"medications":[{id, patient_id, medication, dose, route,
  frequency, normalized_key, status, source}]}`
- `.../allergies` → `{"allergies":[{id, patient_id, allergen, reaction, severity,
  normalized_key, status, source}]}`
- `status` ∈ `active|inactive|resolved|entered-in-error`. "Active keys" = `status
  == active`, use `normalized_key`. Beware placeholder keys (`baseline_med`,
  `baseline_allergy`) and duplicated concepts from different `source`s.

## Encounters
- `.../encounters` → `{"encounters":[{encounter_id, patient_id, date, type,
  provider_id, signed_status, diagnoses:[icd10...], medications_mentioned:[...],
  care_plan_notes}]}`. `signed_status` ∈ `signed|unsigned|amended|draft`.

## Documents
- `.../documents` → `{"documents":[{document_id, patient_id, date, type, status,
  source}]}`. `status` includes `final|preliminary|cancelled`. Types seen:
  `identity_verification`, `chart_summary`, external continuity/specialty exports,
  `echocardiogram`, `office_note`. Use `final` only; apply the packet's type policy.

## Immunizations / Disclosures / Service-requests (per patient)
- `.../immunizations` → `{"immunizations":[{id, patient_id, date, vaccine}]}`
  (pick latest by date).
- `.../disclosures` → `{"disclosures":[{disclosure_id, patient_id, date, status,
  purpose, recipient, recipient_provider_id}]}`. `status` ∈
  `permitted|pending|denied|expired`.
- `.../service-requests` → `{"service_requests":[{service_request_id, patient_id,
  status, intent, priority, service_code, requester_id, performer_id,
  reason_codes:[icd10...], authored_on, occurrence_date,
  sbar:{situation, background, assessment, recommendation}}]}`.

## Duplicates
- `GET /api/duplicates/candidates` and `/api/duplicates/{candidate_id}` →
  `{candidate_id, status, patient_ids:[...], match_signals:[...],
  conflict_signals:[...], merge_preview:{preferred_target_patient_id,
  source_patient_id, active_condition_keys:[...], active_medication_keys:[...],
  active_allergy_keys:[...]}}`. `status` ∈ `open|needs_review|...`.
  `merge_preview` is a HINT — verify against patient list endpoints.
  A null `preferred_target_patient_id` / `source_patient_id` signals the engine
  did not pick a canonical direction (typically `needs_review`/`do_not_merge`).
  Signal vocabularies observed: matches `same_dob|same_phone|same_insurance|
  similar_address|same_address_normalized|name_variant|same_given_name|
  shared_external_*_document`; conflicts `address_abbreviation|different_given_name|
  different_phone|different_dob|different_insurance|different_address|
  opposite_laterality_problem|suffix_discrepancy`. (Templates may require a
  narrower controlled enum — map to the template's `allowed_values`.)

## Referrals
- `GET /api/referrals` (all) and `/api/referrals/{id}` → `{referral_id, batch_id,
  patient_id, service_line, diagnosis_code, diagnosis_narrative,
  documents_received:[...], authorization_status, receiving_provider_id,
  requested_date, status, urgency, coordination_note}`. `authorization_status` ∈
  `approved|pending|missing|denied`. `status` ∈ `open|closed|cancelled|draft`.
  `urgency` ∈ `routine|urgent|stat`. Filter a batch by `batch_id`, a patient by
  `patient_id` — client-side.

## Audit logs
- `GET /api/audit-logs` → `{"audit_logs":[{audit_id, patient_id, date, actor,
  event, summary}]}`. Filter to the case patients + the relevant event; ignore
  unrelated merges/other patients.

## Reference directories
- `GET /api/icd10` / `/api/icd10/{code}` → `{code, chapter, expected_terms:[...],
  requires_laterality}`; 404 ⇒ unknown code. Chapters seen: `Circulatory`,
  `Musculoskeletal`, `Neoplasms`, `Nervous system`, `Endocrine`, `Injury`,
  `Factors influencing health status`, `Respiratory`.
- `GET /api/providers` / `/api/providers/{id}` → `{provider_id, name, role,
  facility, phone, fax, service_line}`. One provider per service line
  (`primary_care`, `orthopedics`, `cardiology`, `pulmonology`, `neurology`,
  `skilled_nursing`, `oncology`).
- `GET /api/service-codes` / `/api/service-codes/{code}` → `{code, display,
  order_kind, service_line, active}`.
