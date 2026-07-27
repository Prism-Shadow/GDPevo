---
name: cedar-ridge-intake-reconciliation
description: Reconcile Cedar Ridge Intake Coordination Portal worklists into strict controlled-value JSON. Use when a task references Cedar Ridge roster access verification, referral readiness or chart activation, dialysis transfer packet and capacity review, chronic-care program enrollment panels, answer_template.json payloads, or the shared intake coordination portal.
---

# Cedar Ridge Intake Reconciliation

## Core Workflow

1. Read the task prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract for keys, enums, ordering, nullability, and counts.
2. Use the portal base URL supplied by the task. Prefer `POST /query` with `SELECT` statements for exact joins; use detail endpoints such as `/referrals/{id}`, `/transfers/{id}`, `/patients/{id}`, `/chart/{patient_id}`, and `/icd/{code}` to spot-check bundled records.
3. Extract target identifiers from the prompt/template instead of hard-coding train IDs. For rosters use `intake_rosters`; for referrals use `referrals.batch_id`; for transfers use `transfer_requests.batch_id`; for programs use `/programs/{program_code}/candidates` or `program_candidates`.
4. Build results from source rows only. Ignore distractor batches and patients unless needed to detect shared IDs or duplicates within the target set.
5. Preserve template ordering exactly: usually ascending item IDs, unordered code sets as stable sorted arrays, and ranked priority lists highest priority first.
6. Emit one JSON object only. Do not add prose, comments, unrequested fields, or enum values not present in the template.

## Useful Tables

- `patients`: demographics, contact availability, `existing_chart`, preferred contact, emergency contact.
- `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`: access verification.
- `lifestyle`, `clinical_history`: lifestyle and clinical risk; chronic-care prioritization.
- `referrals`, `icd_codes`, `documents`, `chart_artifacts`: referral readiness and chart activation.
- `transfer_requests`, `documents`, `facility_capacity`: dialysis transfer packets and start feasibility.
- `program_candidates`, `chart_artifacts`, `clinical_history`: chronic-care enrollment.

## Access Verification Rules

Use roster rows for `requested_service_date` and `service_line`, then join patient, coverage, PBM, preferred pharmacy, lifestyle, and clinical history.

Coverage:
- `valid`: coverage is active on the requested date, has a usable policy, and includes the requested service line.
- `missing`: no coverage row or coverage status is pending. Add `coverage_pending` for pending rows.
- `invalid`: expired or terminated before the requested date, or active coverage excludes the service line. Add `coverage_expired` and/or `excluded_service_line`.

Prescription benefit:
- `valid`: PBM is active, approved, covered, and matches the coverage payer/policy.
- `missing`: no PBM or PBM is pending/review. Add `pbm_missing`.
- `invalid`: inactive, rejected, not found, not covered, payer/policy mismatch, or incompatible specialty requirement. Add `pbm_invalid`, `pbm_policy_mismatch`, or both as applicable.

Pharmacy:
- Use the lowest `preference_rank` pharmacy unless the task says otherwise.
- Map pharmacy network directly to `in_network` or `out_of_network`; use `unknown` when no preferred pharmacy or no network status exists.
- Add `pharmacy_out_of_network` or `pharmacy_unknown` for non-clearable pharmacy results.

Administrative blockers:
- Add `missing_address` when `patients.address` is null.
- Add `emergency_contact_missing` when `emergency_contact_present` is false.
- Add `preferred_contact_unavailable` when the preferred route lacks the needed contact field: email/portal needs email, phone/sms needs phone.

Risk and registration:
- Score lifestyle from smoking, alcohol, exercise, and sleep. Current smoking, heavy alcohol, no/unknown exercise, and sleep under six hours are adverse signals; multiple adverse signals are high risk, one meaningful signal is medium, and no meaningful signals are low.
- Raise overall risk for high lifestyle risk, recent hospitalization, risk flags, high medication burden, or multiple serious chronic conditions such as CKD, diabetes, COPD, CAD, or hypertension.
- Add `overall_risk_high` when overall risk is high.
- Use `rejected` for hard access failures such as expired/excluded coverage or invalid PBM. Use `clinical_review` for high overall risk without a hard rejection. Use `hold` for remediable pending/missing/contact/pharmacy blockers. Use `approved` only when no blockers remain and risk does not require review.
- Cohort summaries are direct counts from the patient result rows.

## Referral Readiness Rules

For each target referral, join ICD metadata and evaluate code fit, documents/flags, authorization, duplicates, shared insurance, and scheduling state.

Clinical code discrepancies:
- `icd_chapter_mismatch` / service-family mismatch: ICD `service_family` does not match referral `service_line`.
- `narrative_mismatch`: referral reason or diagnosis narrative contradicts the ICD description or service family.
- `laterality_mismatch`: ICD laterality is contradicted or required laterality is missing from the referral narrative when the task asks for laterality review.
- Put any discrepant referral in the discrepancy list with observed ICD chapter and expected service-line chapter/family where the template asks for it.

Document and authorization blockers:
- `missing_records`: `records_received` is false.
- `missing_imaging`: `imaging_received` is false, or required imaging documents are absent/not final when document evidence is requested.
- `auth_blocker` / `authorization_blocked`: `auth_required` is true and `auth_status` is `pending`, `denied`, or `not_submitted`.
- `already_scheduled` / `scheduled_before_clearance`: `appointment_scheduled` is true before readiness is clear.

Duplicates and shared insurance:
- Actual duplicate groups share the same patient plus the same insurance/referring contact/clinical intent, or have an explicit duplicate-practice signal. Choose the lowest/referring-primary referral as the keep/primary record and consolidate later duplicates.
- Shared insurance anomalies are same `insurance_id` across different patients inside the target batch; recommend verifying distinct patient policy IDs. Do not treat these as duplicate groups unless patient identity also matches.
- If rows are only marked possible duplicates but patient and insurance differ, clear duplicate review rather than grouping them.

Readiness and actions:
- `ready`: no code, document, authorization, duplicate, insurance, or schedule issue remains.
- `blocked`: missing records/imaging or authorization blockers prevent scheduling.
- `under_review`: clinical code discrepancy or shared-insurance anomaly requires review.
- `admin_followup`: duplicate consolidation or already-scheduled review is the remaining issue.
- Ready-to-schedule lists include only unscheduled referrals with no blockers; keep duplicate primary records only if otherwise clear.
- Use urgency and issue severity for priority: urgent clinical/auth/records blockers are `tier_1_immediate`; routine clinical/auth/records blockers are `tier_2_short_term`; duplicate, shared-insurance, and already-scheduled administrative work is `tier_3_administrative` unless the template’s priority wording says otherwise.
- Map issue codes to action/correspondence codes directly: corrected ICD/code clarification for clinical code issues, request records/imaging, resolve authorization, consolidate duplicates, verify insurance ID, and review existing appointments.
- Summary counts are calculated from the final per-referral statuses and issue sets.

## Dialysis Transfer Rules

For each transfer in the target batch, join packet `documents`, `patients`, and capacity for the transfer modality.

Packet completeness:
- A required packet document is present only when a row exists for the transfer, the `doc_type` is required by the template, and `finalized` is true with final status.
- Draft/non-final rows count as missing for completeness.
- Return missing document codes alphabetically.

Freshness:
- Check freshness only for the doc types listed by the template. Compare the final document `received_date` to the requested start date.
- Use these standard limits unless the prompt/template gives different limits: `monthly_labs` 30 days; `hbsag` 90 days; `hep_b_antibody_core` 180 days; `history_physical` 180 days; `ppd_or_cxr` 365 days.
- A final document older than its limit is stale even if it is not missing. Return stale documents ordered by `doc_type`.

Capacity and intake decision:
- Sum `facility_capacity.open_chairs` for the requested start date and modality. If no matching row exists, treat open chairs as zero and capacity as unavailable.
- `available` means total open chairs is greater than zero; otherwise `unavailable`.
- Feasibility:
  - `ready_on_requested_start`: complete packet, no stale required freshness items, and capacity available.
  - `packet_not_ready_capacity_available`: missing/stale packet items and capacity available.
  - `packet_not_ready_capacity_unavailable`: missing/stale packet items and no capacity.
  - `capacity_unavailable`: packet ready but no capacity.
- Final decision: `accept` only for ready-on-requested-start, `hold` for administrative packet/capacity gaps, and `clinical_review` when stale clinical/infection-control documents require nurse review.
- Next contact: `clinical_nurse` for stale clinical/freshness review, `intake_coordinator` for missing packet documents, `scheduling_coordinator` for capacity-only holds, and `none` when accepted. Use fax to referring facility for document requests, internal queue for scheduling/clinical routing, and none when no contact is needed.
- Cohort summaries are direct counts from the transfer rows.

## Chronic-Care Enrollment Rules

For each current program candidate, join patient, chart artifacts, and clinical history.

Eligibility:
- Candidate must target the program condition, have an active chart, signed consent, active/current required chart artifacts, and chronic history supporting the diagnosis.
- For DM/HTN programs, require both diabetes and hypertension evidence in active problems or clinical history.
- Add normalized reason codes:
  - `meets_dmhtn_criteria` when the condition evidence is present.
  - `wrong_target_condition` when candidate target condition does not match the program.
  - `missing_active_dmhtn_diagnosis` when condition evidence is absent.
  - `consent_declined` or `consent_missing` from candidate consent.
  - `chart_not_active` when no active chart exists.
  - `stale_active_problems` when active problems exist but are stale.
  - `missing_recent_vitals`, `missing_recent_labs`, and `missing_medication_list` for absent or stale required artifacts.

Disposition and cadence:
- `enroll` only when eligible.
- `hold` for remediable missing consent/chart/artifact issues when the target condition is correct.
- `reject` for declined consent, wrong target condition, or absent target diagnosis.
- Use high-touch `weekly` cadence for recent hospitalization, recent ED risk flags, or low adherence. Use `biweekly` for CKD without higher priority. Use `monthly` for standard eligible candidates. Use `deferred` for holds and `none` for rejects.
- Outreach channel is the candidate/patient preferred outreach when action is needed and contact data supports it; otherwise `none`.

Monitoring package:
- `high_touch_dm_htn` for weekly high-touch enrollments; `standard_dm_htn` for monthly/biweekly enrollments; `deferred` for holds; `not_applicable` for rejects.
- Standard components include BP cuff, glucometer, lab order, medication reconciliation, and care plan setup. Add consent packet and chart update request for holds as needed.
- `first_checkin_days` is shortest for high touch, longer for standard enrollment, and null for deferred/not applicable unless the template specifies exact days.
- Summary counts come from the final patient rows and must include every required zero-valued key.

## Final Validation

Before answering, verify:
- All required keys from the template are present and no extra keys were added.
- Every enum value is allowed by the template.
- All required items from the target roster, batch, transfer set, or program candidate list are included once.
- All ID lists and row lists obey the template ordering.
- All summary counts reconcile exactly to detail rows.
