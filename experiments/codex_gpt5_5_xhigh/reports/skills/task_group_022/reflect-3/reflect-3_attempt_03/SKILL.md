---
name: atlas-ops-analytics
description: Analyze Atlas Commerce Operations workplace tasks that require strict JSON answers from operational database records, including cutoff-based fulfillment, refunds, carrier corrections with audit records, warehouse productivity, and support-health reviews. Use when a task provides a prompt, JSON request payload, answer template, and environment access for Atlas-style schema/data-dictionary/query services or controlled correction transactions.
---

# Atlas Ops Analytics

## Core Workflow

1. Read the prompt, request payload, and answer template before querying data.
2. Treat the answer template as the output contract. Produce exactly the required keys, value types, rounding, and array ordering. Do not add commentary or extra fields.
3. Read schema and data-dictionary context from the task-provided environment access. Use the dictionary to identify source rows, canonical fields, snapshot fields, flags, and relationship keys.
4. Build the cohort first. Keep cohort filters separate from metric logic so denominators are auditable.
5. Query only the rows needed for the cohort and related events. If a response is paginated or marked truncated, fetch all pages before computing.
6. Deduplicate imported source events before metrics. For tables with `source_system`, `external_event_id`, and `ingested_at`, keep the latest ingestion per `(source_system, external_event_id)`, using the stable row id as a tie-breaker.
7. Compute final metrics locally or in SQL, but keep intermediate counts for validation: cohort count, event count before and after dedupe, final-state counts, breach counts, and array lengths.
8. Round only final reported values. Use exact decimal arithmetic for money and final ratios when possible.
9. Generate the final JSON programmatically from computed objects. Do not hand-copy long sorted arrays.

## Boundaries And Time

- Treat all timestamps as UTC unless the request explicitly says otherwise.
- Apply inclusive or exclusive boundaries exactly as stated in the request. If a request says an end timestamp is inclusive, use `<=`; if it says a due time is strictly before a cutoff, use `<`.
- Use business event timestamps for cutoff state unless the request explicitly says to use ingestion time or snapshot state.
- Exclude `accounts.is_internal = 1` and `accounts.is_test = 1` whenever the request describes production accounts, production orders, or production customer populations.
- Prefer append-only event history for cutoff state. Use snapshot columns such as `current_status` as cross-checks, not as the primary source, unless the request specifically defines the snapshot as authoritative.

## Query Discipline

- Avoid relying on default query limits. Add deterministic ordering and page with offset or keyset pagination until all rows are retrieved.
- Check `truncated` or equivalent response flags after every query that can return many rows.
- Keep raw and canonical columns distinct. Raw fields preserve source values; canonical fields drive operational analytics and approved corrections.
- Preserve stable ordering requirements exactly: sort IDs ascending; sort ranked objects by the specified metric before rounded display value, then by the stated tie-breaker.

## Fulfillment And Carrier Events

- For fulfillment cohorts, join orders to campaigns, accounts, warehouses, shipments, and carrier scans as required by the request.
- Define physical shipment membership from `shipments`, not carrier scans alone. An order with no physical shipment is incomplete when the request says so.
- Deduplicate carrier scans by source event before deriving shipment state.
- For final carrier status at a cutoff, use the latest effective canonical carrier scan at or before the cutoff for each shipment.
- For delivered timing, use the delivered canonical scan timestamp associated with the effective delivered event, then compare it to the shipment promise.
- For order-level completion, require every associated physical shipment to satisfy the delivery rule. Keep incomplete orders in rate denominators unless the request says otherwise.
- For severe exception logic, separate incomplete-late rules from completed-late rules. Apply late-delivered-shipment rules only to orders that meet the request's completion definition.

## Refund Reconciliation

- Deduplicate refund attempts by source event before identifying logical refunds.
- Treat settled logical refunds as distinct `refund_id` values after dedupe unless the request defines a different logical key.
- Restrict settled refund population by the requested account scope and service-date window.
- Count distinct eligible orders from orders with at least one effective settled logical refund.
- Count linked reversals in the requested close window for the scoped production account population. Subtract those reversal amounts from net refund exposure, even when a reversal links to a non-settled row; do not invent reason attribution when the linked settled refund is outside the reason population.
- Convert monetary minor units to major units, then to USD with the daily FX rate for each refund or reversal service date and row currency.
- For reason rankings, rank by unrounded effective net USD, then the normalized reason code ascending. Attribute reversal offsets to the linked settled refund reason only when the link is inside the settled-reason population.
- For leakage checks, compare order-level net refund USD after reversals to order gross USD using the FX date specified by the request. Check repeated unreversed settled refunds by normalized reason per order.
- Apply risk policies from the request after computing candidate rates and net exposure.

## Controlled Corrections

- Perform correction work only when the request explicitly asks for it and provides an approved correction policy.
- Identify the single source-row contradiction from raw/canonical fields and verify the current old value before mutation.
- Compute all pre-correction analysis from the unmodified state before applying the transaction.
- Use a guarded transaction for the minimal approved canonical field update and the audit insert. Guard the update with stable row id, entity id, raw value, and old canonical value.
- Do not change raw source fields, source identity fields, unrelated rows, or unrelated canonical fields.
- Verify the transaction result, the post-change canonical value, and the audit record. Report `APPLIED` only when the requested success rule is satisfied; otherwise report `NOT_APPLIED` with observed results.
- Compute post-correction analysis from a fresh read after the transaction.

## Warehouse Productivity

- Build the task cohort from `warehouse_tasks` using warehouse, work class, and task-created boundaries from the request.
- Deduplicate `warehouse_task_events` before using event counts, task state, units, or productive minutes.
- Derive task state at the cutoff from the latest deduped task event at or before the cutoff.
- Count completed tasks from final cutoff state when computing completion rate and team completion ranking.
- Sum completed production units and productive minutes from deduped `COMPLETED` events attached to eligible production tasks.
- Compute employee units per hour as completed units divided by completed-event productive minutes, multiplied by 60. Rank by unrounded units per hour descending, then employee id ascending.
- Count rework tasks according to the request's state definition, typically final cutoff state `REWORK` unless the request says any rework event qualifies.
- Identify delayed high-priority tasks from eligible HIGH or URGENT tasks with `due_at` strictly before the cutoff and not completed by the cutoff.
- Rank teams by unrounded completion rate ascending, then team id ascending.

## Support Health

- Build the account scope from production account flags, segment, and region before selecting cases.
- Deduplicate case events by source event before deriving state or clocks.
- Derive cutoff case state from deduped event history when lifecycle events are available. Treat header status as a cross-check unless the request says it is authoritative.
- Treat support active time as time while the case is actively awaiting support work. Pause the active clock during customer-waiting periods and resume on customer reply, reopen, or another active-state event.
- Stop active-time accumulation at resolution for resolved cases. For active cases, carry active time forward to the cutoff.
- Use the request's priority-specific thresholds for first response and resolution active-time breaches.
- Treat first response as the first explicit agent response event unless the request or data dictionary defines a broader response event set.
- Define severe active cases from active open/reopened cases at the cutoff, requested high-severity priorities, and active resolution-threshold breach.
- Rank worst accounts by severe active case count descending, active-clock breach count descending, then account id ascending.
- Compute medians from unrounded active resolution hours, averaging the two central values for even counts, then round the final reported median.

## Validation Checklist

- Confirm every required output field is populated and no extra key exists.
- Confirm denominators match the stated cohort and include incomplete or active cases when required.
- Confirm array lengths, uniqueness, and sort order match the template.
- Confirm final rounded values are rounded only after sorting and risk classification.
- Confirm mutation answers include fresh post-change verification and audit values.
- Avoid persisting scratch candidates, answer values, or analysis transcripts inside the skill package.
