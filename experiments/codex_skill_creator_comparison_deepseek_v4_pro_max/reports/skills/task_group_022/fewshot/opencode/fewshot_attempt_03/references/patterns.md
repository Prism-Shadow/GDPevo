# SQL Translation Patterns

This reference catalogs the recurring patterns for translating business
definitions from request facts into SQL. Each pattern includes the general
form, edge cases to handle, and pitfalls to avoid.

## Cohort eligibility

Every task starts by filtering a population. Typical filters:

### Date windows

When the request facts specify an inclusive date window:

    WHERE created_at >= 'start' AND created_at <= 'end'

When the boundary semantics are not explicit, re-read the facts. Some windows
use `>=` and `<` depending on the boundary keyword.

### Status and tier filters

    WHERE account_tier = 'GOLD'
      AND account_type = 'production'
      AND region IN ('NORTH', 'EAST')

### Campaign attribution

When an entity must be attributed to a specific campaign:

    WHERE campaign_id = '<campaign_id>'
      AND created_at BETWEEN campaign_start AND campaign_end

Use the campaign's official active window from the database, not hardcoded
dates from the request text.

### Distinct vs. non-distinct counts

The request facts state whether counts refer to distinct orders, distinct
shipments, or distinct logical refunds. Use `COUNT(DISTINCT col)` when the
facts say "distinct"; otherwise use `COUNT(*)` or `COUNT(col)`.

## Derived state classification

### Completion based on child-row aggregates

A common pattern: an entity (order, task) is "complete" based on the state of
its children (shipments, work units). Build this with a subquery or CTE that
aggregates child state per parent:

```sql
WITH shipment_state AS (
  SELECT
    order_id,
    COUNT(*) AS total_shipments,
    COUNT(*) FILTER (WHERE status = 'DELIVERED') AS delivered_shipments,
    BOOL_AND(delivered_at <= promised_delivery_at) AS all_on_time
  FROM shipments
  GROUP BY order_id
)
SELECT
  o.order_id,
  CASE
    WHEN s.total_shipments IS NULL OR s.total_shipments = 0 THEN 0
    WHEN s.delivered_shipments = s.total_shipments THEN 1
    ELSE 0
  END AS is_complete
FROM orders o
LEFT JOIN shipment_state s ON o.order_id = s.order_id
```

Key edge cases:

- **No shipments**: An entity with no children is incomplete. Use `LEFT JOIN`
  and treat NULL as zero/false.
- **NULL promised dates**: A shipment with NULL `promised_delivery_at` cannot
  be compared. Guard with `IS NOT NULL` before comparing dates.
- **"Every" vs "at least one"**: Use `BOOL_AND` for universal conditions (every
  shipment must satisfy) and `BOOL_OR` for existential conditions (at least one
  shipment must satisfy).

### Multi-condition classification

When the request facts define a classification with a negative condition
(e.g. "an incomplete order with no shipment promise does not satisfy the first
condition"), handle each branch explicitly:

```sql
CASE
  -- incomplete AND cutoff > 24h after latest promise
  WHEN is_complete = 0
   AND latest_promise IS NOT NULL
   AND cutoff_at > latest_promise + INTERVAL '24 hours'
  THEN 1
  -- completed AND any shipment delivered > 24h after its promise
  WHEN is_complete = 1
   AND EXISTS (
     SELECT 1 FROM shipments sh
     WHERE sh.order_id = o.order_id
       AND sh.delivered_at > sh.promised_delivery_at + INTERVAL '24 hours'
   )
  THEN 1
  ELSE 0
END AS is_severe_exception
```

### Backlog classification

A "backlog" item is one whose final effective state at the cutoff is not a
target status. When each entity has multiple events (scans, status changes),
determine the final state per entity first, then classify:

```sql
WITH final_status AS (
  SELECT DISTINCT ON (shipment_id)
    shipment_id,
    canonical_status
  FROM carrier_scans
  WHERE batch_id = '<import_batch_id>'
    AND scanned_at <= '2026-03-19T23:59:59Z'
  ORDER BY shipment_id, scanned_at DESC
)
SELECT COUNT(*) FILTER (WHERE canonical_status != 'DELIVERED') AS backlog_count
FROM final_status
```

## Rate computation

### Rate formula

A rate is always a numerator divided by a denominator. The request facts
specify the denominator explicitly:

    rate = numerator / denominator

Round only final rates unless the policy says otherwise. Carry full precision
through intermediate steps:

```sql
SELECT
  ROUND(
    COUNT(*) FILTER (WHERE is_on_time_complete = 1)::numeric
      / NULLIF(COUNT(*), 0),
    4
  ) AS on_time_complete_order_rate
FROM eligible_orders
```

`NULLIF(denominator, 0)` prevents division-by-zero. When the denominator is
zero, the rate is undefined; the task may expect 0, NULL, or an absent field.
Check the answer template's `minimum` constraint for guidance.

### Regional rates

When computing rates per region, use the unrounded values for ranking and
round only the final reported values:

```sql
WITH regional AS (
  SELECT
    region,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE is_on_time_complete = 1) AS on_time,
    COUNT(*) FILTER (WHERE is_on_time_complete = 1)::numeric
      / NULLIF(COUNT(*), 0) AS raw_rate
  FROM eligible
  GROUP BY region
)
SELECT
  region,
  ROUND(raw_rate, 4) AS on_time_complete_order_rate
FROM regional
ORDER BY raw_rate ASC, region ASC
LIMIT 2
```

Note: `ORDER BY` uses the unrounded value for ranking, while the SELECT
outputs the rounded value as required by the answer template.

## Ranking and ordering

### Top/bottom N with tie-breakers

When the request facts specify ranking with multiple tie-breakers:

```sql
ORDER BY
  primary_metric DESC,   -- or ASC for "worst"
  tiebreaker_1 ASC,      -- typically an identifier
  tiebreaker_2 ASC
LIMIT N
```

For "worst" rankings, the primary metric is ordered ASC (worst first). For
"best" rankings, it's ordered DESC.

Always include every tie-breaker from the request facts, in the documented
order. A missing tie-breaker produces non-deterministic results.

### Per-group ranking

When ranking within groups (e.g. employees within a warehouse):

```sql
SELECT
  employee_id,
  units_per_hour,
  ROW_NUMBER() OVER (ORDER BY units_per_hour DESC, employee_id ASC) AS rank
FROM employee_metrics
```

## FX conversion

When comparing amounts across currencies, join with the daily FX rates table:

```sql
SELECT
  r.refund_id,
  r.amount * fx.usd_per_unit AS amount_usd
FROM refunds r
JOIN fx_rates fx
  ON fx.rate_date = r.service_date
  AND fx.currency = r.currency
```

Key edge case: if a refund's service_date has no matching FX rate, the row
drops from the JOIN. Check that all service dates have coverage, or use
`LEFT JOIN` and decide how to handle NULL.

For multi-currency comparisons (e.g. order gross in order currency vs refund
in refund currency), apply the same FX rate to both values so the comparison
is fair:

```sql
-- Both valued at the refund's service_date rate
order_gross_in_order_currency * fx.usd_per_unit AS order_gross_usd,
refund_amount * fx.usd_per_unit AS refund_amount_usd
```

## Tiered status and risk classification

Classification rules are applied in priority order. The first matching tier
wins. Build this as a CASE expression with the most restrictive tier first:

```sql
CASE
  WHEN rate >= 0.88 AND severe_rate < 0.05 THEN 'HEALTHY'
  WHEN rate >= 0.78 AND severe_rate < 0.12 THEN 'WATCH'
  ELSE 'CRITICAL'
END AS overall_status
```

For multi-condition tiers where an "otherwise" tier catches everything:

```sql
CASE
  WHEN candidate_pct < 0.02 AND net_refund < 20000 THEN 'LOW'
  WHEN candidate_pct < 0.05 AND net_refund < 50000 THEN 'MODERATE'
  ELSE 'HIGH'
END AS cohort_risk
```

The request facts define tiers with explicit thresholds. Always use `<` and
`>=` exactly as the facts specify. When the facts say "below", use `<`. When
they say "at least", use `>=`.

## Median computation

When computing a median over a set of values:

```sql
SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY active_hours) AS median_hours
FROM resolved_cases
```

If `PERCENTILE_CONT` is not available, compute manually: order the values,
find the middle position(s), and average for even counts. `PERCENTILE_CONT`
handles the even-count averaging automatically.

Always verify: for an odd count, the median is a single value. For an even
count, the request facts typically specify "average the two central values,"
which is what `PERCENTILE_CONT` does.

## Pre/post correction comparison

For data-correction tasks that require comparing state before and after a
mutation:

1. **Pre-check**: Query the state before the correction. Capture the specific
   row(s) that will change and the baseline metrics (e.g. backlog count).
2. **Apply**: Use `POST /api/sql/transaction` with a precise WHERE clause that
   targets exactly one row. Verify the response shows `affected_business_rows: 1`
   and `audit_rows: 1`.
3. **Post-check**: Query the same metrics again. Compute the delta.
4. **Audit verification**: Query `GET /api/correction-audit` with the audit_id
   or correction_key to confirm the audit record contains the expected
   old_value, new_value, and metadata.

```sql
-- Step 1: Pre-check
SELECT COUNT(*) FILTER (WHERE final_status != 'DELIVERED') AS pre_backlog
FROM final_status_view;

-- Step 2: Apply (via /api/sql/transaction)
UPDATE carrier_scans
SET canonical_status = 'DELIVERED'
WHERE scan_row_id = '<scan_row_id>';

-- Step 3: Post-check
SELECT COUNT(*) FILTER (WHERE final_status != 'DELIVERED') AS post_backlog
FROM final_status_view;

-- Step 4: Audit
GET /api/correction-audit?correction_key=<correction_key>
```

The correction_status is `APPLIED` only when both conditions hold: exactly one
business row and one audit row committed, and a post-change query confirms the
corrected canonical value.

## Array output ordering

When constructing arrays for the answer template:

- For IDs sorted ascending: `ORDER BY id ASC`
- For ranked items with tie-breakers: apply every tie-breaker in the documented
  order
- For arrays with a fixed size: use `LIMIT N` and verify the result has exactly
  N elements

If the result has fewer elements than the template requires, the data simply
does not have enough candidates. Report what exists but verify against the
template's `minItems` constraint.

## Common NULL pitfalls

- **NULL in date comparisons**: `NULL > some_date` evaluates to NULL (not
  false), which drops the row from a WHERE clause. Always guard with
  `IS NOT NULL` or use `COALESCE`.
- **NULL in CASE expressions**: A CASE without ELSE returns NULL for unmatched
  branches. Always add `ELSE 0` or `ELSE 'UNKNOWN'` for classification CASEs.
- **NULL in aggregates**: `COUNT(*)` includes NULLs; `COUNT(col)` excludes
  them. Choose deliberately.
- **NULL in rate denominators**: `NULLIF(denominator, 0)` prevents division by
  zero but returns NULL. Handle this case in the answer template.
