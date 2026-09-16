# Atlas Commerce Operations — Detailed Reference

This reference provides column-level guidance, worked SQL patterns for
deduplication and effective-event state, and domain-specific query templates.
Read it when the main skill description is not precise enough for the tables
you are working with.

## Table Relationships

### Core Entity Graph

```
accounts ──< orders ──< shipments ──< carrier_scans
                 │
                 ├──< order_lines ──< products
                 ├──< order_events
                 ├──< payment_events
                 ├──< refund_attempts (self-referencing via linked_refund_id)
                 ├──< warehouse_tasks ──< warehouse_task_events
                 └──< support_cases ──< case_events

campaigns ──< orders

warehouses ──< orders
warehouses ──< shipments
warehouses ──< warehouse_tasks
warehouses ──< employees
warehouses ──< inventory_snapshots
warehouses ──< inventory_movements

source_import_batches ──< carrier_scans

fx_rates (standalone, keyed by rate_date + currency)
```

### Foreign-Key Columns

| Child Table           | FK Column          | Parent Table         |
|-----------------------|--------------------|----------------------|
| orders                | account_id         | accounts             |
| orders                | campaign_id        | campaigns (nullable) |
| orders                | warehouse_id       | warehouses           |
| shipments             | order_id           | orders               |
| shipments             | warehouse_id       | warehouses           |
| carrier_scans         | shipment_id        | shipments            |
| carrier_scans         | import_batch_id    | source_import_batches|
| order_lines           | order_id           | orders               |
| order_lines           | sku                | products             |
| order_events          | order_id           | orders               |
| payment_events        | order_id           | orders               |
| refund_attempts       | order_id           | orders               |
| refund_attempts       | linked_refund_id   | refund_attempts      |
| support_cases         | account_id         | accounts             |
| support_cases         | order_id           | orders (nullable)    |
| case_events           | case_id            | support_cases        |
| warehouse_tasks       | warehouse_id       | warehouses           |
| warehouse_tasks       | order_id           | orders (nullable)    |
| warehouse_tasks       | sku                | products (nullable)  |
| warehouse_tasks       | assigned_employee_id| employees           |
| warehouse_task_events | task_id            | warehouse_tasks      |
| employees             | warehouse_id       | warehouses           |
| employees             | team_id            | (opaque team label)  |
| inventory_movements   | warehouse_id       | warehouses           |
| inventory_movements   | sku                | products             |
| inventory_snapshots   | warehouse_id       | warehouses           |
| inventory_snapshots   | sku                | products             |
| correction_audit      | (entity_type, entity_id) | domain tables   |
| correction_audit      | source_row_id      | carrier_scans, etc.  |

## Deduplication — Worked Examples

### Single-Table Dedup

```sql
WITH dedup_scans AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY source_system, external_event_id
      ORDER BY ingested_at DESC
    ) AS rn
  FROM carrier_scans
)
SELECT scan_row_id, shipment_id, canonical_status, canonical_event_at
FROM dedup_scans
WHERE rn = 1
```

### Dedup Then Apply Cutoff

```sql
WITH dedup_scans AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY source_system, external_event_id
      ORDER BY ingested_at DESC
    ) AS rn
  FROM carrier_scans
),
effective_scans AS (
  SELECT * FROM dedup_scans WHERE rn = 1
)
SELECT *
FROM effective_scans
WHERE canonical_event_at <= '2026-04-15T23:59:59Z'
```

### Dedup Then Get Latest Per Entity (Effective State)

```sql
WITH dedup_events AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY source_system, external_event_id
      ORDER BY ingested_at DESC
    ) AS rn
  FROM warehouse_task_events
),
effective_events AS (
  SELECT * FROM dedup_events WHERE rn = 1
),
latest_per_task AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY task_id
      ORDER BY event_at DESC
    ) AS rn2
  FROM effective_events
  WHERE event_at <= '2026-04-13T23:59:59Z'
)
SELECT * FROM latest_per_task WHERE rn2 = 1
```

## Effective Shipment Delivery Status

This is the canonical pattern for determining whether a shipment was delivered
by a cutoff and whether it was on time.

```sql
WITH dedup_scans AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY source_system, external_event_id
      ORDER BY ingested_at DESC
    ) AS rn
  FROM carrier_scans
),
effective_scans AS (
  SELECT * FROM dedup_scans WHERE rn = 1
),
shipment_status AS (
  SELECT
    s.shipment_id,
    s.order_id,
    s.promised_delivery_at,
    es.canonical_status,
    es.canonical_event_at,
    ROW_NUMBER() OVER (
      PARTITION BY s.shipment_id
      ORDER BY es.canonical_event_at DESC
    ) AS rn_shipment
  FROM shipments s
  JOIN effective_scans es ON es.shipment_id = s.shipment_id
  WHERE es.canonical_event_at <= '<CUTOFF>'
)
SELECT * FROM shipment_status WHERE rn_shipment = 1
```

An order is complete when every one of its shipments has
`canonical_status = 'DELIVERED'`. An order with no shipment rows is incomplete.

An order is on time when every one of its shipments has
`canonical_status = 'DELIVERED'` AND
`canonical_event_at <= promised_delivery_at`.

## Currency and FX

The `fx_rates` table maps `(rate_date, currency)` to `usd_per_unit`.

```sql
-- Refund USD value
SELECT
  r.refund_id,
  r.order_id,
  (r.amount_minor / 100.0) * f.usd_per_unit AS refund_usd
FROM refund_attempts r
JOIN fx_rates f ON f.rate_date = r.service_date AND f.currency = r.currency
WHERE r.status = 'SETTLED'

-- Order gross in USD at refund service date
SELECT
  o.order_id,
  (o.gross_amount_minor / 100.0) * f.usd_per_unit AS order_gross_usd
FROM orders o
JOIN fx_rates f ON f.rate_date = '<REFUND_SERVICE_DATE>' AND f.currency = o.currency
```

## Refund Reconciliation — Full Pattern

```sql
WITH eligible_accounts AS (
  SELECT account_id FROM accounts
  WHERE tier = 'GOLD' AND is_internal = 0 AND is_test = 0
),
eligible_orders AS (
  SELECT o.order_id, o.gross_amount_minor, o.currency
  FROM orders o
  JOIN eligible_accounts a ON o.account_id = a.account_id
),
dedup_refunds AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY source_system, external_event_id
      ORDER BY ingested_at DESC
    ) AS rn
  FROM refund_attempts
),
effective_refunds AS (
  SELECT r.*
  FROM dedup_refunds r
  JOIN eligible_orders o ON r.order_id = o.order_id
  WHERE r.rn = 1
    AND r.status = 'SETTLED'
    AND r.service_date BETWEEN '2026-03-01' AND '2026-04-30'
),
refund_with_fx AS (
  SELECT
    r.refund_id, r.order_id, r.reason_code,
    (r.amount_minor / 100.0) * f.usd_per_unit AS refund_usd
  FROM effective_refunds r
  JOIN fx_rates f ON f.rate_date = r.service_date AND f.currency = r.currency
),
-- Identify reversals: refunds whose refund_id is linked_refund_id of another SETTLED refund
reversal_ids AS (
  SELECT DISTINCT r.linked_refund_id AS refund_id
  FROM effective_refunds r
  WHERE r.linked_refund_id IS NOT NULL
),
reversals AS (
  SELECT rf.* FROM refund_with_fx rf
  JOIN reversal_ids rev ON rf.refund_id = rev.refund_id
),
net_per_order AS (
  SELECT
    rf.order_id,
    COUNT(DISTINCT rf.refund_id) AS refund_count,
    SUM(rf.refund_usd) - COALESCE(SUM(rv.refund_usd), 0) AS net_refund_usd
  FROM refund_with_fx rf
  LEFT JOIN reversals rv ON rv.order_id = rf.order_id
  GROUP BY rf.order_id
)
SELECT * FROM net_per_order
```

Leakage candidates: orders where net_refund_usd > order_gross_usd, or where at
least two unreversed refunds share the same `reason_code`. Unreversed means the
refund_id does not appear as `linked_refund_id` on any SETTLED refund.

## Carrier Quality Correction

### Identifying the Contradiction

```sql
WITH dedup_scans AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY source_system, external_event_id
      ORDER BY ingested_at DESC
    ) AS rn
  FROM carrier_scans
  WHERE import_batch_id = '<BATCH_ID>'
),
effective_scans AS (
  SELECT * FROM dedup_scans WHERE rn = 1
),
shipment_latest AS (
  SELECT
    es.*,
    ROW_NUMBER() OVER (
      PARTITION BY es.shipment_id
      ORDER BY es.canonical_event_at DESC
    ) AS rn_ship
  FROM effective_scans es
  JOIN shipments s ON s.shipment_id = es.shipment_id
  WHERE s.warehouse_id = '<WH_ID>'
    AND es.canonical_event_at <= '<CUTOFF>'
)
SELECT * FROM shipment_latest WHERE rn_ship = 1
```

Look for the single row where `canonical_status` (normalized) contradicts
`raw_status` (source), per the request scope. Only one such contradiction
exists in the batch.

### Applying the Correction

```bash
curl -s -X POST "<BASE>/api/sql/transaction" \
  -H "Authorization: Bearer atlas-ops-token-022" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "carrier_scan",
    "scan_row_id": "SCN-...",
    "field_name": "canonical_status",
    "old_value": "...",
    "new_value": "...",
    "reason_code": "SOURCE_RECONCILIATION",
    "correction_key": "...",
    "audit_id": "...",
    "corrected_at": "...",
    "actor": "ops-data-quality"
  }'
```

### Post-Correction Verification

1. Query the corrected `carrier_scans` row to confirm `canonical_status` and
   `corrected_at`/`correction_reason` columns reflect the change.
2. Query `GET /api/correction-audit?correction_key=<KEY>` to confirm one audit
   record exists with matching `source_row_id`, `field_name`, `old_value`,
   `new_value`.

### Backlog Counts

Pre-correction: count shipments where the effective carrier status is not
`'DELIVERED'` at the cutoff (before applying correction).

Post-correction: same count after the correction is applied (re-query with
updated values). Backlog delta = post minus pre.

```sql
WITH dedup_scans AS (...),
effective_scans AS (...)
SELECT COUNT(DISTINCT s.shipment_id) AS backlog_count
FROM shipments s
JOIN effective_scans es ON es.shipment_id = s.shipment_id
WHERE s.warehouse_id = '<WH_ID>'
  AND es.canonical_status != 'DELIVERED'
  AND es.canonical_event_at <= '<CUTOFF>'
```

## Warehouse Productivity

### Completion State

```sql
WITH dedup_events AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY source_system, external_event_id
      ORDER BY ingested_at DESC
    ) AS rn
  FROM warehouse_task_events
),
effective_events AS (
  SELECT * FROM dedup_events WHERE rn = 1
),
task_completion AS (
  SELECT
    t.task_id, t.assigned_employee_id, t.task_type, t.priority,
    t.due_at, t.planned_units,
    ee.event_type, ee.units, ee.productive_minutes,
    ROW_NUMBER() OVER (
      PARTITION BY t.task_id
      ORDER BY ee.event_at DESC
    ) AS rn_task
  FROM warehouse_tasks t
  LEFT JOIN effective_events ee
    ON ee.task_id = t.task_id AND ee.event_at <= '<STATE_CUTOFF>'
  WHERE t.warehouse_id = '<WH_ID>'
    AND t.work_class = 'PRODUCTION'
    AND t.created_at BETWEEN '<START>' AND '<END>'
)
SELECT * FROM task_completion WHERE rn_task = 1
```

A task is completed if `event_type = 'COMPLETED'` (rn_task = 1 row).

### Delayed High-Priority Tasks

```sql
SELECT task_id
FROM task_completion
WHERE rn_task = 1
  AND priority IN ('HIGH', 'URGENT')
  AND due_at < '<STATE_CUTOFF>'
  AND (event_type IS NULL OR event_type != 'COMPLETED')
ORDER BY task_id ASC
```

### Units Per Hour

Aggregate per employee: sum `units` and sum `productive_minutes` from COMPLETED
events (rn_task = 1, event_type = 'COMPLETED'). Then:

```
units_per_hour = (total_units / total_productive_minutes) * 60
```

Round to 2 decimal places for the top employee's rate. Rank employees by
unrounded `units_per_hour` descending, then `employee_id` ascending.

### Team Completion Rate

Aggregate per team: `completed_tasks / total_eligible_tasks` for each team
(using the task_completion CTE above). Rank by completion rate ascending, then
`team_id` ascending. The lowest-ranked team is the lowest-performing.

## Support Health — Active-Time Patterns

### Effective Case State at Cutoff

```sql
WITH dedup_events AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY source_system, external_event_id
      ORDER BY ingested_at DESC
    ) AS rn
  FROM case_events
),
effective_events AS (
  SELECT * FROM dedup_events WHERE rn = 1
),
latest_event AS (
  SELECT
    ce.*,
    ROW_NUMBER() OVER (
      PARTITION BY ce.case_id
      ORDER BY ce.event_at DESC
    ) AS rn_case
  FROM effective_events ce
  WHERE ce.event_at <= '<CUTOFF>'
)
SELECT
  c.case_id, c.account_id, c.priority, c.opened_at,
  le.event_type AS effective_state,
  le.event_at AS effective_state_at
FROM support_cases c
LEFT JOIN latest_event le ON le.case_id = c.case_id AND le.rn_case = 1
```

Open at cutoff: `effective_state IN ('OPEN', 'REOPEN')` (or NULL if no events
yet, treat as OPEN). Reopened: `effective_state = 'REOPEN'`. Resolved:
`effective_state = 'RESOLVED'`.

### Active Time Computation

Active time is the sum of all OPEN-to-RESOLVED spans. For a reopened case, it
includes the initial OPEN-to-first-RESOLVED span plus the REOPEN-to-final-RESOLVED
span.

```sql
WITH dedup_events AS (...),
effective_events AS (
  SELECT * FROM dedup_events WHERE rn = 1
),
case_timeline AS (
  SELECT
    case_id, event_type, event_at,
    LAG(event_type) OVER (PARTITION BY case_id ORDER BY event_at) AS prev_type,
    LAG(event_at) OVER (PARTITION BY case_id ORDER BY event_at) AS prev_at
  FROM effective_events
)
SELECT
  case_id,
  SUM(
    CASE WHEN prev_type IN ('OPEN', 'REOPEN')
         THEN (julianday(event_at) - julianday(prev_at)) * 24
         ELSE 0
    END
  ) AS active_hours
FROM case_timeline
WHERE event_type = 'RESOLVED'
GROUP BY case_id
```

When a case has no RESOLVED event at the cutoff (still open), compute elapsed
active time from `opened_at` (or most recent REOPEN) to the cutoff.

### First Response

```sql
SELECT
  ce.case_id,
  MIN(ce.event_at) AS first_response_at
FROM effective_events ce
WHERE ce.event_type = 'RESPONSE' AND ce.actor_type = 'AGENT'
GROUP BY ce.case_id
```

First-response active time: `(julianday(first_response_at) - julianday(c.opened_at)) * 24`.
For unresponded cases, use elapsed time from `opened_at` to the cutoff.

### SLA Breach Detection

Compare first-response hours and resolution active hours against the
priority-specific thresholds. An active (unresolved) case at cutoff uses
`(julianday(cutoff) - julianday(opened_at)) * 24` for breach evaluation.

### Severe Active Case

A case that is OPEN or REOPENED at cutoff, with priority URGENT or HIGH, AND
whose resolution active time exceeds the priority threshold:

```sql
WHERE effective_state IN ('OPEN', 'REOPEN')
  AND priority IN ('URGENT', 'HIGH')
  AND active_resolution_hours > CASE priority
        WHEN 'URGENT' THEN 16
        WHEN 'HIGH' THEN 24
      END
```

### Median Resolution Hours

For cases resolved at cutoff, compute `active_resolution_hours`, sort, take
median. For odd count N, use element at position (N+1)/2. For even count N,
average elements at positions N/2 and N/2+1. Round to 2 decimal places.

## Risk Classification Patterns

Many domains use a tiered risk/status classification with cascading conditions.
The general rule: check the most favorable tier first, then fall through.

**Pattern:**
```
IF condition_A THEN best_tier
ELSE IF condition_B THEN middle_tier
ELSE worst_tier
```

Always compute the necessary rates and thresholds first, then classify. Use the
exact thresholds from the request; do not assume them.

The names differ by domain: HEALTHY/WATCH/CRITICAL for fulfillment, LOW/MODERATE/HIGH
for refunds, CONTROLLED/ELEVATED/SEVERE for support, STABLE/PRESSURED/AT_RISK for
warehouse productivity.

## Output Validation Checklist

Use this checklist before finalizing `answer.json`:

- [ ] Every `required` field from the answer template is present
- [ ] No extra fields beyond the template's `properties`
- [ ] Integer fields are exact whole numbers, not floats
- [ ] Number fields have correct precision (check `multipleOf`)
- [ ] Arrays have correct length (`minItems`/`maxItems`)
- [ ] Array items are unique where `uniqueItems: true`
- [ ] String fields match any `pattern` regex
- [ ] Enum fields use exact allowed values (case-sensitive)
- [ ] Array ordering follows the sort rules in the template/request
- [ ] Count consistency: complete + incomplete = eligible (where applicable)
- [ ] Rates are within `[0, 1]` where that constraint exists
- [ ] Timestamps match the ISO-8601 format where required
- [ ] The output file is valid JSON (no trailing commas, no comments)
