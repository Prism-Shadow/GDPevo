# Atlas SQL Patterns

This reference contains reusable SQL and reasoning patterns for Atlas Commerce Operations tasks. Always adapt placeholders, dates, scopes, and thresholds to the current request payload.

## API Shape

The read-only SQL endpoint accepts:

```json
{"sql": "select count(*) as n from orders"}
```

It returns JSON with `columns`, `rows`, `row_count`, and `truncated`. If `truncated` is true, rerun a narrower query for complete detail. Prefer incremental queries while building a complex answer: first cohort count, then effective rows, then metric rollups, then final ordered lists.

## Effective Source Rows

Imported tables may contain repeated copies of the same upstream event. Deduplicate by source identity before using them in metrics:

```sql
WITH effective_scans AS (
  SELECT *
  FROM (
    SELECT
      cs.*,
      row_number() OVER (
        PARTITION BY source_system, external_event_id
        ORDER BY ingested_at DESC, scan_row_id DESC
      ) AS rn
    FROM carrier_scans cs
    WHERE canonical_event_at <= :cutoff_at
  )
  WHERE rn = 1
)
```

Use the table's stable row id for the final tie-breaker:

- `carrier_scans.scan_row_id`
- `case_events.case_event_id`
- `warehouse_task_events.task_event_id`
- `order_events.event_id`
- `payment_events.payment_event_id`
- `refund_attempts.refund_row_id`
- `inventory_movements.movement_row_id`

After import deduplication, select the latest state per business entity:

```sql
latest_shipment_state AS (
  SELECT *
  FROM (
    SELECT
      s.shipment_id,
      s.order_id,
      s.promised_delivery_at,
      es.canonical_status,
      es.canonical_event_at,
      row_number() OVER (
        PARTITION BY s.shipment_id
        ORDER BY es.canonical_event_at DESC, es.scan_row_id DESC
      ) AS rn
    FROM shipments s
    LEFT JOIN effective_scans es ON es.shipment_id = s.shipment_id
  )
  WHERE rn = 1 OR rn IS NULL
)
```

Use analogous CTEs for cases by `case_id`, tasks by `task_id`, orders by `order_id`, and inventory by `(warehouse_id, sku)` as requested.

## Cohorts

Translate every scope term into a predicate and keep it in one CTE. Common Atlas filters:

```sql
JOIN accounts a ON a.account_id = o.account_id
WHERE a.is_internal = 0
  AND a.is_test = 0
```

Inclusive UTC windows should use `BETWEEN :start_at AND :end_at` only when both endpoints are exact timestamps from the request. For date windows, compare date text to date text. Keep "created in window" separate from "state at cutoff"; many tasks need both.

Campaign cohorts normally join `orders` to `campaigns` and require both the named campaign and the campaign active window:

```sql
JOIN campaigns c ON c.campaign_id = o.campaign_id
WHERE o.campaign_id = :campaign_id
  AND o.order_created_at BETWEEN c.starts_at AND c.ends_at
```

## Rates, Rankings, And Rounding

Compute rates as real numbers and round only the final projection:

```sql
CAST(numerator AS REAL) / NULLIF(denominator, 0)
```

For ordered outputs, keep an unrounded metric column for `ORDER BY` and a rounded metric for the final value:

```sql
SELECT region, round(rate_unrounded, 4) AS reported_rate
FROM regional_rollup
ORDER BY rate_unrounded ASC, region ASC
LIMIT 2
```

Use `round(value, 2)` for money or hours when the template requests two decimals. For JSON numbers, trailing zeroes are not significant, so `12.3` is a valid two-decimal rounded number when the exact rounded value is `12.30`.

## Money And FX

Minor monetary fields are in the smallest unit of the row currency. Convert with `amount_minor / 100.0 * fx_rates.usd_per_unit` unless the current task documents a different minor-unit rule.

Refund tasks often need all three layers:

1. Effective settled logical refunds, usually `status = 'SETTLED'`.
2. Effective linked reversals, usually `status = 'REVERSED'` with `linked_refund_id` pointing at a logical refund.
3. Net exposure by order or reason: settled USD minus linked reversal USD.

Join FX by the service date and row currency:

```sql
JOIN fx_rates fx
  ON fx.rate_date = refund_attempts.service_date
 AND fx.currency = refund_attempts.currency
```

When comparing refund value to order gross, convert the order gross with the FX rate required by the request, commonly the candidate refund service date.

## Fulfillment Completion

An order with no physical shipment is incomplete. A complete order has at least one shipment and every shipment's effective final canonical status at the cutoff is `DELIVERED`.

For severe-lateness rules, compare timestamps with SQLite `julianday` to preserve ISO UTC semantics:

```sql
(julianday(delivered_at) - julianday(promised_delivery_at)) * 24.0 > 24.0
```

Incomplete severe exceptions usually depend on the cutoff being more than a threshold after the latest shipment promise. Do not mark a no-shipment order severe under that rule unless the request supplies another promise source.

## Warehouse Productivity

Use `warehouse_tasks` for the created-window cohort and assignment metadata. Use effective `warehouse_task_events` at or before the cutoff for completed units, productive minutes, and rework evidence.

Units per hour:

```sql
SUM(completed_units) * 60.0 / NULLIF(SUM(productive_minutes), 0)
```

Completion rate:

```sql
completed_task_count * 1.0 / NULLIF(eligible_task_count, 0)
```

Delayed high-priority tasks usually mean `priority IN ('HIGH','URGENT')`, `due_at` strictly before the cutoff, and not completed by the cutoff.

## Support Active Time

For support cases, derive active support-clock intervals from effective `case_events` at or before the cutoff. Typical event effects:

- `OPENED`, `REOPENED`, and `CUSTOMER_REPLIED` start or resume active support time.
- `WAITING_CUSTOMER` and `RESOLVED` stop active support time.
- `AGENT_RESPONDED`, `ASSIGNED`, and `ESCALATED` are important milestones but usually do not stop the active clock unless the request says so.

Build intervals with `lead(event_at)` over each case. For still-active intervals, use the cutoff as the interval end. Active hours are:

```sql
(julianday(interval_end_at) - julianday(interval_start_at)) * 24.0
```

First-response active time ends at the first `AGENT_RESPONDED` event; if none exists by cutoff, use active elapsed time through the cutoff. Resolution active time ends at `RESOLVED`; for active cases, use active elapsed time through the cutoff.

Median active resolution hours in SQLite:

```sql
SELECT avg(active_resolution_hours) AS median_hours
FROM (
  SELECT
    active_resolution_hours,
    row_number() OVER (ORDER BY active_resolution_hours) AS rn,
    count(*) OVER () AS n
  FROM resolved_values
)
WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
```

## Controlled Corrections

For correction tasks, do all analysis read-only first:

1. Find the single row where raw/canonical values contradict the business rule.
2. Capture row id, business entity id, field name, old canonical value, and new canonical value.
3. Recompute the pre-correction metric.
4. Submit only the approved canonical update and audit insert through the controlled transaction endpoint.
5. Verify affected business rows, audit rows, corrected canonical value, and post-correction metric with read-only queries.

Never modify raw source values, source identity fields, unrelated rows, or unapproved columns. If the transaction endpoint rejects the request, affects the wrong number of rows, creates the wrong audit record, or verification fails, report the not-applied branch with the observed results.

## Final Projection Checklist

Before writing `answer.json`, check:

- Every required property exists and there are no extras.
- Counts use the requested entity level, not raw imported row counts.
- Rates and money are rounded only in the final JSON.
- Top/worst lists use unrounded sort keys and specified tie-breakers.
- ID arrays are unique and sorted as requested.
- Risk/status enums are evaluated from unrounded rates and counts.
- The final JSON parses cleanly and validates against the template.
