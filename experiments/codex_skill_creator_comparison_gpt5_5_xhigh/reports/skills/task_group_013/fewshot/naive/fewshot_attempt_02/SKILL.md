---
name: cedar-ridge-intake-json
description: Solve Cedar Ridge Intake Coordination Portal tasks that require JSON-only healthcare intake outputs, including new-patient access verification, specialty referral readiness audits, dialysis transfer packet/capacity reviews, chronic-care enrollment panels, and referral-to-chart activation files. Use when the prompt names the Cedar Ridge portal, a task environment base URL, and an answer_template.json with controlled output values.
---

# Cedar Ridge Intake JSON

Use the portal data as the source of truth and the provided `input/payloads/answer_template.json` as the output contract. Return exactly one JSON object and no prose.

## First Pass

1. Read the prompt and template. Extract the task family, identifiers, required top-level keys, controlled values, and ordering rules.
2. Replace `<TASK_ENV_BASE_URL>` with the actual base URL from the prompt or environment access notes.
3. Pull only records related to the requested roster, batch, program, transfer IDs, referral IDs, and linked patient IDs.
4. Prefer `/query` with read-only `SELECT` statements for joins and grouping. The useful tables are:
   `patients`, `intake_rosters`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`, `clinical_history`, `referrals`, `icd_codes`, `documents`, `transfer_requests`, `facility_capacity`, `chart_artifacts`, and `program_candidates`.
5. Build results in the exact template shape. Include required keys with zero counts or empty arrays when no records qualify.
6. Recompute summaries from the per-item rows after all statuses are assigned. Validate counts and ordering before answering.

Never call judge/evaluator endpoints. Do not infer from distractor records outside the requested identifiers.

## Query Patterns

Use placeholders, not literal examples:

```sql
-- Roster access verification
SELECT r.*, p.*, c.status AS coverage_status, c.effective_date, c.termination_date,
       c.network_status, c.service_lines,
       pb.status AS pbm_status, pb.active AS pbm_active, pb.formulary_status,
       pb.specialty_required,
       pp.pharmacy_id, ph.network_status AS pharmacy_network_status,
       l.smoking_status, l.alcohol_use, l.exercise_frequency, l.sleep_hours,
       ch.recent_hospitalization, ch.risk_flags
FROM intake_rosters r
JOIN patients p ON p.patient_id = r.patient_id
LEFT JOIN coverage c ON c.patient_id = r.patient_id
LEFT JOIN pbm pb ON pb.patient_id = r.patient_id
LEFT JOIN patient_pharmacy pp
  ON pp.patient_id = r.patient_id AND pp.preference_rank = 1
LEFT JOIN pharmacies ph ON ph.pharmacy_id = pp.pharmacy_id
LEFT JOIN lifestyle l ON l.patient_id = r.patient_id
LEFT JOIN clinical_history ch ON ch.patient_id = r.patient_id
WHERE r.roster_id = :roster_id
ORDER BY r.patient_id;
```

```sql
-- Referral batch with ICD metadata
SELECT r.*, i.description AS icd_description, i.chapter, i.service_family, i.laterality
FROM referrals r
LEFT JOIN icd_codes i ON i.code = r.icd10_code
WHERE r.batch_id = :batch_id
ORDER BY r.referral_id;
```

```sql
-- Transfer packet and capacity
SELECT t.*, d.doc_type, d.status, d.finalized, d.received_date
FROM transfer_requests t
LEFT JOIN documents d ON d.transfer_id = t.transfer_id
WHERE t.batch_id = :batch_id
ORDER BY t.transfer_id, d.doc_type;

SELECT t.transfer_id, COALESCE(SUM(fc.open_chairs), 0) AS open_chairs_total
FROM transfer_requests t
LEFT JOIN facility_capacity fc
  ON fc.date = t.requested_start_date AND fc.modality = t.modality
WHERE t.batch_id = :batch_id
GROUP BY t.transfer_id
ORDER BY t.transfer_id;
```

For program panels, start with `GET /programs/{program_code}/candidates`, then query `clinical_history` and `chart_artifacts` for those patient IDs.

## Access Verification

Use this for new-patient roster tasks.

Coverage:
- `valid`: an active coverage row, in network, requested service date within effective/termination bounds, and requested service line included in `service_lines`.
- `missing`: no coverage row.
- `invalid`: any present row that fails the validity test.
- Reason codes: expired coverage -> `coverage_expired`; pending coverage -> `coverage_pending`; requested service line absent -> `excluded_service_line`.

Prescription benefit:
- `valid`: PBM row is active and approved.
- `missing`: no PBM row.
- `invalid`: inactive, rejected, pending/review, not found, or a policy/service mismatch.
- Reason codes: no PBM -> `pbm_missing`; rejected/pending/review/not-found -> `pbm_invalid`; active policy that conflicts with the requested service or required benefit rules -> `pbm_policy_mismatch`.

Pharmacy:
- Use the rank-1 preferred pharmacy. Map its `network_status` to `in_network` or `out_of_network`.
- If no preferred pharmacy or no pharmacy status is available, use `unknown`.
- Reason codes: `pharmacy_out_of_network` or `pharmacy_unknown`.

Demographic/contact reason codes:
- `missing_address` when address is null/blank.
- `preferred_contact_unavailable` when the preferred channel has no usable value: phone/sms require phone, email requires email, portal generally requires an existing chart/portal-capable record.
- `emergency_contact_missing` when the emergency contact flag is false.

Lifestyle risk:
- `high` if any high-risk signal is present: current smoking, heavy alcohol use, no/unknown exercise, sleep under 6 hours, recent hospitalization, or strong risk flags.
- `medium` if moderate risk remains without a high-risk signal: former smoking, moderate alcohol use, borderline sleep, elevated medication burden, or mild flags.
- `low` only when lifestyle fields are reassuring and no clinical flags are present.

Overall risk and registration:
- `overall_risk` is `high` if lifestyle risk is high or any serious blocker exists: invalid/missing coverage, excluded service line, invalid/mismatched PBM, out-of-network/unknown pharmacy, missing address/contact/emergency contact, recent hospitalization, or high-risk clinical flags.
- Use `medium` for medium lifestyle or repairable noncritical issues; otherwise `low`.
- `registration_status` precedence: `rejected` for excluded service line or nonrepairable coverage; `clinical_review` for high overall risk, PBM/pharmacy blockers, or clinical/demographic safety concerns; `hold` for repairable administrative pending/missing items only; `approved` when no blockers remain.
- Add `overall_risk_high` whenever `overall_risk` is `high`.

## Referral Readiness

Use this for specialty referral audits and referral-to-chart activation.

Clinical code checks:
- Join each referral to `icd_codes`.
- Flag service-family mismatch when `icd_codes.service_family` does not match the referral `service_line`.
- For orthopedic audits that ask for ICD chapter mismatches, expect musculoskeletal `M00-M99`; injury/poisoning or other chapters are discrepancies even when the service family is orthopedics.
- Flag narrative/clinical reason mismatch when the referral reason or diagnosis narrative is incompatible with the ICD/service family, such as a musculoskeletal pain reason attached to a pulmonary activation.
- Flag laterality mismatch only when both the ICD metadata and referral narrative mention conflicting sides.
- Put observed and expected chapters in discrepancy objects when the template requests them.

Operational blockers:
- `missing_records` or `records_missing`: `records_received = 0`.
- `missing_imaging` or `imaging_missing`: `imaging_received = 0`.
- `auth_blocker` or `authorization_blocked`: `auth_required = 1` and `auth_status` is `pending`, `denied`, or `not_submitted`.
- `already_scheduled` or `scheduled_before_clearance`: appointment already scheduled while other clearance issues remain.

Duplicates and insurance anomalies:
- Duplicate referrals are same-patient repeated referrals in the same batch with matching clinical/request details. Keep the earliest or lowest referral ID as primary; recommend consolidation.
- Same insurance ID across different patient IDs is a shared-insurance anomaly; disposition should verify distinct patient policy ID.
- A note like "possible duplicate" is not enough by itself; if no same-patient duplicate group exists, list it as cleared when the template has a cleared-duplicates field.

Readiness status:
- `ready`: no clinical discrepancy, duplicate issue, admin anomaly, authorization/document blocker, or premature appointment blocker.
- `blocked`: authorization, records, or imaging blockers are present. Keep `blocked` even if clinical issues are also present.
- `under_review`: clinical code/narrative/laterality discrepancy, duplicate review, or already-scheduled review without hard document/auth blockers.
- `admin_followup`: only administrative anomalies such as shared insurance and no clinical/document/auth blocker.

Actions, correspondence, and priority:
- Map code discrepancies to `request_corrected_icd`, `confirm_narrative`, or `confirm_laterality`; map duplicates to `consolidate_duplicate`; shared insurance to `verify_insurance_id`; records/imaging/auth to `request_records`, `request_imaging`, and `resolve_authorization`; appointments to `review_existing_appointment`.
- Correspondence template precedence: appointment hold notice first, then duplicate resolution, then combined auth/records request, then clinical code clarification.
- Use `wrong_service_family` for ICD service-family mismatch and `clinical_reason_mismatch` for narrative mismatch when the template uses those reason codes.
- Priority tiers: urgent clinical discrepancies -> `tier_1_immediate`; routine clinical, duplicate, appointment, auth, records, or imaging issues -> `tier_2_short_term`; admin-only insurance follow-up -> `tier_3_administrative`.
- For priority-ordered lists, include only non-ready referrals. Sort by tier, then urgent before routine, then scheduled/multiple blockers, clinical discrepancies, auth/document blockers, duplicate/admin work, and finally referral ID.

Chart activation:
- Chart gaps are reported for referrals that are otherwise ready; they do not make the referral non-ready.
- Required activation artifacts are the template's chart artifacts. Create/update every missing or non-current required artifact.
- `chart_action`: `create_chart` when no chart exists, `update_chart` when a chart exists but artifacts are missing/stale, otherwise `no_chart_action`.

## Dialysis Transfers

Use this for seasonal dialysis transfer reviews.

Packet completeness:
- Required packet items are the document codes in the answer template plus any non-document fields listed there, such as transportation.
- A document counts as present only when `status = 'final'` and `finalized = 1`.
- Draft, missing, or null transportation values are missing required items.
- `packet_completeness_status` is `complete` when all required items are present, even if some freshness-limited documents are stale.

Freshness:
- Compare `received_date` to the requested start date for that transfer.
- Use 30 days for `hbsag`, `monthly_labs`, and `ppd_or_cxr`.
- Use 365 days for `history_physical` and `hep_b_antibody_core` when the template asks for those stale document types.
- Include stale document objects with the document type, received date, and freshness limit. Sort by doc type.

Capacity and decision:
- Sum `facility_capacity.open_chairs` across all locations for the requested date and modality. Treat no rows as zero.
- `capacity_status` is `available` when open chairs total is greater than zero; otherwise `unavailable`.
- Feasibility values combine packet readiness and capacity:
  `ready_on_requested_start`, `packet_not_ready_capacity_available`, `packet_not_ready_capacity_unavailable`, or `capacity_unavailable`.
- `final_intake_decision`: `accept` only when documents are complete, freshness passes, and capacity is available; `hold` when packet is ready but capacity is unavailable; `clinical_review` when required or freshness-limited clinical packet items are missing/stale.
- Contact routing: missing/stale packet items go to `clinical_nurse` via `fax_referring_facility`; capacity-only holds go to scheduling/internal routing if the template allows it; accepted rows use `none`.

## Chronic-Care Program Panels

Use this for program candidate enrollment outputs.

Data and dates:
- Include every current candidate returned by `/programs/{program_code}/candidates`; do not filter out candidates unless the prompt explicitly says to.
- Use the program/report as-of date from the prompt or portal metadata when available. Do not use individual `candidate_date` values as the panel `as_of_date` unless the template says so.

Eligibility and reasons:
- Determine the target condition from the program and candidate. For diabetes-hypertension programs, eligibility requires the diabetes-hypertension target and active diabetes plus hypertension in clinical history.
- `eligible` means condition eligibility only; consent declined or inactive chart can still produce `eligible: true` with a reject disposition.
- Add `meets_dmhtn_criteria` for eligible diabetes-hypertension candidates when that code is allowed.
- Add `wrong_target_condition` and `missing_active_dmhtn_diagnosis` for candidates whose target/active diagnoses do not match.
- Add `consent_declined` or `consent_missing` from candidate consent, but suppress repairable missing-consent/chart-maintenance codes for already ineligible rejects unless declined consent or inactive chart is explicitly important.
- Add `chart_not_active` when no active/existing chart is available.
- Add stale/missing chart artifact codes from `chart_artifacts`: stale active problems -> `stale_active_problems`; no current vitals/labs/medications/consent -> `missing_recent_vitals`, `missing_recent_labs`, `missing_medication_list`, `consent`.

Disposition and cadence:
- `reject`: ineligible target/diagnosis or declined consent.
- `hold`: eligible but consent is missing or the chart/artifacts need repair before enrollment.
- `enroll`: eligible, signed consent, active chart, and required artifacts current enough.
- `weekly`: recent hospitalization, recent ED risk flag, or low adherence.
- `biweekly`: CKD/renal comorbidity without weekly triggers.
- `monthly`: standard eligible enrollment.
- `deferred`: holds.
- `none`: rejects.

Outreach and monitoring:
- Prefer the candidate's outreach channel when it is allowed and usable. If it is unavailable, fall back to the patient preferred contact with usable data; portal requires an active chart, phone/sms require phone, and email requires email. Use `none` only when no allowed route works.
- High-touch package: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`, `medication_reconciliation`, and `care_plan_setup`, with first check-in at 7 days.
- Standard CKD/biweekly package: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`, and `medication_reconciliation`, with first check-in at 14 days.
- Standard monthly package: `bp_cuff`, `glucometer`, and `lab_order_a1c_cmp_lipid`, with first check-in at 30 days.
- Holds use a deferred package with `consent_packet` and/or `chart_update_request` as applicable and null first check-in.
- Rejects use `not_applicable`, no components, and null first check-in.

## Final Validation

Before returning:
- Sort arrays exactly as the template specifies.
- Keep reason-code/blocker-code arrays as sets, preferably in stable alphabetical or logical order.
- Ensure all enum strings come from the template.
- Count from the final item rows, not from intermediate queries.
- Include zero-valued keys required by summary count objects.
- Emit strict JSON only.
