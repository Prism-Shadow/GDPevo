# Cedar Ridge Reconciliation Rules

Use this reference after reading the prompt, payloads, and portal records. It captures reusable patterns from the Cedar Ridge task family without task-specific completed answers.

## Portal Data Model

Common SQL tables and endpoint-backed concepts:

- `patients`: demographics, preferred contact, address, existing chart, emergency contact.
- `coverage`: payer, active dates, network status, status, and supported service lines.
- `pbm`: prescription-benefit status, active flag, payer/policy details, formulary status, specialty flag.
- `patient_pharmacy` plus `pharmacies`: preferred pharmacy and network status.
- `lifestyle`: smoking, alcohol, exercise, and sleep fields used for lifestyle risk.
- `intake_rosters`: roster membership, requested service date, and service line.
- `referrals`: batch, patient, ICD, service line, records/imaging flags, authorization, appointment, urgency, and insurance ID.
- `icd_codes`: chapter, service family, description, and laterality.
- `documents`: transfer/referral packet documents, finalization, dates, and document type.
- `transfer_requests`: dialysis transfer batch, patient, requested start/end, modality, chair window, transportation.
- `facility_capacity`: open chairs by date, modality, and location.
- `program_candidates`: chronic-care program candidates, consent, outreach, adherence, target condition.
- `chart_artifacts` and `clinical_history`: chart completeness, freshness, diagnoses, recent events, medication/allergy counts, and risk flags.

## General Normalization

- Use the template's controlled values exactly. Do not invent status names or reason codes.
- A missing/null source field is different from a negative source field. Preserve that distinction when the template has `missing`, `unknown`, `none`, or `not_applicable`.
- For required empty categories, emit empty arrays or zero-valued count keys rather than omitting keys.
- For duplicate or shared-identifier analysis, group only within the target cohort unless the prompt explicitly asks for cross-batch review.
- For summary counts, count each emitted row once per requested bucket. For issue-count summaries, count affected referrals/patients unless the template asks for raw issue occurrences.

## Patient Access Verification

Use roster rows to get the requested service date and service line. For each target patient:

- Insurance is valid when a coverage row is active for the requested service date, has an acceptable status, and includes the requested service line. Map expired, pending, absent, or service-line-excluded coverage to the matching template reason code.
- Prescription status comes from PBM rows. Active, compatible PBM data is valid. Missing PBM rows produce missing status/reason codes; inactive, invalid, or payer/policy mismatches produce invalid status/reason codes.
- Preferred pharmacy status comes from the highest-ranked patient pharmacy joined to `pharmacies.network_status`. Use `unknown` when no usable preferred pharmacy can be resolved.
- Missing address, unavailable preferred contact, and missing emergency contact are independent administrative blockers.
- Lifestyle risk is derived from lifestyle risk factors such as current smoking, heavy alcohol use, low exercise, and poor sleep. Use the prompt/template risk buckets, and let strong adverse factors drive high risk.
- Overall risk should reflect the highest relevant clinical/lifestyle and administrative risk. High overall risk usually triggers clinical review unless a rejection-class coverage/service-line problem takes precedence.
- Registration status precedence is: rejection-class coverage or service-line blockers, then clinical review for high overall/clinical risk or unresolved clinical blockers, then hold for administrative/PBM/contact/pharmacy blockers, otherwise approved.

## Specialty Referral Readiness And Chart Activation

For each target referral:

- Join referrals to ICD metadata. A referral is clinically discrepant when the referral service line conflicts with the ICD service family, the diagnosis narrative conflicts with the referral reason, or laterality in the narrative/referral conflicts with ICD laterality.
- Records, imaging, and authorization blockers come directly from `records_received`, `imaging_received`, `auth_required`, and `auth_status`. Treat denied, pending, or not-submitted authorization as blockers when authorization is required.
- Appointment already scheduled before clearance is a separate review blocker when the template includes it.
- Duplicate review usually groups same-patient referrals in the target cohort for the same service family/reason. Keep the earliest or otherwise primary referral when the portal marks one as primary; otherwise justify by received date and referral ID.
- Shared insurance anomalies are same insurance IDs across distinct patients in the target cohort. Same patient reuse is usually a legitimate duplicate rather than a distinct-patient anomaly.
- Readiness precedence: missing records/imaging/authorization blockers make the referral `blocked`; clinical-code or duplicate/scheduled review makes it `under_review`; insurance-only administrative anomalies make it `admin_followup`; no blockers makes it `ready`.
- Priority tiers should reflect urgency and operational severity: urgent clinical-code discrepancies first, then blocked clinical/authorization/document work, then duplicate or already-scheduled reviews, then administrative insurance checks.
- Action/correspondence codes should mirror blocker codes: corrected ICD or clinical clarification for code discrepancies, records/imaging requests for missing documents, authorization resolution for auth blockers, duplicate resolution for duplicate review, appointment hold/review for scheduled-before-clearance.
- For ready referral chart needs, compare required chart artifacts in the template with current chart artifacts. Use `create_chart` when no chart exists, `update_chart` when chart artifacts are missing/stale, and `no_chart_action` only when nothing remains.

## Dialysis Transfer Packet And Capacity Review

For each target transfer:

- Count only finalized documents as satisfying required packet items unless the prompt says drafts are acceptable.
- Required packet items come from the template's allowed document codes. Missing required documents are absent finalized document types.
- Stale document checks are date based. Compare `received_date` to the requested start date. Common freshness limits are 30 days for infection/lab/screening items and 365 days for history and physical items, unless the portal or prompt provides a more specific policy.
- Packet completeness is about missing required finalized documents. A packet can be complete but still not ready when stale documents exist.
- Capacity is the sum of open in-center hemodialysis chairs across relevant Cedar Ridge locations for the requested start date and modality.
- Requested-start feasibility combines packet readiness and capacity availability. Distinguish packet-not-ready/capacity-available from packet-not-ready/capacity-unavailable and capacity-unavailable-only cases.
- Intake decision should be `accept` only when documents are complete, freshness checks pass, and capacity is available. Use clinical review for stale or clinical packet problems, hold for nonclinical scheduling/capacity/admin problems, and route next contact to the owner implied by the blocking work.

## Chronic-Care Program Enrollment

For each target program candidate:

- Candidate target condition controls basic clinical eligibility. Wrong target condition or missing active target diagnosis is rejection-class.
- Consent declined is rejection-class. Consent missing is hold/deferred unless the template says to reject.
- Existing chart and chart artifacts drive missing artifact codes. If no chart exists, chart-level artifacts may all need creation or update depending on the template.
- Stale active problems, missing recent vitals/labs, missing medication list, and missing consent map directly from `chart_artifacts` status/freshness and candidate consent.
- High-touch enrollment is driven by recent hospitalization, recent ED/risk flags, low adherence, or other high-risk clinical history. CKD or similar risk flags often imply biweekly monitoring. Otherwise use standard monthly monitoring for eligible signed candidates.
- Outreach channel should start from the candidate preferred outreach, then fall back to usable patient contact fields. Do not choose portal when there is no active chart/portal access.
- Monitoring packages are derived from status and cadence: high-touch packages include standard devices/orders plus care-plan setup; standard packages include the required devices/orders and medication reconciliation when chart/clinical evidence calls for it; deferred packages include consent or chart-update work; rejected candidates use not-applicable packages.
