---
name: cedar-ridge-intake-coordination
description: Produce schema-compliant JSON answers for Cedar Ridge Intake Coordination Portal tasks. Use when a task asks Codex to reconcile portal data for new-patient access verification, specialty referral readiness or chart activation, dialysis transfer packet and capacity review, or chronic-care program enrollment panels using TASK_ENV_BASE_URL and an answer_template.json.
---

# Cedar Ridge Intake Coordination

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract: required keys, allowed enum values, ordering, nullability, and count keys come from the current task.
2. Read any other payload files in `input/payloads/`. Use payload IDs, roster IDs, batch IDs, program codes, requested dates, and patient/referral/transfer lists from the current task only.
3. Get the base URL from the task or environment access instructions. Use the portal endpoints and, when helpful, the read-only SQL endpoint:
   - `GET /patients`, `/patients/{patient_id}`
   - `GET /referrals?batch_id=...`, `/referrals/{referral_id}`
   - `GET /transfers?batch_id=...`, `/transfers/{transfer_id}`
   - `GET /documents`
   - `GET /chart/{patient_id}`
   - `GET /programs/{program_code}/candidates`
   - `GET /icd/{code}`
   - `GET /pharmacies`
   - `POST /query` with `{"sql":"SELECT ..."}`
4. Prefer one SQL query per workflow to join relevant tables, then spot-check with resource endpoints if a field is ambiguous. Useful tables are `patients`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`, `clinical_history`, `intake_rosters`, `referrals`, `icd_codes`, `documents`, `transfer_requests`, `facility_capacity`, `program_candidates`, and `chart_artifacts`.
5. Build the JSON directly from current portal rows. Do not reuse identifiers, dates, counts, patient decisions, or other answer values from examples.
6. Sort every list exactly as the template says. Treat code arrays marked as unordered sets as de-duplicated arrays; use a stable order that matches the template or business flow.
7. Return JSON only when the task requests JSON only. Include all required zero-count keys and empty arrays.

## New-Patient Access Verification

Use for roster-based primary care or intake verification tasks.

Data to collect per target patient:
- `intake_rosters`: requested service date and service line.
- `patients`: address, phone, email, preferred contact, emergency contact.
- `coverage`: payer, policy, status, effective/termination dates, service lines.
- `pbm`: active flag, status, formulary status, policy number.
- `patient_pharmacy` joined to `pharmacies`: preferred pharmacy network status.
- `lifestyle` and `clinical_history`: risk factors.

Normalize statuses:
- `insurance_status`: `valid` only when a coverage row exists, status is active, the requested service date is within the effective/termination window, and the requested service line is listed. Use `missing` if no coverage row exists; otherwise use `invalid`.
- `prescription_status`: `valid` only when a PBM row exists, is active, status is approved, formulary is covered, and the PBM policy matches the coverage policy when both are present. Use `missing` when no PBM row exists; otherwise use `invalid`.
- `pharmacy_status`: use the rank-1 preferred pharmacy. Map the joined pharmacy network status to `in_network` or `out_of_network`; use `unknown` if no preferred pharmacy or no pharmacy match exists.

Blocked reason mapping:
- Coverage expired before the service date: `coverage_expired`.
- Coverage pending: `coverage_pending`.
- Requested service line absent from coverage service lines: `excluded_service_line`.
- No address: `missing_address`.
- No emergency contact: `emergency_contact_missing`.
- No PBM row: `pbm_missing`.
- PBM rejected, inactive, pending, review, or not found: `pbm_invalid`.
- PBM policy/payer mismatch with coverage: `pbm_policy_mismatch`.
- Preferred pharmacy out of network: `pharmacy_out_of_network`.
- Pharmacy cannot be resolved: `pharmacy_unknown`.
- Preferred contact is unusable: `preferred_contact_unavailable`. Treat `phone` and `sms` as requiring a phone number, `email` as requiring an email address, and `portal` as requiring portal availability from an active chart or portal-capable patient context.
- Overall risk high: `overall_risk_high`.

Risk scoring:
- Lifestyle risk is `high` for current smoking, heavy alcohol use, no exercise/missing exercise, or very short sleep. Use `medium` for former smoking, moderate alcohol, limited exercise, or borderline sleep. Use `low` when risk factors are absent.
- Overall risk is the maximum of lifestyle and clinical/admin risk. Raise to `high` for high lifestyle risk, recent hospitalization, explicit clinical risk flags, complex medication burden, or multiple serious chronic conditions. Raise to at least `medium` for moderate lifestyle risk, moderate medication burden, or multiple chronic conditions.

Registration status:
- `approved`: no blocked reasons and overall risk is not high.
- `hold`: administrative or pending items only, with no hard coverage exclusion and no high clinical risk.
- `clinical_review`: high overall risk, PBM/pharmacy problems, or missing/stale clinical context when not outright rejected.
- `rejected`: hard coverage blockers such as expired coverage or excluded service line, especially when combined with PBM mismatch/invalidity or other critical blockers.

Summaries are simple integer counts over the generated patient rows.

## Specialty Referral Readiness And Activation

Use for batch referral audits and referral-to-chart activation tasks.

Data to collect:
- Referrals in the target batch.
- ICD metadata for each `icd10_code`.
- Patient rows and chart artifacts for each referral patient when chart activation is requested.
- Documents only if the current task/template asks for document-level support; referral flags usually provide records/imaging receipt.

Clinical code discrepancy rules:
- Wrong service family: ICD metadata `service_family` does not match the referral `service_line`.
- Chapter mismatch: the ICD chapter is outside the expected chapter range for the service line when the task asks for chapter checks. Common expected chapters: orthopedics `M00-M99`, pulmonary `J00-J99`, cardiology `I00-I99`. Use ICD metadata as the observed chapter.
- Narrative mismatch: the referral reason or diagnosis narrative conflicts with the ICD/service family, such as pain-oriented reasons for pulmonary codes. Use the template's task-specific code names, for example `narrative_mismatch` or `clinical_reason_mismatch`.
- Laterality mismatch: ICD laterality conflicts with laterality stated in referral reason, diagnosis text, notes, or attached documents.

Referral blocker mapping:
- Records flag false: `missing_records` or `records_missing`.
- Imaging flag false: `missing_imaging` or `imaging_missing`.
- Authorization required with status other than approved/not_required: `auth_blocker` or `authorization_blocked`.
- Appointment already scheduled before clearance: `already_scheduled` or `scheduled_before_clearance`.
- Duplicate referral: same batch/service line/patient and substantially same referral details; keep the lowest or earliest referral as primary.
- Shared insurance anomaly: same insurance ID appears for different patients in the batch. Same patient duplicates are legitimate duplicate handling, not a cross-patient anomaly.

Readiness status:
- `ready`: no blockers or discrepancies.
- `blocked`: records, imaging, or authorization blockers are present.
- `under_review`: clinical code discrepancy, duplicate review, or appointment-before-clearance is present without hard records/auth/imaging blockers.
- `admin_followup`: only administrative issues such as shared insurance verification are present.

Priority/action guidance:
- Tier 1: urgent clinical discrepancy or urgent safety/clearance issue.
- Tier 2: routine clinical discrepancies, duplicate consolidation, scheduled-before-clearance review, and hard records/auth/imaging blockers.
- Tier 3: administrative-only follow-up such as shared insurance verification.
- For action plans, map issues to the template's action enums: corrected ICD/code clarification, narrative confirmation, laterality confirmation, duplicate consolidation, insurance verification, records request, imaging request, authorization resolution, or existing-appointment review.
- For priority-order lists, rank tier 1 first; within a tier, put scheduled-before-clearance and multi-issue clinical cases before single clinical discrepancies, then operational blockers, then sort stably by referral ID.

Chart activation for ready referrals:
- Consider only referrals whose readiness is `ready`.
- Required chart artifacts are the template's artifact enum set, commonly demographics, active problems, medications, allergies, vitals, labs, and consent.
- If no chart exists, `chart_action` is `create_chart` and all required artifacts are needed unless current finalized chart artifacts explicitly exist.
- If a chart exists, `chart_action` is `update_chart` when any required artifact is missing or has status other than current; otherwise use `no_chart_action`.
- `artifacts_to_create` contains missing or stale required artifacts, sorted as the template specifies.

Correspondence queue guidance:
- Use clinical-code templates for isolated service-family, chapter, reason, narrative, or laterality discrepancies.
- Use auth/records templates when authorization or records are the main blockers.
- Use duplicate-resolution templates for duplicate review.
- Use appointment-hold templates when a scheduled appointment exists before clearance; include the scheduled reason plus other unresolved blocker reasons required by the template.

## Dialysis Transfer Packet And Capacity Review

Use for seasonal dialysis transfer batches and requested-start feasibility.

Data to collect:
- Transfer requests in the batch.
- Final transfer-packet documents for each transfer.
- Facility capacity rows for each requested start date and modality.

Document completeness:
- A required document counts as present only when `documents.status` is final and `finalized` is true for that transfer.
- Draft or absent required documents are missing.
- If the template includes `transportation` as a required item, satisfy it from the transfer request's transportation field; missing/null transportation maps to missing `transportation`.
- Sort missing document codes alphabetically.

Freshness checks:
- Check freshness against the requested start date, not the current date.
- Common freshness limits are: `hbsag` 30 days, `monthly_labs` 30 days, `ppd_or_cxr` 30 days, `history_physical` 365 days, and `hep_b_antibody_core` 365 days.
- Include stale document entries only for finalized documents whose age is greater than the limit. Use the document's received date and the limit from the rule/template.
- Sort stale entries by `doc_type`.

Capacity and decisions:
- Sum `facility_capacity.open_chairs` across locations for the exact requested start date and modality. Missing capacity rows mean zero open chairs.
- `capacity_status` is `available` when summed open chairs are greater than zero; otherwise `unavailable`.
- Feasibility:
  - Documents complete, no stale documents, and capacity available: `ready_on_requested_start`.
  - Packet not ready and capacity available: `packet_not_ready_capacity_available`.
  - Packet not ready and capacity unavailable: `packet_not_ready_capacity_unavailable`.
  - Packet ready but capacity unavailable: `capacity_unavailable`.
- Final decision:
  - Ready packet and capacity available: `accept`, owner/route `none`.
  - Any stale clinical document: `clinical_review`, owner `clinical_nurse`, route `fax_referring_facility`.
  - Missing documents without stale clinical items: `hold`, usually owner `intake_coordinator`, route `fax_referring_facility`.
  - Capacity-only blocker: `hold`, usually owner `scheduling_coordinator`, route `internal_queue`.

Summaries count transfers with complete required documents before freshness, transfers with any missing document, transfers with any stale document, transfers with capacity available, transfers ready on requested start, decision counts, and owner counts.

## Chronic-Care Program Enrollment

Use for program candidate panels such as diabetes/hypertension chronic-care enrollment.

Data to collect:
- `GET /programs/{program_code}/candidates`.
- Patient and chart records for each candidate.
- `clinical_history` for diagnoses, recent hospitalization, medication burden, and risk flags.
- `chart_artifacts` for active problems, vitals, labs, medications, consent, and other template-required artifacts.

Eligibility and disposition:
- `eligible` means the candidate matches the program target condition and clinical history supports the required condition set. For diabetes/hypertension, require both diabetes and hypertension and reject wrong target conditions.
- `enroll`: eligible target condition, consent signed, active chart, and required artifacts current.
- `hold`: eligible target condition but consent is missing, chart is inactive, or required chart artifacts need repair without a hard decline.
- `reject`: wrong target condition or consent declined. Include chart-not-active reasons for target-condition-eligible candidates with inactive charts; for wrong-target candidates, keep chart artifact work empty unless the template explicitly asks otherwise.

Reason codes:
- Add `meets_dmhtn_criteria` for eligible diabetes/hypertension candidates who can proceed to enrollment.
- Recent hospitalization takes precedence as `recent_hospitalization_high_touch`.
- Low adherence can add `low_adherence_high_touch` when no higher-priority high-touch reason applies.
- Recent ED risk flags add `recent_ed_high_touch`.
- CKD adds `ckd_biweekly_monitoring` when no weekly high-touch reason applies.
- Consent declined or missing maps to `consent_declined` or `consent_missing`.
- Inactive chart maps to `chart_not_active`.
- Stale active problems map to `stale_active_problems`.
- Missing or stale vitals, labs, and medication artifacts map to `missing_recent_vitals`, `missing_recent_labs`, and `missing_medication_list`.
- Wrong target condition maps to `wrong_target_condition` and `missing_active_dmhtn_diagnosis` for diabetes/hypertension programs.

Missing chart artifacts:
- For eligible candidates, include `chart_record` when the patient has no active chart.
- Include each required chart artifact that is missing or not current, using the template's allowed names.
- For wrong-target candidates, leave missing chart artifacts empty unless the prompt asks for activation work anyway.

Cadence and monitoring:
- Weekly for high-touch reasons such as recent hospitalization, low adherence, or recent ED.
- Biweekly for CKD monitoring when not weekly.
- Monthly for standard eligible enrollment.
- Deferred for holds, none for rejects.
- High-touch package: `high_touch_dm_htn`, components for BP cuff, glucometer, A1c/CMP/lipid lab order, medication reconciliation, and care-plan setup; first check-in 7 days.
- Standard biweekly CKD package: `standard_dm_htn`, BP cuff, glucometer, lab order, medication reconciliation; first check-in 14 days.
- Standard monthly package: `standard_dm_htn`, BP cuff, glucometer, lab order; first check-in 30 days.
- Hold package: `deferred`; include consent packet and/or chart update request components according to the blockers; first check-in null.
- Reject package: `not_applicable`, empty components, first check-in null.

Outreach channel:
- Prefer the candidate's preferred outreach when usable.
- Usability rules: phone and sms require a phone number, email requires an email address, and portal requires an active portal/chart context.
- If preferred outreach is unusable, fall back to patient preferred contact if usable, then any available phone/email/sms channel. Use `none` only if no allowed channel works.

## Final Validation

Before answering:
- Verify every output key is present and no extra prose is included when JSON-only is requested.
- Recompute summary counts from generated rows rather than entering them manually.
- Check all enum strings against the current template.
- Check all required list ordering.
- Ensure dates come from current portal rows, the current task, or allowed environment metadata.
