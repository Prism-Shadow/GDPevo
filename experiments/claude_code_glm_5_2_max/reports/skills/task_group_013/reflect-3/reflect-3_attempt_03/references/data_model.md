# Cedar Ridge Portal — Data Model

The portal is a relational store (a read-only SQL endpoint exposes it). Entities relate by a few
IDs: `patient_id`, `referral_id`, `transfer_id`, `insurance_id`, and `program_code`. Fetching a
patient detail typically returns most of the patient-centric tables joined for you; use the SQL
endpoint to reconcile across batches/tables.

## patients (hub)
`patient_id`, `first_name`, `last_name`, `dob`, `phone`, `email`, `language`, `address`,
`existing_chart` (0/1 — whether an active chart record exists), `preferred_contact`
(portal/phone/sms/email), `emergency_contact_present` (0/1).

## intake_rosters
`roster_id`, `patient_id`, `requested_service_date`, `service_line`, `source_note`. A roster pins the
service date + service line under which a new-patient access verification is performed. Pulled as part
of the patient detail (`rosters`).

## coverage (insurance)
`coverage_id`, `patient_id`, `payer`, `policy_number`, `group_number`, `effective_date`,
`termination_date`, `network_status`, `service_lines` (comma-separated), `status`
(active/expired/pending). One patient can have multiple rows; usually the relevant one is first.

## pbm (prescription benefit)
`pbm_id`, `patient_id`, `payer`, `policy_number`, `active` (0/1), `status`
(approved/rejected/pending), `formulary_status` (covered/not_found/review), `specialty_required` (0/1).
Match `policy_number` against the coverage policy to detect a mismatch.

## pharmacies / patient_pharmacy
`pharmacies`: `pharmacy_id`, `name`, `network_status` (in_network/out_of_network),
`address`, `phone`. `patient_pharmacy` links a patient to pharmacies with `preference_rank` (1 = preferred).

## lifestyle
`patient_id`, `smoking_status` (Current/Former/Never), `alcohol_use` (Heavy/Moderate/Occasional/None),
`exercise_frequency` (None/1-2/3-4 or null), `sleep_hours` (float).

## clinical_history
`patient_id`, `chronic_conditions` (comma-separated: cad, ckd, copd, diabetes, hypertension, asthma,
osteoarthritis, …), `medication_count`, `allergy_count`, `recent_hospitalization` (0/1),
`risk_flags` (e.g. `recent_ed_visit`, `complex_medication_reconciliation`, `fall_risk`, or empty),
`surgeries`.

## referrals
`referral_id`, `batch_id`, `service_line`, `patient_id`, `payer`, `insurance_id`,
`referring_physician`, `referring_practice`, `referring_phone`, `referring_fax`, `icd10_code`,
`diagnosis_description`, `referral_reason`, `urgency` (urgent/routine/admin), `records_received` (0/1),
`imaging_received` (0/1), `auth_required` (0/1), `auth_status` (approved/denied/pending/not_submitted),
`appointment_scheduled` (0/1), `appointment_date`, `assigned_physician`, `notes`, `date_received`.

Duplicate hints live in `notes` ("possible duplicate") and `assigned_physician`/`referring_practice`
(e.g. "duplicate faxed by second practice", "Duplicate … Associates"). Same `insurance_id` across
**different** patients is a shared-insurance anomaly; across the **same** patient it is a legitimate
duplicate.

## icd_codes
`code`, `description`, `chapter` (e.g. S00-T88, M00-M99, J00-J99, I00-I99, R00-R99),
`service_family` (orthopedics/pulmonary/cardiology/chronic_care/dialysis), `laterality`
(left/right/null). Compare `service_family` to a referral's `service_line` to flag a clinical-code
discrepancy. Note: a service family can legitimately span more than one chapter.

## documents
`document_id`, `patient_id`, `referral_id`, `transfer_id`, `doc_type`, `status` (final/draft),
`finalized` (0/1), `received_date`, `service_date`, `content_tag`
(transfer_packet/referral_packet), `notes`. Packet completeness and freshness derive from this table.

Required dialysis-transfer doc types include: allergy_list, face_sheet, flu_vaccine, hbsag,
hep_b_antibody_core, history_physical, insurance_proof, medication_list, monthly_labs,
physician_orders, pneumonia_vaccine, ppd_or_cxr, transportation, treatment_flowsheets,
vascular_access_report. **`transportation` is not a doc_type** — it is satisfied by the transfer's
`transportation` arrangement (null ⇒ missing). Freshness-limited types: hbsag, hep_b_antibody_core,
history_physical, monthly_labs, ppd_or_cxr.

## transfer_requests
`transfer_id`, `batch_id`, `patient_id`, `referring_facility`, `requested_start_date`,
`requested_end_date`, `modality`, `days_requested`, `chair_window`, `transportation`, `status_note`.

## facility_capacity
`location_id` (e.g. CRIC-MAIN, CRIC-NORTH), `date`, `modality` (in_center_hemodialysis),
`open_chairs`. Rows exist on a recurring schedule (e.g. Mon/Wed/Fri). A requested start date with
**no row** for the modality means 0 open chairs at that location; sum across locations for the date.

## chart_artifacts
`artifact_id`, `patient_id`, `artifact_type` (active_problems, vitals, labs, medications, consent,
demographics, care_plan, allergies, …), `status` (current/stale), `last_updated`, `value_summary`.

## program_candidates
`program_code`, `patient_id`, `candidate_date`, `source`, `consent_status` (signed/declined/missing),
`preferred_outreach` (phone/portal/sms/email), `adherence_score` (integer), `target_condition`
(e.g. diabetes_hypertension, copd). A `target_condition` that does not match the program's target is
a wrong-target-condition rejection; absence of the program's required diagnoses in the patient's
`clinical_history` is a missing-diagnosis rejection.
