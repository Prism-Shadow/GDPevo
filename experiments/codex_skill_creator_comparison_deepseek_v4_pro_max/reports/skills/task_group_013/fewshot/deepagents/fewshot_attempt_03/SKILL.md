---
name: cedar-ridge-intake
description: "Navigates the Cedar Ridge Intake Coordination Portal, a read-only REST API with optional SQL query endpoint used for healthcare intake tasks. Use when a task references Cedar Ridge, the intake coordination portal, or asks to work with patient rosters, referral batches, transfer packets, program enrollment panels, chart activation, or patient access verification against a read-only healthcare API. Covers five intake workflows: patient access verification, referral readiness auditing, dialysis transfer review, chronic-care program enrollment, and referral-to-chart activation."
---

# Cedar Ridge Intake Coordination

The portal is a read-only REST API at `<TASK_ENV_BASE_URL>` plus a SQL endpoint at `POST /query`. Every intake task expects a single JSON answer following a supplied answer template. Collect data through the API, reconcile according to the rules below, and populate the template fields exactly.

## Quick Start

1. Identify the task type from the prompt (access verification, referral audit, transfer review, program enrollment, or chart activation).
2. Read the supplied answer template for the required output shape.
3. Collect batch/roster records from the relevant API endpoints.
4. Pull supporting records (patients, coverage, charts, ICD codes, pharmacies, documents, capacity) for every entity in scope.
5. Apply the business rules for the task type (below).
6. Write the final JSON answer. Keep ordering as the template specifies. Do not add prose.

## Portal Endpoints

See [references/api_reference.md](references/api_reference.md) for the full endpoint catalog, data model, field meanings, and SQL table listing. Load it when you need field-level detail or the SQL schema.

## Workflow 1: Patient Access Verification

Used for primary-care intake or similar new-patient registration work.

### Input
A roster ID and a set of patient IDs. Pull the roster from the SQL endpoint (`intake_rosters` table) to get `requested_service_date` and `service_line`.

### Data Collection
For each patient, pull:
- `/patients/{id}` (demographics, emergency contact, preferred contact, existing chart)
- `/chart/{id}` (coverage, lifestyle, PBM via SQL, pharmacy via SQL)

### Insurance Status
- `valid`: at least one coverage row with `status = "active"` and the roster's `service_line` appears in its `service_lines` field.
- `invalid`: coverage exists but is expired, pending, or lacks the service line.
- `missing`: no coverage record.

### Prescription Status
Use the `pbm` table via SQL joined on patient_id or coverage.
- `valid`: PBM record exists and is `active`, with policy matching the coverage.
- `invalid`: PBM exists but is `inactive`, expired, or has a policy mismatch.
- `missing`: no PBM record.

### Pharmacy Status
Use `patient_pharmacy` joined with `pharmacies` tables via SQL.
- `in_network`: patient has an assigned pharmacy with `network_status = "in_network"`.
- `out_of_network`: assigned pharmacy is `out_of_network`.
- `unknown`: no pharmacy assignment.

### Lifestyle Risk
Derive from `lifestyle` table fields: `smoking_status`, `alcohol_use`, `exercise_frequency`, `sleep_hours`.
- `high`: Current smoking OR None exercise plus moderate/heavy alcohol OR sleep below 6 hours.
- `medium`: Former smoking, light alcohol, irregular exercise, or sleep 6-7 hours.
- `low`: None of the above risk factors.

### Overall Risk
Combine lifestyle risk, coverage gaps, and clinical history flags. Any `high` lifestyle risk plus multiple coverage/PBM issues drives `overall_risk: "high"`. Assign `medium` or `low` when risk factors are less severe.

### Registration Status
- `approved`: no blocked reason codes.
- `hold`: only minor administrative blockers (missing_address, preferred_contact_unavailable).
- `clinical_review`: blockers that need clinical judgment (pharmacy issues, PBM issues, coverage_pending, overall_risk_high).
- `rejected`: hard blockers (coverage_expired, excluded_service_line, pbm_policy_mismatch).

### Blocked Reason Codes
Apply from the template's allowed set. Multiple codes may apply. Common triggers:
- `coverage_expired`: coverage status is terminated/expired.
- `coverage_pending`: coverage status is pending.
- `excluded_service_line`: no coverage includes the target service_line.
- `emergency_contact_missing`: `emergency_contact_present = 0`.
- `missing_address`: address is null.
- `pbm_invalid`: PBM inactive/expired.
- `pbm_missing`: no PBM record.
- `pbm_policy_mismatch`: PBM policy doesn't match coverage.
- `pharmacy_out_of_network`: pharmacy is out of network.
- `pharmacy_unknown`: no pharmacy assigned.
- `preferred_contact_unavailable`: preferred contact method lacks data (email preferred but null email, sms preferred but null phone, phone preferred but null phone).
- `overall_risk_high`: overall_risk is high.

## Workflow 2: Referral Readiness Audit

Used for batch referral quality review before scheduling.

### Data Collection
Pull referrals filtered by `batch_id` via `/referrals?batch_id=...` or SQL. For each referral, also pull:
- `/referrals/{id}` (ICD metadata, patient context, documents)
- `/icd/{code}` if needed for chapter/service_family resolution
- `/patients/{id}` for insurance context

### ICD Chapter Mismatch
Compare the referral's ICD chapter against the expected chapter for the referral's `service_line`:
- `orthopedics` -> M00-M99
- `pulmonary` -> J00-J99
- `cardiology` -> I00-I99
- `primary_care` -> any chapter is acceptable
- `neurology` -> G00-G99

If the chapter doesn't match, flag `icd_chapter_mismatch`. Record `observed_chapter` (actual) and `expected_chapter` (expected for the service_line).

### Narrative Mismatch
When the `diagnosis_description` on the referral conflicts with the ICD code's `description` or clinical context.

### Laterality Mismatch
When the referral reason implies different laterality than the ICD code's `laterality` field.

### Duplicate Detection
Two or more referrals for the same patient, same `service_line`, same ICD code. Group them with a derived `group_id`. Recommend `consolidate_to_primary` (keep the earliest-received) or `keep_separate` if clinical context differs.

### Shared Insurance Anomaly
Different patients sharing the same `insurance_id` across referrals. Disposition: `verify_distinct_patient_policy_id` unless the same patient appears twice (then `legitimate_duplicate_same_patient`).

### Authorization Blockers
`auth_status` of `pending` or `denied` when `auth_required = 1`. Only flag as a blocker when the auth is actively blocking scheduling.

### Missing Records / Imaging
`records_received = 0` -> missing_records. `imaging_received = 0` -> missing_imaging.

### Already Scheduled
`appointment_scheduled = 1` or `appointment_date` is set.

### Readiness Status
- `ready`: no issue codes.
- `blocked`: has `auth_blocker`, `missing_records`, or `missing_imaging`.
- `under_review`: has ICD, narrative, laterality, or duplicate issues but no hard blockers.
- `admin_followup`: has `shared_insurance_anomaly` or `already_scheduled` but no hard blockers.

### Priority Tiers
- `tier_1_immediate`: urgent referrals with code discrepancies or clinical questions.
- `tier_2_short_term`: routine referrals with records/imaging/auth gaps or duplicates.
- `tier_3_administrative`: admin or insurance-only issues.

## Workflow 3: Dialysis Transfer Review

Used for seasonal or incoming dialysis patient transfers.

### Data Collection
Pull transfers via `/transfers?batch_id=...` or SQL. For each transfer, pull `/transfers/{id}` which returns documents, capacity, patient, and transfer data together.

### Packet Completeness
Check for expected doc_types in the transfer's documents list. A document is only valid if `finalized = 1` (or `status = "final"`). If finalized = 0 or status = "draft", treat as missing. Required documents are those commonly needed for dialysis intake; see the answer template for the full allowed list.

### Document Staleness
Each doc_type has a freshness limit in days. Compare `received_date` to the effective date (typically `as_of_date` or the task date). If the gap exceeds the limit, the document is stale.

Standard freshness limits:
- `hbsag`: 30 days
- `hep_b_antibody_core`: 30 days
- `history_physical`: 365 days
- `monthly_labs`: 30 days
- `ppd_or_cxr`: 30 days

### Capacity Feasibility
Match the transfer's `requested_start_date` against capacity records from the `facility_capacity` table. Sum `open_chairs` across all locations for that date. If total > 0, capacity is `available`; otherwise `unavailable`.

### Feasibility
- `ready_on_requested_start`: packet complete, no stale docs, capacity available.
- `packet_not_ready_capacity_available`: packet incomplete or stale but capacity available.
- `packet_not_ready_capacity_unavailable`: packet incomplete or stale and no capacity.
- `capacity_unavailable`: packet ready but no capacity.

### Final Intake Decision
- `accept`: ready_on_requested_start.
- `hold`: capacity_unavailable.
- `clinical_review`: packet not ready (incomplete or stale), regardless of capacity.

### Next Contact
- `clinical_nurse` + `fax_referring_facility`: when packet is incomplete or stale (most common).
- `scheduling_coordinator` + `internal_queue`: when only capacity is the issue.
- `intake_coordinator` + `phone_patient`: minor packet issues with available capacity.
- `none` + `none`: when accepted.

## Workflow 4: Chronic-Care Program Enrollment

Used for building enrollment panels from program candidate lists.

### Data Collection
Pull candidates from `/programs/{program_code}/candidates`. For each candidate, pull `/chart/{patient_id}` for clinical history, chart artifacts, vitals, labs, medications, active problems, and consent.

### Eligibility
- `eligible: true`: candidate's `target_condition` matches the program focus AND `existing_chart = 1` AND chart has an active diagnosis matching the program condition.
- `eligible: false`: wrong target condition, chart not active, or missing active diagnosis.

### Enrollment Status
- `enroll`: eligible, consent signed, chart is active and has current artifacts.
- `hold`: eligible, consent is signed or missing, but chart is not active or has stale/missing artifacts requiring work before enrollment.
- `reject`: ineligible, OR consent declined, OR chart not active with no path to activation.

### Reason Codes
Apply from the template's allowed set. Common triggers:
- `meets_dmhtn_criteria`: eligible with matching condition.
- `recent_hospitalization_high_touch`: `recent_hospitalization = 1` in clinical_history.
- `low_adherence_high_touch`: `adherence_score` below 50.
- `ckd_biweekly_monitoring`: chronic conditions include kidney disease (ckd, renal).
- `recent_ed_high_touch`: recent ED visits indicated in clinical history.
- `consent_declined`: consent_status is "declined".
- `consent_missing`: consent_status absent/null but not declined.
- `chart_not_active`: existing_chart = 0 or chart record missing.
- `stale_active_problems`: active_problems last_updated is more than 6 months ago.
- `missing_recent_vitals`: no vitals record in recent_vitals_labs.
- `missing_recent_labs`: no labs record in recent_vitals_labs.
- `missing_medication_list`: no medications artifact.
- `wrong_target_condition`: target_condition doesn't match program focus.
- `missing_active_dmhtn_diagnosis`: no active diagnosis for the program condition in the chart.

### Follow-up Cadence
- `weekly`: high-touch patients (recent hospitalization, low adherence, recent ED).
- `biweekly`: CKD or other chronic monitoring needs.
- `monthly`: standard enrollment, no high-touch flags.
- `deferred`: on hold, waiting for chart/consent resolution.
- `none`: rejected.

### Missing Chart Artifacts
Check for presence and recency of `active_problems`, `vitals`, `labs`, `medications`, `consent`, and the chart record itself. List any that are missing or stale from the template's allowed values: `chart_record`, `active_problems`, `vitals`, `labs`, `medications`, `consent`.

### Outreach Channel
Use the candidate's `preferred_outreach` field. Map: "portal" -> `portal`, "phone" -> `phone`, "email" -> `email`, "sms" -> `sms`. If the preferred method is unavailable (e.g., no email address but email preferred), fall back to the next available contact method.

### Initial Monitoring Package
- `high_touch_dm_htn`: patients with high-touch flags (recent hospitalization, low adherence, recent ED). Components: bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup. First checkin: 7 days.
- `standard_dm_htn`: standard eligible patients. Components: bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation. First checkin: 14 days (biweekly cadence) or 30 days (monthly cadence).
- `deferred`: hold patients. Components: consent_packet, chart_update_request. First checkin: null.
- `not_applicable`: rejected patients. Components: []. First checkin: null.

## Workflow 5: Referral-to-Chart Activation

Used when referrals have passed initial audit and need chart setup before confirming.

### Data Collection
Same as Workflow 2 plus `/chart/{patient_id}` for each referred patient.

### Clinical Code Discrepancy
Compare the ICD `service_family` (from `/icd/{code}`) against the referral's `service_line`. If they don't match, flag `clinical_code_discrepancy`.

### Blocker Sets
- `authorization`: referrals where `auth_status = "denied"` (not pending; pending is under_review).
- `records`: referrals where `records_received = 0`.
- `imaging`: referrals where `imaging_received = 0`.

### Duplicate Handling
Same logic as Workflow 2. Additionally track `cleared_duplicate_review_referrals`: referrals that were flagged as duplicates but the review determined they are distinct (same patient but different clinical context, different ICD codes, etc.).

### Ready Referral Chart Needs
For referrals with readiness_status = `ready`, check `/chart/{patient_id}`:
- `create_chart`: no existing chart (`existing_chart = 0`). List artifacts to create alphabetically from: demographics, active_problems, medications, allergies, vitals, labs, consent.
- `update_chart`: chart exists but missing artifacts. List missing artifacts alphabetically.
- `no_chart_action`: chart is complete with all expected artifacts present.

### Correspondence Queue
For non-ready referrals, determine the `template_type`:
- `clinical_code_clarification`: ICD/service_line mismatch. Reason codes: `wrong_service_family` or `clinical_reason_mismatch`.
- `auth_records_request`: authorization denied or records missing. Reason codes: `authorization_denied`, `records_missing`.
- `duplicate_resolution`: duplicate review needed.
- `appointment_hold_notice`: already scheduled before clearance. Reason codes: `appointment_already_scheduled` plus any other blockers.

### Priority Order
Rank non-ready referrals highest priority first:
- Tier 1 (immediate): urgent referrals needing clinical clarification.
- Tier 2 (short-term): routine referrals with auth/records/imaging/duplicate issues.
- Tier 3 (administrative): admin-only issues.

## SQL Query Endpoint

Use `POST /query` with `{"sql": "..."}` for complex cross-table queries. Only SELECT statements are allowed. All tables are listed in the API reference. Joins spanning patients, coverage, referrals, documents, and capacity are common.

The SQL endpoint is often the fastest way to collect batch-level data in one call instead of N individual API requests. Examples of useful queries:

- Batch referrals with patient info: `SELECT * FROM referrals WHERE batch_id = '<batch_id>' ORDER BY referral_id`
- Roster details: `SELECT * FROM intake_rosters WHERE roster_id = '<roster_id>' ORDER BY patient_id`
- Coverage for multiple patients: `SELECT * FROM coverage WHERE patient_id IN ('<patient_id>',...)`

## Output Conventions

- Every answer is a single JSON object matching the supplied template exactly.
- Patient/referral/transfer lists are ordered ascending by ID as the template specifies.
- Reason codes and blocker codes are treated as unordered sets.
- Use uppercase IDs exactly as the portal returns them.
- Integer counts only; no floating point in summary fields.
- Dates in YYYY-MM-DD format.
- Do not include prose, markdown fences, or explanation outside the JSON.
