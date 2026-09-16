# Cedar Ridge Portal Schema Reference

## SQL Tables

The read-only SQL endpoint (`POST /query` with `{"sql": "SELECT ..."}`) exposes these tables.

### patients
| Column | Type | Notes |
|--------|------|-------|
| patient_id | TEXT | Primary key, e.g. P001 |
| first_name | TEXT | |
| last_name | TEXT | |
| dob | TEXT | YYYY-MM-DD |
| phone | TEXT | nullable |
| email | TEXT | nullable |
| language | TEXT | |
| address | TEXT | nullable |
| existing_chart | INTEGER | 0=no chart, 1=has chart |
| preferred_contact | TEXT | phone, email, sms, portal |
| emergency_contact_present | INTEGER | 0 or 1 |

### coverage
| Column | Type | Notes |
|--------|------|-------|
| coverage_id | INTEGER | PK |
| patient_id | TEXT | FK to patients |
| payer | TEXT | |
| policy_number | TEXT | |
| group_number | TEXT | |
| effective_date | TEXT | YYYY-MM-DD |
| termination_date | TEXT | YYYY-MM-DD or null |
| network_status | TEXT | e.g. in_network |
| service_lines | TEXT | Comma-separated: primary_care,orthopedics,pulmonary,dialysis,etc. |
| status | TEXT | active, expired, pending |

### pbm (Pharmacy Benefit Manager)
| Column | Type | Notes |
|--------|------|-------|
| pbm_id | INTEGER | PK |
| patient_id | TEXT | FK to patients |
| payer | TEXT | |
| policy_number | TEXT | Must match coverage.policy_number for same patient |
| active | INTEGER | 0 or 1 |
| formulary_status | TEXT | covered, not_found, review |
| specialty_required | INTEGER | 0 or 1 |
| status | TEXT | approved, rejected, pending |

### patient_pharmacy
| Column | Type | Notes |
|--------|------|-------|
| patient_id | TEXT | FK |
| pharmacy_id | TEXT | FK to pharmacies |
| preference_rank | INTEGER | 1 = preferred pharmacy |

### pharmacies
| Column | Type | Notes |
|--------|------|-------|
| pharmacy_id | TEXT | e.g. RX001 |
| name | TEXT | |
| address | TEXT | |
| phone | TEXT | nullable |
| network_status | TEXT | in_network, out_of_network |

### lifestyle
| Column | Type | Notes |
|--------|------|-------|
| patient_id | TEXT | FK |
| smoking_status | TEXT | Current, Former, Never |
| alcohol_use | TEXT | None, Occasional, Moderate, Heavy |
| exercise_frequency | TEXT | None, 1-2, 3-4, 5+ (nullable) |
| sleep_hours | REAL | hours per night |

### clinical_history
| Column | Type | Notes |
|--------|------|-------|
| patient_id | TEXT | FK |
| chronic_conditions | TEXT | Comma-separated |
| surgeries | TEXT | |
| medication_count | INTEGER | |
| allergy_count | INTEGER | |
| recent_hospitalization | INTEGER | 0 or 1 |
| risk_flags | TEXT | Empty string or risk notes |

### chart_artifacts
| Column | Type | Notes |
|--------|------|-------|
| artifact_id | INTEGER | PK |
| patient_id | TEXT | FK |
| artifact_type | TEXT | active_problems, vitals, labs, medications, consent, demographics, allergies, care_plan |
| status | TEXT | current, stale |
| last_updated | TEXT | YYYY-MM-DD |

### referrals
| Column | Type | Notes |
|--------|------|-------|
| referral_id | TEXT | e.g. REF0001 |
| batch_id | TEXT | |
| patient_id | TEXT | FK |
| service_line | TEXT | orthopedics, pulmonary, cardiology, neurology, dermatology |
| icd10_code | TEXT | |
| diagnosis_description | TEXT | |
| referral_reason | TEXT | pain evaluation, consult, previsit clearance, etc. |
| urgency | TEXT | urgent, routine, admin |
| auth_required | INTEGER | 0 or 1 |
| auth_status | TEXT | approved, denied, pending, not_required, not_submitted |
| records_received | INTEGER | 0 or 1 |
| imaging_received | INTEGER | 0 or 1 |
| appointment_scheduled | INTEGER | 0 or 1 |
| appointment_date | TEXT | YYYY-MM-DD or null |
| insurance_id | TEXT | |
| payer | TEXT | |
| assigned_physician | TEXT | May contain duplicate hints |
| referring_physician | TEXT | |
| referring_practice | TEXT | |
| referring_phone | TEXT | nullable |
| referring_fax | TEXT | |
| notes | TEXT | batch intake, possible duplicate, etc. |
| date_received | TEXT | YYYY-MM-DD |

### transfer_requests
| Column | Type | Notes |
|--------|------|-------|
| transfer_id | TEXT | e.g. TR0001 |
| batch_id | TEXT | |
| patient_id | TEXT | FK |
| referring_facility | TEXT | |
| requested_start_date | TEXT | YYYY-MM-DD |
| requested_end_date | TEXT | YYYY-MM-DD |
| modality | TEXT | in_center_hemodialysis |
| days_requested | TEXT | e.g. Mon/Wed/Fri |
| chair_window | TEXT | morning, midday, evening |
| transportation | TEXT | family, ride_share, medical_transport, or null |
| status_note | TEXT | |

### documents
| Column | Type | Notes |
|--------|------|-------|
| document_id | TEXT | e.g. DOC00001 |
| patient_id | TEXT | FK |
| referral_id | TEXT | nullable FK |
| transfer_id | TEXT | nullable FK |
| doc_type | TEXT | See transfer document types below |
| status | TEXT | final, draft |
| finalized | INTEGER | 0=draft, 1=final |
| received_date | TEXT | YYYY-MM-DD |
| service_date | TEXT | nullable |
| content_tag | TEXT | transfer_packet, referral_record, etc. |
| notes | TEXT | |

### facility_capacity
| Column | Type | Notes |
|--------|------|-------|
| location_id | TEXT | CRIC-MAIN, CRIC-NORTH |
| date | TEXT | YYYY-MM-DD |
| modality | TEXT | in_center_hemodialysis |
| open_chairs | INTEGER | Open chairs at this location on this date |

### icd_codes
| Column | Type | Notes |
|--------|------|-------|
| code | TEXT | ICD-10 code |
| description | TEXT | |
| chapter | TEXT | e.g. M00-M99, J00-J99, S00-T88, I00-I99, R00-R99 |
| service_family | TEXT | orthopedics, pulmonary, cardiology, etc. |
| laterality | TEXT | left, right, bilateral, or null |

### intake_rosters
| Column | Type | Notes |
|--------|------|-------|
| roster_id | TEXT | |
| patient_id | TEXT | FK |
| requested_service_date | TEXT | YYYY-MM-DD |
| service_line | TEXT | |
| source_note | TEXT | |

### program_candidates
| Column | Type | Notes |
|--------|------|-------|
| patient_id | TEXT | FK |
| program_code | TEXT | |
| target_condition | TEXT | e.g. diabetes_hypertension, copd |
| consent_status | TEXT | signed, declined, missing |
| adherence_score | INTEGER | 0-100 |
| source | TEXT | registry, payer_file, provider_panel |
| candidate_date | TEXT | YYYY-MM-DD |
| preferred_outreach | TEXT | phone, portal, sms, email |
| existing_chart | INTEGER | 0 or 1 |
| first_name | TEXT | |
| last_name | TEXT | |
| dob | TEXT | |
| email | TEXT | nullable |
| phone | TEXT | nullable |

## REST Response Shapes

### GET /patients
Returns `{"count": N, "patients": [...]}`. Each patient has all columns from the patients table.

### GET /patients/{patient_id}
Returns a single patient object (no count wrapper).

### GET /referrals?batch_id=...
Returns `{"count": N, "referrals": [...]}`. Each referral has all columns from the referrals table.

### GET /transfers?batch_id=...
Returns `{"count": N, "transfers": [...]}`.

### GET /documents
Returns `{"count": N, "documents": [...]}`. No built-in filtering; use SQL for targeted queries.

### GET /chart/{patient_id}
Returns `{"patient": {...}, "clinical_history": {...}, "active_problems": [...], "chart_artifacts": [...], "recent_vitals_labs": [...], "meds_allergies": [...]}`.

### GET /programs/{program_code}/candidates
Returns `{"program_code": "...", "count": N, "candidates": [...]}`.

### GET /icd/{code}
Returns `{"icd": {"code": "...", "description": "...", "chapter": "...", "service_family": "...", "laterality": "..."}}`.

### GET /pharmacies
Returns `{"count": N, "pharmacies": [...]}`.

## Key Relationships

- **referrals.patient_id -> patients.patient_id**
- **referrals.icd10_code -> icd_codes.code** (for chapter, service_family, laterality)
- **transfer_requests.patient_id -> patients.patient_id**
- **coverage.patient_id -> patients.patient_id**
- **pbm.patient_id -> patients.patient_id** (also pbm.policy_number should match coverage.policy_number)
- **patient_pharmacy.patient_id -> patients.patient_id**, pharmacy_id -> pharmacies.pharmacy_id
- **lifestyle.patient_id -> patients.patient_id**
- **clinical_history.patient_id -> patients.patient_id**
- **chart_artifacts.patient_id -> patients.patient_id**
- **documents.patient_id -> patients.patient_id**, also documents.referral_id or documents.transfer_id
- **facility_capacity**: Sum open_chairs across all locations for a given date to get total capacity
- **program_candidates.patient_id -> patients.patient_id**

## ICD Chapter to Service Line Mapping

| Service Line | Expected ICD Chapter(s) |
|-------------|------------------------|
| orthopedics | M00-M99 |
| pulmonary | J00-J99 |
| cardiology | I00-I99 |
| neurology | G00-G99 |
| dermatology | L00-L99 |
| primary_care | Any (no single expected) |
| dialysis | N00-N99 (renal) |

Chapters S00-T88 (injury/trauma) and R00-R99 (symptoms/signs) are not organ-system-specific. When a referral's ICD code falls into a chapter that does not match the referral's service_line, flag as `icd_chapter_mismatch`.

## Transfer Document Types

The 15 required document types for dialysis transfer packets, listed here for completeness checking:

1. allergy_list
2. face_sheet
3. flu_vaccine
4. hbsag
5. hep_b_antibody_core
6. history_physical
7. insurance_proof
8. medication_list
9. monthly_labs
10. physician_orders
11. pneumonia_vaccine
12. ppd_or_cxr
13. transportation
14. treatment_flowsheets
15. vascular_access_report

Of these, five have freshness limits (staleness checks): hbsag (30 days), hep_b_antibody_core (30 days), history_physical (365 days), monthly_labs (30 days), ppd_or_cxr (30 days).
