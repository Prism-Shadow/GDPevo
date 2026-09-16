# Computation Patterns

## Rounding

Only round final reported values. Keep all intermediate values at full
precision through every step of the calculation.

### Rate rounding

Rates are typically rounded to 4 decimal places using standard
half-up rounding:

```python
rounded = round(raw_rate, 4)
```

### Currency rounding

Currency values are rounded to 2 decimal places:

```python
rounded = round(amount_usd, 2)
```

### Hours rounding

Time-based values are rounded to 2 decimal places:

```python
rounded = round(hours, 2)
```

## Multi-level sorting with tiebreakers

When the payload specifies multiple sort keys, apply them in order.
A tiebreaker only distinguishes items that are equal on all preceding keys.

Example: "rank by rate ascending, then region ascending"

```python
# Sort by primary key first, then tiebreaker
sorted_items = sorted(items, key=lambda x: (x['rate'], x['region']))
```

When one key is descending and another ascending, negate the numeric
descending key for Python sorting:

```python
sorted_items = sorted(
    items,
    key=lambda x: (-x['net_refund_usd'], x['reason_code'])
)
```

### Top-N selection

After sorting, take the first N items. Every item that makes the cut
must be included — if the Nth and (N+1)th tie on all sort keys, the
payload may require exactly N, so rely on the secondary/tertiary
tiebreaker to resolve the fixed-size result.

## Tiered status classification

Status rules are evaluated in order. Check the first rule's condition;
if it passes, that is the status. Only move to the next rule if the
condition does not pass. The final tier is the catch-all ("otherwise").

Example: HEALTHY / WATCH / CRITICAL

```python
if on_time_rate >= 0.88 and severe_rate < 0.05:
    status = "HEALTHY"
elif on_time_rate >= 0.78 and severe_rate < 0.12:
    status = "WATCH"
else:
    status = "CRITICAL"
```

Use the unrounded rates for condition checks — rounding is only for
display in the answer.

## Rate calculations

### Basic rate

A rate is numerator divided by denominator, where the denominator is
the eligible population:

```python
rate = numerator / denominator
```

Incomplete items stay in the denominator unless the payload
explicitly excludes them.

### Severe exception identification

When an exception condition has two branches (incomplete with late
promise, or complete with late delivery), compute each branch
separately and union the results:

1. Incomplete orders where cutoff > latest_promise + 24h (and latest_promise is not NULL)
2. Complete orders where any shipment was delivered > promise + 24h

An incomplete order with no shipment promise does not satisfy branch 1.

## Median calculation

For an odd count: the middle value of the sorted list.
For an even count: the average of the two middle values.

```python
def median(values):
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 0:
        return 0
    if n % 2 == 1:
        return sorted_vals[n // 2]
    else:
        return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
```

## Least / worst selection

When selecting the lowest performer or worst region:

- Rank by the metric ascending (lowest = worst)
- Tiebreaker by identifier ascending

```python
sorted_regions = sorted(
    regions,
    key=lambda x: (x['raw_rate'], x['region'])
)
worst_two = sorted_regions[:2]
```

## Correction success determination

After a data correction transaction:

1. Confirm `affected_business_rows == 1` AND `audit_rows == 1`
2. Run a post-correction SELECT to confirm the new canonical value is
   present in the target row
3. Verify the audit record via GET /api/correction-audit matches

Report `APPLIED` only when all three checks pass. Otherwise
`NOT_APPLIED` — even if the mutation partially succeeded.

## Currency netting

When computing net refund amounts:

```python
net_usd = sum(refund_usd for each refund) - sum(reversal_usd for each linked reversal)
```

Convert each individual refund and reversal to USD first using its
service_date FX rate, then sum the USD values.

Do not net in source currency and then convert — the FX rates may
differ across service dates.
