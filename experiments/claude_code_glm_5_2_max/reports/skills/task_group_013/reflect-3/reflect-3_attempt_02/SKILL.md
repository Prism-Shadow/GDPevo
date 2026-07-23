# Cedar Ridge Intake Coordination Skill

## Overview

This skill solves intake coordination tasks against the Cedar Ridge Intake Coordination Portal. The portal exposes patient, referral, transfer, chart, program, and clinical data through REST endpoints and a read-only SQL query interface. Each task requires querying the portal, applying domain-specific business rules to cross-reference records, and producing a structured JSON answer that follows a strict template with controlled enum values.

---

## 1. Portal Endpoints

Base URL is provided as `<TASK_ENV_BASE_URL>` in each task prompt. Use these endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Portal home page |
| GET | `/patients` | List/search patients (supports `q`, `limit` query params) |
| GET | `/patients/{patient_id}` | Single patient record |
| GET | `/referrals` | List/search referrals (supports `batch_id`, `service_line`, `limit`) |
| GET | `/referrals/{referral_id}` | Single referral |
| GET | `/transfers` | List/search transfers (supports `batch_id`, `limit`) |
| GET | `/transfers/{transfer_id}` | Single transfer |
| GET | `/documents` | List documents (no filters shown) |
| GET | `/chart/{patient_id}` | Chart data for a patient |
| GET | `/programs/{program_code}/candidates` | Program candidate list |
| GET | `/icd/{code}` | ICD-10 code metadata |
| GET | `/pharmacies` | List pharmacies |
| POST | `/query` | Read-only SQL (body: `{"sql": "SELECT ..."}`) |

No authentication is required.

---

## 2. Database Schema

The SQL endpoint (`POST /query`) is often the most efficient way to gather data. Key tables:

- **intake_rosters**: `roster_id, patient_id, requested_service_date, service_line, source_note`
- **patients**: `patient_id, first_name, last_name, dob, phone, email, language, address, existing_chart, preferred_contact, emergency_contact_present`
- **coverage**: `coverage_id, patient_id, payer, policy_number, group_number, effective_date, termination_date, network_status, service_lines, status`
- **pbm**: `pbm_id, patient_id, payer, policy_number, active, formulary_status, specialty_required, status`
- **patient_pharmacy**: `patient_id, pharmacy_id, preference_rank`
- **pharmacies**: `pharmacy_id, name, address, phone, network_status`
- **lifestyle**: `patient_id, smoking_status, alcohol_use, exercise_frequency, sleep_hours`
- **referrals**: `referral_id, batch_id, service_line, date_received, patient_id, payer, insurance_id, referring_physician, referring_practice, referring_phone, referring_fax, icd10_code, diagnosis_description, referral_reason, urgency, records_received, imaging_received, auth_required, auth_status, appointment_scheduled, appointment_date, assigned_physician, notes`
- **transfers**: `transfer_id, batch_id, patient_id, referring_facility, requested_start_date, requested_end_date, modality, days_requested, chair_window, transportation, status_note`
- **documents**: `document_id, patient_id, referral_id, transfer_id, doc_type, status, finalized, received_date, service_date, content_tag, notes`
- **icd_codes**: `code, description, chapter, service_family, laterality`
- **chart_artifacts**: `artifact_id, patient_id, artifact_type, status, last_updated, value_summary`
- **clinical_history**: `patient_id, chronic_conditions, surgeries, medication_count, allergy_count, recent_hospitalization, risk_flags`
- **program_candidates**: `program_code, patient_id, candidate_date, source, consent_status, preferred_outreach, adherence_score, target_condition`
- **facility_capacity**: `location_id, date, modality, open_chairs`

---

## 3. Task-Type Business Rules

### 3A. New Patient Access Verification (e.g., intake roster)

For each patient on the roster, determine:

**insurance_status** (from `coverage` table):
- `valid`: coverage `status` = "active", `network_status` = "in_network", and the `service_lines` field contains the required service_line
- `invalid`: coverage is expired/pending, or the required service_line is NOT in `service_lines`
- `missing`: no coverage record found

**prescription_status** (from `pbm` table):
- `valid`: `active` = 1, `status` = "approved" (or formulary_status = "covered")
- `invalid`: `active` = 0, `status` = "rejected", or formulary_status indicates rejection
- `missing`: no PBM record

**pharmacy_status** (from `patient_pharmacy` + `pharmacies` join):
- `in_network`: preferred pharmacy's `network_status` = "in_network"
- `out_of_network`: preferred pharmacy's `network_status` = "out_of_network"
- `unknown`: no pharmacy preference or pharmacy not found

**lifestyle_risk** (from `lifestyle` table):
- `high`: current smoker + no exercise + low sleep (< 6), OR heavy alcohol + former smoker + very low sleep
- `medium`: current or former smoker with moderate other factors
- `low`: former smoker with good exercise and sleep

**overall_risk**: Composite of lifestyle_risk plus coverage/pharmacy/PBM issues:
- `high`: lifestyle=high OR multiple blocking issues (expired coverage + out-of-network pharmacy)
- `medium`: lifestyle=medium with some issues, or low lifestyle but significant blockers
- `low`: no significant issues

**registration_status**:
- `approved`: all insurance/prescription valid, pharmacy in-network, low/medium overall risk
- `hold`: fixable blocking issues (pending coverage, PBM issues, pharmacy out-of-network)
- `clinical_review`: high overall risk with clinical concerns
- `rejected`: unresolvable issues (expired coverage + excluded service line)

**blocked_reason_codes**: List all specific blockers from the allowed values in the answer template. Key mappings:
- coverage `status` = "expired" → `coverage_expired`
- coverage `status` = "pending" → `coverage_pending`
- service_line not in coverage `service_lines` → `excluded_service_line`
- patient `address` is null → `missing_address`
- patient `emergency_contact_present` = 0 → `emergency_contact_missing`
- PBM `active` = 0 or `status` = "rejected" → `pbm_invalid`
- No PBM record or formulary not confirmed → `pbm_missing`
- PBM policy_number differs from coverage policy_number → `pbm_policy_mismatch`
- Pharmacy out-of-network → `pharmacy_out_of_network`
- Pharmacy not found → `pharmacy_unknown`
- preferred_contact method unreachable (e.g., preferred "email" but email is null, or preferred "sms" but phone is null) → `preferred_contact_unavailable`
- overall_risk = "high" → `overall_risk_high`

---

### 3B. Referral Batch Readiness Audit (orthopedic, pulmonary, etc.)

For each referral in the batch:

**ICD code audit**: Cross-reference each referral's `icd10_code` against `icd_codes` table:
- If `service_family` does not match the referral's `service_line` → clinical code discrepancy (include in `clinical_code_discrepancy_referrals`)
- Only flag mismatches where the ICD code's `service_family` genuinely conflicts with the referral `service_line`; matching service_family means no discrepancy even if diagnosis_description is generic

**Duplicate detection**:
- Same `patient_id` with same `icd10_code` in same batch → `duplicate_referral` issue; the first (lowest `referral_id`) is the primary
- Same `insurance_id` across different patients → `shared_insurance_anomaly`; disposition depends on whether patients are distinct

**Blocking issues**:
- `records_received` = 0 → `missing_records` / `records_missing`
- `imaging_received` = 0 → `missing_imaging` / `imaging_missing`
- `auth_required` = 1 and `auth_status` in ("denied", "pending", "not_submitted") → `auth_blocker` / `authorization_blocked`
- `appointment_scheduled` = 1 before blockers resolved → `already_scheduled` / `scheduled_before_clearance`
- ICD service_family mismatch → `clinical_code_discrepancy`

**readiness_status**:
- `ready`: no blocking issues (may have informational codes like `already_scheduled`)
- `blocked`: has hard blockers (auth denied, missing records/imaging)
- `under_review`: has soft issues needing confirmation (ICD discrepancy, shared insurance, duplicate flag)
- `admin_followup`: administrative duplicate resolution needed

**priority_tier** (for non-ready referrals):
- `tier_1_immediate`: urgent referrals OR auth denied with scheduled appointment
- `tier_2_short_term`: routine referrals with resolvable blockers
- `tier_3_administrative`: duplicate consolidation, already-scheduled

**ready_to_schedule**: Referrals with `readiness_status` = "ready" and all prerequisites met

---

### 3C. Dialysis Transfer Review

For each transfer in the batch:

**Packet completeness**: Check `documents` table for required document types. A document is missing if:
- No document of that type exists for the transfer, OR
- The document exists but `finalized` = 0 (draft status)

Required document types (from answer template): allergy_list, face_sheet, flu_vaccine, hbsag, hep_b_antibody_core, history_physical, insurance_proof, medication_list, monthly_labs, physician_orders, pneumonia_vaccine, ppd_or_cxr, transportation, treatment_flowsheets, vascular_access_report

**Stale documents**: Among finalized docs, check freshness against the transfer's `requested_start_date`:
- `hbsag`: must be within 90 days of requested_start_date
- `hep_b_antibody_core`: must be within 90 days
- `history_physical`: must be within 365 days
- `monthly_labs`: must be within 30 days
- `ppd_or_cxr`: must be within 365 days

Calculate age as: `requested_start_date - received_date` in days. If age exceeds the freshness limit, the document is stale.

**Capacity**: Query `facility_capacity` table for the `requested_start_date`, filtering by `modality = "in_center_hemodialysis"`. Sum `open_chairs` across all locations for that date. If no capacity rows exist for the requested date, open_chairs_total = 0.

**feasibility**:
- `ready_on_requested_start`: packet complete AND capacity available (open_chairs > 0)
- `packet_not_ready_capacity_available`: packet incomplete AND capacity available
- `packet_not_ready_capacity_unavailable`: packet incomplete AND no capacity
- `capacity_unavailable`: packet complete but no capacity

**final_intake_decision**:
- `accept`: ready_on_requested_start
- `hold`: packet issues are minor/fixable, or capacity-only issue
- `clinical_review`: significant packet gaps or multiple stale documents

**next_contact_owner** / **next_contact_route**:
- accept → `scheduling_coordinator` / `internal_queue`
- hold → `intake_coordinator` / route based on transportation status
- clinical_review → `clinical_nurse` / `fax_referring_facility`

---

### 3D. Chronic Care Enrollment Panel

For each program candidate:

**eligibility**: Must satisfy ALL:
1. `target_condition` matches the program's target (e.g., "diabetes_hypertension" for DMHTN-2026A)
2. `consent_status` = "signed"
3. `existing_chart` = 1
4. Patient has the relevant active diagnoses (diabetes + hypertension in chronic_conditions)

**enrollment_status**:
- `enroll`: eligible
- `hold`: potentially eligible but missing consent or chart (fixable)
- `reject`: wrong target condition, consent declined, or no relevant diagnoses

**reason_codes**: Include all applicable codes from the template's allowed_values. Key mappings:
- Eligible with DM+HTN → `meets_dmhtn_criteria`
- `recent_hospitalization` = 1 → `recent_hospitalization_high_touch`
- `adherence_score` < 50 → `low_adherence_high_touch`
- Has CKD condition → `ckd_biweekly_monitoring`
- `risk_flags` contains "recent_ed_visit" → `recent_ed_high_touch`
- `consent_status` = "declined" → `consent_declined`
- `consent_status` = "missing" → `consent_missing`
- `existing_chart` = 0 → `chart_not_active`
- Chart artifact `active_problems` with status "stale" → `stale_active_problems`
- `target_condition` doesn't match program → `wrong_target_condition`
- No diabetes/hypertension in chronic_conditions → `missing_active_dmhtn_diagnosis`

**Chart artifact assessment**: Query `chart_artifacts` for each patient. Missing artifacts from the template's allowed set include:
- `chart_record`: missing if `existing_chart` = 0
- `active_problems`, `vitals`, `labs`, `medications`, `consent`: missing if no current artifact of that type exists for the patient

**follow_up_cadence**:
- Enrolled with hospitalization, low adherence, or ED visit → `weekly`
- Enrolled with CKD → `biweekly`
- Enrolled standard → `monthly`
- Hold → `deferred`
- Reject → `none`

**outreach_channel**: Use candidate's `preferred_outreach` field (mapped to template: phone, portal, sms, email). Reject → `none`.

**initial_monitoring_package**:
- Enrolled high-touch (hospitalized, low adherence, ED visit): `high_touch_dm_htn` with bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup; first_checkin_days = 7
- Enrolled with CKD: `high_touch_dm_htn` same components; first_checkin_days = 14
- Enrolled standard: `standard_dm_htn` with bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation; first_checkin_days = 30
- Hold: `deferred` with consent_packet (+ chart_update_request if chart missing); first_checkin_days = null
- Reject: `not_applicable` with empty components; first_checkin_days = null

---

### 3E. Referral-to-Chart Activation (Pulmonary)

Combines referral readiness checks with chart activation needs:

**readiness_by_referral**: For each referral, determine readiness_status and blocker_codes following the same rules as 3B, but using this task's specific blocker code vocab.

**clinical_code_discrepancy_referrals**: Referral IDs where ICD service_family doesn't match referral service_line.

**blocker_sets**: Group blocked referrals by blocker type (authorization, records, imaging).

**duplicate_handling**: Identify duplicate referral groups, specify which referral to keep. Referrals flagged "possible duplicate" in notes but confirmed as distinct patients go in `cleared_duplicate_review_referrals`.

**ready_referral_chart_needs**: For each ready/under_review referral, determine chart action:
- `create_chart`: patient has `existing_chart` = 0
- `update_chart`: patient has `existing_chart` = 1 but chart artifacts are missing/stale
- `no_chart_action`: chart is complete and current

For artifacts_to_create, list missing chart artifact types.

**correspondence_queue**: Generate correspondence entries for referrals needing outreach:
- ICD mismatch → `clinical_code_clarification`
- Auth denied + missing records → `auth_records_request`
- Duplicate referrals → `duplicate_resolution`
- Already scheduled → `appointment_hold_notice`

**priority_order**: Rank non-ready referrals by severity (higher priority first).

---

## 4. General Procedures

1. **Read the task prompt carefully** — it specifies the batch/roster/program ID and which patient population to process.

2. **Read the answer template** — it defines the exact JSON structure, required fields, and allowed enum values. Always comply with these constraints.

3. **Gather all relevant data** — use the SQL endpoint to efficiently pull related records. Common queries:
   - `SELECT * FROM intake_rosters WHERE roster_id = '<ID>'`
   - `SELECT * FROM referrals WHERE batch_id = '<ID>'`
   - `SELECT * FROM transfers WHERE batch_id = '<ID>'`
   - `SELECT * FROM coverage WHERE patient_id IN (...)`
   - `SELECT * FROM pbm WHERE patient_id IN (...)`
   - ICD cross-reference: `SELECT * FROM icd_codes WHERE code IN (...)`
   - Document check: `SELECT * FROM documents WHERE transfer_id IN (...)` or `WHERE referral_id IN (...)`
   - Chart status: `SELECT * FROM chart_artifacts WHERE patient_id IN (...)`
   - Pharmacy network: join `patient_pharmacy` with `pharmacies`
   - Capacity: `SELECT date, SUM(open_chairs) FROM facility_capacity WHERE ... GROUP BY date`

4. **Apply business rules per task type** (see Section 3).

5. **Build the answer JSON** matching the template exactly:
   - Use only allowed enum values
   - Sort lists as specified (ascending by ID unless otherwise noted)
   - Treat reason_code/blocker_code arrays as unordered sets
   - Include all required top-level keys
   - Compute cohort/summary counts as integer aggregates

6. **Verify the answer** before submission:
   - All required keys present
   - All enum values match allowed sets
   - List ordering matches template specification
   - Summary counts are consistent with individual records
   - No free-form text where controlled values are expected

---

## 5. Common Pitfalls

- **Don't over-flag narrative mismatches**: A generic "specialty consultation" diagnosis description does NOT constitute a narrative_mismatch if the ICD code's service_family matches the referral's service_line. Only flag when there's a genuine cross-reference error.
- **Don't conflate "draft" with "missing"**: A document that exists but is unfinalized (draft) means the item is incomplete/missing for completeness purposes, but the document type itself is "present as draft".
- **Capacity data may not cover all dates**: If the `facility_capacity` table has no rows for a requested date, that date has 0 open chairs.
- **PBM policy_number cross-reference**: Check whether the PBM record's `policy_number` matches the coverage record's `policy_number` for the same patient. A mismatch indicates `pbm_policy_mismatch`.
- **Preferred contact availability**: If a patient's preferred_contact is "email" but `email` is null, or preferred is "sms" but `phone` is null, flag as `preferred_contact_unavailable`.
- **ICD laterality**: Only flag `laterality_mismatch` when the ICD code specifies a laterality (e.g., "left") but the referral narrative does not acknowledge it. If the ICD code itself contains the laterality, there may be no mismatch.
- **Duplicate detection**: Two referrals for the same patient with the same ICD code are duplicates. The primary referral is the one with the lower referral_id.
- **Shared insurance across different patients**: Different patients sharing the same `insurance_id` is an anomaly requiring verification.
