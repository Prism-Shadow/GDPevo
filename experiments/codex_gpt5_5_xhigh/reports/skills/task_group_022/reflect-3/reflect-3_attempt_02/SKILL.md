---
name: atlas-commerce-ops-analysis
description: Use for Atlas Commerce Operations tasks that require producing exact JSON analytics or applying approved minimal data-quality corrections from workplace schema, dictionary, SQL data, and request payloads.
---

# Atlas Commerce Ops Analysis

## Core Workflow

1. Read the user prompt, request payload, and answer schema before querying data.
2. Treat the answer schema as the contract. Return exactly the required JSON keys, types, rounding, array ordering, and no commentary.
3. Load schema and field definitions from the available workplace context, then identify the smallest table set needed for the request.
4. Build the cohort first. Apply business scope exactly: account production exclusions, segment/tier/region filters, warehouse/campaign/task/case windows, and inclusive or strict timestamp boundaries as stated.
5. Prefer canonical and event-derived operational truth over convenience snapshot columns when the request says cutoff, effective, final, current-at-cutoff, or corrected. Snapshot status fields can lag event history.
6. For imported source rows with `source_system`, `external_event_id`, and `ingested_at`, de-duplicate before analysis: keep the row with the latest `ingested_at`, breaking ties by the stable row id.
7. For final state at a cutoff, use effective rows with business event time at or before the cutoff, then order by event time and stable row id. Use the last state-changing row unless the request defines a different effective event.
8. If the SQL service rejects a large CTE, partitioned window, or complex join, query scoped rows in pages and aggregate locally. Always check truncation or page until complete.
9. Round only final reported values. Keep intermediate rates, currency amounts, and durations unrounded for ranking and status rules.

## Production Scope

When a request says production accounts or production customers, exclude account rows with `is_internal = 1` or `is_test = 1`. Combine this with any requested `segment`, `tier`, or `region` filter.

When a request says production tasks, use `work_class = 'PRODUCTION'`. Do not include training work unless explicitly requested.

For order or shipment production cohorts, join through the account on the order and apply the same production-account exclusions unless the request provides a more specific rule.

## Effective Event Patterns

Use these patterns when the request does not override them:

- Carrier state: de-duplicate `carrier_scans`, then use `canonical_status` and `canonical_event_at`. A shipment's final carrier state at a cutoff is the last effective canonical scan at or before the cutoff.
- Warehouse task state: de-duplicate `warehouse_task_events`. Completed tasks are tasks with an effective `COMPLETED` event by the cutoff. Rework tasks are tasks with an effective `REWORK` event by the cutoff.
- Support case state: de-duplicate `case_events`. Treat `OPENED`, `OPEN`, `REOPENED`, and `CUSTOMER_REPLIED` as active support-clock states; `WAITING_CUSTOMER` pauses the active clock; `RESOLVED` stops it. Use the event stream for cutoff state and durations.

## Fulfillment Scorecards

For campaign fulfillment metrics:

- Build eligible orders from the campaign id and the campaign's active window, then apply production exclusions.
- Join physical shipments by order. An order with no physical shipment is incomplete.
- A complete order requires every associated shipment's final effective carrier state at the cutoff to be `DELIVERED`.
- An on-time complete order requires every completed shipment's effective delivery event time to be no later than its `promised_delivery_at`.
- Regional rates use the warehouse region assigned to the order. Rank regions by unrounded rate, then region label.
- Severe exceptions usually combine incomplete orders past the latest shipment promise plus a grace interval and completed orders with any shipment delivered beyond the same grace interval.

## Refund Reconciliation

For settled refund analysis:

- Scope refund rows by account production filters, account tier or segment, and refund or reversal service-date window.
- De-duplicate refund attempts by source event before classifying.
- Effective settled logical refunds are distinct `refund_id` values whose effective row has `status = 'SETTLED'` and no `linked_refund_id`.
- Effective linked reversals are distinct effective rows with `status = 'REVERSED'` and a non-null `linked_refund_id`, within the requested scope.
- Convert money as `(amount_minor / 100) * usd_per_unit` using the row's service date and currency. Subtract reversal USD from net refund USD.
- Normalize reason codes consistently, usually by uppercasing the stored `reason_code`.
- For reason rankings, aggregate net USD by normalized reason and rank by unrounded net amount descending, then reason code ascending.
- Leakage candidates are drawn from eligible refunded orders. Compare net refund USD after linked reversals to the order gross converted to USD at the relevant settled refund service date. Also flag orders with at least two unreversed settled logical refunds sharing the same normalized reason code.

## Warehouse Productivity

For warehouse weekly or cutoff productivity:

- Eligible tasks are production tasks in the requested warehouse and created window.
- Completed production units are the sum of effective `COMPLETED` event units for eligible tasks completed by the cutoff.
- Employee units per hour is completed units divided by productive minutes on those completed event rows, multiplied by 60. Rank employees by unrounded units per hour descending, then employee id ascending.
- Completion rate is completed eligible task count divided by eligible task count.
- Rework rate is effective rework task count divided by eligible task count.
- Delayed high-priority tasks are `HIGH` or `URGENT` tasks with `due_at` strictly before the cutoff and no effective completion by the cutoff. Sort task ids ascending.
- Team completion rates use the assigned employee's team for each task. Rank teams by unrounded completion rate ascending, then team id ascending.

## Support Health Reviews

For support SLA reviews:

- Build eligible cases from production account filters, segment/region scope, and case-opened window.
- De-duplicate case events before computing state, response, or resolution metrics.
- First-response active time runs from opening until the first qualifying agent response event. If no response exists by the cutoff, use active elapsed time at the cutoff.
- Resolution active time runs until the effective resolution event for resolved cases. For active cases, use active elapsed time at the cutoff.
- Active severe cases are open or reopened at the cutoff, priority `URGENT` or `HIGH`, and beyond the priority resolution active-time threshold.
- Worst-account rankings use severe active case count descending, then active-clock breach count descending, then account id ascending.
- Median active resolution hours is computed only across eligible cases resolved by the cutoff. For even counts, average the two central unrounded durations, then round the final median.

## Approved Corrections

For controlled data-quality corrections:

1. Identify the exact source row from the requested batch, entity scope, raw value, canonical value, and cutoff context.
2. Compute and save the pre-correction metric before mutating data.
3. Apply only the approved canonical field change. Do not alter raw source values, source identity fields, unrelated rows, or broader derived fields.
4. Use a guarded transaction that updates exactly one business row and inserts exactly one audit row with the provided audit identifiers, old/new values, reason, actor, and correction timestamp.
5. Verify the corrected canonical value, audit record, post-correction metric, and mutation counts before writing the answer.
6. Report `APPLIED` only when the mutation counts and post-change verification satisfy the request's success rule; otherwise report the observed result.

## Output Discipline

- Validate every required key against the answer schema before finishing.
- Sort identifier arrays exactly as requested, usually ascending by id.
- Rank lists using unrounded values; round only the values written to JSON.
- Use JSON numbers for numeric fields, not strings.
- Write only the final JSON object when the task asks for an answer file.
