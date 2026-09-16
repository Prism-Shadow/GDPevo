---
name: northstar-payer-operations
description: Solve Northstar Health Plan payer-operations tasks across UM authorization, pharmacy appeals, payment integrity, peer-to-peer, and margin analysis. Use the shared task-environment SQL and REST endpoints to gather records, evaluate policy criteria, and return structured JSON matching the supplied answer template.
---

# Northstar Payer Operations Skill

This skill guides a Codex solver through Northstar Health Plan payer-operations
tasks. It covers five operational domains: utilization management (UM)
authorization review, pharmacy appeals intake, payment integrity claim
repricing, peer-to-peer (P2P) case summarization, and therapy margin queue
analysis.

## Task Shapes

Every Northstar task follows the same skeleton:

1. A `prompt.txt` describes the work in natural language and references the
   shared task environment at `<TASK_ENV_BASE_URL>`.
2. `input/payloads/task_context.json` carries structured parameters: target
   business IDs, requester roles, reporting dates, domain-specific rules, and
   environment access details.
3. `input/payloads/answer_template.json` defines the exact JSON schema the
   solver must conform to, including required keys, enum choices, numeric
   precision, and ordering rules.

Return **only** the JSON object matching the answer template. Do not wrap it in
markdown, code fences, or explanatory prose.

## Environment Access

### SQL Endpoint

Send `POST` to `<TASK_ENV_BASE_URL>/sql/query` with header
`Authorization: Bearer pa-review-token-014` and a JSON body:

```json
{"query": "<SQL statement>"}
```

The SQL service is the primary tool for schema discovery and record retrieval.

### Business REST Endpoints

All are `GET` requests to `<TASK_ENV_BASE_URL>` with no special headers beyond
the standard bearer token when needed:

| Endpoint | Use |
|---|---|
| `GET /api/tables` | List available tables |
| `GET /api/cases` | List cases |
| `GET /api/cases/{case_id}` | Single case detail |
| `GET /api/policies` | List policies |
| `GET /api/policies/{policy_id}` | Single policy detail |
| `GET /api/documents/{document_id}` | Retrieve a clinical or administrative document |
| `GET /api/rate-schedules` | List rate schedules for payment integrity work |
| `GET /api/appeals` | List appeals |
| `GET /api/portal` | Portal summary (context overview) |
| `GET /health` | Health check |

### Exploration Order

When beginning a task, take these steps in order:

1. **Read `task_context.json`** to extract the target business ID, reporting
   date, domain rules, and any local memo instructions.
2. **Read `answer_template.json`** to lock in the required output shape, enum
   sets, ordering rules, and precision constraints before querying any data.
3. **Call `GET /api/tables`** to discover available SQL tables.
4. **Probe the schema** with `SELECT * FROM <table> LIMIT 1` to see column
   names and sample data.
5. **Pull task-specific records** using the target ID from task_context. The
   exact queries depend on the domain (see domain sections below).
6. **Pull related records** (policies, documents, rate schedules, appeals) as
   needed using REST endpoints or SQL.

## Domain Workflows

### Domain 1: UM Authorization Review

Used when `task_context` indicates a case review for physical therapy or similar
service authorization.

**Records to gather:**
- The case record: `GET /api/cases/{case_id}`
- Active member/plan context from the case or via SQL
- Requested therapy lines (CPT codes, units, dates)
- Active policy criteria: `GET /api/policies` and filter by the service domain
- Clinical documents: `GET /api/documents/{document_id}` for each document
  referenced in the case or authorization record
- Any existing authorization record (auth number, approved units, dates)

**Decision process:**
1. Apply each criterion key from the answer template to the evidence. For
   physical therapy cases, the common criteria set is:
   - `PT-ACTIVE`: Is the member actively enrolled and the plan in force?
   - `PT-DEFICIT`: Does the clinical evaluation document a functional deficit?
   - `PT-DX`: Is there a qualifying diagnosis?
   - `PT-POC`: Does the plan of care specify frequency, duration, and goals?
   - `PT-UNITS`: Are the requested units within the policy limit?
2. Classify each document as evidence (relied on) or excluded (stale,
   irrelevant, or superseded). Stale documents are those whose date precedes
   the current clinical evaluation or whose content conflicts with newer
   records.
3. Determine the recommendation based on criteria results:
   - All criteria met: `approve`, final status `approved`, route
     `nurse_approval`
   - Information gaps: `pend_for_information`, `pended`, `pending_information`
   - Clinical judgment needed: `escalate_to_md`, `md_review_required`,
     `medical_director_review`
   - Criteria not met: `deny`, `denied`, `medical_director_review`
4. Build the authorization object from the active auth record (or construct it
   from policy when approving). CPT codes are listed in ascending order.
5. Set `determination_letter` and `next_action` to match the recommendation.

**Source precedence rule:** `current_clinical_records_over_stale_export`.
Controlling records are the current clinical documents actually relied on.
Exception records are stale, excluded, or outdated documents.

### Domain 2: Pharmacy Appeals Intake

Used when `task_context` references a coverage appeal with a drug name and
manufacturer assistance screening.

**Records to gather:**
- The case and appeal records: `GET /api/cases/{case_id}`,
  `GET /api/appeals`
- Drug-specific policy criteria: `GET /api/policies` and filter by drug class
- Drug trial/failure records (via SQL, typically in a `drug_trials` or similar
  table)
- Clinical documents (diagnosis confirmation, prior auth denials)
- Manufacturer assistance program details (via SQL or REST)
- Packet requirement rules from the policy

**Decision process:**
1. Classify prior medication evidence:
   - **Documented failures**: prior medications the member has tried and
     failed, confirmed in the clinical record. List in alphabetical order,
     lowercase.
   - **Undocumented or insufficient failures**: medications referenced but
     lacking sufficient trial evidence (missing fill records, inadequate
     duration, or incomplete documentation). List in alphabetical order,
     lowercase.
2. Determine appeal path:
   - Standard internal appeal if the member has standard coverage and no
     imminent risk factors are documented.
   - Expedited internal appeal if the documentation supports imminent risk.
   - External review if internal appeals are exhausted.
3. Calculate the appeal deadline: for standard internal appeals, this is
   typically 30 calendar days from the appeal filing date. Verify against any
   policy override in the case record.
4. Evaluate drug criteria against policy:
   - `DRUG-AUTH`: Is a prior authorization denial on file?
   - `DRUG-DENIAL`: Was the denial for a covered reason (formulary, step
     therapy, medical necessity)?
   - `DRUG-RATIONALE`: Does the prescriber provide a clinical rationale for
     the requested drug?
   - `DRUG-FAILURES`: Does the member have documented failures of required
     step-therapy alternatives? Use `partial` when only some alternatives have
     been tried and confirmed.
5. Assemble required and missing packet items. Payer appeal items come before
   manufacturer assistance items in the ordered list. Missing items are listed
   in case-specific gap order: appeal evidence gaps before assistance
   information gaps.
6. Screen manufacturer assistance:
   - Identify the program matching the drug (e.g., Vraylar Connect for
     Vraylar, Dupixent MyWay for Dupixent, Humira Complete for Humira).
   - Set status to `eligible_ready` if all required fields are present,
     `eligible_missing_information` if any are missing, `not_eligible` if
     criteria are not met, or `not_applicable` if no program exists.
   - List any missing fields alphabetically.
7. Set `next_action` based on the overall state:
   - Appeal ready for filing: `file_appeal`
   - Information needed: `request_more_information`
   - Expedited with income proof missing:
     `complete_expedited_appeal_and_request_income_proof`
   - Assistance application needed: `submit_assistance_application`
   - Not eligible: `close_not_eligible`

**Source precedence rule:** `payer_appeal_before_manufacturer_assistance`.
Controlling records are the appeal record and confirmed clinical evidence.
Exception records are undocumented trials and missing assistance fields.

### Domain 3: Payment Integrity Claim Repricing

Used when `task_context` references a claim needing benchmark validation and
correction routing.

**Records to gather:**
- The claim and its lines: SQL query on claims and claim_lines tables
- The case record: `GET /api/cases/{case_id}`
- Authorization record associated with the claim
- Rate schedules: `GET /api/rate-schedules` to find available benchmarks
- Benchmark rates for each CPT/modifier combination on the claim lines
- Stale or legacy rate sources that may have been used originally

**Decision process:**
1. Identify the correct benchmark source and version. Compare available rate
   schedules against the claim's date of service, plan, and modifier. Reject
   stale sources (e.g., `Legacy Imaging Export`) that are superseded by
   current schedules.
2. For each claim line (in claim-line order):
   - Look up the benchmark rate for the CPT code and modifier.
   - Multiply the benchmark rate by the line units to get
     `correct_allowed_amount`.
   - Compare to `paid_amount`. If correct > paid, disposition is
     `correct_upward`. If correct < paid, `correct_downward`. If equal,
     `no_change`. If the line should not be paid, `deny_line`.
   - `recovery_amount` = correct_allowed_amount - paid_amount (positive for
     upward corrections, negative for downward).
   - Use `null` for absent modifiers, never an empty string.
3. Compute totals:
   - `paid_total`: sum of all line paid amounts.
   - `correct_allowed_total`: sum of all line correct allowed amounts.
   - `recovery_amount`: correct_allowed_total - paid_total (positive means
     underpayment owed to provider).
4. Set `resubmission_route` and `priority`:
   - Provider adjustment: `provider_adjustment`
   - Internal correction: `payment_integrity_correction`
   - Appeal reopen: `appeal_reopen`
   - No correction needed: `no_resubmission`
   - Priority is `standard` unless urgency indicators are present.

**Source precedence rule:** `effective_benchmark_by_plan_modifier_and_date`.
Controlling records include the claim lines and the benchmark records applied.
Exception records include rejected stale benchmarks.

**Currency precision:** All dollar amounts are JSON numbers rounded to two
decimal places (cents).

### Domain 4: Peer-to-Peer Case Summarization

Used when `task_context` references a P2P discussion that has been completed
and needs a structured final summary for the authorization file.

**Records to gather:**
- The case record: `GET /api/cases/{case_id}`
- The P2P event record (via SQL; look for a `p2p_events` table or similar)
- Active policy criteria for the requested procedure
- Clinical documents submitted as evidence
- Authorization status after the P2P

**Decision process:**
1. Extract the requested CPT code from the authorization line.
2. Evaluate each policy criterion against the evidence:
   - For PET MPI cases: `PET-IND` (indication) and `PET-FACTOR`
     (PET-over-SPECT factors).
   - Each criterion is `met`, `not_met`, `unclear`, or `not_applicable`.
3. Identify unresolved criteria: any criteria where the P2P did not resolve
   the gap (remaining `not_met` or `unclear`). List in ascending criterion ID
   order. Use an empty list when none remain unresolved.
4. Determine P2P outcome:
   - `overturn_to_approval` if the P2P supplied new information that changed
     the review from adverse to approval.
   - `uphold_intended_adverse_decision` if the original adverse determination
     stands.
   - `not_applicable` if no P2P occurred.
5. Flag whether new patient-specific information materially changed the review
   (`new_information_changed_review` boolean).
6. List missing PET-over-SPECT factors when `PET-FACTOR` is not met. Use the
   template's enumerated list in the order given: `prior_equivocal_spect`,
   `bmi_limitation`, `attenuation_artifact`. Include every factor that remains
   unsupported.
7. Set `letter_type`:
   - Approval: `approval`
   - Adverse/denial: `denial`
   - Partial: `partial_denial`
   - No letter needed: `no_letter`
8. Set `recommended_alternative`:
   - `SPECT MPI` when PET is denied but SPECT is a reasonable alternative
   - `PET MPI` when the evidence supports it
   - `none` when no alternative recommendation applies
9. Calculate the internal appeal deadline when the final determination is
   adverse: add the plan's internal appeal window (typically 180 calendar days)
   to the final adverse determination date found in the authorization or case
   record. Use `null` when no deadline applies (i.e., the decision is not
   adverse).

**Source precedence rule:** `new_patient_specific_p2p_information`.
Controlling records are the P2P event and the current clinical evidence.
Exception records are unresolved criteria and unsupported clinical factors.

### Domain 5: Therapy Margin Queue Analysis

Used when `task_context` references a service margin queue with row IDs,
threshold ratios, and finance definitions.

**Records to gather:**
- Queue rows from the `service_margin` table using the `queue_row_ids` from
  `task_context.finance_memo` (in the same order they appear)
- Each row's revenue, variable cost, fixed cost, payer segment, service
  domain, and CPT code

**Decision process:**
1. For each queue row (preserving the order from `task_context`):
   - Compute `total_cost` using the formula in
     `task_context.finance_memo.total_cost_definition` (e.g., variable_cost
     plus fixed_cost_allocated).
   - Compute `margin` = revenue - total_cost.
   - Compute `revenue_to_cost_ratio` = revenue / total_cost, rounded to 4
     decimal places.
   - Set `below_threshold` = true when revenue_to_cost_ratio <
     `task_context.finance_memo.revenue_to_cost_threshold`.
   - Set `charge_sensitive` as indicated by the row data (typically a flag
     when the payer-specific charge rate deviates significantly from plan
     norms).
   - Assign `recommended_action`:
     - `payer_contract_review` for below-threshold rows.
     - `monitor_charge_sensitive` for rows above threshold but with charge
       sensitivity flags.
     - `monitor_no_action` for rows with no issues.
2. Build the segment lists:
   - `below_threshold_segments`: any payer segments with at least one
     below-threshold row, listed alphabetically by enum value.
   - `charge_sensitive_segments`: any payer segments with at least one
     charge-sensitive row, listed alphabetically by enum value.
3. Determine the `top_issue`: the combination of payer segment and CPT code
   that has the worst (lowest) revenue_to_cost_ratio among below-threshold
   rows. Use underscore to join them (e.g., `medicaid_97110`). If no rows are
   below threshold, use `"none"`.
4. Calculate `gap_to_120pct`: for the top issue, compute
   `total_cost * threshold - revenue` (the dollar amount needed to reach the
   threshold ratio of cost). Round to two decimal places.

**Source precedence rule:** `margin_threshold_then_charge_sensitivity`.
Controlling records are the queue rows for the reporting period.
Exception records are the below-threshold rows that need contract review.

## Basis Audit Trail

Every task answer must include a `basis_audit` object with four keys:

- `source_precedence`: the precedence rule that drives the decision logic for
  this domain (choose from the template's enum).
- `precedence_record_order`: all controlling and exception records, ordered by
  priority (controlling first, exception records after), using their
  environment IDs.
- `controlling_record_ids`: the records that directly support the
  determination. Use operational evidence order: case/appeal/claim records
  first, then criteria documents, then supporting evidence, then benchmark or
  margin records.
- `exception_record_ids`: records that explain gaps, exclusions, denials, or
  routing decisions. Use business gap/exception order: criteria or route gaps
  before stale or excluded records.

The `source_precedence` enum values (choose the one that matches the domain):

- `current_clinical_records_over_stale_export` -- UM authorization
- `payer_appeal_before_manufacturer_assistance` -- pharmacy appeals
- `effective_benchmark_by_plan_modifier_and_date` -- payment integrity
- `new_patient_specific_p2p_information` -- peer-to-peer
- `margin_threshold_then_charge_sensitivity` -- margin analysis

## General Rules

### Dates
- All dates use ISO 8601 calendar-date format (`YYYY-MM-DD`).
- Appeal deadlines are calendar-day calculations from the triggering event
  date.
- Authorization periods span the approved start and end dates from the auth
  record or policy.

### Currency
- All dollar amounts are JSON numbers rounded to two decimal places.
- Always use `null` for absent modifiers, never `""` or `"null"`.

### Lists
- Follow the ordering rule specified in the answer template for each list
  field.
- When the template says "ascending", sort ascending. When it says
  "alphabetical", sort alphabetically. When it references claim-line order,
  preserve that order.
- When the template gives a `choices` enum for list items, use only those
  values.

### Enums
- Use exactly the string values defined in the template. Do not invent new
  choices or abbreviate.

### SQL Query Construction
- Use `SELECT * FROM <table> LIMIT 1` to discover schema before writing
  targeted queries.
- Filter by the target ID from `task_context` wherever possible.
- When joining, use simple `JOIN ... ON` syntax.
- Quote identifiers only when needed (reserved words, special characters).

### Template Conformance
- Include every required top-level key from the answer template.
- Do not add fields not defined in the template.
- Match the template's enum sets exactly.
- Verify numeric precision: integer fields are integers, ratio fields to the
  specified decimal places, currency to two decimal places.

## Quick Reference: Common SQL Tables

Probe the environment to confirm the current schema, but these tables are
common across Northstar tasks:

| Table | Purpose |
|---|---|
| `cases` | Authorization and appeal cases |
| `case_lines` | Requested/authorized service lines within a case |
| `policies` | Clinical and administrative policy criteria |
| `policy_criteria` | Individual criteria within a policy |
| `documents` | Clinical documents (evaluations, plans of care, test results) |
| `claims` | Paid and pending insurance claims |
| `claim_lines` | Individual line items on a claim |
| `rate_schedules` | Benchmark rate tables by CPT, modifier, and plan |
| `appeals` | Member and provider appeals |
| `p2p_events` | Peer-to-peer discussion records |
| `service_margin` | Monthly margin analysis rows by payer segment |
| `drug_trials` | Prior medication trial and failure records |
| `members` | Member demographics and enrollment |
| `authorizations` | Prior authorization records |

Always verify the exact table names and column names with `GET /api/tables`
and a `LIMIT 1` probe before writing production queries.

## Step-by-Step Execution

For any Northstar task, follow this sequence:

1. Read `input/payloads/task_context.json` and
   `input/payloads/answer_template.json`.
2. Call `GET /api/tables` and probe key tables with `LIMIT 1`.
3. Pull the primary target record(s) using the business ID from task_context.
4. Pull related records (policies, documents, benchmarks, appeals, margins).
5. Evaluate criteria or business rules against the evidence.
6. Classify evidence documents or records as controlling, supporting, or
   excluded.
7. Build the `basis_audit` trail.
8. Assemble the final JSON object matching every required field from the
   answer template.
9. Verify numeric precision, date formats, enum values, and list ordering
   against the template.
10. Return the raw JSON object with no surrounding text, markdown, or code
    fences.
