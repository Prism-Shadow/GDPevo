# Query & computation patterns

Reusable shapes. Replace bracketed names with the real tables/columns from `/api/schema`
and `/api/data-dictionary`. Keep each `/api/sql` call to a single statement (no semicolon).

## Calling the service

```bash
BASE=$(grep -oP 'Base URL:\s*\K\S+' environment_access.md)
TOKEN=$(grep -oP 'Bearer\s+\K\S+' environment_access.md)

curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/schema"
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/data-dictionary"

curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -X POST "$BASE/api/sql" -d '{"sql":"SELECT ..."}'
```

Response: `{"columns":[...],"rows":[[...]],"row_count":N,"truncated":false}`.
If `truncated` is true, you hit a row cap — aggregate in SQL or paginate.

## Eligible population as a CTE (compose everything else on it)

```sql
WITH eligible AS (
  SELECT o.*
  FROM [orders] o
  WHERE o.[is_production] = true          -- production population
    AND o.[campaign_id]   = '<from request>'
    AND o.[created_at] >= '<window.start>' -- inclusive
    AND o.[created_at] <= '<window.end>'   -- inclusive, exact UTC
)
SELECT count(*) AS eligible_count FROM eligible
```

## State evaluated at the cutoff (not "now")

Compare the state-driving timestamp to the cutoff, using the canonical/effective column:

```sql
-- "complete by cutoff": has >=1 shipment AND every shipment effectively delivered <= cutoff
... WHERE NOT EXISTS (
      SELECT 1 FROM [shipments] s
      WHERE s.[order_id] = e.[order_id]
        AND (s.[effective_status] <> 'DELIVERED' OR s.[delivered_at] > '<cutoff>')
    )
  AND EXISTS (SELECT 1 FROM [shipments] s WHERE s.[order_id] = e.[order_id])
```

## Rate on unrounded values, rounded once at the end

```sql
SELECT round(
         sum(case when [qualifies] then 1 else 0 end)::numeric
         / nullif(count(*),0), 4) AS on_time_rate   -- denominator = full eligible set
FROM eligible
```
Round in the reporting step only; keep unrounded values for sorting and threshold checks.

## Ranking with deterministic tie-break, then slice

```sql
SELECT [region], [rate]
FROM regional_rates
ORDER BY [rate] ASC, [region] ASC      -- primary metric, then id/label ascending
LIMIT 2                                -- exact required size, after the full sort
```

## FX conversion per row (daily rate for that row's service_date + currency)

```sql
SELECT r.*, r.[amount] * fx.[usd_per_unit] AS amount_usd
FROM [refunds] r
JOIN [fx_rates] fx
  ON fx.[currency]     = r.[currency]
 AND fx.[rate_date]    = r.[service_date]
-- net = settled refunds minus linked reversals, valued the same way
```

## Median with even-count averaging

```sql
SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY [active_hours]), 2) AS median_hours
FROM resolved_eligible          -- percentile_cont averages the two central values for even n
```

## Correction task: locate, mutate one field, audit, verify

1. Find the single row where the canonical column contradicts its raw/source counterpart
   (scoped by the request's batch/warehouse/cutoff).
2. Apply the minimal fix + audit insert through `/api/sql/transaction` (discover its exact
   request shape from the schema/dictionary). Change **one canonical field on one row**;
   never touch raw/source or identity columns.
3. Insert the audit row using the request's constants verbatim (audit_id, correction_key,
   reason_code, actor, corrected_at) plus the row's entity/source/field/old/new.
4. Verify with a fresh `/api/sql` read + `/api/correction-audit`: exactly one business row and
   one audit row, new canonical value confirmed. Only then report `APPLIED`.

## Classification (first match wins)

```
if rate_a >= T1 and rate_b <  T2: STATUS_1        # e.g. HEALTHY / STABLE / CONTROLLED / LOW
elif rate_a >= T3 and rate_b < T4: STATUS_2        # WATCH / PRESSURED / ELEVATED / MODERATE
else: STATUS_3                                     # CRITICAL / AT_RISK / SEVERE / HIGH
```
Evaluate in the request's listed order; honor exact operators; last status is the catch-all.
