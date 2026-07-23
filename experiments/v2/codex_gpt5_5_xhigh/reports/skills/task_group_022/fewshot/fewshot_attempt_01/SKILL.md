---
name: atlas-commerce-operations
description: Use when solving Atlas Commerce Operations workplace tasks that provide a prompt, request payload JSON, and answer_template.json, and require authenticated schema/data-dictionary/SQL API use to produce exact answer.json metrics, reconciliations, support/warehouse/fulfillment scorecards, or approved canonical corrections with correction_audit records.
---

# Atlas Commerce Operations

## Required Workflow

1. Read the task prompt and every file under `input/payloads/` before querying data.
2. Treat `answer_template.json` as the output contract: preserve required keys, value types, array ordering rules, rounding precision, enum policies, and `additionalProperties: false`.
3. Read `environment_access.md` for the base URL, token, and allowed endpoints. Fetch `/api/schema` and `/api/data-dictionary` at the start of each task; table availability and field meanings are part of the runtime contract.
4. Use `POST /api/sql` for read-only analysis. Use `POST /api/sql/transaction` only when the prompt explicitly requests an approved correction.
5. Compute from the database each time. Do not reuse answer values from examples or prior runs.
6. Write only the final JSON object to `answer.json`; include no markdown, explanation, comments, or extra fields.

Useful API pattern:

```bash
curl -sS \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql":"WITH ... SELECT ...","params":[]}' \
  "$BASE_URL/api/sql"
```

Prefer parameterized SQL through the `params` array for user/payload values.

## Database Orientation

Core tables:

- `accounts`: production filtering and account scope (`segment`, `tier`, `region`, `is_internal`, `is_test`).
- `campaigns`, `orders`, `order_lines`, `shipments`, `carrier_scans`: fulfillment, delivery, and carrier-status analysis.
- `refund_attempts`, `payment_events`, `fx_rates`: refund/reversal settlement and USD conversion.
- `warehouse_tasks`, `warehouse_task_events`, `employees`, `warehouses`: facility productivity and task state.
- `support_cases`, `case_events`: support SLA and lifecycle analysis.
- `correction_audit`: append-only audit records for controlled canonical corrections.

Stored timestamps are ISO-8601 UTC text ending in `Z`; direct string comparison is valid for same-format timestamps. Use exact boundary language from the request: inclusive windows use `>=` and `<=`; strict "before cutoff" uses `<`. Calendar service dates are `YYYY-MM-DD`.

For production populations, join to `accounts` when the entity has an account path and exclude internal or test accounts unless the request says otherwise:

```sql
a.is_internal = 0 AND a.is_test = 0
```

For append-only or imported source rows with retry identity (`source_system`, `external_event_id`, `ingested_at`), deduplicate retries unless the request asks for raw imports. Keep the latest `ingested_at` for each source identity. For historical state at a cutoff, filter events at or before the cutoff, then pick the last effective event by event timestamp plus stable row id. Avoid using denormalized `current_status` for a historical cutoff when event history is available.

## Shared Calculation Rules

- Build SQL with CTEs and inspect intermediate counts before composing the final answer.
- Count distinct business entities at the grain named by the template: orders, logical refunds, linked reversals, tasks, cases, accounts, or shipments.
- Sort using unrounded values, then round only the final reported numeric fields.
- Use `ROUND(value, n)` for final display, but keep raw values in ordering CTEs.
- For rates, keep incomplete or breached entities in the denominator exactly as the request defines.
- For policy classifications, evaluate rules in the order given by the payload and use strict comparisons where the text says "below" or "greater than".
- For median values in SQLite, sort the metric and average the two center rows for even counts:

```sql
WITH ranked AS (
  SELECT value,
         ROW_NUMBER() OVER (ORDER BY value) AS rn,
         COUNT(*) OVER () AS n
  FROM metric_values
)
SELECT AVG(value) FROM ranked
WHERE rn IN ((n + 1) / 2, (n + 2) / 2);
```

## Fulfillment Scorecards

Use these patterns for campaign/order fulfillment tasks:

- Cohort: production orders matching the requested campaign and created inside the campaign/request active window. Join `campaigns`, `orders`, `accounts`, `warehouses`, `shipments`, and `carrier_scans` as needed.
- Physical shipments: rows in `shipments`; an order with no shipment is incomplete.
- Shipment state by cutoff: use effective carrier scans at or before the cutoff, usually the latest canonical carrier scan per shipment by `canonical_event_at` and `scan_row_id`.
- Complete order: the order has at least one shipment and every associated shipment is effectively `DELIVERED` by the cutoff.
- On-time complete order: every associated shipment is delivered no later than that shipment's `promised_delivery_at`.
- Severe exception: follow the request text exactly. Common forms are incomplete orders where the cutoff is more than 24 hours after the latest shipment promise, or completed orders with any shipment delivered more than 24 hours after its promise.
- Regional rollups: group by `warehouses.region`; rank worst regions by unrounded rate ascending, then region ascending.
- Exception ID arrays: return distinct order ids sorted ascending.

Check denominators by verifying:

```text
eligible_count = complete_count + incomplete_count
```

## Refund Reconciliations

Use these patterns for settlement/refund close tasks:

- Scope orders through `orders` and `accounts`; apply production, tier, segment, region, and service-date filters from the payload.
- Treat `refund_attempts.refund_id` as the logical refund id. Count distinct logical refunds after applying the effective settlement policy.
- Effective settled refunds are rows/logical refunds with settled status in the requested service-date window. Linked reversals are refund rows with reversal status and `linked_refund_id` pointing to the original logical refund.
- Convert money row by row with `fx_rates` on the row `service_date` and `currency`: `amount_minor / 100.0 * usd_per_unit`.
- Net refund USD is settled refund USD minus effective linked reversal USD.
- Reason-code rankings use net USD by normalized `reason_code`, ordered by net USD descending then reason code ascending.
- Leakage candidates commonly include orders where net refund USD exceeds order gross USD at the comparison FX rate, or where the order has repeated unreversed settled logical refunds with the same normalized reason code. Apply the exact candidate definition and output ordering from the request.

Validate that reversal counts and net dollars are at the same logical grain used in the request; do not double-count retry attempts.

## Carrier Quality Corrections

Use this workflow only for prompts that explicitly authorize a correction:

1. Read the approved correction block from the payload (`audit_id`, `correction_key`, `corrected_at`, `actor`, `reason_code`, and scope).
2. Identify the single target contradiction using the requested batch, warehouse, cutoff, and raw/canonical status policy. Preserve raw source values and source identity fields.
3. Compute the requested pre-correction metric before mutating data.
4. Submit one transaction containing a guarded business-row update and one `correction_audit` insert. Set `expected_total_changes` to the exact total requested by the success rule.
5. Guard the update by primary key, old canonical value, and any scope fields needed to prevent accidental broad changes.
6. Insert the audit record with the request-provided audit metadata, the business entity id, source row id, corrected field name, old value, and new value.
7. Re-query the corrected row, `/api/correction-audit`, and the requested post-correction metric.
8. Report `APPLIED` only when the success rule is fully satisfied; otherwise report `NOT_APPLIED` with the observed counts.

Typical carrier-scan update shape:

```sql
UPDATE carrier_scans
SET canonical_status = ?,
    corrected_at = ?,
    correction_reason = ?
WHERE scan_row_id = ?
  AND canonical_status = ?;
```

Use the transaction endpoint, not separate mutation calls, so the audit row and business change commit together.

## Warehouse Productivity

Use these patterns for facility production reviews:

- Eligible tasks: `warehouse_tasks` in the requested warehouse, `work_class = 'PRODUCTION'`, and `created_at` within the requested window.
- Completion at cutoff: a task is completed by cutoff when it has an effective `COMPLETED` event at or before the cutoff, or the request explicitly permits a status snapshot.
- Completed units and productive minutes come from completed `warehouse_task_events` at or before the cutoff.
- Employee units per hour: sum completed units divided by sum productive minutes, multiplied by 60. Rank by raw rate descending, then `employee_id` ascending.
- Rework task count: count distinct eligible tasks with an effective `REWORK` event or request-defined rework state by cutoff.
- Delayed high-priority tasks: priority in the requested high-priority set, `due_at` strictly before the state cutoff, and not completed by the cutoff.
- Lowest-performing team: join employees by `assigned_employee_id`, compute completion rate by `team_id`, rank by completion rate ascending then team id ascending.
- Facility status: evaluate the request's completion-rate and rework-rate thresholds in order.

Cross-check that completed task count never exceeds eligible task count and that completed units only come from eligible tasks.

## Support Health

Use these patterns for support SLA reviews:

- Eligible cases: `support_cases` joined to `accounts`; apply production account filters plus requested segment, regions, and opened window.
- Case state at cutoff: derive from effective `case_events` at or before the cutoff. Open/active states commonly include `OPEN` and `REOPENED`; resolved cases stop at `RESOLVED`.
- Support active clock: accumulate intervals when the case is active for support work. `OPENED`, `OPEN`, `REOPENED`, and `CUSTOMER_REPLIED` start or resume active time; `WAITING_CUSTOMER` pauses it; `RESOLVED` stops it. `AGENT_RESPONDED`, `ASSIGNED`, and `ESCALATED` usually do not pause the resolution clock unless the request says otherwise.
- First-response breach: compare active time from opening to first `AGENT_RESPONDED`; for unresponded cases, use active elapsed time at the cutoff.
- Resolution breach: compare active time to `RESOLVED`; for active cases, use active elapsed time at the cutoff.
- Severe active case: active at cutoff, priority in the requested severe set, and beyond the priority resolution-active-time threshold.
- Worst accounts: aggregate severe active cases and active-clock breaches by account; order exactly as the payload specifies.
- Resolved-case median: compute median active resolution hours across eligible cases resolved at or before the cutoff, then round for output.
- Risk: divide rates by eligible case count unless the payload names a different denominator; apply strict "below" thresholds.

Inspect a few case timelines with `GROUP_CONCAT(event_type || '@' || event_at, ' | ')` when SLA counts look surprising.

## Final Validation

Before finishing:

- Re-read `answer_template.json` and compare every required field, type, enum, numeric precision, and array uniqueness/order rule.
- Run at least one independent SQL cross-check for each high-risk value: denominators, top/worst rankings, exception lists, and post-correction verification.
- Parse the final file as JSON, for example `jq empty answer.json`.
- Ensure analytical prompts made no mutations. For correction prompts, ensure only approved canonical fields and `correction_audit` changed.
