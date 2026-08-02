# EHR API — endpoint catalog & record shapes

Base URL and the allow-list come from `environment_access.md`
(`GDPEVO_ENV_BASE_URL`, no credentials). Only GET the listed paths. All responses
are JSON. Field names below are stable; identifier/value tokens are shown as
placeholders — read the real values from the live response for the current case.

Collection endpoints wrap the list in a named key (`{"patients":[…]}`,
`{"referrals":[…]}`, `{"service_requests":[…]}`, `{"audit_logs":[…]}`); per-patient
clinical lists return a bare JSON array. When in doubt, inspect the top-level keys
first (`curl … | jq 'keys'`).

## Patients

- `GET /api/patients` → `{patients:[{patient_id, display_name, dob, enterprise_mrn,
  insurance_id, phone, canonical_status}]}`. Use for search / batch enumeration.
  Note: names+DOBs repeat across patients — never identify a patient by name alone.
- `GET /api/patients/{id}` → `{patient_id, canonical_patient_id, canonical_status,
  display_name, given_name, family_name, suffix, dob, sex, address, phone,
  insurance_id, enterprise_mrn, primary_care_provider_id, primary_care_provider:{
  provider_id, name, role, service_line, facility, phone, fax}}`.

### Per-patient clinical lists (bare arrays)

- `.../conditions` → `[{id, patient_id, code, description, normalized_key,
  onset_date, source, status}]`  (`status` ∈ active | inactive | …)
- `.../medications` → `[{id, patient_id, medication, normalized_key, dose, route,
  frequency, source, status}]`
- `.../allergies` → `[{id, patient_id, allergen, normalized_key, reaction,
  severity, source, status}]`
- `.../encounters` → `[{encounter_id, patient_id, date, type, provider_id,
  signed_status, diagnoses:[icd10…], medications_mentioned:[…], care_plan_notes}]`
  (`signed_status` ∈ signed | amended | unsigned | draft)
- `.../immunizations` → `[{id, patient_id, date, vaccine}]`  (note: the id field is
  `id`; templates usually call it `immunization_id`)
- `.../documents` → `[{document_id, patient_id, date, type, status, source}]`
  (`type` e.g. external_cardiology_note, identity_verification, chart_summary, echo;
  `status` ∈ final | preliminary | cancelled)
- `.../service-requests` → `{service_requests:[{service_request_id, patient_id,
  status, intent, priority, service_code, requester_id, performer_id, authored_on,
  occurrence_date, reason_codes:[icd10…], sbar:{situation, background, assessment,
  recommendation}}]}`  (note fields are `requester_id`/`performer_id`; templates
  often ask for `requester_provider_id`/`performer_provider_id`)
- `.../disclosures` → `[{disclosure_id, patient_id, date, status, purpose,
  recipient, recipient_provider_id}]`  (`status` ∈ permitted | pending | denied |
  expired)

## Quality-governance endpoints

- `GET /api/audit-logs` → `{audit_logs:[{audit_id, date, actor, event, patient_id,
  summary}]}`. Filter to the case patient_ids and relevant events.
- `GET /api/duplicates/candidates` and `GET /api/duplicates/{candidate_id}` →
  `{candidate_id, status, patient_ids:[…], match_signals:[…], conflict_signals:[…],
  merge_preview:{preferred_target_patient_id, source_patient_id,
  active_condition_keys:[…], active_medication_keys:[…], active_allergy_keys:[…]}}`.
  `status` ∈ open | needs_review | … . **`merge_preview` is a hint and is often
  incomplete** — reconcile it against the patients' own active-list endpoints (see
  normalization rules).
- `GET /api/referrals` and `GET /api/referrals/{referral_id}` → referral rows:
  `{referral_id, patient_id, batch_id, service_line, requested_date, diagnosis_code,
  diagnosis_narrative, receiving_provider_id, status, urgency, authorization_status,
  documents_received:[…], coordination_note}`. `authorization_status` ∈ approved |
  pending | missing | … ; `urgency` ∈ routine | urgent | stat ; `documents_received`
  may contain e.g. echocardiogram, office_note, mri. Filter a batch by `batch_id`.

## Reference / directory endpoints

- `GET /api/icd10/{code}` → `{code, chapter, expected_terms:[…], requires_laterality}`.
  **Unknown code → HTTP 404** (treat as invalid / unknown_code). `chapter` examples:
  Musculoskeletal, Injury, Circulatory, Respiratory, Endocrine.
  `GET /api/icd10` lists the directory.
- `GET /api/service-codes/{code}` → `{code, display, service_line, order_kind,
  active}`. `GET /api/service-codes` lists them.
- `GET /api/providers/{id}` → `{provider_id, name, role, service_line, facility,
  phone, fax}`. `GET /api/providers` lists the directory. Copy the whole block for
  recipient / specialist / owner contact fields.

## Fetch tips

- `curl -sS "$BASE/api/…" | jq .` to inspect; `jq -c '.[]?'` to stream rows.
- Filter a batch: `jq -c '[.referrals[] | select(.batch_id=="<BATCH>")]'`.
- A 404 is meaningful data (unknown code / absent record), not just an error —
  capture it as the corresponding template signal.
