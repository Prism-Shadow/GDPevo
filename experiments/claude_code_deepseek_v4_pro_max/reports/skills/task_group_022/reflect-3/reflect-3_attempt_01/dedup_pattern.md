# Deduplication Pattern Reference

Every event table in Atlas Commerce Operations may contain duplicate imports.
The database includes `idx_*_dedupe` indexes that reveal the dedup key:
`(source_system, external_event_id, ingested_at)`.

## When to deduplicate

Check the schema for any index named `idx_<table>_dedupe`. If found, you MUST
deduplicate that table before any analysis. Tables known to require dedup:

- `carrier_scans` — index `idx_scans_dedupe`
- `refund_attempts` — index `idx_refunds_dedupe`
- `warehouse_task_events` — index `idx_task_events_dedupe`
- `case_events` — index `idx_case_events_dedupe`
- `payment_events` — index `idx_payments_dedupe`
- `order_events` — index `idx_order_events_dedupe`
- `inventory_movements` — index `idx_movements_dedupe`

## Standard dedup CTE

```sql
WITH dedup AS (
  SELECT t.*
  FROM <table_name> t
  WHERE t.<primary_key> = (
    SELECT t2.<primary_key>
    FROM <table_name> t2
    WHERE t2.source_system = t.source_system
      AND t2.external_event_id = t.external_event_id
    ORDER BY t2.ingested_at DESC, t2.<primary_key> DESC
    LIMIT 1
  )
)
```

Replace `<table_name>` with the actual table and `<primary_key>` with the table's
row identifier column (e.g., `scan_row_id`, `refund_row_id`, `task_event_id`,
`case_event_id`, `payment_event_id`, `event_id`, `movement_row_id`).

## Effect on analysis

- Counts will be inflated without dedup (duplicate events counted multiple times)
- Monetary sums will be wrong (duplicate amounts summed multiple times)
- Rates and percentages will be distorted
- Rankings may change if duplicates concentrate in certain categories

## Tiebreaker

When multiple rows share the same `(source_system, external_event_id, ingested_at)`,
use the highest primary key value as the final tiebreaker. This ensures deterministic
row selection.
