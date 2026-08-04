 # Cedar Ridge Intake Coordination Skill

 ## Overview

 This skill covers healthcare intake coordination tasks using the Cedar Ridge Intake Coordination Portal. The portal provides read-only access to patient records, referrals, transfers, documents, insurance coverage, pharmacy networks, facility capacity, ICD code metadata, program candidates, and a SQL query endpoint for data reconciliation.

 The tasks fall into five categories: new-patient access verification, referral readiness audits, dialysis transfer packet review, chronic-care enrollment panels, and referral-to-chart activation workflows. All answers must follow the provided JSON answer template exactly, using only controlled vocabulary values.

 ## Core Workflow

 1. Read the task prompt and the answer template JSON to understand required fields and controlled values.
 2. Explore the environment: query the base URL, list available endpoints, and use SQL to inspect table schemas.
 3. Pull all relevant data from the portal using GET endpoints and SQL queries.
 4. Cross-reference records across tables (patients, coverage, PBM, pharmacies, documents, chart artifacts, clinical history, ICD codes, facility capacity).
 5. Construct the JSON answer following the template ordering, controlled values, and normalization rules.

 ## Data Sources and Key Tables

 Use the SQL endpoint (`POST /query`) to explore and query these tables:

 - `intake_rosters` — maps roster_id to patient_id, requested_service_date, service_line
 - `patients` — demographics, contact info, existing_chart flag, emergency_contact_present, preferred_contact
 - `coverage` — insurance policy details: status (active/pending/expired), service_lines (comma-separated), network_status, payer, policy_number
 - `pbm` — prescription benefit manager: active flag, formulary_status, status (approved/rejected/pending), policy_number
 - `patient_pharmacy` — maps patient to pharmacy_id with preference_rank
 - `pharmacies` — pharmacy network_status (in_network/out_of_network)
 - `lifestyle` — smoking_status, alcohol_use, exercise_frequency, sleep_hours
 - `referrals` — referral records with batch_id, patient_id, icd10_code, diagnosis_description, records_received, imaging_received, auth_required, auth_status, appointment_scheduled, insurance_id, urgency, notes
 - `transfer_requests` — transfer records with batch_id, patient_id, requested_start_date, modality, transportation
 - `documents` — document records linked by transfer_id or referral_id, with doc_type, finalized flag, received_date, status
 - `facility_capacity` — open_chairs by date, location_id, modality
 - `icd_codes` — ICD-10 metadata: code, description, chapter, service_family, laterality
 - `program_candidates` — program enrollment candidates: consent_status, target_condition, adherence_score, preferred_outreach
 - `chart_artifacts` — chart components: artifact_type, status (current/stale), last_updated
 - `clinical_history` — chronic_conditions, recent_hospitalization, risk_flags (e.g., recent_ed_visit), medication_count

 ## Data Interpretation Rules

 ### Insurance Coverage
 - **valid**: coverage status is "active", network_status is "in_network", and the requested service_line appears in the comma-separated service_lines field.
 - **invalid**: coverage is expired (status="expired" with termination_date before service date), pending (status="pending"), or the service_line is not listed in service_lines.
 - **missing**: no coverage record exists for the patient.

 ### Prescription Benefit (PBM)
 - **valid**: PBM record exists with active=1 and status="approved". The PBM policy_number should match the coverage policy_number.
 - **invalid**: PBM is inactive (active=0), rejected (status="rejected"), or there is a policy number mismatch between PBM and coverage.
 - **missing**: no PBM record exists.

 ### Pharmacy Network
 - Check the patient's preferred pharmacy (lowest preference_rank in patient_pharmacy) against the pharmacies table.
 - **in_network**: pharmacy network_status is "in_network".
 - **out_of_network**: pharmacy network_status is "out_of_network".
 - **unknown**: no pharmacy record or network_status is null.

 ### Document Completeness
 - A document is considered present only if it exists AND is finalized (finalized=1, status="final").
 - Draft documents (finalized=0) count as missing — they are not valid for the packet.
 - Compare the set of required document types against what is present and finalized.
 - For transfers, the required documents are the complete set listed in the answer template's allowed_values for missing_required_documents.

 ### Document Freshness (Staleness)
 - Compare document received_date to a reference date (typically the requested service start date).
 - Only certain document types have freshness limits (e.g., monthly_labs: 90 days, hbsag: 365 days, history_physical: 365 days, ppd_or_cxr: 365 days, hep_b_antibody_core: 365 days).
 - A document is stale if its age in days exceeds its freshness limit.

 ### Capacity Assessment
 - Query facility_capacity for the requested date and modality.
 - Sum open_chairs across all locations for that date.
 - If no capacity records exist for a date, treat capacity as unavailable with 0 open chairs.

 ### ICD Code Verification
 - Look up each referral's icd10_code in the icd_codes table.
 - The code's service_family must match the referral's service_line. A mismatch indicates a clinical code discrepancy (wrong service family).
 - The code's chapter indicates the ICD chapter. Compare observed chapter against the expected chapter for the service line.
 - If laterality is specified in the ICD code but not reflected in the diagnosis_description, flag a laterality mismatch.
 - If the diagnosis_description is generic (e.g., "specialty consultation") and does not describe the specific ICD condition, flag a narrative mismatch.

 ### Duplicate Detection
 - Two referrals are duplicates if they share the same patient_id and the same icd10_code (or same clinical reason) within the same batch.
 - One referral is typically the primary (earlier referral_id or first received); the other should be consolidated.
 - The duplicate group's recommendation is "consolidate_to_primary" unless there is a clinical reason to keep both.

 ### Shared Insurance Anomalies
 - When two different patients share the same insurance_id in the referrals table, this is a shared insurance anomaly.
 - Disposition is "verify_distinct_patient_policy_id" (different patients should have distinct insurance identifiers).

 ### Chart Artifacts
 - Required chart artifacts for enrollment/activation typically include: active_problems, vitals, labs, medications, consent.
 - An artifact is missing if no record exists in chart_artifacts for that patient and artifact_type.
 - An artifact with status="stale" indicates outdated data that needs refresh.
 - The existing_chart flag on the patient record indicates whether a chart record exists at all.

 ### Program Eligibility (DMHTN Example)
 - The program targets a specific condition (e.g., "diabetes_hypertension"). Check the candidate's target_condition.
 - Also verify the patient's chronic_conditions from clinical_history contain the relevant diagnoses.
 - Consent status from program_candidates: "signed" = ready, "declined" = blocked, "missing" = needs follow-up.
 - Adherence scores and risk flags (recent_hospitalization, recent_ed_visit) inform follow-up cadence and monitoring intensity.

 ### Registration and Intake Decisions
 - Registration status depends on the combination of insurance validity, PBM validity, pharmacy network, lifestyle risk, and overall risk.
 - Blocked reason codes enumerate specific issues preventing approval.
 - For transfers, the final intake decision (accept/hold/clinical_review) depends on packet completeness, document freshness, and capacity availability.

 ## Answer Construction Rules

 1. **Follow the template exactly.** Every top-level key and nested field must match the answer template JSON.
 2. **Use only controlled values.** Never invent new enum values; use only those listed in the template's allowed_values.
 3. **Sort lists as specified.** Patient lists ascending by patient_id (or transfer_id, referral_id). Document lists alphabetically by code. Blocked reason codes and issue codes are unordered sets — any order is acceptable.
 4. **Provide all required cohort summaries.** Include integer counts for every category specified in the template (counts_by_registration_status, counts_by_risk, decision_counts, etc.).
 5. **Include a record for every item in the batch.** Do not skip patients, referrals, or transfers.
 6. **Cross-reference thoroughly.** Use SQL JOINs or multiple queries to verify relationships across tables before finalizing any field.
 7. **Be precise with dates.** Use YYYY-MM-DD format. Compute age/duration carefully when checking staleness.
 8. **No prose outside the JSON.** The final output must be pure JSON with no additional explanation.

 ## Common Pitfalls

 - **Confusing draft with missing:** A document in draft status (finalized=0) is not usable. Treat it as missing.
 - **Overlooking service line exclusion:** Even if coverage is active, the specific service line must be listed in the coverage's service_lines.
 - **Missing capacity data:** Dates without facility_capacity rows mean no chairs are available.
 - **Ignoring duplicate notes:** The notes field in referrals often flags duplicates or anomalies.
 - **Assuming all artifacts are current:** Check last_updated dates and status fields for staleness.
 - **Mixing up insurance status and blocker codes:** A patient can have valid insurance but still have an excluded_service_line blocker.
