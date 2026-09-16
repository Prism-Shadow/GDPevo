## SQL Patterns

These patterns recur across Atlas Commerce Operations analytical tasks. They
are starting points, not copy-paste templates — always reconcile with the
actual schema returned by GET /api/schema.

### Cutoff-based eligibility

When a request defines a cutoff_at or as_of_cutoff, use it as an upper bound in
WHERE clauses. Time-zone-naive UTC columns are the norm. Window eligibility
(created_at, opened_at, service_date) often uses inclusive boundaries.

```sql
SELECT ...
FROM   orders o
WHERE  o.campaign_id = ?
AND    o.created_at >= ?
AND    o.created_at <= ?
```

### Effective-final status

When a request says "use the effective/current/final status" of an entity that
can have multiple lifecycle rows, pick the row with the latest effective
timestamp at or before the cutoff. Use a subquery or window function:

```sql
SELECT o.id, s.status
FROM orders o
LEFT JOIN LATERAL (
  SELECT status
  FROM   shipment_status_log sl
  WHERE  sl.shipment_id = s.shipment_id
  AND    sl.recorded_at <= ?
  ORDER BY sl.recorded_at DESC
  LIMIT 1
) latest ON true
```

### Tiered status classification

Requests often define status tiers (HEALTHY/WATCH/CRITICAL etc.) with numeric
thresholds. Compute the raw metrics first, then apply the tier:

1. Run one or more aggregation queries to produce scalars (rates, counts).
2. Evaluate each tier condition in order (first-match-wins).
3. Assign the first matching tier; fall through to the default.

Do this in application code after retrieving the aggregates. Avoid encoding
the specific threshold values as a reusable skill rule — they vary by request.

### Ranking and tie-breaking

When a request says "top N by X desc, then Y asc", compute the values and sort
outside the DB. Use the exact unrounded scalar for primary ordering and fall
back to the explicit tie-break attribute. Example:

```python
regions.sort(key=lambda r: (r["unrounded_rate"], r["region"]))
```

### Severe / exception / leakage classification

These are multi-condition boolean classifications applied per-entity:

- Compute each candidate condition as a separate boolean per row.
- Combine conditions with OR (any match = candidate) unless AND is specified.
- Collect qualifying IDs, sort ascending, and report.

### Breach detection against SLA thresholds

When a request defines per-priority SLA thresholds (e.g. first_response,
resolution_active_time), compare each case against its own priority threshold.
For unresolved cases, use the elapsed clock at the cutoff as the current value.

### Rounding and precision

Only round final reported values. Keep intermediate aggregations at full
precision until the final assignment. Rounding rules are always defined in
the request payload, not in the skill.

### Ordered output arrays

When a request requires arrays of objects sorted by specific keys, prefer
Python `sorted()` over SQL ORDER BY when multiple ordering tiers are involved.
This keeps the ordering logic transparent and unit-testable.

### Rate calculation

Divide the qualifying numerator by the full eligible denominator. Unless the
request explicitly excludes a subgroup from the denominator, include it even if
it contributes zero to the numerator. Example:

```python
rate = qualifying_count / eligible_count  # not / (eligible_count - something)
```

### Correction transaction pattern

See [transaction_protocol.md](transaction_protocol.md) for the full correction
workflow. Key points:

- Identify the exact row and column to change via a read-only query.
- Construct the UPDATE and INSERT audit statements.
- Submit via POST /api/sql/transaction with the approved reason_code and
  correction_key.
- Verify by re-querying the changed row and the audit endpoint.
