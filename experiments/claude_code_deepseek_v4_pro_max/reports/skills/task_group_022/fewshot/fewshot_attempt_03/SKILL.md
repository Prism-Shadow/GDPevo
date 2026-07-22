# Atlas Commerce Operations — Analytical & Correction Tasks

## Overview

This skill handles operational analysis and data-correction tasks against the **Atlas Commerce Operations** workplace database. It covers both read-only analytical scorecards/reconciliations/reviews and controlled single-row data corrections with audit verification. The service exposes a REST API with authenticated SQL query, SQL transaction, schema introspection, and correction-audit endpoints.

## When to Use

Invoke this skill when the task:
- References the "Atlas" or "Atlas Commerce Operations" workplace service
- Involves querying business records (orders, shipments, refunds, warehouse tasks, support cases, carrier scans, accounts)
- Requires computing operational metrics from database records using business definitions in a payload
- Requires a controlled data correction with audit trail verification
- Directs you to write a JSON answer conforming to an answer template schema
- Mentions endpoints like `/api/schema`, `/api/data-dictionary`, `/api/sql`, `/api/sql/transaction`, or `/api/correction-audit`

## Environment Connection

### Base URL and Authentication

Read `environment_access.md` (when present) for the service base URL and credentials. If that file is absent, use the `TASK_ENV_BASE_URL` environment variable.

The service authenticates with an `Authorization: Bearer <token>` header. The token is provided in `environment_access.md` or the environment.

### Available Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/schema` | Database schema — table names, column names, types, relationships |
| GET | `/api/data-dictionary` | Field-level documentation — column meanings, enumerations, business context |
| POST | `/api/sql` | **Read-only** SQL queries for analysis. Request body: `{"sql": "<query>"}` |
| POST | `/api/sql/transaction` | **Controlled write** SQL transaction. Used only for approved data corrections. Request body includes the SQL statement and metadata. |
| GET | `/api/correction-audit` | Query correction audit trail records to verify a correction was applied. Supports query parameters to filter by audit_id, correction_key, entity_id, etc. |

## Input Discovery

Every task follows a consistent input layout. Read these files in order:

### 1. Task Prompt (`input/prompt.txt` or `prompt.txt`)

The natural-language prompt describes:
- The business domain and stakeholder (e.g., "Fulfillment leadership", "Refund Operations")
- The operational review or correction being requested
- Which payload files contain the detailed scope and template
- The expected output file (`answer.json`)
- Whether the task is read-only or involves a data mutation

### 2. Business Request Payload (`input/payloads/<request>.json`)

This JSON document defines:
- **Scope**: The population of records to analyze (time windows, account tiers, regions, warehouses, cohorts)
- **Business definitions**: How to classify records (e.g., what makes an order "complete", "on time", a "severe exception", a "leakage candidate")
- **Computation rules**: Formulas for rates, rankings, rollups, rounding, currency conversion
- **Status/risk classification**: Tiered rule sets mapping computed metrics to status labels
- **For corrections**: The exact target record, field, old/new values, audit metadata, and success criteria

### 3. Answer Template (`input/payloads/answer_template.json`)

A JSON Schema document defining the exact output shape. Key properties:
- `type: "object"` with `additionalProperties: false` — no extra fields allowed
- `required` array — every listed field must be present
- Each property has type constraints, `minimum`/`maximum`, `enum` values, `pattern` for IDs, `multipleOf` for precision
- Arrays specify `minItems`, `maxItems`, `uniqueItems`, and ordering rules in descriptions

## Workflow

### Phase 1: Understand the Domain

1. Read `prompt.txt` to identify the business domain.
2. Read the business request payload. Parse every definition, formula, threshold, and rule.
3. Read the answer template. Note every required field and its constraints.

### Phase 2: Explore the Schema

1. Call `GET /api/schema` to discover table names, columns, and relationships.
2. Call `GET /api/data-dictionary` to understand column semantics — which columns are identifiers, which hold status codes, timestamps, amounts, currencies, regions, priorities.
3. Map the business definitions from the request payload onto the actual schema:
   - Which tables hold the population?
   - Which columns implement each business definition?
   - How are joins structured (foreign keys, shared IDs)?

### Phase 3: Query and Compute

Write SQL queries via `POST /api/sql`. Principles:

- **Respect boundaries**: Use the exact cutoff timestamps, date ranges, and boundary rules (inclusive/exclusive) from the request. Timestamps are UTC.
- **Build incrementally**: Start with a count query to verify the population, then add filters, then joins, then aggregations.
- **Apply definitions literally**: Translate each business definition from the request payload into SQL conditions. For example, if "complete" requires every shipment delivered, that means checking MAX(status) or using NOT EXISTS for non-delivered shipments.
- **Handle NULLs explicitly**: Missing data behaves differently from zero/false in business rules. The data dictionary clarifies which columns are nullable.
- **Currency conversion**: When the request specifies FX conversion, join `fx_rates` on the service date and row currency, using the `usd_per_unit` rate.
- **Ranking and ordering**: Apply tie-breaking rules exactly as specified.

### Phase 4: Corrections (Only When Requested)

If the task involves a data correction:

1. **Identify the contradiction**: Query the raw source data to find the mismatch between raw and canonical values described in the request.
2. **Construct the transaction**: Use `POST /api/sql/transaction` with an UPDATE statement that changes only the single canonical field identified. Include the `correction_key`, `reason_code`, `actor`, and `audit_id` from the approved correction block in the request payload.
3. **Verify**: After the transaction, query the corrected row to confirm the value changed. Also query `GET /api/correction-audit` to confirm exactly one audit row was written with the expected metadata.
4. **Report status**:
   - `"APPLIED"` — exactly one business row mutated, exactly one audit row created, and post-change query confirms the new canonical value.
   - `"NOT_APPLIED"` — any other outcome.

### Phase 5: Assemble the Answer

1. Compute every required field from the query results, following the business definitions exactly.
2. Apply rounding only where specified (usually only to final reported rates, not intermediate calculations). Use the precision specified (`multipleOf` in the template).
3. Sort array elements exactly as specified in the template or request (ascending IDs, ranked order, etc.).
4. Construct a JSON object containing exactly the keys listed in the template's `required` array — no extra fields.
5. Validate the result:
   - Every `required` field present?
   - Types match (`integer` vs `number`)?
   - Enums match allowed values?
   - ID patterns match the specified regex?
   - Array lengths match `minItems`/`maxItems`?
   - Numeric values within `minimum`/`maximum`?

### Phase 6: Write Output

Write the validated JSON to `answer.json` with no surrounding commentary, explanation, or markdown formatting. The file must contain only the JSON object.

## Common Pitfalls

- **Time boundary confusion**: "Created during the window" means `created_at >= start AND created_at <= end` for inclusive boundaries. "As of cutoff" means `status_at <= cutoff`. Distinguish creation-time filters from state-at-cutoff filters.
- **Denominator errors**: A rate's denominator is defined in the request — it may be all eligible records, not just the ones that could satisfy the numerator condition.
- **Incomplete ≠ opposite of complete**: An order with no shipments is incomplete under "no physical shipment" rules, but an order with some shipments not yet delivered is also incomplete. Read the complete set of conditions.
- **Ranking before rounding**: When the request says "order by unrounded rate ascending", compute the sort key before rounding, then round only the displayed values.
- **Median for even counts**: When computing median over an even number of values, average the two central values.
- **Correction scope**: Only change the single canonical field specified. Raw/source columns, identity columns, and unrelated rows must stay unchanged.
- **JSON Schema `additionalProperties: false`**: The output object must not contain any fields beyond those listed in the template.

## Reusable Query Patterns

### Counting a Population

```sql
SELECT COUNT(*) AS cnt
FROM <table>
WHERE <scope_filters>
```

### Aggregating with Conditions

When a business definition requires checking conditions across child rows (e.g., "every shipment must be delivered"), use patterns like:

```sql
-- Orders where ALL child rows satisfy a condition
SELECT parent_id
FROM child_table
GROUP BY parent_id
HAVING COUNT(*) = SUM(CASE WHEN <condition> THEN 1 ELSE 0 END)
```

### Regional Rollups

```sql
SELECT region, COUNT(...) AS numerator, ...
FROM facts
JOIN dimension ON ...
GROUP BY region
ORDER BY <computed_rate> ASC, region ASC
```

### Currency Conversion

```sql
SELECT r.amount * fx.usd_per_unit AS amount_usd
FROM refunds r
JOIN fx_rates fx ON fx.service_date = r.service_date AND fx.currency = r.currency
```

### Correction Transaction

```sql
UPDATE <table>
SET <canonical_field> = '<new_value>'
WHERE <row_identifier> = '<id>'
  AND <canonical_field> = '<old_value>'
```

## Task Type Quick Reference

| Task Type | Endpoints Used | Read/Write | Key Challenge |
|-----------|---------------|------------|---------------|
| Scorecard | schema, data-dictionary, sql | Read-only | Cohort filtering, multi-condition status rules |
| Reconciliation | schema, data-dictionary, sql | Read-only | FX conversion, leakage candidate detection, reason ranking |
| Quality Correction | schema, data-dictionary, sql, sql/transaction, correction-audit | Write | Identifying the contradiction, minimal correction, audit verification |
| Productivity Review | schema, data-dictionary, sql | Read-only | Per-employee/team aggregation, rate computation, ranking |
| Health Review | schema, data-dictionary, sql | Read-only | SLA breach computation, active-time clock, multi-tier risk classification |
