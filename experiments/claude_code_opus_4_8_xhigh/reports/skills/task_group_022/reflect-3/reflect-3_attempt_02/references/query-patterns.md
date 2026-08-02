# Query patterns for Atlas Ops reporting

General, reusable SQL idioms for translating business definitions into precise,
read-only queries. Adapt names to whatever the schema/data-dictionary actually
expose — never assume table or column names.

## Discover before you query

- Pull the schema and data dictionary from the workplace first. Confirm the real
  table names, the exact column that holds each value, enum spellings, and which
  columns are *canonical/effective* vs *raw source*.
- Confirm the grain of each table (one row per order? per shipment? per scan? per
  refund line? per audit event?) before you aggregate — mixing grains
  double-counts.

## Build the cohort once, reuse it

Express eligibility as a single CTE and compute everything on top of it, so every
metric shares one denominator.

```sql
WITH eligible AS (
  SELECT ...            -- production population + tier/segment/region/warehouse
  FROM <entity>         -- + attribution (campaign/batch) + created/opened window
  WHERE <population predicate>
    AND <scope predicate>
    AND <created_at BETWEEN window.start AND window.end>   -- honor inclusivity
)
SELECT ... FROM eligible ...;
```

Treat request timestamps as exact UTC boundaries; match the stated inclusivity
(`BETWEEN` for inclusive both ends; use `>=` / `<` deliberately when a bound is
exclusive).

## "Every child satisfies P, and there is at least one child"

Do not express this with a plain join — that silently passes rows with zero
children. Use existence tests:

```sql
SELECT o.id
FROM eligible o
WHERE EXISTS (SELECT 1 FROM child c WHERE c.parent_id = o.id)
  AND NOT EXISTS (
    SELECT 1 FROM child c
    WHERE c.parent_id = o.id
      AND NOT (<P, e.g. c.effective_status = 'DELIVERED' AND c.delivered_at <= :cutoff>)
  );
```

## Canonical vs raw

Always drive metrics from the canonical/effective column; keep raw source columns
read-only and out of the business logic.

```sql
-- correct: use the canonical/effective value
WHERE effective_carrier_status <> 'DELIVERED'
-- wrong: never branch business logic on the raw source value
```

## Deadline / breach comparisons (with active clock to cutoff)

For resolved items use the actual event time; for still-active items the clock
runs to the cutoff, using the stated clock basis.

```sql
CASE
  WHEN <resolved> THEN <active_time_between(open, resolved)>
  ELSE            <active_time_between(open, :cutoff)>       -- elapsed at cutoff
END > :threshold_for_priority
```

Look for a stored "active time" measure or the components to compute it when the
clock basis is "active time" rather than wall-clock.

## Compound flags (severe / leakage / at-risk)

Encode each clause exactly, including carve-outs (e.g. "no promise ⇒ first clause
cannot be satisfied").

```sql
(<incomplete> AND <latest_promise IS NOT NULL> AND :cutoff > datetime(latest_promise,'+24 hours'))
OR
(<complete>   AND EXISTS(SELECT 1 FROM ship s WHERE s.order_id=o.id
                         AND s.delivered_at > datetime(s.promised_delivery_at,'+24 hours')))
```

## FX / money

Join each money row to the daily rate for *its own* service_date and currency,
convert to the reporting currency, then net and rank.

```sql
SELECT r.*, r.amount * fx.usd_per_unit AS amount_usd
FROM refund r
JOIN fx_rates fx ON fx.currency = r.currency AND fx.rate_date = r.service_date;
-- net = settled refunds - linked reversals, per order, before thresholding
```

## Ordering, tie-breaks, limits

Sort on unrounded values; apply the limit after ordering.

```sql
ORDER BY regional_rate ASC, region ASC              -- worst-N
ORDER BY net_usd DESC, reason_code ASC              -- top-N by value
ORDER BY severe_cnt DESC, breach_cnt DESC, id ASC   -- multi-key
LIMIT :n;
```

## Median (even count averages the two central values)

```sql
WITH v AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () n FROM eligible)
SELECT AVG(x) FROM v WHERE rn IN ((n+1)/2, (n+2)/2);   -- integer arithmetic
```

## Corrections (controlled transaction only)

- SELECT the one affected row first; capture old canonical value and the approved
  new value.
- In the transaction: `UPDATE` only the one canonical field on the one business
  row; `INSERT` exactly one audit row with the request-supplied
  reason_code/actor/audit_id/correction_key/corrected_at.
- After commit, SELECT again to confirm the canonical value and that exactly one
  business row and one audit row changed.
- Leave raw source values, identity fields, and unrelated rows unchanged.
