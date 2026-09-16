---
name: cedar-ridge-intake
description: Solve Cedar Ridge Intake Coordination Portal tasks that require strict JSON outputs for patient access verification, specialty referral readiness or chart activation, dialysis transfer packet review, and chronic-care program enrollment. Use when prompts reference the Cedar Ridge portal, TASK_ENV_BASE_URL, rosters, referral batches, transfer batches, program candidates, or answer_template.json controlled values.
---

# Cedar Ridge Intake

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. The template controls required keys, allowed enum values, list ordering, and counts.
2. Resolve `<TASK_ENV_BASE_URL>` from the prompt or environment. Use only the portal endpoints exposed for the task.
3. Identify the workflow from the prompt:
   - New patient roster/access verification: roster id plus patient ids.
   - Referral readiness or chart activation: referral `batch_id`.
   - Dialysis transfer review: transfer `batch_id`.
   - Chronic-care enrollment: program code and `/programs/{code}/candidates`.
4. Collect evidence from the portal, derive controlled codes, then emit one JSON object only. Do not include prose, comments, or unrequested fields.
5. Recompute all summary counts from the patient/referral/transfer rows after finalizing statuses.

Use the helper when it saves time, from this skill directory or by passing the equivalent path:

```bash
python scripts/portal_collect.py --base-url "$TASK_ENV_BASE_URL" --schema
python scripts/portal_collect.py --base-url "$TASK_ENV_BASE_URL" --roster "$ROSTER_ID" --patient-ids "$IDS"
python scripts/portal_collect.py --base-url "$TASK_ENV_BASE_URL" --referral-batch "$BATCH_ID"
python scripts/portal_collect.py --base-url "$TASK_ENV_BASE_URL" --transfer-batch "$BATCH_ID"
python scripts/portal_collect.py --base-url "$TASK_ENV_BASE_URL" --program "$PROGRAM_CODE"
```

The script only gathers portal JSON and useful SQL-filtered rows. You still need to apply the template-specific judgment rules below.

## Portal Evidence

- Prefer detail endpoints when available: `/patients/{patient_id}`, `/referrals/{referral_id}`, `/transfers/{transfer_id}`, `/chart/{patient_id}`, `/icd/{code}`.
- Use `POST /query` with `{"sql": "..."}` for precise filtering against `patients`, `intake_rosters`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`, `clinical_history`, `referrals`, `documents`, `transfer_requests`, `facility_capacity`, `program_candidates`, `chart_artifacts`, and `icd_codes`.
- Treat `0` and `1` fields as booleans. For documents, only `finalized = 1` and final status count as present. Draft or absent documents are missing.
- For chart work, an artifact is ready only when present with `status: "current"`. Missing or stale artifacts require creation or update when the template asks for chart needs.
- If a SQL response is truncated, narrow the query by roster, batch, transfer id, referral id, patient id, program code, or date.

## New Patient Access

For each roster patient, use the roster service date and service line, then inspect patient detail, coverage, PBM, preferred pharmacy, lifestyle, and clinical history.

- `insurance_status`: `valid` when coverage is active on the requested service date, in network, and includes the requested service line. Use `invalid` for expired, pending, out-of-network, or excluded-service-line coverage. Use `missing` only when no coverage record exists.
- `prescription_status`: `valid` when a PBM record is active, approved, covered, and matches the selected coverage payer/policy. Use `invalid` for inactive/rejected/pending/review records or a policy mismatch. Use `missing` when no PBM record exists.
- `pharmacy_status`: use the rank-1 preferred pharmacy network status; use `unknown` when no preferred pharmacy or no network status is available.
- Contact blockers: email requires a non-null email; phone and sms require a non-null phone. Portal contact does not require email or phone.
- Address and emergency-contact blockers come directly from patient demographics.
- Lifestyle risk: current smoking, heavy alcohol use, no/unknown exercise, or short sleep should push risk high; former smoking, moderate alcohol, limited exercise, or borderline sleep should push risk medium unless high triggers exist; otherwise low.
- Overall risk: elevate to high for high lifestyle risk, recent hospitalization, nonempty clinical `risk_flags`, major polypharmacy or complex medication reconciliation, or multiple serious access blockers. Use medium for moderate lifestyle or chronic complexity, and low only when clinical and access signals are clean.
- Registration status: reject when a hard coverage problem makes the service line unusable, use clinical review for high overall risk or clinically significant unresolved issues, use hold for administrative issues that can be corrected, and approve only when required access checks pass and risk is not high.

Map common blocked reasons exactly to template enums: expired coverage, pending coverage, excluded service line, missing address, missing emergency contact, invalid/missing/mismatched PBM, out-of-network or unknown pharmacy, unavailable preferred contact, and high overall risk.

## Referral Readiness And Activation

Filter referrals by the target `batch_id`, then enrich each row with ICD metadata, documents, patient, chart, and batch-level duplicate/shared-insurance checks.

- Clinical code discrepancy:
  - Compare `icd.service_family` with referral `service_line`.
  - For orthopedics, expect musculoskeletal `M00-M99` codes unless the prompt clearly accepts injury codes; injury or other chapters can be chapter mismatches even when the service family is orthopedics.
  - For pulmonary, `J00-J99` pulmonary disease codes and relevant respiratory symptom codes can be acceptable; other service families are wrong-service-family discrepancies.
  - Flag narrative mismatch when `referral_reason` or diagnosis narrative conflicts with the service line or ICD meaning.
  - Flag laterality mismatch when ICD laterality conflicts with left/right/bilateral wording in the referral narrative.
- Blockers: missing records, missing imaging, authorization required with denied/pending/not-submitted status, scheduled appointments before clearance, duplicate review, shared insurance across different patients, and clinical code discrepancies.
- Readiness: `ready` when no blockers remain; `blocked` when records, imaging, or authorization prevents scheduling; `under_review` for clinical code, duplicate, or existing-appointment review without hard missing-item blockers; `admin_followup` for administrative-only anomalies such as shared insurance.
- Duplicate groups: group same-batch referrals for the same patient; keep the earliest or lowest referral id unless the portal indicates another primary. Same insurance across different patients is a shared-insurance anomaly, not a duplicate group.
- Cleared duplicate review: when notes suggest possible duplicate but patient and insurance evidence do not form a true duplicate group, list the referrals as cleared if the template asks for them.
- Priority: tier 1 for urgent clinical-code issues; tier 2 for hard blockers, routine clinical review, duplicates, or appointments needing review; tier 3 for administrative-only follow-up. In priority lists, sort by tier first, then urgency/severity, then referral id.
- Chart activation for ready referrals: create a chart if `existing_chart` is false; update a chart when required artifacts are missing or stale; no chart action only when all requested artifacts are current.

Map issue codes to actions: corrected ICD or clarification for code discrepancies, confirm narrative/laterality for those mismatch types, request records, request imaging, resolve authorization, consolidate duplicates, verify insurance id, and review existing appointments.

## Dialysis Transfer Review

Filter `transfer_requests` by batch and use transfer details, packet documents, patient records, and `facility_capacity`.

- Packet completeness is based on required document types in the answer template. A draft document is missing. Stale documents do not make the packet incomplete, but they do make it not ready.
- Use requested start date as the freshness anchor. Common limits: hbsag 30 days, monthly labs 30 days, ppd-or-cxr 30 days, history and physical 365 days, and hepatitis B core antibody about 365 days unless the template or portal states otherwise.
- Capacity status is available when the sum of open chairs for the requested date and modality is greater than zero.
- Feasibility combines packet readiness and capacity: ready on requested start only when complete, fresh, and capacity is available; otherwise use the template value that names packet-not-ready and/or capacity-unavailable.
- Decision: accept only when packet and capacity are ready; hold when the packet is ready but scheduling capacity is not; clinical review when required or freshness-sensitive packet items are missing/stale.
- Contact owner/route: clinical packet defects go to the clinical nurse by referring-facility fax; capacity-only holds go to scheduling; purely administrative missing demographics/insurance/transport may go to intake coordination when the template offers that owner.

## Chronic-Care Enrollment

Use `/programs/{program_code}/candidates` for the row set, then inspect `/chart/{patient_id}` and patient contact fields.

- Eligibility is based on target condition and active diagnosis evidence. For diabetes-plus-hypertension programs, require the candidate target condition and chart history to support both diabetes and hypertension; wrong target condition or missing active diagnosis makes the candidate ineligible.
- Enrollment status: enroll eligible candidates with signed consent and an active/current chart; hold eligible candidates with missing consent or remediable chart gaps; reject declined consent, inactive chart with declined consent, or wrong target condition.
- Reason codes: include the meet-criteria code only for candidates actually moving to enrollment. Add high-touch reasons for recent hospitalization, low adherence, or recent ED flags. Add CKD biweekly monitoring when CKD is present without a higher-touch trigger. Add consent and chart-readiness reason codes from candidate/chart evidence.
- Missing chart artifacts: include chart record when no active chart exists; include active problems, vitals, labs, medications, and consent when absent or stale and relevant to the program template.
- Outreach channel: prefer the candidate's requested outreach when the needed contact exists; otherwise fall back to patient preferred contact, then available email/phone/sms, and use `none` only when no allowed route is usable. Portal outreach generally requires an active chart.
- Monitoring package: high-touch packages use weekly follow-up, first check-in in 7 days, and include care-plan setup plus device/lab/medication-reconciliation components. CKD standard monitoring is usually biweekly with medication reconciliation. Routine standard monitoring is monthly with device and lab-order components. Deferred packages include consent and chart-update work; rejected candidates are not applicable.
