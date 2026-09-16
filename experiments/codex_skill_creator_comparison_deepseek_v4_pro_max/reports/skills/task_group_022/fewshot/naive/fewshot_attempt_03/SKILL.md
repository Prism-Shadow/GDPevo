---
name: atlas-operations-analyst
description: Analyze Atlas Commerce Operations data using a read-only SQL API with schema discovery, compute business metrics from query results, apply domain rules (rates, rankings, severity classification, currency conversion, SLA breaches), perform controlled data corrections through SQL transactions, and write output conforming exactly to a provided JSON answer template.
---

This skill covers analytical tasks against the Atlas Commerce Operations database. The solver reads a business request and supporting payloads, discovers the database schema, writes SQL, computes results client-side using the stated business rules, and writes a strict-format JSON answer.

## Environment

Every task provides a base URL in a placeholder like `<TASK_ENV_BASE_URL>` or a literal URL such as `http://task-env:9022/`. Use that value throughout. The authentication is already wired:

- Header `Authorization: Bearer atlas-ops-token-022`
- Header `Content-Type: application/json`

Validate connectivity with `GET /health` once at the start.

## API Endpoints

| Method | Path                     | Purpose                                      |
|--------|--------------------------|----------------------------------------------|
| GET    | `/health`                | Confirm the service is reachable             |
| GET    | `/api/schema`            | List tables and columns                      |
| GET    | `/api/data-dictionary`   | Field descriptions, constraints, foreign keys|
| POST   | `/api/sql`               | Run a read-only SQL query                    |
| POST   | `/api/sql/transaction`   | Run a controlled atomic write (corrections)  |
| GET    | `/api/correction-audit`  | Read correction audit records                |

### POST /api/sql

Submit a JSON body with a `"sql"` field containing the SQL statement. The endpoint returns query results as a JSON array of row objects. Column names match the schema exactly as returned by `/api/schema`. Use this endpoint for all analytical reads.

### POST /api/sql/transaction

Used only for controlled data corrections. Submit a JSON body with a `"sql"` field. The endpoint returns mutation results including `affected_business_rows` and `audit_rows`. Follow it with a verifying read query through `POST /api/sql` to confirm the change took effect.

### GET /api/correction-audit

Returns audit records for past corrections. Query parameters may filter by correction key, entity type, or date range.

## Workflow

Execute these steps in order every time:

### 1. Read the inputs

Read three files from the task directory:

- `input/prompt.txt` — the task narrative, often containing a `<TASK_ENV_BASE_URL>` placeholder or a literal URL. Replace the placeholder with the URL from `environment_access.md` or the task-provided context.
- `input/payloads/<request>.json` — the detailed business rules: scope definitions, cutoff timestamps, thresholds, ranking policies, status classification rules, and domain-specific definitions.
- `input/payloads/answer_template.json` — the exact output schema: required fields, types, minimum/maximum bounds, `multipleOf` constraints, `enum` values, `pattern` regexes, and array length constraints.

### 2. Discover the schema

Call `GET /api/schema` for table and column names. Call `GET /api/data-dictionary` for column descriptions and relationships. Match request terminology to database columns: payload key names often map closely to dictionary field names. Identify which tables hold the entities the request references (orders, shipments, carrier scans, refunds, reversals, accounts, support cases, warehouse tasks, employees, teams, etc.).

### 3. Build and run SQL queries

Write SQL against the discovered schema. The query service supports standard SQL: SELECT, JOIN, WHERE, GROUP BY, ORDER BY, aggregate functions, date arithmetic, subqueries, etc.

**Date handling**: Treat timestamps as exact UTC boundaries. Use inclusive/exclusive bounds exactly as stated in the request. Compare against cutoffs with `<=` for inclusive and `<` for exclusive. Prefer ISO 8601 string comparisons in WHERE clauses.

**Joining**: Relate entities through their foreign keys as documented in the data dictionary. Orders link to shipments, shipments link to carrier scans, refunds link to orders, cases link to accounts, tasks link to employees and teams, etc.

**Currency conversion**: When the request calls for USD conversion, join through `fx_rates` using the service date and source currency. Multiply the source amount by `fx_rates.usd_per_unit`.

**Aggregation caution**: When counting distinct entities, use `COUNT(DISTINCT ...)` or handle deduplication client-side. A single order with multiple shipments must count once as an order unless the metric explicitly counts shipments.

### 4. Compute results client-side

After fetching raw rows, apply the business rules from the request payload in code. Do not try to encode the full business logic in SQL alone.

**Rates (ratios)**: Divide the qualifying count by the denominator count. Keep intermediate values unrounded. Round only the final reported ratio to the decimal places specified in the template or request (typically 4 for ratios, 2 for monetary amounts or hours).

**Rankings (top N / worst N)**: Sort by the primary metric as stated (descending or ascending), then by the tiebreak key as stated. Take exactly the top N entries. Verify the sort direction matches the request: "ascending" means smaller values first.

**Severity / exception detection**: Compare row timestamps against the cutoff and threshold durations. A common pattern: `cutoff - timestamp > threshold` for late detection, or checking whether a promised time is breached by more than a stated grace window.

**Status classification**: Apply tiered rules in the order given. First matching tier wins. Compute all required rates first, then test each tier's conditions. If no tier matches, the last (fallback) tier applies.

**SLA breach detection**: Compare active elapsed times (or the equivalent clock field from the schema) against priority-specific thresholds. For unresolved entities at the cutoff, use the elapsed time from the entity timestamp to the cutoff. Match the clock field against the schema; the dictionary often names it something like `support_active_time_seconds` or similar.

**Median**: Sort values ascending. For odd counts, pick the center element. For even counts, average the two central values. Round to the specified precision.

**Productivity (units per hour)**: Divide total completed units by total productive minutes, then multiply by 60. Round to the specified decimal places. The unit-of-work column comes from the schema (e.g., `completed_units`, `productive_minutes`).

**Monetary netting**: When the request asks for net refund amounts after reversals, sum refund amounts and subtract linked reversal amounts, both converted to USD at their respective service-date rates.

### 5. Write the answer

Produce exactly one JSON object conforming to the answer template. Write it to `answer.json` in the working directory. The answer must:

- Contain every `required` field from the template
- Satisfy every type, `minimum`, `maximum`, `multipleOf`, `enum`, `pattern`, `minItems`, `maxItems`, and `additionalProperties` constraint
- Include no extra fields beyond what the template permits
- Contain no narrative, explanation, or commentary outside the JSON

## Correction transactions

When the request asks for a data correction (carrier quality tasks, etc.):

1. **Identify the discrepancy**: Compare raw source values against canonical values in the queried data. The request will state that exactly one contradiction exists. Find the row where the raw value and canonical value disagree.
2. **Build the UPDATE**: Construct an `UPDATE` statement that changes only the single canonical field for the identified row. Use the exact `new_value` derived from the raw source. Do not modify raw source columns, source identity columns, or unrelated rows.
3. **Submit the transaction**: POST the update to `/api/sql/transaction`. The request provides `reason_code`, `actor`, `audit_id`, `correction_key`, and `corrected_at` — include these in any annotations the API expects.
4. **Verify**: Run a confirming SELECT through `POST /api/sql` to check that the corrected canonical value is present.
5. **Determine status**: Report `APPLIED` only when the transaction returned exactly one `affected_business_rows` and one `audit_rows`, and the post-query confirms the new value. Otherwise report `NOT_APPLIED`.
6. **Backlog analysis**: Compute pre-correction and post-correction counts of non-delivered entities at the cutoff. Report the delta as post minus pre.

Read the correction audit record from `GET /api/correction-audit` (filter by the correction key) and include the full audit record fields in the answer.

## Common pitfalls

- **Rounding too early**: Compute rates from raw integer counts, then round only the final reported value. Rounding intermediate values can shift rankings and classifications.
- **Inclusive vs. exclusive boundaries**: The request usually states "inclusive". Use `>=` and `<=` unless told otherwise. A task window of `"start_at": "...T00:00:00Z", "end_at": "...T23:59:59Z", "boundary": "inclusive"` means both endpoints are included.
- **Over-counting distinct entities**: When the denominator is distinct orders but a JOIN with shipments multiplies rows, use `COUNT(DISTINCT order_id)` or deduplicate client-side.
- **Currency mismatch**: Always convert to USD through `fx_rates` before comparing or summing monetary values from different currencies.
- **Template violation**: Adding an extra field, omitting a required field, or violating a `pattern` or `enum` constraint will fail. Check every constraint in the template before writing.
- **Transaction scope creep**: A correction transaction must touch exactly the identified row and column. Broader updates or side-effect mutations violate the approved minimal scope.
- **Clock basis**: When the request specifies a clock basis like `SUPPORT_ACTIVE_TIME`, find the matching column in the data dictionary rather than using a generic timestamp column. The dictionary will name the exact field.
- **Rate denominators**: The request always states what the denominator is. For overall rates it's typically the eligible population count. For regional rates it's the regional eligible count. Read the request carefully rather than reusing the overall denominator.
