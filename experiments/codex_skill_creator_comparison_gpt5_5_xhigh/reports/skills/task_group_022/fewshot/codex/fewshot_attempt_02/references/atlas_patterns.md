# Atlas Commerce Operations Patterns

## Runtime API

- `GET /api/schema` returns DDL and indexes.
- `GET /api/data-dictionary` returns table and column semantics.
- `POST /api/sql` accepts JSON shaped as `{"sql": "select ..."}` and returns `columns`, `rows`, `row_count`, and `truncated`.
- `GET /api/correction-audit` returns committed correction audit rows.
- `POST /api/sql/transaction` is reserved for approved mutations; do not use the read-only SQL endpoint for writes.

## Common SQL Rules

- Stored timestamps are UTC ISO-8601 text. Use request boundaries exactly: inclusive windows use `between` or paired `>=`/`<=`; strict definitions such as "due before cutoff" use `<`.
- Production account scope means `accounts.is_internal = 0` and `accounts.is_test = 0`.
- Money is stored in minor units. Convert with `(amount_minor / 100.0) * fx_rates.usd_per_unit`, joining `fx_rates.rate_date` to the request's service date or the date portion of the relevant timestamp.
- Imported append-only rows can contain retries. For event/source tables with `source_system`, `external_event_id`, and `ingested_at`, first deduplicate by `(source_system, external_event_id)`, keeping the newest `ingested_at` and then the stable row id as a tie-breaker.
- For cutoff state, choose the latest deduplicated event at or before the cutoff using the event timestamp and stable row id as tie-breakers.
- Use stable identifiers ascending as tie-breakers unless the request gives a different order. Sort arrays in SQL, then emit them in that exact order.
- Use unrounded values for comparisons and rankings. Round only final JSON fields to the precision specified by the template or request.

Reusable cutoff pattern:

```sql
with dedup_scans as (
  select *
  from (
    select
      cs.*,
      row_number() over (
        partition by source_system, external_event_id
        order by ingested_at desc, scan_row_id desc
      ) as rn
    from carrier_scans cs
  )
  where rn = 1
),
shipment_final as (
  select *
  from (
    select
      ds.*,
      row_number() over (
        partition by shipment_id
        order by canonical_event_at desc, scan_row_id desc
      ) as rn
    from dedup_scans ds
    where canonical_event_at <= :cutoff_at
  )
  where rn = 1
)
select * from shipment_final;
```

## Table Map

- Accounts and scope: `accounts`, with production flags, segment, tier, region, and currency.
- Orders and campaigns: `orders`, `order_lines`, `order_events`, `campaigns`.
- Shipments and carrier scans: `shipments`, `carrier_scans`, `source_import_batches`, `correction_audit`.
- Refunds and payments: `refund_attempts`, `payment_events`, `fx_rates`.
- Warehouse work: `warehouse_tasks`, `warehouse_task_events`, `employees`, `warehouses`.
- Support health: `support_cases`, `case_events`, `accounts`.
- Inventory: `inventory_movements`, `inventory_snapshots`, `products`, `warehouses`.

## Fulfillment Scorecards

Build the order cohort from `orders` joined to `campaigns`, `accounts`, and `warehouses`. Apply campaign id/name filters, campaign active-window order creation, and production-account exclusions.

For shipment state, derive the latest effective `carrier_scans.canonical_status` at the cutoff for each shipment. An order is complete only when it has at least one shipment and every shipment is effectively `DELIVERED` by the cutoff. It is on time only when every delivered shipment has a delivered canonical event time no later than `shipments.promised_delivery_at`.

Incomplete orders remain in the denominator. Severe-exception logic is usually a union of incomplete orders whose latest shipment promise is more than 24 hours before the cutoff and completed orders with any shipment delivered more than 24 hours after its promise. Orders with no shipment promise should not satisfy a promise-based lateness rule unless the request says otherwise.

Regional rates use `warehouses.region` from the assigned order warehouse. Rank regions by unrounded rate ascending, then region ascending.

## Refund Reconciliation

Join `refund_attempts` to `orders` and `accounts` for tier, production, and date scope. Treat `status = 'SETTLED'` rows as settled logical refunds and `status = 'REVERSED'` rows with `linked_refund_id` as linked reversals when they are in scope under the request's effective service-date rules.

Collapse to distinct logical ids when the template asks for logical refunds or reversals. Convert each in-scope refund and reversal to USD with the service-date FX rate. Net refund value is settled refund USD minus linked reversal USD. Rank reasons by effective net USD descending, then normalized reason code ascending.

For leakage candidates, aggregate at order level. Compare net refund USD to the order gross converted with the specified FX basis, and separately check repeated unreversed settled logical refunds with the same normalized reason code. Return candidate order ids sorted ascending.

## Carrier Quality Corrections

Use the request's import batch, warehouse, and cutoff to define membership. For backlog, identify shipments with an effective scan in the named batch at or before the cutoff, then compute the latest effective final carrier status at the cutoff.

Find the single raw/canonical contradiction by comparing source `raw_status` against the normalized `canonical_status`. Preserve raw values, source ids, timestamps, and unrelated business rows. If the approved correction scope says minimal canonical field only, update only that canonical column and insert the requested `correction_audit` row in the same transaction.

After the transaction, read the target row, the audit endpoint/table, and the backlog metric again. Set the final correction status from the request's success rule, not from the absence of an error alone.

## Warehouse Productivity

Build the cohort from `warehouse_tasks` by warehouse, `work_class = 'PRODUCTION'`, and the created-at window. Use `warehouse_task_events` at or before the state cutoff for completed state, completed units, productive minutes, and rework where the request is cutoff-based.

Employee units per hour is completed units divided by productive minutes, multiplied by 60. Rank employees by unrounded units per hour descending, then `employee_id` ascending. Team completion rates use `employees.team_id`; rank lowest completion rate ascending, then `team_id` ascending.

A delayed high-priority task is usually `priority in ('HIGH','URGENT')`, `due_at < cutoff`, and not completed by cutoff. Use the request's exact priority labels and cutoff comparison.

## Support Health

Build eligible cases from `support_cases` joined to production `accounts`, applying segment, region, and opened-at scope. Use `case_events` at or before the cutoff for active state and SLA clocks.

For active-time clocks, order case events by event time and id, create intervals to the next event or cutoff, and exclude time spent in waiting/resolved states when the request says `SUPPORT_ACTIVE_TIME`. First-response breaches use active elapsed time to first `AGENT_RESPONDED`; unresponded cases use active elapsed time at the cutoff. Resolution breaches use active time to resolution; active cases use active elapsed time at the cutoff.

Open-at-cutoff includes `OPEN` and `REOPENED` active states; reopened-at-cutoff is the reopened subset. Severe active cases are active at cutoff, have request-defined severe priorities, and exceed the active-time resolution threshold. Worst accounts rank by severe active case count descending, active-clock breach count descending, then account id ascending.

For resolved-case medians, compute active resolution hours for eligible cases resolved at the cutoff. For an even count, average the two central unrounded values, then round the final reported median.
