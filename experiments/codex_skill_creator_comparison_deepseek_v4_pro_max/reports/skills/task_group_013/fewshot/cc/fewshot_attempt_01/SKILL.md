---
name: cedar-ridge-intake
description: Use this skill whenever the user needs to work with the Cedar Ridge Intake Coordination Portal — a healthcare-intake REST API and read-only SQL endpoint covering patient registration verification, referral audits, dialysis transfer review, chronic-care enrollment panels, and pulmonary referral-to-chart activation. Trigger on references to Cedar Ridge, intake coordination, patient rosters, referral batches (ORTHO, PULM, etc.), dialysis transfers, chronic-care programs (DMHTN), or any task that mentions the Cedar Ridge portal, intake coordination, clinical intake auditing, or reconciling healthcare referral/transfer/program data against a live API.
---

# Cedar Ridge Intake Coordination Portal

This skill teaches you how to use the shared Cedar Ridge Intake Coordination Portal to complete healthcare intake operations: new-patient access verification, referral audits, dialysis transfer reviews, chronic-care enrollment panels, and pulmonary referral-to-chart activation.

## Portal Overview

The portal is a read-only REST API with a companion SQL endpoint running at a base URL provided in the task prompt (typically `<TASK_ENV_BASE_URL>`). All data is pre-populated; you never write back.

**REST endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Portal home (HTML landing page) |
| GET | `/patients` | List / search patients (query params: `q`, `limit`) |
| GET | `/patients/{patient_id}` | Single patient by ID |
| GET | `/referrals` | List / search referrals (query params: `batch_id`, `service_line`, `limit`) |
| GET | `/referrals/{referral_id}` | Single referral by ID |
| GET | `/transfers` | List / search transfers (query params: `batch_id`, `limit`) |
| GET | `/transfers/{transfer_id}` | Single transfer by ID |
| GET | `/documents` | List all documents (no filtering params documented; use SQL for targeted queries) |
| GET | `/chart/{patient_id}` | Full chart for a patient (patient info, artifacts, clinical history, vitals/labs, meds/allergies) |
| GET | `/programs/{program_code}/candidates` | Candidates for a chronic-care program |
| GET | `/icd/{code}` | ICD-10 code metadata (chapter, description, service_family, laterality) |
| GET | `/pharmacies` | List all pharmacies (network status, contact info) |
| POST | `/query` | Read-only SQL (body: `{"sql": "SELECT ..."}`) |

REST endpoints return JSON with the collection keyed by its type (e.g. `patients`, `referrals`, `transfers`, `documents`, `candidates`) and a `count` field.

The SQL endpoint answers `SELECT` queries against the full schema. It is the most reliable way to fetch joined or filtered data that spans multiple entities. Prefer it whenever a REST endpoint does not directly return what you need.

Before acting on any task, always read [references/schema.md](references/schema.md) to see the complete SQL table schemas and REST response shapes. Then read [references/rules.md](references/rules.md) for the business rules specific to your task type.

## Workflow

### 1. Identify the task type

Every task arrives with a batch/roster/program identifier and directs you to produce a JSON response following a template. Read the prompt and supplied `answer_template.json` carefully. The template dictates every key, ordering rule, and allowed value.

The five task families are:

- **New Patient Access Verification** — roster-driven insurance/PBM/pharmacy/lifestyle screening plus registration decision per patient.
- **Referral Audit** — batch referral review covering ICD discrepancies, duplicates, shared-insurance anomalies, missing records/imaging, authorization blockers, readiness, priority tiers, and action plans.
- **Dialysis Transfer Review** — seasonal transfer packet review with document completeness, staleness freshness checks, chair-capacity feasibility, intake decisions, and next-contact routing.
- **Chronic-Care Enrollment Panel** — program-candidate eligibility screening with chart-artifact audit, enrollment disposition, outreach planning, and monitoring-package assignment.
- **Pulmonary Referral-to-Chart Activation** — referral reconciliation with chart-activation readiness, correspondence queue, and priority ordering.

### 2. Pull all relevant data

For any task, gather data in parallel where possible:

- Query the exact batch/roster/program via the REST endpoint that carries it (e.g. `/referrals?batch_id=ORTHO-JUN-01`) to get the rows you must process.
- Use the SQL endpoint to join related tables (`coverage`, `pbm`, `patient_pharmacy`, `pharmacies`, `lifestyle`, `clinical_history`, `chart_artifacts`, `documents`, `facility_capacity`, `icd_codes`, `program_candidates`) for the patients or referrals in scope.
- Fetch individual patient charts (`/chart/{patient_id}`) only when you need full chart details (program enrollment, chart-activation tasks) — the SQL tables often suffice for coverage/PBM/pharmacy/lifestyle queries.
- Fetch ICD metadata (`/icd/{code}`) for every distinct ICD-10 code in the batch to resolve chapter, service_family, and laterality.

Always cap REST list endpoints with a high enough `limit` to retrieve all records for the batch. Use SQL `WHERE ... IN (...)` clauses to fetch exactly the records you need.

### 3. Apply business rules

Use [references/rules.md](references/rules.md) to make decisions. The rules are ordered by task type. Work patient-by-patient or referral-by-referral, applying each rule systematically. Do not skip the cohort summary at the end — it must reconcile exactly with the per-row decisions you made.

### 4. Produce the JSON answer

Build the JSON object strictly matching the template shape, ordering, and allowed values from `answer_template.json`. Important conventions across all templates:

- **Patient/referral/transfer lists are always sorted ascending by their ID.**
- **Code arrays (blocked_reason_codes, issue_codes, reason_codes, missing_chart_artifacts, components) are unordered sets — do not assign meaning to element order.**
- **Use only controlled-enum values from the template for every enum field.**
- **All integer counts in cohort summaries must sum correctly.**
- **Output only the JSON object — no prose, no markdown fences.**

### 5. Verify the summary

After building the patient/referral/transfer rows, recompute the cohort summary by counting each category from your own rows. If a count does not add up, recheck your decisions before adjusting the summary.

## Common Pitfalls

- **Not checking `service_lines` in coverage.** A coverage record may be `active` but still exclude the target service line — that patient's insurance is `invalid` for this intake, and `excluded_service_line` is a blocked reason.
- **Treating `finalized=0` documents as present.** A document with `finalized=0` (status `draft`) counts as missing for transfer packet completeness.
- **Ignoring staleness windows.** Stale documents are those whose `received_date` plus `freshness_limit_days` falls before the requested start date. This is separate from packet completeness.
- **Overlooking duplicate signals.** Duplicate referrals share the same `patient_id` and `icd10_code` and often carry notes like `"possible duplicate"` or an anomalous `referring_practice` name. Also check the `assigned_physician` field — the portal sometimes encodes duplicate hints there.
- **Skipping the chart-audit step for program enrollment.** Chart artifacts must be inspected via `/chart/{patient_id}` or the `chart_artifacts` SQL table to determine staleness, missing vitals/labs/meds, and consent status.
- **Misidentifying ICD discrepancy types.** There are two distinct discrepancies: `icd_chapter_mismatch` (the ICD chapter does not match the expected chapter for the service line) and `narrative_mismatch` / `clinical_reason_mismatch` (the referral reason text does not match the ICD description). Also check `laterality_mismatch` when the ICD code carries laterality that contradicts the referral narrative.
- **Capacity across locations.** Facility capacity is summed across all Cedar Ridge locations (`CRIC-MAIN`, `CRIC-NORTH`) for a given date. The `open_chairs` field is per-location, per-date.
- **Preferred-contact unavailability.** When a patient's `preferred_contact` is `email` but their `email` is null, or `phone`/`sms` but `phone` is null, the preferred contact is unavailable — a blocking condition.
