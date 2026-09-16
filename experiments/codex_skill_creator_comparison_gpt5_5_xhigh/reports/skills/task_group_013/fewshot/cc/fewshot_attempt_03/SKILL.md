---
name: cedar-ridge-intake-reconciler
description: Reconcile Cedar Ridge Intake Coordination Portal tasks into exact JSON answer-template outputs. Use for patient access verification, referral readiness or chart activation, dialysis transfer packet review, chronic-care program enrollment panels, and similar Cedar Ridge portal tasks that require joining API or SQL data, applying controlled reason codes, ordering rows, and computing cohort summaries.
---

# Cedar Ridge Intake Reconciler

Use this skill when a task asks for a JSON-only Cedar Ridge intake, referral, transfer, or program-panel response from `<TASK_ENV_BASE_URL>`.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the contract for keys, allowed values, ordering, constants, and summary fields.
2. Identify the target entity from the prompt: roster ID, referral batch ID, transfer batch ID, program code, explicit patient IDs, or explicit referral IDs.
3. Query only the relevant portal records. Prefer endpoint reads for small targets and `POST /query` with SQL for batch reconciliation.
4. Build row-level findings before summaries. Every count in a summary should be derived from the final row objects.
5. Emit one JSON object only. Do not add prose, comments, markdown fences, or values outside the template's controlled vocabulary.

## Portal Access

Base URL comes from the prompt or the task's environment access note. The useful endpoints are:

- `GET /patients`, `/patients/{patient_id}`, `/chart/{patient_id}`
- `GET /referrals`, `/referrals/{referral_id}`
- `GET /transfers`, `/transfers/{transfer_id}`
- `GET /documents`, `/icd/{code}`, `/pharmacies`
- `GET /programs/{program_code}/candidates`
- `POST /query` with JSON body `{"sql":"select ..."}`

Useful SQL tables:

- `patients`: identity, contact fields, address, `existing_chart`, preferred contact, emergency contact.
- `intake_rosters`: roster patient IDs, requested service date, service line.
- `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`: patient access checks.
- `referrals`, `icd_codes`, `documents`: referral batch readiness and chart activation.
- `transfer_requests`, `facility_capacity`, `documents`: dialysis transfer packet and capacity review.
- `program_candidates`, `clinical_history`, `chart_artifacts`: chronic-care enrollment panels.

Example SQL patterns with placeholders:

```sql
select r.*, i.chapter, i.service_family, i.laterality
from referrals r
left join icd_codes i on i.code = r.icd10_code
where r.batch_id = '<batch_id>'
order by r.referral_id;
```

```sql
select d.*
from documents d
where d.transfer_id in (
  select transfer_id from transfer_requests where batch_id = '<batch_id>'
)
order by d.transfer_id, d.doc_type;
```

## Template Discipline

- Copy required constant fields from the template or prompt, not from memory.
- Sort exactly as the template says. Common patterns are ascending `patient_id`, `referral_id`, `transfer_id`, `group_id`, or alphabetic code order.
- Treat code arrays marked "unordered set" as sets: no duplicates, only allowed values. Use a stable order when writing them, preferably the order in the template unless it specifies alphabetical.
- Use empty arrays and zero-count buckets when the template requires them.
- Use `null` only where the template allows null.

## Patient Access Verification

Use this for new-patient roster verification tasks.

Gather for each roster patient: patient row, roster service date and service line, coverage, PBM, primary preferred pharmacy, lifestyle, and contact fields.

Insurance:

- `valid`: active coverage on the requested service date, in network when relevant, and the roster service line appears in the coverage service-line list.
- `invalid`: expired coverage, pending/non-active coverage, service-line exclusion, or conflicting coverage data.
- `missing`: no coverage row.
- Reason-code mapping: expired date/status -> `coverage_expired`; pending status -> `coverage_pending`; roster service line absent from coverage service lines -> `excluded_service_line`; missing patient address -> `missing_address`.

Prescription benefits:

- `valid`: PBM row is active/approved and compatible with the requested service.
- `invalid`: inactive, rejected, pending/review, formulary not found, or policy mismatch such as specialty requirements that do not fit the service.
- `missing`: no PBM row.
- Reason-code mapping: no row -> `pbm_missing`; rejected/inactive/pending/review -> `pbm_invalid`; policy incompatibility -> `pbm_policy_mismatch`.

Pharmacy:

- Join the patient's rank-1 pharmacy to `pharmacies`.
- Map pharmacy network to `in_network` or `out_of_network`; no usable pharmacy/network row is `unknown`.
- Add `pharmacy_out_of_network` or `pharmacy_unknown` as appropriate.

Lifestyle and contact:

- Mark lifestyle risk high for current smoking, heavy alcohol use, no/unknown exercise, or very short sleep. Mark medium for former smoking, moderate alcohol, or mild sleep/exercise concerns. Otherwise mark low.
- Add `preferred_contact_unavailable` when the preferred email/phone/SMS route lacks the needed email or phone.
- Add `emergency_contact_missing` when the patient row says no emergency contact is present.

Overall and final registration:

- Overall risk is high if high lifestyle risk or any hard access blocker is present; medium for unresolved administrative concerns without high-risk findings; low only when all checks are clean.
- `approved` requires valid insurance, valid prescription benefit, in-network pharmacy, low/medium risk acceptable to the template, and no blocker codes.
- Use `clinical_review` for high overall risk or mixed clinical/admin blockers that are not outright exclusions.
- Use `hold` for pending/missing items when the template distinguishes temporary administrative hold from clinical review.
- Use `rejected` for service-line exclusion, expired/no valid coverage path, or severe incompatible coverage/PBM combinations.

## Referral Readiness And Chart Activation

Use this for referral batch audits, scheduling readiness, pulmonary/orthopedic activation files, and similar referral-to-chart tasks.

Gather the batch from `referrals`, join `icd_codes`, patient rows, referral documents, and chart artifacts when chart work is requested.

Code and narrative discrepancies:

- Prefer `icd_codes.service_family` to decide whether a code belongs to the referral service line.
- Flag a service-family or clinical-code discrepancy when the ICD service family conflicts with the referral service line.
- Flag a narrative/clinical reason mismatch when the ICD family is plausible but the referral reason or diagnosis wording does not match the service-line workflow.
- When a template specifically asks for chapter mismatch fields, compare `icd_codes.chapter` to the service line's expected chapter. For orthopedics-style chapter audits, musculoskeletal `M00-M99` is the expected chapter even if an injury code is tagged to the orthopedic family.
- Do not use raw chapter alone as a universal mismatch test; symptom chapters can still be appropriate when `service_family` matches and the narrative fits.

Administrative blockers:

- `records_received = 0` -> missing records.
- `imaging_received = 0` -> missing imaging.
- `auth_required = 1` and `auth_status` in `denied`, `pending`, or `not_submitted` -> authorization blocker. Include the actual auth status when the template asks.
- `appointment_scheduled = 1` before clearance -> already scheduled or scheduled-before-clearance review code.

Duplicate and insurance review:

- A true duplicate group requires the same patient or otherwise clearly repeated referral identity, commonly same patient plus policy/contact/referring details. Keep the earliest/lower referral ID as the primary unless the prompt says otherwise.
- The same insurance ID across different patients is a shared insurance anomaly, not a duplicate group. Put it in the shared-insurance/admin follow-up structure when the template has one.
- A note such as "possible duplicate" is not enough by itself; clear it when patient, insurance, and referral identity are distinct.

Readiness precedence:

- `ready`: no code/narrative discrepancy, no missing records/imaging, no auth blocker, no duplicate requiring consolidation, no appointment-before-clearance issue, and no unresolved shared-insurance anomaly.
- `blocked`: any hard missing records/imaging/auth blocker. Keep review-only issue codes too, but hard blockers determine the status.
- `under_review`: code/narrative/chapter discrepancy, true duplicate review, or appointment-before-clearance without a hard blocker.
- `admin_followup`: administrative anomaly only, such as shared insurance across different patients.

Action and correspondence mapping:

- Corrected ICD or code clarification: `request_corrected_icd`, `clinical_code_clarification`, or equivalent template code.
- Narrative or laterality clarification: `confirm_narrative`, `confirm_laterality`, or equivalent.
- Missing records/imaging: request records or imaging.
- Authorization denied/pending/not submitted: resolve authorization.
- True duplicate: consolidate or duplicate-resolution workflow.
- Existing appointment before clearance: review existing appointment or appointment-hold notice.
- Shared insurance anomaly: verify insurance ID.

Priority:

- Tier 1: urgent clinical/code mismatch that can misroute care.
- Tier 2: routine clinical review, missing records/imaging, authorization blockers, duplicate consolidation, or appointment-before-clearance.
- Tier 3: administrative-only anomalies.
- For explicit priority order lists, rank non-ready referrals by tier first, then urgency, then number/severity of blockers, then referral ID for stability.

Chart activation for ready referrals:

- Include only referrals that are ready when the template asks for ready-referral chart needs.
- `existing_chart = 0` means `create_chart`; `existing_chart = 1` with missing/stale artifacts means `update_chart`; no gaps means `no_chart_action`.
- For each artifact allowed by the template, create/update it when absent from `chart_artifacts` or present with stale/non-current status. Exclude current artifacts.

## Dialysis Transfer Review

Use this for seasonal dialysis transfer batch review.

Gather transfer requests for the batch, documents for those `transfer_id`s, patient rows if needed, and `facility_capacity` for requested start dates.

Packet completeness:

- A required document counts as present only when there is a matching document with `finalized = 1` and final status.
- Draft/unfinalized documents count as missing.
- If the transfer row has a required operational field such as transportation and it is null, include the corresponding missing code if the template allows it.
- `packet_completeness_status` is complete only when the missing-required-documents list is empty. Stale documents do not make the packet incomplete by themselves unless the template says so.

Freshness:

- Compare document `received_date` with `requested_start_date`.
- Common freshness limits: HBsAg, monthly labs, and PPD/CXR are 30 days; history and physical is 365 days. Use any stricter limit explicitly given by the prompt or template.
- Report stale documents with the doc type, received date, and freshness limit from the rule/template.

Capacity and decision:

- Sum `facility_capacity.open_chairs` for the exact requested start date and modality across Cedar Ridge locations.
- Open chairs greater than zero is available; no rows or zero total is unavailable.
- Feasibility combines packet readiness and capacity: ready plus capacity means ready on requested start; otherwise choose the template value that names packet-not-ready and/or capacity-unavailable.
- Accept only when the packet is complete, no stale clinical documents remain, and capacity is available. Use clinical review for stale clinical packet items. Use hold/intake follow-up for missing administrative packet items when no clinical review is needed.
- Route stale clinical packets to a clinical nurse by fax to the referring facility when the template has owner/route fields. Missing administrative packet items usually go to intake coordination; capacity-only issues go to scheduling.

## Chronic-Care Enrollment Panels

Use this for program candidate panels such as diabetes-hypertension monitoring.

Gather candidates, patient rows, clinical history, and chart artifacts for the target `program_code`.

Eligibility and disposition:

- Determine clinical eligibility from the program target condition and active clinical history, not merely from presence in the candidate list.
- For a diabetes-hypertension program, eligible patients have both diabetes and hypertension active in clinical history and the candidate target condition matches that program.
- Wrong target condition or missing active target diagnoses makes `eligible` false and usually `reject`.
- Signed consent plus eligibility and usable/current chart artifacts can enroll.
- Declined consent is a reject reason even if the clinical condition matches.
- Missing consent or inactive/stale chart artifacts usually creates a hold/deferred disposition when the target condition otherwise matches.

Reason codes:

- Add the positive criteria code when the target condition matches and active diagnoses support enrollment.
- Add high-touch codes for recent hospitalization, recent ED risk flag, or low adherence. In the evidence, adherence below 50 is low adherence.
- Add CKD biweekly monitoring when CKD is present without a stronger weekly high-touch reason.
- Add chart and consent reason codes only when they matter to the disposition. For wrong-target rejects, avoid adding incidental missing-artifact codes unless the template asks for all issues.

Cadence and monitoring:

- Weekly for high-touch reasons.
- Biweekly for CKD monitoring when not weekly.
- Monthly for standard eligible patients.
- Deferred for hold cases; none for rejects.
- High-touch package: BP cuff, glucometer, lab order, medication reconciliation, and care-plan setup.
- Standard package: BP cuff, glucometer, lab order; include medication reconciliation when CKD or medication complexity indicates it.
- Deferred package: consent packet and chart update request when consent/chart work remains.
- Not applicable for rejects.
- First check-in days generally align with cadence: weekly 7, biweekly 14, monthly 30, otherwise null.

Missing chart artifacts and outreach:

- Required chart artifacts commonly include active problems, vitals, labs, medications, and consent. Mark an artifact missing when absent or stale/non-current.
- Use `chart_record` when the patient has no active existing chart and the template allows it.
- For outreach, start with the candidate's preferred outreach channel, then fall back to a usable patient contact channel. Email requires an email address; phone/SMS require a phone number; portal generally requires an existing chart/portal-capable patient. Use `none` only when no allowed route is usable.

## Final Checks

- Parse the final JSON mentally or with a JSON parser before answering.
- Recompute every summary count from the final arrays.
- Confirm every required ID from the target cohort appears exactly once unless the template explicitly asks for grouped-only lists.
- Confirm every allowed enum value is spelled exactly as the template shows.
