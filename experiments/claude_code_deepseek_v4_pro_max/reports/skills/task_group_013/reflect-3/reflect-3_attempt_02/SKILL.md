# Cedar Ridge Intake Coordination Portal — Skill

## Overview

This skill covers intake coordination tasks for the Cedar Ridge healthcare system. The portal exposes patient, referral, transfer, chart, program, and clinical data through REST endpoints and a read-only SQL interface. Every task follows a consistent pattern: gather data from the portal, cross-reference entities, apply decision rules derived from the answer template's controlled vocabularies, and produce a structured JSON response with patient-level detail and cohort-level summary counts.

## Portal Data Model

All data lives in a SQLite-backed system. Use the read-only `POST /query` endpoint with standard SQL to fetch data efficiently across entities. The GET endpoints return joined views (e.g., `/patients/{id}` returns patient demographics, coverage, PBM, pharmacy assignments, chart artifacts, and rosters in one call). Prefer SQL for bulk cross-entity queries; use GET endpoints to verify single-entity views or when the join logic is unclear.

### Core Tables

| Table | Key columns | Notes |
|---|---|---|
| `patients` | patient_id, existing_chart, preferred_contact, phone, email, address, emergency_contact_present | Demographics and contact preferences |
| `coverage` | patient_id, payer, status, service_lines, effective_date, termination_date, network_status | Insurance coverage; status is `active`, `expired`, or `pending` |
| `pbm` | patient_id, active, status, formulary_status, policy_number, specialty_required | Prescription benefit manager; independently tracks active/approved state |
| `patient_pharmacy` | patient_id, pharmacy_id, preference_rank | Rank 1 is the primary pharmacy |
| `pharmacies` | pharmacy_id, network_status | `in_network` or `out_of_network` |
| `lifestyle` | patient_id, smoking_status, alcohol_use, exercise_frequency, sleep_hours | Risk factor inputs |
| `clinical_history` | patient_id, chronic_conditions, medication_count, allergy_count, recent_hospitalization, risk_flags | Comma-separated conditions; recent_hospitalization is 0/1 |
| `chart_artifacts` | patient_id, artifact_type, status, last_updated | `status` is `current` or `stale`; types include active_problems, vitals, labs, medications, consent, demographics, allergies, care_plan |
| `intake_rosters` | roster_id, patient_id, requested_service_date, service_line | New-patient intake rosters |
| `referrals` | referral_id, batch_id, patient_id, service_line, icd10_code, urgency, records_received, imaging_received, auth_status, appointment_scheduled, insurance_id, notes | Specialty referrals |
| `transfer_requests` | transfer_id, batch_id, patient_id, requested_start_date, modality, transportation | Dialysis and other transfers |
| `documents` | document_id, patient_id, referral_id, transfer_id, doc_type, finalized, received_date, status | 1 = finalized; doc_type identifies the document kind |
| `facility_capacity` | location_id, date, modality, open_chairs | Chair/day-level capacity |
| `icd_codes` | code, description, chapter, service_family, laterality | ICD-10 code metadata |
| `program_candidates` | program_code, patient_id, consent_status, adherence_score, target_condition, preferred_outreach | Chronic-care program candidate lists |

### Endpoint Summary

- `GET /patients`, `GET /patients/{id}` — patient details with nested coverage, PBM, pharmacies, chart artifacts, rosters, referrals, transfers
- `GET /referrals`, `GET /referrals/{id}` — referral records, filterable by batch_id and service_line
- `GET /transfers`, `GET /transfers/{id}` — transfer requests, filterable by batch_id
- `GET /documents` — document records keyed to referral_id or transfer_id
- `GET /chart/{patient_id}` — chart artifacts for a patient
- `GET /programs/{code}/candidates` — program candidate list with patient info
- `GET /icd/{code}` — single ICD-10 code metadata
- `GET /pharmacies` — pharmacy directory with network status
- `POST /query` — read-only SQL; `{"sql": "SELECT ..."}`; returns `columns`, `rows`, `row_count`

## Systematic Approach

### Phase 1 — Understand the Template

Read `input/payloads/answer_template.json` first. It defines:

- **Required top-level keys** and their expected constant values (e.g., `task_id`, `batch_id`, `program_code`)
- **Entity-level required keys** and their allowed enum values — these are your only valid output values
- **Ordering rules**: patient_id ascending, referral_id ascending, alphabetical by code, unordered sets
- **Summary count fields** and which dimensions they must cover
- **List shapes**: whether items are flat strings, objects, or nested structures

The template is the single source of truth for output structure. Every field you output must use an allowed value. If a value doesn't appear in the template's enum list, don't use it.

### Phase 2 — Identify the Target Entities

Extract the batch/roster/program identifier from the prompt (e.g., `NPI-JUN-01`, `ORTHO-JUN-01`, `DMHTN-2026A`). Query the relevant table for all rows matching that identifier. This gives you the complete entity list you must report on.

### Phase 3 — Gather Supporting Data

For each entity, gather cross-referenced data:

- **Patient tasks**: query `coverage`, `pbm`, `patient_pharmacy` + `pharmacies`, `lifestyle`, `clinical_history`, `chart_artifacts`, and the patient GET endpoint for the joined view
- **Referral tasks**: query `icd_codes` for each icd10_code, `documents` for each referral_id, `patients` for demographics, `chart_artifacts` for chart status
- **Transfer tasks**: query `documents` for each transfer_id, `facility_capacity` for the relevant date range and modality, `patients`
- **Program tasks**: query `program_candidates`, `chart_artifacts`, `clinical_history` for each candidate

Use SQL `IN (...)` clauses to fetch all relevant rows in one query rather than looping.

### Phase 4 — Apply Decision Rules

Derive classifications by applying rules consistently across all entities:

**Insurance status:**
- `valid`: coverage status is `active` AND the requested service_line appears in the coverage's `service_lines` field
- `invalid`: coverage exists but is expired, pending, or excludes the requested service line
- `missing`: no coverage record exists for the patient

**Prescription (PBM) status:**
- `valid`: PBM record exists, `active` = 1, `status` = `approved`, and `policy_number` matches the coverage policy
- `invalid`: PBM exists but is inactive, rejected, pending, has a policy mismatch, or the formulary is under review
- `missing`: no PBM record exists

**Pharmacy status:**
- Use the patient's rank-1 pharmacy. Check `pharmacies.network_status` for that pharmacy_id.
- `in_network` or `out_of_network`; use `unknown` when no pharmacy assignment or pharmacy record exists.

**Lifestyle risk:**
- Assess holistically from smoking_status (Current = highest risk), alcohol_use (Heavy = highest), exercise_frequency (None = highest), sleep_hours (< 6 = elevated).
- `high`: multiple high-risk factors present
- `medium`: one or two moderate concerns
- `low`: no significant risk factors

**Overall risk:**
- Combine lifestyle risk with administrative/clinical risk factors (out-of-network pharmacy, missing emergency contact, PBM issues, coverage problems, complex medication reconciliation).
- `high`: multiple serious issues across domains
- `medium`: some issues but manageable
- `low`: no significant concerns

**Readiness (referral tasks):**
- `ready`: all required elements present (records, imaging, authorization approved/not-required, no discrepancies)
- `blocked`: at least one hard blocker (denied auth, missing records, clinical code discrepancy)
- `under_review`: issues needing investigation but not hard-blocking (duplicate review, insurance anomaly)
- `admin_followup`: administrative items only (already scheduled, minor documentation)

**Enrollment eligibility (program tasks):**
- Patient must have the program's target condition in their chronic_conditions
- Consent must be `signed` (not declined or missing)
- Chart must be active (`existing_chart` = 1) with current artifacts
- Missing, stale, or declined items produce specific reason codes

**Transfer packet completeness:**
- Check each required document type for presence AND `finalized` = 1
- Check stale-document types against freshness limits using `received_date` vs the requested start date
- Freshness limits by type: monthly_labs = 30 days, hbsag = 90 days, history_physical/ppd_or_cxr/hep_b_antibody_core = 365 days

**Feasibility (transfer tasks):**
- Cross-reference `requested_start_date` against `facility_capacity.open_chairs` for the matching modality
- If no exact date match exists, capacity is unavailable for that date
- Combine packet completeness with capacity to determine feasibility

### Phase 5 — Build the Response

Assemble the JSON following the template exactly:

1. **Constant fields first**: task_id, batch_id, roster_id, program_code — use the exact value from the template
2. **Entity list**: ordered as specified (ascending patient_id, referral_id, or transfer_id)
3. **Reason/blocker codes**: treat as unordered sets; include every applicable code from the allowed list
4. **Summary counts**: derive from entity-level decisions, not independently. Every count must equal what the entity list shows. Double-check: sum of registration_status counts = total_patients, sum of readiness_status counts = total_referrals, etc.
5. **Nested structures**: ensure required keys are present even when empty (empty arrays `[]`, zero counts `0`)

### Cross-Reference Patterns

- **Duplicate detection**: same patient_id + same insurance_id across referrals = duplicate; same patient_id + same referring_physician = likely duplicate; notes field explicitly saying "duplicate" confirms it
- **Shared insurance anomalies**: different patient_ids sharing the same insurance_id, especially with different payers — flag as `verify_distinct_patient_policy_id`
- **ICD code discrepancy**: when `icd_codes.service_family` doesn't match the referral's `service_line`, flag as `clinical_code_discrepancy` or `icd_chapter_mismatch`
- **Chart status**: `existing_chart` = 0 means no active chart even if artifacts exist; stale artifacts (status = `stale`) count as missing for chart readiness purposes

### Summary Count Construction

Build every summary count from the entity-level data, not independently:

1. Iterate over the final entity list and increment counters
2. Verify: sum of all sub-counts equals the total
3. For cross-dimensional counts (e.g., urgency × readiness), generate the full cross-product with zeroes for empty cells
4. Order cross-product entries as specified (typically urgency then readiness_status)

### Common Pitfalls

- **Policy number matching**: PBM `policy_number` must match coverage `policy_number`. A PBM with a different policy (e.g., `PBM-MISMATCH-6` vs `POL05502`) is `pbm_policy_mismatch`.
- **Service line exclusion**: coverage can be `active` but not cover the needed service line. This is `excluded_service_line`, not `coverage_expired`.
- **Preferred contact unavailable**: when `preferred_contact` is "email" but email is null, or "sms"/"phone" but phone is null, flag as `preferred_contact_unavailable`.
- **Stale documents vs missing documents**: a document that exists but is not finalized (finalized=0, status=draft) is MISSING, not stale. A document that is finalized but past its freshness limit is STALE.
- **Already-scheduled referrals**: a referral with `appointment_scheduled` = 1 that also has blockers (denied auth, missing records) has `scheduled_before_clearance` — the appointment was made prematurely.
- **Generic diagnosis descriptions**: a `diagnosis_description` of "specialty consultation" for all referrals in a batch is a data artifact, not necessarily a narrative mismatch. Only flag narrative mismatches when the description clearly contradicts the ICD code.
- **Chart record vs chart artifacts**: `chart_record` refers to the absence of an active chart (`existing_chart` = 0). Individual artifact types (active_problems, vitals, labs, etc.) are separate missing items when the artifact is absent or stale.
