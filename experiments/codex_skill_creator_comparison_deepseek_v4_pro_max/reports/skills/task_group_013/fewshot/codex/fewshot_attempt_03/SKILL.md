---
name: cedar-ridge-intake
description: Complete intake coordination workflows for the Cedar Ridge Intake Coordination Portal. Use when a task references the Cedar Ridge portal, a task environment base URL with /patients /referrals /transfers /documents /chart /programs /icd /pharmacies endpoints, or any Cedar Ridge intake batch (patient access verification, referral audit, dialysis transfer review, chronic-care enrollment panel, or referral-to-chart activation). Covers all five intake workflows with business rules, SQL schema, and API navigation.
---

# Cedar Ridge Intake Coordination

## Overview

The Cedar Ridge Intake Coordination Portal is a healthcare operations system for verifying patient access, auditing referrals, reviewing dialysis transfers, building chronic-care enrollment panels, and activating referral-to-chart workflows. It exposes both REST endpoints and a read-only SQL interface.

Every task follows the same pattern:
1. Identify the workflow from the prompt (batch ID, roster ID, program code).
2. Read the answer template (`input/payloads/answer_template.json`) for required output shape and controlled vocabularies.
3. Query the portal endpoints and/or SQL to gather all relevant records.
4. Apply the workflow's business rules to derive patient-level decisions.
5. Assemble the JSON exactly as the template specifies, using only controlled enum values.

## Portal Endpoints

| Endpoint | Use |
|---|---|
| `GET /` | Portal home page (HTML) |
| `GET /patients` | List/search patients |
| `GET /patients/{id}` | Single patient |
| `GET /referrals` | List referrals; filter by `batch_id` or `service_line` |
| `GET /referrals/{id}` | Single referral with patient, ICD, and linked documents |
| `GET /transfers` | List transfers; filter by `batch_id` |
| `GET /transfers/{id}` | Single transfer |
| `GET /documents` | List documents; filter by `patient_id`, `referral_id`, `transfer_id` |
| `GET /chart/{patient_id}` | Full chart: patient, clinical_history, chart_artifacts, meds_allergies, active_problems, recent_vitals_labs |
| `GET /programs/{code}/candidates` | Program candidate list with consent and outreach fields |
| `GET /icd/{code}` | ICD-10 code metadata: chapter, service_family, laterality, description |
| `GET /pharmacies` | Pharmacy list with network_status |
| `POST /query` | Read-only SQL (body: `{"sql": "..."}`) |

For REST filtering, use query parameters: `batch_id`, `service_line`, `q` (name/id search), `limit`.

## SQL Schema Quick Reference

See [references/data_model.md](references/data_model.md) for full column listings and join patterns.

Key tables: `patients`, `coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`, `intake_rosters`, `referrals`, `icd_codes`, `documents`, `transfer_requests`, `facility_capacity`, `program_candidates`, `chart_artifacts`, `clinical_history`.

## Workflow Selection

Read the reference for the matching workflow:

| Workflow | Trigger | Reference |
|---|---|---|
| New Patient Access Verification | `roster_id`, mention of patient access, insurance/PBM/pharmacy verification | [access_verification.md](references/access_verification.md) |
| Referral Readiness Audit | `batch_id` with referrals, ICD review, duplicates, blockers | [referral_audit.md](references/referral_audit.md) |
| Dialysis Transfer Review | `batch_id` with transfers, packet completeness, chair capacity | [transfer_review.md](references/transfer_review.md) |
| Chronic Care Enrollment Panel | `program_code`, candidates, enrollment disposition | [enrollment_panel.md](references/enrollment_panel.md) |
| Referral-to-Chart Activation | Combined chart + referral workflow, correspondence queues | [referral_to_chart.md](references/referral_to_chart.md) |

## Common Patterns

### Query by Batch/Roster

Use SQL for precise batch filtering:

```sql
SELECT * FROM referrals WHERE batch_id = 'BATCH-ID' ORDER BY referral_id
SELECT * FROM intake_rosters WHERE roster_id = 'ROSTER-ID' ORDER BY patient_id
SELECT * FROM transfer_requests WHERE batch_id = 'BATCH-ID' ORDER BY transfer_id
SELECT * FROM program_candidates WHERE program_code = 'PROGRAM' ORDER BY patient_id
```

### Cross-Reference Patient Data

When a workflow needs patient-level insurance, PBM, pharmacy, lifestyle, or chart data, join through the patient_id. Use SQL for multi-table fetches to minimize round-trips:

```sql
SELECT * FROM coverage WHERE patient_id IN (...)
SELECT * FROM pbm WHERE patient_id IN (...)
SELECT * FROM patient_pharmacy WHERE patient_id IN (...) AND preference_rank = 1
SELECT * FROM lifestyle WHERE patient_id IN (...)
```

### ICD Code Lookup

Always resolve ICD-10 codes through `GET /icd/{code}` or `icd_codes` table to get `chapter`, `service_family`, and `laterality`. The chapter determines expected service line for mismatch detection.

### Answer Assembly

Every answer must follow its template's exact shape: required keys, enum values, list ordering, and numeric precision. Do not introduce keys not listed in the template. Sort lists as the template specifies (usually ascending by ID). Treat reason-code and blocker-code arrays as unordered sets.
