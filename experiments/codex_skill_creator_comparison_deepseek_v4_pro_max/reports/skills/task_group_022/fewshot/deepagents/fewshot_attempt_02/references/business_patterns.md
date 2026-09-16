# Common Business Patterns: SQL Translations

This reference maps recurring business definitions from Atlas Operations
requests into SQL patterns. Adapt each pattern to the specific table schemas
returned by GET /api/schema and GET /api/data-dictionary.

## Cohort Filtering

**Time windows**
- inclusive boundary: col >= start AND col <= end
- Exact UTC timestamps from the request; do not adjust time zones.
- For created-at or opened-at windows, filter the source table before joining.

**Account, warehouse, region, segment scoping**
- Filter on the relevant dimension column (e.g. account_tier, warehouse_id, region, segment).
- When a region filter is given, join through the account or warehouse table
  that carries the region attribute.

**Campaign attribution**
- Cohort membership: campaign_id = id AND created_at >= campaign_start
  AND created_at <= campaign_end.

## State Classification

**Complete order (fulfillment)**

An order is complete iff:
  - It has at least one shipment, AND
  - Every shipment has final canonical_status = DELIVERED.

Per-order completion:
  SELECT o.id,
         COUNT(s.id) AS shipment_count,
         COUNT(s.id) FILTER (WHERE canonical_status = DELIVERED) AS delivered_count
  FROM orders o LEFT JOIN shipments s ON ...
  GROUP BY o.id
  -- complete when shipment_count > 0 AND shipment_count = delivered_count

**On-time order**

A complete order is on-time iff every shipment delivered_at <= that
shipment promised_delivery_at. Compute per-shipment before aggregating.

**Severe exception (fulfillment)**

An order is a severe exception when:
  1. It is incomplete AND cutoff > latest_promise + 24h, OR
  2. It is complete AND any shipment delivered > promise + 24h.

An incomplete order with no shipment promise does NOT satisfy the first
condition (NULL promise is not > 24h).

**Backlog (carrier quality)**

A shipment is backlogged when its effective final carrier_status IS NOT DELIVERED
at the cutoff. The final status is the canonical_status from the most recent
scan for that shipment at or before the cutoff.

**First-response breach (support)**

Active time to first agent response exceeds the priority threshold.
An unresponded case uses active elapsed time at the cutoff.

**Active-clock resolution breach (support)**

Active time to resolution exceeds the priority threshold.
An unresolved/active case uses active elapsed time at the cutoff.

**Severe active case (support)**

Open or reopened at cutoff, priority URGENT or HIGH, and beyond the
priority resolution active-time threshold.

**Leakage candidate (refund reconciliation)**

Either:
  - The order effective settled refund value (after reversals) > gross order
    value in USD, OR
  - The order has >= 2 unreversed effective settled logical refunds with the
    same normalized reason_code.

## Metric Computation

**Rates and ratios**
- Denominator = eligible population (the full cohort).
- Incomplete / open items remain in the denominator unless the definition
  explicitly excludes them.
- Only round at the final step; keep intermediate values unrounded.

**Currency conversion**

Join fx_rates ON fx.date = service_date AND fx.currency = row currency.
Multiply the local amount by fx.usd_per_unit.
Use the service_date of the refund/reversal for each row when converting.

**Median of even-count sets**

If count is odd: select the middle value.
If count is even: average the two central values.
Compute in Python after fetching the sorted array for reliability.

**Units per hour**

For each employee: total completed units / total productive minutes * 60.
Productive minutes are attached to the completed units, not to all tasks.

**Employee and team ranking**

Rank by metric descending, then by ID ascending.
Fetch all rows, sort in application code, then take the top N.

**Multi-key array sort with tie-breaks**

Primary key descending, secondary key ascending.
Example (Python):
  sorted(items, key=lambda x: (-x[primary], x[secondary]))

## Classification Rules

**General pattern**

Rules are evaluated top-to-bottom. First matching rule wins.
A final catch-all (otherwise, all other outcomes) catches
everything that did not match an earlier rule.

Example (Python):
  if rate >= 0.88 and severe_rate < 0.05:
      status = HEALTHY
  elif rate >= 0.78 and severe_rate < 0.12:
      status = WATCH
  else:
      status = CRITICAL

## Correction Patterns

**Contradiction detection**

Find rows where raw_status != canonical_status for the same scan.
Limit to the import batch, warehouse, and cutoff specified in the request.
There will be exactly one contradiction in the batch.

**Transaction submission**

UPDATE the canonical_status to match the raw_status.
The transaction body includes both the SQL and all audit metadata.
Always verify with a post-change SELECT and an audit-query check.
