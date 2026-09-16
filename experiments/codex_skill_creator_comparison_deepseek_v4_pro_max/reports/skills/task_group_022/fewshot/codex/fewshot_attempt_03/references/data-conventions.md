# Atlas Commerce Data Conventions

Extracted from the live data dictionary. These conventions apply to every query.

## Timestamps

- All stored timestamps use ISO-8601 UTC text ending in `Z` (e.g., `2026-04-15T23:59:59Z`).
- Compare timestamps lexicographically or use SQLite datetime functions.
- Calendar dates use `YYYY-MM-DD` text (e.g., `2026-03-01`).

## Money

- Monetary **minor** fields (`amount_minor`, `gross_amount_minor`) store values in the smallest unit of the named row currency.
  - For most currencies (USD, EUR, GBP, etc.): divide by 100 to get major-unit value.
  - Always check the `currency` column on the same row.
- **FX conversion**: `fx_rates(rate_date, currency, usd_per_unit)`.
  - `usd_per_unit` is the USD value of ONE unit of the source currency.
  - Convert minor amount to major first: `amount_major = amount_minor / 100.0`
  - Then: `amount_usd = amount_major * usd_per_unit`
  - Match `rate_date` to the relevant service date for each row.

### FX Conversion Example

For a refund of 5000 minor units in EUR with service_date `2026-03-15`:

```sql
SELECT r.amount_minor / 100.0 * f.usd_per_unit AS usd_amount
FROM refund_attempts r
JOIN fx_rates f ON f.rate_date = r.service_date AND f.currency = r.currency
WHERE r.refund_row_id = ?
```

## Integer Booleans

- `is_internal`, `is_test`, `is_active`: 1 means true, 0 means false.
- Use `= 0` or `= 1` in WHERE clauses, not boolean expressions.

## Production Scoping

- For `accounts`: `is_internal = 0 AND is_test = 0` means production, external accounts.
- For `warehouse_tasks`: `work_class = 'PRODUCTION'` means production work (exclude `TRAINING`).

## Deduplication

Tables with `source_system` + `external_event_id` + `ingested_at` may contain duplicate imports. Always deduplicate:

```sql
SELECT ...
FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at DESC
  ) AS rn
  FROM table_name
) dedup
WHERE dedup.rn = 1
```

## Effective State from Append-Only Events

For `order_events`, `case_events`, `warehouse_task_events`:

```sql
-- Latest event per entity
SELECT ...
FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY event_at DESC, row_id DESC
  ) AS rn
  FROM events_table
) latest
WHERE latest.rn = 1
```

## Carrier Scan Effective State

Per shipment, use the latest `canonical_event_at`, breaking ties with the latest `scan_row_id`:

```sql
SELECT ...
FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY shipment_id
    ORDER BY canonical_event_at DESC, scan_row_id DESC
  ) AS rn
  FROM carrier_scans
  WHERE ... dedup first ...
) latest_scan
WHERE latest_scan.rn = 1
```

## Support Active Time

Active time is elapsed time during which a case was in an agent-facing state (not SYSTEM actor). Compute by ordering `case_events` per case by `event_at`, then summing the interval to the next event when the current event is not a SYSTEM event.

For breach computation, unresolved cases use `active_elapsed_time` from the most recent event to the cutoff.

## Rounding

- Apply rounding only to **final** reported values.
- Use unrounded values for intermediate aggregates, rankings, and tie-breaking.
- Common rounding functions: `ROUND(value, 4)` for 4 decimal places, `ROUND(value, 2)` for 2 decimal places.

## Median

For an odd count: middle value. For an even count: average of the two central values.

SQL approach using `ROW_NUMBER()`:

```sql
WITH ordered AS (
  SELECT value, ROW_NUMBER() OVER (ORDER BY value) AS rn, COUNT(*) OVER () AS cnt
  FROM dataset
)
SELECT AVG(value) FROM ordered
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
```

## NULL Semantics

- `linked_refund_id` IS NULL means the refund is not a reversal.
- `linked_refund_id` IS NOT NULL means this refund reverses another settled refund.
- `corrected_at` IS NULL means no correction has been applied.
- `shipped_at` IS NULL means the shipment has not been dispatched.
- `campaign_id` IS NULL means the order has no campaign attribution.
