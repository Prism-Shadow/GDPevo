# Cedar Ridge Data Model Reference

## Table Schemas

### patients
```
patient_id TEXT, first_name TEXT, last_name TEXT, dob TEXT, address TEXT,
phone TEXT, email TEXT, language TEXT, preferred_contact TEXT,
emergency_contact_present INTEGER, existing_chart INTEGER
```

### coverage
```
coverage_id INTEGER, patient_id TEXT, payer TEXT, policy_number TEXT,
group_number TEXT, effective_date TEXT, termination_date TEXT,
network_status TEXT, service_lines TEXT, status TEXT
```
- `status`: active, expired, pending
- `service_lines`: comma-separated (e.g., "primary_care,dialysis,cardiology")

### pbm
```
pbm_id INTEGER, patient_id TEXT, payer TEXT, policy_number TEXT,
active INTEGER, formulary_status TEXT, specialty_required INTEGER, status TEXT
```
- `formulary_status`: covered, review, not_found
- `status`: approved, pending, rejected
- `active`: 0 or 1

### patient_pharmacy
```
patient_id TEXT, pharmacy_id TEXT, preference_rank INTEGER
```

### pharmacies
```
pharmacy_id TEXT, name TEXT, address TEXT, phone TEXT, network_status TEXT
```
- `network_status`: in_network, out_of_network

### lifestyle
```
patient_id TEXT, smoking_status TEXT, alcohol_use TEXT,
exercise_frequency TEXT, sleep_hours REAL
```
- `smoking_status`: Current, Former, Never
- `alcohol_use`: Heavy, Moderate, Occasional, None
- `exercise_frequency`: None, 1-2, 3-4, 5+ (or null)

### clinical_history
```
patient_id TEXT, chronic_conditions TEXT, surgeries TEXT,
medication_count INTEGER, allergy_count INTEGER,
recent_hospitalization INTEGER, risk_flags TEXT
```
- `chronic_conditions`: comma-separated condition names
- `recent_hospitalization`: 0 or 1
- `risk_flags`: comma-separated flags (e.g., "recent_ed_visit", "complex_medication_reconciliation")

### chart_artifacts
```
artifact_id INTEGER, patient_id TEXT, artifact_type TEXT,
status TEXT, last_updated TEXT, value_summary TEXT
```
- `artifact_type`: active_problems, vitals, labs, medications, consent, demographics, allergies, care_plan
- `status`: current, stale

### intake_rosters
```
roster_id TEXT, patient_id TEXT, requested_service_date TEXT,
service_line TEXT, source_note TEXT
```

### referrals
```
referral_id TEXT, batch_id TEXT, service_line TEXT, date_received TEXT,
patient_id TEXT, payer TEXT, insurance_id TEXT,
referring_physician TEXT, referring_practice TEXT,
referring_phone TEXT, referring_fax TEXT,
icd10_code TEXT, diagnosis_description TEXT, referral_reason TEXT,
urgency TEXT, records_received INTEGER, imaging_received INTEGER,
auth_required INTEGER, auth_status TEXT,
appointment_scheduled INTEGER, appointment_date TEXT,
assigned_physician TEXT, notes TEXT
```
- `urgency`: urgent, routine, admin
- `auth_status`: approved, denied, pending, not_required
- `records_received`, `imaging_received`, `appointment_scheduled`: 0 or 1

### transfer_requests
```
transfer_id TEXT, batch_id TEXT, patient_id TEXT,
referring_facility TEXT, requested_start_date TEXT,
requested_end_date TEXT, modality TEXT, days_requested TEXT,
chair_window TEXT, transportation TEXT, status_note TEXT
```
- `modality`: in_center_hemodialysis (and potentially others)
- `transportation`: family, ride_share, medical_transport, or null

### documents
```
document_id TEXT, patient_id TEXT, referral_id TEXT, transfer_id TEXT,
doc_type TEXT, status TEXT, finalized INTEGER, received_date TEXT,
service_date TEXT, content_tag TEXT, notes TEXT
```
- `finalized`: 0 (draft) or 1 (final)
- `content_tag`: transfer_packet (and potentially others)

### facility_capacity
```
location_id TEXT, date TEXT, modality TEXT, open_chairs INTEGER
```

### icd_codes
```
code TEXT, description TEXT, chapter TEXT, service_family TEXT, laterality TEXT
```
- `service_family`: orthopedics, pulmonary, cardiology, neurology, etc.
- `laterality`: left, right, bilateral, or null

### program_candidates
```
program_code TEXT, patient_id TEXT, candidate_date TEXT, source TEXT,
consent_status TEXT, preferred_outreach TEXT,
adherence_score INTEGER, target_condition TEXT
```
- `consent_status`: signed, declined, missing
- `target_condition`: condition code (e.g., "diabetes_hypertension")
