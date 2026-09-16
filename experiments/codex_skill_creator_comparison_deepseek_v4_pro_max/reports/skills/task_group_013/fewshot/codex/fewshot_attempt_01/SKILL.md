---
name: cedar-ridge-intake
description: Complete Cedar Ridge Intake Coordination tasks using the shared read-only REST API and SQL endpoint. Use when the task involves patient access verification, referral readiness audits, dialysis transfer reviews, chronic-care program enrollment panels, or referral-to-chart activation at Cedar Ridge. Covers insurance and PBM validation, ICD chapter and narrative matching, duplicate detection, shared insurance anomaly resolution, document packet completeness and staleness checks, capacity assessment, program eligibility determination, and chart artifact activation.
---

# Cedar Ridge Intake Coordination

## Overview

The Cedar Ridge Intake Coordination Portal exposes a read-only REST API and a `POST /query` SQL endpoint. Every task supplies a base URL placeholder like `<TASK_ENV_BASE_URL>`. Replace it with the actual base URL provided in the task prompt and use it for every request.

All endpoints return JSON. The `/chart/{patient_id}` endpoint bundles the richest dataset — use it as the primary source for patient-level decisions.

## Endpoint Quick Reference

| Endpoint | Purpose | Query Params |
|---|---|---|
| `GET /patients` | Patient demographics | `?q=`, `?limit=` |
| `GET /patients/{id}` | Single patient profile | — |
| `GET /referrals` | Referral records | `?batch_id=`, `?service_line=`, `?limit=` |
| `GET /referrals/{id}` | Single referral | — |
| `GET /transfers` | Transfer records | `?batch_id=`, `?limit=` |
| `GET /transfers/{id}` | Single transfer | — |
| `GET /documents` | Document inventory | varies |
| `GET /chart/{patient_id}` | Complete chart | — |
| `GET /programs/{code}/candidates` | Program candidates | — |
| `GET /icd/{code}` | ICD-10 metadata | — |
| `GET /pharmacies` | Pharmacy directory | — |
| `POST /query` | Read-only SQL | body `{"sql": "..."}` |

Full field-level schemas for every major endpoint response shape are in [references/api_reference.md](references/api_reference.md).

## SQL Queries

Use `POST /query` with `{"sql": "SELECT ..."}` for batch-level filtering and joins. The response shape is `{"columns": [...], "rows": [...], "row_count": N, "truncated": false}`.

```sql
-- Fetch all referrals for a batch
SELECT * FROM referrals WHERE batch_id = '<BATCH_ID>' ORDER BY referral_id

-- Fetch all transfers for a batch
SELECT * FROM transfers WHERE batch_id = '<BATCH_ID>' ORDER BY transfer_id

-- Fetch roster records
SELECT * FROM intake_rosters WHERE roster_id = '<ROSTER_ID>' ORDER BY patient_id

-- Count scheduled transfers by date and chair window
SELECT requested_start_date, chair_window, days_requested, COUNT(*) AS scheduled
FROM transfers WHERE requested_start_date = '2026-12-08'
GROUP BY requested_start_date, chair_window, days_requested
```

## General Workflow

Every task supplies an `answer_template.json` in `input/payloads/` that defines the exact output shape, key names, allowed values, and ordering rules. Read that template first. Produce one JSON object matching it exactly — no prose outside the JSON.

1. Read the prompt to identify the batch/roster/program identifier.
2. Read `answer_template.json` for the required output shape and controlled values.
3. Query the portal for the relevant records (referrals, transfers, patients, charts, candidates).
4. Cross-reference records: use `/chart/{patient_id}` to pull coverage, PBM, pharmacies, lifestyle, clinical history, chart artifacts, and related referrals/transfers/rosters. Use `/icd/{code}` to pull ICD chapter, description, laterality, and service_family.
5. Apply the business rules in [references/business_rules.md](references/business_rules.md) to determine each field.
6. Construct the JSON answer following the template ordering rules exactly.

## Task-Type Workflows

### Patient Access Verification (Roster Intake)

For new-patient roster intake tasks:

1. Read the roster from the task payload to get `roster_id` and the target patient list. Pull `requested_service_date` and `service_line` from the roster record via SQL or the roster payload.
2. For each target patient, fetch `GET /chart/{patient_id}`.
3. From `chart.coverage`: determine `insurance_status` (valid/invalid/missing). Check `status`, `termination_date`, `service_lines`, `network_status`.
4. From `chart.pbm`: determine `prescription_status` (valid/invalid/missing). Check `active` and `status`.
5. From `chart.pharmacies`: determine `pharmacy_status` (in_network/out_of_network/unknown). Check `network_status`.
6. From `chart.lifestyle`: determine `lifestyle_risk`. Evaluate smoking, alcohol, exercise, sleep.
7. From `chart.patient`: check `address`, `emergency_contact_present`, and `preferred_contact` availability.
8. Determine `overall_risk` and `registration_status`. Collect `blocked_reason_codes`.
9. Build `cohort_summary` with integer counts across all patients.

### Referral Readiness Audit

For batch referral audit tasks:

1. Fetch referrals for the target batch: `GET /referrals?batch_id=<BATCH>` or SQL.
2. For each referral, fetch `GET /icd/{code}` to get chapter and service_family.
3. Compare ICD chapter against the expected chapter for the referral's `service_line`. Flag chapter mismatches and narrative/reason mismatches.
4. Detect duplicates: group by `(patient_id, icd10_code)`. Referrals sharing both patient and ICD are duplicates. Referrals flagged "possible duplicate" in `notes` but differing in either field are reviewed and cleared.
5. Detect shared insurance anomalies: same `insurance_id` on different `patient_id` values.
6. Identify blockers: `records_received=0`, `imaging_received=0`, `auth_status=denied` or `pending`.
7. Flag already-scheduled referrals: `appointment_scheduled=1`.
8. Assign `readiness_status`, `priority_tier`, and build `action_plan`.
9. Build `icd_discrepancies`, `duplicate_groups`, `shared_insurance_anomalies`, `blocker_sets`, `ready_to_schedule`, and `summary`.

### Dialysis Transfer Review

For transfer batch review tasks:

1. Fetch transfers: `GET /transfers?batch_id=<BATCH>`.
2. For each transfer, fetch `GET /chart/{patient_id}` and `GET /documents` for the patient.
3. Check packet completeness against the required document list (see business rules). Identify `missing_required_documents`.
4. Check document staleness: compare `received_date` against `freshness_limit_days` for each time-sensitive document type.
5. Evaluate capacity for the requested start date using SQL aggregation on transfers.
6. Determine `feasibility`, `final_intake_decision`, `next_contact_owner`, and `next_contact_route`.
7. Build `cohort_summary`.

### Program Enrollment Panel

For chronic-care program enrollment tasks:

1. Fetch candidates: `GET /programs/{code}/candidates`.
2. For each candidate, fetch `GET /chart/{patient_id}`.
3. Evaluate eligibility: `target_condition` must match the program, `consent_status` must be `signed`.
4. Assess chart completeness: check `existing_chart`, `chart_artifacts`, artifact staleness.
5. Evaluate clinical triggers: `recent_hospitalization`, `chronic_conditions` (CKD), `adherence_score`.
6. Assign `eligible`, `enrollment_status`, `reason_codes`, `follow_up_cadence`, `missing_chart_artifacts`, `outreach_channel`, and `initial_monitoring_package`.
7. Build `summary` with integer counts.

### Referral-to-Chart Activation

For referral intake with chart activation requirements:

1. Fetch referrals for the target batch.
2. For each referral, fetch `GET /chart/{patient_id}` and `GET /icd/{code}`.
3. Determine `readiness_by_referral` with `readiness_status` and `blocker_codes`.
4. Identify `clinical_code_discrepancy_referrals`.
5. Build `blocker_sets` (authorization, records, imaging).
6. Handle duplicates: true duplicates form `duplicate_groups`; reviewed-and-cleared go in `cleared_duplicate_review_referrals`.
7. For ready referrals, determine `chart_action` and `artifacts_to_create` based on which chart artifacts are missing or stale.
8. Build `correspondence_queue` for non-ready referrals.
9. Build `priority_order` for non-ready referrals, highest priority first.

## Business Rules

Detailed rules for insurance validation, ICD chapter/service-family mapping, duplicate detection, shared insurance anomaly resolution, document completeness and staleness, capacity assessment, program eligibility criteria, follow-up cadence, monitoring packages, chart activation, correspondence templates, priority tiers, and the full reason-code catalog are in [references/business_rules.md](references/business_rules.md). Load that file whenever applying decision logic to specific patients or referrals.

## Output Construction

- Match the template's key names, ordering, and controlled values exactly.
- Treat reason-code and issue-code arrays as unordered sets, but list referral/patient arrays in the ascending order specified by the template.
- Use `null` only where the template explicitly allows it.
- If a list would be empty, return `[]`, not null or omitted.
- Include every top-level key required by the template, even if empty.
- Counts in the summary must be exact integers reflecting all rows in the output.
