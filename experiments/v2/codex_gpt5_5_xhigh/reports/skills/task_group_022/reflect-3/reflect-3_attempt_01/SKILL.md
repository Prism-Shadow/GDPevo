---
name: atlas-commerce-ops-analysis
description: Analyze Atlas Commerce Operations request payloads against operational database records and produce strict JSON answers. Use for fulfillment, refund, carrier quality, warehouse productivity, support health, cutoff-state analytics, FX/netting reconciliation, event-history SLA calculations, and controlled canonical-correction tasks where Codex must derive metrics from schema, data dictionary, request facts, and output templates.
---

# Atlas Commerce Ops Analysis

## Core Workflow

1. Read the prompt, request payload, and answer template before querying data.
2. Extract exact cohort filters, UTC windows, cutoff timestamps, inclusivity rules, status rules, rounding precision, array ordering, and tie-breakers.
3. Inspect schema and field descriptions, then map each requested metric to source tables and stable identifiers.
4. Build small validation queries first: cohort count, status distribution, event types, duplicate-source counts, and one or two row-level examples.
5. Prefer history/event tables for cutoff-consistent state. Treat denormalized `current_status` fields as snapshots that may lag unless the request explicitly says to use them.
6. Produce the final object only after independent checks confirm counts, rates, sorted arrays, and status classifications.

## Data Handling Rules

- Apply production exclusions when the request says production accounts or production population: exclude accounts where `is_internal = 1` or `is_test = 1`. For warehouse work, also honor `work_class = 'PRODUCTION'`.
- For imported append-only rows, de-duplicate retries by `(source_system, external_event_id)`, keeping the row with the latest `ingested_at`, then the greatest stable row id as a tie-breaker.
- For final state at a cutoff, filter events at or before the cutoff, then rank by event timestamp and stable event id. Use exact UTC boundaries; use `<` for “strictly before” and inclusive comparisons only when requested.
- Use numeric timestamp arithmetic for hour/day thresholds. Do not compare formatted date strings after applying date functions.
- Round only final reported values. Keep intermediate ratios, money, and rates unrounded for ordering and status-rule evaluation.
- Return arrays in the requested deterministic order. Use secondary tie-breakers exactly as stated, usually stable id ascending.

## Common Metric Patterns

### Fulfillment And Carrier State

- An order with no physical shipment is incomplete.
- A shipped order is complete only when every physical shipment has effective final canonical carrier status `DELIVERED` by the cutoff.
- On-time completion requires every delivered shipment to have delivery time no later than its own promise.
- Severe delay checks use numeric elapsed time against the request threshold; incomplete shipments with no relevant promise should not satisfy promise-based delay rules.
- For carrier quality corrections, identify the single raw/canonical contradiction in scope. Correct only the approved canonical field, preserve raw/source identity fields, insert the audit record, then verify affected business rows, audit rows, corrected value, and post-correction rollups before reporting `APPLIED`; otherwise report the actually observed `NOT_APPLIED` state.

### Refund Reconciliation

- Count logical refunds by stable `refund_id`, not physical retry rows.
- Convert money from minor units to major units, then join FX on the row’s service date and row currency.
- Compute net refund exposure as settled refund USD less in-scope linked reversal USD. Count linked reversal rows according to the request scope even when they are reported separately from settled logical refunds.
- Rank refund reasons by unrounded effective net USD descending, then normalized reason code ascending.
- For leakage review, evaluate net order refund USD after reversals against order gross USD valued at the relevant refund service-date FX rate, and separately flag orders with repeated unreversed settled logical refunds sharing the same normalized reason code.

### Warehouse Productivity

- Scope eligible tasks by warehouse, production work class, and created window.
- Determine completed tasks, rework state, and delayed high-priority tasks from de-duplicated task events as of the state cutoff.
- Completed production units and productive minutes should come from completed work events attached to eligible tasks.
- Employee productivity is total completed units divided by total productive minutes, multiplied by 60; order employees by the unrounded rate, then employee id.
- Lowest-performing teams rank by completion rate ascending, then team id.

### Support Health

- Scope support cases through account attributes and the case opened window; apply production exclusions.
- De-duplicate case events before computing lifecycle state or clocks.
- Model active case state from the event history at cutoff. `OPEN` and `REOPENED` are active states; customer replies and escalations generally leave the case active until a later resolved or waiting event changes state.
- First-response active time runs from opened event to first agent response. If no agent response exists, use active elapsed time at the cutoff.
- Resolution active time runs from opened event to resolution for resolved cases, or to the cutoff for active cases.
- Subtract customer-wait pauses from active clocks: pause from `WAITING_CUSTOMER` until the next `CUSTOMER_REPLIED`, or until the measurement endpoint if no reply occurs first.
- Severe active cases are active at cutoff, priority `URGENT` or `HIGH`, and beyond the priority resolution-active-time threshold.
- Median resolved active hours uses resolved eligible cases only; for an even count, average the two central unrounded values, then round the final median.

## Output Discipline

- Shape the answer exactly to the provided template: required keys only, correct scalar types, no commentary, and no extra fields.
- Use stable business identifiers exactly as stored.
- For status classifications, evaluate rules in priority order and leave all denominators exactly as specified.
- Before finalizing, run a quick schema check mentally or with a JSON validator if available: required fields present, arrays sorted, unique ids unique, numeric precision correct, and enum values exact.
