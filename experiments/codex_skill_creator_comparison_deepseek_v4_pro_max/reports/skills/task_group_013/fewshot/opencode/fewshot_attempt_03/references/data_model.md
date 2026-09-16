# Cedar Ridge Data Model

This reference maps the API response fields to their meanings so you can
correctly interpret raw data when applying business rules.

## Patient demographics (from `patient` key)

| Field | Type | Meaning |
|-------|------|---------|
| `patient_id` | string | Unique ID, always uppercase P followed by digits |
| `emergency_contact_present` | 0 or 1 | Whether emergency contact is on file |
| `existing_chart` | 0 or 1 | Whether a clinical chart exists for this patient |
| `preferred_contact` | string | portal / email / phone / sms |
| `address` | string or null | Street address; null means missing |
| `email` | string or null | Email address; null means missing |

## Insurance coverage (from `coverage` array)

| Field | Type | Meaning |
|-------|------|---------|
| `status` | string | active / expired / pending |
| `service_lines` | string | Comma-separated: e.g., `"primary_care,cardiology"` |
| `network_status` | string | in_network / out_of_network |
| `policy_number` | string | The policy ID |
| `payer` | string | BlueCross, Cigna, Aetna, Humana, United, Medicare, etc. |

## PBM / prescription benefits (from `pbm` array)

| Field | Type | Meaning |
|-------|------|---------|
| `status` | string | approved / rejected |
| `active` | 0 or 1 | Whether the PBM record is active |
| `formulary_status` | string | covered / not_found |
| `specialty_required` | 0 or 1 | Whether specialty pharmacy is required |
| `policy_number` | string | Policy ID; a mismatch with the coverage policy_number flags `pbm_policy_mismatch` |

## Pharmacies (from `pharmacies` array on patient)

| Field | Type | Meaning |
|-------|------|---------|
| `network_status` | string | in_network / out_of_network |
| `preference_rank` | integer | 1 = preferred pharmacy |

The network status of the patient's preferred pharmacy (rank 1) determines
`pharmacy_status` in patient access verification.

## Lifestyle risk (from `lifestyle` object)

| Field | Type | Meaning |
|-------|------|---------|
| `smoking_status` | string | Current / Former / Never |
| `alcohol_use` | string | Heavy / Moderate / Occasional / None |
| `exercise_frequency` | string or null | None / 1-2 / 3-4 / 5+ / null |
| `sleep_hours` | float or null | Average sleep hours |

## Clinical history (from `clinical_history` object)

| Field | Type | Meaning |
|-------|------|---------|
| `chronic_conditions` | string | Comma-separated condition names |
| `allergy_count` | integer | Number of known allergies |
| `medication_count` | integer | Number of current medications |
| `risk_flags` | string | Free text flags (non-empty means elevated risk) |
| `recent_hospitalization` | 0 or 1 | Hospitalized in recent window |

## Referral records

| Field | Type | Meaning |
|-------|------|---------|
| `icd10_code` | string | ICD-10-CM diagnosis code |
| `service_line` | string | orthopedics / pulmonary / cardiology / etc. |
| `urgency` | string | urgent / routine / admin |
| `auth_required` | 0 or 1 | Whether authorization is required |
| `auth_status` | string | approved / denied / pending / not_required |
| `records_received` | 0 or 1 | Whether medical records have been received |
| `imaging_received` | 0 or 1 | Whether imaging has been received |
| `appointment_scheduled` | 0 or 1 | Whether an appointment is already scheduled |
| `appointment_date` | string or null | Scheduled appointment date if any |
| `insurance_id` | string | Insurance identifier for this referral |
| `notes` | string | Includes flags like "possible duplicate" |

## Transfer records

| Field | Type | Meaning |
|-------|------|---------|
| `requested_start_date` | date | When the patient wants to start |
| `requested_end_date` | date | When the patient will leave |
| `chair_window` | string | morning / midday / evening |
| `days_requested` | string | e.g., "Mon/Wed/Fri" |
| `modality` | string | in_center_hemodialysis (only value seen) |

## Documents (from `documents` array on patient)

| Field | Type | Meaning |
|-------|------|---------|
| `doc_type` | string | Type code (see business rules for list) |
| `received_date` | date | When the document was received |
| `status` | string | current / stale / missing |
| `transfer_id` | string or null | Linked transfer if applicable |

## Chart artifacts (from `chart_artifacts` array)

| Field | Type | Meaning |
|-------|------|---------|
| `artifact_type` | string | vitals / labs / medications / active_problems / allergies / consent / demographics |
| `last_updated` | date or null | Last modification date |
| `status` | string | current / stale |

A patient's chart is considered "active" if they have chart_artifacts AND
the artifacts have current status. Missing artifacts are identified by
checking which expected artifact types are absent from the array.

## ICD metadata (from /icd/{code})

| Field | Type | Meaning |
|-------|------|---------|
| `chapter` | string | ICD-10-CM chapter range (e.g., "M00-M99") |
| `service_family` | string | Clinical service area |
| `laterality` | string or null | left / right / bilateral / null |

## Program candidates (from /programs/{code}/candidates)

| Field | Type | Meaning |
|-------|------|---------|
| `consent_status` | string | signed / declined / missing |
| `target_condition` | string | diabetes_hypertension / copd / cardiac / etc. |
| `adherence_score` | integer | 0-100, lower = worse adherence |
| `preferred_outreach` | string | portal / phone / email / sms |
| `source` | string | registry / payer_file / provider_panel |
