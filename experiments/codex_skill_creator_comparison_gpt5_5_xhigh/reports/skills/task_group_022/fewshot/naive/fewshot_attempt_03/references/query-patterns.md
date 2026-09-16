# Atlas Query Patterns

These patterns are reusable guidance for Atlas Commerce Operations tasks. Always prefer the current task's payload and the live `/api/schema` and `/api/data-dictionary` over assumptions here.

## API And SQL Basics

- The SQL endpoint accepts JSON shaped like `{"sql": "select ..."}` and returns `columns`, `rows`, `row_count`, and `truncated`.
- Atlas uses SQLite-compatible SQL. Prefer CTEs and window functions so each metric is inspectable.
- Stored timestamps are ISO-8601 UTC text ending in `Z`; dates are `YYYY-MM-DD` text.
- Apply inclusive windows with `>= start AND <= end`. Apply strict rules literally, for example `due_at < cutoff`.
- Compare and order by unrounded expressions. Round only the final reported value.
- Convert monetary minor units to major units before FX, normally `amount_minor / 100.0` or `gross_amount_minor / 100.0`, then multiply by `fx_rates.usd_per_unit` for that row's service date and currency.
- Use `julianday(later) - julianday(earlier)` multiplied by 24 for elapsed hours when SQL must compute hour thresholds.

## Core Schema Conventions

- Production accounts are `accounts.is_internal = 0 AND accounts.is_test = 0`. Apply this through `accounts` for production orders, shipments, refunds, and support cases unless a task defines a narrower or different production filter.
- `orders` link accounts, campaigns, warehouses, gross values, and order creation windows.
- `shipments` link physical shipments to orders. `carrier_scans` are the effective carrier event source.
- `refund_attempts` contains logical refunds and linked reversals; use `refund_id` and `linked_refund_id` to collapse attempts and reversals.
- `warehouse_tasks` contains task scope and current assignment; `warehouse_task_events` contains completion, units, minutes, and rework events.
- `support_cases` contains case headers; `case_events` contains the lifecycle needed for cutoff and active-time analysis.
- Snapshot `current_status` fields may lag history and are not enough for historical cutoff tasks when event tables exist.

## Effective Source Rows

Many imported tables contain `source_system`, `external_event_id`, and `ingested_at`. De-duplicate retries before business logic:

```sql
with effective_events as (
  select *
  from (
    select t.*,
           row_number() over (
             partition by source_system, external_event_id
             order by ingested_at desc, rowid desc
           ) as rn
    from some_imported_table t
  )
  where rn = 1
)
```

If the table has a stable row ID that sorts deterministically, use it as the final tie-breaker instead of `rowid`.

## Historical Cutoff State

For an entity's status as of a cutoff, filter events at or before the cutoff, then select the latest effective event:

```sql
row_number() over (
  partition by entity_id
  order by event_at desc, stable_event_id desc
) = 1
```

For carrier shipment state, use `canonical_event_at` and `scan_row_id` as the time and tie-breaker. A shipment is delivered by a cutoff when its effective final canonical status at or before the cutoff is `DELIVERED`; its delivered time is the effective delivered scan time used for promise comparisons.

## Fulfillment Scorecards

For campaign fulfillment reports:

- Join `orders` to `campaigns`, `accounts`, and `warehouses`.
- Eligible orders usually require production accounts, the requested `campaign_id`, and `order_created_at` inside the campaign's active window or the request's explicit order window.
- Complete orders require at least one physical shipment and every associated shipment effectively `DELIVERED` by the cutoff.
- On-time complete orders require every associated shipment delivered no later than that shipment's `promised_delivery_at`.
- Incomplete orders stay in the denominator for on-time complete-order rates.
- Severe exceptions usually include incomplete orders where the cutoff is more than 24 hours after the latest shipment promise, plus completed orders with any shipment delivered more than 24 hours after promise. Orders with no shipment promise do not satisfy promise-late severe rules unless the request adds another rule.
- Regional rollups use the warehouse region assigned to the order. Rank worst regions by unrounded regional rate ascending, then region ascending.

## Refund Reconciliation

For refund close or leakage tasks:

- Scope orders through production accounts and any requested segment/tier/region/order window.
- Treat principal refunds as rows with `linked_refund_id IS NULL`; treat reversals as rows with `linked_refund_id IS NOT NULL`.
- Collapse retries to effective logical refunds by `refund_id`, keeping the latest relevant attempt after source de-duplication. Count distinct settled principal `refund_id` values for logical refund counts.
- Use effective settled principal refunds in the requested service-date window. Use effective settled linked reversals that point at those principal refunds, using the reversal service date and currency for reversal FX.
- Net USD equals settled principal refund USD minus linked reversal USD. Attribute linked reversal USD back to the principal refund's normalized reason when ranking reasons.
- Normalize reason codes consistently, usually `upper(trim(reason_code))`, unless the request supplies a different normalization.
- Eligible refunded orders are distinct in-scope orders with at least one effective settled principal logical refund.
- Leakage candidates often include orders where net refund USD is greater than gross order USD valued using the refund comparison FX policy, or orders with at least two unreversed effective settled principal refunds sharing the same normalized reason.
- Sort leakage order IDs ascending. Rank reason codes by unrounded net USD descending, then normalized reason code ascending.

## Carrier Quality Corrections

For carrier reconciliation tasks:

- Find the requested import batch, warehouse, and cutoff scope by joining `carrier_scans` to `shipments` and production orders/accounts if the request says production shipments.
- Identify contradictions by comparing raw carrier facts to canonical fields. For example, raw status `DELIVERED` with canonical status not `DELIVERED` is a canonical-status contradiction. Confirm the request's promised cardinality, such as exactly one contradiction, before mutating.
- Pre-correction backlog is the count of in-scope shipments whose effective final canonical status at or before the cutoff is not `DELIVERED`.
- Approved minimal corrections must preserve raw fields, source identity fields, timestamps supplied by the source, and unrelated rows. Update only the approved canonical field, plus only correction metadata that the live schema or task explicitly requires.
- Insert exactly one `correction_audit` row using the request's approved audit fields. Use the request's correction key as the idempotency key.
- Report `APPLIED` only when one business row and one audit row commit and a post-change query confirms the new canonical value. Otherwise report `NOT_APPLIED` and the actually observed row counts and metrics.
- Post-correction backlog uses the same query as pre-correction after the transaction. Backlog delta is post minus pre.

## Warehouse Productivity

For warehouse production health reports:

- Eligible tasks usually filter `warehouse_tasks` by requested `warehouse_id`, `work_class = 'PRODUCTION'`, and `created_at` inside the request window.
- Complete-by-cutoff tasks have an effective `warehouse_task_events.event_type = 'COMPLETED'` at or before the state cutoff.
- Completed production units and productive minutes come from completed event rows for eligible tasks at or before the cutoff.
- Employee units per hour is `sum(completed units) / sum(productive_minutes) * 60`. Rank employees by unrounded units per hour descending, then `employee_id` ascending.
- Rework task count is distinct eligible tasks with a `REWORK` event at or before the cutoff. Rework rate is rework task count divided by eligible task count.
- Delayed high-priority tasks have priority `HIGH` or `URGENT`, `due_at` strictly before the cutoff, and no completion by the cutoff. Sort task IDs ascending.
- Lowest-performing team uses completion rate per `employees.team_id`, ordered by unrounded completion rate ascending and then `team_id` ascending.
- Facility status thresholds use unrounded completion and rework rates.

## Support Health

For support health reviews:

- Eligible cases join `support_cases` to production `accounts` and apply requested segment, regions, and opened window.
- Use de-duplicated `case_events` for lifecycle calculations. Common event types include `OPENED`, `OPEN`, `REOPENED`, `WAITING_CUSTOMER`, `CUSTOMER_REPLIED`, `AGENT_RESPONDED`, `ASSIGNED`, `ESCALATED`, and `RESOLVED`.
- Active support time starts at case open, pauses at `WAITING_CUSTOMER`, resumes at `CUSTOMER_REPLIED`, `OPEN`, or `REOPENED`, and stops at `RESOLVED`. Cap open intervals at the report cutoff.
- First-response elapsed active time ends at the first `AGENT_RESPONDED`. If no agent response exists by cutoff, use active elapsed time through the cutoff for breach testing.
- Resolution active time ends at `RESOLVED` for resolved cases. For cases open or reopened at cutoff, use active elapsed time through the cutoff for resolution breach testing.
- Open at cutoff includes cases whose cutoff state is `OPEN` or `REOPENED`; reopened at cutoff is the reopened subset.
- Severe active cases are active at cutoff, priority `URGENT` or `HIGH`, and beyond the priority resolution active-time threshold. Sort case IDs ascending.
- Worst accounts are ranked by severe active case count descending, then active-clock resolution breach count descending, then account ID ascending.
- Median active resolution hours uses eligible cases resolved by the cutoff. For an even count, average the two central unrounded values, then round the reported median to the requested precision.
- Support risk policies use unrounded breach rates with the requested denominator.

## Final JSON Checks

Before writing `answer.json`:

- Compare keys against the answer template's `required` list.
- Ensure arrays meet `minItems`/`maxItems`, uniqueness, and ordering rules.
- Ensure enums match exactly, including case.
- Ensure numbers use the requested decimal precision. JSON numbers should not be strings.
- Re-run focused SQL checks for any long ID list, top-N ranking, or status/risk classification.
