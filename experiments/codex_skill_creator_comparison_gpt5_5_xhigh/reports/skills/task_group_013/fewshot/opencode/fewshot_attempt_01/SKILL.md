---
name: cedar-ridge-intake-json
description: Use this skill for Cedar Ridge Intake Coordination Portal tasks that ask Codex to verify access, audit referral batches, review dialysis transfers, prepare chronic-care enrollment panels, reconcile referral-to-chart activation work, or return a schema-controlled JSON object from TASK_ENV_BASE_URL. It is especially relevant when prompts mention Cedar Ridge, intake coordination, rosters, referrals, transfers, program candidates, chart artifacts, ICD metadata, documents, authorization, pharmacy/PBM, readiness, blockers, or cohort summaries.
---

# Cedar Ridge Intake JSON

Use this skill to solve Cedar Ridge portal reconciliation tasks and return one valid JSON object that matches the task's `input/payloads/answer_template.json`.

## Core Workflow

1. Read the prompt, every file in `input/payloads/`, and especially `answer_template.json`.
2. Identify the target object and required population from the prompt/template:
   - roster or patient-access task: target roster and patient IDs
   - referral task: target `batch_id` and all referrals in that batch
   - transfer task: target transfer `batch_id` and all transfers in that batch
   - program task: target `program_code` and all current candidates
3. Resolve `<TASK_ENV_BASE_URL>` from the prompt. If it is a placeholder, read `environment_access.md` if present and use its `base_url`.
4. Fetch portal evidence for every target record. Prefer exact detail endpoints and filtered SQL over broad dumps.
5. Build a per-record fact table before deciding statuses. Include IDs, dates, service line/program, patient demographics, coverage/PBM/pharmacy, referral fields, ICD metadata, transfer documents/capacity, chart artifacts, and clinical history as relevant.
6. Apply the task template's controlled values and ordering rules exactly. Recompute all summary counts from your own per-record output.
7. Return JSON only. Do not include prose, markdown fences, or comments in the final answer.

## Portal Access

Use only the task environment base URL and allowed endpoints. These patterns are expected:

```bash
curl -sS "$BASE/patients/$patient_id"
curl -sS "$BASE/referrals/$referral_id"
curl -sS "$BASE/transfers/$transfer_id"
curl -sS "$BASE/chart/$patient_id"
curl -sS "$BASE/programs/$program_code/candidates"
curl -sS "$BASE/icd/$icd10_code"
```

If you need to discover records by a target batch, roster, or program and no direct list is given, use the read-only SQL endpoint with a restrictive `WHERE` clause:

```bash
curl -sS "$BASE/query" \
  -H 'content-type: application/json' \
  -d '{"query":"SELECT * FROM referrals WHERE batch_id = ?","params":["BATCH-ID-HERE"]}'
```

If the SQL endpoint does not accept `params`, send a filtered query string instead. Do not inspect unrelated batches, held-out tasks, or evaluator/source files.

## Template Discipline

- Treat `answer_template.json` as the authority for keys, constants, allowed enum values, nullability, and ordering.
- If the template has `required_value`, `expected_value`, or `constant`, copy that value from the template into the output.
- Include required empty arrays and zero-count buckets. Do not omit a key because the count is zero.
- Use `null` only where the template permits an enum-or-null or integer-or-null value.
- For unordered sets, choose a stable order: template enum order when available, otherwise alphabetic.
- Sort ID lists as the template says, usually ascending by patient, referral, transfer, group, or code.
- After drafting JSON, validate it mechanically with `jq` or a short local script, then recalculate every summary from the per-record rows.

## Shared Decision Patterns

These patterns generalize across the Cedar Ridge tasks. Always prefer explicit task/template wording over a pattern if they conflict.

### Referral Readiness and Activation

For each target referral, fetch the referral detail, patient, ICD metadata, documents, and chart if chart activation is requested.

- Clinical/code discrepancy: compare referral service line to ICD service family and expected specialty/chapter. Flag narrative mismatch when the ICD meaning does not fit the referral reason or diagnosis narrative. Flag laterality mismatch only when both sides are present and conflict.
- Hard blockers: missing records, missing imaging, and required authorization that is not approved are blocking issues.
- Existing appointments before clearance are not ready; include the template's existing-appointment or scheduled-before-clearance code.
- Duplicate handling: group repeated referrals for the same patient and same clinical purpose, especially when notes or referral-office data indicate duplication. Keep the earliest or explicit primary referral.
- Shared insurance anomaly: the same insurance/policy ID on different patients needs verification; the same patient in a duplicate group can be legitimate duplicate handling instead.
- Readiness precedence: hard blockers make the referral `blocked`; clinical/code discrepancy, duplicate review, or uncleared scheduled appointment generally makes it `under_review`; pure insurance/admin follow-up generally makes it `admin_followup`; no issues makes it `ready`.
- Priority: urgent clinical discrepancies are usually immediate; hard blockers and duplicate/appointment review are short-term; pure administrative insurance checks are administrative. Rank non-ready referrals by tier, then urgency/date, then referral ID unless the template specifies another ordering.
- Correspondence/action mapping: code clarification for clinical/code issues, authorization/records request for auth or record blockers, duplicate resolution for duplicate review, and appointment hold notice for already scheduled uncleared referrals.
- Chart activation: only produce ready-referral chart work when the output asks for it. Compare required artifacts in the template with `/chart/{patient_id}`. Missing or stale artifacts need creation/update. Existing charts use update actions; absent charts use create actions; complete current charts need no chart action.

### New Patient Access Verification

For each target patient, use the roster record for requested service date and service line, then fetch patient, coverage, PBM, preferred pharmacies, lifestyle, and clinical history.

- Insurance is valid only when coverage is active on the requested date and includes the requested service line. Expired, pending, absent, or excluded service-line coverage should map to the matching template status/reason code.
- Prescription benefit is valid only when PBM is active, approved, and tied to the current coverage policy. Inactive/rejected/pending PBM records are invalid; absent records are missing; policy mismatches should use the template's mismatch code.
- Preferred pharmacy status comes from the top-ranked preferred pharmacy. Use in-network, out-of-network, or unknown according to that record.
- Preferred contact is unavailable when the selected contact route cannot be used: email needs an email address, phone/SMS needs a phone number, and portal generally needs an active chart or portal-capable profile.
- Address and emergency-contact gaps are independent administrative blockers when the template includes them.
- Lifestyle risk rises with current smoking, heavy alcohol use, no/unknown exercise, short sleep, and similar risk flags. Overall risk should be at least the lifestyle risk and should increase for unresolved coverage, PBM, pharmacy, demographic, or clinical-history risks.
- Registration status: approve only patients with no blockers and acceptable overall risk. Use clinical review for high clinical/lifestyle risk or multiple fixable blockers, hold for purely pending administrative items, and reject for nonrecoverable coverage/service-line exclusion or equivalent hard failure.

### Dialysis Transfer Review

For each target transfer, fetch the transfer detail. The detail should include transfer fields, packet documents, patient, and capacity.

- Packet completeness is about presence/finalization, not freshness. A required packet item is missing when absent, draft, not finalized, or represented by a required transfer field that is null.
- Stale documents are separate from missing documents. Compare each relevant document's `received_date` to the transfer's requested start date. Use freshness limits from the template when present; common limits are 30 days for current infection/lab screening documents and 365 days for history/physical.
- Capacity must match the exact requested start date and requested modality. Sum open chairs across locations on that exact date. If there are no matching rows or the sum is zero, capacity is unavailable.
- Feasibility combines packet readiness and capacity: ready on requested start only if no missing/stale packet issue and capacity is available; otherwise use the template's combined packet/capacity value.
- Intake decision: accept when packet is ready and capacity is available; hold for capacity-only scheduling problems; clinical review for stale clinical documents or clinical packet gaps; use intake/admin follow-up for purely administrative missing items when the template separates them.
- Contact owner/route: clinical nurse for clinical packet or freshness problems, intake coordinator for administrative packet gaps, scheduling coordinator for capacity-only issues, and none when no follow-up is needed. Fax the referring facility for packet corrections, phone the patient for patient logistics, and use an internal queue for scheduling-only work.

### Chronic-Care Enrollment Panels

For each program candidate, fetch the candidate list and each candidate's chart/patient details.

- Eligibility is based on the program's target condition and active diagnoses/clinical history, not on consent or chart readiness alone.
- For diabetes/hypertension programs, look for both diabetes and hypertension in the target condition or active clinical history. Wrong target condition or absent active diagnosis makes the candidate ineligible.
- Consent declined generally rejects; consent missing generally holds unless the candidate is already ineligible for the target condition.
- Chart-not-active and stale/missing artifacts are disposition reasons when the candidate is otherwise clinically relevant. Do not request chart cleanup for a patient rejected solely as the wrong program population unless the template explicitly asks for it.
- High-touch reasons include recent hospitalization, very low adherence, recent ED visit flags, or other high-risk flags. CKD commonly moves an otherwise standard candidate to biweekly monitoring.
- Follow-up cadence: weekly for high-touch enrollment, biweekly for CKD monitoring, monthly for standard enrollment, deferred for holds, and none for rejects.
- Outreach channel should use the candidate's preferred outreach when reachable. Portal requires portal/chart availability; phone or SMS requires a phone number; email requires an email address. If preferred outreach is not reachable, fall back to another available route allowed by the template.
- Initial monitoring package: high-touch packages include the standard devices/orders plus care-plan setup; standard packages include the monitoring devices and lab orders, adding medication reconciliation when chart/clinical context calls for it; deferred packages include consent and chart-update requests; rejected candidates use not-applicable.

## Final Validation Checklist

Before final answer:

- All target records from the prompt/template are present exactly once.
- No non-target records are included.
- Every enum value appears in the template.
- Required constants and dates came from the template or portal, not memory.
- Lists follow the template ordering.
- Blocker/action/reason arrays contain no duplicates.
- Summary counts equal the detailed rows.
- The final message is a single parseable JSON object.
