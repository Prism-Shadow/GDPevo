# Cedar Ridge Data Model

## SQL Schema

All tables are accessible via `POST /query` with `{"sql": "..."}`. Only SELECT is allowed.

### patients
| Column | Type | Notes |
|---|---|---|
| patient_id | TEXT | Primary key, format Pnnn |
| first_name | TEXT | |
| last_name | TEXT | |
| dob | TEXT | YYYY-MM-DD |
| phone | TEXT | Nullable |
| email | TEXT | Nullable |
| language | TEXT | |
| address | TEXT | Nullable; null = missing address |
| existing_chart | INTEGER | 0/1 boolean |
| preferred_contact | TEXT | portal, email, phone, sms |
| emergency_contact_present | INTEGER | 0/1 boolean |

### coverage (insurance)
| Column | Type | Notes |
|---|---|---|
| coverage_id | INTEGER | |
| patient_id | TEXT | FK to patients |
| payer | TEXT | BlueCross, Medicare, Aetna, etc. |
| policy_number | TEXT | |
| group_number | TEXT | |
| effective_date | TEXT | YYYY-MM-DD |
| termination_date | TEXT | YYYY-MM-DD |
| network_status | TEXT | in_network, out_of_network |
| service_lines | TEXT | Comma-separated: e.g. "primary_care,cardiology" |
| status | TEXT | active, expired, pending |

### pbm (prescription benefit)
| Column | Type | Notes |
|---|---|---|
| pbm_id | INTEGER | |
| patient_id | TEXT | FK to patients |
| payer | TEXT | |
| policy_number | TEXT | |
| active | INTEGER | 0/1 boolean |
| formulary_status | TEXT | covered, not_covered, restricted |
| specialty_required | INTEGER | 0/1 boolean |
| status | TEXT | approved, denied, missing, policy_mismatch |

### patient_pharmacy
| Column | Type | Notes |
|---|---|---|
| patient_id | TEXT | FK |
| pharmacy_id | TEXT | FK to pharmacies, format RXnnn |
| preference_rank | INTEGER | 1 = primary preferred pharmacy |

### pharmacies
| Column | Type | Notes |
|---|---|---|
| pharmacy_id | TEXT | Primary key, format RXnnn |
| name | TEXT | |
| address | TEXT | |
| phone | TEXT | |
| network_status | TEXT | in_network, out_of_network |

### lifestyle
| Column | Type | Notes |
|---|---|---|
| patient_id | TEXT | FK |
| smoking_status | TEXT | Current, Former, Never |
| alcohol_use | TEXT | None, Light, Moderate, Heavy |
| exercise_frequency | TEXT | None, Light, Moderate, Regular |
| sleep_hours | REAL | |

### intake_rosters
| Column | Type | Notes |
|---|---|---|
| roster_id | TEXT | e.g. NPI-JUN-01 |
| patient_id | TEXT | FK |
| requested_service_date | TEXT | YYYY-MM-DD |
| service_line | TEXT | primary_care, cardiology, orthopedics, etc. |
| source_note | TEXT | |

### referrals
| Column | Type | Notes |
|---|---|---|
| referral_id | TEXT | Primary key, format REFnnnn |
| batch_id | TEXT | e.g. ORTHO-JUN-01 |
| service_line | TEXT | orthopedics, pulmonary, cardiology, etc. |
| date_received | TEXT | YYYY-MM-DD |
| patient_id | TEXT | FK |
| payer | TEXT | |
| insurance_id | TEXT | |
| referring_physician | TEXT | |
| referring_practice | TEXT | |
| referring_phone | TEXT | Nullable |
| referring_fax | TEXT | Nullable |
| icd10_code | TEXT | |
| diagnosis_description | TEXT | |
| referral_reason | TEXT | pain evaluation, consult, etc. |
| urgency | TEXT | urgent, routine, admin |
| records_received | INTEGER | 0/1 |
| imaging_received | INTEGER | 0/1 |
| auth_required | INTEGER | 0/1 |
| auth_status | TEXT | approved, denied, pending, not_required, not_submitted |
| appointment_scheduled | INTEGER | 0/1 |
| appointment_date | TEXT | YYYY-MM-DD, nullable |
| assigned_physician | TEXT | |
| notes | TEXT | |

### icd_codes
| Column | Type | Notes |
|---|---|---|
| code | TEXT | ICD-10 code |
| description | TEXT | |
| chapter | TEXT | e.g. S00-T88, M00-M99, I00-I99, J00-J99 |
| service_family | TEXT | orthopedics, pulmonary, cardiology, etc. |
| laterality | TEXT | left, right, bilateral, null |

### documents
| Column | Type | Notes |
|---|---|---|
| document_id | TEXT | Primary key, format DOCnnnnn |
| patient_id | TEXT | FK |
| referral_id | TEXT | FK, nullable |
| transfer_id | TEXT | FK, nullable |
| doc_type | TEXT | See doc type values |
| status | TEXT | final, draft, received |
| finalized | INTEGER | 0/1 |
| received_date | TEXT | YYYY-MM-DD |
| service_date | TEXT | YYYY-MM-DD, nullable |
| content_tag | TEXT | transfer_packet, chart_document, referral_document |
| notes | TEXT | |

### transfer_requests
| Column | Type | Notes |
|---|---|---|
| transfer_id | TEXT | Primary key, format TRnnnn |
| batch_id | TEXT | e.g. DIAL-WINTER-01 |
| patient_id | TEXT | FK |
| referring_facility | TEXT | |
| requested_start_date | TEXT | YYYY-MM-DD |
| requested_end_date | TEXT | YYYY-MM-DD |
| modality | TEXT | in_center_hemodialysis, etc. |
| days_requested | TEXT | e.g. "Mon/Wed/Fri" |
| chair_window | TEXT | morning, midday, evening |
| transportation | TEXT | family, ride_share, medical_transport, null |
| status_note | TEXT | |

### facility_capacity
| Column | Type | Notes |
|---|---|---|
| location_id | TEXT | CRIC-MAIN, etc. |
| date | TEXT | YYYY-MM-DD |
| modality | TEXT | |
| open_chairs | INTEGER | |

### program_candidates
| Column | Type | Notes |
|---|---|---|
| program_code | TEXT | e.g. DMHTN-2026A |
| patient_id | TEXT | FK |
| candidate_date | TEXT | YYYY-MM-DD |
| source | TEXT | registry, payer_file, provider_panel |
| consent_status | TEXT | signed, declined, missing |
| preferred_outreach | TEXT | portal, phone, email, sms |
| adherence_score | INTEGER | 0-100 |
| target_condition | TEXT | diabetes_hypertension, copd, etc. |

### chart_artifacts
| Column | Type | Notes |
|---|---|---|
| artifact_id | INTEGER | |
| patient_id | TEXT | FK |
| artifact_type | TEXT | vitals, labs, medications, allergies, active_problems, consent, demographics |
| status | TEXT | current, stale, missing |
| last_updated | TEXT | YYYY-MM-DD |
| value_summary | TEXT | |

### clinical_history
| Column | Type | Notes |
|---|---|---|
| patient_id | TEXT | FK |
| chronic_conditions | TEXT | Comma-separated |
| surgeries | TEXT | |
| medication_count | INTEGER | |
| allergy_count | INTEGER | |
| recent_hospitalization | INTEGER | 0/1 |
| risk_flags | TEXT | |

## Join Patterns

### Patient with coverage, PBM, pharmacy
```sql
SELECT p.*, c.*, pb.*, pp.*, ph.*, l.*
FROM patients p
LEFT JOIN coverage c ON p.patient_id = c.patient_id
LEFT JOIN pbm pb ON p.patient_id = pb.patient_id
LEFT JOIN patient_pharmacy pp ON p.patient_id = pp.patient_id AND pp.preference_rank = 1
LEFT JOIN pharmacies ph ON pp.pharmacy_id = ph.pharmacy_id
LEFT JOIN lifestyle l ON p.patient_id = l.patient_id
WHERE p.patient_id IN (...)
```

### Referral with ICD metadata
```sql
SELECT r.*, i.chapter, i.service_family as icd_service_family, i.laterality
FROM referrals r
JOIN icd_codes i ON r.icd10_code = i.code
WHERE r.batch_id = '...'
ORDER BY r.referral_id
```

### Transfer with documents and capacity
```sql
SELECT t.*, d.doc_type, d.received_date, d.status, d.finalized
FROM transfer_requests t
LEFT JOIN documents d ON t.transfer_id = d.transfer_id
WHERE t.batch_id = '...'
ORDER BY t.transfer_id, d.doc_type
```

### Program candidate with chart data
```sql
SELECT pc.*, cl.*, ca.artifact_type, ca.status as artifact_status, ca.last_updated
FROM program_candidates pc
LEFT JOIN clinical_history cl ON pc.patient_id = cl.patient_id
LEFT JOIN chart_artifacts ca ON pc.patient_id = ca.patient_id
WHERE pc.program_code = '...'
ORDER BY pc.patient_id
```
