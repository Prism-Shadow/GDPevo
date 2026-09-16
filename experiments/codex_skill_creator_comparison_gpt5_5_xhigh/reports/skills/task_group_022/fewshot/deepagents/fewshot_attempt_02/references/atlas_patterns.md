# Atlas SQL Patterns

Use these patterns after reading the task prompt, request payloads, live schema, and data dictionary. They are reusable mechanics, not task answers.

## API And Result Handling

`POST /api/sql` accepts a JSON body shaped like `{"sql": "select ..."}` and returns:

```json
{"columns": ["name"], "rows": [["value"]], "row_count": 1, "truncated": false}
```

Convert `columns` plus each row into dictionaries when inspecting results manually. If `truncated` is true for a query that feeds an answer array, narrow the query or aggregate in SQL so the complete result is returned.

## Source Row Dedupe

Imported source tables can contain retry copies for the same upstream event. Dedupe before building effective event history for tables that have `source_system`, `external_event_id`, and `ingested_at`.

Common source-event tables:

- `carrier_scans`
- `case_events`
- `inventory_movements`
- `order_events`
- `payment_events`
- `refund_attempts`
- `warehouse_task_events`

Pattern:

```sql
with deduped_events as (
  select *
  from (
    select
      e.*,
      row_number() over (
        partition by e.source_system, e.external_event_id
        order by e.ingested_at desc, e.row_id_column desc
      ) as dedupe_rank
    from source_table e
  )
  where dedupe_rank = 1
)
```

Replace `row_id_column` with the stable primary key for that table, such as `scan_row_id`, `case_event_id`, `task_event_id`, `payment_event_id`, or `refund_row_id`.

## Cutoff State

For state as of a cutoff, filter events to `event_at <= cutoff` or the table's canonical event timestamp, then rank latest event per entity:

```sql
latest_state as (
  select *
  from (
    select
      e.*,
      row_number() over (
        partition by e.entity_id
        order by e.event_at desc, e.row_id_column desc
      ) as state_rank
    from deduped_events e
    where e.event_at <= :cutoff_at
  )
  where state_rank = 1
)
```

Use a strict predicate only when the request says strict, such as `due_at < cutoff`.

## Cohort Filters

Use explicit production flags and classes where present:

- Production accounts: `accounts.is_internal = 0` and `accounts.is_test = 0`.
- Production warehouse work: `warehouse_tasks.work_class = 'PRODUCTION'`.
- Campaign order cohorts: join `campaigns` and filter the requested `campaign_id`; if the request cites the campaign's official active window, use `orders.order_created_at` within `campaigns.starts_at` and `campaigns.ends_at`.
- Support account cohorts: join `support_cases` to `accounts`, then apply account segment, region, and production-account filters from the request.
- Warehouse cohorts: use the requested `warehouse_id` and the requested created, due, or event windows exactly.

## Fulfillment And Carrier Scans

Physical shipment analysis usually starts from `shipments`, then uses deduped `carrier_scans` for effective carrier status by cutoff.

Useful CTE sequence:

1. Eligible orders from `orders`, `accounts`, `campaigns`, and `warehouses`.
2. Physical shipments for those orders.
3. Deduped carrier scans.
4. Latest scan per shipment at or before cutoff using `canonical_event_at`.
5. Per-shipment delivery timestamp from the effective `DELIVERED` canonical scan.
6. Per-order rollup:
   - complete only if the order has at least one physical shipment and every shipment is effectively delivered by cutoff.
   - on time only if complete and every shipment delivered no later than its own `promised_delivery_at`.
   - severe lateness compares the relevant delivered timestamp or latest shipment promise against the request's lateness threshold.

When finding raw/canonical contradictions, compare source `raw_status` to the normalized `canonical_status` in the requested batch and cohort. If raw status plainly maps to a different canonical value, correct only the canonical field when authorized.

## Refund Reconciliation

Refund tasks typically combine `orders`, `accounts`, `refund_attempts`, and `fx_rates`.

Reusable mechanics:

- Scope accounts and orders first, then join effective refund rows.
- A logical refund is usually keyed by `refund_id`; count distinct logical IDs, not retry rows.
- Effective settled refunds come from status and service-date rules in the request.
- Linked reversals use `linked_refund_id` to offset the logical refund they reverse.
- Convert monetary values as `(amount_minor / 100.0) * fx.usd_per_unit`.
- For gross comparisons, value the order's gross amount in USD with the FX rate for the refund service date when the request says so.
- Normalize `reason_code` as requested before ranking.
- Rank reasons by unrounded effective net USD, then the requested textual tie-breaker.
- Leakage lists should use distinct order IDs and the request's exact candidate conditions.

## Warehouse Productivity

Warehouse productivity tasks typically use `warehouse_tasks`, `warehouse_task_events`, `employees`, and sometimes `warehouses`.

Reusable mechanics:

- Build eligible tasks from `warehouse_tasks` by warehouse, created window, and work class.
- Dedupe task events before counting completions, rework, units, or productive minutes.
- A task is completed by cutoff if it has a completion event at or before cutoff, unless the request names another completion source.
- Completed units and productive minutes should come from the events tied to completed work.
- Employee units per hour is `completed_units * 60.0 / productive_minutes`; guard against zero minutes.
- Count rework as distinct eligible tasks with a qualifying `REWORK` event in scope.
- Delayed high-priority work normally uses `priority in ('HIGH','URGENT')`, the request's due/cutoff comparison, and not completed by cutoff.
- Rank teams with the request's completion-rate formula and tie-breakers.

## Support Active-Clock Metrics

Support health tasks typically use `support_cases`, `case_events`, and `accounts`.

Known support events include `OPENED`, `OPEN`, `ASSIGNED`, `AGENT_RESPONDED`, `CUSTOMER_REPLIED`, `WAITING_CUSTOMER`, `ESCALATED`, `REOPENED`, and `RESOLVED`. Use the data dictionary and request wording to decide which events start, stop, or resume the active clock.

Reusable mechanics:

- Build eligible cases by opened window, account segment, account regions, and production-account flags.
- Dedupe case events before deriving lifecycle state.
- First response is usually the first `AGENT_RESPONDED` event; for unresponded cases, measure active elapsed time through cutoff when the request says so.
- Resolution active time for resolved cases ends at resolution; for active cases, use active elapsed time at cutoff.
- `OPEN` and `REOPENED` are active states when the request says open-at-cutoff includes reopened cases.
- Severe active cases combine active-at-cutoff state, priority, and the priority-specific resolution active-time threshold.
- Median active resolution hours should be computed over eligible cases resolved at the cutoff; for an even count, average the two central values.

SQLite median pattern:

```sql
with ordered as (
  select
    value,
    row_number() over (order by value) as rn,
    count(*) over () as n
  from values_to_measure
)
select avg(value) as median_value
from ordered
where rn in ((n + 1) / 2, (n + 2) / 2);
```

## Risk And Status Rules

Apply named risk/status policies in the request order. Use unrounded rates for threshold comparisons unless the request explicitly says to classify on rounded values. If no named condition applies, use the stated fallback.

## Controlled Correction Pattern

For an approved correction:

1. Query the pre-change metric and the exact target row.
2. Prepare one atomic transaction that updates only the approved canonical field and any correction metadata columns, then inserts one `correction_audit` row using the request's audit values.
3. Use the request's idempotency key or correction key exactly. If the audit key already exists, inspect whether the intended correction is already applied before deciding status.
4. Re-query the target row, audit view, and post-change metric.
5. Report applied status only if the request's success rule is satisfied.
