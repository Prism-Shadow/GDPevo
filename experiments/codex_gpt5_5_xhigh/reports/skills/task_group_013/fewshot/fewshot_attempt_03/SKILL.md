---
name: cedar-ridge-intake-reconciliation
description: Reconcile Cedar Ridge Intake Coordination Portal tasks and produce schema-valid JSON for patient access verification, referral readiness or activation audits, dialysis transfer packet reviews, and chronic-care enrollment panels. Use when a task references the Cedar Ridge portal, an environment_access.md base URL, intake rosters, referral batches, transfer batches, program candidates, chart artifacts, ICD metadata, documents, pharmacies, or read-only SQL reconciliation.
---

# Cedar Ridge Intake Reconciliation

## Core Workflow

1. Read the user's prompt and every file under `input/payloads/`, especially `answer_template.json`.
2. Read `environment_access.md` when present and use only its base URL and listed endpoints for network access. Substitute any `<TASK_ENV_BASE_URL>` placeholder with that base URL. Credentials are normally absent unless the file says otherwise.
3. Identify the target object from the prompt/template: roster, referral batch, transfer batch, program code, or explicit patient/referral/transfer IDs.
4. Query the portal for the complete target cohort before reasoning. Prefer `POST /query` for compact joins, and use detail endpoints such as `/patients/{id}`, `/referrals/{id}`, `/transfers/{id}`, `/chart/{patient_id}`, `/icd/{code}`, `/documents`, and `/pharmacies` to confirm ambiguous fields.
5. Build the JSON strictly from the template: required top-level keys, controlled values, nullability, ordering rules, and summary/count keys. Do not emit prose outside JSON when the task asks for JSON only.
6. Derive every ID, date, count, and row from the current prompt/template/environment. Never reuse literal values from examples or prior tasks.

Useful portal tables exposed through read-only SQL include `patients`, `intake_rosters`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`, `clinical_history`, `referrals`, `icd_codes`, `documents`, `transfer_requests`, `facility_capacity`, `program_candidates`, and `chart_artifacts`.

## General Validation

- Treat `answer_template.json` as the output contract even when endpoint data uses different field names.
- Sort each list exactly as the template specifies. Common orders are ascending `patient_id`, `referral_id`, `transfer_id`, or `group_id`; priority lists use the template's priority definition.
- Treat reason-code, issue-code, and blocker-code arrays as unordered sets unless the template gives an ordering.
- Recompute summary counts from the completed item rows, not from separate assumptions.
- Include empty arrays and zero-valued count buckets when the template requires them.
- Use `null` only where the template permits it.

## Access Verification

For new-patient roster verification, join the roster to patient identity, coverage, PBM, preferred pharmacy, lifestyle, and clinical history records.

- Use the roster row for `requested_service_date` and `service_line`.
- Mark insurance valid only when a coverage record is active for the requested service date and includes the requested service line. Flag expired, pending, missing, or excluded-line cases with the template's matching reason codes.
- Mark prescription benefits valid only when PBM data is present, active, approved, and covered. Rejected, pending, inactive, not-found, review, missing, payer/policy mismatch, or specialty-policy conflicts should map to the closest PBM reason code allowed by the template.
- Use the patient's first preferred pharmacy by `preference_rank`; map its pharmacy `network_status` to in-network/out-of-network/unknown.
- Score lifestyle risk from smoking, alcohol, exercise, and sleep. Current smoking, heavy alcohol, absent exercise, or very low sleep increase risk; multiple adverse factors usually become high.
- Score overall risk from lifestyle risk plus clinical burden such as high medication count, recent hospitalization, risk flags, and major access blockers.
- Registration status should follow blocker severity: hard coverage/service-line conflicts reject, remediable administrative or benefit issues hold or clinical-review, high clinical risk routes to clinical review, and clean low-risk rows approve.

## Referral Readiness And Activation

For referral batch audits, query the target batch and reconcile each referral with ICD metadata, patient/chart information, documents, authorization fields, appointment fields, duplicate patterns, and shared insurance IDs.

- Use `/icd/{code}` or `icd_codes` to compare referral `service_line` with ICD `service_family`, expected chapter, narrative, and laterality.
- Clinical code discrepancies include wrong service family/chapter, mismatch between referral reason or diagnosis text and ICD meaning, and laterality conflicts.
- Records and imaging blockers come from `records_received` and `imaging_received`.
- Authorization blockers apply when authorization is required and the status is denied, pending, not submitted, or otherwise not cleared.
- Existing scheduled appointments before clearance should be flagged with the template's appointment/hold reason.
- Duplicates usually share patient, insurance, referring contact, reason, or a "duplicate" note. Keep the earliest or primary referral unless the task gives another rule.
- Shared insurance anomalies are shared insurance IDs across distinct patients; shared insurance on duplicate referrals for the same patient is usually a legitimate duplicate.
- Readiness precedence: no issues is ready; records/imaging/auth blockers are blocked; clinical-code, duplicate, or scheduled-before-clearance issues are under review unless combined blockers make the template call for blocked; pure administrative insurance/contact issues are administrative follow-up.
- Map issues to action or correspondence codes using the template vocabulary. Urgent clinical discrepancies are highest priority, clinical/admin blockers usually follow, and pure administrative verification is lowest.

## Dialysis Transfer Packet Review

For transfer batches, gather transfer requests, packet documents, patient records, and facility capacity for the requested start date and modality.

- A required packet item is complete only when the document exists for the transfer/patient and is finalized/final. Draft, absent, or non-final documents count as missing.
- For stale checks, compare `received_date` with the requested start date. Common freshness windows are 30 days for current dialysis labs/infectious-screening/PPD-CXR style items and 365 days for history and physical; use task/template wording if it gives a different limit.
- Capacity is available when the sum of `facility_capacity.open_chairs` for the requested date and modality is greater than zero.
- Feasibility combines packet readiness and capacity: ready on requested start only when the packet is complete/fresh and capacity is available; otherwise choose the template value matching packet-not-ready and/or capacity-unavailable.
- Intake decision should accept only fully ready transfers with capacity. Missing or stale clinical packet items usually require clinical review; capacity-only issues route to scheduling or hold; administrative-only missing items route to intake coordination.

## Chronic-Care Program Panels

For program candidate panels, load `/programs/{program_code}/candidates`, then join each candidate to patient, chart artifacts, and clinical history.

- Eligibility depends on the program target condition and active clinical history. For diabetes/hypertension panels, require both active diabetes and hypertension evidence unless the task defines another target.
- Consent declined usually rejects. Missing consent or inactive/missing chart data usually holds unless combined with wrong target condition, which rejects.
- Missing chart artifacts come from absent or stale `chart_artifacts` rows for the artifact types required by the template. Treat `status != current` as needing refresh.
- High-touch monitoring is appropriate for recent hospitalization, recent ED/risk flags, very low adherence, or other high-risk clinical markers. CKD commonly routes to biweekly monitoring. Stable eligible candidates can use monthly or standard monitoring.
- Outreach should follow the candidate or patient preferred channel when usable; fall back only when the preferred channel has no usable phone/email/portal information and the template permits another channel.
- Initial monitoring packages should match disposition: high-touch for high-risk enrollment, standard for stable enrollment, deferred for holds needing consent or chart updates, and not applicable for rejects.

## Output Discipline

Before finalizing, parse the JSON locally if possible and check:

- All required keys from the template are present.
- All controlled values are from the template.
- Every required target row is included exactly once.
- Summary counts equal the row-level data.
- No task-local answer constants or example rows have been copied from prior work.
