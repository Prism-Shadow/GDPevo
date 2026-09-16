# Atlas Workflow Reference

Use this reference after reading the task prompt and payloads. It summarizes the
reusable patterns from the staged examples without carrying over their solved
answer values.

## Service Shape

- `GET /api/schema` returns table DDL and indexes.
- `GET /api/data-dictionary` returns table and column meanings.
- `POST /api/sql` accepts JSON shaped as `{"sql": "select ..."}` and returns
  `columns`, `rows`, `row_count`, and `truncated`.
- `POST /api/sql/transaction` is for approved controlled mutations only.
- `GET /api/correction-audit` exposes committed correction audit records.

Always run schema and dictionary reads first, then small SQL probes. Useful
probes include `select distinct ...`, `group by status`, earliest/latest
timestamps, and join-cardinality checks.

## General SQL Pattern

Prefer a CTE pipeline:

```sql
with eligible as (
  select ...
  from ...
  where ...
),
entity_flags as (
  select
    entity_id,
    ... as is_complete,
    ... as is_breach,
    ... as ranking_metric
  from eligible
),
rollup as (
  select
    count(*) as eligible_count,
    sum(case when is_complete then 1 else 0 end) as complete_count
  from entity_flags
)
select * from rollup;
```

Build list fields from the same `entity_flags` CTE:

```sql
select entity_id
from entity_flags
where is_breach = 1
order by entity_id;
```

For rankings, keep unrounded metrics in SQL for `order by`, then round only the
value that is reported in JSON.

SQLite timestamp differences are usually easiest with `julianday`:

```sql
(julianday(actual_at) - julianday(promised_at)) * 24.0 as hours_late
```

For exact date joins such as FX rates, derive the calendar date with `date(...)`
only when the business rule uses a date rather than a timestamp.

## Imported Row Dedupe

Several tables contain upstream source identity fields and retry-friendly
indexes. When the task says "effective", "logical", "source retries",
"append-only", or similar, dedupe before business logic.

Common choices:

- For event tables, partition by `source_system, external_event_id` and keep the
  latest `ingested_at`, breaking ties by the stable row ID.
- For logical refunds, reason over distinct `refund_id` and linked reversals,
  not raw retry rows.
- For final status at a cutoff, rank effective rows for an entity by business
  event timestamp descending, then stable row ID descending.

Example:

```sql
with ranked as (
  select
    e.*,
    row_number() over (
      partition by source_system, external_event_id
      order by ingested_at desc, event_at desc, event_id desc
    ) as rn
  from order_events e
)
select *
from ranked
where rn = 1;
```

Use the actual row ID column for the table being queried.

## Production Scope

When a request scopes to production accounts, join `accounts` and filter:

```sql
a.is_internal = 0 and a.is_test = 0
```

Then apply the requested account tier, segment, region, campaign, warehouse, or
time-window filters. Keep account-production filtering in the base eligibility
CTE so every reported metric shares it.

## Fulfillment And Shipments

Relevant tables: `orders`, `accounts`, `campaigns`, `shipments`,
`carrier_scans`, `warehouses`.

Use the request's campaign, order-created window, production account rule, and
cutoff. A robust shipment pipeline is:

1. Select eligible orders.
2. Select shipments for those orders.
3. For each shipment, find the final effective carrier scan at or before the
   cutoff using `canonical_event_at` and `scan_row_id`.
4. Mark an order complete only when it has at least one shipment and every
   shipment's final effective status satisfies the request's delivered rule.
5. Mark on-time completion only when every delivered shipment is delivered no
   later than its own `promised_delivery_at`.
6. Use warehouse region from the order's assigned warehouse for regional
   rollups, unless the prompt says to use shipment warehouse.

Incomplete orders stay in denominators when the request defines rates that way.
For severe exception rules, calculate entity-level flags for both incomplete
late promises and completed-but-late shipments. Orders with no shipment promise
only qualify if the request explicitly defines such a case.

## Refunds, Payments, And FX

Relevant tables: `refund_attempts`, `orders`, `accounts`, `fx_rates`, sometimes
`payment_events`.

Useful defaults from the examples:

- Treat settled refund attempts as effective refund value unless the prompt
  narrows or changes status rules.
- Treat linked reversal rows through `linked_refund_id`.
- Convert each refund or reversal by joining `fx_rates` on row currency and the
  row's service date.
- Convert an order's gross amount for leakage comparison using the same service
  date basis required by the prompt.
- Normalize reason codes with a stable expression such as
  `upper(trim(reason_code))` unless the dictionary gives a stricter rule.
- Count distinct logical refunds and distinct eligible orders separately.

For leakage or exception lists, make an order-level CTE containing net refund
USD, gross order USD, unreversed logical-refund counts by reason, and candidate
flags. Sort output order IDs ascending unless the template says otherwise.

## Carrier Data-Quality Corrections

Relevant tables: `carrier_scans`, `shipments`, `source_import_batches`,
`correction_audit`.

Only mutate when the request explicitly approves a minimal canonical correction.
Before mutating:

1. Locate the single target contradiction inside the requested batch, warehouse,
   entity type, and cutoff.
2. Verify the old canonical value, requested new canonical value, source row ID,
   shipment or entity ID, and backlog impact with read-only SQL.
3. Calculate pre-correction metrics from the same effective-state logic that
   will be used post-correction.

The transaction should be minimal:

```sql
update carrier_scans
set canonical_status = :new_value,
    corrected_at = :corrected_at,
    correction_reason = :reason_code
where scan_row_id = :source_row_id
  and canonical_status = :old_value;

insert into correction_audit (
  audit_id, correction_key, entity_type, entity_id, source_row_id,
  field_name, old_value, new_value, reason_code, corrected_at, actor
) values (
  :audit_id, :correction_key, :entity_type, :entity_id, :source_row_id,
  :field_name, :old_value, :new_value, :reason_code, :corrected_at, :actor
);
```

Post-verify the corrected canonical value, audit row, affected-row counts, and
post-correction metric. Report an applied status only when every success
condition in the request is satisfied.

The same pattern applies to other controlled correction tasks, such as inventory
canonical unit corrections: identify one approved canonical field, update only
that field and correction metadata, insert one audit row, then verify.

## Warehouse Productivity

Relevant tables: `warehouse_tasks`, `warehouse_task_events`, `employees`,
`warehouses`.

Use the task-created window for eligibility and the state cutoff for event state.
For each eligible production task:

- Completion should come from task events at or before the cutoff, not only from
  `current_status`.
- Completed units and productive minutes should be attached to completed
  production work. Sum them at the task-event level, then aggregate by employee.
- Units per hour is `completed_units / productive_minutes * 60`; guard against
  divide-by-zero.
- Rework is usually a task-level flag based on at least one rework event.
- Delayed high-priority tasks require the request's priority set, due date rule,
  and "not completed by cutoff" flag.
- Team performance should use the same eligible-task denominator, grouped by
  employee team or task team as requested.

For top employees and low-performing teams, use the request's explicit
tie-breakers in SQL.

## Support And SLA Health

Relevant tables: `support_cases`, `case_events`, `accounts`.

Support tasks usually require active-time clocks rather than raw elapsed time.
Derive active intervals from ordered events at or before the cutoff. Treat
customer-waiting and resolved states as inactive; treat opened/open/reopened,
assigned, agent response, escalation, and customer reply states as active unless
the request says otherwise.

Interval skeleton:

```sql
with ordered_events as (
  select
    e.*,
    lead(e.event_at, 1, :cutoff) over (
      partition by e.case_id
      order by e.event_at, e.case_event_id
    ) as next_event_at
  from case_events e
  join eligible_cases c on c.case_id = e.case_id
  where e.event_at <= :cutoff
),
intervals as (
  select
    case_id,
    event_type,
    event_at,
    next_event_at,
    case
      when event_type in (
        'OPENED','OPEN','REOPENED','ASSIGNED',
        'AGENT_RESPONDED','ESCALATED','CUSTOMER_REPLIED'
      )
      then (julianday(next_event_at) - julianday(event_at)) * 24.0
      else 0.0
    end as active_hours
  from ordered_events
)
select case_id, sum(active_hours) as active_hours_to_cutoff
from intervals
group by case_id;
```

For first-response breaches, sum active time from case open to the first
`AGENT_RESPONDED`; for unresponded cases, sum active time through the cutoff.
For resolution breaches and median active resolution time, sum active time from
case open to the first effective `RESOLVED`; for active unresolved cases, sum
through the cutoff when the breach definition says to do so.

Determine open or reopened at cutoff from the latest effective event at or
before the cutoff when possible. If a snapshot appears inconsistent with events,
trust the event-derived state for event-defined metrics and use a probe query to
document the mismatch for yourself.

Worst-account lists should be built from account-level CTEs that count severe
active cases and active-clock breaches using the same eligible case population.
Apply the request's ranking order exactly.

## Inventory Patterns

Relevant tables: `inventory_movements`, `inventory_snapshots`, `products`,
`warehouses`, `correction_audit`.

For stock analysis:

- Use `canonical_quantity_each` for normalized stock movement math.
- `raw_quantity`, `raw_uom`, and raw multipliers preserve source facts and
  should not be overwritten unless a request explicitly approves it.
- Snapshot availability is usually `on_hand_each - reserved_each`, but use the
  request's definition if present.
- Movement rollups should respect the requested occurrence window and warehouse
  or SKU scope.
- For source/canonical unit contradictions, compare the raw quantity and raw
  unit multiplier to the canonical quantity or multiplier, then apply only the
  requested canonical correction with an audit row.

## Final Assembly Checklist

Before writing `answer.json`:

- Every answer key comes from the template, and no extra keys are present.
- Counts are integers, not numeric strings.
- Money and rates use the requested final precision.
- Ranking lists are sorted by unrounded metrics and tie-breakers.
- ID arrays are unique and sorted as requested.
- Risk or status values come from applying the policy thresholds after computing
  the numerator and denominator from the same eligible population.
- For mutation tasks, post-correction verification queries support every field
  in `mutation_result`, `audit_record`, and the correction status.
