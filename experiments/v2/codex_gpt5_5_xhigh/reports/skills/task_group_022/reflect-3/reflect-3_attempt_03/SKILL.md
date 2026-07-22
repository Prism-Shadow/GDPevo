---
name: skill
description: Analyze scoped Atlas Commerce Operations requests that require database-backed operational metrics, cutoff-based state reconstruction, reconciliation, or controlled canonical corrections. Use when the user provides a request payload, answer schema/template, and authenticated Atlas Commerce schema/query services for fulfillment, refunds, carrier quality, warehouse productivity, support health, or similar operational scorecards.
---

# Atlas Commerce Operations Analysis

## Core Workflow

1. Read the prompt, request payload, and answer template before querying data. Treat the template as the output contract: exact keys only, correct scalar types, arrays ordered exactly as specified, and no commentary in machine-consumed answers.
2. Load the provided schema and data dictionary. Identify each table's row grain, source identity fields, timestamp columns, status columns, and relationship keys before writing SQL.
3. Translate every request phrase into explicit filters: account segment/tier/region, production exclusions, campaign or warehouse scope, service-date windows, opened/created windows, cutoff timestamps, inclusive versus strict boundaries, and required tie-breakers.
4. Prefer append-only event/source tables for cutoff state and metrics. Treat denormalized `current_status` columns as convenience snapshots that may lag unless the request explicitly makes them authoritative.
5. Round only final reported values. Use unrounded values for rankings and status-policy thresholds.

## Effective Rows

Many Atlas source tables contain retried imports. Build an "effective rows" layer before computing metrics:

- Deduplicate source rows by `(source_system, external_event_id)`.
- Keep the row with the latest `ingested_at`; break ties with the stable row identifier for that table.
- For final state at a cutoff, choose the latest effective event at or before the cutoff by event timestamp, then stable row identifier.
- Apply this pattern to carrier scans, refund attempts, warehouse task events, support case events, order events, and other source-imported facts.

If a large all-in-one SQL statement is rejected or hard to validate, decompose it into smaller CTEs or page source rows into a local in-memory calculation. Always check whether query responses are truncated and paginate with deterministic ordering when needed.

## Production Scope

When a request says production accounts, production orders, or production shipments, exclude internal and test accounts by joining through the account owning the record. Preserve the request's other population filters, such as account tier, segment, region, campaign, warehouse, or work class.

## Fulfillment Scorecards

For campaign fulfillment metrics:

- Select eligible orders by campaign ID and the campaign's active window, then apply production-account exclusions.
- An order is complete only if it has at least one physical shipment and every shipment's final effective carrier status at the cutoff is `DELIVERED`.
- On-time completion requires every delivered shipment's delivery event time to be no later than that shipment's promise.
- Incomplete orders remain in the denominator for completion-rate metrics.
- Severe exceptions usually combine incomplete orders past their latest shipment promise plus a grace period with completed orders containing shipment deliveries beyond the allowed lateness threshold.
- Region rollups use the order's assigned warehouse region unless the request says otherwise.

## Refund Reconciliation

For refund settlement requests:

- Build effective refund rows first, then count settled logical refunds at the `refund_id` grain.
- Scope settled refunds by the request's account population and refund service-date window.
- Count effective linked reversals from `REVERSED` refund rows in the same account/date scope; subtract reversal USD value from settlement exposure.
- Convert monetary minor units with the FX rate for each refund or reversal service date and row currency.
- For gross-overage leakage checks, convert the order gross using the settled refund service date and the order currency.
- Attribute reason-code rankings by effective net USD, subtracting reversals from the appropriate reason when a linkage resolves; otherwise use the reversal row's normalized reason code.
- For repeated-refund leakage, count unreversed logical refund IDs, not duplicate imported source rows.

## Carrier Quality Corrections

For controlled carrier correction requests:

- Identify the single raw/canonical contradiction inside the requested batch, warehouse, entity population, and cutoff. Compare exact canonical status meaning, not loose substring matches.
- Compute pre-correction backlog from scoped shipments whose final effective carrier status at the cutoff is not `DELIVERED`.
- Apply only the approved canonical field change. Do not alter raw source values, source identity fields, unrelated rows, or shipment snapshots unless explicitly approved.
- Insert the required audit record in the same controlled transaction as the business-row update.
- Report `APPLIED` only after verifying exactly one business row changed, exactly one audit row was inserted, and a post-change query confirms the corrected canonical value. Otherwise report `NOT_APPLIED` with observed row counts and observed post-change metrics.

## Warehouse Productivity

For warehouse production reviews:

- Scope tasks by warehouse, `PRODUCTION` work class, and the exact created-at window.
- Use effective task events at or before the state cutoff for completion, units, productive minutes, rework, and delayed-work determinations.
- Completed production units come from completed task events, not planned units.
- Employee productivity is total completed units divided by total productive minutes attached to completed units, multiplied by 60.
- Delayed high-priority tasks are `HIGH` or `URGENT` tasks with `due_at` strictly before the cutoff and no completed event by the cutoff.
- Team completion rates use assigned employee team membership and completed eligible task count divided by eligible task count; rank by unrounded rate, then team ID.

## Support Health

For support-health reviews:

- Scope cases by production account filters and opened-at window.
- Reconstruct case state from effective case events at or before the cutoff. Treat `OPEN`, `OPENED`, `REOPENED`, `ASSIGNED`, `AGENT_RESPONDED`, `CUSTOMER_REPLIED`, and `ESCALATED` histories as active unless a later event pauses or resolves the case; treat `REOPENED` as the reopened active subset when it is the current effective state.
- Compute support active time as elapsed time while the case is support-active. Pause the clock during `WAITING_CUSTOMER`; resume on `CUSTOMER_REPLIED`, `OPEN`, or `REOPENED`; stop on `RESOLVED`.
- First-response breaches use active time to the first agent response; unresponded cases use active elapsed time at the cutoff.
- Resolution breaches use active time to resolution for resolved cases and active elapsed time at the cutoff for active cases.
- Severe active cases are active at the cutoff, priority `URGENT` or `HIGH`, and beyond the priority resolution active-time threshold.
- Worst-account rankings should include all eligible accounts as candidates and apply the request's ordered tie-breakers.
- Median active resolution hours uses resolved eligible cases only; for an even count, average the two central unrounded active-time values before final rounding.
