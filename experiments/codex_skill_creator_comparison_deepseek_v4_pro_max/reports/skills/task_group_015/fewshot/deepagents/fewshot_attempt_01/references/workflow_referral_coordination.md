## Referral coordination packet

### Objective

Produce a normalized cardiology/orthopedic referral coordination packet. Reconcile the referral with the active chart, validate diagnosis codes, assess allergy readiness, and choose normalized referral-letter field values.

### Step-by-step

#### 1. Fetch the referral

`GET /api/referrals/{referral_id}`

Extract: `patient`, `diagnosisCode`, `supportingCodes`, `narrative`, `serviceLine`, `authorizationStatus`, `status` (open/closed), `batchId`, `requestedDate`, `urgent`, `providerId`.

#### 2. Fetch the patient

`GET /api/patients/{patient_id}`

Extract demographics and identifiers.

#### 3. Fetch patient clinical lists

`GET /api/patients/{patient_id}/conditions`
`GET /api/patients/{patient_id}/medications`
`GET /api/patients/{patient_id}/allergies`

Filter for active records. Include relevant source annotations for active diagnoses (e.g., "problem_list", "referral_intake").

#### 4. Validate the primary diagnosis code

`GET /api/icd10/{primary_code}`

Check:
- The code exists and is valid
- The chapter matches the service line (Cardiology → "Circulatory", Orthopedics → "Musculoskeletal")
- The ICD-10 description matches the referral narrative (check key clinical terms)

For `icd_validation`, use:
- `valid_matches_narrative`: code is valid and narrative agrees
- `valid_but_narrative_mismatch`: code is valid but narrative describes something else
- `invalid_code`: code not found in ICD-10 directory
- `wrong_service_chapter`: code exists but chapter is wrong for the service line

Set `narrative_match` to true only when the ICD-10 description aligns with the referral narrative. Check for laterality mismatches (left vs right), condition mismatches (e.g., osteoarthritis vs meniscus tear), and body-site mismatches (e.g., knee vs hip vs lumbar spine).

#### 5. Assess allergy readiness

From the active allergies, classify readiness:
- `complete_documented`: active allergies with reactions and severity documented
- `incomplete_needs_clarification`: allergies present but missing severity or reaction details
- `no_known_allergies`: no active allergies found
- `conflicting_allergy_records`: multiple conflicting records

Each allergy entry includes: `allergen`, `reaction`, `severity`, `status`, and `source`.

#### 6. Identify the most recent relevant encounter

From encounters, find the encounter whose diagnosis codes and care plan most closely match the referral reason. Look for encounters dated just before the referral requested_date. Tag the encounter with a `care_plan_tag`:
- `cardiology_referral_for_hfpef_dyspnea`: encounter documents heart failure with dyspnea
- `hypertension_followup`: routine BP follow-up
- `unrelated_recent_visit`: recent but not related to referral
- `other`: catch-all

Record the encounter's diagnosis codes and mentioned medications.

#### 7. Verify required documents

Check the patient's documents for required items. For a cardiology referral, verify:
- Echocardiogram: look for document type "echocardiogram" with status "final"
- Office note: confirm the referring provider's office note is present

List any missing required documents.

#### 8. Determine authorization and overall readiness

From the referral's `authorizationStatus`, classify as approved, pending, denied, not_required, or unknown.

Determine `overall_readiness`:
- `ready_to_send`: authorization approved, documents complete, allergy documented, codes valid
- `hold_for_authorization`: authorization pending or denied
- `hold_for_missing_documents`: required documents absent
- `hold_for_clinical_clarification`: diagnosis code issues or allergy conflicts

Populate `blocking_issues` with the specific enum values for each blocker.

#### 9. Highlight referral-relevant medications

From active medications, highlight ones relevant to the referral reason. Classify with `highlight_reason`:
- `heart_failure_diuretic`: furosemide, bumetanide, etc.
- `blood_pressure_management`: lisinopril, losartan, amlodipine, etc.
- `diabetes_management`: metformin, insulin, etc.
- `lipid_management`: atorvastatin, rosuvastatin, etc.
- `other_active_medication`: any active medication not in the above categories

Put referral-relevant medications first in the list.

#### 10. Choose referral letter field values

From the enumerated enum choices, select the normalized values that best represent the evidence:

- `diagnosis_summary_choice`: based on the primary diagnosis match with narrative and evidence
- `allergy_statement_choice`: based on allergy readiness findings
- `recent_encounter_choice`: based on the most relevant encounter
- `document_packet_choice`: based on document availability
- `medication_summary_choice`: based on highlighted medications
- `recipient_choice`: based on the receiving provider
- `authorization_statement_choice`: based on authorization status
- `readiness_choice`: based on overall readiness

### Output shape

The template provides the full schema. Top-level keys: `patient_referral`, `active_diagnoses`, `referral_code_set`, `allergy_readiness`, `recent_encounter_evidence`, `required_document_evidence`, `receiving_provider`, `authorization_readiness`, `medication_highlights`, `referral_letter_fields`.
