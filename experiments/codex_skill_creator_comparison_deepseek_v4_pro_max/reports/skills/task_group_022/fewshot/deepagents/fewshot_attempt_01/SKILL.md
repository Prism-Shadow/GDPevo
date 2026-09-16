---
name: atlas-ops-analyst
description: Operational analytics against the Atlas Commerce Operations REST API. Query read-only business data, apply controlled canonical corrections, and verify audit trails. Use when the task environment provides an Atlas API base URL with /api/schema, /api/data-dictionary, /api/sql, /api/sql/transaction, or /api/correction-audit endpoints and the prompt involves querying or correcting a shared commerce database spanning orders, shipments, refunds, payments, carrier scans, support cases, warehouse work, inventory, campaigns, accounts, products, FX rates, or facilities.
---

# Atlas Ops Analyst

## API Endpoints

All endpoints live under the base URL provided in the task environment. Every call uses the `Authorization: Bearer <token>` header from the task environment. The API returns JSON.

- `GET /api/schema` -- Full DDL for every table and index. The response contains `tables` (each with `name` and `ddl`) and `indexes`.
- `GET /api/data-dictionary` -- Column descriptions, conventions (timestamps, dates, money), and production-exclusion flags. The response contains `conventions` and `tables` with per-column `name`, `type`, `nullable`, and `description`.
- `POST /api/sql` -- Read-only SQL. Send a JSON body with `{"query": "<SQL text>"}`. Returns a `rows` array of objects and `row_count`. Accepts only SELECT statements.
- `POST /api/sql/transaction` -- Controlled write. Send `{"transaction": "<SQL text>"}`. The SQL may include UPDATE statements that modify canonical fields on specific tables (carrier_scans, inventory_movements). Returns `{"affected_business_rows": N, "audit_rows": N}`.
- `GET /api/correction-audit` -- Returns all correction audit records. The response contains `columns` (field names) and `rows` (array of arrays). Use this to verify a correction after applying it.

## Workflow

Every analytical task follows this sequence:

1. Call `GET /api/schema` and `GET /api/data-dictionary` to learn the tables, columns, and conventions. Always read both before writing any SQL.
2. Read the business request JSON (the payload with request_id, scope, definitions, and rules). Every operational definition and calculation rule lives there.
3. Write progressive SQL queries against `POST /api/sql`. Start with the cohort query to understand row counts, then layer in metrics. Use the SQL conventions below.
4. Compute derived metrics (rates, rankings, classifications) from query results. Apply rounding and ordering rules exactly as the request specifies.
5. For correction tasks only: identify the contradiction, call `POST /api/sql/transaction` with a single UPDATE, then call `GET /api/correction-audit` to confirm.
6. Assemble the final JSON object matching the answer template and output it to `answer.json`.

## SQL Conventions

### Timestamps and Dates

All stored timestamps use ISO-8601 UTC text ending in `Z`. Calendar dates use `YYYY-MM-DD` text. When comparing against a cutoff, use string comparison (`<= '2026-04-15T23:59:59Z'`). Date ranges are inclusive on both ends unless the request says otherwise. The schema DDL shows `NOT NULL` on timestamp columns that are never null; `TEXT` columns that can be null are marked nullable in the data dictionary.

### Deduplication

Tables that receive imported or replayed events carry a `source_system` + `external_event_id` pair. Always deduplicate with a window function:

```sql
SELECT * FROM (
  SELECT t.*, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at ASC
  ) AS rn
  FROM <table> t
  WHERE <scope filters>
) WHERE rn = 1
```

Tables that need deduplication: `carrier_scans`, `case_events`, `order_events`, `payment_events`, `refund_attempts`, `warehouse_task_events`, `inventory_movements`.

### Append-Only Event Reconstruction

Event tables (`order_events`, `case_events`, `warehouse_task_events`) are append-only. The current state of an entity is the latest event by `event_at` (and then by `event_id` or `case_event_id` for ties). Use window functions to find the last event per entity:

```sql
SELECT * FROM (
  SELECT e.*, ROW_NUMBER() OVER (
    PARTITION BY entity_id ORDER BY event_at DESC, event_id DESC
  ) AS rn
  FROM deduplicated_events e
) WHERE rn = 1
```

For `carrier_scans`, effective ordering uses `canonical_event_at` and `scan_row_id`.

### Money and FX

Monetary fields ending in `_minor` are in the smallest unit of the row currency (e.g., cents for USD). To convert to USD:

```sql
(amount_minor / 100.0) * fx.usd_per_unit AS amount_usd
```

Join `fx_rates` on `rate_date` matching the transaction's `service_date` or `event_at` date, and on `currency`. The `usd_per_unit` column is USD per one unit of the named currency.

### Production Scope

Most requests target production data. Filter out test and internal records:
- `accounts.is_internal = 0` and `accounts.is_test = 0`
- `warehouse_tasks.work_class = 'PRODUCTION'` (training tasks are excluded)

### Effective Final Status for Shipments

For carrier scans, the effective final status per shipment is the latest scan by `canonical_event_at` (then `scan_row_id`). Use this pattern to determine if a shipment is delivered:

```sql
SELECT shipment_id, canonical_status FROM (
  SELECT cs.*, ROW_NUMBER() OVER (
    PARTITION BY shipment_id ORDER BY canonical_event_at DESC, scan_row_id DESC
  ) AS rn
  FROM (deduplicated carrier_scans) cs
) WHERE rn = 1
```

## Correction Workflow

When a task requires a canonical correction:

1. Identify the contradiction. Look for rows where `raw_status` does not match `canonical_status` for the same entity, or where a source-import batch has conflicting values. The request will define the specific batch and facility scope.
2. Write the UPDATE as a single-statement transaction targeting exactly one row. The call goes to `POST /api/sql/transaction`:
   ```json
   {"transaction": "UPDATE carrier_scans SET canonical_status = '<new>', corrected_at = '<timestamp>', correction_reason = '<reason>' WHERE scan_row_id = '<id>'"}
   ```
3. Verify the mutation result has `affected_business_rows: 1` and `audit_rows: 1`.
4. Call `GET /api/correction-audit` and find the matching audit record by `correction_key` or `source_row_id`.
5. Run a post-correction query to confirm the canonical value changed.
6. Compute pre- and post-correction metrics (e.g., backlog counts) using the cutoff.

## Schema Reference

The full schema with table descriptions, column details, key relationships, and index usage is in [references/schema.md](references/schema.md). Read it after discovering the API schema and data dictionary to get a consolidated view of how tables connect.

## Output Conventions

- Write exactly one JSON object to `answer.json` matching the answer template schema.
- No commentary, explanation, or extra fields outside the JSON.
- Round only final reported rates to the specified number of decimal places. Keep intermediate values unrounded for ranking and comparison.
- For even-length median: average the two central values.
- Use `APPLIED` / `NOT_APPLIED` as defined in the correction request for mutation tasks.

## Common Analysis Patterns

### Fulfillment Scorecards

Scope orders by campaign and creation window. Join shipments to get per-order delivery state. Use carrier_scans (deduplicated, effective-final) to determine whether every shipment delivered. An order is complete only when it has at least one shipment and all shipments are delivered by the cutoff. On-time means every shipment delivered on or before its `promised_delivery_at`. Warehouse region comes from the order's warehouse. Severe exceptions apply the 24-hour-over-promise rule.

### Refund Reconciliation

Scope settled refunds by account tier, account type (production), and service-date range. An effective settled logical refund is a deduplicated refund_attempts row with `status = 'SETTLED'` and no linked reversal (check `linked_refund_id IS NULL` on the same refund_id in a self-join, or scan `payment_events` with `linked_event_id` for reversals). Convert amounts to USD via `fx_rates`. Leakage candidates: orders where net refund USD exceeds order gross USD, or orders with two or more unreversed settled refunds sharing the same reason code.

### Warehouse Productivity

Scope production-class tasks created in a window at a specific warehouse. Completed units come from `warehouse_task_events` with `event_type = 'COMPLETED'`. Units per hour = (completed units / productive minutes) * 60. Rework is `task_type = 'REWORK'`. Delayed high-priority means `priority IN ('HIGH', 'URGENT')`, `due_at < cutoff`, and not completed by cutoff. Team ranking uses completion rate (completed eligible tasks / eligible tasks).

### Support Health

Scope enterprise production-account cases opened in a window in specific regions. Reconstruct case state from `case_events` (deduplicated, effective-last): `OPEN`, `REOPENED`, `RESOLVED`, `CLOSED`. First-response breach: active time to first agent response exceeds the priority threshold. Resolution breach: active time to resolution exceeds the priority threshold. Unresponded or unresolved cases use elapsed time at cutoff. Severe active: open/reopened, priority URGENT or HIGH, and beyond resolution threshold. Median resolution time uses resolved cases only.

### Carrier Quality Corrections

Scope one import batch at one warehouse. Find the raw/canonical contradiction: any scan where `raw_status` != `canonical_status` within that batch. The canonical value should match the raw value for the contradiction. Backlog: shipments whose effective final canonical status is not `DELIVERED` at the cutoff. Correction status `APPLIED` only when exactly one business row and one audit row commit and a post-query confirms the change.
