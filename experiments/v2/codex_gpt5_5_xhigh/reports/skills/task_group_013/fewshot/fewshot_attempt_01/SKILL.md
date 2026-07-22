---
name: cedar-ridge-intake-reconciliation
description: Reconcile Cedar Ridge Intake Coordination Portal data into constrained JSON outputs. Use when a task asks Codex to audit or prepare Cedar Ridge patient access rosters, referral batches, dialysis transfers, chronic-care program enrollment panels, referral-to-chart activation, or similar intake workflows using TASK_ENV_BASE_URL and an answer_template.json schema.
---

# Cedar Ridge Intake Reconciliation

## Core Workflow

1. Read the user prompt and every file under `input/payloads/` before querying the portal. Treat `answer_template.json` as the source of truth for required keys, constants, controlled values, list ordering, nullability, and summary fields.
2. Use the base URL from `environment_access.md`. Use only the listed Cedar Ridge endpoints and the read-only `POST /query` endpoint.
3. Scope records from the prompt/template: roster ID, referral batch ID, transfer batch ID, program code, and any required patient/referral/transfer IDs. Do not reuse IDs, dates, counts, or row outcomes from prior examples.
4. Prefer one `POST /query` SELECT with joins for batch work, then use REST endpoints for spot checks:
   - `patients`, `clinical_history`, `chart_artifacts`
   - `intake_rosters`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`
   - `referrals`, `icd_codes`, `documents`
   - `transfer_requests`, `facility_capacity`
   - `program_candidates`
5. Build intermediate issue sets per patient/referral/transfer. Derive summaries from the final rows, not from separate assumptions.
6. Validate the final object against the template: required keys present, constants copied from the template/prompt, enum values allowed, lists ordered as specified, count fields internally consistent, and no prose outside JSON.

Use `/query` like:

```bash
curl -sS -X POST "$TASK_ENV_BASE_URL/query" \
  -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT ..."}'
```

Check `row_count` and `truncated`; rerun narrower queries if needed.

## Access Roster Rules

For new-patient access or registration rosters, query `intake_rosters` by roster ID and join patient, coverage, PBM, preferred pharmacy, lifestyle, and clinical history.

- Coverage is valid only when a coverage row exists, status is active, the requested service date is within the effective/termination window, network is acceptable, and the roster service line appears in the coverage service-line list.
- Coverage blockers map from the failing field: expired/terminated coverage, pending coverage, excluded service line, or missing coverage. Missing address is a separate demographic blocker.
- PBM is valid only when the PBM row exists, is active, approved, covered by formulary, and matches the medical coverage payer/policy. Map inactive/rejected/pending/review/not-found states to PBM invalid, absent rows to PBM missing, and payer/policy mismatch to PBM policy mismatch.
- Preferred pharmacy status comes from `patient_pharmacy` rank 1 joined to `pharmacies.network_status`; use unknown when no preferred pharmacy can be verified.
- Preferred-contact blockers apply when the preferred channel is unusable: email requires email, phone/sms requires phone, and portal requires an active/existing chart. Emergency-contact absence is its own blocker.
- Lifestyle risk is high for current smoking, heavy alcohol use, no/unknown exercise, or short sleep; medium for former smoking, moderate alcohol, mild sleep/exercise concerns; low only when no material lifestyle concern is present.
- Overall risk is high for high lifestyle risk, recent hospitalization, nonempty clinical risk flags, complex medication burden, or multiple serious chronic conditions; medium for moderate lifestyle/clinical burden; low otherwise. Add the high-risk blocker when overall risk is high.
- Registration disposition should follow severity: reject for disqualifying coverage such as expired coverage or excluded service line; clinical review for high clinical risk or clinical/PBM conflicts; hold for administrative or pending items when not otherwise rejected/reviewed; approve only when no blockers remain.

## Referral Audit And Activation Rules

For referral batches, query `referrals` by `batch_id`, join `icd_codes`, and join patients/chart artifacts when chart activation is requested.

- Clinical code discrepancies:
  - Flag service-family mismatch when `icd_codes.service_family` does not match the referral service line.
  - Flag chapter mismatch when the task expects a service-line ICD chapter and `icd_codes.chapter` falls outside it. Orthopedic readiness tasks commonly expect musculoskeletal `M00-M99`; injury `S00-T88` codes should be reviewed unless the task explicitly accepts trauma/injury.
  - Flag narrative mismatch when `diagnosis_description` or `referral_reason` is clinically inconsistent with the ICD description/service line.
  - Flag laterality mismatch when left/right terms in the referral text conflict with `icd_codes.laterality`.
- Referral blockers:
  - `records_received = 0` means records missing.
  - `imaging_received = 0` means imaging missing when the template tracks imaging.
  - `auth_required = 1` with status pending, denied, or not submitted is an authorization blocker.
  - `appointment_scheduled = 1` before clearance requires appointment/scheduled-before-clearance review.
- Duplicate handling:
  - Group same-patient duplicate referrals in the same batch when patient, insurance, ICD/reason, or fax/phone indicates a repeated referral; keep the earliest/lowest referral ID unless the portal notes identify a primary.
  - Treat shared insurance IDs across different patients as shared-insurance anomalies, not ordinary duplicate referrals.
  - If rows are only marked possible duplicates but patient/insurance/clinical facts do not match, clear duplicate review when the template has such a field.
- Readiness precedence:
  - `ready`: no clinical, administrative, authorization, records, imaging, duplicate, or appointment issues.
  - `blocked`: records/imaging/auth blockers, even if clinical issues also exist.
  - `under_review`: clinical code/narrative/laterality, duplicate, or scheduled-before-clearance issues without hard missing/auth blockers.
  - `admin_followup`: insurance/admin-only anomalies.
- Priority:
  - Tier 1 for urgent clinical-code, service-family, narrative, or laterality issues.
  - Tier 2 for hard blockers, routine clinical review, duplicate consolidation, or scheduled-before-clearance work.
  - Tier 3 for administrative-only follow-up.
  - Rank non-ready referrals by tier, then scheduled-before-clearance/urgent safety concerns, then ascending referral ID unless the template says otherwise.
- Action/correspondence mapping: code discrepancies need corrected ICD or clinical-code clarification; narrative issues need narrative confirmation; laterality issues need laterality confirmation; duplicates need consolidation or duplicate-resolution correspondence; shared insurance needs policy verification; missing records/imaging/auth need the matching request or authorization action; scheduled-before-clearance needs appointment hold/review.
- Chart activation for ready referrals: inspect `chart_artifacts`. Create/update required artifacts that are missing or stale. Existing charts generally need update actions; patients without charts need create actions. Sort artifact lists as the template requires.

## Dialysis Transfer Rules

For transfer batches, query `transfer_requests`, related `documents`, and `facility_capacity`.

- A required packet document is present only when a matching document row exists for the transfer, status is final, and `finalized = 1`. Draft, non-final, and absent rows are missing.
- Treat `transportation` as satisfied by the transfer row when the template includes it; null/empty transportation is missing.
- Sort missing document codes alphabetically unless the template specifies another order.
- Freshness is measured from each transfer's requested start date. Use these default limits unless the template overrides them:
  - `hbsag`, `monthly_labs`, `ppd_or_cxr`: 30 days
  - `history_physical`, `hep_b_antibody_core`: 365 days
- Capacity is available only when `facility_capacity` has open chairs for the exact requested start date and modality. Sum open chairs across locations.
- Feasibility values follow packet readiness and capacity:
  - packet complete/fresh and capacity available: ready on requested start
  - packet incomplete or stale and capacity available: packet not ready, capacity available
  - packet incomplete or stale and capacity unavailable: packet not ready, capacity unavailable
  - packet ready and capacity unavailable: capacity unavailable
- Intake decision/contact:
  - Accept only when packet is complete/fresh and capacity is available.
  - Hold when the packet is ready but scheduling/capacity or admin-only work remains.
  - Clinical review when any clinical packet document is missing or stale.
  - Route clinical packet gaps to the clinical nurse/referring facility, admin/insurance/transportation gaps to intake or patient contact, capacity-only work to scheduling/internal queue, and accepted cases to none.

## Program Enrollment Rules

For program panels, get candidates from `/programs/{program_code}/candidates` or `program_candidates`, then join patients, clinical history, and chart artifacts. Include every current candidate returned for the program and sort as the template specifies.

- Use an explicit as-of date from the prompt/template/portal metadata when present. Do not derive it from the maximum candidate date. If no date is exposed, use the task's stated current panel date.
- Determine target-condition eligibility from `target_condition` and `clinical_history.chronic_conditions`. Common mappings: diabetes-hypertension requires both diabetes and hypertension; renal-diabetes requires diabetes plus CKD/renal disease; COPD requires COPD; CAD/cardiology programs require CAD/cardiac history.
- Consent and chart status affect disposition but do not by themselves change target-condition eligibility.
- Reason-code mapping:
  - Add the program criteria code when the target condition is met.
  - Add high-touch codes for recent hospitalization, recent ED risk flags, or low adherence when the template allows them.
  - Add CKD/renal monitoring codes when CKD is present and no higher-touch cadence applies.
  - Add consent declined/missing, chart not active, stale active problems, missing recent vitals/labs/medications, wrong target condition, and missing active diagnosis codes from the corresponding candidate/chart/history facts.
- Disposition:
  - Enroll eligible candidates with signed consent and required current chart artifacts.
  - Hold eligible candidates with missing consent or remediable chart gaps.
  - Reject ineligible candidates and candidates who declined consent, unless the template instructs a different disposition.
- Missing chart artifacts should include only allowed template values. For eligible chart-gap cases, include `chart_record` when no active chart exists; include stale/missing active problems, vitals, labs, medications, and consent as applicable. For ineligible rejections, avoid adding chart artifacts unless the template specifically asks for chart remediation.
- Outreach uses `preferred_outreach` only if usable: portal requires an existing chart, email requires email, and phone/sms requires phone. If unusable, fall back to patient preferred contact, then any available channel, then none.
- Monitoring package:
  - High-touch packages for hospitalization, ED, or low-adherence high-touch cases; weekly cadence and early check-in.
  - Standard packages for routine eligible candidates; monthly cadence unless CKD/renal monitoring sets biweekly cadence.
  - Deferred package with consent/chart update components for holds.
  - Not applicable package with no components for rejected/ineligible candidates.

## Final JSON Checks

- Use constants from the template and prompt for `task_id`, `batch_id`, `roster_id`, `program_code`, service date, and service line.
- Preserve required list ordering exactly: usually ascending ID, alphabetical code, or explicit priority rank.
- Treat issue/reason/blocker arrays marked unordered as sets: no duplicates; use only allowed enum strings.
- Include zero counts for every required count key, even when absent from the data.
- Recompute summary counts from the final rows after all status decisions are complete.
- Return JSON only when the prompt asks for JSON only.
