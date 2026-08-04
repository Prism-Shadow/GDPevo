 # Cedar Ridge Data Model — Schema Reference

 Full DDL for the shared intake coordination database.

 ```sql
 CREATE TABLE patients (
     patient_id TEXT PRIMARY KEY,
     first_name TEXT NOT NULL,
     last_name TEXT NOT NULL,
     dob TEXT NOT NULL,
     phone TEXT,
     email TEXT,
     language TEXT NOT NULL,
     address TEXT,
     existing_chart INTEGER NOT NULL,
     preferred_contact TEXT,
     emergency_contact_present INTEGER NOT NULL
 );

 CREATE TABLE coverage (
     coverage_id INTEGER PRIMARY KEY AUTOINCREMENT,
     patient_id TEXT NOT NULL,
     payer TEXT NOT NULL,
     policy_number TEXT,
     group_number TEXT,
     effective_date TEXT,
     termination_date TEXT,
     network_status TEXT NOT NULL,
     service_lines TEXT NOT NULL,
     status TEXT NOT NULL
 );

 CREATE TABLE pbm (
     pbm_id INTEGER PRIMARY KEY AUTOINCREMENT,
     patient_id TEXT NOT NULL,
     payer TEXT NOT NULL,
     policy_number TEXT,
     active INTEGER NOT NULL,
     formulary_status TEXT NOT NULL,
     specialty_required INTEGER NOT NULL,
     status TEXT NOT NULL
 );

 CREATE TABLE patient_pharmacy (
     patient_id TEXT NOT NULL,
     pharmacy_id TEXT NOT NULL,
     preference_rank INTEGER NOT NULL,
     PRIMARY KEY (patient_id, pharmacy_id)
 );

 CREATE TABLE pharmacies (
     pharmacy_id TEXT PRIMARY KEY,
     name TEXT NOT NULL,
     address TEXT NOT NULL,
     phone TEXT,
     network_status TEXT NOT NULL
 );

 CREATE TABLE lifestyle (
     patient_id TEXT PRIMARY KEY,
     smoking_status TEXT,
     alcohol_use TEXT,
     exercise_frequency TEXT,
     sleep_hours REAL
 );

 CREATE TABLE clinical_history (
     patient_id TEXT PRIMARY KEY,
     chronic_conditions TEXT,
     surgeries TEXT,
     medication_count INTEGER NOT NULL,
     allergy_count INTEGER NOT NULL,
     recent_hospitalization INTEGER NOT NULL,
     risk_flags TEXT
 );

 CREATE TABLE referrals (
     referral_id TEXT PRIMARY KEY,
     batch_id TEXT NOT NULL,
     service_line TEXT NOT NULL,
     date_received TEXT NOT NULL,
     patient_id TEXT NOT NULL,
     payer TEXT,
     insurance_id TEXT,
     referring_physician TEXT,
     referring_practice TEXT,
     referring_phone TEXT,
     referring_fax TEXT,
     icd10_code TEXT,
     diagnosis_description TEXT,
     referral_reason TEXT,
     urgency TEXT,
     records_received INTEGER NOT NULL,
     imaging_received INTEGER NOT NULL,
     auth_required INTEGER NOT NULL,
     auth_status TEXT NOT NULL,
     appointment_scheduled INTEGER NOT NULL,
     appointment_date TEXT,
     assigned_physician TEXT,
     notes TEXT
 );

 CREATE TABLE transfer_requests (
     transfer_id TEXT PRIMARY KEY,
     batch_id TEXT NOT NULL,
     patient_id TEXT NOT NULL,
     referring_facility TEXT NOT NULL,
     requested_start_date TEXT NOT NULL,
     requested_end_date TEXT,
     modality TEXT NOT NULL,
     days_requested TEXT,
     chair_window TEXT,
     transportation TEXT,
     status_note TEXT
 );

 CREATE TABLE documents (
     document_id TEXT PRIMARY KEY,
     patient_id TEXT NOT NULL,
     referral_id TEXT,
     transfer_id TEXT,
     doc_type TEXT NOT NULL,
     status TEXT NOT NULL,
     finalized INTEGER NOT NULL,
     received_date TEXT,
     service_date TEXT,
     content_tag TEXT,
     notes TEXT
 );

 CREATE TABLE icd_codes (
     code TEXT PRIMARY KEY,
     description TEXT NOT NULL,
     chapter TEXT NOT NULL,
     service_family TEXT NOT NULL,
     laterality TEXT
 );

 CREATE TABLE intake_rosters (
     roster_id TEXT NOT NULL,
     patient_id TEXT NOT NULL,
     requested_service_date TEXT NOT NULL,
     service_line TEXT NOT NULL,
     source_note TEXT,
     PRIMARY KEY (roster_id, patient_id)
 );

 CREATE TABLE facility_capacity (
     location_id TEXT NOT NULL,
     date TEXT NOT NULL,
     modality TEXT NOT NULL,
     open_chairs INTEGER NOT NULL,
     PRIMARY KEY (location_id, date, modality)
 );

 CREATE TABLE program_candidates (
     program_code TEXT NOT NULL,
     patient_id TEXT NOT NULL,
     candidate_date TEXT NOT NULL,
     source TEXT NOT NULL,
     consent_status TEXT NOT NULL,
     preferred_outreach TEXT,
     adherence_score INTEGER,
     target_condition TEXT NOT NULL,
     PRIMARY KEY (program_code, patient_id)
 );

 CREATE TABLE chart_artifacts (
     artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
     patient_id TEXT NOT NULL,
     artifact_type TEXT NOT NULL,
     status TEXT NOT NULL,
     last_updated TEXT,
     value_summary TEXT
 );
 ```

 ## Key relationships

 - `patients.patient_id` → `coverage.patient_id`, `pbm.patient_id`, `lifestyle.patient_id`, `clinical_history.patient_id`, `patient_pharmacy.patient_id`
 - `patient_pharmacy.pharmacy_id` → `pharmacies.pharmacy_id`
 - `referrals.patient_id` → `patients.patient_id`; `referrals.icd10_code` → `icd_codes.code`
 - `transfer_requests.patient_id` → `patients.patient_id`
 - `documents.referral_id` → `referrals.referral_id`; `documents.transfer_id` → `transfer_requests.transfer_id`
 - `program_candidates.patient_id` → `patients.patient_id`
 - `chart_artifacts.patient_id` → `patients.patient_id`
 - `intake_rosters.roster_id` + `intake_rosters.patient_id` is the composite key
 - `facility_capacity` composite key: `(location_id, date, modality)`

 ## Common query patterns

 Pull all data for a batch of patients:
 ```sql
 SELECT * FROM patients WHERE patient_id IN ('P001','P002',...);
 SELECT * FROM coverage WHERE patient_id IN (...);
 SELECT * FROM pbm WHERE patient_id IN (...);
 SELECT * FROM lifestyle WHERE patient_id IN (...);
 SELECT * FROM clinical_history WHERE patient_id IN (...);
 ```

 Pull referrals for a batch:
 ```sql
 SELECT * FROM referrals WHERE batch_id = 'ORTHO-JUN-01' ORDER BY referral_id;
 ```

 Pull documents for referrals:
 ```sql
 SELECT * FROM documents WHERE referral_id IN (SELECT referral_id FROM referrals WHERE batch_id = '...') ORDER BY referral_id, doc_type;
 ```

 Check ICD metadata:
 ```sql
 SELECT * FROM icd_codes WHERE code IN ('J44.9','I25.10',...);
 ```

 Check capacity for specific dates:
 ```sql
 SELECT date, SUM(open_chairs) AS total FROM facility_capacity WHERE modality = 'in_center_hemodialysis' AND date IN (...) GROUP BY date;
 ```
