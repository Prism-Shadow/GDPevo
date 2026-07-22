---
name: cedar-ridge-intake-reconciliation
description: Reconcile Cedar Ridge intake portal data into strict JSON templates for patient access verification, specialty referral readiness, dialysis transfer packets, chronic-care program panels, and referral-to-chart activation. Use when a task provides Cedar Ridge portal data plus an answer template and asks for controlled-value intake, referral, transfer, program enrollment, or chart activation output.
---

# Cedar Ridge Intake Reconciliation

## Core Workflow

1. Read the prompt and answer template first. Treat the template as the contract for required keys, allowed values, ordering, and count fields.
2. Identify the target cohort from the prompt and template: roster, referral batch, transfer batch, program code, or explicit patient/referral/transfer IDs.
3. Pull structured portal data for only that cohort. Prefer database or JSON joins over screen scraping or manual transcription.
4. Join the cohort to all relevant support tables before deciding statuses:
   - Patient demographics and contact availability.
   - Coverage, PBM, pharmacy preference, lifestyle, and clinical history for access verification.
   - ICD metadata, referral flags, duplicate indicators, authorization fields, and chart artifacts for referrals.
   - Transfer request rows, finalized packet documents, transportation, and capacity for dialysis transfer work.
   - Program candidates, chart artifacts, and clinical history for chronic-care enrollment.
5. Derive controlled values from source records, then build the exact JSON shape. Sort rows and nested lists as the template specifies. Treat reason-code arrays as sets unless the template says otherwise.
6. Recompute every summary count from the final row-level objects, not from an earlier draft.
7. Return JSON only when the task asks for JSON. Do not add prose, comments, or extra fields.

## Shared Normalization

- Count a document as present only when it is finalized or clearly final. Draft, absent, or non-final documents are missing.
- Treat stale chart artifacts as not usable for activation or enrollment. Report the stale reason when the template provides one, and include the corresponding artifact in work-to-create lists when current chart content is required.
- Prefer explicit row flags for referral blockers such as records, imaging, authorization, and scheduled appointment state. Use document rows to confirm packet completeness and chart activation work.
- Map availability from actual usable values: a missing phone blocks phone or SMS contact, a missing email blocks email or portal contact when the workflow requires that channel, and a missing transportation value blocks transfer packet readiness when transportation is a required packet element.
- Use exact controlled enum strings from the template. If a source status has more detail than the template, collapse it to the closest allowed value and carry the detail in the allowed reason code.

## Access Verification

For new-patient access rosters:

- Coverage is valid only when it is active, in network, includes the requested service line, and covers the requested service date. Expired coverage, pending coverage, absent coverage, and excluded service lines map to separate blocker codes when those values exist.
- Prescription benefit is valid only when PBM data is active, approved, covered, and matches the medical coverage payer or policy. Rejected/inactive PBM data is invalid; absent PBM data is missing; policy mismatch gets its own blocker when available.
- Use the first-preference pharmacy network status for pharmacy status. Missing pharmacy data is unknown.
- Lifestyle risk should consider current smoking, heavy alcohol use, no or missing exercise, and short sleep. Overall risk should also consider chronic condition burden, high medication counts, recent hospitalization, and explicit risk flags.
- Registration status should distinguish administrative holds from clinical review and hard rejection. Use clinical review for high overall clinical risk when the record is otherwise workable; use hold for fixable administrative gaps; use rejection for hard coverage or service-line exclusion when the template supports it.

## Referral Readiness

For specialty referral batches:

- Compare ICD metadata to the requested service line. Flag wrong service family. When the template asks for chapter, narrative, or laterality discrepancies, compare the code chapter and laterality against the specialty expectation and referral narrative or reason.
- Do not flag a symptom code solely because it is a symptom chapter if its ICD metadata service family fits the specialty and the referral reason is clinically compatible.
- Flag clinical reason mismatch when the referral reason is incompatible with the specialty or code, such as a pain-only reason for a non-pain specialty.
- Records, imaging, and authorization blockers come from referral flags. Authorization is blocked when authorization is required and status is pending, denied, or not submitted.
- Treat an appointment scheduled before unresolved clearance as an appointment or scheduled-before-clearance blocker.
- Detect duplicate groups from same-patient repeated referrals, shared referral contact details, duplicate notes, or repeated insurance identifiers. Choose the primary referral from the earliest or otherwise complete referral and put secondary referrals into administrative follow-up. If a possible-duplicate note does not identify a true duplicate, list it as cleared when the template provides a cleared-duplicates field.
- Shared insurance across different patients is an anomaly, not a same-patient duplicate. Verify distinct patient policy ID when the template has that disposition.
- Readiness status precedence:
  - `blocked` for missing records, missing imaging, authorization blockers, or scheduled-before-clearance blockers.
  - `under_review` for clinical code, narrative, laterality, or shared-insurance anomalies without hard blockers.
  - `admin_followup` for duplicate consolidation or already-scheduled administrative review without clinical or hard blockers.
  - `ready` only when no unresolved blocker, discrepancy, duplicate, or administrative review remains.
- Priority tiers should reflect urgency and operational risk: urgent clinical issues and scheduled-before-clearance cases are immediate, routine clinical/auth/records work is short term, and pure duplicate or appointment administration is administrative.

## Dialysis Transfer Packets

For seasonal dialysis transfer reviews:

- Required packet documents come from the template. Draft or absent required documents are missing. Use the transfer request transportation field to satisfy transportation when the template treats it as required.
- Use these default Cedar Ridge freshness windows unless the task provides different limits: monthly labs 30 days, HBsAg 90 days, history and physical 90 days, PPD or CXR 365 days, hepatitis B core antibody 365 days.
- Compare freshness against the requested start date. Include stale document objects sorted by document type.
- Capacity is available only when the requested start date has positive open in-center hemodialysis chair capacity. Sum capacity across locations for the requested modality.
- Feasibility mapping:
  - Complete and fresh packet plus capacity available: ready on requested start.
  - Packet not ready plus capacity available: packet not ready, capacity available.
  - Packet not ready plus no capacity: packet not ready, capacity unavailable.
  - Complete packet plus no capacity: capacity unavailable.
- Missing or stale clinical packet items should route to clinical review or clinical nurse follow-up when the template supports it. Pure capacity issues route to scheduling. Accepted transfers need no next contact.

## Chronic-Care Enrollment Panels

For program candidate panels:

- Clinical eligibility is based on the program target condition and active clinical history, not solely on consent or chart readiness. Use the enrollment status to express operational disposition.
- For a diabetes-hypertension program, require diabetes and hypertension in active conditions. Add `wrong_target_condition` when the candidate target condition does not match and `missing_active_dmhtn_diagnosis` when the chart lacks the active diagnosis pair.
- Consent declined is a rejection. Consent missing is a hold unless another hard ineligibility reason requires rejection.
- Missing or stale current chart support creates hold reasons: active problems, vitals, labs, medication list, consent, or chart record.
- High-touch reasons:
  - Recent hospitalization: weekly follow-up.
  - Low adherence score, usually below 50: weekly follow-up.
  - Recent ED risk flag: weekly follow-up.
  - CKD comorbidity: biweekly monitoring unless a weekly high-touch reason also applies.
  - Otherwise eligible candidates get monthly follow-up.
- Outreach should use the candidate preferred outreach channel when actionable; use none for rejected candidates unless the template explicitly asks for rejection outreach.
- Monitoring packages:
  - Standard enrollment: BP cuff, glucometer, labs order, medication reconciliation, and care-plan setup.
  - High-touch enrollment: same core components with the high-touch package type and shorter first check-in.
  - Deferred hold: consent packet and chart update request as applicable.
  - Rejection: not applicable with no components.

## Referral-To-Chart Activation

For activation files:

- Build referral readiness first, then chart actions only for referrals that can move forward.
- `create_chart` when the patient lacks an active chart; `update_chart` when a chart exists but required artifacts are missing or stale; `no_chart_action` only when all required artifacts are current.
- Required activation artifacts commonly include demographics, active problems, medications, allergies, vitals, labs, and consent. Include only the artifacts that must be created or refreshed, sorted alphabetically by the enum string.
- Correspondence template mapping:
  - Wrong service family or clinical reason mismatch: clinical code clarification.
  - Missing records plus authorization denial or pending authorization: authorization/records request.
  - True duplicate review: duplicate resolution.
  - Already scheduled before clearance: appointment hold notice.
- Priority order should include non-ready referrals only, ranked first by priority tier and then by clinical or operational severity.
