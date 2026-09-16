# Atlas Commerce Query Patterns

Read this reference when solving Atlas Commerce Operations SQL tasks. The request payload remains authoritative; adapt these patterns to the live schema and definitions.

## API And Schema Orientation

The workplace exposes a SQLite-like database through `/api/sql`. Discovery responses describe these common tables:

- Customer scope: `accounts(account_id, segment, tier, region, is_internal, is_test)`.
- Orders and fulfillment: `campaigns`, `orders`, `order_lines`, `shipments`, `carrier_scans`, `order_events`, `warehouses`.
- Payments and refunds: `payment_events`, `refund_attempts`, `fx_rates`.
- Warehouse labor: `warehouse_tasks`, `warehouse_task_events`, `employees`.
- Support: `support_cases`, `case_events`.
- Corrections: `correction_audit`; mutable canonical-source tables can include `carrier_scans` and `inventory_movements`.

Money fields ending in `_minor` are in the smallest currency unit. Convert with `/ 100.0` before multiplying by `fx_rates.usd_per_unit`.

## Effective Imported Rows

Many append-only tables can contain source retries. Use the latest ingested copy for each upstream event before lifecycle work:

```sql
with effective_events as (
  select *
  from (
    select e.*,
           row_number() over (
             partition by source_system, external_event_id
             order by ingested_at desc, rowid desc
           ) as rn
    from some_event_table e
  )
  where rn = 1
)
```

If a table has a stable row ID but no `rowid` in the allowed query, use that stable ID as the final tie-break.

## Cohorts And Cutoffs

- Production accounts usually mean `accounts.is_internal = 0 and accounts.is_test = 0`.
- Production warehouse work usually means `warehouse_tasks.work_class = 'PRODUCTION'`.
- For "created/opened during window" requests, apply the payload's inclusive or exclusive boundary exactly.
- For "at cutoff" status, prefer effective event history at or before the cutoff when the request defines a state at a historical time. Treat denormalized `current_status` as a convenience snapshot unless the request explicitly permits it.
- For physical shipments, confirm whether the request means shipment rows, shipped rows, or latest carrier-scan state. Do not assume `shipments.current_status` is cutoff-consistent.

## Fulfillment Scorecards

Use the campaign and account/order scope first, then roll up shipments per eligible order.

- Complete order: require at least one qualifying physical shipment and require every qualifying shipment to be effectively delivered by the cutoff.
- On-time complete order: complete order where every qualifying shipment's delivered timestamp is no later than its shipment promise.
- Incomplete order: eligible order not satisfying complete-order logic; keep it in rate denominators.
- Severe exception patterns: incomplete beyond the latest shipment promise plus the requested tolerance, or complete with any shipment delivered beyond its promise plus the requested tolerance.
- Regional rollups join `orders.warehouse_id` to `warehouses.region`; rank regions using unrounded rates.

Use separate checks for eligible orders, orders with no shipments, delivered shipment rollups, and severe ID count.

## Refund Reconciliation

Build logical refunds at the `refund_id` level after effective-row dedupe.

- In-scope account/order filters commonly use account tier, production-account flags, and a refund service-date window.
- Effective settled logical refunds are distinct `refund_id` values whose effective status is settled and whose service date is in scope.
- Linked reversals use reversal rows whose `linked_refund_id` points to a settled logical refund; subtract their USD value from the linked refund.
- Convert each refund/reversal using `fx_rates` on that row's `service_date` and `currency`.
- Compare order gross by converting `orders.gross_amount_minor / 100.0` at the settled refund's service-date rate for the order currency.
- Leakage candidates are usually evaluated per order after reversal offsets. A common second condition is multiple unreversed settled refunds sharing the same normalized reason code.
- Reason rankings use effective net USD by normalized reason code, descending, then reason code ascending.

## Carrier Quality Corrections

Find contradictions in `carrier_scans` by joining `shipments` for warehouse scope and filtering the named import batch and cutoff. A typical contradiction is a raw delivered status with a different canonical status, but always follow the request's stated contradiction rule.

For backlog-at-cutoff:

- Start with shipments that have an effective scan in the named batch at or before the cutoff.
- Pick each shipment's final effective canonical scan at or before the cutoff.
- Backlog means the final effective canonical status is not delivered, unless the request defines another final state.

For the mutation, update only the approved canonical field on the target row and insert the exact audit fields supplied by the request. Verify through read-only SQL and `/api/correction-audit`.

## Warehouse Productivity

Use eligible `warehouse_tasks` by warehouse, creation window, and production work class.

- Completion at cutoff should be based on task events at or before the cutoff when historical state is required.
- Completed production units usually come from effective `warehouse_task_events` with completion events for eligible tasks at or before the cutoff.
- Units per hour is `sum(completed units) / sum(productive_minutes) * 60`; guard against division by zero.
- Rework counts are distinct eligible tasks with a rework state/event according to the request.
- Delayed high-priority tasks are high/urgent tasks due strictly before the cutoff and not completed by the cutoff.
- Employee ranking sorts units per hour descending, then `employee_id` ascending.
- Team ranking for lowest performance sorts completion rate ascending, then `team_id` ascending.

## Support Health

Use `support_cases` joined to production `accounts` for segment/region scope, then effective `case_events` for time calculations.

Support active time is usually the sum of intervals where the case clock is running:

- Start at case open or reopen.
- Pause at `WAITING_CUSTOMER`.
- Resume at `CUSTOMER_REPLIED` or `REOPENED`.
- Stop at `RESOLVED`; for still-active cases, stop at the cutoff.
- Ignore events after the cutoff for active-at-cutoff and breach calculations.

First response active time runs from opening to the first agent response, excluding paused intervals; if no response exists, use active elapsed time through the cutoff. Resolution active time runs through resolution for resolved cases or through the cutoff for active cases.

For medians, order active resolution hours for eligible resolved cases and average the two center values for an even count. Rank worst accounts by the requested severe-active count, then breach count, then account ID.
