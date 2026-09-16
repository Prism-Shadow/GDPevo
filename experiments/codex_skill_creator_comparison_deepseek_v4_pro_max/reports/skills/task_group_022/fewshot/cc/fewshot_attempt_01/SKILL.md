---
name: atlas-commerce-ops
description: Solve analytical tasks against the Atlas Commerce Operations database API. Use this skill whenever the user asks you to produce a business report, scorecard, reconciliation, operational health review, or data-quality correction using an Atlas Commerce Operations workplace service. Typical signals include references to a workplace API base URL, bearer token authorization, SQL endpoints, answer templates, or business domains like fulfillment, refund reconciliation, carrier quality, warehouse productivity, or support case health. Trigger even when the user describes the task in domain language without naming the API explicitly.
---

# Atlas Commerce Operations Analytical Skill

This skill describes how to solve analytical and data-correction tasks against the
Atlas Commerce Operations API. The system exposes a read-only SQL endpoint, a
transaction endpoint for controlled corrections, and metadata endpoints for schema
and data-dictionary discovery.

## Connection Setup

Every task provides a base URL and an authorization token. Construct the HTTP
client using these values from the task prompt or environment:

- Base URL: `<TASK_ENV_BASE_URL>` (or explicit URL from user)
- Auth header: `Authorization: Bearer <TOKEN>`

Available endpoints:

| Method | Path                     | Purpose                                 |
|--------|--------------------------|-----------------------------------------|
| GET    | `/api/schema`            | Full DDL and indexes                    |
| GET    | `/api/data-dictionary`   | Column descriptions and conventions     |
| POST   | `/api/sql`               | Read-only analytical queries            |
| POST   | `/api/sql/transaction`   | Controlled mutation for corrections     |
| GET    | `/api/correction-audit`  | Read committed correction audit records |

## Core Workflow

For every task, follow this sequence:

### 1. Read the inputs

Open the task prompt and every file in the payloads directory. Identify:
- The business request with scope, definitions, and rollup rules
- The answer template (JSON Schema) that constrains the output

### 2. Discover the data model

Call `GET /api/schema` and `GET /api/data-dictionary` before writing any SQL.
These return the complete DDL, indexes, and column-level descriptions. Pay
attention to:

- Table relationships (foreign keys are in the DDL)
- Which tables are append-only event streams vs. denormalized headers
- Which columns are raw vs. canonical
- The deduplication indexes present on each import table
- Boolean integer conventions (`is_internal`, `is_test`, `is_active`)

### 3. Write and execute SQL

Use `POST /api/sql`. The request body is:

```json
{"sql": "<query text>"}
```

The response contains `rows` (array of arrays), `columns` (array of names),
and `row_count`.

**Always apply these SQL patterns:**

#### Deduplication of imported event streams

Tables with `source_system`, `external_event_id`, and `ingested_at` columns
are append-only import logs where the same upstream event may appear more than
once on retry. Apply this stable deduplication window for every query:

```sql
SELECT ... FROM carrier_scans cs
WHERE cs.ingested_at = (
  SELECT MIN(cs2.ingested_at)
  FROM carrier_scans cs2
  WHERE cs2.source_system = cs.source_system
    AND cs2.external_event_id = cs.external_event_id
)
```

Use the same pattern for `order_events`, `payment_events`, `refund_attempts`,
`case_events`, `inventory_movements`, and `warehouse_task_events`.

For `refund_attempts`, also apply the `linked_refund_id` chain: a settled
refund's effective net is its own amount minus the amount of any refund row
whose `linked_refund_id` points back to it (reversals). The reversal
rows must also pass deduplication.

#### Production-only filtering

The `accounts` table has `is_internal` and `is_test` integer boolean columns.
When the request mentions "production" scope, always add:

```sql
AND a.is_internal = 0
AND a.is_test   = 0
```

The `warehouse_tasks` table has a `work_class` column. When only production
tasks are needed, add `AND wt.work_class = 'PRODUCTION'`.

#### Effective state from append-only events

Do not rely on denormalized `current_status` columns in `orders`, `shipments`,
or `support_cases` for analytical cutoffs; the data dictionary warns these
"may lag append-only event history." Instead, determine effective state from
the deduplicated event stream at or before the cutoff timestamp.

For carrier_scans, use the effective-final scan per shipment: the deduplicated
row with the latest `canonical_event_at` at or before the cutoff, breaking ties
with the last `scan_row_id` ingested.

#### Timestamp comparisons

All stored timestamps use ISO-8601 UTC text ending in `Z`. Use simple string
comparison (e.g., `event_at <= '2026-04-15T23:59:59Z'`) unless the task
requires calendar-date semantics, in which case use `date()` extraction or
compare only the date prefix.

When the request specifies an inclusive boundary, use `<=` or `>=`.

#### Money and currency

Monetary values are stored in the smallest unit of the row currency
(`amount_minor`, `gross_amount_minor`). To convert to major units, divide by
100 for most currencies. Do not assume 100 for all currencies; always verify
against the currency column.

For USD conversions, join against `fx_rates` on the currency and the
service/event date:

```sql
fx.usd_per_unit * (ra.amount_minor / 100.0)
```

The `fx_rates.rate_date` column stores calendar dates (YYYY-MM-DD), not
timestamps. When joining, extract the date from the timestamp.

### 4. Compute business metrics

Translate every business definition from the request payload into SQL logic.
The request payload is authoritative for:
- Cohort membership rules (which rows are eligible)
- Metric formulas (how rates and counts are computed)
- Rollup groupings (by region, team, account, etc.)
- Ranking and tie-breaking rules
- Status classification thresholds

Apply rounding only at final reporting time, not at intermediate steps.
The request typically specifies rounding precision (e.g., 4 decimal places).

### 5. Handle corrections

When the task requires a data correction, use `POST /api/sql/transaction`.
The body format is:

```json
{
  "statements": ["UPDATE ...", "INSERT INTO correction_audit ..."],
  "audit_id": "<idempotent key>",
  "reason_code": "SOURCE_RECONCILIATION"
}
```

The transaction is atomic: both the business update and the audit insert
succeed or fail together. After applying, verify the correction by querying
the corrected table and the audit endpoint (`GET /api/correction-audit`).

Only correct the minimal canonical field. Never change raw source values,
source identity columns (`source_system`, `external_event_id`), or unrelated
business rows.

If the post-correction verification confirms exactly one business row changed
and one audit row was committed with the expected canonical value, report
`APPLIED`; otherwise report `NOT_APPLIED`.

### 6. Validate and write the answer

After computing results, validate the JSON output against the answer template
schema. The template is a JSON Schema document from the payloads directory.
Check:
- All `required` fields are present
- Types match (`integer`, `number`, `string`, `array`, `object`)
- Integer values are whole numbers (no `.0`)
- Number precision matches the template's `multipleOf` or precision spec
- Array lengths respect `minItems`/`maxItems`
- Enum values match exactly
- Sort orders match the request specification
- String patterns match (e.g., `^ORD-[0-9]{6}$`)

A validation script at [scripts/validate_answer.py](scripts/validate_answer.py)
can check conformance automatically when given the template path and answer path.

Write the final validated JSON to `answer.json` with no commentary outside the
JSON document.

## Database Quick Reference

The full schema and data dictionary are in [references/schema.md](references/schema.md)
and [references/dictionary.md](references/dictionary.md). Key tables:

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `accounts` | Customer master data | `account_id`, `segment`, `tier`, `region`, `currency`, `is_internal`, `is_test` |
| `orders` | Order headers | `order_id`, `account_id`, `campaign_id`, `warehouse_id`, `order_created_at`, `currency`, `gross_amount_minor` |
| `order_lines` | Order SKU quantities | `order_id`, `sku`, `quantity_each` |
| `shipments` | Physical shipments | `shipment_id`, `order_id`, `warehouse_id`, `promised_delivery_at` |
| `carrier_scans` | Carrier tracking events | `scan_row_id`, `shipment_id`, `raw_status`, `canonical_status`, `canonical_event_at`, `import_batch_id` |
| `refund_attempts` | Refund/return events | `refund_row_id`, `refund_id`, `order_id`, `status`, `reason_code`, `amount_minor`, `currency`, `service_date`, `linked_refund_id` |
| `payment_events` | Payment events | `payment_event_id`, `order_id`, `event_type`, `amount_minor`, `currency`, `linked_event_id` |
| `fx_rates` | Daily FX rates | `rate_date`, `currency`, `usd_per_unit` |
| `warehouse_tasks` | Work assignments | `task_id`, `warehouse_id`, `assigned_employee_id`, `task_type`, `work_class`, `priority`, `planned_units`, `created_at`, `due_at` |
| `warehouse_task_events` | Task execution events | `task_event_id`, `task_id`, `event_type`, `units`, `productive_minutes` |
| `support_cases` | Support case headers | `case_id`, `account_id`, `order_id`, `priority`, `opened_at` |
| `case_events` | Case lifecycle events | `case_event_id`, `case_id`, `event_type`, `event_at`, `actor_type` |
| `campaigns` | Marketing campaigns | `campaign_id`, `starts_at`, `ends_at`, `channel` |
| `warehouses` | Fulfillment facilities | `warehouse_id`, `region`, `timezone` |
| `employees` | Warehouse staff | `employee_id`, `warehouse_id`, `team_id`, `role` |
| `correction_audit` | Correction log | `audit_id`, `correction_key`, `entity_type`, `entity_id`, `source_row_id`, `field_name`, `old_value`, `new_value` |
| `products` | SKU master data | `sku`, `product_family`, `unit_weight_grams`, `units_per_case` |

### Event-Type Values

From the five train tasks, observed event types include:

**case_events.event_type**: `OPENED`, `FIRST_AGENT_RESPONSE`, `CLOSED`, `REOPENED`, `NOTE_ADDED`
**warehouse_task_events.event_type**: `PICK_STARTED`, `PICK_COMPLETED`, `NON_PICK_STARTED`, `NON_PICK_COMPLETED`
**order_events.event_type**: `CREATED`, `CONFIRMED`, `ALLOCATED`, `SHIPPED`, `DELIVERED`, `CANCELLED`

When a task references an event type not listed here, inspect the actual data
via SQL to discover available values.

### Status Values

**orders.current_status / order state**: `CREATED`, `CONFIRMED`, `ALLOCATED`, `PARTIALLY_SHIPPED`, `SHIPPED`, `DELIVERED`, `CANCELLED`

**shipments.current_status**: `LABEL_CREATED`, `PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `RETURNED`

**carrier_scans.canonical_status**: `LABEL_CREATED`, `PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `EXCEPTION`

**support_cases.current_status**: `OPEN`, `CLOSED`, `REOPENED`

**warehouse_tasks.current_status**: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`

**refund_attempts.status**: `SETTLED`, `FAILED`, `REVERSED`

**refund_attempts.reason_code**: `DAMAGED`, `NOT_AS_DESCRIBED`, `DEFECTIVE`, `WRONG_ITEM`, `LATE_DELIVERY`, `CUSTOMER_REQUEST`

Again, when a task introduces a new value, verify it exists in the live data.

## Common Pitfalls

1. **Forgetting deduplication on import tables.** Every query against
   `carrier_scans`, `order_events`, `case_events`, `payment_events`,
   `refund_attempts`, `inventory_movements`, or `warehouse_task_events`
   must deduplicate unless the task explicitly asks for raw row counts.

2. **Using denormalized `current_status` for analytical cutoffs.** Use the
   effective event stream instead.

3. **Including internal or test accounts in production reports.** Always
   filter `is_internal = 0 AND is_test = 0` on `accounts` for production scope.

4. **Rounding intermediate values.** Only round final reported numbers.
   Keep intermediate calculations at full precision.

5. **Wrong FX date matching.** `fx_rates.rate_date` is a calendar date; the
   refund/payment `service_date` is also a calendar date. The order
   `order_created_at` or event `event_at` is a full timestamp. Extract the
   date portion when matching against FX rates.

6. **Assuming 100 minor units per currency unit.** Most currencies in the
   system use 100, but always check the currency column and task scope.

7. **Missing the `linked_refund_id` chain.** When a refund row has a non-null
   `linked_refund_id`, it is a reversal of the linked row. The settled refund's
   effective net is its amount minus the sum of its reversals' amounts.

8. **Mixing work_class values in warehouse tasks.** Only `PRODUCTION` tasks
   count for production metrics; `TRAINING` tasks are excluded.

9. **Forgetting to handle even-count medians.** When computing medians and the
   count is even, average the two central values after sorting.

10. **Applying corrections to more than the minimal field.** The request
    always specifies a minimal canonical correction. Do not cascade changes.

## Output Contract

The final answer must be a single JSON object written to `answer.json` in the
working directory. It must:

- Match the exact structure from the answer template
- Contain no extra fields beyond what the template requires
- Have no commentary, markdown fences, or explanatory text outside the JSON
- Use the field names, types, and constraints from the template

Run the validation script before declaring the answer final:

```bash
python /work/skill/scripts/validate_answer.py answer.json input/payloads/answer_template.json
```
