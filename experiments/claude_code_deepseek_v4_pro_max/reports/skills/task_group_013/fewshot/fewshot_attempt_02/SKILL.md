# Cedar Ridge Intake Coordination Portal — Reusable Task Skill

## Overview

This skill completes a healthcare intake-coordination task by querying the Cedar Ridge Intake Coordination Portal REST API and producing a single JSON response that follows a provided answer template. The tasks span domains such as patient access verification, referral auditing, transfer review, enrollment paneling, and referral-to-chart activation, but all follow the same core workflow.

## When to Use

Invoke this skill whenever the task prompt references:
- The "Cedar Ridge Intake Coordination Portal" (or similar healthcare intake system)
- A `<TASK_ENV_BASE_URL>` placeholder that must be resolved to a real base URL
- An `input/payloads/answer_template.json` file that defines the required output shape
- A batch, roster, program code, or other grouping identifier whose data lives behind the portal

## Step 1 — Resolve the Environment

1. Read `environment_access.md` (or the file the prompt points to) for the real `base_url`.
2. Replace every occurrence of `<TASK_ENV_BASE_URL>` in the prompt and in any payload files with that `base_url`. Strip trailing slashes so all URLs are `{base_url}/endpoint`.
3. Note the list of `allowed_endpoints` — only these may be called. The standard set is:

   ```
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

4. All endpoints require no authentication (credentials: none).

## Step 2 — Read the Task Prompt

The prompt (usually `prompt.txt`) tells you:
- **Which business domain** the task belongs to (primary care intake, orthopedic referral audit, dialysis transfer review, chronic-care enrollment, pulmonary referral activation, etc.)
- **Which batch/roster/program identifier** to target (e.g., a roster ID, batch ID, program code)
- **Which answer template** to follow (always `input/payloads/answer_template.json`)
- **Any special instructions** (e.g., "use the roster record for the service date," "include only JSON in the final response")

## Step 3 — Read and Internalize the Answer Template

The answer template is a JSON Schema–like document that defines:

1. **Top-level required keys** and their types.
2. **Controlled vocabularies** — every enum field has an `allowed_values` list. You MUST only use values from these lists.
3. **Ordering rules** — lists are ordered by a stated key (usually `patient_id`, `referral_id`, `transfer_id`, or `group_id` ascending). Some lists are "unordered sets" where order does not matter.
4. **Constant / required values** — some fields have a fixed `required_value` that must appear verbatim in the output (e.g., `task_id` must equal a specific string, `batch_id` must match the batch).
5. **Nested object shapes** — the template defines required keys and allowed values for every nested object and list item.

**Critical rule**: Every value in your output that comes from a controlled vocabulary must be drawn from the template's `allowed_values`. Never invent a status, code, or label.

## Step 4 — Gather Data from the Portal

### 4a. Identify the Primary Entity Endpoint

Map the task domain to the primary collection endpoint:

| Task contains…                     | Start at…                                      |
|------------------------------------|------------------------------------------------|
| Patients, roster, insurance, PBM   | `GET /patients`, `GET /patients/{id}`          |
| Referrals, ICD codes, authorizations| `GET /referrals`, `GET /referrals/{id}`        |
| Transfers, packets, chair capacity | `GET /transfers`, `GET /transfers/{id}`        |
| Program candidates, enrollment     | `GET /programs/{code}/candidates`              |

### 4b. Fetch the Primary Collection

Call the collection endpoint (e.g., `GET /referrals`) to list all records. Filter to the target batch/roster/program using the identifier from the prompt. If the batch identifier is stored in a field on each record, filter client-side. If the API provides a query mechanism, use `POST /query` with an appropriate filter.

### 4c. Fetch Detail and Related Records

For each entity from the primary collection, fetch related detail:

- **Patients**: `GET /patients/{patient_id}` returns insurance, demographics, contact info.
- **Chart**: `GET /chart/{patient_id}` returns active problems, vitals, labs, medications, allergies, consent status.
- **Referrals**: `GET /referrals/{referral_id}` returns ICD codes, authorization status, documents, scheduling info.
- **Transfers**: `GET /transfers/{transfer_id}` returns packet documents, requested start dates, facility info.
- **Documents**: `GET /documents` (or document lists embedded in referrals/transfers) returns document types, received dates, and status.
- **ICD metadata**: `GET /icd/{code}` returns chapter, description, and laterality information for an ICD-10 code.
- **Pharmacies**: `GET /pharmacies` returns pharmacy network status for PBM verification.

### 4d. Cross-Reference Across Endpoints

Many determinations require joining data from multiple endpoints. Common cross-reference patterns:

- **Insurance ↔ Pharmacy**: A patient's insurance status (from `/patients/{id}`) combined with their pharmacy's network status (from `/pharmacies`) determines `pharmacy_status`.
- **Referral ICD ↔ ICD Metadata**: The ICD-10 code on a referral (from `/referrals/{id}`) checked against `/icd/{code}` reveals chapter mismatches.
- **Transfer Documents ↔ Freshness Rules**: Document received dates (from `/transfers/{id}` or `/documents`) compared against freshness-limit days determine staleness.
- **Program Candidates ↔ Chart Data**: A candidate's chart (from `/chart/{id}`) determines whether required artifacts are present and current.

## Step 5 — Apply Business Rules and Classify

For each entity in the batch, classify every status field using the template's allowed values. The business rules observed across training tasks include:

### Insurance & Pharmacy
- `insurance_status` is `valid` when the patient record shows active, in-date coverage; `invalid` when coverage is expired or excludes the service line; `missing` when no insurance record exists.
- `prescription_status` is `valid` when PBM data is present and policy-compatible; `invalid` when PBM data conflicts with the service; `missing` when no PBM record exists.
- `pharmacy_status` is `in_network` when the patient's preferred pharmacy appears in the network list; `out_of_network` when it does not; `unknown` when no pharmacy is recorded.

### Referral Readiness
- `ready` — no blockers; all required records, imaging, and authorizations present and valid.
- `blocked` — one or more hard blockers (missing records, missing imaging, authorization denied/pending).
- `under_review` — issues that need clinical or coding clarification (ICD discrepancies, duplicates, code mismatches).
- `admin_followup` — administrative issues (insurance anomalies, contact verification).

### Packet Completeness (Transfers)
- Compare the documents present in the transfer packet against the required document list.
- Missing required documents → `incomplete`.
- Check each document's received date against its freshness limit; if `today - received_date > freshness_limit_days`, mark it stale.

### Enrollment Eligibility
- `eligible: true` when the patient meets the program's target condition and has an active chart with the qualifying diagnosis.
- `eligible: false` when the patient has the wrong target condition, no qualifying diagnosis, or a chart that cannot be activated.
- `enrollment_status: enroll` — eligible with no blockers.
- `enrollment_status: hold` — eligible but missing chart artifacts or consent.
- `enrollment_status: reject` — ineligible, consent declined, or chart not active.

### Chart Activation
- `create_chart` — no chart record exists for the patient.
- `update_chart` — chart exists but is missing required artifacts.
- `no_chart_action` — chart is complete.

### Blocked Reason Codes and Issue Codes
Only use codes from the template's `allowed_values` for `blocked_reason_codes`, `issue_codes`, `reason_codes`, or `blocker_codes`. Assign codes based on the specific deficiency found, not an aggregate.

### Risk Classification
- `lifestyle_risk` is based on patient-level factors (smoking, BMI, etc.) found in the patient record.
- `overall_risk` aggregates clinical and administrative risk factors. When multiple high-risk indicators are present, lean toward `high`.

### Registration / Intake Decision
- `approved` — all checks pass, no blockers.
- `hold` — administrative issues only, resolvable without clinical review.
- `clinical_review` — clinical flags (high risk, PBM issues, stale documents) require clinician judgment.
- `rejected` — hard blockers (expired coverage, excluded service line, multiple missing critical items).

## Step 6 — Assemble the Output JSON

1. Start from the answer template's top-level structure.
2. Fill in constant/required values exactly as specified.
3. Build patient/referral/transfer result lists in the required sort order.
4. For each entity, set every required field using only controlled vocabulary values.
5. `blocked_reason_codes`, `issue_codes`, `reason_codes`, and similar code arrays should be treated as unordered sets — include only codes that apply; do not duplicate.
6. Compute cohort/summary/batch-level aggregates:
   - Count totals, status breakdowns, risk breakdowns.
   - Cross-tabulation counts (e.g., counts by urgency AND status) when the template requests them.
   - Ensure all count keys specified in the template are present, even when the count is zero.
7. Verify every required key from the template is present.
8. Verify no value outside the template's allowed lists is used.

## Step 7 — Validate and Return

1. Confirm the JSON is valid and parseable.
2. Confirm list ordering matches the template (ascending by the specified key).
3. Confirm all counts in `summary` / `cohort_summary` are integers that sum correctly.
4. Return the JSON object as the **entire response** — no markdown fences, no prose preamble or postamble, unless the prompt explicitly allows it. Most prompts say "return a single JSON object" or "use only JSON."

## Common Pitfalls

- **Using values not in the template**: Every enum value must come from the template's `allowed_values`. Even if a status seems reasonable, if it is not in the list, do not use it.
- **Wrong sort order**: Check whether the template says "ascending by patient_id", "ascending by referral_id", or "unordered set". Code arrays are usually unordered; entity lists are usually ascending by ID.
- **Missing zero-count keys**: Summary objects must include every key listed in the template, even when the count is zero (e.g., `"approved": 0`).
- **Forgetting to cross-reference**: A patient's status often depends on data from multiple endpoints. Do not classify based on a single endpoint's data alone.
- **Date-arithmetic errors**: When checking document freshness, compute `today - received_date` in days. If the result exceeds the freshness limit, the document is stale.
- **ID format**: Use IDs exactly as returned by the API — preserve case, leading zeros, and punctuation.
- **Base URL substitution**: Always replace `<TASK_ENV_BASE_URL>` with the real base URL before making any requests. If the placeholder appears in payload files, replace it there too.
