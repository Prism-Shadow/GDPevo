---
name: atlas-commerce-ops
description: Analyze or correct Atlas Commerce Operations workplace data through the authenticated task service. Use when a task provides prompt and payload files that define business scope, output JSON schema, cutoff windows, operational metrics, refund or fulfillment reconciliation, support health, warehouse productivity, or an approved minimal canonical data correction.
---

# Atlas Commerce Operations

Use this skill to turn request payloads into exact JSON answers from the Atlas Commerce Operations service.

## Core Workflow

1. Read the task prompt and every file under `input/payloads/` before querying data.
2. Read the environment access file in the workspace and use only its base URL, auth header, and allowed endpoints. Do not use outside network sources.
3. Fetch `GET /api/schema` and `GET /api/data-dictionary` at the start of each task. Treat them as authoritative for table names, relationships, nullable columns, source/canonical meaning, timestamp conventions, and endpoint behavior.
4. Use `POST /api/sql` for analytical work. The response shape is `columns`, `rows`, `row_count`, and `truncated`; if `truncated` is true, rerun narrower queries.
5. Treat analytical tasks as read-only. Use `POST /api/sql/transaction` only when the prompt explicitly requests an approved correction.
6. Build the final result directly from the request payload and answer template. Write exactly one JSON object to `answer.json`, with no commentary or additional fields.

## Request Interpretation

- Treat the answer template as the output contract, including exact property names, array lengths, uniqueness, sort order, enum values, decimal places, and disallowed extra fields.
- Use the request payload for all IDs, windows, thresholds, status policies, ranking rules, and rounding. Do not hardcode values from prior tasks.
- Apply timestamp boundaries exactly. For inclusive windows use `>= start` and `<= end`; for strict-before rules use `< cutoff`. Stored timestamps are ISO-8601 UTC text ending in `Z`, so string comparisons are valid for exact UTC boundaries.
- Build one eligible cohort CTE first, then derive all counts, rates, rankings, and exception lists from that cohort. Keep incomplete, unresolved, active, or unreversed records in denominators when the business definition says they remain eligible.
- Use unrounded metric values for ranking and risk/status classification. Round only final reported numeric fields to the precision required by the template.
- Sort identifier arrays exactly as requested, usually ascending by the stable business ID. Use specified tie-breakers on unrounded values.

## Effective Data Rules

- Prefer event/import history over `current_status` snapshot columns for cutoff-state analysis; the data dictionary warns that snapshot columns may lag append-only history.
- For imported source tables with retryable upstream events, deduplicate on `(source_system, external_event_id)` by the latest `ingested_at`; use the stable row ID as the final tie-breaker.
- Work at the business grain requested by the payload: distinct orders, shipments, tasks, cases, logical refunds, accounts, employees, or teams. Avoid counting source rows when the metric asks for distinct business entities.
- Preserve raw source values. Use canonical fields for operational analytics and approved corrections.
- Use `julianday()` differences for elapsed-hour calculations, and compare ISO timestamp text for ordering and cutoff filters.
- Use `NULLIF(denominator, 0)` for rates; decide how to report zero-denominator cases from the output schema and request policy.

## Common Domain Patterns

### Production Population

- For production accounts, exclude rows where `accounts.is_internal = 1` or `accounts.is_test = 1`.
- For production orders or support cases, join through `accounts` and apply the production account filter unless the request defines production differently.
- For warehouse work, apply `warehouse_tasks.work_class = 'PRODUCTION'` when the request asks for production tasks.
- Do not add status, segment, tier, region, campaign, or warehouse filters unless they are present in the request scope.

### Fulfillment Scorecards

- Use `orders`, `campaigns`, `warehouses`, `shipments`, and effective `carrier_scans`.
- When a request says to use a campaign's official active window, join `campaigns` and filter order creation between `starts_at` and `ends_at`.
- A complete order requires at least one physical shipment and every associated shipment effectively delivered by the cutoff.
- Derive each shipment's effective final carrier state from its latest effective canonical scan at or before the cutoff.
- An on-time complete order requires every delivered shipment to have `DELIVERED` at or before its `promised_delivery_at`.
- For incomplete severe exceptions, compare the cutoff to the latest shipment promise only when a shipment promise exists. For completed severe exceptions, check whether any shipment was delivered more than 24 hours after its promise.

### Refund Reconciliation

- Use `refund_attempts`, `orders`, `accounts`, and `fx_rates`.
- Work at `refund_id` for logical refunds and linked reversals, not just `refund_row_id`.
- Treat `SETTLED` rows as principal settled refunds and `REVERSED` rows with `linked_refund_id` as linked reversals, unless the request defines different effective statuses.
- Normalize reason codes with `UPPER(TRIM(reason_code))` before grouping or duplicate-reason checks.
- Convert monetary minor units to currency units, then to USD with `fx_rates.usd_per_unit` for the row currency and service date. Convert linked reversals at the reversal service date.
- When comparing an order's gross amount to a refund candidate, value the order gross in its own currency using the settled refund service-date FX rate named by the request.
- For net refund by reason, subtract linked reversals from the normalized reason of the original settled refund. Count unresolved duplicate-reason leakage only among unreversed effective settled logical refunds.

### Carrier Quality Corrections

- Use read-only SQL first to isolate the exact contradiction named by the request, usually from `carrier_scans`, `shipments`, `orders`, `warehouses`, and `source_import_batches`.
- Identify the target by stable IDs such as `scan_row_id` and `shipment_id`; verify old canonical value, proposed new canonical value, batch, warehouse, and cutoff scope.
- Compute pre-correction business metrics before the mutation.
- In the transaction, update only the approved canonical field and correction metadata on the single target row, and insert exactly one `correction_audit` row with the request-provided audit fields.
- Do not change raw fields, source identity fields, unrelated business rows, or noncanonical data.
- After the transaction, verify affected business row count, audit row count, corrected canonical value, audit contents, and post-correction metrics. Report an applied status only when the request's success rule is fully satisfied; otherwise report the observed result.

### Warehouse Productivity

- Use `warehouse_tasks`, `warehouse_task_events`, `employees`, and `warehouses`.
- Filter eligible tasks by requested warehouse, created window, and production work class.
- Derive completion by effective `COMPLETED` task events at or before the state cutoff. Count distinct completed tasks for completion rate.
- Sum completed production units and productive minutes from the completed units specified by task events. Units per hour is `completed_units / productive_minutes * 60`.
- Count rework as distinct eligible tasks with a `REWORK` event in scope.
- Delayed high-priority tasks are `HIGH` or `URGENT`, have `due_at` strictly before the cutoff, and are not completed by the cutoff.
- Rank employees, teams, and task lists with the tie-breakers from the request, not with rounded display values.

### Support Health

- Use `support_cases`, `case_events`, and `accounts`.
- Filter eligible cases by production account, segment, region, and opened window from the request.
- Derive case state at cutoff from lifecycle events at or before the cutoff. Treat `OPENED` as open, `REOPENED` as reopened, and `RESOLVED` as resolved; count the reopened subset separately when requested.
- For support active time, accumulate intervals where support owes action. Start active intervals on `OPENED`, `REOPENED`, and `CUSTOMER_REPLIED`; stop them on `WAITING_CUSTOMER` and `RESOLVED`; close still-active intervals at the cutoff.
- First-response breach uses active time from opening until first `AGENT_RESPONDED`; for unresponded cases, use active elapsed time at the cutoff.
- Resolution breach uses active time to `RESOLVED`; for active cases, use active elapsed time at the cutoff.
- Severe active cases are active at cutoff, have a qualifying priority from the request, and exceed that priority's active-time resolution threshold.
- For medians, order unrounded resolved-case active resolution hours; for an even count average the two central values, then round only the reported median.

## SQL Practice

- Use CTEs to make each business grain explicit: `eligible`, `effective_events`, `latest_state`, `per_entity`, `rollup`, and `exceptions`.
- Use window functions such as `row_number()` for source retry deduplication and latest-at-cutoff state selection.
- Keep verification queries independent from the main query where possible: total cohort size, category breakdowns, exception IDs, and ranking inputs should reconcile.
- Use left joins from the eligible cohort when absence is meaningful, such as orders with no shipments, cases with no response, or tasks not completed by cutoff.
- Inspect small grouped vocabularies with `select status, count(*) ... group by status` before assuming status names.

## Finalization Checklist

- Confirm every required field in the answer template is present and no extra fields are present.
- Confirm all arrays are unique and in the required order.
- Confirm decimal precision matches the template and that risk/status rules used unrounded source metrics.
- Confirm no analytical request changed workplace data.
- For correction tasks, confirm the audit endpoint or audit table shows exactly the expected audit row before using an applied status.
- Parse `answer.json` as JSON before finishing.
