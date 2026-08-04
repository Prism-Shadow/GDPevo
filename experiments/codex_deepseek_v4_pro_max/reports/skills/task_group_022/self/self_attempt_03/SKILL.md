---
name: atlas-commerce-operations
description: Work with the Atlas Commerce Operations database service to produce analytical reports and apply controlled data corrections. Use for fulfillment scorecards, refund reconciliations, carrier quality corrections, warehouse productivity reviews, and support health assessments.
---

# Atlas Commerce Operations

## Overview

This skill covers working with the Atlas Commerce Operations REST API — an authenticated SQL-backed service for querying business records and applying controlled data corrections. Tasks fall into two modes: read-only analytical reporting and read-write data correction with audit trails.

## Service Endpoints

All endpoints live under the base URL provided by the environment (typically `<TASK_ENV_BASE_URL>`). Every `/api/` request requires the header `Authorization: Bearer atlas-ops-token-022`.

### Discovery Endpoints (GET)

| Endpoint | Purpose |
|---|---|
| `GET /api/schema` | Returns table names, column names, and types for all business tables. |
| `GET /api/data-dictionary` | Returns human-readable descriptions for tables and columns. |
| `GET /api/correction-audit` | Returns the correction audit log for verification. |

### Read-Only SQL (POST)

`POST /api/sql` accepts a JSON body with:
- `sql` (string, required): A `SELECT` or `WITH` query.
- `params` (array, optional): Positional bind parameters for values in the query.

Always use parameterized queries. Never interpolate values directly into SQL strings.

### Transactional SQL (POST)

`POST /api/sql/transaction` accepts a JSON body with:
- `statements` (array of `{sql, params}` objects, 1–6 entries): The ordered SQL statements.
- `expected_total_changes` (integer, 0–12): The total number of business rows that should be modified across all statements.

**Allowed statement types:**
- `SELECT` / `WITH` queries (anywhere in the transaction).
- `UPDATE` statements targeting only `carrier_scans` or `inventory_movements`.
- `INSERT` statements into `correction_audit` with all audit columns populated.

## Task Anatomy

Every task follows the same input structure:

```
input/
├── prompt.txt              ← High-level business purpose
└── payloads/
    ├── <request>.json       ← Business scope, definitions, computation rules
    └── answer_template.json  ← Exact output JSON schema
```

The task always expects the result written to `answer.json` at the workspace root.

## Standard Workflow

### Step 1 — Discover the Data Model

Before writing any queries, call `GET /api/schema` and `GET /api/data-dictionary`. Understand:
- Which tables exist and how they relate (foreign keys, join columns).
- What each column means (units, enumerations, timestamp semantics).
- Which tables are relevant to the current task's domain.

### Step 2 — Parse the Business Request

Read the request JSON in `payloads/`. Extract:
- **Scope**: Time windows (start/end, inclusive/exclusive), population filters, cohort definitions.
- **Business definitions**: How metrics are computed, what "complete", "on time", "severe", "leakage candidate" etc. mean.
- **Computation rules**: Rounding instructions, ordering rules, rate formulas.
- **Status classification**: Cascading condition rules for status enums.
- **Correction details** (if applicable): The approved field change, reason code, actor, audit metadata.

### Step 3 — Parse the Answer Template

Read the answer template JSON in `payloads/`. It defines:
- Required fields and their types.
- Numeric constraints (minimum, maximum, multipleOf).
- Array item schemas, min/max items, uniqueness constraints.
- Enum values for status/risk fields.
- Ordering rules for arrays.
- Pattern constraints (e.g., `^ORD-[0-9]{6}$`).

### Step 4 — Query and Compute

For **analytical** tasks:
- Write parameterized `SELECT`/`WITH` queries against `POST /api/sql`.
- Filter by the exact scope boundaries using bind parameters.
- Compute metrics per the business definitions, keeping intermediate values unrounded.
- Apply rounding only to final reported values at the specified precision.
- Apply ordering rules exactly as stated (multi-key, ascending/descending per key).

For **corrective** tasks:
- Query to identify the contradiction described in the request.
- Compute any pre-correction state metrics.
- Construct the transaction with an `UPDATE` and an `INSERT INTO correction_audit`.
- After the transaction, run a verification `SELECT` to confirm the corrected value.

### Step 5 — Produce the Answer

Write a single JSON object to `answer.json` that conforms exactly to the answer template:
- Every required field must be present; no additional fields.
- Arrays must satisfy `minItems`, `maxItems`, `uniqueItems` constraints.
- Strings must match any `pattern` constraint.
- Numbers must respect `minimum`, `maximum`, `multipleOf` constraints.
- Enum fields must use exactly the specified values.
- No commentary, narrative, or extra whitespace outside the JSON.

## Operational Rules

### Query Discipline
- Always use parameterized queries (`params` array). Never concatenate values into SQL strings.
- Use `WITH` clauses (CTEs) for multi-step logic when it improves clarity.
- For time-window filtering, apply boundary semantics exactly: inclusive means `>=`/`<=`, exclusive means `>`/`<`.

### Cutoff Semantics
- When a cutoff timestamp is given, evaluate record state as of that exact moment.
- "Complete by the cutoff" means the relevant event timestamp is `<=` the cutoff.
- "Incomplete" means no qualifying event exists by the cutoff.

### Rounding and Precision
- Carry full precision through intermediate calculations.
- Round only the final reported value to the specified number of decimal places.
- For rates, the denominator typically includes all eligible records, not just the completed/qualifying subset.

### Ordering Rules
- Apply multi-key ordering in the exact sequence specified.
- When a tie-break key is given (e.g., "then by label ascending"), it is mandatory.
- Sort ascending by default unless "descending" is explicitly stated.

### Status Classification
- Evaluate conditions in the order listed — the first matching condition determines the status.
- If no explicit condition matches, use the fallback (often the most severe category).
- Compute all rate inputs from the same consistent population.

### FX Conversion
- When currency conversion is required, look up the daily rate for the transaction's `service_date`.
- Multiply the local-currency amount by the `usd_per_unit` rate.
- Use the same date-based rate for all comparisons involving a given transaction.

### Correction Rules
- Only apply corrections that are explicitly approved in the business request.
- The transaction must include both the data `UPDATE` and the `INSERT INTO correction_audit`.
- Populate all audit columns: `audit_id`, `correction_key`, `entity_type`, `entity_id`, `source_row_id`, `field_name`, `old_value`, `new_value`, `reason_code`, `corrected_at`, `actor`.
- Set `expected_total_changes` to exactly the number of business rows the UPDATE should modify (typically 1).
- After the transaction, run a verification query. Set correction status to `APPLIED` only when the post-change query confirms the corrected value and the mutation counts match expectations. Otherwise use `NOT_APPLIED`.

### Output Discipline
- Validate the output JSON against the answer template before writing.
- Use the exact field names, types, and constraints from the template.
- Do not include explanatory text, markdown fences, or any content outside the JSON object.

## Common Task Categories

### Fulfillment Scorecard
Compute order completion rates against a cutoff, identify worst-performing regions, flag severe exceptions, and assign an overall status using cascading rate thresholds.

### Refund Reconciliation
Reconcile settled refunds with reversals, convert amounts to a reporting currency using daily FX rates, rank refund reasons by net value, identify leakage candidates, and classify cohort risk.

### Carrier Quality Correction
Identify a single carrier-status contradiction between raw and canonical values, compute pre- and post-correction backlog counts, apply the approved correction with an audit record, and report the outcome.

### Warehouse Productivity Review
Compute task completion metrics, rank employees by units-per-hour, identify rework rates, find delayed high-priority tasks, determine the lowest-performing team, and classify facility health.

### Support Health Review
Analyze case SLAs by priority tier, count first-response and resolution breaches, list severe active cases, identify the worst-affected accounts, compute median resolution time, and classify overall support risk.
