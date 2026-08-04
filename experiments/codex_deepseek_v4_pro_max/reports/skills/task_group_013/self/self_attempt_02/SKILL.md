---
name: cedar-ridge-intake
description: >
  Operate the Cedar Ridge Intake Coordination Portal to complete patient access
  verifications, referral readiness audits, transfer reviews, program enrollment
  panels, and referral-to-chart activation tasks. Distills reusable operating
  rules from five diverse intake-coordination workflows across primary care,
  orthopedics, dialysis, chronic care, and pulmonary service lines.
---

# Cedar Ridge Intake Coordination – Operating Rules

## Environment

- The portal root is always read from the environment variable
  `GDPEVO_ENV_BASE_URL`.  A placeholder such as `<TASK_ENV_BASE_URL>` or
  `<TASK_ENV_BASE_URL>/path` in a prompt must be expanded to
  `$GDPEVO_ENV_BASE_URL/path`.

## API Surface

### REST endpoints (read-only GET)

| Endpoint                               | Returns                           |
|----------------------------------------|-----------------------------------|
| `GET /`                                | API index / available endpoints   |
| `GET /patients`                        | Patient demographics & identity   |
| `GET /patients/{patient_id}`           | Single patient record             |
| `GET /referrals`                       | Referral batch rows               |
| `GET /referrals/{referral_id}`         | Single referral detail            |
| `GET /transfers`                       | Transfer batch rows               |
| `GET /transfers/{transfer_id}`         | Single transfer detail            |
| `GET /documents`                       | Document / packet metadata        |
| `GET /chart/{patient_id}`              | Patient chart artifacts           |
| `GET /programs/{program_code}/candidates` | Candidates for a program     |
| `GET /icd/{code}`                      | ICD code chapter & metadata       |
| `GET /pharmacies`                      | Pharmacy network directory        |

### Arbitrary SQL (read-only)

```
POST /query
Content-Type: application/json
{"sql": "<string>", "params": ["<value>", ...]}
```

Use the SQL endpoint to reconcile cross-entity records, join tables, or answer
questions that span multiple REST resources.  Start from
`SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name` to
discover the schema.

## Workflow

1. **Read the prompt** – Identify the task type (verification, audit, review,
   enrollment, activation), the target roster/batch/program identifier, and
   any special instructions.

2. **Read the answer template** – The file `input/payloads/answer_template.json`
   (or the one referenced in the prompt) is the **ground truth** for the
   output shape.  It defines every required key, ordering rule, allowed enum
   value, and numeric precision.  The output must pass validation against this
   shape.

3. **Read supporting payloads** – Some tasks include extra files such as a
   roster list or batch manifest.  Incorporate their data into the workflow.

4. **Explore the portal** – Use GET endpoints and `/query` to collect every
   entity row referenced by the task (patients, referrals, transfers,
   documents, chart artifacts, ICD codes, pharmacy entries, program
   candidates).  Always map identifiers exactly as the portal presents them
   (preserve casing).

5. **Apply business rules** – Derive statuses, risk levels, discrepancy flags,
   and decisions by evaluating the data against the controlled vocabularies in
   the answer template.  The template's enum values encode the business logic:
   if a value is listed it must be reachable under some condition.

6. **Produce a single JSON object** – No prose outside the JSON.  Follow every
   ordering rule (ascending by ID, alphabetical by code, unordered set for
   reason-code arrays).  Include every top-level key, every nested required
   key, and every summary count.

## JSON Output Conventions

- **Ordering** – Lists of identifiers (patient_id, referral_id, transfer_id)
  are ordered ascending unless the template says otherwise.  Reason-code and
  blocker-code arrays are treated as unordered sets; any stable order is
  acceptable, but `ascending alphabetical` is the safe default.

- **Casing** – Use uppercase IDs exactly as returned by the portal.  Enum
  values are lowercase snake_case unless the template shows a different style.

- **Nullable fields** – A field is nullable only when the template explicitly
  lists `null` in its allowed values.  Otherwise supply a concrete value.

- **Counts** – All summary counts must be non-negative integers.  Cross-check
  that cohort-level counts sum to the total and that sub-group counts are
  internally consistent.

- **task_id** – When the template requires a `task_id`, use the train task
  label exactly as given (e.g. `train_001`).  This is a metadata key, not
  business data.

- **as_of_date** – When the template has an `as_of_date` field, report the
  current date in `YYYY-MM-DD` format.

## Business-Domain Cheat Sheet

### Patient Access Verification

- Insurance status derives from coverage validity and expiration dates.
- Prescription benefit status derives from PBM (pharmacy benefit manager) data.
- Pharmacy network status derives from comparing the patient's preferred
  pharmacy against the network directory.
- Lifestyle risk and overall risk are clinical composite judgments informed by
  the patient record and chart.
- Registration status (`approved`, `hold`, `clinical_review`, `rejected`) is
  the final disposition after evaluating all checks.
- Blocked reason codes are applied when a specific check fails.  Multiple
  reasons can co-occur.

### Referral Readiness Audit

- ICD discrepancies include chapter mismatches (code belongs to wrong body
  system), narrative mismatches (free-text reason doesn't match the code), and
  laterality mismatches (side-of-body conflicts).
- Duplicate referrals share the same patient, procedure, and date window; the
  primary (earliest or most complete) should be kept.
- Shared insurance anomalies occur when different patients share the same
  insurance/policy ID — flag for verification.
- Readiness status: `ready` (all clear), `blocked` (missing records, imaging,
  or authorization), `under_review` (clinical-code issues), `admin_followup`
  (insurance or duplicate work).
- Priority tiers: `tier_1_immediate` (urgent clinical need or expiring auth),
  `tier_2_short_term` (routine follow-up), `tier_3_administrative` (clean-up).

### Transfer Review

- Packet completeness is determined by checking the required document checklist
  against uploaded documents.
- Staleness: certain documents (HBsAg, HEP B, H&P, monthly labs, PPD/CXR) have
  freshness windows; if `received_date + freshness_limit_days < today`, the
  document is stale.
- Capacity feasibility compares requested start date against open chair counts
  across all locations.
- Final decision (`accept`, `hold`, `clinical_review`) weighs packet
  completeness, staleness, and capacity together.

### Program Enrollment Panel

- Eligibility depends on: active chart, confirmed diagnosis for the target
  condition, recent vitals/labs/medications, and consent on file.
- Enrollment status: `enroll` (meets criteria, consent present), `hold`
  (missing data or consent), `reject` (wrong condition, declined consent, or
  inactive chart).
- Monitoring package: `standard_dm_htn` for routine enrollees,
  `high_touch_dm_htn` for patients with recent hospitalization, ED visits, or
  low adherence.
- Follow-up cadence matches monitoring intensity; `deferred` or `none` for
  non-enrolled patients.

### Referral-to-Chart Activation

- Chart action: `create_chart` when no chart exists for the patient,
  `update_chart` when a chart exists but key artifacts are stale or missing,
  `no_chart_action` when the chart is current.
- Correspondence templates map to the blocker reason: code discrepancies get
  `clinical_code_clarification`, missing records/imaging get
  `auth_records_request`, duplicates get `duplicate_resolution`, premature
  scheduling gets `appointment_hold_notice`.
- Priority order ranks non-ready referrals by urgency so the office knows what
  to work first.

## Common Pitfalls

- **Missing `task_id`** – Check whether the template requires it; if it does,
  include it.
- **Wrong ordering** – `ascending` means lexicographic for string IDs, numeric
  for integer ranks.  Double-check when IDs mix letters and digits (e.g.
  `R010` vs `R02` — natural sort, not pure lexicographic).
- **Count mismatches** – Every patient/transfer/referral in the input batch
  must appear in the output lists.  Summaries must reconcile exactly.
- **Stale data interpretation** – A document is stale only when it exists but
  is past its freshness window; a missing document is a separate concern.
- **Enum casing** – Use the exact strings from the template's `allowed_values`
  or `allowed` lists.  Do not invent synonyms or change case.
