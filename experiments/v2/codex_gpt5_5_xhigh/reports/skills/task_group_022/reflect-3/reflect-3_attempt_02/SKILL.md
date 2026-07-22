---
name: atlas-ops-analytics
description: Solve Atlas Commerce Operations database tasks that ask for exact JSON operational analytics or controlled canonical corrections. Use when a prompt provides request facts, an answer template, authenticated schema/data-dictionary access, and SQL access for fulfillment scorecards, refund reconciliation, carrier scan quality corrections, warehouse productivity reviews, support health reviews, or similar cutoff-based operations reports.
---

# Atlas Ops Analytics

## Core Workflow

1. Read the prompt, request payload, and answer template before querying data.
2. Pull the schema and data dictionary from the provided workplace context. Use column names and dictionary warnings over assumptions.
3. Scope the population first, then compute facts from that scoped set. Apply every requested boundary exactly; inclusive windows use `between` or equivalent `>= start and <= end`, while "strictly before" means `< cutoff`.
4. Treat production scope as excluding `accounts.is_internal = 1` and `accounts.is_test = 1`. When the population is production accounts, also apply the requested segment, tier, and region filters. When the population is production orders or shipments, join through `orders.account_id` to apply the account production filter.
5. Prefer append-only event/source tables over denormalized `current_status` snapshots when the dictionary says snapshots may lag. Derive state as of the cutoff from effective source events at or before the cutoff.
6. Deduplicate imported source events before using them:
   - For carrier scans, case events, and warehouse task events, keep the latest `ingested_at` row for each `(source_system, external_event_id)` upstream event. Use a stable row id as a tie-breaker when needed.
   - For refund reconciliation, treat `refund_id` as the logical refund key and keep the latest ingested row per `refund_id`.
7. Use raw, unrounded values for ordering and thresholds. Round only final reported decimals, to the precision requested by the answer template or policy.
8. Sort all identifier arrays deterministically, usually ascending unless the request states another order. For ranked arrays, apply every tie-breaker in the request.
9. Return exactly the JSON object required by the answer template. Do not add commentary or additional fields.

## Fulfillment Scorecards

- Find eligible orders by campaign id and the campaign's official active window, then apply production-account exclusions.
- A physical shipment is a row in `shipments`. Orders with no physical shipment are incomplete.
- For shipment state at a cutoff, use the effective carrier scan history at or before the cutoff. After source dedupe, select the latest scan by `canonical_event_at`, with `scan_row_id` as a deterministic tie-breaker.
- A complete order has at least one shipment and every shipment's final effective canonical status is `DELIVERED`.
- An on-time complete order is complete and every shipment's effective delivery timestamp is at or before that shipment's `promised_delivery_at`.
- Severe exception logic is order-level:
  - incomplete with a shipment promise where the cutoff is more than 24 hours after the latest shipment promise, or
  - complete with any shipment delivered more than 24 hours after its promise.
- Regional on-time rates use the same denominator rule as the overall rate within each warehouse region. Rank worst regions by unrounded rate ascending, then region ascending.

## Refund Reconciliation

- Scope refunds through the associated order's account, applying requested account tier/segment/region and production filters.
- Use one effective row per `refund_id`, chosen by latest `ingested_at`.
- Count effective settled logical refunds from effective rows with status `SETTLED`.
- Count linked reversal rows from effective rows with status `REVERSED` in the requested scope.
- Convert every refund or reversal row independently to USD using `fx_rates.usd_per_unit` for that row's `service_date` and currency.
- Net refund USD is settled refund USD minus reversal USD.
- Reason rankings use normalized `reason_code`, net USD descending, then reason code ascending.
- For leakage candidates:
  - aggregate net refund USD per order after reversals,
  - value order gross in the order currency using the FX rate for the settled refund service date used in the comparison,
  - flag orders whose net refund USD exceeds gross order USD,
  - also flag orders with at least two unreversed settled logical refunds with the same normalized reason code.
- Apply risk policies using strict "below" comparisons exactly as written.

## Carrier Scan Corrections

- Identify raw/canonical contradictions inside the requested import batch, facility, and cutoff. Compare `raw_status` to `canonical_status`; do not alter raw fields, source identity fields, timestamps, or unrelated rows.
- For backlog cohorts marked as production shipments, join `shipments -> orders -> accounts` and apply production-account exclusions.
- Shipment membership usually comes from having an effective scan in the named batch at or before the cutoff.
- Backlog is based on each cohort shipment's effective final canonical carrier status at the cutoff.
- For approved minimal canonical corrections, update only the approved canonical field and append the required audit record in the same controlled transaction.
- Report `APPLIED` only after verifying exactly one business row changed, exactly one audit row was inserted, and a post-change query confirms the corrected canonical value. Otherwise report `NOT_APPLIED` and the observed post-state.
- In audit records for scan corrections, use the shipment as the business entity and the scan row as the source row.

## Warehouse Productivity

- Eligible tasks are `warehouse_tasks` rows matching the requested warehouse, `work_class = 'PRODUCTION'`, and the created-at window.
- Compute task state from deduped `warehouse_task_events` at or before the state cutoff.
- A task is completed if it has an effective `COMPLETED` event by the cutoff.
- Completed production units are the sum of `units` on effective `COMPLETED` events for eligible tasks by the cutoff.
- Employee units per hour is, per employee, `completed_units / completed_productive_minutes * 60`. Rank employees by this unrounded value descending, then employee id ascending; round only the reported top value.
- Rework task count is the count of eligible tasks with an effective `REWORK` event by the cutoff. Rework rate uses eligible task count as denominator.
- Delayed high-priority tasks are `HIGH` or `URGENT`, have `due_at` strictly before the cutoff, and are not completed by the cutoff.
- Lowest-performing team ranks by completion rate ascending, then team id ascending.
- Facility status rules use completion rate and rework rate calculated from the same eligible task denominator.

## Support Health

- Eligible cases come from `support_cases` joined to production accounts, with requested segment/region filters and the requested `support_cases.opened_at` window.
- Use `support_cases.opened_at` as the support clock start. Use deduped `case_events` to derive lifecycle timing and cutoff state.
- Treat `WAITING_CUSTOMER` as pausing support active time. Resume active time on `CUSTOMER_REPLIED`, `OPEN`, or `REOPENED`. `RESOLVED` stops active time. `ASSIGNED`, `AGENT_RESPONDED`, and `ESCALATED` do not by themselves change active/paused/resolved state.
- First-response breach uses active time from opening to the first `AGENT_RESPONDED` event. If no response exists, use active elapsed time at the cutoff.
- Resolution breach uses active time from opening to the first effective `RESOLVED` event for resolved cases, or active elapsed time at the cutoff for active cases.
- Open at cutoff includes cases whose event-derived state is `OPEN` or `REOPENED`. Reopened at cutoff is the subset whose event-derived state is `REOPENED`.
- Severe active cases are open or reopened at cutoff, priority `URGENT` or `HIGH`, and beyond that priority's active-time resolution threshold.
- Worst-account ranking uses severe active case count descending, active-clock breach count descending, then account id ascending.
- Median active resolution hours is computed across cases resolved at the cutoff. For even counts, average the two central values; round the final median to the requested precision.
