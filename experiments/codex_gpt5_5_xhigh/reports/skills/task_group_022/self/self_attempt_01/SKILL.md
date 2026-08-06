---
name: atlas-commerce-ops
description: Solve Atlas Commerce Operations database tasks that require cutoff-based operational analytics, source-stream reconciliation, or controlled canonical data corrections through the Atlas API. Use when prompts provide JSON request payloads and answer templates for fulfillment, refunds, carrier quality, warehouse productivity, support health, inventory, orders, payments, shipments, or similar Atlas Commerce workflows.
---

# Atlas Commerce Ops

Use this skill to turn an Atlas Commerce Operations request payload plus answer template into an exact `answer.json`.

## Required Workflow

1. Read the prompt, every request payload, and the answer template before querying.
2. If `environment_access.md` is present, use only its base URL, auth token, and allowed endpoints for network access.
3. Fetch `/api/schema` and `/api/data-dictionary` at the start of each task. Treat the live schema as authoritative.
4. Use `POST /api/sql` only for analytical `SELECT` or `WITH` queries unless the request explicitly asks for an approved correction.
5. Use parameterized constants from the request payload. Do not hard-code values from prior tasks.
6. Build the final object to match the answer template exactly: required keys only, correct nesting, exact enum strings, no extra commentary.
7. Write only the JSON document to `answer.json`.

## Global Rules

- Respect UTC timestamp boundaries exactly. Apply inclusive, exclusive, and strict-before wording from the request literally.
- Round only final reported values. Keep unrounded values for ranking and status/risk decisions.
- Use requested tie-breaks exactly, commonly by ascending stable ID or label after descending metric order.
- Treat "production" accounts or orders as excluding `accounts.is_internal = 1` and `accounts.is_test = 1` when the request scopes to production populations.
- Prefer append-only event/source tables over denormalized `current_status` fields for as-of, cutoff, effective, or lifecycle metrics. Dictionary text says current snapshots may lag.
- Count distinct business IDs at the requested grain: orders, logical refunds, linked reversals, shipments, tasks, cases, accounts, or rows.
- Use `NULLIF(denominator, 0)` in SQL ratios and decide how the template expects zero-population outputs before finalizing.
- Validate array uniqueness and sort order explicitly before writing the answer.

## Effective Source Rows

Several Atlas tables contain source retries using `source_system`, `external_event_id`, and `ingested_at`. For metrics over imported observations or events, create effective CTEs that keep one row per source identity unless the request says otherwise:

```sql
WITH effective_events AS (
  SELECT *
  FROM (
    SELECT e.*,
           ROW_NUMBER() OVER (
             PARTITION BY source_system, external_event_id
             ORDER BY ingested_at DESC, <stable_row_id> DESC
           ) AS rn
    FROM <event_table> e
  )
  WHERE rn = 1
)
```

Use the table's stable row ID as the final tie-breaker, such as `scan_row_id`, `refund_row_id`, `case_event_id`, `task_event_id`, `event_id`, `payment_event_id`, or `movement_row_id`.

For named import-batch membership, be explicit about scope: dedupe rows within the named batch for membership tests, then use all effective rows at or before the cutoff when computing final entity state unless the request limits final state to the batch.

## Common SQL Patterns

- Latest state at cutoff: filter effective events to `event_at <= :cutoff`, rank by event time descending and stable row ID descending, then take `rn = 1`.
- Physical shipment state: use effective `carrier_scans` canonical statuses and canonical event timestamps, not raw fields, unless the request is asking for a raw/canonical contradiction.
- Money: convert minor units to currency units with `amount_minor / 100.0`, join `fx_rates` by service date and currency, and multiply by `usd_per_unit`.
- Median: sort unrounded values, average the two central values for an even count, then round to requested precision.
- Status/risk rules: evaluate from most favorable to least only when the request defines ordered policies that way; otherwise implement the stated boolean conditions literally.

## Fulfillment Scorecards

Use this pattern for campaign/order/shipment cutoff reports:

- Eligible orders usually join `orders` to `accounts`, `campaigns`, and `warehouses`; filter the named campaign, the campaign active window or requested order window, and production accounts.
- A complete order must have at least one physical shipment and every shipment must be effectively delivered by the cutoff.
- Delivery time is the effective canonical `DELIVERED` scan timestamp. An order with no shipment, no effective delivered scan, or any non-delivered latest shipment state at cutoff is incomplete.
- On-time completion requires every shipment delivery timestamp to be at or before that shipment's `promised_delivery_at`.
- Severe shipment/order exceptions usually compare cutoff or actual delivery time against the latest shipment promise plus the request's grace window.
- Regional rollups use the warehouse region assigned to the order and keep incomplete orders in rate denominators when requested.

## Refund Reconciliation

Use this pattern for refund settlement and leakage reports:

- Scope eligible orders through production accounts and account attributes such as tier, segment, or region.
- Treat a logical refund as the business `refund_id`; dedupe source rows before classifying status.
- Effective settled refunds are normally `status = 'SETTLED'` within the requested service-date window.
- Linked reversals are normally `status = 'REVERSED'` rows with `linked_refund_id` pointing at a settled logical refund. Subtract linked reversal USD from settled refund USD.
- Normalize reason codes consistently, usually `UPPER(TRIM(reason_code))`, before grouping or detecting repeats.
- Rank reasons by effective net USD and the request's tie-break.
- For leakage candidates, compute order-level net refund exposure after reversals, compare to order gross converted to USD using the request's FX basis, and also check repeat unreversed settled logical refunds with the same normalized reason.

## Carrier Quality Corrections

Use this pattern only when the request explicitly asks for a controlled correction:

- Identify the single source row whose raw and canonical carrier status contradict the approved policy within the requested batch, warehouse, entity, and cutoff.
- Preserve raw fields, source identity fields, unrelated rows, and unrelated canonical columns.
- Before mutating, run read-only verification queries for the target row, current canonical value, intended new value, affected shipment, pre-correction backlog, and absence or presence of prior audit rows.
- Use `POST /api/sql/transaction` with guarded statements and exact `expected_total_changes`. The normal minimal carrier correction is one guarded `UPDATE carrier_scans` plus one `INSERT correction_audit`.
- Guard the update by stable source row ID and old canonical value. Populate audit values exactly from the request: audit ID, correction key, entity type, entity ID, source row ID, field name, old value, new value, reason code, corrected timestamp, and actor.
- After the transaction, verify the business row, audit row, and post-correction metric. Report `APPLIED` only if the request's success rule is satisfied; otherwise report `NOT_APPLIED` with observed counts.

## Warehouse Productivity

Use this pattern for warehouse task health reports:

- Eligible tasks come from `warehouse_tasks`, usually filtered by warehouse, `work_class = 'PRODUCTION'`, and the requested created-at window.
- Use effective `warehouse_task_events` at or before the state cutoff to determine completion, rework, units, and productive minutes.
- A completed task has a `COMPLETED` event by cutoff. Sum completed units and productive minutes from completion events, not planned units.
- Units per hour is completed units divided by productive minutes times 60. Rank employees by unrounded units per hour, then employee ID.
- Rework task count is distinct eligible tasks with a `REWORK` event by cutoff unless the request defines a different source.
- Delayed high-priority tasks use `priority IN ('HIGH','URGENT')`, `due_at < cutoff` when the request says strictly before, and no completion by cutoff.
- Team completion rates join assigned employees to `employees.team_id`; rank lowest teams by unrounded completion rate and team ID.

## Support Health

Use this pattern for support SLA and active-case reports:

- Eligible cases come from `support_cases` joined to production `accounts`, filtered by segment, region, and opened-at window.
- Deduplicate `case_events` and build a timeline ordered by `event_at`, then stable row ID.
- Active support-clock intervals usually start or resume at `OPENED`, `OPEN`, `REOPENED`, or `CUSTOMER_REPLIED`; pause or stop at `WAITING_CUSTOMER` or `RESOLVED`. Treat `ASSIGNED`, `ESCALATED`, and `AGENT_RESPONDED` as events inside the active interval unless the request defines state differently.
- First-response breach uses active time from opening until the first `AGENT_RESPONDED`; for unresponded cases, use active elapsed time through the cutoff.
- Resolution active-clock breach uses active time to `RESOLVED`; for active cases, use active elapsed time through the cutoff.
- Open-at-cutoff counts cases whose as-of state is open or reopened. Reopened-at-cutoff is the subset whose active state came from a reopen path.
- Severe active cases combine active-at-cutoff, requested priorities, and resolution active-time threshold breach.
- Worst accounts rank by severe active case count, then active-clock breach count, then account ID. Resolved-case medians use only eligible cases resolved by the cutoff.

## Final Checks

Before writing `answer.json`:

- Re-run independent count queries for denominators and numerator subsets.
- Confirm mutually related fields add up, such as complete plus incomplete counts when the template implies a partition.
- Confirm rates and status/risk labels were decided from unrounded values.
- Confirm correction tasks have both pre- and post-change verification and audit evidence.
- Validate the final JSON parses and contains no fields outside the template.
