# Cedar Ridge Intake Coordination — Reusable Operating Rules

## Purpose

Execute intake-coordination tasks against the Cedar Ridge Intake Coordination Portal. This skill covers patient access verification, referral auditing, transfer review, chronic-care enrollment panel assembly, and referral-to-chart activation. Adapt the workflow to whichever intake domain the prompt specifies.

## Pre-Flight

### Environment

The portal base URL and allowed endpoints are defined in `environment_access.md` at the repository root. Read that file first and resolve `<TASK_ENV_BASE_URL>` (or `TASK_ENV_BASE_URL`) placeholders in prompts to the `base_url` value it declares. Use only the endpoints listed in its `allowed_endpoints` block; do not invent URLs.

```
allowed route set (subject to change — always consult environment_access.md):
  GET  /
  GET  /patients
  GET  /patients/{patient_id}
  GET  /referrals
  GET  /referrals/{referral_id}
  GET  /transfers
  GET  /transfers/{transfer_id}
  GET  /documents
  GET  /chart/{patient_id}
  GET  /programs/{program_code}/candidates
  GET  /icd/{code}
  GET  /pharmacies
  POST /query
```

No credentials are required.

### Answer Template

Every task includes an `input/payloads/answer_template.json` that defines the required output shape. Read it first — before fetching any portal data. The template specifies:

- Required top-level keys and their types
- Enum sets for every controlled-vocabulary field
- Ordering rules for lists (ascending by ID, alphabetical by code, unordered set)
- Mandatory patient/referral/transfer IDs when the scope is pre-defined
- Summary/count fields with exact key names and precision

**Do not deviate from the template.** Use only values enumerated in the schema. Introduce no new keys or free-form prose outside the JSON structure.

### Task Identification

The prompt names exactly one domain object that scopes the work:

| Concept | Identified by | Portal fetch |
|---------|---------------|--------------|
| Patient access roster | `roster_id` (e.g. NPI-JUN-01) | Read `target_roster.json` if present; otherwise seed from prompt IDs |
| Referral batch | `batch_id` (e.g. ORTHO-JUN-01, PULM-JUN-02) | `GET /referrals` filtered to batch |
| Transfer batch | `batch_id` (e.g. DIAL-WINTER-01) | `GET /transfers` filtered to batch |
| Program enrollment panel | `program_code` (e.g. DMHTN-2026A) | `GET /programs/{program_code}/candidates` |

Use the portal to discover the full set of records within the scoped batch — do not assume the prompt lists every ID.

## Portal Interaction Pattern

### Fetch Order

Work from collections to individual records:

1. **Fetch the collection** appropriate to the task (`/patients`, `/referrals`, `/transfers`, `/programs/{code}/candidates`).
2. **Filter** to the scoped batch/roster/program. If the collection endpoint returns records from multiple batches, use `POST /query` with a SQL `SELECT` (or `WHERE batch_id = ...`) to narrow. Alternatively, iterate the collection and filter client-side on the batch/roster field.
3. **Drill into each record** individually:
   - `GET /patients/{patient_id}` — patient identity, insurance, demographics
   - `GET /referrals/{referral_id}` — referral detail, ICD codes, urgency, authorization fields
   - `GET /transfers/{transfer_id}` — transfer request, packet status, requested start date
   - `GET /chart/{patient_id}` — active problems, vitals, labs, medications, consent status
   - `GET /documents` — document metadata (type, received date, patient/transfer link)
   - `GET /icd/{code}` — ICD-10 chapter and description for each diagnosis code
   - `GET /pharmacies` — pharmacy network directory
4. **Cross-reference** patient-level data across endpoints by `patient_id`.

### Using POST /query

The read-only SQL endpoint accepts a JSON body with a `query` field. Prefer it for:
- Filtering referral or transfer collections to a specific batch when the collection endpoint lacks a `?batch=` parameter
- Reconciling document-to-referral or document-to-transfer links
- Joining insurance IDs across patients to detect shared-insurance anomalies

Parameters beyond `query` are not documented; do not invent them.

### Document Freshness Rules

When checking document staleness, apply these freshness limits (observed from portal data; verify against actual portal records on each run):

| Document type | Staleness threshold |
|---------------|---------------------|
| hbsag | 365 days |
| hep_b_antibody_core | 365 days (or lifetime, per portal) |
| history_physical | 180 days |
| monthly_labs | 30 days |
| ppd_or_cxr | 365 days |

A document is **stale** if `current_date - received_date > freshness_limit_days`. Staleness limits may be embedded in portal document records — defer to portal values when present.

## Domain-Specific Patterns

### 1. Patient Access Verification (train_001 pattern)

**When the prompt mentions**: roster, primary care intake, access verification, insurance/prescription/pharmacy validation.

**Workflow**:
1. Read the roster file (`target_roster.json`) for `requested_service_date` and `service_line`.
2. For each patient in the roster, fetch `GET /patients/{patient_id}`.
3. From the patient record, extract insurance status, prescription benefit status, pharmacy assignment, and risk fields.
4. Cross-check the assigned pharmacy against `GET /pharmacies` to determine in-network / out-of-network.
5. Derive `blocked_reason_codes` from the union of any failing checks — see the **Blocker Codes** section below.
6. Build `cohort_summary` with counts by registration status, overall risk, and lifestyle risk.

**Risk derivation**: `lifestyle_risk` and `overall_risk` come from the patient record. If the portal provides them as structured fields, copy directly. If derived, use the portal's risk model (check for flags like smoking, BMI, prior utilization in chart data).

**Registration status logic**:
- `approved`: no blockers, all checks pass
- `hold`: one or more non-clinical blockers (coverage, pharmacy, contact, address)
- `clinical_review`: lifestyle_risk or overall_risk = `high`, or clinical-flag blockers
- `rejected`: coverage_expired + no alternatives, excluded service line, or explicit portal rejection

### 2. Referral Audit (train_002 pattern)

**When the prompt mentions**: referral batch audit, orthopedic/spine/joint referral, ICD coding review, scheduling readiness.

**Workflow**:
1. Fetch all referrals in the batch (`GET /referrals` filtered to batch).
2. For each referral, fetch its detail record, the linked patient record, and any associated documents.
3. For each ICD code on the referral, fetch `GET /icd/{code}` and compare the chapter against the referral's narrative service line.
4. Detect:
   - **ICD chapter mismatch**: ICD code chapter ≠ expected chapter for the referral's stated service line
   - **Narrative mismatch**: referral narrative text does not match the ICD description
   - **Laterality mismatch**: ICD code specifies a side (left/right/bilateral) that conflicts with the referral narrative
   - **Duplicates**: same patient, same procedure/body part, overlapping or identical dates → group together
   - **Shared insurance anomaly**: same insurance policy ID on referrals for different patients with different surnames or DOBs
   - **Missing records/imaging**: referral expects records/imaging that are absent from `/documents`
   - **Authorization blockers**: auth_status is `pending`, `denied`, or `not_submitted`
5. Assign `readiness_status` per referral:
   - `ready`: no blockers, no discrepancies, authorization approved
   - `blocked`: one or more hard blockers (auth_denied, missing imaging, missing records)
   - `under_review`: ICD or narrative discrepancies needing clinical review
   - `admin_followup`: duplicates, insurance anomalies, pending auth
6. Assign `priority_tier`:
   - `tier_1_immediate`: urgent + ready, or urgent + only admin-fixable blockers
   - `tier_2_short_term`: routine + ready or under_review
   - `tier_3_administrative`: admin-only issues, duplicates, insurance verification
   - `null`: for referrals that are already scheduled or fully resolved

**Duplicate resolution**: When referrals share the same patient and overlapping clinical intent, recommend `consolidate_to_primary` and designate the earliest-created or most-complete referral as primary. Use `keep_separate` when the referrals target different body parts or unrelated conditions.

### 3. Transfer Review (train_003 pattern)

**When the prompt mentions**: dialysis, transfer batch, packet completeness, document freshness/staleness, facility capacity, winter/Gulf Coast arrivals.

**Workflow**:
1. Fetch all transfers in the batch (`GET /transfers` filtered to batch).
2. For each transfer, fetch the linked patient record and any packet documents.
3. Check packet completeness against the required document set for dialysis intake:
   - Required: face_sheet, history_physical, physician_orders, insurance_proof, medication_list, allergy_list, vascular_access_report, monthly_labs, treatment_flowsheets, hbsag, hep_b_antibody_core, ppd_or_cxr, flu_vaccine, pneumonia_vaccine, transportation
4. Check document staleness against the freshness limits above.
5. Assess capacity: the transfer record carries a `requested_start` date. Determine open in-center hemodialysis chair count from portal facility/capacity data.
6. Derive `feasibility`:
   - `ready_on_requested_start`: packet complete, capacity available
   - `packet_not_ready_capacity_available`: packet incomplete but chairs open
   - `packet_not_ready_capacity_unavailable`: both packet and capacity issues
   - `capacity_unavailable`: packet complete but no chairs
7. Assign `final_intake_decision`:
   - `accept`: packet complete, capacity available, no clinical flags
   - `hold`: packet or capacity issue that is resolvable
   - `clinical_review`: clinical flags in chart, abnormal labs, high-risk patient
8. Set `next_contact_owner` and `next_contact_route` based on the blocking issue.

### 4. Chronic-Care Enrollment Panel (train_004 pattern)

**When the prompt mentions**: chronic-care, enrollment panel, program code (DMHTN, etc.), candidates, DM/HTN.

**Workflow**:
1. Fetch `GET /programs/{program_code}/candidates` — this returns the candidate list.
2. For each candidate, fetch `GET /patients/{patient_id}` and `GET /chart/{patient_id}`.
3. Determine `eligible` (boolean):
   - True: patient has active DM/HTN diagnosis, chart is active, consent is on file
   - False: wrong target condition, chart not active, consent declined/missing
4. Assign `enrollment_status`:
   - `enroll`: eligible, all chart artifacts present, consent obtained
   - `hold`: eligible but missing chart artifacts or consent
   - `reject`: ineligible (wrong condition, consent declined, chart inactive)
5. Populate `reason_codes` from the template's allowed set reflecting why the patient is at their status.
6. Set `follow_up_cadence`:
   - `weekly`: high-touch (recent hospitalization, low adherence, recent ED visit)
   - `biweekly`: CKD comorbidity
   - `monthly`: standard DM/HTN management
   - `deferred`: not enrolling now but may later
   - `none`: rejected
7. Determine `missing_chart_artifacts` by comparing expected chart sections against what `/chart/{patient_id}` returns.
8. Assign `outreach_channel` per patient preference from their record (phone, portal, sms, email, none).
9. Assign `initial_monitoring_package`:
   - `standard_dm_htn`: bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup
   - `high_touch_dm_htn`: standard components + consent_packet + chart_update_request (if needed), shorter first_checkin_days
   - `deferred`: not enrolling now
   - `not_applicable`: rejected

### 5. Referral-to-Chart Activation (train_005 pattern)

**When the prompt mentions**: pulmonary referral, chart activation, reconciliation, ready referrals, correspondence queue.

This combines elements of the referral audit (#2) with an additional chart-activation layer. After auditing referrals:

1. For each **ready** referral, determine what chart artifacts exist vs. are needed:
   - `create_chart`: no chart exists for the patient → create demographics, active_problems, medications, allergies, vitals, labs, consent
   - `update_chart`: chart exists but is incomplete → list only missing artifacts
   - `no_chart_action`: chart is complete and current
2. Build the `correspondence_queue` for referrals needing outreach:
   - `clinical_code_clarification`: ICD/narrative mismatches
   - `auth_records_request`: missing records or authorization issues
   - `duplicate_resolution`: duplicate groups needing consolidation
   - `appointment_hold_notice`: referral is blocked because an appointment was scheduled before clearance
3. Build `priority_order`: rank non-ready referrals highest-priority-first, assigning `tier_1_immediate` → `tier_2_short_term` → `tier_3_administrative`.

## Controlled Vocabulary Reference

These sets appear across multiple templates. Use **only** the values enumerated in the current task's `answer_template.json` — the lists below are a cross-task reference, not authoritative for any single task.

### Blocker / Reason Codes (variable by domain)

Patient-access blockers: `coverage_expired`, `coverage_pending`, `emergency_contact_missing`, `excluded_service_line`, `missing_address`, `pbm_invalid`, `pbm_missing`, `pbm_policy_mismatch`, `pharmacy_out_of_network`, `pharmacy_unknown`, `preferred_contact_unavailable`, `overall_risk_high`

Referral issue codes: `icd_chapter_mismatch`, `narrative_mismatch`, `laterality_mismatch`, `duplicate_referral`, `shared_insurance_anomaly`, `missing_records`, `missing_imaging`, `auth_blocker`, `already_scheduled`

Referral action codes: `request_corrected_icd`, `confirm_narrative`, `confirm_laterality`, `consolidate_duplicate`, `verify_insurance_id`, `request_records`, `request_imaging`, `resolve_authorization`, `review_existing_appointment`

Chart-activation blocker codes: `clinical_code_discrepancy`, `records_missing`, `imaging_missing`, `authorization_blocked`, `duplicate_review`, `scheduled_before_clearance`

Enrollment reason codes: `meets_dmhtn_criteria`, `recent_hospitalization_high_touch`, `low_adherence_high_touch`, `ckd_biweekly_monitoring`, `recent_ed_high_touch`, `consent_declined`, `consent_missing`, `chart_not_active`, `stale_active_problems`, `missing_recent_vitals`, `missing_recent_labs`, `missing_medication_list`, `wrong_target_condition`, `missing_active_dmhtn_diagnosis`

Dialysis transfer required documents: `allergy_list`, `face_sheet`, `flu_vaccine`, `hbsag`, `hep_b_antibody_core`, `history_physical`, `insurance_proof`, `medication_list`, `monthly_labs`, `physician_orders`, `pneumonia_vaccine`, `ppd_or_cxr`, `transportation`, `treatment_flowsheets`, `vascular_access_report`

### Readiness Status (referral)
`ready`, `blocked`, `under_review`, `admin_followup`

### Registration Status (patient access)
`approved`, `hold`, `clinical_review`, `rejected`

### Priority Tier
`tier_1_immediate`, `tier_2_short_term`, `tier_3_administrative`

### Risk Levels
`low`, `medium`, `high`

### Insurance / Pharmacy Status
Insurance: `valid`, `invalid`, `missing`
Pharmacy: `in_network`, `out_of_network`, `unknown`

### Intake Decision (transfers)
`accept`, `hold`, `clinical_review`

### Enrollment Status (chronic care)
`enroll`, `hold`, `reject`

## Output Formatting Rules

1. **Output JSON only** — no prose, no markdown fences, no commentary outside the JSON object.
2. **Ordered lists** obey the template: ascending by ID, alphabetical by code/name, or unordered-set semantics as specified.
3. **IDs are uppercase** — match the portal's casing exactly.
4. **Null vs. empty**: use `null` for optional fields explicitly typed as nullable; use `[]` for empty lists; omit a key only if the template marks it optional.
5. **Counts are integers** — never floats, never strings.
6. **Dates use `YYYY-MM-DD`** format.
7. **Empty lists in summaries**: if no referrals are in a category (e.g. no auth_blockers), return `[]` not `null`.
8. **Cohort/summary counts must sum correctly**: `total` must equal the sum of per-status counts, and per-status counts must equal the number of items with that status.

## Common Pitfalls

- **Not reading the answer template first**: Every task's template defines its exact vocabulary. Codes and keys differ across domains even when they sound similar.
- **Assuming the batch/roster ID from the prompt**: Verify through the portal that the named batch exists and returns records.
- **Client-side vs. server-side filtering**: If `GET /referrals` returns more than the target batch, use `POST /query` with `WHERE batch_id = '...'`. Do not silently process the wrong records.
- **Staleness math**: `current_date - received_date` in days, not months or years.
- **Duplicate detection scope**: Check for same patient + same body part/procedure + overlapping time window, not just same patient.
- **Shared insurance requires different patients**: Same insurance ID on the same patient's multiple referrals is normal; it's only anomalous across different patients.
- **Laterality from ICD codes**: ICD-10 laterality is encoded in the final character position; not all codes have laterality.
- **Consent is a chart artifact**: In chronic-care enrollment, consent status comes from the chart, not the patient record.

## Task-Type Quick Dispatch

| Prompt signal | Follow pattern | Primary endpoint |
|---------------|---------------|------------------|
| roster, primary care, access verification, insurance validation | §1 Patient Access | `/patients`, `/pharmacies` |
| referral batch audit, orthopedic/spine/joint, ICD coding, scheduling readiness | §2 Referral Audit | `/referrals`, `/patients`, `/documents`, `/icd/{code}`, `POST /query` |
| dialysis, transfer batch, packet completeness, facility capacity | §3 Transfer Review | `/transfers`, `/patients`, `/documents` |
| chronic-care, enrollment panel, program code, DM/HTN, candidates | §4 Enrollment Panel | `/programs/{code}/candidates`, `/patients`, `/chart/{id}` |
| pulmonary referral, chart activation, correspondence queue, ready referrals | §5 Chart Activation | `/referrals`, `/patients`, `/chart/{id}`, `/documents`, `/icd/{code}` |
