# SQL Query Patterns

## Query structure

Every analytical query is POSTed to `/api/sql` as:

```json
{"query": "SELECT ..."}
```

The service returns a JSON array of row objects. Column names in the
result match the column names in the SELECT clause.

## Time window filtering

The task payload sets time boundaries. Apply them consistently:

```sql
-- Inclusive start, inclusive end:
WHERE created_at >= '2026-03-01T00:00:00Z'
  AND created_at <= '2026-04-30T23:59:59Z'
```

When a cutoff is "at or before", use `<=`. When "strictly before", use
`<` for date-only boundaries and `<=` for the exact timestamp when the
payload says "at or before".

## Effective/canonical resolution

### Effective final state per entity

When a business entity (shipment, order, case) has multiple rows and
the rule cares about the effective final row:

```sql
SELECT shipment_id, canonical_status
FROM (
  SELECT shipment_id, canonical_status,
    ROW_NUMBER() OVER (
      PARTITION BY shipment_id ORDER BY scan_at DESC
    ) AS rn
  FROM carrier_scans
  WHERE canonical_status IS NOT NULL
) sub
WHERE rn = 1
```

### Effective settled logical refunds

Filter refund rows to those marked effective and settled:

```sql
SELECT *
FROM refunds
WHERE effective_settled = true
```

Similarly, filter reversals to those marked effective and linked to
settled refunds.

## JOIN patterns

### Order -> shipment (one-to-many)

```sql
SELECT o.order_id, s.shipment_id, s.delivered_at, s.promised_delivery_at
FROM orders o
LEFT JOIN shipments s ON o.order_id = s.order_id
```

A LEFT JOIN preserves orders with no shipments (incomplete orders).

### Shipment -> carrier scans (one-to-many)

```sql
SELECT s.shipment_id, cs.canonical_status, cs.scan_at
FROM shipments s
LEFT JOIN carrier_scans cs ON s.shipment_id = cs.shipment_id
```

### Order -> refunds (one-to-many)

```sql
SELECT o.order_id, r.refund_id, r.amount, r.currency
FROM orders o
JOIN refunds r ON o.order_id = r.order_id
WHERE r.effective_settled = true
```

## Aggregation patterns

### Count with condition

```sql
SELECT COUNT(*) AS total,
  COUNT(*) FILTER (WHERE condition) AS subset
FROM ...
```

Or equivalently:

```sql
SELECT COUNT(*) AS total,
  SUM(CASE WHEN condition THEN 1 ELSE 0 END) AS subset
FROM ...
```

### Group-level rates

Compute a rate per group, keeping the denominator as all rows:

```sql
SELECT region,
  COUNT(*) AS total,
  SUM(CASE WHEN on_time THEN 1 ELSE 0 END) AS on_time_total,
  SUM(CASE WHEN on_time THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS raw_rate
FROM ...
GROUP BY region
```

Rate = numerator / denominator. Incomplete orders stay in the
denominator unless the payload says otherwise.

### Median

Use `percentile_cont` when the SQL dialect supports it:

```sql
SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) AS median
FROM ...
```

When not available, sort the values and pick the middle (or average
the two middle values for an even count).

## NULL handling in conditions

NULLs in boolean expressions:

```sql
-- An order is complete only when it HAS shipments AND all are delivered
SUM(CASE
  WHEN s.shipment_id IS NULL THEN 0  -- no shipment = incomplete
  WHEN s.delivered_at IS NULL THEN 0
  WHEN s.delivered_at > cutoff THEN 0
  ELSE 1
END) AS complete_count
```

For severe exceptions where a NULL changes the branch:

```sql
-- incomplete AND (cutoff > promise + 24h)
-- NULL promise = condition can never be true
CASE
  WHEN is_complete = false
    AND s.promised_delivery_at IS NOT NULL
    AND cutoff > s.promised_delivery_at + INTERVAL '24 hours'
  THEN true
  ELSE false
END
```

## Currency conversion

When the task requires USD conversion:

```sql
SELECT r.amount * fx.usd_per_unit AS amount_usd
FROM refunds r
JOIN fx_rates fx ON fx.date = r.service_date AND fx.currency = r.currency
```

Apply the rate for each row's service date and currency. Sum after
converting individually.

## Self-joins for same-reason detection

To find orders with at least two unreversed effective settled refunds
sharing the same reason code:

```sql
SELECT r1.order_id
FROM refunds r1
JOIN refunds r2
  ON r1.order_id = r2.order_id
  AND r1.reason_code = r2.reason_code
  AND r1.refund_id < r2.refund_id
WHERE r1.effective_settled = true
  AND r2.effective_settled = true
  AND r1.reversed = false
  AND r2.reversed = false
GROUP BY r1.order_id
```

## Sorting with tiebreakers

When the payload specifies multi-level ordering:

```sql
ORDER BY primary_key DESC, secondary_key ASC, tertiary_key ASC
```

Apply the ordering after computing all values. Tiebreakers only resolve
actual ties on the preceding keys.
