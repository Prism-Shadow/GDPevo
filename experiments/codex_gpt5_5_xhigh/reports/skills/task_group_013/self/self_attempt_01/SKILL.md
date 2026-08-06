---
name: cedar-ridge-intake-coordination
description: Reconcile Cedar Ridge Intake Coordination Portal data into schema-constrained JSON for patient access verification, referral readiness or chart activation, dialysis transfer packet and capacity review, and chronic-care enrollment panels. Use when a task references Cedar Ridge intake rosters, referral batches, transfer batches, program candidates, patients or charts, ICD metadata, documents, pharmacies, or the portal endpoints.
---

# Cedar Ridge Intake Coordination

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Treat the template as the authority for required keys, allowed enum values, output ordering, and count buckets.
2. Read `environment_access.md` before any network access. Use only the listed base URL and endpoints. No credentials are required unless that file says otherwise.
3. Query narrowly by the target roster, batch, program code, transfer IDs, referral IDs, and patient IDs. Ignore distractor rows outside the target scope.
4. Prefer `POST /query` with read-only `SELECT` statements for joins across portal tables. Use detail endpoints such as `/patients/{patient_id}`, `/referrals/{referral_id}`, `/transfers/{transfer_id}`, `/chart/{patient_id}`, and `/icd/{code}` when nested evidence is useful.
5. Produce exactly one JSON object matching the template. Do not include prose outside JSON when the task asks for JSON only.

## Output Discipline

- Use controlled values exactly as listed in the task template. Do not invent reason codes, statuses, owners, routes, or package components.
- Include all required keys and all required summary count buckets, even when a count is zero.
- Sort lists exactly as the template specifies. Treat reason-code arrays and blocker-code arrays as unordered sets unless the template gives an order.
- Count patients, referrals, transfers, and issues from the final in-scope output rows, not from all portal data.
- Treat integer flags `0` and `1` as booleans. Treat document presence as valid only when the document is finalized and its status is final.

## Data Sources

Use these joins as the default evidence map:

- Roster access verification: `intake_rosters` -> `patients`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`.
- Referral reconciliation: `referrals` -> `patients`, `icd_codes`, `documents`, and `/chart/{patient_id}` when chart activation is requested.
- Dialysis transfers: `transfer_requests` -> `documents`, `patients`, and `facility_capacity`.
- Chronic-care panels: `/programs/{program_code}/candidates` or `program_candidates` -> `patients`, `clinical_history`, and `chart_artifacts`.

## Roster Access Verification

For each roster patient:

- Set insurance valid only when coverage exists, is active on the requested service date, is in network, and includes the requested service line. Use `coverage_expired`, `coverage_pending`, or `excluded_service_line` blockers when those values are allowed; otherwise represent absent coverage with the template's missing insurance status.
- Set prescription benefit valid only when a PBM row exists, is active, has an approved status, has a covered formulary status, and its policy number matches the coverage policy. Use `pbm_missing`, `pbm_invalid`, or `pbm_policy_mismatch` blockers as applicable when the template allows them.
- Set pharmacy status from the rank-1 preferred pharmacy joined to `pharmacies.network_status`. Use unknown when the preferred pharmacy or network lookup is absent.
- Add demographic and contact blockers for missing address, missing emergency contact, and unavailable preferred contact. Validate availability by channel: email requires an email address, phone or SMS requires a phone number, and portal requires an active portal-capable chart.
- Assign lifestyle risk from smoking, alcohol, exercise, and sleep evidence. Use high for severe or multiple risks such as current smoking, heavy alcohol use, no exercise, very low sleep, or combined moderate risks; medium for one moderate or unknown risk; low when no material lifestyle concern is present.
- Assign overall risk from lifestyle risk plus access blockers. Escalate to high when lifestyle risk is high, when there are multiple serious blockers, or when the template provides an overall-risk blocker. Use medium for fixable administrative or benefit problems and low when the patient is clear.
- Approve only when insurance, PBM, pharmacy, demographics, contacts, and risk are acceptable. Use hold for fixable administrative or benefit blockers, clinical review for high overall risk or clinical uncertainty, and rejected for non-covered or excluded service-line cases when the template allows those values.

## Referral Readiness and Chart Activation

For every referral in the target batch:

- Compare `referrals.service_line` with `icd_codes.service_family`. A mismatch is a clinical code discrepancy; use codes such as `icd_chapter_mismatch` or `clinical_code_discrepancy` only when the template allows them, and record the observed ICD chapter and expected specialty family or chapter when requested.
- Compare the ICD description, service family, and laterality with the referral diagnosis narrative and reason. Use `narrative_mismatch` or `clinical_reason_mismatch` when the stated reason contradicts the ICD family or symptom. Use `laterality_mismatch` when a side-specific ICD code is contradicted or the task specifically requires laterality confirmation and the referral text lacks usable side evidence.
- Treat `records_received = 0` as missing records and `imaging_received = 0` as missing imaging when those blockers are represented in the template.
- Treat authorization as blocking when authorization is required and the status is pending, denied, not submitted, or otherwise not approved/not required.
- Treat a scheduled appointment before clearance as an appointment blocker when the referral is not otherwise ready.
- Detect true duplicates by same patient plus matching or near-matching referral facts such as insurance ID, ICD, reason, received date, fax, or explicit duplicate-fax notes. Keep the earliest or primary referral and consolidate the duplicate.
- Detect shared insurance anomalies when the same insurance ID appears across different patients in the same batch. Do not merge these as duplicates unless the patient is the same.
- Clear "possible duplicate" referrals when the evidence shows distinct patients and distinct referral facts; include them only in the cleared duplicate review field if the template asks for it.
- Set readiness to ready only when there are no clinical, duplicate, insurance, records, imaging, authorization, or appointment blockers. Use blocked for hard administrative or authorization blockers, under review for clinical-code or duplicate ambiguity, and admin follow-up for administrative cleanup when those statuses are available.
- Build action or correspondence queues from blockers: `clinical_code_clarification` for code/narrative/laterality issues, `auth_records_request` for authorization and packet blockers, `duplicate_resolution` for duplicate review, and `appointment_hold_notice` for scheduled-before-clearance issues when those template values are available.
- Prioritize non-ready referrals by urgency and blocker severity: urgent clinical or denied-authorization issues first, then routine clinical or packet blockers, then administrative duplicate or insurance verification.

For chart activation fields:

- Inspect `patients.existing_chart` and `/chart/{patient_id}` or `chart_artifacts`.
- Use create-chart when no active chart exists, update-chart when a chart exists but required artifacts are missing or stale, and no-chart-action when all required artifacts are current.
- Required activation artifacts usually include demographics, active problems, medications, allergies, vitals, labs, and consent when the template offers those values. Return only artifacts allowed by the template, sorted as requested.

## Dialysis Transfer Review

For each transfer request:

- Required packet items are the document codes listed in the task template. Treat missing rows, draft documents, and non-final documents as missing.
- Treat a null transportation field as a missing transportation packet item when the template includes `transportation`.
- Check freshness only for present, final documents. Use these evidence-backed limits unless the prompt or template overrides them:
  - `hbsag`: 30 days
  - `monthly_labs`: 30 days
  - `history_physical`: 90 days
  - `hep_b_antibody_core`: 365 days
  - `ppd_or_cxr`: 365 days
- Compute age against the requested start date. A document is stale when `requested_start_date - received_date` is greater than the freshness limit.
- Set packet completeness from missing required items. For intake readiness, require both no missing items and no stale freshness items.
- Sum `facility_capacity.open_chairs` for the requested start date and modality across Cedar Ridge locations. If no capacity rows exist or the sum is zero, capacity is unavailable.
- Set requested-start feasibility from packet readiness and capacity: ready on requested start only when both are good; otherwise distinguish packet-not-ready with available capacity, packet-not-ready with unavailable capacity, and capacity-unavailable for ready packets with no chairs.
- Accept only transfers with packet readiness and capacity available. Use hold for administrative missing items or capacity problems, and clinical review when stale clinical packet items require clinical validation.
- Route next contact to the owner implied by the blocker: clinical nurse for stale clinical documents, intake coordinator for missing packet items or referring-facility follow-up, scheduling coordinator for capacity-only issues, and none when accepted. Use fax to the referring facility for packet documents, phone to the patient for patient-supplied transportation, internal queue for capacity or clinical routing, and none when no contact is needed.

## Chronic-Care Program Panels

For every current candidate returned for the program:

- Evaluate the target condition first. For a diabetes-hypertension program, require the candidate target condition to match and the clinical history to include active diabetes and hypertension. Use `wrong_target_condition` or `missing_active_dmhtn_diagnosis` reason codes when allowed.
- Consent declined is a rejection-level blocker. Consent missing is a hold-level blocker and should add the consent packet to a deferred monitoring package when allowed.
- An inactive or absent chart is a hold-level blocker unless another rejection-level blocker applies. Add `chart_not_active` and include chart update work when allowed.
- Required chart artifacts for enrollment are active problems, vitals, labs, medications, and consent. Mark missing or stale artifacts with the corresponding reason codes and missing artifact values available in the template.
- Add high-touch reason codes from clinical evidence: `recent_hospitalization_high_touch`, `low_adherence_high_touch`, `recent_ed_high_touch`, and `ckd_biweekly_monitoring` when the evidence supports them and the template allows them.
- Enroll only candidates who meet the target clinical criteria, have usable consent, have an active chart, and have required chart artifacts current. Hold clinically appropriate candidates with fixable consent or chart gaps. Reject wrong-condition, missing-diagnosis, or declined-consent candidates.
- Choose follow-up cadence by precedence: none for rejected candidates, deferred for holds, weekly for high-touch risks, biweekly for CKD-only monitoring, and monthly for standard eligible enrollment.
- Choose outreach by the candidate preferred outreach when that channel is reachable. If unreachable, fall back to another available channel in the allowed enum set; use none only when no allowed channel is reachable or the candidate is rejected.
- Use a high-touch monitoring package for weekly follow-up and a standard diabetes-hypertension package for ordinary enrollment. Use deferred for fixable holds and not applicable for rejections. Set first check-in days from cadence when the template asks: weekly 7, biweekly 14, monthly 30, and null for deferred or not applicable.

## Final Checks

Before finalizing:

- Re-read the answer template and compare every top-level key and item key against the JSON you built.
- Verify every enum value appears in the template.
- Verify every target entity is represented exactly once unless the template defines grouping.
- Recompute summary counts from the output object.
- Ensure the final response is valid JSON and contains no explanatory prose.
