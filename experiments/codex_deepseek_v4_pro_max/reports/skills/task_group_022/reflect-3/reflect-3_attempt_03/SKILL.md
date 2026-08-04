## When to use

Use this skill when presented with an operational analytics or data-correction
task that references an Atlas Commerce Operations workplace service, includes
input payloads with business definitions and an answer template, and requires
producing a JSON result conforming to a strict output schema.

## Task anatomy

Every task instance supplies three artifacts:

- **prompt.txt** — natural-language summary of the request and the workplace
  service location (`<TASK_ENV_BASE_URL>`).
- **payloads/*_request.json** — business scope, population eligibility rules,
  metric definitions, rounding policies, status/risk classification rules, and
  correction parameters. This is the authoritative specification.
- **payloads/answer_template.json** — strict JSON Schema for the output. Every
  field, type, constraint (`minimum`, `maximum`, `multipleOf`, `enum`,
  `pattern`, `minItems`, `maxItems`, `uniqueItems`), and ordering rule
  (`ordering`, `order`) must be satisfied exactly.

## Discovery workflow

1. **Explore the schema.** Call `GET /api/schema` to list all tables and
   columns. Call `GET /api/data-dictionary` to learn field meanings, units,
   enumerations, and relationships.
2. **Map business definitions to columns.** For each term in the request JSON
   (e.g. "eligible order", "effective settled refund", "delivered shipment",
   "completed task"), identify the corresponding table columns and filter
   conditions from the data dictionary.
3. **Write focused queries.** Build `SELECT`/`WITH` queries that answer one
   business question at a time. Use the request's time windows, population
   filters, and join keys exactly. Test small queries before combining.
4. **Assemble the answer.** Collect results into the answer-template shape,
   apply rounding and ordering rules from the request, and validate against
   every constraint in the template.

## Query and transaction endpoints

- `POST /api/sql` — read-only analysis. Body: `{"sql": "<query>", "params":
  [...]}`. Use for all analytical work (counts, rates, rankings, anomaly
  detection).
- `POST /api/sql/transaction` — guarded writes. Body: `{"statements": [...],
  "expected_total_changes": N}`. Only use when the task explicitly requires a
  data correction. Statements are limited to `SELECT`/`WITH` queries and
  guarded `UPDATE`/`INSERT` on `carrier_scans`, `inventory_movements`, or
  `correction_audit`.
- `GET /api/correction-audit` — verify that a correction was recorded
  correctly.

All `/api/` endpoints require `Authorization: Bearer <token>` and
`Content-Type: application/json`.

## Reading the business request

The request JSON is the single source of truth. Extract these elements
systematically:

- **Scope / cohort.** Which rows qualify? Look for `campaign_id`,
  `account_tier`, `warehouse_id`, `regions`, `segment`, and time-window
  fields (`cutoff_at`, `as_of_cutoff`, `task_created_window`,
  `case_opened_window`, `effective_refund_service_date`). Note boundary
  semantics (`inclusive` vs. exclusive).
- **Metric definitions.** How is each count or rate computed? The request
  defines terms like "complete order", "on time", "severe exception",
  "leakage candidate", "backlog", "breach" — translate these into `WHERE`
  and `CASE` logic.
- **Rounding.** Look for `rounding`, `decimal_places`, `multipleOf`,
  `net_refund_display_decimals`. Apply rounding only to final reported values,
  not intermediate calculations.
- **Ranking / ordering.** Requests specify sort keys and directions (e.g.
  "units_per_hour descending, employee_id ascending"). Use `ORDER BY` clauses
  that match exactly, then apply `LIMIT`.
- **Classification rules.** Status/risk rules appear as ordered lists of
  conditions (e.g. `status_rules`, `facility_status_rules`,
  `cohort_risk_policy`, `support_risk_policy`). Evaluate in the given order;
  the first matching condition wins. When a catch-all is labeled "otherwise"
  or "All other outcomes", it is the fallback.

## Common output-field patterns

- **Count fields** — non-negative integers. Name often ends in `_count`.
- **Rate fields** — decimals in [0, 1], typically rounded to 4 decimal places
  (`multipleOf: 0.0001`). Name often ends in `_rate`.
- **Monetary fields** — numbers rounded to 2 decimal places. Include unit
  label (USD) when specified.
- **Enum status/risk** — string from a fixed set. Apply the request's
  classification rules in order.
- **ID arrays** — sorted as specified (ascending or by a composite key).
  Items must be unique and match the given `pattern` regex.
- **Ranked arrays** — sorted by explicit criteria in the request. When a
  limit is specified (e.g. top 3, worst 2), apply `LIMIT` after sorting.
- **Nested objects** — use the exact required property names. The template
  schema declares `required` and `additionalProperties: false` for each
  nested level.

## Task-type guidance

### Scorecard / productivity review

Count an eligible population in a time window, then subdivide by business
status (complete vs. incomplete, on-time vs. late). Compute aggregate rates,
segment by a grouping column (region, team), rank the segments, and classify
an overall status from ordered rules.

Key pitfalls: incomplete items must remain in rate denominators. Empty
populations may force zero rates and worst-case status.

### Financial reconciliation

Join monetary facts (refunds, reversals, order gross) across tables. Apply FX
conversion using daily rates keyed by service date and currency. Compute net
amounts per order, identify leakage candidates from business rules, rank
reason codes by net exposure, and classify cohort risk from rate and
absolute-value thresholds.

Key pitfalls: reversals reduce net refunds. FX rates are date-specific.
Leakage candidates are a subset of eligible orders.

### Data correction

Identify exactly one row with a canonical-value contradiction. Capture pre-
correction state. Execute a guarded update through the transaction endpoint
changing only the canonical field. Insert an audit row with all required
columns. Verify post-correction state. Compute backlog before and after.

Key pitfalls: the mutation must affect exactly one business row and one audit
row. The audit record must include every column listed in the template.
`APPLIED` requires both commit success and post-change verification.

### SLA health review

Filter cases by open window and account scope. Compute active elapsed time at
cutoff. Compare against per-priority SLA thresholds for first-response and
resolution. Identify severe cases, rank worst accounts by severity and breach
count, compute median resolution time for resolved cases, and classify overall
risk from rate thresholds.

Key pitfalls: active (unresolved) cases use elapsed time at cutoff for breach
determination. Reopened cases are a subset of open-at-cutoff. Median of an
even-length set is the average of the two central values.

## Validation checklist

Before finalizing the answer:

- [ ] Every `required` field in the template is present.
- [ ] No `additionalProperties` beyond what the template declares.
- [ ] Integer fields are whole numbers (no fractional part).
- [ ] Rate fields satisfy `minimum`, `maximum`, and `multipleOf`.
- [ ] Enum fields use only allowed values, with correct casing.
- [ ] Array fields have correct `minItems`/`maxItems` length.
- [ ] Array items are unique and sorted in the specified order.
- [ ] ID strings match the required `pattern` regex.
- [ ] Nested objects include all their `required` sub-fields.
- [ ] Rounding is applied per-request, only to final values.
- [ ] Status/risk classification follows the ordered rule list.
