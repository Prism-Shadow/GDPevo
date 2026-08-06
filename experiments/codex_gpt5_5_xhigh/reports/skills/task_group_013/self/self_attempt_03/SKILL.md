---
name: cedar-ridge-intake-auditor
description: Use for Cedar Ridge Intake Coordination Portal tasks that require reconciling patient access, referral readiness, dialysis transfers, chronic-care enrollment panels, chart activation, ICD metadata, insurance/PBM/pharmacy status, packet documents, capacity, and strict template-shaped JSON outputs.
---

# Cedar Ridge Intake Auditor

## Core Workflow

1. Read the user prompt, every input payload, and the answer template before querying the portal.
2. Read `environment_access.md` for the base URL and allowed endpoints. Use only those endpoints for network access.
3. Treat the answer template as the contract: include every required key, use only controlled enum values, preserve required list ordering, and compute all summary counts from the row-level output.
4. Pull only the requested roster, batch, program, transfer, referral, or patient cohort. Ignore distractor rows from other cohorts.
5. Prefer the read-only SQL endpoint for reconciliation when several tables must be joined. Use record endpoints when they package related context more directly:
   - `GET /patients/{patient_id}` for demographics and contact flags.
   - `GET /referrals/{referral_id}` for referral, patient, ICD, and referral documents.
   - `GET /transfers/{transfer_id}` for transfer, patient, packet documents, and nearby capacity.
   - `GET /chart/{patient_id}` for clinical history and chart artifacts.
   - `GET /programs/{program_code}/candidates` for current program scope.
   - `GET /icd/{code}` for code description, chapter, service family, and laterality.
6. Keep an evidence table while working. Record the source field for every status, blocker, reason code, or count so unsupported codes do not enter the final JSON.
7. Before final output, parse the JSON mentally or with a local validator if available. Ensure there is no prose when the prompt requires JSON only.

## Portal Data Map

Use these table relationships when the SQL endpoint is available:

- `intake_rosters.patient_id -> patients.patient_id`
- `coverage.patient_id`, `pbm.patient_id`, `lifestyle.patient_id`, `clinical_history.patient_id`
- `patient_pharmacy.patient_id -> pharmacies.pharmacy_id`, using the lowest/preferred `preference_rank`
- `referrals.icd10_code -> icd_codes.code`
- `documents.referral_id -> referrals.referral_id`
- `documents.transfer_id -> transfer_requests.transfer_id`
- `facility_capacity.date + modality` for transfer requested-start capacity
- `program_candidates.patient_id -> patients`, `clinical_history`, and `chart_artifacts`

## JSON Assembly Rules

- Populate constant identifiers from the prompt/template and live cohort record, not from memory.
- Sort arrays exactly as specified. Common sort keys are ascending `patient_id`, ascending `referral_id`, ascending `transfer_id`, ascending `group_id`, alphabetical document/artifact codes, or priority rank.
- Treat reason-code, issue-code, blocker-code, and component arrays as unordered sets, but emit a stable order using the template's enum order unless the template says otherwise.
- Include zero-valued count keys when the template lists required count categories.
- Use `null` only where the template allows it. Use empty arrays for no findings when the schema expects a list.
- Recompute cohort summaries after all row-level decisions are complete; do not infer summaries separately.

## New Patient Access Verification

Gather roster rows, patient demographics, coverage, PBM, preferred pharmacy network status, lifestyle, and clinical history for every target patient.

Use these status rules unless the current prompt/template gives stricter rules:

- Insurance is valid only when coverage exists, is active, is in network, covers the requested service date, and includes the requested service line.
- Insurance is missing when no usable coverage row exists. Pending coverage should produce a coverage-pending blocker and map to the closest allowed non-valid status in the template.
- Insurance is invalid when coverage is expired/terminated for the requested date, inactive, out of network, or excludes the requested service line.
- Prescription benefits are valid only when PBM exists, is active/approved, formulary status is covered, and PBM policy matches the medical coverage policy.
- PBM blockers map to missing, invalid, policy mismatch, or pending/review according to the controlled codes available in the template.
- Pharmacy status comes from the top-ranked preferred pharmacy: `in_network`, `out_of_network`, or `unknown` if no preference or pharmacy record is usable.
- Missing patient address, missing emergency contact, or an unavailable preferred contact channel are administrative blockers when the template provides those codes.
- Lifestyle risk rises with current smoking, heavy alcohol use, no/unknown exercise, and short sleep. Use low for no material signals, medium for one or moderate signals, and high for multiple high-risk signals.
- Overall risk should be at least lifestyle risk and should escalate for recent hospitalization, explicit risk flags, complex medication burden, or other clinical-history flags.
- Registration disposition should reflect the most serious unresolved issue: approve only when all required administrative, coverage, PBM, pharmacy, and risk checks pass; hold for administrative/coverage/PBM/pharmacy follow-up; clinical review for high clinical risk; reject only when the template or evidence supports a hard exclusion.

## Referral Readiness And Chart Activation

For each target referral batch, gather referrals, patients, ICD metadata, referral documents, duplicate candidates, insurance reuse, authorization status, appointment status, and chart artifacts when chart activation is requested.

Use these issue rules:

- Code/service discrepancy exists when `icd_codes.service_family` does not match the referral service line. Report observed chapter from the ICD row and derive the expected chapter/service family from the target service line or local ICD rows.
- Narrative mismatch exists only when referral reason, diagnosis text, notes, or supporting documents conflict with the ICD meaning or service line. Do not invent a mismatch from generic text alone.
- Laterality mismatch exists only when a left/right side in the narrative conflicts with `icd_codes.laterality`.
- Missing records and imaging come from referral flags and any required supporting document checks in the prompt/template.
- Authorization is a blocker only when authorization is required and status is pending, denied, not submitted, or otherwise not cleared. Approved or not-required authorization is cleared.
- Already scheduled or scheduled-before-clearance is a blocker when an appointment exists while unresolved clinical, record, imaging, authorization, or duplicate issues remain.
- Duplicate groups are true duplicates when referrals share the same patient and materially duplicate clinical/referring details, or when the portal notes explicitly show a duplicate submission. Choose the primary/kept referral by earliest/lowest referral ID unless the prompt gives a different rule.
- Shared insurance anomalies are insurance IDs reused across different patients in the same batch. Do not classify same-patient duplicate insurance reuse as a cross-patient anomaly.
- Possible-duplicate notes without matching patient, insurance, or clinical/referring evidence should be either cleared or left as administrative follow-up only if the template has a place for that distinction.

Map issue severity consistently:

- `ready`: no unresolved clinical, records, imaging, authorization, duplicate, shared-insurance, or appointment blockers.
- `blocked`: required records/imaging are absent, authorization is not cleared, or another hard prerequisite prevents scheduling.
- `under_review`: clinical code, narrative, laterality, or cross-patient insurance discrepancies require human review.
- `admin_followup`: duplicate consolidation, appointment cleanup, or referring-office paperwork follow-up is needed without a clinical denial.
- Priority tier should put urgent clinical/auth/scheduled-before-clearance issues first, ordinary clinical or hard prerequisite blockers next, and duplicate/admin-only work last. Leave priority null for ready rows when the template allows null.

For chart activation outputs, include only referrals that are ready to move forward unless the template says otherwise. Use existing chart status and chart artifacts:

- `create_chart` when no chart exists.
- `update_chart` when a chart exists but required artifacts are missing or stale.
- `no_chart_action` when all required artifacts are current.
- Treat stale artifacts as needing update/creation for the requested output code.

## Dialysis Transfer Review

For each transfer, gather the transfer request, patient, packet documents, and facility capacity for the requested start date and modality.

Packet rules:

- Use the template's required document code set. A document counts as present only when it exists for the transfer and is finalized/final.
- Draft, non-final, absent, or wrong-transfer documents count as missing for the required document code.
- Evaluate staleness only for document types listed by the template. Compare the latest finalized `received_date` to the requested start date.
- When no explicit freshness limits are provided, use Cedar Ridge defaults: `monthly_labs` 30 days, `hbsag` 30 days, `history_physical` 90 days, `hep_b_antibody_core` 365 days, and `ppd_or_cxr` 365 days.

Capacity and disposition:

- Sum open chairs across locations for the exact requested start date and modality unless the prompt asks for a window. No matching rows or a zero sum means unavailable.
- Feasibility combines packet readiness and capacity: complete plus capacity available means ready on requested start; incomplete plus capacity available means packet-not-ready/capacity-available; incomplete plus no capacity means packet-not-ready/capacity-unavailable; complete plus no capacity means capacity-unavailable.
- Accept only when required documents are complete, freshness checks pass, and capacity is available.
- Hold for administrative packet gaps or capacity problems. Use clinical review for stale or clinically sensitive packet findings when the template provides that decision.
- Assign next contact to the party that can resolve the main blocker: clinical nurse for clinical/stale packet review, intake coordinator for missing packet documents, scheduling coordinator for capacity, and none when no action remains.
- Use fax to referring facility for packet/document requests, internal queue for capacity/scheduling work, phone patient for patient-specific logistics, and none when no contact is needed.

## Chronic-Care Enrollment Panels

For each program candidate, gather candidate data, demographics/contact availability, clinical history, and chart artifacts.

Use these rules:

- Include every current candidate returned by the program endpoint; do not add patients from other sources.
- Determine condition fit from the program target and active/chronic conditions. A diabetes-hypertension program requires both diabetes and hypertension evidence; wrong target condition or missing active diagnoses should use the template's controlled reason codes.
- A candidate is enrollment-ready only when consent is signed, the chart exists, required chart artifacts are current, and target-condition criteria are met.
- Declined consent usually rejects. Missing consent, missing/stale chart artifacts, or absent chart usually holds unless the template says to reject.
- Required chart artifacts commonly include active problems, vitals, labs, medications, and consent. Mark missing or stale artifacts with the normalized artifact codes from the template.
- Add high-touch reason codes for recent hospitalization, recent ED flags, low adherence, CKD, and similar explicit clinical-history signals. Use local thresholds from the prompt when supplied; otherwise treat adherence below 50 as low adherence.
- Follow-up cadence should match intensity: weekly for recent hospitalization, recent ED, or low adherence high-touch needs; biweekly for CKD-oriented monitoring; monthly for standard eligible enrollment; deferred for holds; none for rejects.
- Outreach should use `preferred_outreach` only when the corresponding contact detail exists. Fall back to an available allowed channel when needed; use none for no viable outreach or non-actionable rejection.
- Monitoring packages should mirror disposition: high-touch package for high-touch enrolled candidates, standard package for routine enrolled candidates, deferred package for holds with remediation components, and not-applicable for rejects.

## Final Validation Checklist

- The output is one JSON object if the prompt asks for one object.
- No task-specific final values from examples are copied into unrelated tasks.
- Every ID in output belongs to the requested cohort.
- Every enum value appears in the active answer template.
- Every list obeys the requested ordering.
- Counts exactly match row-level lists, including zero-count categories.
- JSON contains no comments, markdown fences, or explanatory prose when JSON-only is required.
