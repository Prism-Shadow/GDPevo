# EHR quality-governance API — endpoint & data-model reference

All access is **read-only HTTP GET**, **no credentials**. The base URL is given in the
task's `environment_access.md` as `GDPEVO_ENV_BASE_URL` (prompts write it as
`<TASK_ENV_BASE_URL>`). Only the endpoints listed in `environment_access.md` are
allowed — re-read that file each task; do not assume an endpoint exists.

Fetch, then filter/join client-side. List endpoints return the **whole** collection
(e.g. `/api/referrals` returns every referral across every batch; `/api/audit-logs`
returns every log for every patient). Never assume a list is pre-scoped to your case.

## Endpoint catalog

| Endpoint | Returns | Key fields |
|---|---|---|
| `GET /api/patients` | `{patients:[...]}` all patients | `patient_id, display_name, given_name, family_name, dob, sex, phone, address, insurance_id, enterprise_mrn, canonical_status, canonical_patient_id, primary_care_provider{...}, primary_care_provider_id` |
| `GET /api/patients/{id}` | one patient (same fields) | see above |
| `GET /api/patients/{id}/conditions` | `{conditions:[...]}` | `id, code, description, normalized_key, status, onset_date, source, patient_id` |
| `GET /api/patients/{id}/medications` | `{medications:[...]}` | `id, medication, dose, route, frequency, normalized_key, status, source` |
| `GET /api/patients/{id}/allergies` | `{allergies:[...]}` | `id, allergen, reaction, severity, normalized_key, status, source` |
| `GET /api/patients/{id}/encounters` | `{encounters:[...]}` | `encounter_id, date, type, provider_id, signed_status, diagnoses[], medications_mentioned[], care_plan_notes` |
| `GET /api/patients/{id}/immunizations` | `{immunizations:[...]}` | `id, date, vaccine` |
| `GET /api/patients/{id}/documents` | `{documents:[...]}` | `document_id, type, status, date, source` |
| `GET /api/patients/{id}/service-requests` | `{service_requests:[...]}` | `service_request_id, status, intent, priority, service_code, requester_id, performer_id, authored_on, occurrence_date, reason_codes[], sbar{situation,background,assessment,recommendation}` |
| `GET /api/patients/{id}/disclosures` | `{disclosures:[...]}` | `disclosure_id, date, status, purpose, recipient, recipient_provider_id` |
| `GET /api/audit-logs` | `{audit_logs:[...]}` **(global)** | `audit_id, date, actor, event, patient_id, summary` |
| `GET /api/duplicates/candidates` | `{duplicate_candidates:[...]}` | see below |
| `GET /api/duplicates/{candidate_id}` | one candidate | see below |
| `GET /api/referrals` | `{referrals:[...]}` **(global)** | see below |
| `GET /api/referrals/{referral_id}` | one referral | see below |
| `GET /api/icd10` | `{icd10:[...]}` full directory | `code, chapter, expected_terms[], requires_laterality` |
| `GET /api/icd10/{code}` | one code; **404 `{error,status:404}` if unknown** | as above |
| `GET /api/providers` | `{providers:[...]}` directory | `provider_id, name, role, service_line, facility, phone, fax` |
| `GET /api/providers/{provider_id}` | one provider | as above |
| `GET /api/service-codes` | `{service_codes:[...]}` | `code, display, order_kind, service_line, active` |
| `GET /api/service-codes/{code}` | one service code | as above |

## Duplicate candidate shape
```
candidate_id, status(open|needs_review|...), patient_ids[],
match_signals[]   (e.g. same_dob, same_phone, same_insurance, name_variant,
                   similar_address, same_address_normalized, shared_external_*_document),
conflict_signals[] (e.g. address_abbreviation, different_given_name, different_phone,
                   opposite_laterality_problem, suffix_discrepancy),
merge_preview{ preferred_target_patient_id, source_patient_id,
               active_condition_keys[], active_medication_keys[], active_allergy_keys[] }
```
`merge_preview` is a **hint/preview only** (may be stale, partial, or `null`); patient
active-list endpoints are authoritative (see decision_rules.md).

## Referral shape
```
referral_id, batch_id, patient_id, service_line, requested_date, status, urgency,
diagnosis_code, diagnosis_narrative, authorization_status(approved|pending|missing),
documents_received[]  (e.g. echocardiogram, office_note, mri, xray, insurance_card,
                       physical_therapy_note, chest_xray),
receiving_provider_id, coordination_note
```

## Patient identity / canonical fields
- `canonical_status`: `active` (a live canonical record), `duplicate` (already resolved
  into another chart — see `canonical_patient_id`), `possible_duplicate` (unresolved).
- `canonical_patient_id`: for a `duplicate`, the patient_id it collapses into; `null`
  for an `active` record.
- `enterprise_mrn`: stable enterprise identifier per record.

## Provider directory service lines
`primary_care, cardiology, orthopedics, pulmonology, neurology, skilled_nursing,
oncology`. Each provider row carries `name, role, service_line, facility, phone, fax`.
A patient's PCP is embedded in the patient detail (`primary_care_provider`). Look up
the **specialist / receiving** provider by matching the case's target service line to
`providers[].service_line` (or by the `receiving_provider_id` / `performer_id` on the
referral / service-request).

## Service codes
`{CARD-CONSULT, ORTHO-CONSULT, PULM-CONSULT, NEURO-CONSULT, ONC-CONSULT}` are
`consultation` orders; `SNF-HANDOFF` is a `handoff`. Each has `service_line` and
`active`. A service code is **valid** when it exists, `active:true`, and its
`service_line` matches the performer's service line.

## ICD-10 directory
Each code returns `chapter` (e.g. `Musculoskeletal, Injury, Circulatory, Respiratory,
Neoplasms, Endocrine, Nervous system, Symptoms, Factors influencing health status`),
`expected_terms[]` (narrative phrases the code stands for), and `requires_laterality`
(bool). Unknown code ⇒ HTTP 404. Use these three fields for all code validation
(chapter-range, narrative-match, laterality).
