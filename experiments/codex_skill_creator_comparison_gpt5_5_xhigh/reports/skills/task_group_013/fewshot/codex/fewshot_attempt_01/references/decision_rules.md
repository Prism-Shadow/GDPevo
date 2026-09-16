# Decision Rules

Use these rules as reusable defaults. The answer template always wins when it narrows allowed values, names, or ordering.

## Common Normalization

- Treat integer flags `1`/`0` as true/false.
- Treat draft or non-final documents as absent for completeness unless the template explicitly asks for drafts.
- For code arrays described as unordered sets, include each reason once and order by the template's allowed-value list.
- Count summaries from the rows you actually output, not from raw portal counts.

## New Patient Access Verification

Join roster rows to patient, coverage, PBM, preferred pharmacy, and lifestyle data.

- `insurance_status`: `missing` if no coverage row. `valid` when coverage is active on the requested service date and includes the requested service line. Otherwise `invalid`.
- Coverage blocker codes: use `coverage_expired` when coverage is expired or terminates before the requested service date; `coverage_pending` when coverage status is pending; `excluded_service_line` when the requested service line is not included; `missing_address` when patient address is absent.
- `prescription_status`: `missing` if no PBM row. `valid` when PBM is active, approved, formulary-covered, and has no policy mismatch for the requested service. Otherwise `invalid`.
- PBM blocker codes: use `pbm_invalid` for inactive, rejected, pending, review, or not-found PBM states; `pbm_policy_mismatch` for an otherwise active PBM whose policy requirements conflict with the requested service; `pbm_missing` for no PBM row.
- `pharmacy_status`: map the preferred-rank pharmacy's network status to `in_network` or `out_of_network`; use `unknown` when no preferred pharmacy/network is available. Add the matching pharmacy blocker if the template has one.
- Contact blockers: add `preferred_contact_unavailable` when the preferred route cannot be used: email needs an email address, phone or sms needs a phone number, and portal generally needs an existing chart/account. Add `emergency_contact_missing` when the patient flag is false.
- `lifestyle_risk`: high for current smoking, heavy alcohol, no/unknown exercise, short sleep, or multiple moderate risk factors; medium for former smoking, moderate alcohol, limited exercise, or borderline sleep; low when no meaningful lifestyle flags are present.
- `overall_risk`: high when lifestyle is high or when severe coverage/PBM/pharmacy/contact blockers stack up; medium for limited unresolved blockers or medium lifestyle risk; low when administrative, coverage, PBM, pharmacy, and lifestyle findings are clean.
- `registration_status`: reject when the requested service is excluded or coverage is definitively unusable; clinical-review high overall risk or clinical policy mismatches; hold recoverable pending/missing administrative items; approve only clean rows.

## Referral Readiness And Referral-To-Chart Activation

Start from the referral batch, join ICD metadata, then pull referral documents, patient records, and chart artifacts.

- Clinical code discrepancy: flag when ICD `service_family` conflicts with referral `service_line`, when the workflow expects a specific chapter and the ICD chapter differs, when the referral reason/narrative is inconsistent with the ICD description or service family, or when laterality text conflicts with ICD laterality.
- For orthopedic readiness, trauma/injury chapters can still have orthopedic service family but should be reviewed when the office expects musculoskeletal `M00-M99` coding.
- Missing records/imaging: map `records_received = 0` and `imaging_received = 0` directly to template blocker codes.
- Authorization blocker: flag when `auth_required = 1` and `auth_status` is pending, denied, or not submitted. Approved or not-required authorization is clear.
- Existing appointment before clearance: flag `appointment_scheduled = 1` as `already_scheduled` or `scheduled_before_clearance` according to template wording.
- Duplicate group: group same-patient duplicate referrals, especially shared insurance/contact details or duplicate-practice notes. Keep the lowest referral ID as primary unless the template or data gives a stronger primary marker.
- Shared insurance anomaly: same insurance ID across different patients is administrative follow-up, not a duplicate group.
- Readiness: `ready` only with no blockers. Use `blocked` for missing records, missing imaging, or authorization blockers. Use `under_review` for clinical code discrepancies, duplicates, or scheduled-before-clearance review when no hard admin blocker dominates. Use `admin_followup` for administrative anomalies such as shared insurance only.
- Priority tiers: urgent clinical/code issues are `tier_1_immediate`; missing records/imaging/auth, duplicate review, existing appointment, and routine code clarification are `tier_2_short_term`; insurance-only or clerical-only issues are `tier_3_administrative`.
- Correspondence: clinical code issues use a clinical-code clarification template; authorization plus records use an auth/records request; duplicate-only issues use duplicate resolution; scheduled-before-clearance issues use appointment hold notice, including any accompanying reasons the template allows.

For ready referral chart needs, consider required chart artifacts such as demographics, active problems, medications, allergies, vitals, labs, and consent. Include artifacts that are absent or stale. Use `create_chart` when no chart exists, `update_chart` when a chart exists but artifacts need work, and `no_chart_action` only when required artifacts are current.

## Dialysis Transfer Review

Use transfer requests, packet documents, and facility capacity.

- Packet completeness is based on required document codes in the template. A document counts as present only when finalized/final. Draft or missing documents are listed under `missing_required_documents`.
- If `transportation` is listed as a required item and the transfer request has no transportation value, include it as missing.
- Staleness is separate from completeness. Common freshness limits are 30 days for `hbsag`, `monthly_labs`, and `ppd_or_cxr`, and 365 days for `history_physical`. Include the received date and freshness limit from the document you mark stale.
- Capacity is the sum of `facility_capacity.open_chairs` for the requested start date and modality across Cedar Ridge locations. No rows or a zero sum means unavailable.
- Feasibility: packet complete plus capacity available is ready on requested start; incomplete/stale packet plus available capacity is packet-not-ready/capacity-available; packet not ready plus unavailable capacity is packet-not-ready/capacity-unavailable; clean packet plus unavailable capacity is capacity-unavailable.
- Decision: accept only when packet is complete, fresh, and capacity is available. Use clinical review when clinical packet documents are missing or stale. Use hold for capacity-only or administrative-only waits.
- Contact owner: clinical nurse for missing/stale clinical documents; intake coordinator for administrative packet gaps; scheduling coordinator for capacity-only issues; none when accepted. Fax the referring facility for packet document requests, phone the patient for patient-owned items, and use the internal queue for scheduling-only work.

## Chronic-Care Enrollment Panels

Use program candidates, patient contact/chart fields, clinical history, and chart artifacts.

- Eligibility for diabetes/hypertension panels requires the candidate target condition and active history to include both diabetes and hypertension. Wrong target condition or missing active diagnoses makes the candidate ineligible.
- Consent declined leads to reject. Consent missing leads to hold when otherwise eligible. Signed consent can enroll if eligibility and chart requirements are satisfied.
- Chart readiness should check for an active chart and current active problems, vitals, labs, medications, and consent. Missing or stale artifacts become reason codes and `missing_chart_artifacts` if the template asks for them.
- Reason codes: use target-condition and active-diagnosis codes for ineligible candidates; use consent, chart-not-active, stale-problem, missing-vitals, missing-labs, and missing-medication codes for chart/consent gaps; use criteria/high-touch codes for eligible enrolled candidates.
- Follow-up cadence: weekly for high-touch signals such as recent hospitalization, recent ED visit, or low adherence; biweekly for CKD monitoring; monthly for standard enrolled candidates; deferred for holds; none for rejects.
- Monitoring package: high-touch gets BP cuff, glucometer, lab order, medication reconciliation, and care plan setup. Standard gets BP cuff, glucometer, and lab order; add medication reconciliation for CKD/biweekly cases. Deferred gets consent packet and chart update request. Rejects use not applicable with no components and `null` check-in days.
- Outreach route: prefer the candidate's preferred outreach if usable. Portal requires an existing chart/account, email requires an email address, and phone/sms require a phone number. If unusable, fall back to the patient's preferred usable contact, then another available route, then `none`.
