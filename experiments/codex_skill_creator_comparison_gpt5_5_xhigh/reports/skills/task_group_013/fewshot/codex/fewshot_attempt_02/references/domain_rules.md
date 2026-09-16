# Cedar Ridge Portal Domain Rules

Use this reference for Cedar Ridge Intake Coordination Portal tasks that ask for a controlled JSON answer. Treat the task prompt and `input/payloads/answer_template.json` as the output contract.

## Data Collection

The portal base URL is supplied in the task prompt. The useful endpoints are:

- `GET /patients`, `GET /patients/{patient_id}`
- `GET /referrals`, `GET /referrals/{referral_id}`
- `GET /transfers`, `GET /transfers/{transfer_id}`
- `GET /documents`
- `GET /chart/{patient_id}`
- `GET /programs/{program_code}/candidates`
- `GET /icd/{code}`
- `GET /pharmacies`
- `POST /query` with body `{"sql":"select ..."}`

Prefer `POST /query` for joined/filterable work. Relevant tables observed in the portal are:

- `patients(patient_id, phone, email, address, existing_chart, preferred_contact, emergency_contact_present, ...)`
- `intake_rosters(roster_id, patient_id, requested_service_date, service_line, ...)`
- `coverage(patient_id, payer, policy_number, effective_date, termination_date, service_lines, status, ...)`
- `pbm(patient_id, payer, policy_number, active, formulary_status, specialty_required, status)`
- `lifestyle(patient_id, smoking_status, alcohol_use, exercise_frequency, sleep_hours)`
- `patient_pharmacy(patient_id, pharmacy_id, preference_rank)` and `pharmacies(pharmacy_id, network_status, ...)`
- `referrals(referral_id, batch_id, service_line, patient_id, icd10_code, referral_reason, urgency, records_received, imaging_received, auth_required, auth_status, appointment_scheduled, insurance_id, referring_fax, notes, ...)`
- `icd_codes(code, description, chapter, service_family, laterality)`
- `documents(document_id, patient_id, referral_id, transfer_id, doc_type, status, finalized, received_date, service_date, content_tag, ...)`
- `transfer_requests(transfer_id, batch_id, patient_id, requested_start_date, requested_end_date, modality, ...)`
- `facility_capacity(location_id, date, modality, open_chairs)`
- `program_candidates(program_code, patient_id, candidate_date, consent_status, preferred_outreach, adherence_score, target_condition, ...)`
- `chart_artifacts(patient_id, artifact_type, status, last_updated, ...)`
- `clinical_history(patient_id, chronic_conditions, medication_count, allergy_count, recent_hospitalization, risk_flags, ...)`

Filter first by the task identifier: roster ID, referral batch ID, transfer batch ID, or program code. Then collect only the linked patients, documents, chart artifacts, ICD rows, pharmacies, and capacity rows needed for those records.

## Output Discipline

- Return JSON only when requested.
- Preserve every required top-level key and nested key from the template.
- Use only enum and reason-code values listed in the template.
- Include zero-count enum keys when the template names them.
- Sort lists exactly as the template says. Common orderings are ascending IDs, alphabetical code strings, or explicit priority rank.
- Treat reason-code arrays described as unordered sets as deduplicated sets; choose a stable order, usually the template order or alphabetical if the template says alphabetical.
- Recompute summaries from the emitted item rows after the rows are final.

## New Patient Access Verification

Use `intake_rosters` for `requested_service_date`, `service_line`, and target patient IDs unless the task provides a narrower roster payload.

Insurance status:

- `missing`: no coverage row for the patient.
- `valid`: coverage `status` is active, the requested date is within `effective_date` and `termination_date` if present, and the requested service line appears in `service_lines`.
- `invalid`: coverage is pending/expired/out of date or the requested service line is not included.

Common blocked reason mappings:

- Pending coverage -> `coverage_pending`.
- Expired coverage or requested date after termination -> `coverage_expired`.
- Requested service line absent from `service_lines` -> `excluded_service_line`.
- Missing patient address -> `missing_address`.
- Missing emergency contact -> `emergency_contact_missing`.
- Preferred email without an email, phone/SMS without a phone -> `preferred_contact_unavailable`.

Prescription benefit status:

- `missing`: no PBM row.
- `valid`: PBM row is active, approved, covered, and its payer/policy aligns with coverage.
- `invalid`: inactive/rejected/not found, pending/review where the template has no separate pending enum, or payer/policy mismatch.

Common PBM reason mappings:

- No PBM row -> `pbm_missing`.
- Inactive/rejected/not found/pending review -> `pbm_invalid`.
- PBM payer or policy differs from coverage, or specialty rules conflict with the service -> `pbm_policy_mismatch`.

Pharmacy status:

- Use the rank-1 preferred pharmacy when available.
- Map pharmacy `network_status` to `in_network` or `out_of_network`.
- Use `unknown` when no usable preferred pharmacy or pharmacy lookup exists.

Lifestyle and overall risk:

- Mark lifestyle `high` when there is a major risk factor such as current smoking, heavy alcohol use, no/missing exercise, or very short sleep.
- Mark lifestyle `medium` for former smoking or moderate/subthreshold concerns without a major current factor.
- Mark lifestyle `low` when lifestyle fields are consistently low risk.
- Escalate overall risk to `high` for high lifestyle risk or any serious clinical/access blocker; otherwise use the highest remaining access or lifestyle concern.

Registration status:

- `approved`: all access checks pass and risk is not high.
- `hold`: administrative or coverage/PBM uncertainty blocks automatic approval but does not require rejection.
- `clinical_review`: high overall risk or clinical/access concerns need review but coverage is not a hard reject.
- `rejected`: hard coverage failure such as expired coverage or excluded service line, especially when combined with other blockers.

## Referral Readiness and Chart Activation

For referral batch tasks, filter `referrals` by `batch_id` and join to patients, ICD metadata, documents, and chart artifacts.

Clinical code discrepancies:

- Compare referral `service_line` with ICD `service_family`.
- Compare ICD `chapter` with the expected chapter family when the task asks for chapter checks; common chapters are orthopedics `M00-M99`, pulmonary `J00-J99`, cardiology `I00-I99`, chronic care `E00-E89`/`I00-I99` depending on condition, and dialysis `Z00-Z99`/renal codes.
- Treat ICD/service-family mismatch as `wrong_service_family` or `icd_chapter_mismatch`, depending on the template vocabulary.
- Treat incompatible narrative or referral reason as `clinical_reason_mismatch`/`narrative_mismatch`.
- Treat conflicting laterality between ICD metadata and referral narrative as `laterality_mismatch`.

Administrative and clinical blockers:

- `records_received == 0` -> records missing.
- `imaging_received == 0` -> imaging missing when the template tracks imaging.
- `auth_required == 1` and `auth_status` is denied, pending, or not submitted -> authorization blocker.
- `appointment_scheduled == 1` before clearance -> already scheduled / scheduled before clearance.
- Same patient and duplicate referral signals such as matching fax/insurance plus duplicate notes -> duplicate group; keep the earliest or most complete referral unless task rules say otherwise.
- Same insurance ID across different patients -> shared insurance anomaly; same insurance ID for the same patient is a duplicate-referral signal, not a shared-patient anomaly.

Readiness status:

- `ready`: no clinical discrepancy, missing records/imaging, auth blocker, duplicate review, shared insurance anomaly, or pre-clearance appointment issue.
- `blocked`: missing records/imaging or auth blocker is present.
- `under_review`: clinical code/narrative/laterality discrepancy, duplicate referral, or pre-clearance appointment issue is present without stronger template-specific status.
- `admin_followup`: administrative anomaly only, such as shared insurance across different patients.

Action/correspondence mappings:

- Clinical code issue -> request corrected ICD / clinical code clarification.
- Narrative mismatch -> confirm narrative / clinical reason clarification.
- Laterality mismatch -> confirm laterality.
- Duplicate group -> consolidate duplicate / duplicate resolution.
- Shared insurance across patients -> verify insurance ID.
- Missing records -> request records.
- Missing imaging -> request imaging.
- Authorization blocker -> resolve authorization.
- Already scheduled before clearance -> review existing appointment / appointment hold notice.

Priority:

- Tier 1 for urgent clinical-code or clinical-reason discrepancies.
- Tier 2 for blocked referrals, duplicate consolidation, appointment-hold work, and routine clinical review.
- Tier 3 for purely administrative follow-up.
- When an explicit ranked `priority_order` is required, include non-ready referrals only; sort by tier, then urgency/severity, then referral ID unless the prompt gives another rule.

Ready referral chart needs:

- Include only referrals that are ready if the template says ready referrals.
- `create_chart` when the patient has no chart at all; `update_chart` when a chart exists but required artifacts are missing/stale; `no_chart_action` when all required artifacts are current.
- For `artifacts_to_create`, include required chart artifacts missing entirely or present only with non-current status. Common artifacts are demographics, active problems, medications, allergies, vitals, labs, and consent.

## Dialysis Transfer Review

Filter `transfer_requests` by transfer batch. Link documents by `transfer_id` and capacity by requested start date and modality.

Packet completeness:

- Required documents are the document codes in the template. Count a document as present only when it is finalized/final.
- Draft or non-final documents do not satisfy required packet completeness.
- `packet_completeness_status` is `complete` when every required document is present, even if some present documents are stale. Staleness is reported separately.

Freshness:

- Compare document `received_date` with the requested start date unless the prompt supplies another anchor date.
- Common freshness windows are 30 days for HBsAg, monthly labs, and PPD/CXR, and 365 days for history and physical. Use template-provided limits when present.
- Include stale entries only for document types the template allows, with the received date and freshness limit.

Capacity and decision:

- Sum `facility_capacity.open_chairs` for the requested start date and modality across locations.
- Capacity is unavailable when the sum is zero or no capacity row exists for that date/modality.
- Feasibility combines packet readiness and capacity: ready on requested start only when packet is complete, no stale required freshness blockers remain, and capacity is available.
- Use clinical review or hold when packet or freshness issues remain; accept only when packet and capacity both clear.
- Clinical nurse ownership is appropriate for missing/stale clinical packet items; scheduling coordinator is appropriate when only capacity/scheduling remains; intake coordinator is appropriate for administrative packet gaps.

## Chronic-Care Program Enrollment

Use `GET /programs/{program_code}/candidates` for the current candidate list, then fetch each candidate's chart and clinical history.

Eligibility and reasons:

- `meets_dmhtn_criteria`: candidate targets diabetes/hypertension and clinical history has active diabetes and hypertension.
- `wrong_target_condition`: candidate target condition is not the program target.
- `missing_active_dmhtn_diagnosis`: clinical history lacks active diabetes plus hypertension for a DM/HTN program.
- `consent_declined` or `consent_missing`: map directly from candidate consent status.
- `chart_not_active`: patient has no active existing chart record.
- `stale_active_problems`, `missing_recent_vitals`, `missing_recent_labs`, `missing_medication_list`: required chart artifacts are missing or not current.
- High-touch reasons include recent hospitalization, recent ED flags, and low adherence.
- CKD adds biweekly monitoring for otherwise enrollable DM/HTN candidates.

Disposition:

- `enroll`: eligible for the target condition, signed consent, active chart, and required chart artifacts are current.
- `hold`: eligible but missing consent or chart artifacts require outreach/chart work.
- `reject`: wrong target condition, missing required diagnosis, or consent declined with inactive chart.

Follow-up cadence:

- `weekly`: high-touch reasons such as recent hospitalization, recent ED visit, or low adherence.
- `biweekly`: CKD monitoring without weekly high-touch reason.
- `monthly`: standard eligible enrollment.
- `deferred`: hold status.
- `none`: reject status.

Outreach:

- Start with candidate `preferred_outreach`.
- Fall back to a usable patient contact when the preferred route is unavailable: phone/SMS requires a phone, email requires an email, and portal requires portal/chart availability.
- Use `none` only when the template allows it and no outreach is required or possible.

Monitoring package:

- High-touch DM/HTN: BP cuff, glucometer, labs, medication reconciliation, and care-plan setup.
- Standard monthly DM/HTN: BP cuff, glucometer, and labs.
- Standard biweekly/CKD DM/HTN: standard package plus medication reconciliation.
- Deferred: consent packet and chart update request when those are the blockers.
- Not applicable: empty components and null first check-in.
