---
name: cedar-ridge-intake-coordination
description: Reusable workflow for Cedar Ridge Intake Coordination Portal tasks that require JSON-only healthcare intake audits from TASK_ENV_BASE_URL. Use for patient access verification, referral readiness or chart activation, dialysis transfer reviews, chronic-care program enrollment panels, and similar tasks that join portal REST or SQL data with input/payloads/answer_template.json.
---

# Cedar Ridge Intake Coordination

Use this skill to solve Cedar Ridge portal tasks by deriving every output field from the current prompt, the local answer template, and live portal data. Do not reuse prior task rows, counts, patient IDs, referral IDs, dates, or final answer values.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the schema authority for required keys, enum values, nullability, ordering, count buckets, and fixed identifiers.
2. Extract task selectors from the prompt and payloads: roster ID, batch ID, program code, patient IDs, referral IDs, transfer IDs, requested service line, and date fields.
3. Gather portal data from the provided base URL. Use REST endpoints for single records and `POST /query` with `{"sql":"..."}` for joins, roster rows, and table-wide reconciliation. Keep all evidence row-level until the final aggregation.
4. Build a working table per output row with source fields, derived issue codes, status, priority, and any missing/stale artifacts. Resolve conflicts before writing JSON.
5. Assemble exactly one JSON object matching the template. Include every required count bucket, including zeroes. Sort lists exactly as requested; for unordered code sets, use a stable order from the template or alphabetical order.
6. Validate the final object against the template: no extra prose, no free-form codes, no missing required keys, no omitted empty arrays, and `null` only where allowed.

Optional helper: `scripts/collect_portal_context.py` can collect filtered portal data for supplied IDs, batches, rosters, and programs. It does not solve the task.

```bash
python scripts/collect_portal_context.py --base-url "$TASK_ENV_BASE_URL" --batch-id "$BATCH_ID" --program-code "$PROGRAM_CODE" --roster-id "$ROSTER_ID"
```

## Portal Data

Common endpoints:

- `GET /patients`, `GET /patients/{patient_id}`
- `GET /referrals`, `GET /referrals/{referral_id}`
- `GET /transfers`, `GET /transfers/{transfer_id}`
- `GET /documents`
- `GET /chart/{patient_id}`
- `GET /programs/{program_code}/candidates`
- `GET /icd/{code}`
- `GET /pharmacies`
- `POST /query` with a SQL string for read-only reconciliation

Useful tables exposed through SQL include `patients`, `intake_rosters`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`, `referrals`, `icd_codes`, `documents`, `transfer_requests`, `facility_capacity`, `program_candidates`, `chart_artifacts`, and `clinical_history`.

Prefer SQL when the task needs joins or grouped anomaly detection. Prefer REST when the prompt gives direct IDs and only a small number of records are needed.

## New Patient Access

Use for roster-based new patient access verification.

Data sources:

- `intake_rosters`: roster patients, requested service date, service line.
- `patients`: address, contact channels, existing chart, emergency contact.
- `coverage`: payer, effective/termination dates, network status, covered service lines, status.
- `pbm`: prescription benefit status, formulary status, active flag, specialty policy.
- `patient_pharmacy` plus `pharmacies`: preferred pharmacy network status; use lowest `preference_rank`.
- `lifestyle`: smoking, alcohol, exercise, sleep.

Normalization:

- `insurance_status`: `missing` when no coverage row exists. `valid` only when coverage is active for the requested date, in network, and includes the requested service line. Otherwise `invalid`.
- Coverage blocker codes: expired status or termination before the requested date -> `coverage_expired`; pending/future/incomplete coverage -> `coverage_pending`; missing requested service line -> `excluded_service_line`; missing address -> `missing_address`; missing emergency contact -> `emergency_contact_missing`.
- `prescription_status`: `missing` when no PBM row exists. `valid` only when PBM is active, approved, covered on formulary, and compatible with the requested service. Use `pbm_invalid` for inactive, rejected, pending, review, or not-found benefit states; `pbm_missing` for absent PBM; `pbm_policy_mismatch` for specialty or payer/policy conflicts.
- `pharmacy_status`: use the preferred rank-1 pharmacy. Map in-network to `in_network`, out-of-network to `out_of_network`, and no resolvable preferred pharmacy to `unknown`. Add `pharmacy_out_of_network` or `pharmacy_unknown` when allowed by the template.
- Preferred contact is unavailable when the preferred channel has no reachable value; phone and SMS require a phone number, email requires email, and portal should have a usable portal/email-backed contact.
- Lifestyle risk is high for current smoking, heavy alcohol use, no/missing exercise, or very short sleep; medium for former smoking, moderate alcohol use, mild inactivity, or borderline sleep; low when no risk factors appear.
- Overall risk should rise to high for high lifestyle risk, hard access blockers, or multiple moderate blockers. Keep it low only when access, PBM, pharmacy, contact, and lifestyle checks are clean.

Registration status:

- `approved`: no blockers and low overall risk.
- `hold`: administrative gaps or pending items without high clinical/access risk.
- `clinical_review`: high overall risk, pending coverage, PBM problems, out-of-network/unknown pharmacy, missing contact data, or other reviewable blockers.
- `rejected`: hard coverage failure such as expired coverage or excluded service line, especially with PBM/pharmacy/contact blockers.

## Referral Readiness And Activation

Use for referral batch audits, readiness queues, correspondence queues, duplicate handling, and ready-referral chart activation.

Data sources:

- `referrals`: batch rows, service line, patient, ICD, reason text, records/imaging/auth flags, appointment status, urgency, insurance ID.
- `icd_codes` or `/icd/{code}`: description, chapter, service family, laterality.
- `patients`, `/chart/{patient_id}`, `chart_artifacts`: chart existence and missing/stale artifacts for ready referrals.
- `documents`: only if the prompt asks for supporting document reconciliation beyond referral flags.

Issue detection:

- Clinical code discrepancy: ICD service family does not match referral service line, code chapter is implausible for the service-specific template, referral narrative conflicts with code/service, or laterality conflicts with code metadata. Use the template's exact names such as `icd_chapter_mismatch`, `narrative_mismatch`, `laterality_mismatch`, or `clinical_code_discrepancy`.
- Missing records/imaging: `records_received = 0` or `imaging_received = 0`.
- Authorization blocker: `auth_required = 1` and `auth_status` is not approved. Preserve statuses such as pending, denied, or not submitted when the template asks.
- Duplicate referral: same patient appears more than once in the same batch. Use the earliest or lowest referral ID as the primary/keep referral unless the task gives a stronger rule.
- Shared insurance anomaly: the same non-empty insurance ID is used by different patients. The same insurance ID on duplicate referrals for one patient is a duplicate group, not a distinct-patient anomaly.
- Already scheduled before clearance: appointment is scheduled while unresolved clinical, authorization, records, imaging, or duplicate issues remain.
- Possible duplicate notes with different patients and distinct insurance should be cleared, not turned into duplicate groups.

Readiness precedence:

- `ready`: no unresolved clinical, duplicate, admin, auth, records, imaging, or appointment-clearance issues.
- `blocked`: operational blockers are present, especially missing records, missing imaging, or authorization blockers. Keep `blocked` even when clinical discrepancies also exist.
- `under_review`: clinical code/narrative/laterality discrepancy, duplicate review, or already-scheduled review without operational blockers.
- `admin_followup`: administrative anomaly only, such as shared insurance verification.

Priority and action mapping:

- `tier_1_immediate`: urgent clinical discrepancy or urgent safety-sensitive review.
- `tier_2_short_term`: routine clinical review, duplicate consolidation, scheduled-before-clearance review, missing records/imaging, or authorization work.
- `tier_3_administrative`: pure administrative verification.
- Map issues to actions directly: corrected ICD or clinical clarification, confirm narrative/laterality, consolidate duplicate, verify insurance ID, request records, request imaging, resolve authorization, or review existing appointment.
- For correspondence queues, prefer appointment-hold notice when scheduled-before-clearance is present; otherwise use clinical-code clarification for clinical discrepancies, auth/records request for authorization or record blockers, and duplicate resolution for duplicate review.

Ready-referral chart work:

- Only include ready referrals when the template asks for chart needs for ready referrals.
- If no chart exists, use `create_chart`; if a chart exists but artifacts are absent or stale, use `update_chart`; if all required artifacts are current, use `no_chart_action`.
- Required activation artifacts commonly include demographics, active problems, medications, allergies, vitals, labs, and consent. Include absent or stale artifacts only, sorted as the template requires.

## Dialysis Transfer Review

Use for transfer batches and seasonal dialysis intake packets.

Data sources:

- `transfer_requests`: batch rows, patient, requested start date, modality, requested days/window, transportation.
- `documents`: packet document rows keyed by transfer ID.
- `facility_capacity`: open chairs by date and modality across locations.

Packet rules:

- A required packet document is present only when the document row exists, `finalized = 1`, and status is final. Draft or unfinalized documents count as missing.
- Treat transportation as missing when the transfer request has no transportation value, even though it may not be a document row.
- Packet completeness usually reflects missing required items only. Stale items are separate findings but still make the requested start not ready.
- Staleness is measured from document `received_date` to the requested start date. Common freshness limits: `hbsag`, `monthly_labs`, and `ppd_or_cxr` expire after 30 days; `history_physical` and `hep_b_antibody_core` are long-window items, commonly 365 days unless the template or portal says otherwise.

Capacity and decision rules:

- Sum `facility_capacity.open_chairs` for the requested start date and modality across all locations. No rows or total zero means unavailable.
- Feasibility combines packet readiness and capacity: ready packet plus available capacity -> ready on requested start; incomplete/stale packet plus available capacity -> packet not ready but capacity available; incomplete/stale packet plus no capacity -> packet not ready and capacity unavailable; ready packet plus no capacity -> capacity unavailable.
- `accept` only when packet is complete, fresh, and capacity is available.
- `hold` when packet is ready but capacity is unavailable.
- `clinical_review` when required documents are missing or stale. Use clinical nurse/fax to referring facility for clinical packet problems; intake coordinator for administrative-only packet gaps; scheduling coordinator/internal queue for capacity-only holds; none for accepted transfers.

## Chronic-Care Program Panels

Use for program candidate enrollment panels such as diabetes plus hypertension monitoring.

Data sources:

- `GET /programs/{program_code}/candidates`: authoritative candidate list.
- `/chart/{patient_id}`: patient, chart artifacts, clinical history.
- `chart_artifacts`: active problems, vitals, labs, medications, consent, care plan, demographics, and status/currentness.
- `clinical_history`: chronic conditions, medication/allergy counts, recent hospitalization, risk flags.

Eligibility and disposition:

- Include every candidate returned for the program, even if ineligible.
- Program eligibility is clinical: the target condition and clinical history must match the program's target diagnoses. For a diabetes/hypertension panel, require diabetes and hypertension evidence. Wrong target condition or missing active target diagnoses makes the candidate ineligible.
- Chart activation and consent affect enrollment disposition, not necessarily clinical eligibility.
- `enroll`: clinically eligible, consent signed, active/current chart artifacts sufficient for the program.
- `hold`: clinically eligible but consent is missing, chart is inactive, or required chart artifacts are stale/missing.
- `reject`: ineligible target condition, missing target diagnosis, or consent declined.

Reason and artifact codes:

- Add `meets_*_criteria` only when the candidate has the target diagnoses and a usable active chart.
- High-touch reasons: recent hospitalization, recent ED risk flag, or low adherence. Recent hospitalization takes precedence over low-adherence labeling when both are present.
- CKD on a diabetes/hypertension candidate usually drives biweekly monitoring unless a higher-touch reason drives weekly monitoring.
- Missing chart artifacts include `chart_record` when no active chart exists, and artifact-specific codes for absent or stale active problems, vitals, labs, medications, or consent.
- Outreach should use the candidate's preferred outreach only when that channel is reachable; otherwise fall back to the patient's reachable preferred contact, then another available channel, then `none`.

Monitoring packages:

- High-touch enrollment: high-touch package, weekly cadence, first check-in around 7 days, include BP cuff, glucometer, lab order, medication reconciliation, and care plan setup.
- Standard diabetes/hypertension enrollment: standard package, monthly cadence, first check-in around 30 days, include BP cuff, glucometer, and lab order. Add medication reconciliation for CKD or medication-complexity cases and use biweekly cadence with first check-in around 14 days.
- Deferred enrollment: deferred package with consent packet and chart update request when consent/chart gaps can be fixed.
- Reject/not applicable: no monitoring components and null first check-in.

## Final JSON Checks

- Do not include reasoning fields unless the template requires them.
- Keep ID casing exactly as returned by the portal.
- Use integer counts, not strings.
- Count summaries from the finalized per-row objects, not independently from raw data.
- Include all enum count keys specified by the template even when the count is zero.
- If a template says a set is unordered, still output a deterministic order.
