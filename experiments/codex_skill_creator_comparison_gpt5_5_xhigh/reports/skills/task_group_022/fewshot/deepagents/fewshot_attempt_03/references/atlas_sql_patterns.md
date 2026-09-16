# Atlas SQL Patterns

Use these patterns as reusable starting points. Replace placeholders with the current request values and always re-check the live schema and data dictionary.

## Table Map

- Accounts and orders: `accounts`, `campaigns`, `orders`, `order_lines`, `order_events`
- Delivery and carrier data: `shipments`, `carrier_scans`, `source_import_batches`, `warehouses`
- Payments and refunds: `refund_attempts`, `payment_events`, `fx_rates`
- Warehouse work: `warehouse_tasks`, `warehouse_task_events`, `employees`, `warehouses`
- Support: `support_cases`, `case_events`, `accounts`
- Corrections: canonical source tables plus `correction_audit`

Production customer populations usually exclude `accounts.is_internal = 1` and `accounts.is_test = 1`.

## Source Deduplication

Imported event tables carry `source_system`, `external_event_id`, and `ingested_at`. When a metric uses source events, first keep the latest ingested copy of each source event.

```sql
with dedup_events as (
  select *
  from (
    select e.*,
           row_number() over (
             partition by source_system, external_event_id
             order by ingested_at desc, event_at desc, case_event_id desc
           ) as rn
    from case_events e
  )
  where rn = 1
)
```

Use the table's stable row id as the final tie-breaker: `event_id`, `scan_row_id`, `task_event_id`, `refund_row_id`, or `case_event_id`.

## Cutoff State

For state at a cutoff, filter events at or before the cutoff, then take the last effective event per business entity. Do not rely only on `current_status` when the request asks for historical or cutoff state.

```sql
with final_event as (
  select *
  from (
    select e.*,
           row_number() over (
             partition by e.task_id
             order by e.event_at desc, e.task_event_id desc
           ) as rn
    from dedup_task_events e
    where e.event_at <= :cutoff_at
  )
  where rn = 1
)
```

Use strict or inclusive boundaries exactly as stated. Common forms:

```sql
created_at >= :start_at and created_at <= :end_at
due_at < :cutoff_at
event_at <= :cutoff_at
```

## Money and FX

Minor-unit money converts to major units before FX:

```sql
(amount_minor / 100.0) * fx.usd_per_unit
```

Join `fx_rates` on the row service date and row currency:

```sql
join fx_rates fx
  on fx.rate_date = refund.service_date
 and fx.currency = refund.currency
```

For order gross comparisons tied to a refund date, value the order's `gross_amount_minor` using the refund service date and the order currency unless the request specifies another basis.

## Rounding, Ranking, and Medians

Keep raw numeric measures through ranking and risk logic. Round only the final field:

```sql
round(numerator * 1.0 / nullif(denominator, 0), 4)
```

Median in SQLite:

```sql
with ordered as (
  select value,
         row_number() over (order by value) as rn,
         count(*) over () as n
  from metric_values
)
select avg(value) as median_value
from ordered
where rn in ((n + 1) / 2, (n + 2) / 2);
```

For exact list ordering, perform the final `order by` in SQL and then preserve that order in JSON.

## Fulfillment and Carrier Delivery

For order completion by cutoff:

- Build eligible production orders from `orders` joined to `accounts`, `campaigns`, and `warehouses`.
- Campaign windows usually use `orders.order_created_at` between `campaigns.starts_at` and `campaigns.ends_at`, with the request's boundary semantics.
- Physical shipments are rows in `shipments`. An order with no shipment is incomplete.
- For each shipment, derive effective carrier state from deduplicated `carrier_scans` at or before the cutoff, ordered by `canonical_event_at`, then `scan_row_id`.
- A shipment is delivered by cutoff when its effective canonical status is `DELIVERED`.
- An order is complete only when it has at least one physical shipment and all associated physical shipments are delivered by cutoff.
- An on-time complete order requires every delivered shipment's delivery event time to be no later than `shipments.promised_delivery_at`.
- Severe lateness checks should use `julianday(delivered_at) - julianday(promised_delivery_at) > 1` or `julianday(cutoff_at) - julianday(latest_promise) > 1` for incomplete shipments with a promise.

Carrier correction tasks usually identify a row where raw and canonical values contradict inside an import batch or facility scope. Keep `raw_status`, `raw_event_at`, `source_system`, and `external_event_id` unchanged; correct only the approved canonical column.

## Refund Settlement and Leakage

Reusable settlement flow:

1. Join `refund_attempts` to `orders` and `accounts`; apply production, tier, segment, date-window, and status filters from the request.
2. Treat `status = 'SETTLED'` rows as settled logical refund candidates unless the request names different statuses.
3. Treat `status = 'REVERSED'` rows with `linked_refund_id` as linked reversals. Subtract reversal USD from the linked settled refund's USD.
4. Count distinct in-scope orders for eligible refunded order count.
5. Count distinct logical settled refunds by `refund_id`.
6. Count distinct effective reversals by reversal row or reversal refund id, according to the template wording.
7. Rank reason codes by unrounded effective net USD, then the request tie-break.
8. For leakage lists, aggregate order-level net refund USD after reversals and compare to order gross USD; also check duplicate unreversed logical refunds with the same normalized reason code when requested.

Use the request's service-date window for refund rows and the request's FX basis for both refunds and order gross.

## Warehouse Productivity

Reusable warehouse task flow:

- Filter `warehouse_tasks` by requested `warehouse_id`, `work_class = 'PRODUCTION'`, and the task creation window.
- Reconstruct task state at the cutoff from deduplicated `warehouse_task_events` when the request is cutoff-consistent.
- Completed production units usually come from `warehouse_task_events` rows with `event_type = 'COMPLETED'` at or before the cutoff.
- Employee units per hour is `sum(completed units) / sum(productive_minutes) * 60`; rank by the unrounded value, then `employee_id`.
- Completion rate is completed eligible task count divided by eligible task count.
- Rework task count is normally distinct eligible tasks with a `REWORK` event by cutoff or final cutoff state `REWORK`; follow the request wording if it chooses one.
- Delayed high-priority tasks use priority membership from the request, `due_at` strictness from the request, and not-completed-by-cutoff state.
- Lowest-performing teams rank by unrounded completion rate ascending, then `team_id`.

## Support Active-Time SLAs

Support active time is based on `case_events`, not just the case header snapshot.

Recommended event-state model:

- Active after `OPENED`, `OPEN`, `REOPENED`, or `CUSTOMER_REPLIED`.
- Inactive after `WAITING_CUSTOMER` or `RESOLVED`.
- `ASSIGNED`, `AGENT_RESPONDED`, and `ESCALATED` preserve the prior active or inactive state.

For each eligible case:

1. Deduplicate case events.
2. Keep events at or before the cutoff.
3. Sort by `event_at`, then `case_event_id`.
4. Convert events into intervals from each event to the next event, or to the cutoff.
5. Sum interval hours only while active.

First-response breach:

- End the clock at the first `AGENT_RESPONDED` event at or before the cutoff.
- If no agent response exists, use active elapsed time through the cutoff.
- Compare against the priority's first-response threshold.

Resolution active-clock breach:

- End the clock at the resolving `RESOLVED` event for cases resolved at the cutoff.
- Use active elapsed time through the cutoff for active cases.
- Compare against the priority's resolution threshold.

Open at cutoff includes cases whose reconstructed cutoff state is open or reopened. Reopened at cutoff is the reopened subset. Severe active cases combine active-at-cutoff state, priority membership, and resolution-threshold breach as specified by the request.

Worst-account ranking should aggregate after case-level breach flags are computed, then order by the exact request tie-breaks.

## Controlled Corrections

Use a correction transaction only when the prompt approves mutation. Before committing:

- Prove the target row is unique with a read-only query.
- Prove the old canonical value is still present.
- Compute the pre-correction metric.
- Prepare one update guarded by stable row id, old value, and relevant scope.
- Prepare one `correction_audit` insert using the request-provided `audit_id`, `correction_key`, `reason_code`, `corrected_at`, and `actor`.

After committing:

- Verify exactly one business row changed.
- Verify exactly one audit row exists with the requested values.
- Requery the target row and post-correction metric.
- Report success only if the request's success rule is satisfied; otherwise report the observed non-success state.
