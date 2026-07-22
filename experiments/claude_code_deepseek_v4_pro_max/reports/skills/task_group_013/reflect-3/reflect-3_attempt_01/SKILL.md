# Cedar Ridge Intake Coordination Portal — Solver Skill

## Overview

This skill covers how to solve structured healthcare intake tasks against the Cedar Ridge Intake Coordination Portal. The portal exposes read-only REST endpoints for patients, referrals, transfers, documents, charts, programs, ICD codes, pharmacies, and a read-only SQL query interface.

## Core Workflow

### 1. Read the prompt and payloads first

- Open the task `prompt.txt` to identify the target batch/roster/program and the task type.
- Open `payloads/answer_template.json` to understand the **exact required JSON shape** before querying any data.
- The template defines required keys, allowed enum values, list ordering, and numeric precision. Deviating from these constraints produces wrong answers.

### 2. Discover and query the API

The portal runs at the environment base URL. A GET to `/` returns an HTML page listing the available endpoints. Key endpoints:

| Endpoint | Use |
|---|---|
| `GET /patients` | List/search patients |
| `GET /patients/{id}` | Full patient detail (demographics, coverage, PBM, pharmacies, lifestyle, clinical history, chart artifacts, documents, referrals, transfers, rosters, program candidates) |
| `GET /referrals?batch_id=` | List referrals in a batch |
| `GET /referrals/{id}` | Referral detail with ICD metadata and linked patient |
| `GET /transfers?batch_id=` | List transfers in a batch |
| `GET /transfers/{id}` | Transfer detail with capacity data and packet documents |
| `GET /programs/{code}/candidates` | Program candidate list |
| `GET /chart/{patient_id}` | Chart artifacts |
| `GET /icd/{code}` | ICD-10 metadata (chapter, service family, laterality, description) |
| `GET /documents` | Document index |
| `POST /query` | Read-only SQL (JSON body: `{"sql": "SELECT ..."}`) |

**Always fetch the full detail endpoint** (`/patients/{id}`, `/referrals/{id}`, `/transfers/{id}`) rather than relying on list results — the detail response includes nested coverage, PBM, pharmacy, lifestyle, clinical history, documents, and capacity data that the list endpoints omit.

### 3. Cross-reference with SQL when needed

The `POST /query` endpoint accepts read-only SELECT statements. Use it to reconcile records or aggregate across entities. Example: `SELECT * FROM intake_rosters WHERE roster_id = '...' ORDER BY patient_id`.

### 4. Derive fields from data, not assumptions

Every field in the answer must trace back to specific data values from the API. Common derivation patterns:

#### Insurance status
- **valid**: coverage `status` is `"active"` AND the relevant `service_line` appears in the coverage's `service_lines` field.
- **invalid**: coverage exists but is `"expired"` or does not cover the required service line.
- **missing**: no coverage record.

#### Prescription/PBM status
- **valid**: PBM `active` = 1 AND `status` = `"approved"` AND `policy_number` matches the coverage policy.
- **invalid**: PBM exists but is inactive, rejected, pending, or has a policy mismatch.
- **missing**: no PBM record.

#### Pharmacy network
- Use the preferred pharmacy's `network_status` (`"in_network"`, `"out_of_network"`). If no pharmacy is listed, use `"unknown"`.

#### Lifestyle and overall risk
Consider smoking status, alcohol use, exercise frequency, and sleep hours. Also factor in chronic conditions and risk flags from `clinical_history` for overall risk. Use only the enum values from the template.

#### Registration/readiness/decision status
Derive from the presence and combination of blockers:
- No issues → `"ready"` / `"approved"` / `"accept"`
- Administrative issues → `"hold"` / `"admin_followup"`
- Clinical uncertainty → `"clinical_review"` / `"under_review"`
- Unfixable issues → `"rejected"` / `"blocked"`

#### Reason codes and blocker codes
Only use codes from the template's allowed_values lists. Match each concrete data finding to the most specific code available.

#### Cohort summaries
Derive counts from the patient-level results. All counts must be integers that sum correctly to the total.

### 5. Respect ordering

- Patient/referral/transfer lists: **ascending by ID** (lexical sort of the identifier string).
- Document and reason-code arrays: **alphabetical order** (when template says "alphabetical").
- Unordered sets: any order is acceptable; the template will note this.

### 6. Validate before submitting

- Every required top-level key is present.
- Every enum value is from the allowed list.
- Every patient/referral/transfer in the batch appears in the results, sorted correctly.
- Counts in the summary match the patient-level data exactly.

## Task-Type Patterns

### Patient Access Verification (roster-based)
- Query the roster via SQL or the patients endpoint (roster data is nested in patient detail).
- For each patient: check insurance→service line coverage, PBM validity, pharmacy network, lifestyle risk, clinical risk, then derive registration status and blocker codes.
- Summarize by registration status, overall risk, and lifestyle risk.

### Referral Readiness Audit (batch-based)
- Fetch all referrals for the batch, then fetch each referral's detail for ICD metadata.
- For each referral: check ICD chapter vs service family, records received, imaging received, authorization status, duplicate flags, shared insurance IDs.
- Identify ICD discrepancies (chapter mismatch, narrative mismatch, laterality mismatch).
- Group duplicates by shared patient+ICD+insurance. Identify shared insurance anomalies by shared insurance_id across different patients.
- List which referrals are ready to schedule (no blockers, records+imaging received, auth approved).
- Build action plan with priority tiers: urgent→tier_1, routine with blockers→tier_2 or tier_3.

### Transfer/Dialysis Review (batch-based)
- Fetch all transfers, then each transfer's detail for documents and capacity.
- For each transfer: compare present documents against the required set. Check finalized status — non-finalized (draft) documents count as missing.
- Check document freshness: compare received_date against requested_start_date using the doc-type-specific freshness limit (e.g., monthly_labs: 30 days, others: 365 days).
- Capacity: sum open chairs across all locations for the requested start date. If date not in capacity data, capacity is unavailable.
- Derive feasibility from the combination of packet completeness and capacity availability.
- Final decision: accept if complete+capacity, hold if incomplete, clinical_review if complete but no capacity.

### Program Enrollment Panel
- Fetch the candidate list from `/programs/{code}/candidates`.
- For each candidate: fetch patient detail for clinical history and chart artifacts.
- Eligibility: target_condition matches the program's condition AND chart is active.
- Enrollment: enroll if eligible+consent signed, hold if consent missing, reject if consent declined or wrong target condition.
- Follow-up cadence: weekly (high-touch triggers: low adherence <50, recent hospitalization, recent ED), biweekly (moderate, CKD), monthly (stable), deferred/none (not enrolling).
- Monitoring package: high_touch_dm_htn for high-risk enrollees, standard_dm_htn for stable enrollees, deferred for hold, not_applicable for reject.
- Missing chart artifacts: list which of [chart_record, active_problems, vitals, labs, medications, consent] are absent from the chart.

### Pulmonary/Service-Line Referral Reconciliation
- Fetch all referrals in the batch, each with ICD metadata.
- Clinical code discrepancy: ICD service_family does not match the referral's service_line (e.g., cardiology ICD for a pulmonary referral).
- Duplicate handling: referrals with `notes` containing "possible duplicate" → check for same patient+ICD+insurance combinations. If no match found, add to cleared_duplicate_review_referrals.
- For each ready referral: check chart artifacts to determine if chart needs creation, update, or no action. List missing artifacts alphabetically.
- Correspondence queue: one entry per non-ready referral, with the appropriate template_type and reason codes.
- Priority order: rank non-ready referrals highest-priority-first (urgent+tier_1 before routine+tier_2 before admin+tier_3).

## Common Pitfalls

- **Missing nested data**: The list endpoints omit coverage, PBM, pharmacy, documents, and capacity. Always call the detail endpoint.
- **Transportation document**: The transportation field on a transfer object IS the transportation document — null means missing, any value means present.
- **Draft documents**: Documents with `finalized: 0` count as missing from the packet.
- **Capacity dates**: Capacity data may not include every date. If the requested date is absent, open_chairs_total is 0 and capacity is unavailable.
- **Insurance vs. payer**: The `payer` field on a referral is the referring entity, not the patient's insurance. Use `insurance_id` to cross-reference.
- **ICD chapter mismatch**: Compare the ICD code's `service_family` against the referral's `service_line`, not the chapter letter against an expected range.
- **Duplicate detection**: Same patient + same ICD + same insurance across different referral IDs = duplicate group. Same insurance_id across different patients = shared insurance anomaly.
