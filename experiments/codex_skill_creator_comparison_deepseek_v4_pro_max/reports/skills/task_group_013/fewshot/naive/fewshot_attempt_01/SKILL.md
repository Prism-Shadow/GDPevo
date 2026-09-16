---
name: cedar-ridge-intake
description: How to use the Cedar Ridge Intake Coordination Portal REST and SQL API for healthcare intake, referral audit, transfer review, chronic-care enrollment, and referral-to-chart activation tasks. Use this skill whenever the task references Cedar Ridge, intake coordination, or the portal at a task environment base URL with /patients, /referrals, /transfers, /chart, /programs, /documents, or /query endpoints.
---

# Cedar Ridge Intake Coordination Portal

This is a shared read-only healthcare intake system. Every task that targets
this system follows the same pattern: collect a batch of patients, referrals,
or transfers from the portal, cross-reference related records, apply the
business rules documented below, and emit a single JSON response matching the
supplied answer template.

## Discovery

The portal root page (`GET /`) is an HTML dashboard. The machine-readable
entrypoints are:

| Endpoint | Description |
|---|---|
| `GET /health` | Database readiness, record counts per table, task group id |
| `GET /patients` | List/search patients (`?q=` query, `?limit=`) |
| `GET /patients/{patient_id}` | Single patient with all related records |
| `GET /referrals` | List/search referrals (`?batch_id=`, `?service_line=`, `?limit=`) |
| `GET /referrals/{referral_id}` | Single referral |
| `GET /transfers` | List/search transfers (`?batch_id=`, `?limit=`) |
| `GET /transfers/{transfer_id}` | Single transfer |
| `GET /documents` | List/search documents |
| `GET /chart/{patient_id}` | Chart artifacts, clinical history, vitals, labs, active problems |
| `GET /programs/{program_code}/candidates` | Program enrollment candidates |
| `GET /icd/{code}` | ICD-10 code metadata (chapter, description, laterality, service_family) |
| `GET /pharmacies` | Pharmacy directory with network status |
| `POST /query` | Read-only SQL. Body: `{"sql": "SELECT ..."}`. Returns `{columns, row_count, rows, truncated}` |

All GET endpoints return JSON. The `POST /query` endpoint accepts any `SELECT`
against the live schema; use it to join tables, filter by date ranges, or
aggregate counts when the REST endpoints cannot express the needed query.

## Data Model

Every patient is the hub. When you fetch `GET /patients/{id}`, the response
bundles all related records in one object with these top-level keys:

- `patient` -- demographics (address, dob, email, phone, language,
  emergency_contact_present, existing_chart, preferred_contact)
- `coverage` -- list of insurance policies (payer, policy_number, status,
  effective_date, termination_date, service_lines, network_status)
- `pbm` -- pharmacy benefit manager records (active, formulary_status, status,
  policy_number, payer)
- `pharmacies` -- preferred pharmacies (pharmacy_id, network_status,
  preference_rank)
- `lifestyle` -- alcohol_use, exercise_frequency, sleep_hours, smoking_status
- `chart_artifacts` -- list of chart entries (artifact_type, status,
  last_updated). Status values include `current` and `stale`.
- `clinical_history` -- chronic_conditions, medication_count, allergy_count,
  recent_hospitalization, risk_flags, surgeries
- `referrals` -- referrals for this patient
- `rosters` -- intake roster membership
- `transfers` -- transfer requests for this patient
- `documents` -- documents linked to this patient
- `program_candidates` -- program enrollment records

**Referrals** include: referral_id, patient_id, batch_id, icd10_code,
diagnosis_description, referral_reason, service_line, urgency,
assigned_physician, referring_physician, referring_practice, referring_phone,
referring_fax, auth_required, auth_status, records_received, imaging_received,
appointment_scheduled, appointment_date, insurance_id, payer, notes.

**Transfers** include: transfer_id, patient_id, batch_id,
requested_start_date, requested_end_date, modality, chair_window,
days_requested, referring_facility, status_note, transportation.

**Documents** include: document_id, patient_id, transfer_id, referral_id,
doc_type, status (`final`/`draft`), finalized (0/1), received_date,
content_tag.

**ICD codes**: `GET /icd/{code}` returns `chapter`, `description`, `laterality`
(null when not applicable), and `service_family`. Use `service_family` to
detect wrong-service-line referrals; use `chapter` to detect ICD chapter
mismatches (a code from, say, S00-T88 on an orthopedics referral is a mismatch
because orthopedics codes normally live in M00-M99).

**Facility capacity** is accessible only through `POST /query` against the
`facility_capacity` table (columns: location_id, date, modality, open_chairs).
Sum `open_chairs` across all locations for a given date and modality to get
total open chairs.

## Workflow Patterns

Every task follows this general sequence:

1. **Read the answer template** supplied in the task payloads. It defines every
   required key, allowed enum value, sort order, and list shape. All output
   must conform to it exactly.

2. **Collect the batch** using the batch-specific endpoint or SQL query.
   - For rosters: `POST /query` with `SELECT ... FROM intake_rosters WHERE
     roster_id = ...`
   - For referrals: `GET /referrals?batch_id=...`
   - For transfers: `GET /transfers?batch_id=...`
   - For program candidates: `GET /programs/{code}/candidates`

3. **Enrich each record** by fetching patient details (`GET
   /patients/{id}`), chart data (`GET /chart/{id}`), ICD metadata (`GET
   /icd/{code}`), documents, and facility capacity as needed.

4. **Apply business rules** (see sections below) to derive statuses, reason
   codes, risk levels, and decisions.

5. **Aggregate cohort summaries** from the per-record results. Count across
   the controlled enum values specified in the template. Integer counts only.

6. **Sort lists** exactly as the template requires (typically `patient_id` or
   `referral_id` or `transfer_id` ascending). Enum key arrays in template
   outputs (reason codes, blocker codes) are unordered sets but lists in JSON;
   include each code at most once per item, in any stable order.

## Business Rules by Domain

### Patient Access Verification (Primary Care / New Patient Intake)

**Insurance status** (`valid` / `invalid` / `missing`):
- Find the best coverage record: prefer the one whose `service_lines` includes
  the rostered service line, then fall back to the first active record.
- `valid`: coverage `status` is `"active"` AND `service_lines` contains the
  rostered service line.
- `invalid`: coverage `status` is `"expired"`, `"pending"`, or `"active"` but
  `service_lines` does not include the rostered service line.
- `missing`: no coverage record exists.

**Prescription (PBM) status** (`valid` / `invalid` / `missing`):
- Match PBM to the patient's coverage by `payer` and `policy_number`.
- `valid`: PBM `active == 1` AND PBM `status == "approved"`.
- `invalid`: PBM `active == 0` OR PBM `status` is `"rejected"` or `"pending"`,
  OR PBM `policy_number` differs from the coverage `policy_number`
  (a policy-number mismatch is a PBM-level issue). Also invalid if
  `formulary_status == "review"` and `status == "pending"`.
- `missing`: no PBM record.

**Pharmacy status** (`in_network` / `out_of_network` / `unknown`):
- Use the patient's top-ranked pharmacy (`preference_rank == 1`).
- Read the pharmacy's `network_status`.
- `unknown`: no pharmacy records.

**Lifestyle risk** (`low` / `medium` / `high`):
- Derived from lifestyle fields. Heavier alcohol use, current smoking, low
  sleep hours, and absent exercise push risk higher. Former smokers with
  moderate habits are typically medium. Multiple risk factors (heavy alcohol +
  current smoking + low sleep) yield high.

**Overall risk** (`low` / `medium` / `high`):
- If lifestyle risk is `high` or any combination of blockers exists, overall
  risk is typically `high`. Treat overall risk as the maximum of lifestyle
  risk and a clinical-risk signal derived from the presence of any other
  flagged issues.

**Blocked reason codes** (use only the codes listed in the answer template):
- `coverage_expired` -- coverage status is `"expired"`.
- `coverage_pending` -- coverage status is `"pending"`.
- `excluded_service_line` -- the rostered service line is not in the
  coverage's `service_lines`.
- `missing_address` -- patient address is null.
- `emergency_contact_missing` -- `emergency_contact_present == 0`.
- `preferred_contact_unavailable` -- the patient's `preferred_contact` channel
  cannot be reached: `"email"` with null email, `"phone"` or `"sms"` with null
  phone.
- `pbm_invalid` -- PBM status is invalid (rejected, pending, inactive).
- `pbm_missing` -- no PBM record.
- `pbm_policy_mismatch` -- PBM `policy_number` differs from coverage
  `policy_number`.
- `pharmacy_out_of_network` -- pharmacy `network_status` is `"out_of_network"`.
- `pharmacy_unknown` -- no pharmacy on file.
- `overall_risk_high` -- overall risk evaluated as `"high"`.

**Registration status** (`approved` / `hold` / `clinical_review` / `rejected`):
- `approved`: no blockers.
- `clinical_review`: one or more non-fatal blockers (coverage_pending, PBM
  issues, pharmacy issues, missing address, preferred_contact_unavailable,
  overall_risk_high) but no hard-fatal blockers.
- `rejected`: contains hard-fatal blockers (coverage_expired,
  excluded_service_line combined with other issues, or a heavy combination
  of major issues).
- `hold`: used when the template provides it; follow template-specific rules
  (may indicate deferred pending actions).

If coverage is expired or coverage is active but excludes the service line
AND there are multiple other blockers, the result is usually `rejected`. If
coverage is merely pending, it tends toward `clinical_review` instead.

### Referral Audit (Orthopedic, Pulmonary, etc.)

**ICD discrepancy detection**:
For every referral, fetch `GET /icd/{icd10_code}`.
- `icd_chapter_mismatch`: the ICD chapter does not belong to the expected
  chapter range for the referral's service line. For example, orthopedics
  referrals expect codes in chapter M00-M99; an S00-T88 code is a chapter
  mismatch. Pulmonary expects J00-J99; an I00-I99 or R00-R99 code is a
  mismatch.
- `narrative_mismatch`: the referral's `diagnosis_description` or
  `referral_reason` conflicts with the ICD description. For example, a
  pulmonary referral with a cardiology ICD code and "worsening symptoms" where
  the ICD describes something unrelated.
- `laterality_mismatch`: the ICD code has a `laterality` value but the
  narrative does not match or is missing laterality.
- Also flag when `service_family` from the ICD lookup does not match the
  referral's `service_line`.

**Duplicate detection**:
- Group referrals by same `patient_id` where ICD codes, referring practice, or
  date_received suggest the referral was submitted more than once. The
  referral `notes` field may contain "possible duplicate" as a hint.
- In each duplicate group, designate one referral as primary (typically the
  earlier-received or first-listed).

**Shared insurance anomaly**:
- If the same `insurance_id` appears on referrals for different `patient_ids`,
  flag it with disposition `"verify_distinct_patient_policy_id"`. If it
  appears multiple times for the same patient, disposition is
  `"legitimate_duplicate_same_patient"`.

**Blocker identification**:
- `missing_records`: `records_received == 0`.
- `missing_imaging`: `imaging_received == 0`.
- `auth_blocker`: `auth_required == 1` AND `auth_status` is `"denied"` or
  `"pending"` or `"not_submitted"`.
- `already_scheduled`: `appointment_scheduled == 1` (check whether this was
  scheduled before referral clearance).
- `duplicate_referral`: the referral is part of a detected duplicate group.
- `shared_insurance_anomaly`: the referral is part of a shared-insurance
  anomaly group.

**Readiness status** (`ready` / `blocked` / `under_review` / `admin_followup`):
- `ready`: no issues.
- `blocked`: has auth_blocker, missing_records, missing_imaging, or
  already_scheduled blocker.
- `under_review`: has ICD discrepancies or duplicate issues but no hard
  blockers.
- `admin_followup`: has shared_insurance_anomaly only (administrative rather
  than clinical).

**Priority tiers**:
- `tier_1_immediate`: urgent referrals with ICD discrepancies requiring fast
  correction.
- `tier_2_short_term`: routine referrals with blockers, duplicates, or
  discrepancies that need follow-up this week.
- `tier_3_administrative`: shared insurance anomalies or other administrative
  issues that do not block clinical scheduling.

**Action codes** map directly to issues found:
- `request_corrected_icd` -- ICD discrepancy
- `confirm_narrative` -- narrative mismatch
- `confirm_laterality` -- laterality mismatch
- `consolidate_duplicate` -- duplicate referral
- `verify_insurance_id` -- shared insurance anomaly
- `request_records` -- missing records
- `request_imaging` -- missing imaging
- `resolve_authorization` -- auth blocker
- `review_existing_appointment` -- already scheduled

### Transfer Review (Dialysis, Seasonal)

**Document completeness**:
The required document types for a dialysis transfer packet are:
`allergy_list`, `face_sheet`, `flu_vaccine`, `hbsag`, `hep_b_antibody_core`,
`history_physical`, `insurance_proof`, `medication_list`, `monthly_labs`,
`physician_orders`, `pneumonia_vaccine`, `ppd_or_cxr`, `transportation`,
`treatment_flowsheets`, `vascular_access_report`.

A document is **missing** if it is absent from the transfer's documents OR
exists but `finalized == 0` (draft). A document is **present** if it exists
with `finalized == 1` (final).

`packet_completeness_status` is `"complete"` only when all 15 required
document types are present. Otherwise `"incomplete"`.

**Document freshness (staleness)**:
Each document type has a freshness window expressed in days, measured backward
from the transfer's `requested_start_date`.

| Document type | Freshness limit (days) |
|---|---|
| hbsag | 30 |
| monthly_labs | 30 |
| ppd_or_cxr | 30 |
| hep_b_antibody_core | 30 |
| history_physical | 365 |

A final document is **stale** when:
`requested_start_date - received_date > freshness_limit_days`.

Only include stale documents that are listed in the answer template's allowed
`doc_type` enum for staleness (typically hbsag, hep_b_antibody_core,
history_physical, monthly_labs, ppd_or_cxr). Do not flag other document types
as stale even if they are old.

**Capacity check**:
Use `POST /query` to read `facility_capacity` for the transfer's
`requested_start_date`, summing `open_chairs` across all locations for
`modality == "in_center_hemodialysis"`.

- `capacity_status`: `"available"` when `open_chairs_total > 0`, else
  `"unavailable"`.
- `open_chairs_total`: the integer sum.

**Feasibility**:
- `"ready_on_requested_start"`: packet complete AND no stale docs AND capacity
  available.
- `"packet_not_ready_capacity_available"`: packet has missing or stale docs
  AND capacity available.
- `"packet_not_ready_capacity_unavailable"`: packet has missing or stale docs
  AND capacity unavailable.
- `"capacity_unavailable"`: packet is ready but capacity is unavailable.

**Final intake decision**:
- `"accept"`: ready on requested start.
- `"hold"`: complete packet but capacity unavailable (template-dependent).
- `"clinical_review"`: packet has missing or stale documents -- clinical nurse
  must review before accepting.

**Next contact**:
- `next_contact_owner`: `"clinical_nurse"` for clinical review cases;
  `"scheduling_coordinator"` for capacity-only issues; `"intake_coordinator"`
  for administrative gaps; `"none"` for accepted transfers.
- `next_contact_route`: `"fax_referring_facility"` when the referring facility
  must send updated documents; `"phone_patient"` for patient outreach;
  `"internal_queue"` for internal handoffs; `"none"` for accepted transfers.

### Chronic-Care Enrollment Panel

**Eligibility**:
- `eligible: true` when `target_condition` includes diabetes and hypertension
  (check both "diabetes_hypertension" and "diabetes_hypertension" variants).
- `eligible: false` when `target_condition` is unrelated (e.g., "copd" alone).

**Reason codes** (unordered set):
- `meets_dmhtn_criteria`: candidate's target_condition matches the program AND
  chart confirms diabetes+hypertension in chronic_conditions.
- `wrong_target_condition`: target_condition does not match the program.
- `missing_active_dmhtn_diagnosis`: chronic_conditions lacks evidence of both
  diabetes and hypertension, or active_problems is stale/missing.
- `consent_declined`: consent_status == `"declined"`.
- `consent_missing`: consent_status == `"missing"`.
- `chart_not_active`: existing_chart == 0 OR chart has no current artifacts.
- `stale_active_problems`: chart's active_problems status is `"stale"`.
- `missing_recent_vitals`: no vitals artifact in recent_vitals_labs.
- `missing_recent_labs`: no labs artifact in recent_vitals_labs.
- `missing_medication_list`: no medications artifact in chart.
- `recent_hospitalization_high_touch`: clinical_history.recent_hospitalization
  == 1.
- `low_adherence_high_touch`: adherence_score < 50.
- `ckd_biweekly_monitoring`: chronic_conditions includes "ckd".
- `recent_ed_high_touch`: (from clinical data when the patient has had recent
  ED utilization).

**Enrollment status**:
- `enroll`: eligible AND consent signed AND chart active.
- `hold`: eligible but chart issues or missing consent prevent immediate
  enrollment.
- `reject`: ineligible (wrong condition) OR consent declined OR chart
  inactive with no path to resolve quickly.

**Follow-up cadence**:
- `weekly`: high-touch patients (recent hospitalization, low adherence, recent
  ED).
- `biweekly`: patients with CKD requiring closer monitoring.
- `monthly`: standard eligible patients without high-touch triggers.
- `deferred`: hold status -- waiting on chart updates or consent.
- `none`: rejected patients.

**Outreach channel**:
Use the candidate's `preferred_outreach` field, mapped to the enum:
- `portal` -> `"portal"`
- `phone` -> `"phone"`
- `email` -> `"email"`
- `sms` -> `"sms"`
- If no viable channel, fall back to `"email"` when email exists, else
  `"phone"` when phone exists, else `"none"`.

**Missing chart artifacts** (unordered set):
From the allowed list: `chart_record`, `active_problems`, `vitals`, `labs`,
`medications`, `consent`. Include each artifact type that is absent, stale, or
incomplete in the patient's chart, checking only the types in the allowed list.

**Initial monitoring package**:
- `standard_dm_htn`: standard eligible patients. Components typically include
  `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid` (plus
  `medication_reconciliation` or `care_plan_setup` depending on needs).
  `first_checkin_days` matches follow-up cadence: 14 for biweekly, 30 for
  monthly.
- `high_touch_dm_htn`: high-touch patients. Components add `care_plan_setup`
  to the standard set. `first_checkin_days`: 7 for weekly.
- `deferred`: hold patients. Components: `consent_packet` and
  `chart_update_request`. `first_checkin_days`: null.
- `not_applicable`: rejected patients. Components: []. `first_checkin_days`:
  null.

### Referral-to-Chart Activation (Pulmonary example)

**Readiness per referral**:
Same blocker logic as Referral Audit above (ICD discrepancy, records_missing,
imaging_missing, authorization_blocked, duplicate_review,
scheduled_before_clearance).

**Clinical code discrepancy referrals**:
List every referral_id that has an ICD mismatch (wrong service_family, chapter
mismatch, or clinical reason mismatch against the ICD description).

**Duplicate handling**:
- `duplicate_groups`: same-patient, same-ICD referrals submitted through
  different channels. Identify the `keep_referral_id` (the primary).
- `cleared_duplicate_review_referrals`: referrals that were in a possible
  duplicate note but turned out to be distinct (different ICD codes, different
  referral reasons, legitimately separate).

**Ready referral chart needs**:
For each `ready` referral, inspect the patient's chart (`GET
/chart/{patient_id}`):
- `chart_action`: `"create_chart"` if no chart exists; `"update_chart"` if
  chart exists but some required artifacts are missing or stale;
  `"no_chart_action"` if chart is fully current.
- `artifacts_to_create`: list (alphabetical) of missing artifact types from
  the allowed enum: `demographics`, `active_problems`, `medications`,
  `allergies`, `vitals`, `labs`, `consent`.

**Correspondence queue**:
For referrals that are not `ready`:
- `clinical_code_clarification`: ICD discrepancy referrals. Reason codes
  include `wrong_service_family` or `clinical_reason_mismatch`.
- `auth_records_request`: authorization denied + records missing. Reason codes
  include `authorization_denied` and `records_missing`.
- `duplicate_resolution`: duplicate review referrals.
- `appointment_hold_notice`: already-scheduled referrals with other blockers.
  Reason codes include `appointment_already_scheduled`.

**Priority order** (non-ready referrals only, highest-priority first):
- `tier_1_immediate`: urgent + clinical code discrepancy.
- `tier_2_short_term`: routine with auth/records/imaging blockers or
  discrepancies.
- `tier_3_administrative`: duplicate-only or scheduling-only issues.

## Using the SQL Endpoint

`POST /query` accepts `{"sql": "SELECT ..."}`. The response shape is
`{columns, row_count, rows, truncated}`. Use this endpoint when:

- Filtering `intake_rosters` by roster_id.
- Querying `facility_capacity` for date ranges and summing open_chairs.
- Joining `documents` with transfers to assess packet completeness across a
  batch.
- Aggregating counts that span multiple tables.
- Retrieving specific subsets of records that the REST list endpoints cannot
  filter precisely enough.

Always `SELECT` specific columns rather than `*` when you only need a subset,
to keep responses compact.

## General Guidance

**Templates are authoritative**: Every task supplies an `answer_template.json`.
It defines the exact JSON shape, allowed enum values, sort order, and required
keys. Your output must match it. Do not invent keys or values outside the
template.

**Sort orders**: Patient-level lists are always sorted ascending by the entity
id (`patient_id`, `referral_id`, `transfer_id`). Summary count keys use the
order defined in the template. Reason-code and blocker-code arrays are
unordered sets; use a stable alphabetical or appearance-order listing.

**Enum discipline**: Only use values from the template's `allowed_values`
lists. If the data suggests a condition not covered by the allowed enum values,
map it to the closest matching value or the catch-all value defined in the
template.

**Null handling**: When a field is null in the source data, reflect that in
the output only where the template allows null (e.g., `priority_tier` null,
`first_checkin_days` null). Otherwise map null source data to the appropriate
enum value (e.g., missing coverage -> `"missing"`).

**Reference dates**: When computing freshness or staleness, use the
task-relevant reference date. For transfers that is the `requested_start_date`.
For chart staleness the reference is typically the current date or an `as_of`
date specified in the task. For referral readiness it is the intake processing
date.

**Data enrichment order**: Fetch the batch records first, then enrich in
parallel where possible. Use `GET /patients/{id}` to get coverage, PBM,
pharmacy, and lifestyle all at once. Use `GET /chart/{id}` for chart details.
Use `GET /icd/{code}` for code lookups. Use `POST /query` for
cross-table aggregations.

**Cohort summaries**: After processing all individual records, count across
the status and risk enum values. Every integer-count field must sum to the
total cohort size. Cross-check: the sum of `counts_by_registration_status`
values must equal `total_patients`; the sum of `status_counts` must equal
`total_candidates`; etc.
