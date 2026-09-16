---
name: northstar-payer-review
description: >
  Process Northstar Health Plan payer operations reviews that require data
  gathering from a shared API environment and structured JSON output. Use this
  skill whenever the task involves Northstar, payer operations, prior
  authorization, UM review, pharmacy appeals, claim repricing, payment
  integrity, peer-to-peer, therapy margin analysis, or any review that
  references a task environment with SQL and REST endpoints. This applies when
  the task includes a task_context.json and answer_template.json specifying the
  output contract, and mentions endpoints like POST /sql/query with a bearer
  token.
---

# Northstar Payer Operations Review

## Overview

This skill covers the Northstar Health Plan payer review methodology: query a
shared API environment, evaluate cases against policy criteria and rate
schedules, and return structured JSON matching a provided output template.
The methodology applies across all Northstar review types:

- Prior authorization (UM nurse)
- Pharmacy coverage appeals and manufacturer assistance intake
- Claim repricing and payment integrity correction
- Peer-to-peer final summaries
- Therapy margin queue analysis

All tasks share a common API surface, a fixed set of source-precedence rules,
and a consistent basis-audit structure. What varies is the business domain, the
criteria keys, and the specific output fields, all of which are defined in the
per-task `answer_template.json`.

## Environment Configuration

Every Northstar task environment exposes these endpoints:

- Base URL: provided as `<TASK_ENV_BASE_URL>` in the task prompt or
  `environment_access.md`. Resolve the placeholder to the actual URL before
  making any request.
- SQL endpoint: `POST /sql/query` with header
  `Authorization: Bearer pa-review-token-014`
- Business REST endpoints:
  - `GET /` and `GET /portal` — system overview
  - `GET /api/tables` — available database tables
  - `GET /api/cases` and `GET /api/cases/{case_id}` — case records
  - `GET /api/policies` and `GET /api/policies/{policy_id}` — policy criteria
  - `GET /api/documents/{document_id}` — clinical and administrative documents
  - `GET /api/rate-schedules` — fee schedule and benchmark records
  - `GET /api/appeals` — appeal records

When making SQL requests, send JSON with a `query` field:

```json
{"query": "SELECT ... FROM ... WHERE ..."}
```

The response contains a `rows` array or a `data` array with the result set.

## Input File Conventions

Each task provides three files inside `input/`:

1. **prompt.txt** — Business narrative: who is requesting what, and why
2. **payloads/task_context.json** — Structured metadata: business ID, requester
   role, reporting date, environment config, local memo, finance memo, queue
   row IDs, and domain hints
3. **payloads/answer_template.json** — Exact JSON output contract: required
   top-level keys, field types, enum choices, ordering rules, and precision
   constraints

Read all three before making any API calls. The template defines the output
shape; the context defines the business target and scope.

## Workflow

### Step 1: Load and Parse the Task

Read `prompt.txt`, `task_context.json`, and `answer_template.json`. Identify:

- The business case, appeal, claim, or queue ID (from `task_context`)
- The requester role (drives the review perspective)
- The reporting date (used for effective-date comparisons and deadline math)
- Every required top-level field and its constraints
- Every allowed enum value for each field
- Every ordering rule for list fields
- Any numeric precision requirements

### Step 2: Survey the Environment

Start with a broad survey to understand what data the environment holds:

- `GET /api/tables` — discover available tables and their column names
- `GET /api/cases` — list accessible cases; then fetch the target case with
  `GET /api/cases/{target_id}`
- `GET /api/appeals` — list appeal records when the task involves an appeal
- `GET /api/rate-schedules` — list rate schedules for claim and repricing tasks
- `GET /api/policies` — list policy and criteria records
- `GET /api/documents/{document_id}` — fetch specific clinical or
  administrative documents

Use SQL for structured extraction when REST endpoints do not expose the needed
granularity. Common patterns:

- Query a specific table with a WHERE clause on the business ID
- Join case, document, and criteria tables to correlate records
- Aggregate financial data by row ID, payer segment, or CPT code

### Step 3: Gather Controlling Records

For each task type, identify which records from the environment directly control
the result and which explain gaps or exclusions:

| Task Type | Controlling Records | Exception Records |
|-----------|-------------------|-------------------|
| Prior auth (UM) | Current clinical documents, authorization record | Stale documents, unmet criteria IDs |
| Pharmacy appeal | Appeal record, supporting trial/clinical records | Insufficient trial records, missing packet field IDs |
| Claim repricing | Claim lines, current benchmark/rate records | Stale schedule records |
| P2P | P2P event record, clinical documents | Unmet criteria IDs, missing factor enum values |
| Margin queue | All target service-margin rows | Below-threshold rows, charge-sensitive rows |

For documents, separate into two categories:

- **Evidence documents**: current clinical or administrative records that
  support the determination
- **Excluded documents**: stale, superseded, or irrelevant records

A record is stale when a newer record of the same type exists with a more
recent effective date or version. Cross-reference dates, versions, and
effective periods across records before deciding. Never use a stale record in
place of a current equivalent.

### Step 4: Evaluate Policy Criteria

Map every criteria key from the template to data in the environment. For each
criterion:

- **`met`**: the environment records clearly satisfy the criterion
- **`not_met`**: the records contradict or fail to demonstrate it
- **`unclear`**: the records are ambiguous or insufficient
- **`not_applicable`**: the criterion does not apply to this case or task type

Check criteria against the target case's documents, member and plan context,
and applicable policy records. A criterion stays `unresolved` when it is
`not_met` or `unclear` and the review could not resolve it.

### Step 5: Assign the Source Precedence Rule

Pick the correct `source_precedence` from these six rules. The task type
determines which rule applies:

| Rule | When to Use |
|------|-------------|
| `current_clinical_records_over_stale_export` | Prior auth or clinical review where stale documents must be excluded in favor of current evaluation records |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy or coverage appeal where payer-side appeal evidence takes priority over manufacturer assistance programs |
| `effective_benchmark_by_plan_modifier_and_date` | Claim repricing where the correct rate schedule is determined by effective date, plan, and modifier |
| `new_patient_specific_p2p_information` | Peer-to-peer review where the P2P discussion adds patient-specific information on top of existing clinical records |
| `margin_threshold_then_charge_sensitivity` | Margin queue analysis where rows are classified first by threshold violation, then by charge sensitivity |
| `appeal_deadline_then_clinical_then_payment_integrity` | Appeals where processing order follows deadline urgency, then clinical merit, then payment integrity |

### Step 6: Construct the Basis Audit

Every output requires a `basis_audit` object with exactly four keys. Build them
in this order:

1. **source_precedence**: the rule selected in Step 5.

2. **controlling_record_ids**: every record ID that directly controls the
   result, ordered by operational evidence priority:
   - Prior auth: current clinical documents first, then authorization record
   - Appeals: appeal record first, then supporting clinical or trial records
   - Claims: claim lines first, then benchmark and rate records
   - P2P: P2P event first, then clinical documents
   - Margin: all target rows in the order they appear in the queue

3. **exception_record_ids**: records that explain gaps, exclusions, denials, or
   stale data. Order criteria or route gaps before stale or excluded records
   when both appear. Include:
   - Stale schedule or document records that were rejected
   - Unmet criteria IDs
   - Missing packet items (by their field identifier from the template)
   - Trial records that document insufficient or undocumented failures
   - Missing PET factor enum values

   A row can appear in both `controlling_record_ids` and
   `exception_record_ids` when it is part of the analysis and also the record
   that triggers the exception (e.g. the below-threshold row in a margin
   analysis).

4. **precedence_record_order**: the full ordered trail merging controlling and
   exception records in source-precedence order, highest priority first. Put
   records that override or take precedence before the records they supersede.
   Put controlling records before exception records of the same type. For
   margin tasks, follow the queue row order from `task_context`.

### Step 7: Fill Every Template Field

Go through the template's required top-level fields and populate each one:

- **Enums**: pick exactly from the allowed choices. Never invent new values.
- **Lists**: follow the ordering rule specified in the template. Common
  orderings are: ascending by document or record ID, alphabetical by name or
  code, claim-line order from the source claim, operational packet order
  (payer items before assistance items), and case-specific gap order (appeal
  evidence gaps before assistance information gaps).
- **Numbers**: match the precision in the template. Currency values are rounded
  to 2 decimal places; ratios to 4 decimal places; units are whole integers.
- **Nulls**: use `null` for absent modifiers, non-applicable dates, and
  non-applicable deadline fields. Do not use empty strings.
- **Booleans**: return `true` or `false` as JSON literals, not strings.
- **Dates**: ISO 8601 `YYYY-MM-DD` format.

Financial formulas to use when the template requires computed amounts:

- `total_cost` = `variable_cost` + `fixed_cost_allocated`
- `margin` = `revenue` - `total_cost`
- `revenue_to_cost_ratio` = `revenue` / `total_cost`
- `recovery_amount` (claim level) = `correct_allowed_total` - `paid_total`
- `recovery_amount` (line level) = `correct_allowed_amount` - `paid_amount`
- `gap_to_120pct` = (`threshold` x `total_cost`) - `revenue`, where `threshold`
  is the `revenue_to_cost_threshold` from the task context

For internal appeal deadlines: add 180 calendar days to the adverse
determination date. If the date is not specified, use the P2P event or appeal
determination date.

### Step 8: Validate and Return

Before returning, verify:

- Every required top-level key from the template is present
- Every enum value is from the allowed set
- Every list follows its ordering rule
- Every numeric value matches its precision spec
- `basis_audit` has all four required keys
- `null` is used for absent modifiers, not empty strings

Return exactly one JSON object. Do not wrap it in markdown fences, do not add
commentary or prose outside the JSON.

## Common Pitfalls

- **Mixing up stale and current records**: always compare effective dates and
  version identifiers. When two records serve the same purpose, the newer one
  controls; the older one is an exception.
- **Wrong source precedence for the task type**: a prior auth uses
  `current_clinical_records_over_stale_export`, not
  `effective_benchmark_by_plan_modifier_and_date`. Match the rule to the task.
- **Forgetting to cross-reference**: the environment may hold records from
  multiple tables. Join or correlate them by business ID, case ID, or document
  ID before concluding.
- **Using empty strings instead of null**: when a modifier is absent or a
  deadline does not apply, use JSON `null`, not `""`.
- **Omitting ordering rules**: the template specifies list ordering for a
  reason. Sorting by document ID, CPT code, or business-ID order is part of the
  output contract.
- **Counting stale records as evidence**: a document superseded by a newer
  evaluation belongs in `excluded_documents` (or `stale_source_rejected`),
  not in `evidence_documents`.
- **Double-counting financial components**: when computing `total_cost`, use
  the formula from the task context (`variable_cost` + `fixed_cost_allocated`),
  not an ad-hoc sum.
