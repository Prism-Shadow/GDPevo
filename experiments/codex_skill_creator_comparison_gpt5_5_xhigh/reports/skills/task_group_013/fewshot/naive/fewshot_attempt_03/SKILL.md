---
name: cedar-ridge-intake-json
description: Solve Cedar Ridge Intake Coordination Portal tasks that require strict JSON from read-only portal records and answer_template schemas, including new-patient access verification, referral readiness and chart activation, dialysis transfer packet and capacity review, and chronic-care enrollment panels.
---

# Cedar Ridge Intake JSON

## Core Workflow

1. Read the user prompt, `input/payloads/answer_template.json`, and any other payload files before querying the portal.
2. Extract the target identifier, target type, output ordering, required keys, allowed enum values, count keys, and any fixed values from the template. Treat the template as the output contract.
3. Use only the read-only Cedar Ridge portal endpoints supplied by the task. Never call a judge or evaluator endpoint.
4. Fetch only records relevant to the target roster, referral batch, transfer batch, or program code. Prefer the SQL endpoint or the bundled helper for complete, filterable snapshots.
5. Build an intermediate work table with one row per required patient, referral, transfer, or candidate. Record the raw facts that justify every status and reason code.
6. Emit exactly one JSON object. Do not include prose, comments, markdown fences, or fields not requested by the template.
7. Validate with `jq` or Python JSON parsing, then verify required keys, enum values, list ordering, nulls, and summary counts.

## Portal Snapshot Helper

Use [scripts/portal_snapshot.py](scripts/portal_snapshot.py) when a fast local snapshot is useful:

```bash
SKILL_DIR=/work/skill
python "$SKILL_DIR/scripts/portal_snapshot.py" --base-url "$TASK_ENV_BASE_URL" --kind roster --id "<ROSTER_ID>"
python "$SKILL_DIR/scripts/portal_snapshot.py" --base-url "$TASK_ENV_BASE_URL" --kind referral-batch --id "<BATCH_ID>"
python "$SKILL_DIR/scripts/portal_snapshot.py" --base-url "$TASK_ENV_BASE_URL" --kind transfer-batch --id "<BATCH_ID>"
python "$SKILL_DIR/scripts/portal_snapshot.py" --base-url "$TASK_ENV_BASE_URL" --kind program --id "<PROGRAM_CODE>"
```

The helper outputs raw portal rows only. It does not decide statuses or produce final answers.

## Data Gathering

For roster access verification, gather `intake_rosters`, `patients`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, and `lifestyle` for the roster patients. Use the roster rows for requested service date and service line unless the prompt or template fixes them.

For referral intake, gather all `referrals` in the batch, matching `icd_codes`, related patients, chart artifacts, and referral documents when document flags matter. Detect duplicates from same-patient repeated referrals with matching identifiers such as insurance, fax, reason, or explicit duplicate notes. Detect shared-insurance anomalies separately when one insurance ID appears across different patients.

For transfer reviews, gather `transfer_requests`, packet `documents`, related patients, and `facility_capacity` on requested start dates. Sum open chairs across locations for the requested modality.

For program enrollment panels, gather program candidates, patients, clinical history, and chart artifacts. Use the candidate endpoint when it returns joined patient fields, then fill gaps from `/patients/{id}` and `/chart/{id}` or SQL.

If a program template requires `as_of_date`, use the date supplied by the prompt, template, or portal metadata. If the portal lacks metadata, derive it from the task context and do not treat future candidate dates as the as-of date.

## New-Patient Access Rules

Classify insurance as `valid` only when coverage exists, is active on the requested service date, is in network, and includes the requested service line. Use `missing` when no coverage row exists. Otherwise use `invalid` and add the matching template reason code: expired coverage, pending coverage, service-line exclusion, or other coverage failure.

Classify prescription benefits as `valid` only when PBM exists, is active, approved, and formulary status is covered. Use `missing` when no PBM row exists. Use `invalid` for rejected, pending, review, inactive, not-found, or policy-mismatch rows. Map those failures to the available PBM reason codes in the template.

Classify pharmacy from the rank-1 preferred pharmacy. In-network rank-1 pharmacy is `in_network`, out-of-network is `out_of_network`, and no usable preferred pharmacy is `unknown`.

Mark address, emergency contact, and preferred-contact failures from patient demographics. A contact channel is usable only if the required detail is present: phone and sms need a phone number, email needs an email address, and portal normally needs an active chart or portal-capable contact detail.

Assign lifestyle risk from the strongest lifestyle factor. Current smoking, heavy alcohol use, no exercise, missing exercise, or very low sleep usually makes risk `high`; former smoking, moderate alcohol use, limited exercise, or borderline sleep usually makes risk `medium`; otherwise use `low`.

Assign overall risk after adding access blockers. High lifestyle risk, multiple blockers, hard coverage failures, or clinical-risk flags usually make overall risk `high`; one fixable administrative blocker or medium lifestyle risk usually makes it `medium`.

Registration status priority:

1. Use `rejected` for hard non-registerable failures such as excluded service line, expired coverage, or other non-fixable coverage mismatch.
2. Use `clinical_review` for high overall risk, PBM policy problems, out-of-network/unknown pharmacy with other risks, or clinical concerns.
3. Use `hold` for fixable administrative gaps when clinical review and rejection are not warranted.
4. Use `approved` only when there are no blocking reason codes.

## Referral Readiness Rules

Map hard blockers directly from referral fields:

- missing records: `records_received` is false.
- missing imaging: `imaging_received` is false when the task requires imaging clearance.
- authorization blocker: authorization is required and status is pending, denied, or not submitted.
- scheduled before clearance: an appointment already exists while other clearance blockers remain.

Map clinical code discrepancies by comparing referral service line, ICD metadata, diagnosis description, referral reason, and laterality. Service-family mismatch is a wrong-service-family issue. When a template asks for chapter review, compare ICD chapter to the expected chapter for the service line. Narrative or laterality mismatches are review issues even when the broad service family matches.

Readiness status priority:

1. `blocked` if any hard records, imaging, authorization, or scheduled-before-clearance blocker exists.
2. `under_review` if clinical code, narrative, laterality, duplicate, or already-scheduled review remains without a hard blocker.
3. `admin_followup` for administrative-only anomalies such as shared insurance across different patients.
4. `ready` only when no issue code remains.

Choose priority tiers from urgency and issue severity. Urgent clinical discrepancies are `tier_1_immediate`; hard blockers, duplicate review, routine clinical discrepancies, and scheduled-before-clearance issues are usually `tier_2_short_term`; administrative-only anomalies are `tier_3_administrative`. For priority lists, sort by tier first, then scheduled/clinical concerns before pure records or authorization cleanup, preserving deterministic referral ordering within equal severity.

For duplicate groups, keep the earliest or lowest referral ID as primary unless the portal explicitly marks another primary. For same-insurance different-patient anomalies, request insurance verification rather than duplicate consolidation.

For ready referral chart activation, inspect required chart artifacts such as demographics, active problems, medications, allergies, vitals, labs, and consent. If no chart exists, use `create_chart`; if a chart exists but artifacts are missing or stale, use `update_chart`; if all required artifacts are current, use `no_chart_action`. Include missing or stale artifacts only, sorted as the template requires.

## Dialysis Transfer Rules

Packet completeness is based on required documents being present and finalized. Treat absent documents, draft documents, or non-final statuses as missing. Freshness is separate from completeness.

Use these freshness windows unless the task template says otherwise:

- `hbsag`, `monthly_labs`, and `ppd_or_cxr`: 30 days before the requested start date.
- `history_physical` and `hep_b_antibody_core`: 365 days before the requested start date.

A stale finalized document appears in `stale_documents` with its received date and freshness limit, but it does not appear in `missing_required_documents`.

Capacity is available when the summed open in-center hemodialysis chairs for the requested start date and modality is greater than zero. If no capacity row exists for that date, treat open chairs as zero and capacity as unavailable.

Feasibility mapping:

- complete packet, no stale documents, capacity available: `ready_on_requested_start`.
- packet missing or stale, capacity available: `packet_not_ready_capacity_available`.
- packet missing or stale, capacity unavailable: `packet_not_ready_capacity_unavailable`.
- packet ready, capacity unavailable: `capacity_unavailable`.

Use `accept` only for packet-ready transfers with capacity. Use `clinical_review` for missing or stale clinical packet items. Use `hold` for capacity-only problems. Route packet issues to clinical nursing and the referring facility; route capacity-only issues to scheduling.

## Program Enrollment Rules

Separate clinical eligibility from enrollment disposition. A candidate can be clinically eligible and still be rejected or held because consent or chart activation is not workable.

For diabetes-hypertension programs, eligibility requires the target condition to match the program and active diabetes plus hypertension evidence in clinical history or chart artifacts. Wrong target conditions or missing active diagnoses make `eligible` false and usually produce a rejection disposition.

Disposition priority:

1. Reject wrong target condition, missing active target diagnoses, or declined consent.
2. Hold clinically eligible candidates with missing consent, inactive charts, stale active problems, or missing recent vitals, labs, medications, or consent artifacts.
3. Enroll clinically eligible candidates with signed consent and usable current chart evidence.

High-touch enrollment applies to recent hospitalization, recent emergency-department flags, or low adherence when the candidate is otherwise enrollable. Use weekly cadence, the high-touch package, and early check-in. CKD without high-touch flags usually uses biweekly cadence and the standard package. Standard enrollments usually use monthly cadence and the standard package.

Rejected candidates use no follow-up cadence and a not-applicable package. Held candidates use deferred cadence and a deferred package with consent or chart update components as appropriate.

For outreach, start from the program candidate preferred outreach channel, then fall back to the patient's preferred contact if the candidate channel is unusable. Phone and sms require a phone number, email requires an email address, and portal requires portal availability or an active chart.

## Final Validation

Before final output:

- Confirm every ID requested by the prompt or returned by the target endpoint is represented exactly once unless the template asks for grouped output.
- Confirm lists obey template ordering. Sort ID lists ascending; sort artifact and document-code lists as specified; treat reason-code arrays as unordered sets but keep deterministic ordering.
- Recompute every summary from the emitted detail rows, not from separate estimates.
- Include zero-valued count keys required by the template.
- Parse the final JSON with `jq .` or `python -m json.tool`.
