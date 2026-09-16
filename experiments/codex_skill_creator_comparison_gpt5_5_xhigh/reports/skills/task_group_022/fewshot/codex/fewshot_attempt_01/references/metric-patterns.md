# Metric Patterns

## Table Map

- `accounts`: production-exclusion flags, segment, tier, region, account currency.
- `campaigns`: official campaign windows.
- `orders`, `order_lines`, `order_events`: order headers, SKU quantities, and lifecycle events.
- `shipments`, `carrier_scans`: physical shipments and imported carrier observations.
- `refund_attempts`, `payment_events`, `fx_rates`: refund/payment rows and currency conversion.
- `warehouse_tasks`, `warehouse_task_events`, `employees`, `warehouses`: fulfillment work, execution events, teams, and regions.
- `support_cases`, `case_events`: support case headers and lifecycle events.
- `inventory_movements`, `inventory_snapshots`, `products`: stock movement and inventory analytics.
- `correction_audit`: required audit trail for approved canonical corrections.

## Source Dedupe

Use this pattern for imported append-only tables that can contain retries:

```sql
WITH deduped AS (
  SELECT *
  FROM (
    SELECT t.*,
           ROW_NUMBER() OVER (
             PARTITION BY source_system, external_event_id
             ORDER BY ingested_at DESC, <stable_row_id> DESC
           ) AS src_rn
    FROM <source_table> t
  )
  WHERE src_rn = 1
)
```

For cutoff state, rank the deduped rows per entity:

```sql
latest_asof AS (
  SELECT *
  FROM (
    SELECT d.*,
           ROW_NUMBER() OVER (
             PARTITION BY <entity_id>
             ORDER BY <effective_event_at> DESC, <stable_row_id> DESC
           ) AS entity_rn
    FROM deduped d
    WHERE <effective_event_at> <= '<cutoff>'
  )
  WHERE entity_rn = 1
)
```

If the SQL endpoint rejects a large nested query, materialize the reasoning through smaller aggregate queries and keep the same ordering logic.

## Production Cohorts

Apply production filters only where the request requires them. Common forms:

- Customer/account production: `accounts.is_internal = 0 AND accounts.is_test = 0`.
- Warehouse production work: `warehouse_tasks.work_class = 'PRODUCTION'`.
- Production shipments/orders/cases usually inherit production status through joined accounts or explicit request scope.

Keep the raw cohort count visible during development. Most metric errors come from a missing production flag, a wrong boundary, or using a snapshot where the request needs an as-of event state.

## Fulfillment And Carrier Quality

- Campaign orders: join `orders.campaign_id` to `campaigns`, then apply the campaign's official `starts_at`/`ends_at` window and any production-account filter requested.
- Physical shipment completeness: an order with no `shipments` row is incomplete. Otherwise, every associated shipment must be effectively `DELIVERED` by the cutoff.
- Effective shipment status: prefer latest deduped `carrier_scans.canonical_status` by `shipment_id` and `canonical_event_at` at or before the cutoff. Use the delivered scan's `canonical_event_at` as delivered time.
- On-time completeness: a complete order is on time only when every shipment's delivered time is no later than that shipment's `promised_delivery_at`.
- Severe fulfillment exceptions: follow the request's two branches separately: incomplete after the latest shipment promise plus the grace window, and completed with any shipment delivered after its promise plus the grace window.
- Regional rollups: join `orders.warehouse_id` or `shipments.warehouse_id` to `warehouses`; use the warehouse region named by the request. Rank on unrounded rates, then round only output rates.
- Carrier correction targets: find the single row in the named import batch where raw and canonical carrier status contradict the request's policy. Correct only the canonical column, leave raw/source fields untouched, and insert the matching audit record.

## Refund Reconciliation

- Scope accounts through `orders.account_id` and `accounts` attributes such as tier, segment, region, and production flags.
- Treat settled logical refunds as distinct `refund_id` values from effective `refund_attempts` rows with settled status in the service-date window.
- Treat linked reversals as effective reversal rows whose `linked_refund_id` points to an in-scope settled logical refund.
- Net USD is settled refund USD minus linked reversal USD. Convert each row as `(amount_minor / 100.0) * fx_rates.usd_per_unit` using the row currency and the request's stated rate date basis.
- Rank reason codes by unrounded net USD descending, then normalized reason code ascending.
- Leakage candidates commonly combine over-refund checks against order gross USD and duplicate unreversed settled refunds with the same normalized reason. Sort final order ids ascending.

## Warehouse Productivity

- Eligible work usually filters `warehouse_tasks` by warehouse, `work_class`, and a task-created window.
- Completed task state should be derived from effective `warehouse_task_events` at or before the cutoff when the request asks for cutoff consistency.
- Completed production units and productive minutes come from completed execution events. Units per hour is `completed_units * 60.0 / productive_minutes`; guard against zero productive minutes.
- Rework counts are distinct eligible tasks with an effective `REWORK` event.
- Delayed high-priority work uses the request's priority set, `due_at` comparison, and not-completed-by-cutoff state. Sort task ids ascending.
- Employee and team rankings must use unrounded metrics with the stated identifier tie-breaker.

## Support Health

- Eligible support cases usually join `support_cases.account_id` to `accounts` and filter by production flags, segment, region, and opened window.
- Derive case state as of cutoff from deduped `case_events` where needed. `OPEN` or `REOPENED` states are active at cutoff; `RESOLVED` is closed.
- Support active time excludes waiting-on-customer intervals. Build event intervals ordered by `event_at`, pausing after `WAITING_CUSTOMER`, resuming after customer activity or reopened activity, and stopping at resolution or cutoff.
- First response breach: compare active time to the first agent response against the priority threshold. If there is no agent response by cutoff, use active elapsed time at cutoff.
- Active-clock resolution breach: for resolved cases, compare active time to resolution; for active cases, compare active elapsed time at cutoff.
- Severe active cases: active at cutoff, priority in the request's severe set, and beyond the active-time resolution threshold. Sort case ids ascending.
- Median resolved active hours: compute across eligible cases resolved at or before the cutoff; for an even count, average the two central active-hour values and round only the final median.

## JSON Output

The answer template controls field names and shapes even when it uses nonstandard schema keys such as `additional_properties`, `min_items`, or `decimal_places`. The final file must be a plain JSON object and nothing else.
