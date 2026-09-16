---
name: atlas-ops-sql-solver
description: Use this skill for Atlas Commerce Operations tasks that require exact JSON answers from prompt payloads and the authenticated Atlas database, including cutoff-based fulfillment scorecards, refund reconciliation, carrier-scan canonical corrections, warehouse productivity reviews, support health reviews, and similar operational analytics. It guides schema discovery, SQL against the Atlas API, de-duplication of source imports, event-timeline logic, controlled corrections, rounding, ordering, risk/status rules, and answer.json validation.
---

# Atlas Operations SQL Solver

Use this when the task references the Atlas Commerce Operations workplace, `<TASK_ENV_BASE_URL>`, `answer_template.json`, or a request payload asking for an exact `answer.json`.

## Core Workflow

1. Read the prompt, `input/payloads/answer_template.json`, and every request payload before querying.
2. Extract the cohort, cutoff/window boundaries, metric definitions, ranking tie-breakers, rounding rules, status/risk policy, and required output fields.
3. Call `GET /api/schema` and `GET /api/data-dictionary`; do not assume table details from memory if the live schema is available.
4. Use `POST /api/sql` with `{"sql":"..."}` for read-only analysis. It returns `{columns, rows, row_count, truncated}`.
5. For correction tasks, use read-only SQL to identify the single approved target first. Use `POST /api/sql/transaction` only when the request explicitly asks for an approved correction, then verify the business row, audit row, and post-change analytics.
6. Compute with SQL CTEs where possible, keeping unrounded values for ordering and policy thresholds. Round only final reported numbers.
7. Write exactly one JSON object to `answer.json` that conforms to the template: no commentary, no extra keys, arrays in the requested order.

The helper at `scripts/atlas_api.py` can call the API and validate an answer template using only the Python standard library.

## API Helper

Examples:

```bash
python <skill-path>/scripts/atlas_api.py schema
python <skill-path>/scripts/atlas_api.py dictionary
python <skill-path>/scripts/atlas_api.py sql query.sql > result.json
python <skill-path>/scripts/atlas_api.py audit
python <skill-path>/scripts/atlas_api.py validate answer.json input/payloads/answer_template.json
```

Set `TASK_ENV_BASE_URL` if the prompt gives a URL other than the default, and `TASK_ENV_API_TOKEN` must contain the bearer token.

## Atlas SQL Patterns

Timestamps are ISO-8601 UTC text, so direct text comparison works for inclusive or strict cutoffs. Be explicit about `<=`, `<`, `>=`, and `BETWEEN` according to the request.

Source event tables can contain retries. For imported append-only rows, first create an effective-row CTE:

```sql
with effective_events as (
  select *
  from (
    select e.*,
           row_number() over (
             partition by source_system, external_event_id
             order by ingested_at desc, <stable_row_id> desc
           ) as rn
    from <event_table> e
  )
  where rn = 1
)
```

Then derive state at a cutoff from the effective event history:

```sql
final_state as (
  select *
  from (
    select e.*,
           row_number() over (
             partition by <entity_id>
             order by <event_at> desc, <stable_row_id> desc
           ) as rn
    from effective_events e
    where <event_at> <= :cutoff_at
  )
  where rn = 1
)
```

Use current snapshot columns (`current_status`) only when the request asks for the snapshot. Cutoff analytics usually require effective event histories instead.

For production populations, exclude internal and test accounts when accounts are in scope:

```sql
join accounts a on a.account_id = ...
where a.is_internal = 0 and a.is_test = 0
```

For money, convert minor units to major currency units and multiply by `fx_rates.usd_per_unit` for the row service date or requested valuation date:

```sql
(amount_minor / 100.0) * fx.usd_per_unit
```

For sorted ID arrays, select the exact IDs ordered ascending and assemble the JSON array in the final answer. If the SQL endpoint truncates, narrow or paginate the query; do not infer missing IDs.

## Fulfillment Scorecards

Typical tables: `campaigns`, `orders`, `accounts`, `warehouses`, `shipments`, `carrier_scans`.

Use this shape:

- Eligible orders: production accounts/orders attributed to the requested campaign, with `order_created_at` inside the campaign active window or explicit request window.
- Physical shipments: rows in `shipments`; an order with no shipment is incomplete.
- Shipment final status at cutoff: use effective `carrier_scans`, ordered by `canonical_event_at`, then `scan_row_id`, filtered at or before cutoff.
- Complete order: at least one shipment and every shipment's final effective canonical status is `DELIVERED`.
- On-time complete order: complete and every shipment's delivered canonical event time is no later than that shipment's `promised_delivery_at`.
- Severe exception: apply the request exactly. Common pattern: incomplete and cutoff is more than 24 hours after the latest shipment promise, or completed with any shipment delivered more than 24 hours after its promise. Handle no-shipment/no-promise cases as the request states.
- Regional rates: denominator is all eligible orders in that warehouse region; rank by unrounded rate ascending, then region ascending.
- Overall status: compute severe rate from severe IDs divided by eligible orders and apply the policy in priority order.

Do not let incomplete orders fall out of denominators.

## Refund Reconciliation

Typical tables: `accounts`, `orders`, `refund_attempts`, `fx_rates`.

Use this shape:

- Scope accounts by requested tier/segment/region and production flags.
- Effective logical refunds are distinct effective `refund_id` values with in-scope `service_date` and settled status.
- Linked reversals are effective rows whose reversal status links to an in-scope settled logical refund through `linked_refund_id`.
- Net USD is settled refund USD minus linked reversal USD using daily FX for each row's service date and currency.
- Reason ranking uses normalized reason codes, usually `upper(trim(reason_code))`, ordered by unrounded effective net USD descending then reason ascending.
- For leakage candidates, evaluate each order after reversals. Common triggers are net refund USD greater than order gross USD valued at the refund service-date FX rate, or at least two unreversed settled logical refunds with the same normalized reason.
- Count distinct eligible orders, distinct logical refunds, and distinct linked reversals separately. Do not count retry rows as separate logical refunds.

Round the final net amount to the requested decimal places only after all additions/subtractions.

## Carrier Quality Corrections

Typical tables: `source_import_batches`, `carrier_scans`, `shipments`, `orders`, `accounts`, `correction_audit`.

Use this shape:

1. Build the shipment cohort from the request: warehouse, import batch, cutoff, production shipment/account rules, and "has effective scan in batch at or before cutoff" membership.
2. Find the one raw/canonical contradiction in the named batch by comparing raw carrier meaning to `canonical_status`. Preserve raw fields and source identity fields.
3. Calculate pre-correction backlog from final effective carrier status at cutoff: backlog means final canonical status is not `DELIVERED`.
4. Apply only the approved minimal canonical field correction and the corresponding audit insert. Keep the request-provided audit identifiers, actor, timestamp, and reason code.
5. Verify exactly one business row changed, exactly one audit row exists, and the corrected row now has the intended canonical value. Return `APPLIED` only if the request's success rule is satisfied; otherwise return `NOT_APPLIED` with observed counts.
6. Recompute post-correction backlog with the same cohort and cutoff.

When constructing the audit record, use the corrected source row as `source_row_id`, the affected shipment as the business `entity_id` when the request treats the carrier scan as shipment-scoped, and `entity_type`/`field_name` exactly as the request/database convention requires.

## Warehouse Productivity

Typical tables: `warehouse_tasks`, `warehouse_task_events`, `employees`.

Use this shape:

- Eligible tasks: requested warehouse, `work_class = 'PRODUCTION'`, and `created_at` inside the inclusive or exact task window.
- Effective task events: de-duplicate `warehouse_task_events` by source identity, then use events at or before the state cutoff.
- Completed tasks: tasks with an effective `COMPLETED` event by the cutoff or final effective state of `COMPLETED`, according to the request wording.
- Completed units and productive minutes: sum `units` and `productive_minutes` from effective completed events attached to eligible tasks.
- Employee units per hour: `(sum(completed units) / sum(productive_minutes)) * 60`; rank descending by unrounded value, then `employee_id` ascending.
- Rework count: count eligible tasks with an effective `REWORK` signal by cutoff unless the request specifies final-state rework only.
- Delayed high priority: priority in the requested high set, `due_at` strictly before cutoff, and not completed by cutoff.
- Team completion rate: group eligible tasks by the assigned employee's `team_id`; rank completion rate ascending, then `team_id` ascending.

Calculate completion rate and rework rate against all eligible production tasks, not just tasks with events.

## Support Health

Typical tables: `accounts`, `support_cases`, `case_events`.

Use this shape:

- Eligible cases: production accounts matching requested segment/regions, with `opened_at` inside the requested window.
- Effective case events: de-duplicate `case_events` by source identity.
- State at cutoff: derive final effective event/current active state at or before cutoff. Treat `OPEN` and `REOPENED` as active when the request says open-at-cutoff includes reopened cases.
- First response breach: compare active time from opening to first `AGENT_RESPONDED`; for unresponded cases, use active elapsed time through the cutoff.
- Resolution breach: for resolved cases, compare active time to `RESOLVED`; for active cases, use active elapsed time through the cutoff.
- Support active time: count time while the case is waiting on support; exclude intervals after `WAITING_CUSTOMER` until customer activity or reopening resumes the clock, unless the request defines a different basis.
- Severe active cases: active at cutoff, priority in the severe set, and beyond the priority resolution active-time threshold. Sort case IDs ascending.
- Worst accounts: group eligible cases by account and rank by severe active case count descending, active-clock breach count descending, then account ID ascending.
- Median resolved active hours: compute active resolution hours for cases resolved by cutoff; for an even count, average the two central values. Round only the reported median.

Apply support risk policies using rates over the eligible case denominator and the exact "below" versus "at least" semantics in the request.

## Validation Checklist

Before writing the final answer:

- Re-run the cohort count independently or with a narrower check.
- Confirm arrays are sorted and have the requested cardinality/uniqueness.
- Confirm rank tie-breakers use unrounded metrics.
- Confirm all rates include the correct denominator and incomplete/active rows remain in scope.
- Confirm final numeric precision matches the template (`decimal_places`, `precision`, `multipleOf`, or description).
- Validate `answer.json` against the template with the helper or an equivalent check.
- If a mutation was required, query the audit endpoint and post-change row before setting an applied status.
