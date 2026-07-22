# Atlas Commerce Operations — Analytical Task Skill

## Overview

This skill covers analytical and correction tasks against the Atlas Commerce Operations database. The service exposes a read-only SQL endpoint, a controlled transaction endpoint for corrections, a schema endpoint, a data-dictionary endpoint, and a correction-audit listing. Use these to answer business requests that arrive as a prompt.txt paired with payloads in a sibling `payloads/` directory.

## Entry workflow

1. **Read the request facts and answer template.**
   - `prompt.txt` names the business question, references `<TASK_ENV_BASE_URL>`, and points to supporting payloads.
   - `payloads/` contains a request-facts JSON and an `answer_template.json` that defines the exact output shape (required fields, types, constraints, ordering rules).

2. **Load the database surface.**
   - `GET /api/schema` — table DDL, indexes.
   - `GET /api/data-dictionary` — column descriptions, dedup conventions, timestamp/money encoding notes.

3. **Explore the scope with read-only SQL.**
   - `POST /api/sql` accepts `{"sql": "<query>"}`. It is read-only; mutations are rejected.
   - If the result set exceeds the internal row limit, batch by segmenting on an indexed key (e.g. shipment_id ranges).

## Data-integrity conventions

### Deduplication

Every append-only event table (`carrier_scans`, `order_events`, `refund_attempts`, `payment_events`, `case_events`, `warehouse_task_events`, `inventory_movements`) may contain retry-duplicates. The effective row is the one with the maximum `ingested_at` per `(source_system, external_event_id)` pair.

Always apply this dedup before computing aggregates, statuses, or counts:

```sql
-- Keep the latest ingested copy of each event
SELECT ...
FROM table t
WHERE t.ingested_at = (
  SELECT MAX(t2.ingested_at) FROM table t2
  WHERE t2.source_system = t.source_system
    AND t2.external_event_id = t.external_event_id
)
```

When the full dedup query is rejected, query without dedup and filter in the calling code — duplicates share the same canonical values, so dedup rarely changes the final answer for status checks, but always verify.

### Raw vs canonical fields

Several tables carry both `raw_*` and `canonical_*` columns:
- `carrier_scans.raw_status` / `carrier_scans.canonical_status`
- `carrier_scans.raw_event_at` / `carrier_scans.canonical_event_at`
- `inventory_movements.raw_quantity` / `inventory_movements.canonical_quantity_each`

**Always use the canonical column for operational analytics.** The raw column is the unmodified source value; the canonical column is the normalized operational value. A "contradiction" between them is a data-quality defect to be corrected through the transaction endpoint.

### Timestamps and dates

- All stored timestamps use ISO‑8601 UTC text ending in `Z`.
- Calendar-date columns (`fx_rates.rate_date`, `refund_attempts.service_date`) use `YYYY-MM-DD` text.
- A request's stated cutoff is an inclusive UTC boundary: `<= '2026-04-15T23:59:59Z'`.

### Monetary amounts

- Fields ending in `_minor` store the smallest currency unit (cents, pence, etc.). Divide by 100 to obtain major-unit values.
- `fx_rates.usd_per_unit` gives the USD value of one unit of the named currency for the calendar date.
- For multi-currency refund analysis: convert each row at its own `service_date` and row `currency`; for the order-gross comparison, convert the order gross using the refund's `service_date` rate.

## Status determination

### Shipment delivery status

A shipment's *effective final carrier status* at a cutoff is the `canonical_status` of the latest (by `canonical_event_at`) deduplicated carrier scan at or before the cutoff:

```sql
SELECT cs.canonical_status
FROM carrier_scans cs
WHERE cs.shipment_id = ?
  AND cs.canonical_event_at <= '<cutoff>'
ORDER BY cs.canonical_event_at DESC, cs.scan_row_id DESC
LIMIT 1
```

When counting the first delivery time for on-time checks, use the earliest `canonical_event_at` among deduplicated `DELIVERED` scans at or before the cutoff.

### Task / case completion

- `warehouse_tasks.current_status` is a convenience snapshot. Use it for completion/rework classification unless the request explicitly requires event-driven logic.
- `support_cases.current_status` is similar. `OPEN` and `REOPENED` both count as active; `REOPENED` is a subset of active-at-cutoff cases.

### Reversal chains (refunds)

A `REVERSED` row with a `linked_refund_id` reverses the target refund. Chains of reversals are possible. An *effective settled logical refund* is a `SETTLED` row whose `refund_id` is not the target of any `REVERSED` row. When reversals target `FAILED` or already-`REVERSED` refunds they do not affect the settled-refund count.

## Applying corrections

Use `POST /api/sql/transaction` for controlled writes. The transaction atomically updates the business row and inserts an audit record into `correction_audit`.

- Refer to the request's `approved_correction` block for the `correction_key`, `audit_id`, `reason_code`, `actor`, and `corrected_at`.
- The `correction_status` in the output must be `APPLIED` only when exactly one business row and one audit row commit, and a post-change query confirms the corrected canonical value.
- Any other outcome (rejected transaction, mismatch, zero rows affected) → `NOT_APPLIED`, with the pre-correction state reported.

Before applying, verify the contradiction by querying for rows where `raw_status != canonical_status` (for carrier scans) or the analogous mismatch for the entity type in scope.

## General query patterns

### Campaign-attributed orders

```sql
SELECT o.*, w.region
FROM orders o
JOIN accounts a ON o.account_id = a.account_id
JOIN warehouses w ON o.warehouse_id = w.warehouse_id
WHERE o.campaign_id = '<campaign_id>'
  AND a.is_internal = 0 AND a.is_test = 0     -- "production" accounts
  AND o.order_created_at >= '<campaign.starts_at>'
  AND o.order_created_at <= '<campaign.ends_at>'
```

### Cohort-scoped shipments

When a request defines a cohort by import batch, first find distinct shipment IDs (`SELECT DISTINCT shipment_id FROM carrier_scans WHERE import_batch_id = ? AND canonical_event_at <= ?`), then fetch effective final statuses for that shipment set.

### Regional rollups

Join through `orders.warehouse_id → warehouses.region`. For regional rates, compute per-region numerators and denominators independently, sort by the unrounded rate ascending then region ascending, and report exactly the number of regions the request specifies.

### Breach and SLA checks

For each case/task, compute the active-time duration from the open/creation timestamp to the first qualifying event (agent response, resolution). If the event has not occurred by the cutoff, use the elapsed time at the cutoff. Compare against the priority-tier threshold table in the request. An "active clock" breach for a still-open case uses the cutoff as the endpoint.

## Output rules

- Produce exactly one JSON object conforming to `answer_template.json`.
- No commentary, no additional fields, no narrative outside the JSON.
- Round final reported rates to the decimal places specified in the answer template.
- Sort array elements as stated (ascending IDs, ranked accounts, etc.).
- Use the exact enum values from the template/request for status fields.
