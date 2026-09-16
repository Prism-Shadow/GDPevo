# Atlas Commerce Operations — Reusable Solution Patterns

These patterns repeat across task types. Apply the appropriate pattern for each
task, adapting to the request's specific business definitions.

---

## General Patterns

### Production population filter

Every task scoping "production" data must exclude internal and test accounts:

```sql
JOIN accounts a ON ... AND a.is_internal = 0 AND a.is_test = 0
```

If the request further restricts by segment, tier, or region, add those
to the same JOIN or WHERE clause. The production filter applies first.

### UTC window filtering

Windows in requests use ISO-8601 UTC and are inclusive unless stated otherwise.
Compare timestamps lexicographically:

```sql
WHERE t.created_at >= '2026-04-06T00:00:00Z'
  AND t.created_at <= '2026-04-12T23:59:59Z'
```

For date-only windows, compare as YYYY-MM-DD strings:

```sql
WHERE r.service_date >= '2026-03-01'
  AND r.service_date <= '2026-04-30'
```

### Effective final per entity

When "effective" rows are needed per entity, use window functions to pick the
latest by timestamp. For carrier scans:

```sql
WITH ranked_scans AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY shipment_id
      ORDER BY canonical_event_at DESC, scan_row_id ASC
    ) AS rn
  FROM carrier_scans
)
SELECT * FROM ranked_scans WHERE rn = 1
```

The tie-breaker is always the primary key ascending.

### Event-driven state (do not trust current_status)

orders.current_status, shipments.current_status, support_cases.current_status,
and warehouse_tasks.current_status are convenience snapshots that may lag.
Always derive state from the append-only event tables:

- Case state: Scan case_events for the latest OPENED/REOPENED/RESOLVED/CLOSED per case.
- Task completion: Check for a COMPLETED event in warehouse_task_events.
- Order/shipment completion: Use carrier scan canonical_status, not order/shipment current_status.

### FX conversion (money)

Convert monetary minor values to USD:

1. Divide amount_minor by 100 to get the display amount in the row currency.
2. Join fx_rates on rate_date = date column and currency to get usd_per_unit.
3. Multiply: (amount_minor / 100.0) * fx.usd_per_unit.

Use the relevant date for each row (e.g., refund service_date, payment event_at
date). Round only final monetary results to the decimal places in the request.

### Ranking

Multi-key ordering applies sorts in priority order. For top-N lists, compute the
metric for every candidate, apply the full sort, and take the first N.

### Tiered classification

Requests define status/risk rules as ordered conditions. Evaluate sequentially;
the first rule whose conditions are all true wins. The final rule is the catch-all.

### Rounding

Round only final reported rates and monetary amounts. Intermediate values remain
at full precision.

---

## Fulfillment Campaign Scorecard

### Eligible orders

```sql
SELECT o.order_id, o.promised_at, o.warehouse_id, w.region
FROM orders o
JOIN accounts a ON o.account_id = a.account_id
  AND a.is_internal = 0 AND a.is_test = 0
JOIN warehouses w ON o.warehouse_id = w.warehouse_id
JOIN campaigns c ON o.campaign_id = c.campaign_id
WHERE c.campaign_id = '<campaign_id>'
  AND o.order_created_at >= c.starts_at
  AND o.order_created_at <= c.ends_at
```

### Completion

An order is complete when it has at least one physical shipment AND every
shipment effective final carrier scan has canonical_status = DELIVERED at
or before the cutoff. Orders with no shipments are incomplete.

### On-time completion

A complete order is on time only when every shipment final delivered time is
<= that shipment promised_delivery_at. Use canonical_event_at of the final
DELIVERED scan as the delivered time.

### Severe exceptions

Two conditions, either makes an order severe:

- Incomplete and late: order incomplete AND cutoff > 24 hours past the latest
  promised_delivery_at among its shipments. An incomplete order with no shipments
  (no shipment promise) does NOT satisfy this.
- Late delivery: any shipment delivered > 24 hours past its promise.

### Regional rates

Group eligible orders by warehouse.region. Compute each region on-time
complete-order rate against its own eligible order count.

### Worst regions

Sort regions by unrounded on-time complete-order rate ascending, then region
ascending. Take the first two.

---

## Refund Settlement Reconciliation

### Eligible refunded orders

Distinct in-scope orders with at least one effective settled logical refund:

```sql
SELECT DISTINCT r.order_id
FROM refund_attempts r
JOIN orders o ON r.order_id = o.order_id
JOIN accounts a ON o.account_id = a.account_id
  AND a.is_internal = 0 AND a.is_test = 0
  AND a.tier = '<tier>'
WHERE r.status = 'SETTLED'
  AND r.linked_refund_id IS NULL
  AND r.service_date >= '<start>'
  AND r.service_date <= '<end>'
```

### Effective settled logical refunds

status = SETTLED AND linked_refund_id IS NULL. These are the positive amounts.

### Effective linked reversals

status = SETTLED AND linked_refund_id IS NOT NULL. These offset refund amounts.

### Net refund USD

For each effective settled refund: (amount_minor / 100.0) * fx.usd_per_unit.
For each effective reversal: same conversion.
Net = sum(refunds USD) - sum(reversals USD). Round to 2 decimal places.
Join fx_rates on rate_date = service_date and the row currency.

### Leakage candidates

An order is a leakage candidate if either:

- Net refund USD > gross order USD (convert gross using same service_date rate)
- At least two unreversed effective settled logical refunds with the same
  normalized reason_code

For gross comparison, value the order gross_amount_minor in its order currency
at the settled refund service_date rate. Output candidate order_ids sorted ascending.

### Reason ranking

For each reason_code, sum net refund USD across effective settled refunds with
that code. Sort by net USD descending, then reason_code ascending. Take top N.

### Cohort risk

leakage_rate = leakage_candidates / eligible_refunded_orders.
Evaluate risk rules in order: check each rule condition against both rate and
net_refund_amount threshold. The first satisfied rule wins.

---

## Carrier Quality Correction

### Finding the contradiction

1. Get carrier_scans for the named import_batch_id.
2. Compute effective final scan per shipment (latest canonical_event_at, tie-break
   scan_row_id ASC).
3. Find the single scan where raw_status != canonical_status. This is the
   contradiction. The request says exactly one exists.

### Determining the correction value

The canonical value to use is the raw_status. For carrier quality, the raw
carrier event is the trusted source: set canonical_status = raw_status.

### The transaction

Construct exactly one UPDATE and one INSERT:

```sql
UPDATE carrier_scans
SET canonical_status = '<new_value>',
    corrected_at = '<corrected_at>',
    correction_reason = '<reason_code>'
WHERE scan_row_id = '<scan_row_id>'

INSERT INTO correction_audit
  (audit_id, correction_key, entity_type, entity_id, source_row_id,
   field_name, old_value, new_value, reason_code, corrected_at, actor)
VALUES
  ('<audit_id>', '<correction_key>', 'carrier_scan', '<shipment_id>',
   '<scan_row_id>', 'canonical_status', '<old_value>', '<new_value>',
   '<reason_code>', '<corrected_at>', '<actor>')
```

All parameter values come from the request approved_correction block.
Submit as {"transaction": ["<update>", "<insert>"]} to POST /api/sql/transaction.

### Verification

After the transaction, call GET /api/correction-audit and verify the audit
record matches approved parameters. Run a POST /api/sql query to confirm the
corrected row canonical_status is now the new value.

### Correction status

APPLIED only if affected_business_rows = 1 AND audit_rows = 1 AND post-change
query confirms the corrected canonical value. Otherwise NOT_APPLIED.

### Backlog analysis

Pre-correction: Count shipments in the cohort (having an effective scan in the
named batch at or before cutoff) whose effective final carrier status is NOT
DELIVERED.

Post-correction: Re-run after the transaction. Count delivered the same way
(effective final status IS DELIVERED).

backlog_delta = post_backlog_count - pre_backlog_count.

---

## Warehouse Productivity

### Eligible production tasks

```sql
SELECT t.task_id, t.assigned_employee_id, t.task_type, t.work_class,
       t.priority, t.planned_units, t.created_at, t.due_at,
       e.team_id
FROM warehouse_tasks t
JOIN employees e ON t.assigned_employee_id = e.employee_id
WHERE t.warehouse_id = '<warehouse_id>'
  AND t.work_class = 'PRODUCTION'
  AND t.created_at >= '<start_at>'
  AND t.created_at <= '<end_at>'
```

work_class = PRODUCTION filters production tasks. TRAINING tasks excluded.

### Task completion

A task is completed when a COMPLETED event exists in warehouse_task_events.
Do not use warehouse_tasks.current_status. Multiple COMPLETED events may exist;
sum units and productive_minutes.

### Units per hour

For each employee: sum units from their COMPLETED task events, sum
productive_minutes from those events.
units_per_hour = (total_units / total_minutes) * 60.0 if total_minutes > 0.
Round to 2 decimal places.

### Completion rate

completed_task_count / eligible_production_task_count. A task counts as
completed if it has at least one COMPLETED event.

### Rework rate

Rework tasks divided by eligible production tasks. Round to 4 decimal places.

### Delayed high-priority tasks

HIGH or URGENT tasks with due_at strictly before the state cutoff that are NOT
completed by the cutoff. Output task_ids sorted ascending.

### Employee ranking

Rank by units_per_hour descending, then employee_id ascending. Take top 3.

### Team ranking

Group by team_id. Compute each team completion rate. Sort by completion rate
ascending, then team_id ascending. Take the lowest.

### Facility status

Evaluate tiered rules using completion_rate and rework_rate.

---

## Support Health Review

### Eligible cases

```sql
SELECT sc.case_id, sc.account_id, sc.priority, sc.opened_at
FROM support_cases sc
JOIN accounts a ON sc.account_id = a.account_id
  AND a.is_internal = 0 AND a.is_test = 0
  AND a.segment = 'ENTERPRISE'
  AND a.region IN ('NORTH', 'EAST')
WHERE sc.opened_at >= '<start_at>'
  AND sc.opened_at <= '<end_at>'
```

### Active-time clock

The clock runs only during active support time. Compute from case_events:

1. Get all events for each case, ordered by event_at.
2. The clock runs between events where the actor is AGENT or SYSTEM, or before
   first response. It pauses when actor is CUSTOMER.
3. Sum time gaps between consecutive events where the clock is running.

For unresolved cases, compute active elapsed time from opened_at to cutoff
using the same active-time logic.

### Event-derived case state

- First agent response time: time from OPENED to first AGENT_RESPONSE.
- Resolution time: active time from OPENED to RESOLVED.
- Open at cutoff: last event before cutoff was OPENED or REOPENED and no
  subsequent RESOLVED/CLOSED before cutoff.
- Reopened: open at cutoff AND a REOPENED event occurred after a RESOLVED.

### First-response breach

Active time to first agent response exceeds the priority threshold. An
unresponded case uses active elapsed time at cutoff.

### Resolution breach

Active time to resolution exceeds the priority threshold. An unresolved
(open at cutoff) case uses active elapsed time at cutoff.

### Severe active cases

Open or reopened at cutoff, priority URGENT or HIGH, AND beyond the active-time
resolution threshold.

### Median active resolution hours

For resolved cases at cutoff: compute active resolution time in hours. Sort.
For odd count, take the central value. For even, average the two central values.
Round to 2 decimal places.

### Worst accounts

For each account: count severe active cases and active-clock resolution breaches.
Sort by severe count descending, breach count descending, account_id ascending.
Take top 3.

### Support risk

severe_rate = severe_active_case_count / eligible_case_count.
breach_rate = first_response_breach_count / eligible_case_count.
Evaluate tiered risk rules in order using both rates.
