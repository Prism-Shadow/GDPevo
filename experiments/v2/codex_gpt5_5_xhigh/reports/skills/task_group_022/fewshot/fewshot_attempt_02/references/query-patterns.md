# Atlas Commerce Query Patterns

Use these patterns as templates. Replace placeholder literals from the task payload; do not reuse example task values.

## Common CTEs

De-duplicate imported events by source identity:

```sql
with dedup_events as (
  select e.*
  from <event_table> e
  where not exists (
    select 1
    from <event_table> e2
    where e2.source_system = e.source_system
      and e2.external_event_id = e.external_event_id
      and (
        e2.ingested_at > e.ingested_at
        or (e2.ingested_at = e.ingested_at and e2.<row_id> > e.<row_id>)
      )
  )
)
```

Pick latest event state at a cutoff:

```sql
latest_state as (
  select e.*
  from dedup_events e
  where e.event_at <= '<cutoff_at>'
    and not exists (
      select 1
      from dedup_events e2
      where e2.<entity_id> = e.<entity_id>
        and e2.event_at <= '<cutoff_at>'
        and (
          e2.event_at > e.event_at
          or (e2.event_at = e.event_at and e2.<row_id> > e.<row_id>)
        )
    )
)
```

Some service instances reject very long SQL or window functions. If that happens, break work into narrower count/list queries and use correlated `NOT EXISTS` instead of `row_number()`.

## Fulfillment Scorecard

Use request payload values for campaign id, cutoff, severe thresholds, and status policy.

Core cohort:

- Join `orders` to `campaigns` and production `accounts`.
- Require the order's campaign id and creation inside the campaign active window.
- Reconstruct latest `order_events` state at the cutoff; exclude orders whose latest cutoff state is `CANCELLED`.

Shipment completion:

- De-duplicate `carrier_scans`.
- For each shipment, select the latest scan at or before the cutoff by `canonical_event_at`, tie-breaking by `scan_row_id`.
- An eligible order is complete only when it has at least one shipment and every shipment's latest cutoff `canonical_status` is `DELIVERED`.
- On-time complete means every delivered shipment was delivered no later than its `promised_delivery_at`.
- Severe exception means either the incomplete order's latest shipment promise is more than the request threshold before cutoff, or any completed shipment was delivered more than the threshold after its promise. Do not mark no-shipment/no-promise orders severe unless the request says so.

Regional rates:

- Join order `warehouse_id` to `warehouses.region`.
- Denominator remains all eligible orders in the region.
- Rank by unrounded regional rate ascending, then region ascending; round only output rates.

## Refund Reconciliation

Use request payload values for account tier/segment, date range, leakage policy, risk policy, and ranking size.

Effective refund rows:

```sql
with dedup_refunds as (
  select r.*
  from refund_attempts r
  where not exists (
    select 1
    from refund_attempts r2
    where r2.source_system = r.source_system
      and r2.external_event_id = r.external_event_id
      and (
        r2.ingested_at > r.ingested_at
        or (r2.ingested_at = r.ingested_at and r2.refund_row_id > r.refund_row_id)
      )
  )
),
scoped as (
  select r.*
  from dedup_refunds r
  join orders o on o.order_id = r.order_id
  join accounts a on a.account_id = o.account_id
  where a.is_internal = 0
    and a.is_test = 0
    and <account filters from request>
    and r.service_date between '<start_date>' and '<end_date>'
),
settled as (
  select * from scoped where status = 'SETTLED'
),
reversals as (
  select * from scoped
  where status = 'REVERSED' and linked_refund_id is not null
)
```

Metrics:

- Eligible refunded orders: `count(distinct settled.order_id)`.
- Effective settled logical refunds: `count(distinct settled.refund_id)`.
- Effective linked reversals: `count(distinct reversals.refund_id)`.
- Net refund USD: settled USD minus reversal USD, using `fx_rates` on each row's `service_date` and `currency`.
- Reason ranking: aggregate settled effective USD by normalized `reason_code`; order by unrounded USD descending, then reason code ascending.
- Leakage candidates: aggregate by order after subtracting linked reversals. Flag orders whose net effective refund USD exceeds order gross USD under the request's FX basis, or whose unreversed settled logical refunds contain duplicate normalized reason codes. Return candidate order IDs sorted as requested.
- Risk: compute candidate rate over eligible refunded orders and apply the request's policy in order.

## Carrier Quality Correction

Use request payload values for batch id, warehouse, cutoff, correction metadata, and status rule.

Pre-checks:

- Find raw/canonical contradictions in `carrier_scans` for the named import batch. A status contradiction is a row where the raw carrier status clearly maps to a different canonical status than stored.
- Confirm the request says exactly one contradiction is in scope. If your query finds zero or more than one, do not mutate.
- Compute pre-correction backlog before changing data.

Backlog cohort:

- Shipment membership is based on having an effective scan in the named batch at or before the cutoff.
- The final carrier status is the shipment's latest de-duplicated scan at or before the cutoff across carrier scans, ordered by `canonical_event_at` then `scan_row_id`.
- Backlog shipments are final status not `DELIVERED`; delivered shipments are final status `DELIVERED`.

Mutation pattern:

- Update only `carrier_scans.<approved canonical field>` on the target `scan_row_id`.
- Set correction metadata columns only if the request or endpoint requires them; never change raw/source fields.
- Insert one `correction_audit` row using the request's audit id/key, entity type, entity id, source row id, field name, old value, new value, reason code, corrected timestamp, and actor.
- Submit both statements through `/api/sql/transaction` so they commit atomically.
- Post-query the target row and `GET /api/correction-audit`; report `APPLIED` only if affected business rows, audit rows, and corrected value satisfy the request success rule.

## Warehouse Productivity

Use request payload values for warehouse id, created window, state cutoff, priorities, and status policy.

Core cohort:

- Eligible tasks are `warehouse_tasks` in the requested warehouse, with `work_class = 'PRODUCTION'`, and `created_at` inside the requested window.
- De-duplicate `warehouse_task_events` before counting units, minutes, rework, completion, or delay state.

Metrics:

- Completed production units: sum `units` from de-duplicated `COMPLETED` events for eligible tasks at or before the state cutoff.
- Employee units per hour: for each assigned employee, `sum(completed units) * 60.0 / sum(productive_minutes)` over completed events; rank by unrounded rate descending, then employee id ascending.
- Rework task count: distinct eligible tasks with a de-duplicated `REWORK` event at or before cutoff.
- Delayed high-priority tasks: eligible tasks with request-listed high priorities, `due_at` strictly before cutoff, and no de-duplicated `COMPLETED` event at or before cutoff. Sort task IDs as requested.
- Lowest-performing team: join employees for `team_id`; completion rate is completed eligible tasks divided by all eligible tasks in the team. Rank ascending by unrounded completion rate, then team id.
- Facility status: calculate completion rate and rework rate, then apply the request's status rules in order.

## Support Health

Use request payload values for account scope, opened window, cutoff, priority SLA thresholds, severe policy, ranking, and risk policy.

Core cohort:

- Join `support_cases` to production `accounts`.
- Apply requested segment/region/account filters.
- Use cases with `opened_at` inside the requested window.
- De-duplicate `case_events`.

State at cutoff:

- Reconstruct latest effective case event at or before the cutoff.
- Cases with latest event `RESOLVED` are resolved; cases with latest event `WAITING_CUSTOMER` are not active on the support clock.
- Active/open-at-cutoff cases are latest effective states that represent support-owned work, including open/reopened/customer-replied/escalated/assigned/responded states unless the request narrows this.
- Reopened-at-cutoff is the active subset whose latest state is `REOPENED`, unless the request defines a broader reopened lifecycle.

Support active time:

- Build ordered de-duplicated events per case up to the endpoint timestamp.
- The active clock starts at `OPENED` or the case `opened_at`.
- Active intervals run while support owns the case; pause after `WAITING_CUSTOMER`, resume at `CUSTOMER_REPLIED` or `REOPENED`, and stop at `RESOLVED`.
- For first response, the endpoint is the first `AGENT_RESPONDED`; if absent, use the cutoff.
- For resolution active-time breach, use `RESOLVED` time for resolved cases and cutoff for active cases.
- Compare active hours to the request's priority-specific thresholds.

Outputs:

- Severe active cases: active at cutoff, priority in the request's severe set (commonly urgent/high), and beyond the priority resolution active-time threshold. Sort IDs as requested.
- Worst accounts: aggregate severe active case count and active-clock breach count per account; order by the request's ranking keys.
- Median active resolution hours: calculate active resolution hours for cases resolved at or before cutoff, sort numeric values, average the two central values for even counts, and round final output.
- Support risk: compute severe-active and first-response breach rates over eligible cases and apply the request's risk policy in order.
