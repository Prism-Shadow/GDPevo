# Atlas Commerce Operations — Analytical Task Skill

## Purpose
Solve operational analytics and data-correction tasks against the Atlas Commerce Operations database. Each task provides a business-request payload and an answer template; produce a JSON answer conforming exactly to the template.

## Workflow

### Phase 1: Orient
1. **Read the schema** (`GET /api/schema`). Identify all tables that participate in the task. Note primary keys, foreign keys, and check constraints — they encode domain invariants.
2. **Read the data dictionary** (`GET /api/data-dictionary`). Note field-level conventions: timestamp format (ISO-8601 UTC), monetary minor units, boolean encoding (0/1 integers), and dedup indexes.
3. **Read the task prompt** and the **business-request payload**. Extract: cohort/scope rules, date windows, cutoff timestamps, business definitions, rollup instructions, rounding rules, and status-tier conditions.
4. **Read the answer template**. Every `required` field must appear; every `additionalProperties: false` constraint means no extra fields. Match `type`, `enum`, `pattern`, `minimum`/`maximum`, `multipleOf`, and `minItems`/`maxItems` exactly.

### Phase 2: Scope the cohort
- **Production accounts**: `is_internal = 0 AND is_test = 0`.
- **Date windows**: boundary is inclusive unless stated otherwise. Timestamp comparisons use ISO-8601 lexical order (`<=` / `>=`).
- **Cohort membership**: derive from join paths through the schema (accounts → orders → shipments → carrier_scans, etc.).
- **Distinct counts**: use `COUNT(DISTINCT …)` for orders, shipments, cases, and refunds unless the template explicitly asks for row counts.

### Phase 3: Deduplicate event tables
Tables with import retries carry a dedup index on `(source_system, external_event_id, ingested_at)`. Always dedup before using the rows:

```sql
WITH dedup AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY source_system, external_event_id
               ORDER BY ingested_at DESC
           ) AS rn
    FROM <table>
    WHERE <cohort-filter>
)
SELECT … FROM dedup WHERE rn = 1
```

Affected tables: `carrier_scans`, `refund_attempts`, `payment_events`, `warehouse_task_events`, `case_events`, `order_events`, `inventory_movements`.

### Phase 4: Determine effective state
For append-only event tables, the *effective* value is the latest by event timestamp:

```sql
SELECT …
FROM   <table>
WHERE  corrected_at IS NULL                    -- exclude superseded corrections
  AND  <event_timestamp> = (
       SELECT MAX(<event_timestamp>)
       FROM   <table> AS t2
       WHERE  t2.<entity_id> = <table>.<entity_id>
         AND  t2.corrected_at IS NULL
       )
```

**Tiebreak rule**: when multiple rows share the same maximum event timestamp with different statuses, prefer the more advanced operational status. For carrier scans the precedence order is:
`DELIVERED > OUT_FOR_DELIVERY > AT_HUB > IN_TRANSIT > PICKED_UP > LABEL_CREATED`.
Implement this with `ORDER BY CASE canonical_status WHEN 'DELIVERED' THEN 0 … END` and take the first row.

### Phase 5: Compute derived metrics
Translate each business definition from the request payload into code:

- **Rates**: numerator / denominator; denominator is typically the full eligible cohort (not just the subset that could qualify).
- **Rounding**: round only final reported values. Use `Decimal(str(val)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)` for 4-decimal precision, `Decimal('0.01')` for 2-decimal. Do not round intermediate values used for ranking or further computation.
- **Ranking with tiebreaks**: rank by the *unrounded* primary metric, then by the stated tiebreak columns. Example: "worst regions by rate ascending, then region ascending" → `ORDER BY unrounded_rate ASC, region ASC`.
- **Monetary conversion**: `amount_minor` is in the smallest unit of the row's currency (cents for USD/EUR/GBP/AUD/CAD). Convert to USD via `(amount_minor / 100.0) * fx_rates.usd_per_unit` using the rate for the transaction's `service_date` and the row's currency. For cross-currency comparisons, convert both sides to USD at the refund/service-date rate.

### Phase 6: Classify according to business rules
Status tiers are usually evaluated in order — the first matching condition wins. Translate the JSON rule arrays into cascading if/elif/else blocks. Pay attention to:
- Whether conditions use strict or non-strict inequalities (`>=` vs `>`).
- Whether "below" means `<` and "at least" means `>=`.
- Whether an `otherwise` / fallback tier exists.

### Phase 7: Handle corrections (when requested)
A correction task provides an `approved_correction` block with audit metadata.

1. Identify the target row and field from the raw/canonical contradiction.
2. Build the UPDATE statement for the single business row.
3. Build the INSERT statement for `correction_audit` using the provided `audit_id`, `correction_key`, `reason_code`, `actor`, and `corrected_at`.
4. Call the transaction endpoint with both statements and `expected_total_changes` set to the number of rows both statements will change together.
5. **Check the result**: query the corrected row and the audit table. Report `APPLIED` only when exactly one business row AND one audit row committed AND a post-change query confirms the corrected canonical value. Report `NOT_APPLIED` for every other outcome — include the actual `affected_business_rows`, `audit_rows`, and observed backlog analysis.

### Phase 8: Validate the answer
Before finalizing, verify:
- The output is a single JSON object matching the template schema exactly.
- All `required` fields are present; no extra fields.
- All `enum` values match; all `pattern` constraints hold.
- Array fields are sorted as specified.
- Counts sum correctly (e.g., `effectively_complete + incomplete = eligible_production_order_count`).
- Rates are within [0, 1] and rounded as specified.

## Common patterns by domain

### Fulfillment scorecards
- Effective delivery status comes from the latest `carrier_scans.canonical_event_at` per shipment, with `DELIVERED` tiebreak.
- An order is complete when **every** shipment is effectively `DELIVERED`. An order is on-time when every shipment's delivery scan is `<=` its `promised_delivery_at`.
- **Severe exception**: incomplete with cutoff > latest-promise + 24h, or complete with any delivery > promise + 24h.
- Regional rollups use `warehouses.region` from the order's assigned warehouse.

### Refund reconciliation
- Eligible refunds: `status = 'SETTLED'` within the service-date window.
- Reversals: rows with `status = 'REVERSED'` whose `linked_refund_id` points to an eligible settled refund. Subtract reversal USD from the linked refund's reason-code bucket.
- **Leakage candidate**: net refund USD > order gross USD (both at the refund's service-date rate), **or** ≥ 2 unreversed settled refunds with the same `reason_code` on the same order.
- Reason ranking: by net USD descending, then reason code ascending.

### Warehouse productivity
- `work_class = 'PRODUCTION'` tasks created in the window.
- **Completed units**: sum `warehouse_task_events.units` from `event_type = 'COMPLETED'` rows of tasks with `current_status = 'COMPLETED'`.
- **Rework**: `current_status = 'REWORK'`.
- **Units per hour**: `(total_completed_units / total_productive_minutes) * 60` per employee.
- **Delayed high-priority**: `priority IN ('HIGH','URGENT')`, `due_at < cutoff`, `current_status != 'COMPLETED'`.

### Support health
- **Clock basis**: active time starts at `opened_at`. First-response time is elapsed hours until the first `AGENT_RESPONDED` event. Resolution time is elapsed hours until `RESOLVED` event or cutoff for active cases.
- **Breach**: active hours exceeds the priority's SLA threshold.
- **Severe active case**: `current_status IN ('OPEN','REOPENED')`, `priority IN ('URGENT','HIGH')`, and active resolution time exceeds the priority's resolution threshold.
- **Median**: for even count, average the two central values. Round to 2 decimal places.

## Data quality conventions
- **`corrected_at IS NULL`**: exclude rows superseded by a canonical correction when determining effective state. The correction itself creates a new row; use the uncorrected originals to identify the pre-correction state.
- **`is_internal = 0 AND is_test = 0`**: production-only filter applied to `accounts`.
- **Timestamps**: all stored in ISO-8601 UTC (`…Z`). Dates are `YYYY-MM-DD`. Comparisons use string lexical order.
- **Monetary minor fields**: integer in the smallest unit. For FX, divide by 100 (or the currency's minor-unit factor) before multiplying by `usd_per_unit`.
