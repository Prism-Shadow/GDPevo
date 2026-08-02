# EHR governance API reference

Read-only. Base URL = `GDPEVO_ENV_BASE_URL` from `environment_access.md`
(no credentials). Only the endpoints listed there are permitted. List endpoints
wrap rows in a single plural key; detail endpoints return the bare object;
missing resources return HTTP 404 `{"error": "...", "status": 404}`.

Field names below are the observed response shape. **Values shown are illustrative
placeholders — always read live data; never reuse a value from this file or from
any prior run.**

## Patients

- `GET /api/patients` → `{"patients": [ {patient_id, display_name, dob,
  enterprise_mrn, insurance_id, phone, canonical_status} ]}`. Query filters are
  unreliable; fetch all and filter locally (e.g. by `insurance_id` to find
  shared-insurance groups).
- `GET /api/patients/{id}` → full detail: `patient_id, display_name, given_name,
  family_name, suffix, dob, sex, address, phone, insurance_id, enterprise_mrn,
  canonical_status, canonical_patient_id, primary_care_provider_id,
  primary_care_provider{provider_id,name,role,service_line,facility,phone,fax}`.
  - `canonical_status`: `active` for a real chart, `duplicate` for a shell that
    was merged away. `canonical_patient_id` on a duplicate points at its target.
    These two fields confirm merge direction independently of the candidate.

### Clinical lists (per patient)

- `GET /api/patients/{id}/conditions` → `{"conditions": [ {id, patient_id, code,
  description, normalized_key, status, source, onset_date} ]}`
- `GET /api/patients/{id}/medications` → `{"medications": [ {id, patient_id,
  medication, normalized_key, status, source, dose, route, frequency} ]}`
- `GET /api/patients/{id}/allergies` → `{"allergies": [ {id, patient_id, allergen,
  normalized_key, status, source, reaction, severity} ]}`

`status` ∈ {`active`, `inactive`, `entered-in-error`, …}. **Active sets use only
`status == "active"`, de-duped by `normalized_key`.** Non-active records are
distractors. `source` (e.g. `problem_list`, `pcp_note`, `cardiology_import`,
`legacy_import`, `medication_reconciliation`, `patient_reported`,
`referral_intake`, `referral_form`) can disambiguate but does not by itself make
a record active.

### Other per-patient endpoints

- `GET /api/patients/{id}/encounters` → `{"encounters": [ {encounter_id, date,
  type, provider_id, signed_status, diagnoses[], medications_mentioned[],
  care_plan_notes} ]}`. `signed_status` ∈ {signed, amended, unsigned, draft}.
  `type` e.g. office_visit, telehealth, care_transition. Sequential case ids look
  like `ENC-<patient>-<n>`; random hashes (`ENC-<hex>`) are often distractors.
- `GET /api/patients/{id}/immunizations` → `{"immunizations": [ {id, date,
  vaccine, patient_id} ]}`. "Latest" = max `date`.
- `GET /api/patients/{id}/disclosures` → `{"disclosures": [ {disclosure_id, date,
  status, purpose, recipient, recipient_provider_id, patient_id} ]}`. `status` ∈
  {permitted, pending, denied, expired}. Pick the one whose
  `recipient_provider_id` / `purpose` matches the case.
- `GET /api/patients/{id}/documents` → `{"documents": [ {document_id, patient_id,
  type, status, date, source} ]}`. `status` ∈ {final, preliminary, cancelled}.
  Types include identity_verification, external_cardiology_note (external
  continuity), chart_summary (routine/distractor), echocardiogram, office_note.
- `GET /api/patients/{id}/service-requests` → `{"service_requests": [
  {service_request_id, patient_id, status, intent, priority, service_code,
  requester_id, performer_id, authored_on, occurrence_date, reason_codes[],
  sbar{situation, background, assessment, recommendation}} ]}`.
  Note the API keys `requester_id`/`performer_id` may map to template keys
  `requester_provider_id`/`performer_provider_id`.

## Duplicates

- `GET /api/duplicates/candidates` → `{"duplicate_candidates": [ … ]}`
- `GET /api/duplicates/{candidate_id}` → `{candidate_id, status, patient_ids[],
  match_signals[], conflict_signals[], merge_preview{preferred_target_patient_id,
  source_patient_id, active_condition_keys[], active_medication_keys[],
  active_allergy_keys[]}}`.
  - `status` ∈ {open, needs_review, …}. `match_signals` / `conflict_signals` are
    controlled labels (e.g. same_dob, same_insurance, same_phone, similar_address,
    name_variant, shared_external_cardiology_document; address_abbreviation,
    different_given_name, different_phone, opposite_laterality_problem). Map these
    onto whatever the template's `allowed_values` are.
  - `merge_preview` is a *preview only* — reconcile it against the live patient
    active-list endpoints (those win).

## Audit logs

- `GET /api/audit-logs` → `{"audit_logs": [ {audit_id, patient_id, actor, event,
  date, summary} ]}`. No server-side filter — fetch all and select the entries
  whose `patient_id`/`event` relate to your case (e.g. identity_review,
  external_import for a merge).

## Referrals

- `GET /api/referrals` → `{"referrals": [ … ]}` (fetch all; filter by `batch_id`
  or `patient_id` locally). `GET /api/referrals/{id}` → detail.
- Fields: `{referral_id, batch_id, patient_id, service_line, requested_date,
  diagnosis_code, diagnosis_narrative, receiving_provider_id, authorization_status,
  status, urgency, documents_received[], coordination_note}`.
  - `authorization_status` ∈ {approved, pending, missing, denied}.
  - `status` ∈ {open, closed, cancelled, draft}. `urgency` ∈ {routine, urgent, stat}.
  - `documents_received` holds labels like office_note, mri, xray, echocardiogram,
    insurance_card. Absence of an expected label drives the follow-up queues.

## Reference directories

- `GET /api/icd10` → `{"icd10": [ … ]}`; `GET /api/icd10/{code}` →
  `{code, chapter, requires_laterality, expected_terms[]}`; **404 ⇒ code is
  unknown/invalid.**
  - `chapter` examples: Musculoskeletal, Injury, Circulatory, Respiratory.
    Orthopedic referrals expect **Musculoskeletal**; any other chapter is
    `out_of_range_chapter`.
  - **narrative_match**: the referral/condition narrative is consistent with the
    code's `expected_terms` (semantic match, allowing synonyms). Otherwise a
    narrative mismatch.
  - **laterality_mismatch**: narrative names a side (left/right) opposite to the
    side implied by the code / its `expected_terms`.
  - **missing_laterality**: `requires_laterality == true` but the narrative names
    no side.
- `GET /api/service-codes` and `/api/service-codes/{code}` →
  `{code, display, service_line, order_kind, active}`. A service code is valid
  when the record exists and `active == true` (and, where relevant, its
  `service_line` matches the ordered specialty).
- `GET /api/providers` and `/api/providers/{id}` → `{provider_id, name, role,
  service_line, facility, phone, fax}`. Source of the full contact block for any
  packet recipient / specialist / PCP.
