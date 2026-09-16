# Cedar Ridge Derivation Rules

Use these rules as a reusable checklist. The task template always wins if it uses different controlled values or narrower fields.

## General Schema Discipline

- Normalize IDs exactly as shown by the portal.
- Keep patient/referral/transfer rows in the ordering specified by the template, usually ascending ID.
- Treat reason-code and blocker-code arrays as sets. Include every applicable controlled code and no free text.
- Distinguish absent data from negative data. Missing rows often map to `missing` or a missing-artifact code; present but invalid rows map to an invalid/blocker code.
- After deriving row-level results, calculate counts directly from those rows.

## New Patient Access Verification

Use roster rows for `requested_service_date` and `service_line`. For each target patient, fetch the patient bundle and evaluate coverage, PBM, pharmacy, demographics, contact channels, lifestyle, and clinical history.

Coverage:

- `insurance_status` is `missing` if no coverage row is present.
- It is `valid` only when a coverage row is active, in network, effective on the requested service date, not terminated before that date, and includes the requested service line.
- It is `invalid` for expired/out-of-window coverage, pending status, excluded service line, or other present-but-unusable coverage.
- Add `coverage_expired` for expired or terminated coverage, `coverage_pending` for pending coverage, and `excluded_service_line` when the requested service line is absent from coverage `service_lines`.

Prescription benefits:

- `prescription_status` is `missing` if no PBM row is present.
- It is `valid` only when the PBM is active, approved, covered, and its payer/policy aligns with the selected coverage.
- It is `invalid` for inactive, rejected, pending/review, not-covered, or coverage/PBM policy mismatches.
- Add `pbm_missing`, `pbm_invalid`, or `pbm_policy_mismatch` as appropriate.

Pharmacy:

- Use the preferred pharmacy with the lowest `preference_rank`.
- Map pharmacy `network_status` to `in_network`, `out_of_network`, or `unknown`.
- Add `pharmacy_out_of_network` or `pharmacy_unknown` when applicable.

Administrative blockers:

- Add `missing_address` when the patient address is absent.
- Add `emergency_contact_missing` when `emergency_contact_present` is false.
- Add `preferred_contact_unavailable` when the preferred channel cannot be used: phone or SMS requires a phone number, email requires an email address, and portal should have enough patient/contact context to support portal outreach.

Risk:

- Lifestyle risk is `high` for strong signals such as current smoking, heavy alcohol use, no or missing exercise, or very short sleep. It is `medium` for moderate signals such as former smoking, moderate alcohol, limited exercise, or mildly short sleep. Otherwise use `low`.
- Overall risk is at least lifestyle risk. Escalate to `high` for recent hospitalization, non-empty clinical `risk_flags`, high chronic-condition burden, high medication burden, or any explicitly high-risk clinical signal. Add `overall_risk_high` when the final overall risk is high.

Registration status:

- Use `approved` only when coverage, PBM, pharmacy, demographics, contact, and risk checks have no blockers requiring follow-up.
- Use `rejected` for hard-stop mismatches such as expired coverage or an excluded service line, especially when combined with PBM or administrative blockers.
- Use `clinical_review` for high overall risk, clinical complexity, PBM mismatch, or pharmacy/network problems that require review rather than outright rejection.
- Use `hold` for pending or missing administrative items when the template provides a hold state and no clinical rejection/review rule is stronger.

## Referral Readiness And Chart Activation

For referral batches, collect referrals filtered by `batch_id`, ICD metadata for each `icd10_code`, referral documents, patient rows, and chart data when the template asks for chart activation.

Clinical code discrepancies:

- Compare referral `service_line` with ICD `service_family`. A mismatch is a clinical code discrepancy.
- If the template explicitly asks for `icd_chapter_mismatch`, compare the observed ICD chapter with the specialty's expected chapter. Orthopedic musculoskeletal referrals may expect `M00-M99` even when an injury code is otherwise orthopedic.
- Add `narrative_mismatch` or a clinical-reason mismatch when the referral reason or narrative clearly belongs to another specialty or complaint family.
- Add `laterality_mismatch` only when laterality in ICD metadata conflicts with referral narrative or supporting records.

Operational blockers:

- Add missing-records blockers when `records_received` is false.
- Add missing-imaging blockers when `imaging_received` is false and the template tracks imaging.
- Add authorization blockers when `auth_required` is true and `auth_status` is pending, denied, not submitted, or otherwise not approved.
- Add scheduled-before-clearance or already-scheduled codes when an appointment exists before the referral is otherwise clear.

Duplicates and insurance anomalies:

- Duplicate referral groups are same-patient referrals in the same batch that represent the same intake work. Keep the earliest or lowest referral ID as the primary unless the portal indicates another primary.
- Shared insurance anomalies are repeated insurance IDs across distinct patient IDs. Same patient plus same insurance is normally a duplicate-referral issue, not a distinct-patient insurance anomaly.

Readiness and priority:

- `ready`: no clinical, duplicate, record, imaging, authorization, scheduled-before-clearance, or administrative blocker remains.
- `blocked`: authorization, records, or imaging blockers prevent scheduling. If these coexist with clinical discrepancies, keep the referral blocked and include all blocker codes.
- `under_review`: clinical code/narrative/laterality discrepancies, duplicate review, or existing appointment review without a hard records/auth blocker.
- `admin_followup`: administrative-only issues such as shared insurance verification.
- Use tier 1 for urgent clinical discrepancies or immediate specialty review. Use tier 2 for blocked referrals, routine clinical review, duplicates, and appointment holds. Use tier 3 for administrative-only follow-up.

Action and correspondence mapping:

- Code discrepancy -> corrected ICD or clinical clarification.
- Narrative mismatch -> confirm narrative or clinical reason.
- Laterality mismatch -> confirm laterality.
- Duplicate -> consolidate or duplicate-resolution correspondence.
- Shared insurance -> verify insurance ID.
- Missing records/imaging -> request those materials.
- Authorization denied/pending/not submitted -> resolve authorization.
- Already scheduled or scheduled before clearance -> review existing appointment or appointment-hold notice.

Ready referral chart needs:

- Include only referrals the template considers ready for chart work.
- If no chart exists, use `create_chart` and include required artifacts to create.
- If a chart exists, use `update_chart` for required artifacts that are absent or have `status` other than current.
- Use `no_chart_action` only when every required chart artifact is current.
- Common required chart artifacts are demographics, active problems, medications, allergies, vitals, labs, and consent. Treat stale artifacts as needing creation/update.

## Dialysis Transfer Review

For transfer batches, collect transfer requests, packet documents, patient rows, and facility capacity for each requested start date and modality.

Packet completeness:

- Required documents are controlled by the answer template. A document is present only when its row exists, `finalized` is true, and status is final.
- Draft, unfinalized, or absent required documents belong in `missing_required_documents`.
- `packet_completeness_status` is `complete` when no required documents are missing. Stale documents do not by themselves make the packet incomplete, but they do prevent final acceptance.

Freshness:

- Evaluate freshness against the transfer's requested start date.
- Common freshness limits: `hbsag`, `monthly_labs`, and `ppd_or_cxr` are 30 days; `history_physical` and `hep_b_antibody_core` are 365 days unless the task states otherwise.
- Add a stale document item for each final document older than its limit, including the received date and freshness limit.

Capacity and feasibility:

- Sum `open_chairs` across facility capacity rows for the exact requested start date and modality.
- If no capacity row exists for that exact date/modality, treat open chairs as 0 and capacity as unavailable.
- Feasibility combines packet readiness and capacity: ready on requested start only when no missing/stale packet issue exists and capacity is available; otherwise choose the template value that names packet-not-ready and/or capacity-unavailable.

Decision and contact:

- Accept only when the packet is complete, no stale required clinical documents remain, and capacity is available.
- Hold when packet data is ready but scheduling/capacity is not.
- Use clinical review when packet documents are missing or stale.
- Route packet document requests to the referring facility, usually owned by a clinical nurse. Use scheduling ownership for capacity-only issues and `none` when no follow-up is needed.

## Chronic-Care Enrollment Panels

For program panels, use the current candidates returned for the requested program. Do not filter candidates out unless the prompt or endpoint explicitly says to do so. Fetch each candidate's chart and clinical history.

Eligibility:

- A diabetes/hypertension program generally requires target condition `diabetes_hypertension` plus active diabetes and hypertension in clinical history.
- Wrong target condition or missing active target diagnoses makes the candidate ineligible.
- Lack of an active chart or declined/missing consent can change enrollment status even when clinical eligibility is true.

Reason codes:

- Add the meets-criteria code for clinically eligible target-condition candidates.
- Add recent-hospitalization high-touch for recent hospitalization.
- Add recent-ED high-touch for a recent ED risk flag.
- Add low-adherence high-touch for low adherence when no stronger high-touch reason already explains the cadence.
- Add CKD biweekly monitoring for CKD candidates who do not have a weekly high-touch reason.
- Add consent declined or missing, chart-not-active, stale active-problems, and missing recent vitals/labs/medications/consent from candidate, patient, and chart-artifact data.
- For wrong-condition candidates, keep the focus on target-condition rejection. Add consent or chart-not-active codes only when the template pattern expects those administrative facts as secondary reasons.

Enrollment status and cadence:

- `enroll`: eligible target condition, consent signed, active chart, and required chart artifacts current enough for enrollment.
- `hold`: otherwise eligible but blocked by missing consent or chart/update artifacts.
- `reject`: wrong target condition, missing active target diagnosis, consent declined, or inactive chart when the template treats those as rejection.
- Weekly cadence for high-touch candidates, biweekly for CKD monitoring, monthly for standard enrolled candidates, deferred for holds, and none for rejects.

Outreach:

- Start with candidate `preferred_outreach`.
- Validate the channel: phone or SMS needs a phone number, email needs an email address, and portal usually requires an active chart/portal-capable patient.
- If the preferred channel is unavailable, fall back to the patient preferred contact or another available channel allowed by the template.

Monitoring packages:

- High-touch package: BP cuff, glucometer, lab order, medication reconciliation, care plan setup, first check-in in 7 days.
- CKD/biweekly standard package: BP cuff, glucometer, lab order, medication reconciliation, first check-in in 14 days.
- Monthly standard package: BP cuff, glucometer, lab order, first check-in in 30 days.
- Deferred package: consent packet and chart update request, no first check-in date.
- Not-applicable package: empty components and null first check-in.
