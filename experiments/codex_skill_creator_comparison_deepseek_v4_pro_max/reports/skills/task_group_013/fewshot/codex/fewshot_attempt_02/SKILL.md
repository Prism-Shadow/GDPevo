---
name: cedar-ridge-intake
description: Navigate the Cedar Ridge Intake Coordination Portal API to process patient intake verification, referral audit, transfer review, program enrollment panels, and referral-to-chart activation. Use when working with Cedar Ridge intake tasks that involve the portal's REST API (patients, referrals, transfers, documents, charts, ICD codes, pharmacies, programs, and the read-only SQL endpoint).
---

# Cedar Ridge Intake Coordination

## Overview

The Cedar Ridge Intake Coordination Portal is a read-only REST API plus a SQL query endpoint. Five intake workflows recur across the system: new-patient access verification, referral readiness audit, dialysis transfer review, chronic-care program enrollment panels, and referral-to-chart activation.

## Quick Start

Replace `<TASK_ENV_BASE_URL>` with the actual environment base URL from the task prompt. All endpoints are read-only GET except the SQL endpoint, which uses `POST /query` with `{"sql": "..."}`.

```bash
# List all patients
curl -s "<TASK_ENV_BASE_URL>/patients"

# Get one patient (composite: demographics, coverage, PBM, pharmacy, lifestyle, documents, referrals, transfers, rosters, program candidates)
curl -s "<TASK_ENV_BASE_URL>/patients/<patient_id>"

# Get patient chart (chart_artifacts, active_problems, meds_allergies, clinical_history, recent_vitals_labs)
curl -s "<TASK_ENV_BASE_URL>/chart/<patient_id>"

# List referrals for a batch
curl -s "<TASK_ENV_BASE_URL>/referrals?batch_id=<batch_id>"

# Get a single referral
curl -s "<TASK_ENV_BASE_URL>/referrals/<referral_id>"

# List transfers for a batch
curl -s "<TASK_ENV_BASE_URL>/transfers?batch_id=<batch_id>"

# List all documents (or filter with query params)
curl -s "<TASK_ENV_BASE_URL>/documents"

# Get ICD metadata
curl -s "<TASK_ENV_BASE_URL>/icd/<code>"

# List pharmacies
curl -s "<TASK_ENV_BASE_URL>/pharmacies"

# Get program candidates
curl -s "<TASK_ENV_BASE_URL>/programs/<program_code>/candidates"

# Run a read-only SQL query
curl -s -X POST "<TASK_ENV_BASE_URL>/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM intake_rosters WHERE roster_id = ''NPI-JUN-01''"}'
```

## Workflow Decision Tree

| Task signature | Workflow |
|---|---|
| Rosters, patient insurance/PBM/pharmacy, registration_status, blocked_reason_codes | **Access Verification** — see [references/business_rules.md](references/business_rules.md#access-verification) |
| Referral batch, ICD codes, duplicates, insurance anomalies, authorization, records/imaging | **Referral Readiness Audit** — see [references/business_rules.md](references/business_rules.md#referral-readiness-audit) |
| Transfer batch, packet documents, freshness checks, chair capacity | **Transfer Review** — see [references/business_rules.md](references/business_rules.md#transfer-review) |
| Program candidates, chart records, eligibility, monitoring packages | **Enrollment Panel** — see [references/business_rules.md](references/business_rules.md#enrollment-panel) |
| Referral batch + chart needs, correspondence templates, chart activation | **Referral-to-Chart Activation** — see [references/business_rules.md](references/business_rules.md#referral-to-chart-activation) |

## General Patterns

### Fetching Patient Data

The `/patients/<patient_id>` endpoint returns a composite object: `patient`, `coverage[]`, `pbm[]`, `pharmacies[]`, `lifestyle`, `clinical_history`, `chart_artifacts[]`, `documents[]`, `referrals[]`, `transfers[]`, `rosters[]`, and `program_candidates[]`. Use this single call first.

For chart-specific data (active_problems, allergies, vitals, labs) use `/chart/<patient_id>`.

### SQL Endpoint

The `POST /query` endpoint supports read-only SELECT statements. Use it to:
- Fetch intake roster data: `SELECT * FROM intake_rosters WHERE roster_id = '...'`
- Cross-check referral or patient data when batch endpoints are insufficient
- Verify aggregate counts

Always quote string literals carefully in curl (escape single quotes with `'\''`).

### Answer Template

Each task provides an `answer_template.json` defining the exact output shape, required keys, allowed enum values, and ordering constraints. Read it before starting and build the response to match its schema exactly. Lists named with `ordering` must be sorted as specified (typically ascending by ID). Lists of codes treated as "unordered set" should still be alphabetically sorted for determinism.

### API Reference

Complete endpoint documentation, response shapes, and field definitions are in [references/api_reference.md](references/api_reference.md).

### Business Rules

Detailed decision rules for each workflow (insurance evaluation, ICD discrepancy detection, stale-document checks, eligibility logic, chart-activation rules) are in [references/business_rules.md](references/business_rules.md).

## Data Integrity Notes

- When a patient has no records for a given resource (e.g., no PBM, no pharmacy, no chart), the corresponding array is empty. Treat empty arrays the same as missing data for status determination.
- Document `status` can be `"draft"` or `"final"`. Only final documents count as received.
- Referral `notes` containing `"possible duplicate"` or `"duplicate faxed by second practice"` are signals for duplicate detection.
- ICD `service_family` should match referral `service_line`. Mismatch indicates an ICD chapter discrepancy.
- Coverage `service_lines` is a comma-separated string (e.g., `"primary_care,cardiology"`). Split on comma for individual check.
- All patient IDs in the portal use uppercase `P` prefix (e.g., `P001`). Referral IDs use `REF` prefix. Transfer IDs use `TR` prefix.

## Response Construction

1. Read the prompt and `answer_template.json` to understand the required output shape and controlled values.
2. Fetch all relevant portal data for every target patient/referral/transfer/candidate.
3. Apply business rules from [references/business_rules.md](references/business_rules.md) to produce the per-entity determinations.
4. Compute cohort summary counts from the individual results.
5. Validate that every required key is present and every value is from the allowed enum set.
6. Output a single JSON object with no prose outside the JSON.
