# Atlas Commerce Analytical Patterns

Reusable query patterns for the five core Atlas analytical workflows. Read this when the task matches one of these domains.

## 1. Fulfillment Scorecard

**Request shape**: Campaign-scoped, cutoff-based, with order completion definitions, on-time rules, severe exception criteria, regional rollups, and tiered overall status.

### Campaign Orders

```sql
SELECT o.*, c.starts_at, c.ends_at
FROM orders o
JOIN campaigns c ON c.campaign_id = o.campaign_id
JOIN accounts a ON a.account_id = o.account_id
WHERE a.is_internal = 0 AND a.is_test = 0
  AND o.campaign_id = ?  -- campaign_id from request payload
  AND o.order_created_at >= c.starts_at
  AND o.order_created_at <= c.ends_at
```

### Shipment Delivery State per Order

The canonical delivery status for a shipment is determined from the latest effective carrier scan. Do not rely on `shipments.current_status` alone.

```sql
WITH dedup_scans AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at DESC
  ) AS rn
  FROM carrier_scans
),
effective_scans AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY shipment_id
    ORDER BY canonical_event_at DESC, scan_row_id DESC
  ) AS rn2
  FROM dedup_scans WHERE rn = 1
)
SELECT s.shipment_id, s.order_id, s.promised_delivery_at,
  es.canonical_status, es.canonical_event_at
FROM shipments s
LEFT JOIN effective_scans es ON es.shipment_id = s.shipment_id AND es.rn2 = 1
```

### Order Completion Logic

An order is complete when:
- It has at least one shipment, AND
- Every one of its shipments has an effective canonical status of `DELIVERED` by the cutoff.

```sql
-- Per order: count total shipments and delivered-by-cutoff shipments
WITH order_shipment_state AS (...),
order_delivery AS (
  SELECT order_id,
    COUNT(*) AS total_shipments,
    SUM(CASE WHEN canonical_status = 'DELIVERED'
         AND canonical_event_at <= ?  -- cutoff_at from request
         THEN 1 ELSE 0 END) AS delivered_shipments
  FROM order_shipment_state
  GROUP BY order_id
)
SELECT order_id, total_shipments, delivered_shipments,
  CASE WHEN total_shipments > 0 AND total_shipments = delivered_shipments
       THEN 1 ELSE 0 END AS is_complete
FROM order_delivery
```

### On-Time Check

A complete order is on time when EVERY shipment was delivered no later than its `promised_delivery_at`:

```sql
-- Per order: mark on-time if no shipment was late
CASE WHEN MAX(CASE WHEN canonical_event_at > promised_delivery_at
              THEN 1 ELSE 0 END) = 0 THEN 1 ELSE 0 END AS is_on_time
```

### Severe Exception

An order is a severe exception when:
- **Incomplete** AND cutoff > 24h after its latest shipment promise (only if promise exists), OR
- **Completed** with any shipment delivered > 24h after its promise.

### Worst Warehouse Regions

Compute the regional on-time complete-order rate (unrounded), then sort ascending by rate, then by region ascending. Take the first two.

### Overall Status

Compute `severe_exception_rate = severe_count / eligible_count` and compare against thresholds.

---

## 2. Refund Reconciliation

**Request shape**: Account-tier scoped, date-range filtered, with FX conversion, leakage candidate rules, reason ranking, and tiered risk classification.

### Eligible Refunded Orders

Accounts in the named tier, production-only, with at least one effective settled logical refund in the service date range.

```sql
WITH dedup_refunds AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at DESC
  ) AS rn
  FROM refund_attempts
  WHERE status = 'SETTLED'
    AND service_date >= ?  -- service_date start from request
    AND service_date <= ?  -- service_date end from request
)
SELECT DISTINCT r.order_id
FROM dedup_refunds r
JOIN orders o ON o.order_id = r.order_id
JOIN accounts a ON a.account_id = o.account_id
WHERE a.is_internal = 0 AND a.is_test = 0
  AND a.tier = ?  -- account_tier from request
  AND r.rn = 1
```

### Logical Refund Count

Each `refund_id` with `linked_refund_id IS NULL` is one logical refund. Reversals are the rows where `linked_refund_id IS NOT NULL`.

### Net Refund USD

```sql
-- Per order: sum settled refunds, subtract reversals, convert to USD
WITH refund_usd AS (
  SELECT r.order_id, r.refund_id, r.linked_refund_id,
    r.amount_minor / 100.0 * f.usd_per_unit AS usd_amount
  FROM (deduplicated settled refunds) r
  JOIN fx_rates f ON f.rate_date = r.service_date AND f.currency = r.currency
)
SELECT order_id,
  SUM(CASE WHEN linked_refund_id IS NULL THEN usd_amount ELSE 0 END)
  - SUM(CASE WHEN linked_refund_id IS NOT NULL THEN usd_amount ELSE 0 END)
  AS net_usd
FROM refund_usd
GROUP BY order_id
```

### Leakage Candidates

```sql
-- Condition 1: net refund > order gross in USD
-- Condition 2: >= 2 unreversed logical refunds with same reason_code
SELECT DISTINCT order_id FROM (...) WHERE condition1 OR condition2
ORDER BY order_id ASC
```

### Top Two Reason Codes

Rank by effective net refund USD descending, then reason_code ascending.

### Cohort Risk

Based on `candidate_count / eligible_count` and net refund thresholds.

---

## 3. Carrier Quality Correction

**Request shape**: One batch, one warehouse, one cutoff, one approved correction with audit parameters.

### Finding the Contradiction

Query carrier_scans for the named batch and warehouse, compare raw_status with canonical_status, use deduplication and effective scan logic.

```sql
WITH dedup AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at DESC
  ) AS rn
  FROM carrier_scans
  WHERE import_batch_id = ?  -- import_batch_id from request
)
SELECT cs.*, s.shipment_id, s.warehouse_id
FROM dedup cs
JOIN shipments s ON s.shipment_id = cs.shipment_id
WHERE cs.rn = 1 AND s.warehouse_id = ?  -- warehouse_id from request
```

### Pre-Correction Backlog

Count shipments in the cohort whose effective final carrier status is not `DELIVERED` at the cutoff:

```sql
WITH effective AS (
  SELECT shipment_id, canonical_status, canonical_event_at,
    ROW_NUMBER() OVER (PARTITION BY shipment_id ORDER BY canonical_event_at DESC, scan_row_id DESC) AS rn
  FROM (deduplicated carrier_scans in cohort)
)
SELECT COUNT(*) FROM effective
WHERE rn = 1 AND canonical_status != 'DELIVERED'
```

### Transactional Correction

Use `POST /api/sql/transaction` with the full audit block. After committing, verify:
1. Re-query the corrected row to confirm the new value.
2. Check `/api/correction-audit` for the new audit record.

### Correction Status

`APPLIED` only when: exactly 1 business row + 1 audit row committed, and re-query confirms the new value.

---

## 4. Warehouse Productivity

**Request shape**: Single warehouse, task created window, state cutoff, with units-per-hour formula, completion/rework rates, delayed high-priority detection, team ranking, and facility status.

### Eligible Production Tasks

```sql
SELECT *
FROM warehouse_tasks
WHERE warehouse_id = ?  -- warehouse_id from request
  AND work_class = 'PRODUCTION'
  AND created_at >= ?  -- task_created_window start
  AND created_at <= ?  -- task_created_window end
```

### Task Completion

A task is completed when its `current_status` indicates completion by the state cutoff. Sum `units` from `warehouse_task_events` for completed tasks to get `completed_production_units`.

### Units Per Hour

```sql
-- Per employee:
-- 1. Sum units from warehouse_task_events for completed tasks assigned to that employee
-- 2. Sum productive_minutes from the same events
-- 3. units_per_hour = (total_units / total_productive_minutes) * 60
SELECT e.employee_id,
  SUM(te.units) AS total_units,
  SUM(te.productive_minutes) AS total_minutes,
  (SUM(te.units) * 60.0) / SUM(te.productive_minutes) AS units_per_hour
FROM employees e
JOIN warehouse_tasks t ON t.assigned_employee_id = e.employee_id
JOIN warehouse_task_events te ON te.task_id = t.task_id
WHERE e.warehouse_id = ?  -- warehouse_id from request
  AND t.work_class = 'PRODUCTION'
  AND t.created_at >= ... AND t.created_at <= ...
  AND t.current_status = 'COMPLETED'
GROUP BY e.employee_id
```

### Rework Rate

Rework tasks are those with `task_type = 'REWORK'`. Count them, divide by eligible production task count.

### Delayed High Priority Tasks

Tasks with `priority IN ('HIGH', 'URGENT')` AND `due_at < state_cutoff` AND `current_status != 'COMPLETED'`.

### Lowest Performing Team

Rank teams by `completion_rate ASC, team_id ASC`. Completion rate = completed tasks / eligible tasks for that team.

---

## 5. Support Health

**Request shape**: Account segment/region scoped, case opened window, cutoff, with priority SLA thresholds, active-time-based breach rules, severe case definition, worst account ranking, median resolution time, and risk classification.

### Eligible Cases

```sql
SELECT sc.*
FROM support_cases sc
JOIN accounts a ON a.account_id = sc.account_id
WHERE a.is_internal = 0 AND a.is_test = 0
  AND a.segment = ?  -- segment from request
  AND a.region IN (?  -- regions from request)
  AND sc.opened_at >= ?  -- case_opened_window start
  AND sc.opened_at <= ?  -- case_opened_window end
```

### Case State Summary

Open at cutoff: `current_status IN ('OPEN', 'REOPENED')`.
Reopened: subset where `current_status = 'REOPENED'`.

### First Response Breach

Compute `active_time_to_first_agent_response` from case_events. An unresponded case uses elapsed active time to the cutoff. Breach if exceeds the priority threshold.

### Resolution Breach

Compute `active_time_to_resolution` from case_events. An active (unresolved) case uses elapsed active time to the cutoff. Breach if exceeds the priority threshold.

### Severe Active Cases

`current_status IN ('OPEN', 'REOPENED')` AND `priority IN ('URGENT', 'HIGH')` AND `active_time_to_resolution > priority threshold`.

### Worst Accounts

Rank by `severe_active_case_count DESC`, `active_clock_breach_count DESC`, `account_id ASC`. Take three.

### Median Active Resolution Hours

Across cases `current_status = 'RESOLVED'` at cutoff, compute each case's active resolution hours (from opened to resolved, summing only active intervals). Take the median.

### Support Risk

Compute `severe_active_case_rate` and `first_response_breach_rate`. Compare against CONTROLLED/ELEVATED thresholds; otherwise SEVERE.
