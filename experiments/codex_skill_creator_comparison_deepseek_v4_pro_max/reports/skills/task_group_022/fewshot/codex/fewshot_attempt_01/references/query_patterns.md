## Reusable Athena SQL Patterns

All queries run against the Atlas Commerce Operations API via `POST /api/sql`.
The database uses SQLite3 SQL dialect. Every query must return valid SQLite result sets.

### 1. Deduplication Everywhere

Tables with a `(source_system, external_event_id, ingested_at)` import key will contain
duplicate rows from retried ingestions. Always filter to the last-ingested copy:

```sql
SELECT ... COLLAPSE_BEFORE JOIN ...

WITH dedup AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at DESC
  ) AS rn
  FROM table_name
)
SELECT ...
FROM dedup
WHERE rn = 1
```

Tables requiring this pattern: `carrier_scans`, `case_events`, `inventory_movements`,
`order_events`, `payment_events`, `refund_attempts`, `warehouse_task_events`.

### 2. Effective Final State from Event History

The `current_status` columns on headers (`orders`, `shipments`, `warehouse_tasks`,
`support_cases`) are convenience snapshots that may lag. For accurate cutoff-based
state determination, derive the final state from the event table:

```sql
SELECT entity_id, event_type AS final_state
FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY event_at DESC, event_id DESC
  ) AS rn
  FROM deduped_events
  WHERE event_at <= '<cutoff>'
)
WHERE rn = 1
```

Use the effective-event indexes: `idx_scans_shipment_effective`, `idx_case_events_effective`,
`idx_task_events_effective`, `idx_order_events_effective`.

### 3. FX Conversion (Currency to USD)

Join `fx_rates` on the date of the event and the row's currency:

```sql
SELECT r.amount_minor * f.usd_per_unit / 100.0 AS amount_usd
FROM deduped_refund r
JOIN fx_rates f ON f.rate_date = r.service_date AND f.currency = r.currency
```

Monetary amounts in minor units (cents for USD, etc.). Divide by 100 to get display
dollars. The `fx_rates.usd_per_unit` is the USD value of 1 unit of that currency.

For order gross comparisons when the order currency differs from the refund/reversal
currency, value the order gross at the refund/reversal service_date rate:

```sql
o.gross_amount_minor * f.usd_per_unit / 100.0 AS order_gross_usd
```

### 4. Rounding Rules

Round only at the final reporting stage. Carry unrounded intermediate values through
computations:

- **Rates** (4 decimal places): `ROUND(value, 4)`
- **Dollars** (2 decimal places): `ROUND(value, 2)`
- **Hours** (2 decimal places): `ROUND(value, 2)`

### 5. Inclusive Timestamp Windows

All task-level boundaries are inclusive on both ends:

```sql
WHERE o.order_created_at >= '2026-04-01T00:00:00Z'
  AND o.order_created_at <= '2026-04-15T23:59:59Z'
```

### 6. Corrected / Canonical Only

When a table has `raw_*` and `canonical_*` columns alongside `corrected_at` /
`correction_reason`, always use canonical values for business logic. Raw values
are preserved for source forensics only.

On `carrier_scans`, the effective scan for a shipment is the deduplicated row with
the latest `canonical_event_at` at-or-before the cutoff (use `scan_row_id` as tiebreak).

### 7. Controlled Transaction for Corrections

Use `POST /api/sql/transaction` with a JSON body:

```json
{
  "statements": [
    "UPDATE carrier_scans SET canonical_status = 'DELIVERED', corrected_at = '2026-03-20T09:30:00Z', correction_reason = 'SOURCE_RECONCILIATION' WHERE scan_row_id = 'SCN-0001272'",
    "INSERT INTO correction_audit (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) VALUES ('AUD-...', 'CQR-...', 'carrier_scan', 'SHP-...', 'SCN-...', 'canonical_status', 'IN_TRANSIT', 'DELIVERED', 'SOURCE_RECONCILIATION', '2026-03-20T09:30:00Z', 'ops-data-quality')"
  ]
}
```

The transaction API commits both statements atomically or rolls back entirely.
After committing, verify the change with a read-only `POST /api/sql` query.
Use `GET /api/correction-audit?correction_key=...` to confirm the audit record.

### 8. Production-Population Filters

The accounts table carries `is_internal` and `is_test` flags. Most analytical
tasks scope to production (non-internal, non-test) accounts:

```sql
JOIN accounts a ON o.account_id = a.account_id
WHERE a.is_internal = 0 AND a.is_test = 0
```

For warehouse task queries, filter tasks through `work_class = 'PRODUCTION'` to
exclude training work.

### 9. Time Math (Hours Between Timestamps)

SQLite3 difference in hours (fractional):

```sql
(julianday(later_ts) - julianday(earlier_ts)) * 24 AS hours_elapsed
```

### 10. Median Across a Set

SQLite3 has no built-in `MEDIAN`. For even row counts, average the two central
values:

```sql
WITH ordered AS (
  SELECT value, ROW_NUMBER() OVER (ORDER BY value) AS rn,
         COUNT(*) OVER () AS cnt
  FROM dataset
)
SELECT AVG(value) AS median
FROM ordered
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
```

### 11. Ranking with Stable Tiebreaks

Always include stable tiebreak columns in `ORDER BY` inside `ROW_NUMBER()`:

```sql
ROW_NUMBER() OVER (
  ORDER BY metric DESC, tiebreak_id ASC
) AS rn
```

### 12. Severe Exception / Leakage Detection

Common patterns involve chaining conditions with OR:

- **Incomplete order past promise**: incomplete AND cutoff > (latest promise + 24h)
- **Late delivery**: complete AND any shipment delivered > (promise + 24h)
- **Leakage**: refund value exceeds order gross, OR multiple unreversed refunds with same reason

Express as UNION of two subqueries when conditions are structurally different.

### 13. Regional Rollups

Use `warehouses.region` joined through `orders.warehouse_id`:

```sql
SELECT w.region, COUNT(*) ...
FROM orders o
JOIN warehouses w ON o.warehouse_id = w.warehouse_id
GROUP BY w.region
```

### 14. SLA Breach Detection

Compare elapsed active time against priority thresholds. An unresolved case at
cutoff uses elapsed time from open to cutoff. A resolved case uses time from
open to resolution.

Active time = time in OPEN/REOPENED state (exclude time in RESOLVED/CLOSED
intermediate states). Compute by walking case_events in temporal order.

For first-response breach: find the earliest AGENT actor_type RESPONDED event,
or use cutoff elapsed if no response exists.

### 15. Units Per Hour (Productivity)

```sql
SELECT e.employee_id,
       SUM(te.units) * 1.0 / NULLIF(SUM(te.productive_minutes), 0) * 60 AS units_per_hour
FROM warehouse_tasks t
JOIN warehouse_task_events te ON te.task_id = t.task_id AND te.event_type = 'COMPLETED'
... proper grouping ...
```

Use `NULLIF` to avoid division-by-zero.
