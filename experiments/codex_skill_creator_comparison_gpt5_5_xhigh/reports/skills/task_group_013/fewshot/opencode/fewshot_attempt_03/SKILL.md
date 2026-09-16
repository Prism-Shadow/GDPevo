---
name: cedar-ridge-intake-json
description: Use for Cedar Ridge Intake Coordination Portal tasks that require strict JSON from patient, roster, insurance, PBM, pharmacy, referral, ICD, document, transfer, capacity, chart, or program-candidate records. Trigger whenever the prompt mentions Cedar Ridge intake coordination, TASK_ENV_BASE_URL, answer_template.json, access verification, referral readiness or activation, dialysis transfer review, chronic-care enrollment panels, or cohort summaries.
---

# Cedar Ridge Intake JSON Solver

Use this skill to turn Cedar Ridge Intake Coordination Portal records into the exact JSON shape requested by `input/payloads/answer_template.json`.

## Operating Rules

1. Read the task prompt and `answer_template.json` before fetching data. Treat the template as the output contract: required keys, controlled values, nullability, ordering, and count keys come from it.
2. Resolve `<TASK_ENV_BASE_URL>` from the prompt or environment access instructions. Use only the task environment endpoints needed for the requested scope.
3. Prefer scoped requests over broad listings. Use exact patient, referral, transfer, batch, roster, or program identifiers from the prompt/template. The SQL `/query` endpoint is useful when the REST endpoint does not expose a batch/roster listing directly.
4. Build an evidence table before writing JSON. Keep one row per requested patient, referral, transfer, or candidate with source fields, derived issue codes, status, priority, and summary buckets.
5. Return JSON only. Do not include prose, markdown fences, comments, or values outside the template's allowed enums.

## Portal Endpoints

- `GET /patients/{patient_id}`: patient demographics, coverage, PBM, preferred pharmacies, lifestyle, clinical history, rosters, referrals, transfers, documents, chart artifacts, and program candidates.
- `GET /referrals/{referral_id}`: referral row plus patient, ICD metadata, and referral documents.
- `GET /transfers/{transfer_id}`: transfer row plus patient, packet documents, and capacity rows near the requested period.
- `GET /chart/{patient_id}`: chart artifacts and clinical history for program enrollment or chart activation work.
- `GET /programs/{program_code}/candidates`: candidate list for chronic-care panels.
- `GET /icd/{code}`: ICD chapter, service family, laterality, and description when referral payloads do not already include it.
- `POST /query`: use scoped SQL such as roster ID or batch ID filters when the task names a roster or referral batch rather than individual IDs.

## JSON Assembly Discipline

- Include every required top-level key and nested key, even when a list is empty or a count is zero.
- Sort records exactly as the template says. Common patterns are ascending `patient_id`, `referral_id`, `transfer_id`, or `group_id`; priority lists are sorted by priority rules first.
- Treat issue-code and reason-code arrays as unordered sets: include each applicable code once, using the template's exact spelling.
- Compute summary counts from the final derived rows, not directly from raw records.
- Validate final JSON mentally against the template before answering: required keys present, enum values valid, no extra explanation fields, integers are integers, `null` only where permitted.

## New Patient Access Verification

Use this flow for roster-based primary-care or access-verification tasks.

Data collection:

- Get roster rows from patient `rosters` or via `/query` filtered by `roster_id`.
- For each target patient, use `/patients/{patient_id}` and inspect `patient`, `coverage`, `pbm`, `pharmacies`, `lifestyle`, and `clinical_history`.
- Use the roster's requested service date and service line, not the system date.

Derivations:

- `insurance_status` is `valid` when a coverage row is active on the requested service date and includes the requested service line. Use `invalid` for expired, pending, inactive, or excluded-service-line coverage; use `missing` when no coverage row exists.
- Coverage blockers: expired coverage -> `coverage_expired`; pending coverage -> `coverage_pending`; requested service line absent from `coverage.service_lines` -> `excluded_service_line`.
- Demographic blockers: missing address -> `missing_address`; missing emergency contact -> `emergency_contact_missing`; preferred contact route without a usable phone/email/portal route -> `preferred_contact_unavailable`.
- `prescription_status` is `valid` only when PBM is active/approved and policy/payer matches coverage. Rejected, pending, inactive, or otherwise not approved -> `invalid`; no PBM row -> `missing`.
- PBM blockers: no PBM -> `pbm_missing`; rejected/pending/inactive/not approved -> `pbm_invalid`; approved PBM whose policy does not match coverage -> `pbm_policy_mismatch`.
- `pharmacy_status` comes from the rank-1 preferred pharmacy: `in_network`, `out_of_network`, or `unknown`. Add `pharmacy_out_of_network` or `pharmacy_unknown` as applicable.
- Lifestyle risk: high for current smoking, heavy alcohol, no/unknown exercise, very short sleep, or multiple adverse lifestyle factors; medium for former smoking/moderate alcohol or a single moderate concern; low only when lifestyle fields are reassuring.
- Overall risk is at least the lifestyle risk. Raise to high for explicit clinical risk flags, recent hospitalization, complex medication burden, or multiple significant chronic conditions. Add `overall_risk_high` when overall risk is high.
- Registration status: reject when the requested service line is excluded or another hard eligibility blocker prevents registration; clinical review when high overall risk or clinical/pharmacy/PBM review is needed; hold for administrative blockers that can be corrected; approve only when no blockers remain and risk is acceptable.

## Referral Readiness And Activation

Use this flow for orthopedic, pulmonary, and similar referral-batch tasks.

Data collection:

- If a batch ID is provided, fetch all batch rows with `/query` filtered by `batch_id`, then inspect each referral through `/referrals/{referral_id}`.
- For every referral, collect referral fields, patient demographics, ICD metadata, document flags, authorization fields, scheduling fields, insurance ID, and chart artifacts when chart activation is requested.

Clinical/code checks:

- Wrong service family: flag when `icd.service_family` does not match `referral.service_line`.
- Chapter mismatch: when the template asks for chapter discrepancies, compare `icd.chapter` with the expected chapter for the service line. For orthopedics, musculoskeletal chapter codes are expected unless the task says otherwise.
- Narrative mismatch: compare ICD description/service family with `diagnosis_description`, `referral_reason`, and task service line. A referral reason that clearly belongs to a different clinical domain is a mismatch even if the code family is acceptable.
- Laterality mismatch: when ICD laterality is present or the narrative states a side, flag contradictions or missing expected side details according to the template.

Administrative checks:

- Missing records: `records_received` is false/zero.
- Missing imaging: `imaging_received` is false/zero when the task expects imaging readiness.
- Authorization blocker: `auth_required` is true and `auth_status` is not approved. Preserve the raw status where the template requests it.
- Already scheduled before clearance: `appointment_scheduled` is true on a referral that still has clinical, authorization, records, imaging, or duplicate issues.
- Duplicate group: same patient and materially same referral within the batch. Use the earliest/lower referral ID as the primary or keep referral unless the task states another rule.
- Shared insurance anomaly: same insurance ID used by different patient IDs. Do not treat this as a duplicate group unless the patient is the same.
- Possible duplicate notes on different patients are not enough to create a duplicate group; list them as cleared duplicate review if the template asks and the records show distinct patients/referrals.

Status and action mapping:

- `ready`: no clinical/code, missing-document, auth, duplicate, or scheduling blockers.
- `blocked`: hard operational blockers such as missing records, missing imaging, or authorization denial/pending. If hard blockers and clinical issues coexist, the row remains blocked.
- `under_review`: clinical/code discrepancies, duplicate review, or already scheduled before clearance without hard missing/auth blockers.
- `admin_followup`: administrative anomalies such as shared insurance issues when the referral is otherwise clinically and operationally clear.
- Issue codes feed action codes directly: corrected ICD/code clarification for clinical code issues; request records/imaging for missing inputs; resolve authorization for auth blockers; consolidate duplicates for duplicate groups; verify insurance ID for shared insurance; review existing appointment or hold notice for scheduled-before-clearance.
- Priority: urgent clinical discrepancies are tier 1; hard blockers and duplicate/scheduled-review work are usually tier 2; pure administrative insurance verification is tier 3; ready rows normally have no priority unless the template requires one.

Chart activation:

- For ready referrals, call `/chart/{patient_id}`.
- If no existing chart is present and the row is ready, `chart_action` is `create_chart`; otherwise use `update_chart` when required artifacts are absent or stale, and `no_chart_action` only when the chart is current.
- Artifacts to create are required chart elements that are missing or stale. For pulmonary activation, check demographics, active problems, medications, allergies, vitals, labs, and consent. Existing current artifacts do not need creation.

## Dialysis Transfer Review

Use this flow for seasonal dialysis transfer batches.

Data collection:

- Fetch each scoped transfer with `/transfers/{transfer_id}`.
- Use the transfer's requested start date, modality, packet documents, and capacity rows. Compare capacity only for the requested start date and matching modality.

Packet rules:

- A required document is present only when its document row is final/finalized. Draft or non-final rows count as missing.
- Packet completeness is based on missing required documents only. Stale documents do not make the packet incomplete, but they do make it not ready.
- Sort missing document codes alphabetically.
- Freshness is measured against the requested start date. Use the freshness limits implied by the template; common Cedar Ridge limits are 30 days for HBsAg, monthly labs, and PPD/CXR, and 365 days for history/physical and hepatitis B core antibody when the template includes them.
- Sort stale document entries by `doc_type`.

Capacity and decisions:

- Sum open chairs across capacity rows for the requested start date and matching modality.
- Capacity is available when the sum is greater than zero; otherwise unavailable.
- Feasibility:
  - packet complete, no stale docs, capacity available -> ready on requested start.
  - packet not ready and capacity available -> packet-not-ready/capacity-available value from the template.
  - packet not ready and capacity unavailable -> packet-not-ready/capacity-unavailable value from the template.
  - packet ready but capacity unavailable -> capacity-unavailable value from the template.
- Accept only when packet is complete, fresh, and capacity is available. Use clinical review for missing/stale clinical packet items. Use hold for capacity-only or administrative waiting states when the template supports it.
- Missing/stale packet issues usually route to the clinical nurse and referring facility fax. Capacity-only issues route to scheduling/internal queue. Accepted rows usually have no next contact.

## Chronic-Care Program Enrollment

Use this flow for program-candidate panels.

Data collection:

- Fetch candidates from `/programs/{program_code}/candidates`.
- For each candidate, fetch `/chart/{patient_id}` to verify clinical history and current chart artifacts.
- Use any program or portal as-of date exposed by the environment. If the obvious endpoint lacks it, keep the task/template-required date source consistent with portal metadata rather than the system date.

Eligibility and disposition:

- A candidate is clinically eligible for a diabetes/hypertension program when the target condition and active clinical history support both conditions. Wrong target condition or absent active diabetes/hypertension evidence makes the candidate ineligible.
- Signed consent, active chart, and current required artifacts allow enrollment when clinical criteria are met.
- Declined consent or wrong target condition leads to reject. Missing consent or inactive/stale/missing chart artifacts leads to hold when the clinical target is otherwise correct.
- Use `chart_not_active` when the candidate lacks an active chart. Use stale/missing chart reason codes only for artifacts relevant to a hold or enrollment decision.

Cadence and package:

- Weekly/high-touch for recent hospitalization, recent ED flag, or low adherence. If more than one high-touch reason applies, include the clinically strongest reason supported by the template.
- Biweekly for CKD monitoring when no weekly high-touch reason dominates.
- Monthly for standard eligible candidates without high-touch or CKD escalation.
- Deferred for holds; none for rejects.
- High-touch package includes BP cuff, glucometer, lab order, medication reconciliation, and care plan setup. Standard package includes BP cuff, glucometer, lab order, and medication reconciliation when CKD or medication complexity warrants it; otherwise the standard core may omit medication reconciliation if the template examples imply a lighter package. Deferred package uses consent packet and chart update request. Rejects use not-applicable with empty components and null first check-in.
- Outreach uses the candidate's preferred route only when usable. If phone/email is missing or portal is not available because there is no active chart, fall back to another available patient contact route; use none only if no route is usable.

## Final Validation Checklist

Before sending the final answer:

- The JSON parses.
- Top-level keys and nested keys match `answer_template.json`.
- All controlled values are from the template.
- Required empty lists and zero-count keys are present.
- Patient/referral/transfer rows are sorted as requested.
- Summary counts equal the derived rows.
- No train-specific examples, evidence notes, or prose appear in the answer.
