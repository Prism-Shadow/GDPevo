---
name: cedar-ridge-intake-audit
description: Use this skill for Cedar Ridge Intake Coordination Portal tasks that require a JSON audit or activation file from a TASK_ENV_BASE_URL, including new-patient access verification, referral readiness, referral-to-chart activation, dialysis transfer packet review, and chronic-care program enrollment panels. Use it whenever a prompt mentions Cedar Ridge intake rosters, referrals, transfers, program candidates, chart artifacts, ICD metadata, or answer_template.json-controlled output.
---

# Cedar Ridge Intake Audit

Use this skill to solve Cedar Ridge portal tasks by deriving a JSON-only answer from the prompt, the provided `answer_template.json`, and the task environment. The examples show that accuracy depends more on schema discipline and blocker precedence than on prose reasoning.

## Core Workflow

1. Read the user prompt and every local payload template before querying the portal.
2. Replace `<TASK_ENV_BASE_URL>` with the provided base URL. Use only the allowed portal endpoints and the read-only SQL endpoint.
3. Fetch only records named or implied by the prompt: roster patient IDs, referral batch IDs, transfer batch IDs, or program candidate codes.
4. Build an intermediate table per patient/referral/transfer/candidate with raw fields, derived blockers, final status, and summary counters.
5. Return one JSON object and no prose. Use only keys and controlled values present in the template.

Prefer the narrow object endpoints for individual records:

- `GET /patients/{patient_id}`
- `GET /referrals/{referral_id}`
- `GET /transfers/{transfer_id}`
- `GET /chart/{patient_id}`
- `GET /programs/{program_code}/candidates`
- `GET /icd/{code}`
- `GET /pharmacies`

Use `POST /query` when a prompt identifies a batch or roster but not every row. Keep queries narrow:

```json
{"sql":"select * from intake_rosters where roster_id = '{roster_id}' order by patient_id"}
```

```json
{"sql":"select * from referrals where batch_id = '{batch_id}' order by referral_id"}
```

```json
{"sql":"select * from transfer_requests where batch_id = '{batch_id}' order by transfer_id"}
```

## Output Discipline

- Treat the template as the contract. Match top-level keys, nested keys, enum spellings, nullability, and ordering exactly.
- Sort row arrays by the key named in the template. Sort reason/blocker-code arrays for stable output even when the template says they are unordered sets.
- Recompute summaries from your derived rows after all statuses are final. Include required zero-count categories.
- Do not add explanatory fields, comments, markdown fences, or prose around the final JSON.
- If a template uses a different code vocabulary than the examples below, translate the same finding into the template's allowed code.

## New Patient Access Verification

Use roster rows for `requested_service_date` and `service_line`, then fetch each patient. Derive these fields per patient:

**Insurance**

- `valid`: an active coverage row is effective on the requested service date, not terminated before that date, and includes the requested service line.
- `invalid`: coverage exists but is expired, pending, not yet effective, terminated, out of scope for the service line, or otherwise unusable.
- `missing`: no usable coverage row exists.

Map blockers:

- `coverage_expired`: coverage status is expired or the termination date is before the requested service date.
- `coverage_pending`: coverage status is pending or effective after the requested date.
- `excluded_service_line`: the requested service line is absent from `coverage.service_lines`.

**Prescription Benefit**

- `valid`: PBM row exists, is active, is approved, has covered formulary status, and its policy matches the active coverage policy.
- `invalid`: PBM exists but is inactive, rejected, pending/review, non-covered, policy-mismatched, or incompatible with the service.
- `missing`: no PBM row exists.

Map blockers:

- `pbm_invalid`: inactive/rejected/pending PBM, non-covered formulary, or review status.
- `pbm_missing`: absent PBM data.
- `pbm_policy_mismatch`: PBM policy does not match coverage policy, or PBM requirements do not fit the requested intake service.

**Preferred Pharmacy**

- Use the patient pharmacy with the lowest `preference_rank`.
- `in_network` and `out_of_network` come from the pharmacy record.
- Use `unknown` when there is no preferred pharmacy or no network status.
- Add `pharmacy_out_of_network` or `pharmacy_unknown` when applicable.

**Demographic/contact blockers**

- `missing_address`: patient address is null or blank.
- `emergency_contact_missing`: emergency contact flag is false.
- `preferred_contact_unavailable`: the preferred channel cannot be used. Phone and SMS require a phone number; email requires email; portal should have a usable email and an active portal/chart context when available.

**Risk**

- Lifestyle risk is `high` for current smoking, heavy alcohol use, no/unknown exercise combined with short sleep, or multiple adverse lifestyle signals. It is `medium` for former smoking, moderate alcohol, mildly short sleep, or one moderate signal. Otherwise use `low`.
- Overall risk is at least the lifestyle risk. Raise to `high` for recent hospitalization, explicit risk flags, high medication burden, multiple serious chronic conditions, or any high lifestyle risk.
- Add `overall_risk_high` when overall risk is high.

**Registration status precedence**

- `rejected`: hard disqualifier such as expired coverage or excluded service line.
- `clinical_review`: high overall risk or unresolved clinical/benefit/network/contact blockers without a hard disqualifier.
- `hold`: administrative incompleteness without clinical escalation.
- `approved`: no blockers.

## Referral Readiness and Referral-to-Chart Activation

For referral batches, fetch all referrals in the batch, ICD metadata, patient records, documents, and chart artifacts when the template asks for chart activation.

**Clinical code discrepancies**

- Compare `referral.service_line`, ICD `service_family`, ICD `chapter`, ICD `laterality`, `diagnosis_description`, and `referral_reason`.
- Orthopedic spine/joint readiness expects musculoskeletal chapter `M00-M99`; injury/trauma chapters such as `S00-T88` are chapter mismatches even if the ICD service family says orthopedics.
- Pulmonary activation accepts pulmonary-family respiratory diagnoses and symptom codes when the referral narrative fits pulmonary care. A non-pulmonary service family is a wrong-service-family discrepancy.
- Use narrative mismatch when the ICD family is plausible but the referral reason or diagnosis narrative points to another clinical domain.
- Use laterality mismatch only when a lateral ICD conflicts with the narrative or required side.

**Operational blockers**

- Missing records: `records_received` is false.
- Missing imaging: `imaging_received` is false.
- Authorization blocker: `auth_required` is true and `auth_status` is pending, denied, not submitted, or otherwise not approved.
- Scheduled before clearance: `appointment_scheduled` is true while any blocker or clinical discrepancy remains.

**Duplicate and insurance checks**

- Actual duplicate groups require same patient and matching identifiers such as insurance ID, ICD, referral reason, service line, or intake date. Keep the earliest/lowest referral ID as the primary when no stronger signal exists.
- If a record is marked as a possible duplicate but patient and insurance identity differ, list it as cleared when the template has a cleared-duplicate field.
- Shared insurance anomaly means the same insurance ID appears on different patient IDs in the same batch. If the same patient owns the repeated insurance ID, treat it as a legitimate same-patient duplicate rather than an anomaly.

**Readiness status precedence**

- `ready`: no clinical discrepancy, duplicate issue, shared-insurance anomaly, missing records/imaging, authorization blocker, or scheduled-before-clearance issue.
- `blocked`: any missing records, missing imaging, authorization blocker, or scheduled-before-clearance blocker.
- `under_review`: clinical code/narrative/laterality discrepancy or duplicate review without a hard operational blocker.
- `admin_followup`: administrative issue only, such as shared insurance anomaly.

**Action/correspondence mapping**

- Code discrepancy: request corrected ICD or clinical code clarification.
- Narrative mismatch: confirm narrative or clinical reason.
- Laterality mismatch: confirm laterality.
- Duplicate group: consolidate duplicate or duplicate resolution.
- Shared insurance anomaly: verify insurance ID.
- Missing records/imaging: request records or imaging.
- Authorization blocker: resolve authorization; for correspondence use authorization denied/pending/not-submitted reason allowed by the template.
- Already scheduled before clearance: review existing appointment or send appointment hold notice.

**Priority**

- Tier 1: urgent clinical discrepancies or urgent items requiring immediate clinical clarification.
- Tier 2: non-urgent clinical discrepancies, duplicate review, missing records/imaging, authorization blockers, scheduled-before-clearance items, or multiple non-admin blockers.
- Tier 3: admin-only follow-up.
- For explicit `priority_order`, sort by tier first, then urgent or scheduled-before-clearance/multiple-blocker cases, then stable referral ID.

**Chart activation for ready referrals**

Only include ready referrals in chart-activation work unless the template says otherwise.

- Required activation artifacts are usually `demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`, and `consent`.
- If no chart exists, `chart_action` is `create_chart` and artifacts should include every required activation artifact.
- If a chart exists, `chart_action` is `update_chart` when any required artifact is missing or stale; include missing/stale artifacts only.
- If all required artifacts are current, use `no_chart_action` with an empty artifact list when the template allows it.

## Dialysis Transfer Packet Review

For transfer batches, fetch each transfer, patient, packet documents, and facility capacity for the requested start date and modality.

**Packet completeness**

- A required document is present only when a document row exists with `finalized = 1` and final status.
- Treat transfer logistics such as transportation as satisfied from the transfer request field when the template includes them as required packet items.
- Missing required document lists should use the template's document codes and alphabetical ordering.

**Freshness**

Compare document `received_date` to the requested start date:

- 30-day freshness: `hbsag`, `monthly_labs`, `ppd_or_cxr`.
- 365-day freshness: `hep_b_antibody_core`, `history_physical`.
- Only final documents can satisfy freshness; draft documents are missing, not fresh.

**Capacity**

- Sum `facility_capacity.open_chairs` where `date` equals the requested start date and `modality` equals the transfer modality.
- If no capacity row exists for that exact date/modality, open chairs are `0` and capacity is unavailable.

**Feasibility and decision**

- `ready_on_requested_start`: packet complete, no stale documents, and capacity available.
- `packet_not_ready_capacity_available`: packet incomplete or stale, with open chairs available.
- `packet_not_ready_capacity_unavailable`: packet incomplete or stale, with no open chairs.
- `capacity_unavailable`: packet ready but no open chairs.
- `accept`: ready on requested start.
- `clinical_review`: stale clinical/lab/infection-control documents or clinical packet concerns.
- `hold`: missing administrative packet items or capacity-only blocking without clinical review.

Next contact owner should reflect the blocker: clinical nurse for stale clinical documents, intake coordinator for missing packet paperwork, scheduling coordinator for capacity-only issues, and none for accepted transfers. Fax the referring facility for packet-document remediation; use internal queue for scheduling/capacity follow-up when appropriate.

## Chronic-Care Program Enrollment

For program panels, fetch the candidate list, each patient, clinical history, and chart artifacts.

**Eligibility and status**

- The target condition must match the program. For diabetes-hypertension panels, the candidate target and active clinical history should support both diabetes and hypertension.
- `eligible` reflects whether the candidate clinically belongs to the program population. A clinically eligible patient may still be held or rejected for consent/chart blockers.
- `reject`: wrong target condition, missing active target diagnoses, or declined consent.
- `hold`: missing consent, inactive chart, stale required artifacts, or missing recent vitals/labs/medications for an otherwise eligible patient.
- `enroll`: target condition and diagnoses match, consent is signed, chart is active enough, and required artifacts are current.

**Reason codes**

- Use wrong-target and missing-active-diagnosis codes for candidates outside the target condition.
- Use consent declined/missing codes from candidate consent status.
- Use chart not active when `existing_chart` is false.
- Use stale active-problems when the active-problems artifact is stale.
- Use missing-recent vitals/labs/medication-list codes when those artifacts are missing or not current.
- Add meets-criteria only for candidates ready to enroll based on target condition and active diagnoses.
- High-touch reasons: recent hospitalization, low adherence, or recent ED risk flags.
- CKD without a higher-touch trigger maps to biweekly monitoring.

**Follow-up and package**

- Weekly cadence: high-touch enrollment, including recent hospitalization, recent ED flag, or low adherence.
- Biweekly cadence: CKD monitoring without higher-touch trigger.
- Monthly cadence: standard enrollment.
- Deferred: hold.
- None: reject.

Monitoring packages:

- High touch: `high_touch_dm_htn`, BP cuff, glucometer, lab order, medication reconciliation, care plan setup, first check-in about one week after enrollment.
- Biweekly standard: `standard_dm_htn`, BP cuff, glucometer, lab order, medication reconciliation, first check-in about two weeks after enrollment.
- Monthly standard: `standard_dm_htn`, BP cuff, glucometer, lab order, first check-in about one month after enrollment.
- Hold/deferred: `deferred`, consent packet and/or chart update request as needed, null first check-in.
- Reject: `not_applicable`, no components, null first check-in.

**Outreach**

Start with the program candidate's preferred outreach channel. If it is unusable, fall back to the patient preferred contact, then any usable allowed channel:

- Phone and SMS require a phone number.
- Email requires an email address.
- Portal should only be used when the patient has a usable portal/chart context.
- Use `none` only when no allowed channel can be used.

## Final Checks

Before finalizing:

- Validate every enum against the template.
- Confirm all requested IDs are present exactly once unless the template asks for grouped duplicates.
- Confirm summaries equal the row-level derivations.
- Confirm dates are ISO `YYYY-MM-DD`.
- Confirm no task-analysis notes or raw portal records appear in the final JSON.
