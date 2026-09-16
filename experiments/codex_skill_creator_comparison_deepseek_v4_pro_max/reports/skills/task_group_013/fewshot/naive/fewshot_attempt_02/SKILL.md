---
name: cedar-ridge-intake
description: Solve Cedar Ridge Intake Coordination Portal tasks using REST API data collection, business-rule classification, and template-conformant JSON output. Covers patient access verification, referral readiness audits, transfer packet reviews, chronic-care enrollment panels, and referral-to-chart activation.
---

# Cedar Ridge Intake Coordination — Solver Guide

## Overview

This skill covers task types submitted to the Cedar Ridge Intake Coordination
Portal, a healthcare operations API. Every task follows the same structural
loop: read the prompt for the batch identifier and task type, collect data from
the REST API, classify each entity using deterministic business rules, and emit
a single JSON object that conforms to the provided answer template.

The environment variable `<TASK_ENV_BASE_URL>` is injected into the prompt and
points at the portal base URL. All endpoints are read-only GET or POST /query.

## Data Sources

Always begin by collecting all relevant data before making any classification
decision. Parallelize independent reads.

### REST Endpoints

| Method | Path | Returns |
|--------|------|---------|
| GET    | `/`                     | API root / documentation |
| GET    | `/health`               | Health check |
| GET    | `/patients`             | List of all patients |
| GET    | `/patients/{patient_id}`| Single patient profile (insurance, demographics, contacts, pharmacy preference, lifestyle flags) |
| GET    | `/referrals`            | List of all referrals |
| GET    | `/referrals/{referral_id}` | Single referral (ICD codes, narrative, laterality, urgency, authorization status, documents, scheduling status) |
| GET    | `/transfers`            | List of all dialysis transfers |
| GET    | `/transfers/{transfer_id}` | Single transfer (patient, requested start, packet documents, receiving facility) |
| GET    | `/documents`            | List of all documents |
| GET    | `/chart/{patient_id}`   | Patient chart (problems, medications, labs, vitals, allergies, consent, demographics) |
| GET    | `/programs/{program_code}/candidates` | Current candidate list for a program |
| GET    | `/icd/{code}`           | ICD-10 metadata (chapter, description, laterality, narrative hints) |
| GET    | `/pharmacies`           | Pharmacy directory with network status |
| POST   | `/query`                | Read-only SQL endpoint; accepts `{"query": "<SQL>"}` |

### Data Relationships

- Patients link to referrals, transfers, chart records, and program candidates
  via `patient_id`.
- Referrals carry ICD-10 codes resolvable through `/icd/{code}`.
- Patients carry a `pharmacy_id` resolvable through `/pharmacies`.
- Documents link by `patient_id` or `referral_id` and carry `doc_type` and
  `received_date`.
- Transfers carry `documents` (a list of doc_type strings in the packet) that
  must be validated against a required-documents baseline and checked for
  freshness.

## Template Conformity

Every task ships with `input/payloads/answer_template.json`. The template is
the authoritative schema and must be followed exactly:

- Top-level keys, nested required keys, and value types are non-negotiable.
- Enum values use the exact strings from the template. Never invent aliases.
- Lists ordered "ascending by ID" mean alphanumeric ascending sort.
- Lists marked "unordered set" may appear in any order, but the solver should
  use a consistent internal convention (e.g., alphabetical) to avoid spurious
  differences.
- `null` fields must be explicit JSON `null`, never absent.
- Integer counts must be integers, not floats.
- Dates use `YYYY-MM-DD` format.

## Task-Type Classification Frameworks

Identify the task type from the prompt. Each type is described below with its
decision rules.

---

### Task A: Patient Access Verification (New Patient Intake)

**Prompt signals**: roster ID, patient list, "access verification", "insurance
status", "prescription benefit", "pharmacy network", "registration status".

**Data collection**:
1. Fetch each patient from `/patients/{patient_id}`.
2. For each patient's `pharmacy_id`, fetch `/pharmacies` and resolve network
   status.
3. Fetch each patient's chart from `/chart/{patient_id}` for risk signals.
4. Locate the roster record in the environment to obtain
   `requested_service_date` and `service_line`.

**Field classification rules**:

*insurance_status* — `valid` when the patient record shows active coverage with
a future expiration date; `invalid` when coverage is expired, excluded for the
service line, or otherwise non-applicable; `missing` when no insurance record
exists.

*prescription_status* — `valid` when a PBM (pharmacy benefit manager) record
exists with active policy matching the service date; `invalid` when the PBM
record is expired, mismatched, or inconsistent; `missing` when no PBM record
exists.

*pharmacy_status* — `in_network` when the patient's preferred pharmacy is found
in the pharmacy directory with network participation; `out_of_network` when
found but not in network; `unknown` when the pharmacy_id is absent or not found
in the directory.

*lifestyle_risk* — derived from chart flags and patient profile fields. Use
`high` when multiple risk indicators are present (e.g., smoking, sedentary,
high BMI, substance use flags), `medium` with one or two indicators, `low` when
no flags are present.

*overall_risk* — the higher of lifestyle_risk and any clinical risk flags from
the chart (uncontrolled chronic conditions, recent acute events, missing
preventive care). Treat as `high` when any clinical risk flag is present or
lifestyle_risk is high, `medium` with moderate clinical findings, `low` only
when clean clinical picture and low lifestyle risk.

*blocked_reason_codes* — apply deterministically from field statuses:
- `coverage_expired`: insurance_status is `invalid` due to expiration.
- `coverage_pending`: insurance shows pending/under-review state.
- `excluded_service_line`: service_line from roster is excluded by the
  insurance plan.
- `missing_address`: patient record has no address.
- `emergency_contact_missing`: patient record has no emergency contact.
- `preferred_contact_unavailable`: preferred contact method returned
  unreachable.
- `pbm_invalid`: prescription_status is `invalid`.
- `pbm_missing`: prescription_status is `missing`.
- `pbm_policy_mismatch`: PBM policy does not cover the service line or date.
- `pharmacy_out_of_network`: pharmacy_status is `out_of_network`.
- `pharmacy_unknown`: pharmacy_status is `unknown`.
- `overall_risk_high`: overall_risk is `high`.

*registration_status* — composite decision:
- `approved`: zero blocked_reason_codes.
- `hold`: only minor administrative blockers (missing_address,
  emergency_contact_missing, preferred_contact_unavailable, pharmacy_unknown),
  no clinical or coverage blockers.
- `clinical_review`: at least one clinical-significant blocker
  (overall_risk_high, pbm_invalid, pbm_policy_mismatch, pbm_missing,
  pharmacy_out_of_network, coverage_pending) but no combination of
  coverage_expired + excluded_service_line + additional blockers.
- `rejected`: coverage_expired or excluded_service_line present; *or* three or
  more blockers spanning both coverage and clinical domains.

*cohort_summary* — count patients by registration_status, overall_risk, and
lifestyle_risk. Every count must sum to `total_patients`.

---

### Task B: Referral Readiness Audit

**Prompt signals**: batch ID, "referral", "audit", "ICD", "authorization",
"duplicate", "imaging", "readiness", "priority tiers".

**Data collection**:
1. Fetch all referrals from `/referrals` and filter to the target batch.
2. For each referral, fetch the detail from `/referrals/{referral_id}` and the
   patient from `/patients/{patient_id}`.
3. For each ICD code on each referral, fetch `/icd/{code}` to get chapter
   metadata.
4. Use `/documents` and referral/patient document links to check for missing
   records and imaging.

**ICD discrepancy detection**:
Compare the ICD code's `chapter` against the expected chapter for the service
line. For orthopedic referrals, the expected chapter is `M00-M99`
(musculoskeletal); codes from `S00-T88` (injury) indicate
`icd_chapter_mismatch`. Check the referral narrative against the ICD
description for `narrative_mismatch`. Check laterality fields for
`laterality_mismatch` when the ICD code has laterality constraints that
disagree with the referral.

**Duplicate detection**:
Group referrals by `patient_id`. When multiple referrals exist for the same
patient in the same batch, flag `duplicate_referral`. Designate the earlier or
more complete referral as primary and recommend `consolidate_to_primary`.

**Shared insurance anomalies**:
Group referrals by `insurance_id`. When the same insurance ID appears on
different `patient_id` values, flag `shared_insurance_anomaly`. If the
patients are genuinely distinct, disposition is
`verify_distinct_patient_policy_id`; if it is the same patient under different
referrals, `legitimate_duplicate_same_patient`.

**Blocker sets**:
- `missing_records`: referral or patient has no linked clinical records
  documents.
- `missing_imaging`: referral has no linked imaging documents.
- `auth_blocker`: authorization status is `pending`, `denied`, or
  `not_submitted`.
- `already_scheduled`: referral has an existing appointment before clearance.

**Readiness status**:
- `ready`: zero issue_codes.
- `blocked`: one or more of missing_records, missing_imaging, auth_blocker,
  already_scheduled present.
- `under_review`: only clinical discrepancies (ICD mismatches, narrative
  mismatches, laterality mismatches) — no administrative or authorization
  blockers.
- `admin_followup`: duplicate_referral or shared_insurance_anomaly present
  without clinical or hard blockers.

When multiple issue categories overlap, the most severe status wins:
`blocked` > `under_review` > `admin_followup` > `ready`.

**Priority tier**:
- `tier_1_immediate`: active clinical discrepancy on an urgent referral.
- `tier_2_short_term`: routine referral with resolvable blockers.
- `tier_3_administrative`: administrative-only issues (duplicates, shared
  insurance).

**Action codes** map one-to-one from issue_codes:
- `icd_chapter_mismatch` / `narrative_mismatch` / `laterality_mismatch` →
  `request_corrected_icd`, `confirm_narrative`, `confirm_laterality`.
- `duplicate_referral` → `consolidate_duplicate`.
- `shared_insurance_anomaly` → `verify_insurance_id`.
- `missing_records` → `request_records`.
- `missing_imaging` → `request_imaging`.
- `auth_blocker` → `resolve_authorization`.
- `already_scheduled` → `review_existing_appointment`.

**Summary counts**: count referrals by readiness_status, urgency, and
cross-product of urgency × readiness_status. Include distinct counts for each
issue category (referrals with ICD discrepancies, duplicate groups,
shared-insurance anomalies, etc.).

---

### Task C: Transfer Packet Review (Dialysis / Facility Transfer)

**Prompt signals**: transfer batch ID, "dialysis", "transfer", "packet",
"chair capacity", "requested start", "documents".

**Data collection**:
1. Fetch all transfers from `/transfers` and filter to the target batch.
2. For each transfer, fetch detail from `/transfers/{transfer_id}` and the
   patient from `/patients/{patient_id}`.
3. Check `/documents` for the packet documents linked to each transfer.

**Required documents baseline** (dialysis intake):
`allergy_list`, `face_sheet`, `flu_vaccine`, `hbsag`, `hep_b_antibody_core`,
`history_physical`, `insurance_proof`, `medication_list`, `monthly_labs`,
`physician_orders`, `pneumonia_vaccine`, `ppd_or_cxr`, `transportation`,
`treatment_flowsheets`, `vascular_access_report`.

**Packet completeness**: compare the transfer's document list against the
required baseline. Any missing required type → `incomplete`.

**Document freshness**: only the following doc types have freshness limits:

| Doc Type | Freshness Limit (days) |
|----------|------------------------|
| hbsag | 30 |
| hep_b_antibody_core | 30 |
| history_physical | 365 |
| monthly_labs | 30 |
| ppd_or_cxr | 30 |

A document is stale when `(as_of_date - received_date) > freshness_limit_days`.
Use the current date or the review date specified in the prompt as `as_of_date`.

**Requested-start feasibility**:
Compare the transfer's `requested_start.date` against capacity. A facility with
`open_chairs_total > 0` on that date is `available`, otherwise `unavailable`.
Feasibility is the cross-product:
- Packet complete AND capacity available → `ready_on_requested_start`.
- Packet incomplete AND capacity available → `packet_not_ready_capacity_available`.
- Packet incomplete AND capacity unavailable → `packet_not_ready_capacity_unavailable`.
- Packet complete AND capacity unavailable → `capacity_unavailable` (rare).

**Final intake decision**:
- `accept`: feasibility is `ready_on_requested_start` AND no stale documents
  that would expire before the requested start.
- `hold`: packet is complete but capacity is unavailable, or minor issues.
- `clinical_review`: packet is incomplete, stale documents exist, or capacity
  constraints require clinical judgment. This is the default when any
  non-trivial issue exists.

**Next contact**: `clinical_nurse` with `fax_referring_facility` when packet or
clinical issues need resolution. `intake_coordinator` for administrative gaps.
`scheduling_coordinator` when only capacity is the issue.

**Cohort summary**: total transfers, counts of complete/incomplete packets,
patients with missing or stale documents, capacity availability counts, and
decision/contact-owner distribution.

---

### Task D: Chronic-Care Program Enrollment Panel

**Prompt signals**: program code (e.g., `DMHTN-2026A`), "enrollment panel",
"candidates", "chronic-care", "chart", "monitoring".

**Data collection**:
1. Fetch all candidates from `/programs/{program_code}/candidates`.
2. For each candidate, fetch `/patients/{patient_id}` and
   `/chart/{patient_id}`.
3. Review chart artifacts: active problems, medications, vitals, labs,
   allergies, consent, demographics.

**Eligibility** — `true` when the patient has:
- An active diagnosis matching the program's target condition (e.g., both
  diabetes and hypertension for DMHTN).
- A consent record that is not explicitly declined.
- A chart record exists and is not marked inactive.

`false` when the target condition is absent or consent is declined.

**Enrollment status**:
- `enroll`: eligible AND chart is active with sufficient data AND consent is
  present.
- `hold`: eligible but missing chart artifacts, consent, or recent clinical
  data. The patient can be enrolled after gaps are resolved.
- `reject`: ineligible (wrong condition, consent declined, chart inactive in a
  way that cannot be resolved).

**Reason codes** — apply cumulatively:
- `meets_dmhtn_criteria`: eligible, target condition confirmed.
- `recent_hospitalization_high_touch`: chart shows recent inpatient discharge.
- `low_adherence_high_touch`: medication refill gaps or missed appointments.
- `ckd_biweekly_monitoring`: CKD diagnosis needing closer follow-up.
- `recent_ed_high_touch`: recent emergency department visit.
- `consent_declined`: consent record explicitly refused.
- `consent_missing`: no consent record.
- `chart_not_active`: chart is inactive or absent.
- `stale_active_problems`: problems list not recently updated.
- `missing_recent_vitals`: no vitals in recent period.
- `missing_recent_labs`: no labs in recent period.
- `missing_medication_list`: no medication list.
- `wrong_target_condition`: diagnosis doesn't match program.
- `missing_active_dmhtn_diagnosis`: no active DM/HTN diagnoses.

**Follow-up cadence**:
- `weekly`: high-touch patients (recent hospitalization, ED visit, low
  adherence).
- `biweekly`: CKD or other comorbidity needing closer monitoring.
- `monthly`: standard eligible patients with no acuity flags.
- `deferred`: patients on hold.
- `none`: rejected patients.

**Outreach channel**: from the patient profile's preferred contact or last
successful contact method: `phone`, `portal`, `sms`, `email`, `none`.

**Initial monitoring package**:
- `high_touch_dm_htn`: for weekly-cadence patients. Components: bp_cuff,
  glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation,
  care_plan_setup. First checkin: 7 days.
- `standard_dm_htn`: for biweekly/monthly patients. Components: bp_cuff,
  glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation (add
  care_plan_setup for biweekly). First checkin: 14 or 30 days matching
  cadence.
- `deferred`: for hold patients. Components: consent_packet,
  chart_update_request. First checkin: null.
- `not_applicable`: for rejected patients. Components: []. First checkin:
  null.

**Missing chart artifacts**: enumerate which of `chart_record`, `active_problems`, `vitals`, `labs`, `medications`, `consent` are absent or stale. This derives from chart inspection.

**Summary**: total candidates, eligible/ineligible counts, counts by enrollment
status, follow-up cadence, outreach channel, and monitoring package type.

---

### Task E: Referral-to-Chart Activation (Pulmonary / Specialty)

**Prompt signals**: batch ID, "referral intake", "chart activation",
"pulmonary", "clinical code discrepancy", "blocker sets",
"correspondence queue".

**Data collection**:
1. Fetch all referrals and filter to the target batch.
2. For each, fetch referral detail, patient, chart, and ICD codes.
3. Check authorization status, document links, and scheduling state.

**Readiness classification**:
- `ready`: no blockers. Referral is clear to proceed.
- `under_review`: `clinical_code_discrepancy` present but no hard blockers.
- `blocked`: `authorization_blocked`, `records_missing`, `imaging_missing`, or
  `scheduled_before_clearance` present.
- `admin_followup`: `duplicate_review` present without hard blockers.

Severity precedence: `blocked` > `under_review` > `admin_followup` > `ready`.

**Blocker codes**:
- `clinical_code_discrepancy`: ICD code chapter doesn't match the service line
  (e.g., non-pulmonary code on a pulmonary referral).
- `records_missing`: no clinical records documents linked.
- `imaging_missing`: no imaging documents linked.
- `authorization_blocked`: authorization is denied or not submitted.
- `duplicate_review`: referral is a suspected duplicate.
- `scheduled_before_clearance`: appointment exists before clearance.

**Clinical code discrepancy** — resolve through `/icd/{code}`:
- `wrong_service_family`: ICD chapter belongs to a different specialty.
- `clinical_reason_mismatch`: ICD description doesn't match referral narrative.

**Duplicate handling**:
- Group referrals by patient. When the same patient has multiple referrals,
  create a duplicate_group. The earlier or more complete referral is
  `keep_referral_id`.
- Referrals that were reviewed and determined NOT to be duplicates go in
  `cleared_duplicate_review_referrals`.

**Blocker sets** collect referral IDs by blocker category (`authorization`,
`records`, `imaging`), sorted ascending.

**Ready referral chart needs**: for each `ready` referral, inspect the chart
and list missing artifacts that must be created before the referral can be
confirmed. Chart action is `create_chart` when no chart exists, `update_chart`
when chart exists but lacks required artifacts, `no_chart_action` when chart is
complete. Required artifacts: `demographics`, `active_problems`, `medications`,
`allergies`, `vitals`, `labs`, `consent`. List artifacts alphabetically.

**Correspondence queue**: for non-ready referrals, determine the template type
and reason codes:
- `clinical_code_clarification`: for `clinical_code_discrepancy` (reasons:
  `wrong_service_family`, `clinical_reason_mismatch`).
- `auth_records_request`: for `authorization_blocked` or `records_missing`
  (reasons: `authorization_denied`, `records_missing`).
- `duplicate_resolution`: for `duplicate_review` (reason: `duplicate_review`).
- `appointment_hold_notice`: for `scheduled_before_clearance` combined with
  other blockers (reasons: `appointment_already_scheduled` plus relevant
  others).

**Priority order**: rank non-ready referrals highest-first by severity.
`tier_1_immediate`: active authorization denials or clinical discrepancies on
urgent referrals. `tier_2_short_term`: routine referrals with resolvable
issues. `tier_3_administrative`: duplicates or admin-only issues.

---

## General Workflow

For any task:

1. **Read the prompt** to extract the batch/roster/program identifier, task
   type, and `<TASK_ENV_BASE_URL>`.

2. **Read the answer template** (`input/payloads/answer_template.json`) to
   understand the output shape, required keys, enum values, and ordering rules.

3. **Collect data** from the API in parallel where possible. Start with list
   endpoints, then fetch individual records for the entities in scope.

4. **Classify each entity** using the decision rules above for the identified
   task type. Derive every field deterministically from API data; never guess.

5. **Aggregate cohort summaries** by counting entities in each status bucket.
   Verify counts sum correctly.

6. **Emit the final JSON** as a single object with no surrounding prose.

## API Usage Notes

- The `POST /query` endpoint accepts `{"query": "<SQL statement>"}` and returns
  rows as JSON arrays of objects. Use it for cross-entity joins when list
  endpoints are insufficient. Keep queries read-only.
- `/patients` and `/referrals` return all records; filter client-side by
  batch/roster/program as needed.
- `/transfers` returns all transfers; filter by batch_id.
- `/documents` returns all documents; filter by patient_id or referral_id as
  needed.
- `/chart/{patient_id}` returns the full chart object. Key sub-objects:
  `problems`, `medications`, `labs`, `vitals`, `allergies`, `consent`,
  `demographics`.
- `/icd/{code}` returns `chapter`, `description`, `laterality`, and related
  metadata.
- `/pharmacies` returns a list of pharmacy objects with `pharmacy_id`,
  `network_status`, and contact details.

## Common Pitfalls

- Do not assume a patient is in a batch just because they appear in a roster
  file; verify through the API.
- Document freshness limits differ by doc_type. `history_physical` has a
  365-day window; most labs and vaccines have 30 days.
- `null` vs empty array: use `[]` when a patient has no missing documents,
  `null` when the field is not applicable (e.g., `first_checkin_days` for
  `not_applicable` package).
- Ordering rules in templates are strict: "ascending by referral_id" means
  alphanumeric sort (REF0001 before REF0010).
- Risk classification is cumulative: a patient with `high` clinical risk AND
  `low` lifestyle risk still gets `overall_risk: high`.
- When a referral appears in both duplicate detection and ICD discrepancy, all
  issue codes apply; do not drop any.
