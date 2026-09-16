# Referral Coordination Packet

Use when the task asks for a "referral coordination packet" or mentions a referral ID and patient ID.

## Input Signals

- A referral ID and patient ID in the task prompt.
- An `answer_template.json` with keys: `patient_referral`, `active_diagnoses`, `referral_code_set`, `allergy_readiness`, `recent_encounter_evidence`, `required_document_evidence`, `receiving_provider`, `authorization_readiness`, `medication_highlights`, `referral_letter_fields`.

## Evidence Gathering Order

1. `GET /api/referrals/{referral_id}` - referral detail, diagnosis code, narrative, receiving provider, authorization status.
2. `GET /api/patients/{patient_id}` - patient demographics.
3. `GET /api/patients/{patient_id}/conditions` - all conditions, cross-walk active ones with referral diagnosis.
4. `GET /api/patients/{patient_id}/medications` - filter to active, identify referral-relevant ones.
5. `GET /api/patients/{patient_id}/allergies` - active allergies for allergy readiness.
6. `GET /api/patients/{patient_id}/encounters` - most recent encounter with related care_plan_tag.
7. `GET /api/patients/{patient_id}/documents` - echo, office note, imaging documents.
8. `GET /api/icd10/{code}` for the referral diagnosis code and each active condition code.
9. `GET /api/providers/{receiving_provider_id}` - the specialist receiving the referral.
10. `GET /api/providers/{pcp_id}` - the patient's primary care provider.

## Reconciliation Rules

### Referral Code Set

- The `primary_code` is the diagnosis code on the referral.
- `supporting_codes` come from referral narrative or recent encounter diagnosis codes related to the referral reason.
- Validate primary code: check it exists, chapter matches service line, description aligns with narrative.
- If chapter does not match service line: `icd_validation` is `valid_but_narrative_mismatch` or `wrong_service_chapter`.

### Active Diagnoses

- Include all active conditions from problem list plus referral intake diagnoses not on the list.
- Mark `referral_relevant: true` for diagnoses related to the referral service line or narrative.
- Sort by code ascending.

### Allergy Readiness

- Collect all active allergies. `ready_for_letter: true` when complete and documented.
- `follow_up_needed: true` only when allergy records are missing or conflicting.

### Recent Encounter Evidence

- Select the most recent signed encounter whose `care_plan_tag` or `diagnosis_codes` relate to the referral.
- Extract `diagnosis_codes` and `medications_mentioned`.

### Required Document Evidence

- Check document requirements per service line: echo for cardiology, office note for all, imaging for ortho.
- Report received documents with ID, date, status. List missing types in `missing_required_documents`.

### Authorization Readiness

- Map `authorization_status` and `referral_status` to template enums.
- `overall_readiness: ready_to_send` when auth approved, docs received, allergies complete, code valid.
- Hold statuses for missing auth, missing docs, or clinical clarification.

### Medication Highlights

- From active meds, select those relevant to the service line. Cardiovascular: diuretics, ACE inhibitors. Orthopedic: analgesics.
- `highlight_reason` describes clinical relevance.

### Referral Letter Fields

- Each `*_choice` field selects a normalized label from the template enums summarizing that section of evidence.

## Output Shape

Follow `answer_template.json` exactly. All enum values are defined in the template.
