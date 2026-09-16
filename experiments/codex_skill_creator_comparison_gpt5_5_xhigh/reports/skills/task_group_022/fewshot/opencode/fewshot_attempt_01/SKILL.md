---
name: atlas-commerce-ops
description: Use this skill for Atlas Commerce Operations tasks that ask Codex to analyze the authenticated workplace database, calculate operational metrics, reconcile refunds or fulfillment/support/warehouse results, perform an approved minimal source-data correction with audit, or write an exact answer.json from request payloads and an answer_template.json. Trigger whenever the prompt mentions Atlas, TASK_ENV_BASE_URL, /api/schema, /api/sql, fulfillment scorecards, refund reconciliation, carrier quality corrections, warehouse productivity, support health, production cohorts, cutoff-based metrics, or controlled SQL transactions.
---

# Atlas Commerce Operations

Use this skill to solve Atlas workplace tasks that combine JSON business facts, a JSON output contract, and SQL access to the task environment.

## Core workflow

1. Read the user prompt, every request JSON in `input/payloads/`, and `input/payloads/answer_template.json`.
2. Fetch live metadata before writing analysis SQL:
   - `GET /api/schema`
   - `GET /api/data-dictionary`
3. Translate the request into explicit cohort filters, cutoff rules, metric definitions, ordering rules, rounding rules, and risk/status thresholds.
4. Build SQL in stages with CTEs. Run small count checks for each cohort before computing the final object.
5. For cutoff state, prefer append-only event or scan history over denormalized `current_status` snapshots when the request says "effective", "as of cutoff", "state at cutoff", or gives an event-basis definition.
6. Round only final reported values. Use unrounded values for ranking and threshold comparisons unless the request says otherwise.
7. Write only `answer.json`, matching the template exactly: required keys only, correct nesting, sorted arrays, exact cardinality, no commentary.

Use `scripts/atlas_api.py` from this skill to remove HTTP boilerplate. Run it from the skill root or with an absolute path to the script:

```bash
python scripts/atlas_api.py schema
python scripts/atlas_api.py dictionary
python scripts/atlas_api.py sql "select count(*) as n from orders"
python scripts/atlas_api.py sql-file query.sql
python scripts/atlas_api.py audit
python scripts/atlas_api.py post /api/sql/transaction transaction_body.json
```

The helper reads `TASK_ENV_API_TOKEN` and uses `TASK_ENV_BASE_URL` if set, otherwise `http://task-env:9022`.

## Atlas table map

Common tables from the Atlas schema:

- `accounts`: account master data. Treat production accounts as `is_internal = 0 and is_test = 0`.
- `orders`, `order_lines`, `order_events`: order headers, items, and append-only order lifecycle events.
- `campaigns`: campaign active windows.
- `shipments`, `carrier_scans`: shipment headers and raw/canonical carrier observations.
- `refund_attempts`, `payment_events`, `fx_rates`: refunds, payment events, and daily USD FX rates.
- `warehouse_tasks`, `warehouse_task_events`, `employees`, `warehouses`: warehouse work and labor events.
- `support_cases`, `case_events`: support case headers and lifecycle events.
- `correction_audit`: public audit records for controlled canonical corrections.

Imported/source event tables usually have `source_system`, `external_event_id`, and `ingested_at`. When a request says "effective" or refers to source retries, deduplicate by `(source_system, external_event_id)` and keep the latest `ingested_at`, with the stable row id as a deterministic tie-breaker.

## SQL habits that prevent wrong answers

- Preserve the denominator. Start from the eligible cohort and `LEFT JOIN` outcomes so incomplete, unresolved, or no-shipment rows remain counted.
- Count distinct business ids when the template says orders, shipments, cases, tasks, logical refunds, or accounts. Count physical rows only when the template asks for rows.
- Compare Atlas UTC timestamps as ISO text only when all values are UTC `...Z`; otherwise normalize in SQL.
- Translate inclusive and strict boundaries literally. Examples: inclusive windows use `>= start and <= end`; "strictly before cutoff" uses `< cutoff`.
- Use `sum(case when ... then 1 else 0 end)` or `count(*) filter (...)` only if the SQLite version supports it. The safer portable form is `sum(case when condition then 1 else 0 end)`.
- Cast ratio denominators: `1.0 * numerator / nullif(denominator, 0)`.
- Sort IDs lexicographically ascending when the template says ascending; Atlas IDs are fixed-width strings.
- Convert minor monetary units to major currency before FX: `(amount_minor / 100.0) * usd_per_unit`.
- Join `fx_rates` by the row's service date or requested valuation date and row currency. Do not reuse the order currency rate for refund/reversal rows unless the request says so.
- For ranking, order by the unrounded metric, then by the stated tie-breaker. Report the rounded metric afterward.

## Domain patterns

### Fulfillment scorecards

For campaign fulfillment:

- Eligible production orders: join `orders` to `accounts` for production flags and to `campaigns` for campaign id/window. Apply the request's campaign id and campaign active-window boundaries.
- Physical shipments: rows in `shipments`.
- Complete order: at least one physical shipment and every physical shipment is effectively `DELIVERED` by the cutoff.
- On-time complete order: complete, and every shipment's delivered timestamp is no later than `shipments.promised_delivery_at`.
- Incomplete orders stay in the denominator for the overall and regional rates.
- Severe exception logic usually depends on both incomplete overdue promises and delivered-more-than-24-hours-late shipments. Implement the exact request text; incomplete orders with no shipment promise should not satisfy a promise-based severe rule.
- Warehouse region rollups use `warehouses.region` from the order's assigned warehouse.

Carrier-delivery SQL should derive one delivered timestamp per shipment from effective carrier scans at or before the cutoff. Keep both "ever delivered by cutoff" and the delivered timestamp for lateness checks.

### Refund reconciliation

For refund close tasks:

- Scope accounts through `accounts` tier/segment/region and production flags.
- Treat `refund_attempts.status = 'SETTLED'` as settled logical refunds unless the request states another status.
- Treat linked `REVERSED` rows through `linked_refund_id`; subtract their USD value from the linked settled refund or order net.
- Normalize reason codes with `upper(trim(reason_code))` before grouping.
- Count logical refunds with `distinct refund_id`, not retry/source rows, after applying effective-row deduplication.
- Net USD is settled refund USD minus linked reversal USD, using daily `fx_rates.usd_per_unit` for each refund or reversal service date and currency.
- Leakage candidates are order-level. Evaluate every candidate rule in the request, dedupe order ids, then sort as requested.
- Risk policies usually use leakage candidates divided by eligible refunded orders plus a net-refund threshold. Apply the named tiers in order from least severe to most severe.

### Carrier quality corrections

For controlled carrier corrections:

1. Use read-only SQL first to identify the exact candidate contradiction in the named import batch, warehouse, population, and cutoff.
2. Confirm the target row id, shipment id, canonical field, old canonical value, desired canonical value, pre-correction backlog count, and expected post-correction effect.
3. Mutate only the approved canonical field and correction metadata allowed by the request. Never alter raw source values, source identity fields, unrelated rows, or analytic rows outside the target.
4. Insert exactly one `correction_audit` record using the request's audit id, correction key, reason code, corrected timestamp, and actor.
5. Use `/api/sql/transaction` for the update and audit insert. If the transaction endpoint shape is not documented in the prompt, first probe it with a harmless read-only statement or inspect its error response; do not send a mutating body until the body shape is confirmed.
6. Add guards in the `update`: target row id, shipment id, field old value, and null or expected correction metadata if relevant.
7. Verify after commit with a fresh select and `GET /api/correction-audit`.
8. Report `APPLIED` only when exactly one business row and one audit row committed and the post-change query confirms the new canonical value. Otherwise report `NOT_APPLIED` with the observed counts and values.

For backlog, compute final effective carrier status per shipment at the cutoff by ordering effective scans by canonical event timestamp and stable scan id. The backlog is the scoped shipments whose final effective canonical status is not `DELIVERED`.

### Warehouse productivity

For warehouse production reviews:

- Eligible tasks: `warehouse_tasks` in the requested warehouse, `work_class = 'PRODUCTION'`, and created within the requested window.
- State cutoff: derive completed/rework/delayed state from `warehouse_task_events` at or before the cutoff when event history is available.
- Completed production units: sum units on completed events for eligible tasks completed by the cutoff.
- Employee units per hour: total completed units divided by total productive minutes attached to those completed units, multiplied by 60. Rank by unrounded units per hour descending, then employee id ascending.
- Rework task count: count eligible tasks with a rework state/event by the cutoff, according to the request wording.
- Delayed high-priority task: priority in the request's high-priority set, `due_at` strictly before cutoff, and not completed by cutoff.
- Lowest-performing team: group eligible tasks by the assigned employee's `team_id`; rank by completion rate ascending, then team id ascending.
- Facility status: apply the completion-rate and rework-rate tiers in request order.

### Support health

For support reviews:

- Scope eligible cases through `support_cases` joined to production `accounts` with the requested segment, region, tier, and opened-window filters.
- Determine state at cutoff from effective `case_events` ordered by `event_at` and stable event id. Use header `current_status` only as a fallback or sanity check.
- Active states include open/reopened work. `WAITING_CUSTOMER` pauses active time, `RESOLVED` stops it, and customer replies or reopen/open events resume it. Treat `AGENT_RESPONDED`, `ASSIGNED`, and `ESCALATED` as active-time events that usually do not pause the clock.
- First-response breach: active time from opening until the first `AGENT_RESPONDED`; if no response exists by cutoff, use active elapsed time at cutoff.
- Resolution active-clock breach: active time from opening until resolution; for active cases, use active elapsed time at cutoff.
- Severe active case: open or reopened at cutoff, priority included by the request, and beyond the resolution active-time threshold.
- Median active resolution hours: compute across eligible cases resolved at the cutoff; for an even count, average the two central values before rounding.
- Worst accounts: aggregate within eligible accounts and order by the request's severe-case count, breach count, and account-id tie-breakers.
- Risk policies usually compare severe-active and first-response breach rates to thresholds. Use the eligible case count as denominator unless the request says otherwise.

## Exact JSON output

Before finalizing:

1. Compare `answer.json` against every `required` key in the template.
2. Remove any property not allowed by `additionalProperties: false` or `additional_properties: false`.
3. Check numeric precision: rates and medians rounded to the requested decimals, currency to cents when requested.
4. Check arrays: exact min/max length, uniqueness, sort order, and object key names.
5. Check enum values exactly, including capitalization.
6. Re-run one final SQL query that returns the key counts/rates used in the answer, and compare it to the JSON values.

Do not include training-example answer values, reconstructed answer records, or commentary in the final output.
