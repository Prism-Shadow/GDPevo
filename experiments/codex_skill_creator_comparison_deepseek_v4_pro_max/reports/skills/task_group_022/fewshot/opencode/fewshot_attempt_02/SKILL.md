---
name: atlas-ops-api
description: Analyze the Atlas Commerce Operations database through its REST API. Use this skill whenever the user mentions Atlas, the workplace service, task-env, /api/schema, /api/data-dictionary, /api/sql, /api/sql/transaction, /api/correction-audit, fulfillment scorecards, refund reconciliation, carrier quality reviews, warehouse productivity, support health reviews, or any business-analytical task that requires querying the Atlas Commerce Operations schema. Also use it when the user asks about production orders, shipments, carrier scans, payment events, refund attempts, support cases, warehouse tasks, inventory movements, or campaign-attributed analytics.
---

# Atlas Commerce Operations API

Analyze business data from the Atlas Commerce Operations workplace through its
documented REST API. The service exposes a read-only SQL interface, a controlled
correction mechanism, and discovery endpoints for schema and field definitions.

## API Endpoints

Base URL is provided in the task prompt as `<TASK_ENV_BASE_URL>`.

All business endpoints share one authorization header:

```
Authorization: Bearer atlas-ops-token-022
```

| Method | Path                 | Purpose                                      |
|--------|----------------------|----------------------------------------------|
| GET    | /api/schema          | Full DDL for every table and index            |
| GET    | /api/data-dictionary | Column-level descriptions and conventions     |
| POST   | /api/sql             | Read-only SQL queries (SELECT only)           |
| POST   | /api/sql/transaction | Controlled single-row canonical correction    |
| GET    | /api/correction-audit| Read audit records for applied corrections    |

`POST /api/sql` accepts a JSON body with a `sql` string field. The query must be
a single SELECT statement. Returned rows are JSON arrays of objects.

`POST /api/sql/transaction` accepts a JSON body describing exactly one canonical
correction. It commits atomically: one business-row update plus one audit-row
insert, or nothing. The response reports `affected_business_rows` and
`audit_rows`.

`GET /api/correction-audit` filters on `correction_key` (query parameter) to
verify that a correction audit record was created.

## Workflow

Follow this sequence for every analytical task served by this API:

1. **Read the request payload and answer template.** The request defines scope,
   business definitions, and output rules. The answer template is a JSON Schema
   that constrains the exact shape of the output. Every required field must be
   present; every constraint (type, enum, minItems, pattern, multipleOf) must
   be satisfied.

2. **Discover the schema.** Call `GET /api/schema` and `GET /api/data-dictionary`
   to understand available tables, columns, relationships, and conventions.
   The schema describes foreign-key links, index coverage, and nullable
   columns. The data dictionary explains column meanings, unit conventions,
   and the deduplication strategy.

3. **Query in stages.** Build SQL queries incrementally rather than trying to
   answer everything in one enormous query. Start by scoping the eligible
   population, then join in detail tables. Use CTEs (WITH clauses) to keep
   complex queries readable and debuggable.

4. **Apply business rules in SQL where possible.** Filtering, classification,
   ranking, and aggregation should happen in the database. Reserve
   post-processing only for operations SQL cannot express cleanly.

5. **Validate the output.** Before writing `answer.json`, check every required
   field against the template. Verify counts are consistent (e.g., complete +
   incomplete = eligible). Confirm ordering rules, rounding rules, and enum
   values.

## Database Conventions

These conventions apply across all tables in the Atlas schema. Understand them
before writing any query.

### Deduplication

Source systems may re-send the same event on import retries. Every import table
carries `(source_system, external_event_id, ingested_at)` as its deduplication
key. **Always** use this pattern to select the effective row:

```sql
WITH dedup AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at DESC
  ) AS rn
  FROM some_import_table
)
SELECT ... FROM dedup WHERE rn = 1
```

The import tables that require deduplication: `carrier_scans`, `case_events`,
`inventory_movements`, `order_events`, `payment_events`, `refund_attempts`,
`warehouse_task_events`.

Master-data tables (`accounts`, `campaigns`, `employees`, `products`,
`warehouses`) and header tables (`orders`, `shipments`, `support_cases`,
`warehouse_tasks`) do not require deduplication; their primary key is already
stable.

### Effective Event State

Append-only event tables track lifecycle state. For each tracked entity, the
**effective state** at a given point in time is determined by the latest event
before or at the cutoff.

For `carrier_scans`: the effective scan for a shipment is the latest deduplicated
scan ordered by `canonical_event_at`. The effective carrier status of a shipment
comes from that scan's `canonical_status`.

For `order_events`, `case_events`, and `warehouse_task_events`: use the latest
deduplicated event per tracked entity ordered by `event_at`.

The convenience `current_status` columns on header tables (`orders`,
`shipments`, `support_cases`, `warehouse_tasks`) are denormalized snapshots that
may lag event history. When a task specifies a cutoff, derive effective state
from the event tables, not from `current_status`.

### Timestamps

All stored timestamps use ISO-8601 UTC text ending in `Z`
(e.g., `2026-04-15T23:59:59Z`). Compare timestamps lexicographically in SQL;
the format is sortable.

Calendar-date columns (such as `fx_rates.rate_date` and
`refund_attempts.service_date`) use `YYYY-MM-DD` text.

When a task specifies inclusive boundaries, use `>=` and `<=`. Use `<` only
when a boundary is explicitly exclusive.

### Money

Monetary amounts are stored as integers in the smallest unit of the row's
currency column (`amount_minor`, `gross_amount_minor`). Divide by 100 to get
major-unit values for most currencies.

Foreign exchange uses the `fx_rates` table. Each row gives `usd_per_unit` for a
`(rate_date, currency)` pair. To convert a minor-unit amount to USD:

```
(amount_minor / 100.0) * fx.usd_per_unit
```

For `refund_attempts`, match `service_date` (a date) to `fx_rates.rate_date`.
For `payment_events`, match `DATE(event_at)` to `fx_rates.rate_date`.

### Integer Booleans

Columns named `is_*` use INTEGER `0` (false) and `1` (true). Filter with
`= 0` or `= 1`, never with boolean literals.

### Production Filtering

When a task scopes to "production" accounts, exclude `is_internal = 1` and
`is_test = 1` from the `accounts` table. Apply additional filters on
`segment`, `tier`, and `region` as the request specifies.

For warehouse work, filter on `work_class = 'PRODUCTION'` (exclude
`'TRAINING'`).

## Domain Patterns

Each domain has recurring table relationships, filter criteria, and ranking
rules. Use these patterns as starting points and adapt to the specific request.

### Fulfillment Scorecards

Tables: `orders`, `shipments`, `carrier_scans`, `campaigns`, `warehouses`,
`accounts`.

Eligible orders are scoped by campaign (join `orders.campaign_id` to
`campaigns.campaign_id` and filter `order_created_at` within the campaign
active window) or by other cohort criteria in the request.

An order is complete when every associated shipment is effectively DELIVERED by
the cutoff. First find the effective carrier status per shipment using the
deduplicated `carrier_scans` table (latest scan by `canonical_event_at`). An
order with no shipments is incomplete.

An on-time complete order requires every shipment's effective delivery timestamp
to be on or before that shipment's `promised_delivery_at`.

Regional rollups join `orders.warehouse_id` to `warehouses.warehouse_id` and
group by `warehouses.region`.

Ranking rules typically use the unrounded rate before rounding the reported
value.

### Refund Reconciliation

Tables: `refund_attempts` (deduplicated), `orders`, `accounts`, `fx_rates`,
linked reversals via `refund_attempts.linked_refund_id`.

A settled logical refund is a deduplicated `refund_attempts` row with
`status = 'SETTLED'`. A reversal is a settled refund whose `refund_id` appears
as `linked_refund_id` on another settled refund.

The effective settled value in USD for a refund: `(amount_minor / 100.0) *
fx.usd_per_unit` using the `service_date` as the rate date and the refund's
`currency` as the FX currency. Net refund per order subtracts linked reversals.

Leakage candidates are identified by comparing net refund USD to the order's
gross value in USD (convert `gross_amount_minor` at the same rate date), and by
detecting duplicate same-reason-code refunds.

Reason-code ranking uses net refund USD descending with normalized reason code
ascending as tiebreaker.

### Carrier Quality Correction

Tables: `carrier_scans` (deduplicated), `shipments`, `source_import_batches`,
`correction_audit`, `orders`, `accounts`.

Scope to a specific `import_batch_id` and `warehouse_id`. The effective scan for
each shipment is the latest deduplicated scan (by `canonical_event_at`).

A **canonical contradiction** exists when the effective canonical status for a
shipment contradicts the raw status of the source scan, or when a single scan
row is identified as needing canonical correction per the request scope.

The correction is applied via `POST /api/sql/transaction` targeting one
`scan_row_id` and one `canonical_status` field. After the transaction, verify by
querying the corrected row and by checking `GET /api/correction-audit` for the
`correction_key`.

Backlog counts shipments whose effective final carrier status is not DELIVERED.
Pre-correction backlog uses current canonical values; post-correction backlog
reflects the applied change. Backlog delta is post minus pre.

### Warehouse Productivity

Tables: `warehouse_tasks`, `warehouse_task_events` (deduplicated), `employees`,
`warehouses`.

Eligible tasks are scoped by `warehouse_id`, `work_class = 'PRODUCTION'`,
`created_at` within the window, and `task_type` (if the request filters on
type). Tasks are not filtered by their current status for eligibility; the
cutoff determines completion state.

Completion is determined by the effective task state from deduplicated
`warehouse_task_events`: a task is complete if a COMPLETED event exists at or
before the state cutoff. Sum `units` from COMPLETED events for completed
production units; sum `productive_minutes` from COMPLETED events for
productivity calculations.

Units per hour: `(total_completed_units / total_productive_minutes) * 60`.

Rework tasks are those with `task_type = 'REWORK'`. The rework rate uses
eligible production tasks as denominator.

A delayed high-priority task has `priority IN ('HIGH', 'URGENT')`, `due_at`
strictly before the state cutoff, and is not completed by the cutoff.

Employee ranking: units per hour descending, employee_id ascending.
Team ranking: completion rate ascending, team_id ascending.

### Support Health Review

Tables: `support_cases`, `case_events` (deduplicated), `accounts`,
`orders` (optional).

Eligible cases are scoped by account segment/tier/region (join `accounts`),
`opened_at` within the case-opened window, and production-account filtering
(`is_internal = 0`, `is_test = 0`).

Case state at cutoff is determined from deduplicated `case_events`, not from
`support_cases.current_status`. A case is open at cutoff if its latest event
before cutoff has `event_type` in `('OPEN', 'REOPEN')`. It is reopened if the
latest event is specifically `'REOPEN'`. It is resolved if the latest event is
`'RESOLVED'`.

**Active time** is measured by support-active clock hours between `opened_at`
and resolution. For a case that was reopened, the reopened-to-resolution gap
counts as additional active time. Use the event timestamps from deduplicated
`case_events` to compute these spans.

First response: the earliest deduplicated `case_events` row where
`event_type = 'RESPONSE'` and `actor_type = 'AGENT'`. The active time to first
response is the difference between that event's `event_at` and the case
`opened_at`. An unresponded case uses elapsed active time at the cutoff.

Resolution: a case resolved at cutoff has a deduplicated RESOLVED event.
Active time to resolution is computed from `opened_at` through resolution,
accounting for any reopen gaps.

**SLA breach**: For each case, compare first-response active time and
resolution active time against the priority-specific thresholds defined in the
request. An active unresolved/unresponded case at cutoff uses elapsed active
time at the cutoff for breach determination.

**Severe active case**: OPEN or REOPENED at cutoff with priority URGENT or
HIGH, beyond the active-time resolution threshold for its priority.

**Worst accounts**: Rank by severe active case count descending, active-clock
breach count descending, account_id ascending.

**Median**: For resolved cases, compute active resolution hours, sort, and take
the median. For an even count, average the two central values.

## Output Validation

Before writing `answer.json`, verify:

- All `required` fields from the answer template are present.
- No `additionalProperties` beyond those in the template.
- Integer fields are whole numbers (no fractional parts).
- Number fields match their `multipleOf` and `minimum`/`maximum` constraints.
- Array fields respect `minItems`, `maxItems`, and `uniqueItems`.
- String fields match their `pattern` regex.
- Enum fields contain only allowed values.
- Ordering rules (ascending/descending, primary/secondary sort keys) are
  followed precisely.

When the answer template defines ordering inline, respect every sort key in
sequence. When a request defines rounding rules ("round only final reported
rates"), compute with full precision and round only the output values.

## Reference Files

- [references/schemas.md](references/schemas.md): Detailed table relationships,
  deduplication and effective-event SQL patterns with worked examples, and
  currency/FX patterns. Read this when you need precise column-level guidance
  or example queries for a specific domain.
