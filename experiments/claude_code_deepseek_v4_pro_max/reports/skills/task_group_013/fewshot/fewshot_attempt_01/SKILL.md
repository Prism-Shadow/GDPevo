# Cedar Ridge Intake Coordination — Reusable Skill

## Overview

This skill handles healthcare intake coordination tasks against the Cedar Ridge Intake Coordination Portal, a REST API serving patient, referral, transfer, document, chart, pharmacy, ICD, and program-candidate data. Tasks arrive as a natural-language prompt paired with a JSON answer template that specifies the exact output shape.

## When to use this skill

Invoke this skill whenever a task:
- Mentions the Cedar Ridge Intake Coordination Portal or a `<TASK_ENV_BASE_URL>` placeholder.
- Requires building a structured JSON response from an answer template.
- Involves healthcare intake workflows: patient access verification, referral auditing, transfer review, chronic-care enrollment panels, or chart-activation reconciliation.

## Step 1 — Discover the base URL

The environment base URL is provided through one of two channels:

1. **`environment_access.md`** in the working directory — contains `base_url:`, `credentials:`, `notes:`, and `allowed_endpoints:`. This file overrides any other source. If it exists, use its `base_url` as the root for all API calls.
2. **The task prompt** — contains a `<TASK_ENV_BASE_URL>` placeholder. Substitute the base URL from `environment_access.md` for this placeholder.

If neither source provides a reachable base URL, report the gap and stop.

## Step 2 — Read the task prompt and answer template

Every task has two required inputs:

- **`input/prompt.txt`** — natural-language instructions naming the batch, roster, or program identifier, the goal, and the template path.
- **`input/payloads/answer_template.json`** — the required JSON output shape. It defines:
  - Required top-level keys with types, allowed values, and enumerations.
  - List ordering rules (e.g., "ascending by patient_id", "ascending referral_id", "alphabetical by code").
  - Set semantics for reason-code and blocker-code arrays ("treat as unordered set").
  - Cohort/summary aggregation rules (which buckets to count, integer precision).

Additional payloads (e.g., `target_roster.json`) may provide batch-level identifiers or parameter overrides. Read every file under `input/payloads/`.

## Step 3 — Identify the task type

Classify the task by the template's top-level keys and the prompt's language. The portal supports these intake workflows:

| Workflow | Template signature keys | Primary API endpoints |
|---|---|---|
| Patient access verification | `roster_id`, `patient_results`, `registration_status` | `/patients`, `/chart/{id}`, `/pharmacies` |
| Referral audit / readiness | `batch_id`, `referral_reviews`, `icd_discrepancies`, `duplicate_groups`, `ready_to_schedule` | `/referrals`, `/patients`, `/icd/{code}`, `/documents`, `POST /query` |
| Transfer review | `batch_id`, `patients` (with `transfer_id`), `packet_completeness_status`, `requested_start`, `cohort_summary` | `/transfers`, `/patients`, `/documents` |
| Program enrollment panel | `program_code`, `patients` (with `eligible`, `enrollment_status`), `summary` | `/programs/{code}/candidates`, `/patients`, `/chart/{id}` |
| Referral-to-chart activation | `batch_id`, `readiness_by_referral`, `ready_referral_chart_needs`, `correspondence_queue`, `priority_order` | `/referrals`, `/patients`, `/chart/{id}`, `/documents`, `/icd/{code}` |

## Step 4 — Gather data from the API

Use the endpoints listed in `environment_access.md`. Fetch data in parallel where dependencies allow.

### Endpoint reference

See `api_reference.md` for the full schema of every endpoint. Key endpoints:

- `GET /` — portal health check.
- `GET /patients` — list all patients; `GET /patients/{patient_id}` — single patient (insurance, demographics, risk scores, contact preferences).
- `GET /referrals` — list all referrals; `GET /referrals/{referral_id}` — single referral (ICD codes, authorization status, document flags, scheduling state).
- `GET /transfers` — list all transfers; `GET /transfers/{transfer_id}` — single transfer (packet documents with receipt dates, requested start date, facility).
- `GET /documents` — document metadata indexed by patient or referral (type, received date, status).
- `GET /chart/{patient_id}` — active chart record (problems, vitals, labs, medications, allergies, consent status, chart active/inactive flag).
- `GET /programs/{program_code}/candidates` — list of patient IDs currently returned for a program code.
- `GET /icd/{code}` — ICD-10 metadata (chapter, description, laterality).
- `GET /pharmacies` — pharmacy network directory.
- `POST /query` — read-only SQL endpoint. Send `{"sql": "<query>"}`. Use for batch reconciliation when the REST endpoints do not directly join related entities (e.g., cross-referencing referrals against patients, documents, and ICD codes in one pass).

### Data-gathering strategy by task type

1. **Access verification**: Fetch the roster's patients (`/patients/{id}` for each), their charts (`/chart/{id}`), and the pharmacy list (`/pharmacies`). Also check for a roster record at the portal (the prompt may direct you to a roster endpoint or the roster data may be embedded in a payload file).

2. **Referral audit / readiness**: Fetch `/referrals` to get the batch. For each referral, cross-reference `/patients/{id}`, `/icd/{code}` for each ICD on the referral, and `/documents` filtered to the referral. Use `POST /query` for joins that the REST endpoints don't natively support — e.g., finding all referrals that share an insurance ID across different patients, or bulk-joining referral-document status.

3. **Transfer review**: Fetch `/transfers` for the batch, `/patients/{id}` for each transfer's patient, and `/documents` for packet documents. Compare document receipt dates against freshness limits.

4. **Program enrollment**: Fetch `/programs/{code}/candidates` to get the candidate list. For each candidate, fetch `/patients/{id}` and `/chart/{id}`. Check for active DM/HTN diagnosis, consent status, recent vitals/labs, and chart completeness.

5. **Chart activation**: Fetch `/referrals` for the batch. For each referral, cross-reference `/patients/{id}`, `/chart/{id}`, `/documents`, and `/icd/{code}`. Identify what chart artifacts exist vs. are missing.

## Step 5 — Cross-reference and apply business rules

See `business_rules.md` for the reusable decision tables. The general pattern is:

1. **Join entities**: Match patients to referrals/transfers/programs by patient_id. Match documents to referrals/transfers by referral_id or transfer_id. Match ICD codes to referrals by the codes listed on the referral.

2. **Evaluate statuses**: For each entity, compare observed state against required state. The template's `allowed_values` enumerations define the controlled vocabulary.

3. **Accumulate reason codes**: When a check fails, add the corresponding reason code. Reason-code arrays are unordered sets — no duplicates, order not meaningful.

4. **Compute risk and priority**: Aggregate individual findings into overall risk levels and priority tiers. The templates define the tiers (e.g., `tier_1_immediate`, `tier_2_short_term`, `tier_3_administrative`).

5. **Determine final dispositions**: Map the accumulated findings to the final status (approved/hold/clinical_review/rejected; ready/blocked/under_review/admin_followup; accept/hold/clinical_review; enroll/hold/reject).

## Step 6 — Build the JSON response

1. Start from the template structure — respect every required key, allowed value, and ordering rule.
2. Populate patient/referral/transfer lists in the specified sort order.
3. Reason-code and blocker-code arrays must be deduplicated and treated as unordered sets.
4. Summary/count objects must use integer values and cover every bucket key listed in the template.
5. Use `null` only where the template explicitly allows it.
6. Use uppercase for all identifiers exactly as the portal returns them.
7. Do not include prose, explanations, or extra keys outside the template.

## Step 7 — Validate before returning

Before delivering the answer:
- Every required top-level key from the template is present.
- Every list is sorted as the template specifies.
- Every enum value is from the template's `allowed_values`.
- All counts in `cohort_summary` / `summary` sum consistently with the patient/referral/transfer lists.
- No task-specific answer values from training data have leaked in (this skill is reusable, not a cheat sheet).

## Supporting files

- `api_reference.md` — full endpoint reference with response shapes.
- `business_rules.md` — reusable decision tables for status determination, risk scoring, document freshness, and disposition mapping.
