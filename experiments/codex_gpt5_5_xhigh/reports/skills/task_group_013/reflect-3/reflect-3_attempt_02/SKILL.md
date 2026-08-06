---
name: cedar-ridge-intake-reconciliation
description: Reconcile Cedar Ridge intake coordination tasks into controlled JSON outputs. Use when Codex must prepare roster access verification, specialty referral readiness, dialysis transfer intake, chronic-care enrollment panels, or referral-to-chart activation files from task prompts, answer templates, and Cedar Ridge patient/chart/document/coverage/ICD/capacity data.
---

# Cedar Ridge Intake Reconciliation

## Core Workflow

1. Read the prompt and answer template before analyzing records. Treat the template as the contract for top-level keys, item keys, enums, ordering, nullability, and summary count buckets.
2. Identify the target cohort from the prompt/template: roster, referral batch, transfer batch, program code, or explicit patient/referral/transfer IDs.
3. Gather only target rows and directly related records: patient demographics, coverage, PBM, preferred pharmacy, lifestyle, ICD metadata, documents, chart artifacts, clinical history, and capacity as relevant to the template.
4. Normalize every output value to the template enums exactly. Do not invent reason codes, statuses, summary keys, or explanatory fields.
5. Apply the template ordering literally. Sort ID lists ascending unless the template specifies another order; sort unordered reason-code sets deterministically for readability.
6. Recompute summaries from the finished per-patient or per-referral rows. Include all required zero-count keys when the template names fixed count buckets.
7. Return JSON only when the task asks for JSON. Before finalizing, verify required top-level keys, cohort completeness, ID ordering, controlled values, and count reconciliation.

## Access Verification

- Mark insurance `valid` only when coverage exists, is active for the requested date, is in network, and includes the requested service line. Use invalid or missing status and reason codes for expired, pending, absent, or service-excluded coverage.
- Mark prescription benefits `valid` only when PBM coverage exists, is active/approved, matches the coverage policy when policy numbers are present, and has an acceptable formulary status. Use PBM invalid/missing/policy-mismatch reason codes where the template allows them.
- Use the rank-1 preferred pharmacy when a preference is present; derive pharmacy network status from the pharmacy record, not from payer coverage.
- Add contact and demographic blockers only when the requested/preferred route cannot work from the patient record, such as missing phone for phone/SMS or missing email for email/portal workflows.
- Treat lifestyle risk as separate from administrative access blockers. Current smoking, heavy alcohol use, no exercise, and short sleep increase lifestyle risk; combine lifestyle risk with access blockers to determine overall risk.
- Use `approved` only when no blocking reasons remain. Prefer `hold` for remediable administrative blockers, `clinical_review` for high clinical/lifestyle concern, and `rejected` for non-covered, expired, or excluded core access when the template provides those statuses.

## Referral Readiness

- Compare each referral's service line with ICD metadata. A service-family mismatch is a clinical code discrepancy; when a template distinguishes reason types, use the code for wrong service family.
- Compare the referral narrative/reason with the ICD description. Use clinical or narrative mismatch codes when the reason does not support the diagnosis, even if the broad service family is correct.
- For laterality-specific ICD codes, require the referral narrative or supporting record to confirm the same side. Missing or conflicting side information is a laterality discrepancy.
- Treat `records_received`, `imaging_received`, and authorization fields as hard readiness signals. Missing required records/imaging and denied, pending, or not-submitted authorizations block scheduling unless the template says otherwise.
- Treat an appointment already scheduled before clearance as an administrative blocker or hold-notice item when the template includes that code.
- Do not rely on a "possible duplicate" note alone. Confirm duplicates by matching patient identity and/or shared policy/referral identifiers. Clear duplicate review when rows are different patients with distinct identifiers and no duplicate evidence.
- For repeated insurance IDs, distinguish same-patient legitimate duplicates from different-patient policy anomalies. Keep both duplicate groups and shared-insurance anomaly lists sorted as specified.
- Use `ready` only when no clinical, authorization, document, appointment, or duplicate/admin blockers remain. Use `blocked` for hard missing/auth blockers, `under_review` for clinical code/narrative/laterality issues, and `admin_followup` for duplicate, shared-policy, scheduling, or clerical follow-up.
- Priority usually follows patient impact first: urgent clinical clarification or denied authorization, then routine clinical/hard blockers, then administrative cleanup.

## Transfer Intake

- Use the required document list from the template. A document that is absent, draft, or not finalized counts as missing.
- Evaluate stale documents separately from missing documents. Use the requested start date as the freshness anchor and apply any freshness limits given by the template or task domain.
- Treat short-window dialysis packet items conservatively; monthly labs and HBsAg are commonly short-freshness items. TB screening and history/physical are usually longer-window items unless the task specifies otherwise.
- Include only stale document types allowed by the template, with received date and freshness limit. Keep stale and missing lists in the template order.
- Sum open chairs across all relevant locations for the requested start date and modality. If no capacity record exists for that date/modality, treat capacity as unavailable with zero open chairs.
- `ready_on_requested_start` requires a ready packet and available capacity. Use packet-not-ready feasibility when missing or stale packet items remain; use capacity-unavailable feasibility when capacity alone blocks the request.
- Final decisions should separate clean accepts, administrative holds for missing packet/capacity work, and clinical review for stale clinical documents when no administrative packet gap remains.
- Choose the next-contact owner from the dominant blocker: clinical nurse for stale clinical review, intake coordinator for missing packet items, scheduling coordinator for capacity-only issues, and none for accepted transfers.

## Program Enrollment Panels

- Separate clinical eligibility from enrollment disposition. A candidate can meet clinical criteria but still be held or rejected because consent, target condition, or chart readiness fails.
- For DM/HTN panels, clinical eligibility requires the correct target condition plus active diabetes and hypertension evidence in clinical history or active problems. Wrong target condition or missing active DM/HTN evidence makes the candidate ineligible.
- Consent declined normally rejects enrollment. Consent missing usually holds a clinically eligible candidate and should add consent to missing chart artifacts when the template allows it.
- Existing chart and chart-artifact status are distinct. Add chart-not-active when the patient record lacks an active chart; add stale or missing artifact reason codes from chart artifact status and absent required artifacts.
- High-touch cadence comes from recent hospitalization, recent ED flags, or low adherence. CKD drives biweekly monitoring unless a higher-touch weekly reason is present. Uncomplicated enrolled patients are usually monthly.
- Use a reachable outreach channel. Start with the program's preferred outreach value, then fall back to an available patient contact method when the preferred channel cannot work; use `none` when no outreach should occur.
- Select monitoring package type from disposition and intensity: high-touch for high-touch enrollments, standard for uncomplicated enrollments, deferred for holds needing consent/chart updates, and not applicable for rejects.

## Chart Activation

- Include chart activation needs only for referrals that may move forward unless the template requests all referrals.
- Use `create_chart` when no active chart exists, `update_chart` when a chart exists but required artifacts are missing or stale, and `no_chart_action` only when required chart artifacts are current.
- For artifacts to create or update, include stale required artifacts and absent required artifacts. Use only template-allowed artifact names and sort them as specified.
- Keep correspondence queues limited to referrals requiring external clarification or notification. Match the template type to the dominant issue: clinical code clarification, authorization/records request, duplicate resolution, or appointment hold notice.
