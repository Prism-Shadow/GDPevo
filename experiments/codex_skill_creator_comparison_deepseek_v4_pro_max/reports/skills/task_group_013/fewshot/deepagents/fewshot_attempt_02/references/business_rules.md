# Business Rules

This document describes the deterministic business rules used across Cedar Ridge intake workflows. Apply these rules consistently; same inputs always produce same outputs.

## General Reconciliation Rules

### ICD Chapter Validation

When a referral includes ICD-10 codes, validate them against the expected chapter for the service line:

- Compare each ICD code chapter from GET /icd/{code} to the expected chapter for the specialty
- Chapter mismatch produces the icd_chapter_mismatch issue code
- If narrative or laterality also disagrees with what the ICD code implies, also report narrative_mismatch or laterality_mismatch
- Expected chapters: orthopedic referrals expect M00-M99; pulmonary referrals expect J00-J99; primary care is broader

### Duplicate Detection

- Two or more referrals for the same patient_id within a batch are duplicates
- Assign a group_id using the pattern DUP-{batch_id}-{sequence_number}
- The earliest referral by referral_id is the primary
- Use consolidate_to_primary when referrals appear identical; keep_separate when they are for different conditions
- Referrals flagged as potential duplicates but determined to be distinct go in cleared_duplicate_review_referrals

### Shared Insurance Anomaly

- When the same insurance_id appears on referrals for different patients, flag as shared_insurance_anomaly
- verify_distinct_patient_policy_id unless the same patient legitimately has multiple referrals (legitimate_duplicate_same_patient)

### Document Completeness

- Each workflow has a checklist of required documents defined by the task domain
- A packet is complete when all required documents are present, incomplete otherwise
- Missing documents are listed as the document type codes from the answer template allowed values

### Document Freshness (Staleness)

- Each document type has a freshness limit in days
- A document is stale if (requested_start_date or current_date) minus received_date exceeds the freshness_limit_days
- Common freshness limits: hbsag 30 days, hep_b_antibody_core 30 days, history_physical 365 days, monthly_labs 30 days, ppd_or_cxr 30 days

## Status Determination Rules

### Registration Status (Patient Access)

Determined by the most severe issue found:

- approved: No issues; insurance valid, prescription valid, pharmacy in-network or unknown, all required fields present
- hold: Non-critical issues only such as missing_address or coverage_pending, and no critical blockers
- clinical_review: Clinical concern needing human review but not an automatic reject; includes pharmacy out-of-network, pbm issues short of policy mismatch, preferred_contact_unavailable, AND overall_risk is high
- rejected: Critical blockers such as coverage_expired, excluded_service_line, pbm_policy_mismatch, or multiple severe issues combined

### Referral Readiness Status

- ready: No blockers and no issues requiring review
- blocked: One or more of missing_records, missing_imaging, or auth_blocker
- under_review: Issues present but not blocking, e.g. ICD mismatches, duplicates needing resolution, already_scheduled
- admin_followup: Non-clinical issues only, e.g. shared_insurance_anomaly without clinical issues

When multiple issue types exist, pick the most severe: blocked > under_review > admin_followup > ready.

### Transfer Intake Decision

- accept: Packet is complete with no stale documents, and capacity is available on the requested start date
- hold: Packet is ready but capacity is unavailable, or minor administrative issues prevent immediate acceptance
- clinical_review: Packet is incomplete, has stale documents, capacity is unavailable, or any combination requires clinical evaluation

### Enrollment Status (Chronic Care)

- enroll: Eligible, consent not declined, chart active (or only minor chart artifacts missing)
- hold: Eligible but consent missing, chart inactive, or significant chart data stale/missing; can be resolved with administrative follow-up
- reject: Ineligible (wrong target condition, missing active diagnosis) OR consent explicitly declined

## Risk Assessment

### Lifestyle Risk

Determined from patient chart data: conditions, history, social factors. Values: low, medium, high.

### Overall Risk

- high: Lifestyle risk is high, OR critical clinical flags present, OR combination of insurance plus pharmacy plus prescription issues
- medium: Lifestyle risk is medium with some but not all administrative issues
- low: Lifestyle risk is low and no significant issues

When overall_risk is high, always include overall_risk_high in the blocked_reason_codes.

## Priority Tier Assignment

- tier_1_immediate: Urgent clinical issues requiring same-day attention, e.g. ICD mismatches flagged as urgent
- tier_2_short_term: Routine issues needing resolution within days, e.g. missing records, auth blockers, duplicate resolution
- tier_3_administrative: Administrative-only issues that can wait, e.g. insurance verification

## Follow-Up Cadence (Chronic Care)

- weekly: High-touch signals: recent hospitalization, low medication adherence, recent ED visit
- biweekly: CKD comorbidity requiring closer monitoring
- monthly: Standard enrollment, meets criteria without high-touch signals
- deferred: Enrollment on hold; cadence starts after hold is resolved
- none: Patient is rejected

## Chart Activation Rules

For referrals that are ready to schedule:

- create_chart: No chart record exists; create demographics and all standard artifacts
- update_chart: Chart exists but is missing artifacts; create only the missing ones
- no_chart_action: Chart is complete; no action needed

Artifacts include demographics, active_problems, medications, allergies, vitals, labs, consent.

## Correspondence Templates

Map issue types to correspondence template types:

- Clinical code discrepancy maps to clinical_code_clarification
- Authorization blocked or records missing maps to auth_records_request
- Duplicate review needed maps to duplicate_resolution
- Appointment already scheduled before clearance maps to appointment_hold_notice

Correspondence reason codes map to the specific underlying issue.

## Next-Contact Rules (Transfers)

- clinical_nurse: When clinical_review is needed; route is fax_referring_facility
- intake_coordinator: For accept or hold decisions; route is phone_patient or internal_queue for holds
- scheduling_coordinator: When the only issue is capacity; route is phone_patient
- none: No follow-up needed
