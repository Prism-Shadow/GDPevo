# Metric Patterns

These patterns are reusable starting points. The current request payload can override names, boundaries, orderings, and thresholds.

## Common Rules

- "Production" account/order scope normally excludes `accounts.is_internal = 1` and `accounts.is_test = 1`.
- Inclusive timestamp windows use `>= start_at` and `<= end_at`; strict wording such as "before cutoff" uses `< cutoff`.
- For ranked outputs, sort by the unrounded metric and only then by the stated stable tie-breaker.
- For "worst" outputs, verify whether the sort is ascending metric, descending problem count, or another request-specific rule.
- For array IDs, select distinct IDs after all business rules, then order exactly as requested.

## Fulfillment and Shipments

Useful tables: `orders`, `accounts`, `campaigns`, `warehouses`, `shipments`, `carrier_scans`.

1. Build eligible orders from campaign or account scope, production filters, and the campaign/request active order-created window.
2. Build effective shipment status by shipment as of the cutoff from canonical carrier scans when the request says "effectively delivered" or "by cutoff". If the request defines physical shipment existence, require at least one shipment row.
3. An order is complete only when every associated physical shipment has effective delivered status by the cutoff. Orders with no physical shipments are incomplete when the request says so.
4. On-time completion usually requires every shipment delivery time to be no later than its `promised_delivery_at`.
5. Severe exceptions commonly include incomplete orders more than the threshold after their latest shipment promise, plus completed orders with any shipment delivered more than the threshold after promise. Keep no-promise edge cases aligned with the payload.
6. Region rollups usually join `orders.warehouse_id` to `warehouses.region`.

## Refunds, Reversals, and Leakage

Useful tables: `refund_attempts`, `orders`, `accounts`, `fx_rates`.

1. Filter account tier, production population, and refund service-date window from the request.
2. Treat `SETTLED` refund attempts as effective logical refunds unless the request says otherwise. Exclude `FAILED` and `VOIDED`.
3. Treat `REVERSED` rows linked to an effective refund as linked reversals. Subtract reversal USD from settled refund USD for net exposure.
4. Count distinct logical refund IDs and distinct linked reversal rows according to the template wording.
5. Convert each refund/reversal row using `fx_rates` for that row's `service_date` and `currency`.
6. For gross-order comparisons, convert `orders.gross_amount_minor` using the request-specified comparison date and the order currency.
7. Leakage candidates often come from either net refund USD greater than gross order USD, or multiple unreversed settled logical refunds with the same normalized reason code. Apply `candidate_if_any` rules as OR conditions.
8. Rank refund reasons by net USD descending, then reason code ascending unless overridden.

## Carrier Quality Corrections

Useful tables: `carrier_scans`, `shipments`, `source_import_batches`, `correction_audit`.

1. Scope scans by import batch, warehouse/facility through `shipments`, and cutoff if provided.
2. Look for the single raw/canonical contradiction described by the request. For example, a raw terminal delivery value paired with a non-terminal canonical status may be the approved target, but do not assume the mapping without checking all contradictions in scope.
3. Compute pre-correction backlog from effective final carrier status by shipment at the cutoff. A shipment is backlog when the final effective canonical status is not delivered.
4. Apply only the approved canonical field change, insert exactly one audit row, and verify.
5. Compute post-correction backlog from the same query shape used for the pre-correction count.

## Warehouse Productivity

Useful tables: `warehouse_tasks`, `warehouse_task_events`, `employees`, `warehouses`.

1. Eligible tasks are usually scoped by warehouse, `work_class = 'PRODUCTION'`, and task `created_at` boundaries.
2. Derive completion by cutoff from task events when the request is cutoff-consistent. `COMPLETED` events carry completed units and productive minutes.
3. Units per hour is total completed units divided by total productive minutes times 60. Guard against zero productive minutes.
4. Count rework by eligible tasks with a `REWORK` event in scope, not by number of rework event rows, unless the request says rows/events.
5. Delayed high-priority work usually means `priority in ('HIGH','URGENT')`, `due_at` strictly before the cutoff, and not completed by the cutoff.
6. Lowest-performing teams generally rank by completion rate ascending, then `team_id` ascending.

## Support Health and Active-Time SLAs

Useful tables: `support_cases`, `case_events`, `accounts`.

1. Build eligible cases from account segment/region/production scope and case `opened_at` window.
2. Use case events, not just `support_cases.current_status`, for cutoff state and elapsed-time calculations.
3. The event vocabulary includes lifecycle events such as `OPENED`, `OPEN`, `REOPENED`, `WAITING_CUSTOMER`, `CUSTOMER_REPLIED`, `AGENT_RESPONDED`, `ASSIGNED`, `ESCALATED`, and `RESOLVED`. Confirm distinct values in the current environment.
4. Active support time usually excludes customer-wait intervals and includes time while the support team can act. Implement it as intervals between ordered case events, stopping at resolution or cutoff according to the request.
5. For first-response breaches, use active time from opening until first agent response; for unresponded cases, use active elapsed time at the cutoff.
6. For resolution breaches, use active time until resolution for resolved cases and active elapsed time at cutoff for active cases.
7. Open-at-cutoff usually includes `OPEN` and `REOPENED`; severe active cases usually combine active-at-cutoff, urgent/high priority, and active resolution threshold breach.
8. Medians over resolved-case active resolution hours should sort all eligible resolved durations; for even counts, average the two central values before final rounding.
