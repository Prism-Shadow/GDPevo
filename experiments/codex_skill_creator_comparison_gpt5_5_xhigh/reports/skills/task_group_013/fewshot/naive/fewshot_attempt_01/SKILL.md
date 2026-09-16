---
name: cedar-ridge-intake-json
description: Solve Cedar Ridge Intake Coordination Portal tasks that require reconciling roster, referral, dialysis transfer, chart, program, pharmacy, coverage, PBM, document, capacity, or ICD data into a strict JSON answer template.
---

# Cedar Ridge Intake JSON

Use this skill for Cedar Ridge Intake Coordination Portal tasks where the prompt gives a portal base URL and an `input/payloads/answer_template.json` file. Produce only the final JSON object requested by the template.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract for required keys, allowed enum values, ordering, constants, and count keys.
2. Identify the task family and target ID from the prompt: intake roster, referral batch, dialysis transfer batch, or chronic-care program.
3. Query the portal data. The listed REST endpoints are useful for browsing; the read-only SQL endpoint is best for reconciliation:

```bash
curl -sS -X POST "$BASE_URL/query" \
  -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT ..."}'
```

4. Build an evidence table per target entity before writing JSON. Include all fields that drive status, reason codes, readiness, counts, and ordering.
5. Fill every required object and every required count key from the template. Use `0`, `[]`, or `null` when the template requires a field and no evidence applies.
6. Validate the final JSON mechanically: parse it, check required keys, allowed enum values, ordering, set-like arrays, and summary counts. Do not include prose outside JSON.

Use only the business endpoints and `/query`. Do not call judge/evaluator endpoints.

## Useful Table Map

- `patients`: demographics, contact availability, `existing_chart`, preferred contact, emergency contact.
- `intake_rosters`: roster patient IDs, requested service date, service line.
- `coverage`: payer coverage status, dates, network status, covered service lines.
- `pbm`: prescription benefit active/status/formulary/specialty flags.
- `patient_pharmacy` plus `pharmacies`: preferred pharmacy and network status.
- `lifestyle` and `clinical_history`: lifestyle risk inputs and clinical flags.
- `referrals`: batch rows, ICD code, referral reason, records/imaging/auth/scheduled flags, urgency, duplicate hints.
- `icd_codes`: code description, chapter, service family, laterality.
- `documents`: referral support documents and transfer packet documents; only finalized final documents count as present.
- `transfer_requests`: dialysis transfer dates, modality, schedule, transportation.
- `facility_capacity`: sum open chairs by requested date and modality.
- `program_candidates`: chronic-care candidate source, consent, outreach, adherence, and target condition.
- `chart_artifacts`: chart artifact status and recency/currentness.

## SQL Starting Points

For roster access verification:

```sql
SELECT r.*, p.address, p.phone, p.email, p.preferred_contact,
       p.emergency_contact_present,
       c.status AS coverage_status, c.effective_date, c.termination_date,
       c.network_status, c.service_lines,
       pb.active AS pbm_active, pb.formulary_status, pb.specialty_required,
       pb.status AS pbm_status,
       l.smoking_status, l.alcohol_use, l.exercise_frequency, l.sleep_hours,
       h.risk_flags, h.medication_count, h.recent_hospitalization,
       ph.network_status AS pharmacy_network
FROM intake_rosters r
JOIN patients p ON p.patient_id = r.patient_id
LEFT JOIN coverage c ON c.patient_id = r.patient_id
LEFT JOIN pbm pb ON pb.patient_id = r.patient_id
LEFT JOIN lifestyle l ON l.patient_id = r.patient_id
LEFT JOIN clinical_history h ON h.patient_id = r.patient_id
LEFT JOIN patient_pharmacy pp ON pp.patient_id = r.patient_id AND pp.preference_rank = 1
LEFT JOIN pharmacies ph ON ph.pharmacy_id = pp.pharmacy_id
WHERE r.roster_id = '<ROSTER_ID>'
ORDER BY r.patient_id;
```

For referral batches:

```sql
SELECT r.*, i.description AS icd_description, i.chapter, i.service_family, i.laterality
FROM referrals r
LEFT JOIN icd_codes i ON i.code = r.icd10_code
WHERE r.batch_id = '<BATCH_ID>'
ORDER BY r.referral_id;
```

For transfer batches:

```sql
SELECT tr.*, d.doc_type, d.status, d.finalized, d.received_date
FROM transfer_requests tr
LEFT JOIN documents d ON d.transfer_id = tr.transfer_id
WHERE tr.batch_id = '<BATCH_ID>'
ORDER BY tr.transfer_id, d.doc_type;
```

For program candidates:

```sql
SELECT pc.*, p.phone, p.email, p.preferred_contact, p.existing_chart,
       h.chronic_conditions, h.recent_hospitalization, h.risk_flags,
       h.medication_count
FROM program_candidates pc
LEFT JOIN patients p ON p.patient_id = pc.patient_id
LEFT JOIN clinical_history h ON h.patient_id = pc.patient_id
WHERE pc.program_code = '<PROGRAM_CODE>'
ORDER BY pc.patient_id;
```

## Roster Access Verification Rules

Use the roster record for `requested_service_date` and `service_line`.

Insurance:

- `valid`: coverage exists, is active on the requested service date, and the service line appears in `coverage.service_lines`.
- `invalid`: coverage exists but is expired, pending, outside its effective dates, out of network, or excludes the requested service line.
- `missing`: no coverage record.

Insurance reason codes:

- `coverage_expired`: coverage status is expired or the requested date is after termination.
- `coverage_pending`: coverage status is pending.
- `excluded_service_line`: requested service line is absent from `service_lines`.
- `missing_address`: patient address is absent.

Prescription benefit:

- `valid`: PBM exists, `active = 1`, `status = approved`, `formulary_status = covered`, and no policy/service mismatch applies.
- `invalid`: PBM exists but is inactive, rejected, pending/review, not covered, not found, or mismatched to the service context.
- `missing`: no PBM record.

PBM reason codes:

- `pbm_missing`: no PBM record.
- `pbm_invalid`: inactive, rejected, pending, review, not found, or non-covered PBM evidence.
- `pbm_policy_mismatch`: the PBM policy requires a specialty/scope that does not match the requested intake service.

Pharmacy:

- Use the rank-1 preferred pharmacy.
- `in_network` or `out_of_network`: copy the pharmacy network status.
- `unknown`: no preferred pharmacy or no pharmacy network evidence.

Pharmacy reason codes:

- `pharmacy_out_of_network`: preferred pharmacy is out of network.
- `pharmacy_unknown`: preferred pharmacy/network evidence is missing.

Administrative/contact reason codes:

- `preferred_contact_unavailable`: preferred contact route cannot be used because the required phone or email is missing, or portal access depends on an inactive chart.
- `emergency_contact_missing`: `emergency_contact_present = 0`.

Risk:

- Lifestyle `high`: any high-risk lifestyle factor such as current smoking, heavy alcohol use, no/missing exercise, or short sleep.
- Lifestyle `medium`: former smoking, moderate alcohol, borderline sleep, or other moderate lifestyle concern without a high-risk factor.
- Lifestyle `low`: no material lifestyle concerns.
- Overall `high`: high lifestyle risk, hard coverage/PBM/pharmacy blockers, missing emergency contact, recent hospitalization, complex risk flags, or other serious clinical/admin blocker.
- Overall `medium`: medium lifestyle or moderate clinical/admin concern without high criteria.
- Overall `low`: clean access and low lifestyle/clinical risk.

Registration status:

- `approved`: all access checks are valid/in-network, no blocked reasons, and overall risk is not high.
- `rejected`: hard ineligibility such as expired coverage or excluded service line.
- `clinical_review`: overall high risk or clinical/access issues that require review but are not hard rejection.
- `hold`: administrative gaps that can be fixed without clinical rejection.

## Referral Readiness And Activation Rules

Evaluate every referral in the target batch.

Clinical code discrepancy:

- Join each referral to `icd_codes`.
- `icd_chapter_mismatch`: the ICD chapter is outside the chapter expected for the batch/service family when the template asks for chapter discrepancies.
- `wrong_service_family` or service-family discrepancy: `icd_codes.service_family` does not match the referral `service_line`.
- `narrative_mismatch` / `clinical_reason_mismatch`: referral reason or diagnosis narrative is incompatible with the ICD description/service family.
- `laterality_mismatch`: ICD laterality conflicts with referral narrative, documents, or laterality fields.
- Include observed chapter from the ICD row and the expected chapter/service family implied by the target service.

Operational blockers:

- Missing records: `records_received = 0`.
- Missing imaging: `imaging_received = 0` when imaging is expected or the template has imaging blockers.
- Authorization blocker: `auth_required = 1` and `auth_status` is `pending`, `denied`, or `not_submitted`.
- Already scheduled / scheduled before clearance: `appointment_scheduled = 1` while any blocker or review issue remains.

Duplicates and shared insurance:

- Duplicate referral group: same batch plus same patient, same insurance or repeated referral facts, or explicit duplicate-practice/duplicate-note evidence. Use the lowest referral ID as the primary/keep referral unless stronger evidence says otherwise.
- Shared insurance anomaly: same `insurance_id` appears for different patients in the batch. Use a verify-distinct-patient disposition.
- Legitimate same-patient duplicate insurance belongs with duplicate handling, not distinct-patient anomaly.
- Referrals flagged as possible duplicate but not actually duplicate should be cleared when the template asks for cleared duplicate review referrals.

Readiness status:

- `ready`: no clinical discrepancy, no missing records/imaging, no authorization blocker, no unresolved duplicate/shared-insurance issue, and not scheduled before clearance.
- `blocked`: any hard operational blocker, especially missing records, missing imaging, or authorization blocker. Hard blockers dominate clinical review.
- `under_review`: clinical code discrepancy, duplicate review, or already-scheduled issue without hard operational blockers.
- `admin_followup`: administrative-only issue such as shared-insurance verification.

Priority:

- `tier_1_immediate`: urgent referrals with clinical code discrepancy or other clinically important review.
- `tier_2_short_term`: routine clinical review, duplicate review, scheduled-before-clearance, missing records/imaging, or authorization work.
- `tier_3_administrative`: admin-only verification.
- For a ranked priority list, include non-ready referrals only. Sort by tier, then urgent before routine, then scheduled-before-clearance/multiple blockers, then clinical-code issues, then auth/records/imaging-only issues, and keep deterministic ID order for ties.

Action and correspondence mapping:

- Corrected ICD/code discrepancy -> `request_corrected_icd` or clinical-code clarification.
- Narrative mismatch -> `confirm_narrative` or clinical reason clarification.
- Laterality mismatch -> `confirm_laterality`.
- Duplicate -> `consolidate_duplicate` or duplicate resolution.
- Shared insurance -> `verify_insurance_id`.
- Missing records -> `request_records`.
- Missing imaging -> `request_imaging`.
- Authorization blocker -> `resolve_authorization`.
- Appointment scheduled before clearance -> `review_existing_appointment` or appointment hold notice.

Only put referrals with no remaining blockers into ready-to-schedule or ready chart-activation lists.

For chart activation outputs, inspect `chart_artifacts` for ready referrals:

- `create_chart`: patient has no existing chart.
- `update_chart`: existing chart has missing or stale required artifacts.
- `no_chart_action`: all required chart artifacts are current.
- Artifacts to create/update are the allowed artifact names whose chart artifact is missing or not current. Sort alphabetically when required.

## Dialysis Transfer Review Rules

For each transfer in the target batch:

Packet completeness:

- Required documents are the document codes listed in the template.
- A document counts as present only when `finalized = 1` and `status = final`.
- Draft or non-final documents count as missing.
- `transportation` may be a required item even though it comes from `transfer_requests.transportation`; null transportation is missing.
- `packet_completeness_status` is `complete` when all required items are present, otherwise `incomplete`.

Freshness:

- Compare each stale-check document's final `received_date` to the transfer `requested_start_date`.
- Use freshness limits from the template when present. If the task relies on Cedar Ridge defaults: `hbsag`, `monthly_labs`, and `ppd_or_cxr` expire after 30 days; `history_physical` and `hep_b_antibody_core` expire after 365 days.
- Include stale documents even when the packet is otherwise complete.

Capacity and feasibility:

- Sum `facility_capacity.open_chairs` across locations for the exact requested start date and modality.
- `capacity_status = available` when total open chairs is greater than zero; otherwise `unavailable` and total is `0`.
- `ready_on_requested_start`: packet complete, no stale documents, and capacity available.
- `packet_not_ready_capacity_available`: missing or stale packet evidence with capacity available.
- `packet_not_ready_capacity_unavailable`: missing or stale packet evidence and no capacity.
- `capacity_unavailable`: packet ready but no capacity.

Final decision and routing:

- `accept`: packet complete, no stale documents, capacity available.
- `clinical_review`: stale clinical documents or clinical packet gaps.
- `hold`: administrative-only packet or capacity issue.
- `clinical_nurse` plus `fax_referring_facility`: clinical packet missing/stale issues.
- `intake_coordinator`: administrative document or transportation follow-up.
- `scheduling_coordinator` plus `internal_queue`: capacity-only issue.
- `none`: no follow-up required.

## Chronic-Care Program Enrollment Rules

Use the program candidate endpoint or `program_candidates` table for the exact program code. Include every current candidate returned by the portal.

Eligibility and reasons:

- For a diabetes-hypertension program, eligible candidates have the target condition and active clinical history for both diabetes and hypertension.
- `wrong_target_condition`: candidate target condition is not the program target.
- `missing_active_dmhtn_diagnosis`: clinical history lacks active diabetes and hypertension.
- `meets_dmhtn_criteria`: eligible, consent signed, active chart, and required chart evidence is current enough for enrollment.
- `consent_declined` and `consent_missing`: from `program_candidates.consent_status`; declined is a rejection reason, missing is a hold reason for otherwise eligible candidates.
- `chart_not_active`: patient does not have an active existing chart.
- `stale_active_problems`, `missing_recent_vitals`, `missing_recent_labs`, `missing_medication_list`: required chart artifacts are missing or not current.

High-touch and cadence:

- Recent hospitalization -> `recent_hospitalization_high_touch`, `weekly`, high-touch package.
- Low adherence -> `low_adherence_high_touch`, `weekly`, high-touch package. Treat low adherence as a low numeric adherence score; recent hospitalization takes precedence when both apply.
- Recent ED risk flag -> `recent_ed_high_touch`, `weekly`, high-touch package.
- CKD without higher-touch criteria -> `ckd_biweekly_monitoring`, `biweekly`, standard package.
- Standard eligible enrollment -> `monthly`, standard package.
- Holds -> `deferred`; rejects -> `none`.

Enrollment status:

- `enroll`: eligible, consent signed, active chart, and no missing/stale required enrollment artifacts.
- `hold`: eligible but consent or chart artifacts need follow-up.
- `reject`: ineligible target/diagnosis or declined consent.

Outreach:

- Use `preferred_outreach` when the route is usable.
- Phone/SMS require a phone number. Email requires an email address. Portal requires an active chart.
- If preferred outreach is unusable, fall back to a usable patient preferred contact, then phone, email, sms, portal. Use `none` only when no route works or the template requires no outreach for the disposition.

Monitoring package:

- `high_touch_dm_htn`: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`, `medication_reconciliation`, `care_plan_setup`; first check-in `7`.
- `standard_dm_htn` with CKD/biweekly: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`, `medication_reconciliation`; first check-in `14`.
- `standard_dm_htn` monthly: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`; first check-in `30`.
- `deferred`: `consent_packet` and/or `chart_update_request` as indicated by missing consent/chart artifacts; first check-in `null`.
- `not_applicable`: empty components and `null` check-in.

## Final Validation

- Sort entity rows exactly as the template states, usually ascending patient, referral, transfer, group, or insurance ID.
- Treat reason-code and blocker-code arrays as unordered sets unless the template gives a sort rule; a stable alphabetical order is acceptable for unordered sets.
- Recompute all summary counts from the completed entity rows, not from intermediate notes.
- Include required zero-valued enum keys in count objects.
- Confirm the response is one valid JSON object and nothing else.
