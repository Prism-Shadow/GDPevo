---
name: atlas-ops
description: Operational analytics and data-quality correction workflows against the Atlas Commerce Operations database. Use this skill whenever the user needs to query fulfillment, refund, carrier, warehouse, support, or financial records from the Atlas workplace, run SQL analysis, apply controlled canonical corrections, compute business metrics from raw event data, or produce operational scorecards from the Atlas schema. Trigger on mentions of Atlas, commerce operations, operational analytics, fulfillment scorecards, refund reconciliation, carrier quality review, warehouse productivity, support health, shipping data, payment/settlement data, or any request that references an authenticated workplace SQL/transaction service.
---

# Atlas Commerce Operations

Authenticated operational analytics, reconciliation, and controlled data correction for the Atlas Commerce Operations database. The workplace runs a read-only SQL query service, a controlled SQL transaction endpoint, and an audit view. All business data lives in ISO-8601 UTC timestamps, monetary minor units, and append-only event tables with canonical as well as raw fields.

## Connection

Every request to the Atlas API must use:

- **Base URL**: the value of `<TASK_ENV_BASE_URL>` from the task prompt, defaulting to `http://task-env:9022/`
- **Authorization header**: `Authorization: Bearer atlas-ops-token-022`

Allowed endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/schema` | Table DDL, indexes, foreign keys |
| GET | `/api/data-dictionary` | Column descriptions, conventions |
| POST | `/api/sql` | Read-only analytical SQL queries |
| POST | `/api/sql/transaction` | Controlled single-statement mutations |
| GET | `/api/correction-audit` | Public audit records |

The SQL endpoint returns JSON with `columns`, `rows`, `row_count`, and `truncated`.

The transaction endpoint expects a JSON body with a single SQL statement and returns affected-row counts.

## Discovery Workflow

When approaching an unfamiliar Atlas task, work in this order every time:

1. **Fetch the schema** (`GET /api/schema`) to learn table structures, foreign keys, and indexes.
2. **Fetch the data dictionary** (`GET /api/data-dictionary`) to understand column meanings, conventions (timestamps, money, source vs canonical), and business semantics.
3. **Explore with small queries** — check distinct values for enums (`event_type`, `status`, `priority`, `segment`, `region`), spot row counts, and verify assumptions before writing the big query.
4. **Read the request payload thoroughly** — the business definitions, cutoffs, rounding rules, SLAs, and classification policies embedded in the request JSON are authoritative over any general pattern in this skill.

## Deduplication

Every event table (`carrier_scans`, `order_events`, `payment_events`, `refund_attempts`, `warehouse_task_events`, `case_events`, `inventory_movements`) can contain import-retry duplicates. The schema indexes confirm the deduplication key is `(source_system, external_event_id)` and the tiebreak is `MAX(ingested_at)`.

For any event table, wrap the query in a deduplication subquery:

```sql
SELECT ... FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at DESC
  ) AS rn
  FROM <table>
) WHERE rn = 1
```

Alternatively, use `GROUP BY source_system, external_event_id` with `MAX(ingested_at)` and join back to the table. The window-function approach is preferred because it preserves all columns cleanly.

Never count or aggregate rows from an undeduplicated event table — duplicates inflate counts and break correctness.

## Production Filtering

**Accounts**: Exclude internal and test accounts with `is_internal = 0 AND is_test = 0`. The data dictionary confirms 0 means false for integer booleans.

**Warehouse tasks**: Filter to production work with `work_class = 'PRODUCTION'`.

Always apply these filters before applying any task-specific cohort scoping.

## Money and Currency

- Monetary fields (`amount_minor`, `gross_amount_minor`) store values in the smallest unit of the row's `currency` column.
- Convert to USD using the `fx_rates` table: join on `rate_date` (use the service date or event date) and `currency`, then multiply `amount_minor * usd_per_unit / 100.0` (or the appropriate minor-unit divisor) to get USD.
- For order gross comparison, use the order's own `currency` and the refund's `service_date` rate.
- Report final USD amounts with 2 decimal places unless the request specifies otherwise.

## Order Fulfillment Analytics

Orders are the central entity. Key relationships:

- `orders` → `accounts` (via `account_id`): account segment, tier, region
- `orders` → `warehouses` (via `warehouse_id`): facility region, timezone, cutoff
- `orders` → `campaigns` (via `campaign_id`): campaign active window
- `orders` → `shipments` (via `order_id`): physical delivery tracking
- `shipments` → `carrier_scans` (via `shipment_id`): carrier scan events
- `orders` → `order_events` (via `order_id`): order lifecycle events

**Effective shipment delivery status**: Derive from the deduplicated `carrier_scans` table, not from `shipments.current_status` (which may lag). Group scans by `shipment_id`, take the latest by `canonical_event_at`, and use that row's `canonical_status` as the effective delivery state. A shipment is DELIVERED when its latest canonical_status is `DELIVERED`.

**On-time delivery**: A delivered shipment is on time when its latest scan's `canonical_event_at` <= the shipment's `promised_delivery_at`.

**Severe exceptions**: Identify orders that are incomplete with cutoff past the latest promise by >24h, or completed with any shipment delivered >24h past its promise.

## Refund Reconciliation

- `refund_attempts` contains provider refund attempts linked to orders. Status values: `SETTLED`, `FAILED`, `VOIDED`, `REVERSED`.
- A **logical refund** is a distinct `refund_id`. An **effective settled logical refund** is one where at least one row for that `refund_id` has `status = 'SETTLED'`.
- **Linked reversals**: A refund row where `status = 'REVERSED'` and `linked_refund_id` points to another settled `refund_id`. The reversal offsets the original refund's value.
- **Net refund amount**: Sum settled refund amounts minus reversal amounts, all converted to USD.
- **Leakage detection**: For each order, compare effective net refund USD against the order's gross amount in USD (converted at the refund service date rate). Also check for multiple unreversed settled refunds with the same `reason_code` on the same order.
- **Reason ranking**: Group by `reason_code`, sum net refund USD per code, rank descending by USD then ascending by code.

## Carrier Quality Corrections

When the task involves finding and fixing a raw/canonical contradiction in `carrier_scans`:

1. Query scans where `raw_status != canonical_status` within the scoped batch and warehouse cohort.
2. Identify the single contradiction the request targets (the request payload specifies exactly one exists).
3. Verify the correction target: raw status is correct, canonical should match it.
4. **Backlog analysis**: A shipment is in backlog when its effective final carrier status (latest canonical status by `canonical_event_at`) is not `DELIVERED`. Count the pre-correction backlog, then simulate (or apply and count) the post-correction backlog.

**Applying a correction** via `POST /api/sql/transaction`:

```sql
UPDATE carrier_scans
SET canonical_status = '<new_value>',
    corrected_at = '<timestamp>',
    correction_reason = '<reason>'
WHERE scan_row_id = '<row_id>'
```

The transaction endpoint returns `affected_business_rows`. Then verify with a read query.

**Audit records**: After a correction, query `GET /api/correction-audit` for the matching `correction_key`. The audit is appended automatically by the transaction.

**Correction status**: Report `APPLIED` only when exactly 1 business row was mutated, exactly 1 audit row exists, and a post-correction read confirms the new canonical value.

## Warehouse Productivity

- `warehouse_tasks` defines planned work (task type, priority, work class, assigned employee, planned units, created/due dates).
- `warehouse_task_events` records execution events for those tasks.
- Task scoping: filter by `created_at` in the request window, `warehouse_id`, and `work_class = 'PRODUCTION'`.

**Completion**: A task is completed when it has at least one `COMPLETED` event (after dedup). Use `SUM(units)` from the latest completion event per task for completed units.

**Rework**: A task with a `REWORK` event is a rework task.

**Productive minutes**: From the task events, sum `productive_minutes` for completed tasks.

**Units per hour**: For each employee, `SUM(units) / SUM(productive_minutes) * 60` from completed production task events.

**Delayed high-priority tasks**: Tasks with `priority IN ('HIGH', 'URGENT')` where `due_at` < cutoff and the task is not completed.

**Team performance**: Group by `team_id` (from employees table), compute completion rate per team, rank ascending.

## Support Health

- `support_cases` holds case headers with priority, open time, current status.
- `case_events` holds the append-only lifecycle events for each case.

**Active time computation** (clock basis: SUPPORT_ACTIVE_TIME): Active time is elapsed time minus time spent in `WAITING_CUSTOMER` state. Track the timeline: OPENED starts the clock, WAITING_CUSTOMER pauses it, CUSTOMER_REPLIED resumes it, RESOLVED stops it. For each WAITING_CUSTOMER interval, subtract its duration from the total elapsed time.

**First response**: Active time from OPENED to the first `AGENT_RESPONDED` event. If no agent response exists by the cutoff, use active elapsed time to cutoff.

**Resolution time**: Active time from OPENED to RESOLVED. If unresolved at cutoff, use active elapsed time to cutoff for breach detection.

**Breach detection**: Compare first-response active time and resolution active time against the priority's SLA thresholds from the request.

**Severe active cases**: Cases open or reopened at cutoff, priority URGENT or HIGH, and beyond the resolution active-time SLA threshold.

**Median**: For an even count, average the two central values. Round to 2 decimal places as specified.

**Status at cutoff**: Derive effective status from the latest event per case by `event_at`, not from `support_cases.current_status` (which may lag). OPEN, REOPENED → active/open; RESOLVED → resolved.

## Output Formatting

Every Atlas task requires the answer as one JSON object conforming to a template:

1. Read the `input/payloads/answer_template.json` to understand required fields, types, ranges, and ordering constraints.
2. Compute all values according to the business definitions in the request payload.
3. Round floating-point values only at the final reported output, using the decimal places specified in the template or request (typically 2 or 4).
4. Sort arrays exactly as the template or request specifies (typically ascending by natural sort order for IDs, descending for ranked metrics then ascending for tiebreaks).
5. Write the JSON to `answer.json` with no commentary or additional fields outside the JSON document.
6. Use `APPLIED` / `NOT_APPLIED` for correction status, facility status enums, and risk classification enums exactly as defined in the request payloads.

## Reference Files

For the full schema DDL, indexes, and column-level data dictionary, read these whenever a task needs precise column types or relationship details:

- [schema.md](references/schema.md) — complete table DDL and index definitions
- [data-dictionary.md](references/data-dictionary.md) — column descriptions, conventions, and domain semantics

Load the appropriate reference when the task involves a table you have not yet queried or when you need to understand specific column semantics like dedup keys, nullable behavior, or the meaning of a status/enum value.
