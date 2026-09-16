---
name: cedar-intake-reconciliation
description: Solve Cedar Ridge Intake Coordination Portal tasks that require querying patients, referrals, transfers, documents, charts, programs, coverage, PBM, pharmacies, ICD metadata, or facility capacity and returning strict JSON for access verification, referral readiness, dialysis transfer review, chronic-care enrollment, or referral-to-chart activation.
---

# Cedar Intake Reconciliation

Use this skill to turn Cedar Ridge portal records into the exact JSON object requested by the task template.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the schema, controlled vocabulary, ordering rule, and count contract.
2. Extract the target identifier from the prompt or template: roster ID, referral batch ID, transfer batch ID, or program code.
3. Query only records scoped to that target and its linked patient IDs. Prefer REST endpoints for direct objects and `POST /query` for joins.
4. Derive fields from portal data, not from prose expectations. Use the rules below only when the template does not define a different rule.
5. Emit JSON only. Include required zero-count keys and empty arrays. Sort rows exactly as the template specifies; otherwise sort IDs ascending and sort artifact/document code arrays alphabetically.

## Portal Access

Use the task base URL from the prompt or environment access file. Credentials are not needed.

Useful endpoints:

- `GET /patients/{patient_id}` for patient, coverage, PBM, pharmacies, lifestyle, documents, chart artifacts, and program candidates.
- `GET /chart/{patient_id}` for chart artifacts and clinical history.
- `GET /referrals?batch_id=...`, `GET /transfers?batch_id=...`, and `GET /programs/{program_code}/candidates`.
- `GET /icd/{code}` for ICD chapter, service family, description, and laterality.
- `POST /query` with `{"sql": "..."}` for scoped joins.

The helper script can print formatted JSON:

```bash
python scripts/portal_fetch.py --base-url "$TASK_ENV_BASE_URL" referrals BATCH_ID
python scripts/portal_fetch.py --base-url "$TASK_ENV_BASE_URL" transfers BATCH_ID
python scripts/portal_fetch.py --base-url "$TASK_ENV_BASE_URL" program PROGRAM_CODE
python scripts/portal_fetch.py --base-url "$TASK_ENV_BASE_URL" chart PATIENT_ID
python scripts/portal_fetch.py --base-url "$TASK_ENV_BASE_URL" sql "select * from referrals where batch_id='BATCH_ID' order by referral_id"
```

## Access Verification

For new-patient roster tasks:

- Read `intake_rosters` for `requested_service_date`, `service_line`, and patient IDs.
- Set insurance `valid` when coverage exists, is active, is effective on the requested date, is not terminated before that date, and includes the requested service line. Use `missing` for no coverage and `invalid` otherwise.
- Add coverage reasons from the failing condition: `coverage_expired`, `coverage_pending`, and `excluded_service_line`.
- Set prescription benefit `valid` when a PBM row exists, is active, has an approved/covered status, and its policy matches the active coverage policy. Use `missing` for no PBM, `invalid` for inactive/rejected/pending/review rows, and `pbm_policy_mismatch` for a policy mismatch.
- Use the rank-1 preferred pharmacy. Map its pharmacy network to `in_network` or `out_of_network`; use `unknown` when no preferred pharmacy/network is available.
- Add contact/demographic reasons when present: missing address, missing emergency contact, or unavailable preferred contact channel. Email/portal require an email; phone/sms require a phone.
- Assign lifestyle risk by strongest signal: high for current smoking, heavy alcohol use, no/missing exercise, or very short sleep; medium for former smoking, moderate alcohol, low exercise, or mildly short sleep; low when none apply.
- Assign overall risk high when high lifestyle risk or any hard blocker exists; medium for medium lifestyle or softer admin blockers; low only when clean.
- Registration status precedence: `rejected` for non-covered/excluded service-line cases; `clinical_review` for high overall risk, PBM failure, pharmacy out-of-network, or clinical blockers; `hold` for admin-only or pending items; `approved` only when no blockers remain.

## Referral Readiness And Activation

For referral batch tasks:

- Fetch referral rows by `batch_id`, ICD metadata for every `icd10_code`, patient/chart data when chart activation is requested, and documents when the template asks for support-document status.
- Flag clinical code discrepancies when ICD service family does not match the referral service line, when the ICD chapter is not expected for the line, when referral reason/diagnosis narrative is incompatible with the code, or when laterality conflicts with referral text. Common expected chapters: orthopedics `M00-M99`, pulmonary `J00-J99`.
- Hard blockers are missing records, missing imaging, and authorization statuses such as denied, pending, or not submitted when authorization is required.
- Duplicate groups require strong identity overlap, usually the same patient plus repeated clinical/referring/insurance details. Keep the earliest or lowest referral ID as primary unless the portal marks another primary. A "possible duplicate" note alone is not enough; if the suspected rows are distinct patients/policies, clear duplicate review when the template asks.
- Shared insurance anomalies are repeated insurance IDs across different patient IDs; repeated insurance for the same patient is a duplicate signal instead.
- Readiness precedence: hard blockers -> `blocked`; clinical code discrepancy, duplicate review, or already scheduled before clearance -> `under_review`; shared-insurance-only issues -> `admin_followup`; no issues -> `ready`.
- Priority tiers: urgent clinical/code issues -> `tier_1_immediate`; hard blockers, duplicate review, scheduling-before-clearance, and routine clinical/code issues -> `tier_2_short_term`; insurance-only admin follow-up -> `tier_3_administrative`; ready rows usually have null/no priority.
- Map actions directly from issue codes: corrected ICD or clinical clarification for code discrepancies, confirm narrative/laterality for narrative/laterality mismatches, consolidate duplicate, verify insurance ID, request records, request imaging, resolve authorization, and review existing appointment.
- For correspondence queues, use clinical-code templates for code-only issues, auth/records templates for authorization or records blockers, duplicate templates for duplicate review, and appointment-hold templates when an uncleared referral is already scheduled.
- For ready referral chart work, inspect chart artifacts for `demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`, and `consent`. Include missing or stale artifacts. Use `create_chart` when no chart exists, `update_chart` when an existing chart needs artifacts, and `no_chart_action` when nothing is needed.

## Dialysis Transfer Review

For transfer batch tasks:

- Fetch transfer rows by `batch_id`, all documents with matching `transfer_id`, and `facility_capacity` rows for each requested start date and modality.
- Required documents come from the answer template. A document counts as present only when it is final/finalized. Draft documents count as missing.
- Treat transportation as missing when the transfer has no transportation value or required transportation document.
- Packet completeness means all required documents are present; stale documents do not by themselves make `packet_completeness_status` incomplete.
- Staleness is measured against the requested start date. Use these freshness limits unless the template overrides them: `hbsag`, `monthly_labs`, and `ppd_or_cxr` are 30 days; `history_physical` and `hep_b_antibody_core` are 365 days.
- Sum `facility_capacity.open_chairs` across locations for the requested start date and modality. Capacity is available when the total is greater than zero.
- Feasibility combines packet readiness and capacity: ready on requested start only when no documents are missing or stale and capacity is available; otherwise use the template value matching packet-not-ready and/or capacity-unavailable.
- Final decision: accept only when packet ready and capacity available; hold for capacity-only constraints; clinical review for missing or stale clinical packet items. Contact owner is usually clinical nurse for document/freshness work, scheduling coordinator for capacity-only work, intake coordinator for admin-only work, and none when accepted.

## Chronic-Care Program Enrollment

For program candidate tasks:

- Fetch the program candidate list and include every current candidate returned for the program. Join patient, chart, and clinical history by patient ID.
- Derive eligibility from both candidate target condition and active clinical diagnoses. For diabetes/hypertension programs, require the candidate target condition and clinical history to include both diabetes and hypertension.
- Use portal/chart statuses for missing artifacts. Required chronic-care artifacts are active problems, vitals, labs, medications, and consent. Mark `chart_record` when the patient has no active chart, and mark individual artifacts when missing or stale.
- Status precedence: reject wrong target condition, missing active program diagnosis, declined consent, or inactive chart that prevents enrollment; hold eligible candidates with missing consent or chart cleanup; enroll eligible candidates with signed consent and current required artifacts.
- Reason codes should be normalized from the cause: target mismatch, missing active diagnosis, consent declined/missing, chart not active, stale active problems, missing recent vitals/labs, missing medication list, and program-fit/high-touch reasons.
- High-touch weekly follow-up applies for recent hospitalization, low adherence, or recent ED flags. CKD without a high-touch trigger uses biweekly follow-up. Otherwise use monthly for clean enrollments, deferred for holds, and none for rejects.
- Monitoring packages: high-touch includes BP cuff, glucometer, labs, medication reconciliation, and care plan setup with first check-in in 7 days; standard includes BP cuff, glucometer, and labs, adding medication reconciliation for CKD/biweekly cases with first check-in in 14 or 30 days; deferred uses consent packet/chart update request; rejects are not applicable.
- Outreach should use the preferred outreach channel when usable. Portal requires portal access/active chart and email; email requires email; phone and SMS require phone. Fall back to the patient's usable preferred contact, then to another available allowed channel, else `none`.

## Final Checks

- Validate the final object against the template before answering: required keys, enum values, nullability, ordering, and integer counts.
- Recompute summaries from the final patient/referral/transfer rows rather than from intermediate notes.
- Do not include explanatory prose outside the JSON when the user asks for JSON only.
