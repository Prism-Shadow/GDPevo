---
name: atlas-commerce-ops-sql-analyst
description: Solve Atlas Commerce Operations workplace tasks that provide prompt/payload files, a strict answer_template.json, and a TASK_ENV_BASE_URL with schema, data-dictionary, SQL, correction-audit, or controlled transaction endpoints. Use for fulfillment, refunds, carrier quality corrections, warehouse productivity, support health, inventory/order/payment analytics, and similar cutoff-based operational JSON reports.
---

# Atlas Commerce Ops SQL Analyst

Use this skill to calculate strict JSON answers from the Atlas Commerce Operations service. Always compute from the live workplace data; never reuse values from examples or prior runs.

## Required Workflow

1. Read `input/prompt.txt`, every file under `input/payloads/`, and especially `answer_template.json`.
2. Extract the business scope, cutoff/window boundaries, ordering rules, rounding rules, status/risk rules, and mutation permission from the request payload.
3. Resolve `<TASK_ENV_BASE_URL>` and the provided authorization token. Do not call `POST /api/judge`.
4. Fetch `GET /api/schema` and `GET /api/data-dictionary` before writing SQL. Confirm table and column names from the live service.
5. Use `POST /api/sql` for read-only analysis:

```bash
curl -sS \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql":"select 1 as x"}' \
  "$TASK_ENV_BASE_URL/api/sql"
```

The SQL response has `columns`, `rows`, `row_count`, and `truncated`. If `truncated` is true, replace row-dumping queries with aggregates or narrower filters.

6. Use `POST /api/sql/transaction` only when the prompt and request explicitly authorize a controlled correction. Otherwise perform no writes.
7. Build `answer.json` as exactly one JSON object matching `answer_template.json`: no commentary, no extra keys, exact field names, arrays sorted as specified, and numeric precision from the template/request.

## Core SQL Rules

- Treat stored timestamps as UTC ISO text. Apply inclusive or strict boundaries exactly as written.
- Prefer event history over denormalized `current_status` when the request asks for state at a cutoff.
- Imported source tables can contain retry copies. Deduplicate by `(source_system, external_event_id)` before counting or sequencing:

```sql
with effective_events as (
  select *
  from (
    select e.*,
           row_number() over (
             partition by source_system, external_event_id
           order by ingested_at desc, stable_row_id desc
           ) as rn
    from some_event_table e
  )
  where rn = 1
)
```

Replace `stable_row_id` with that table's explicit primary key, such as `scan_row_id`, `case_event_id`, `task_event_id`, or `refund_row_id`.

- For point-in-time status, first dedupe source rows, then take the latest effective event at or before the cutoff per business entity. Order by event timestamp descending, then a stable row id descending.
- For production account scope, join `accounts` and require `is_internal = 0` and `is_test = 0`, plus any requested `segment`, `tier`, or `region` filters.
- Monetary fields ending in `_minor` are minor units. Convert with `/ 100.0` and join `fx_rates` on the row's service date and currency when USD reporting is requested.
- Round only final reported numbers. Use unrounded values for ranking and thresholds unless the request says otherwise.
- Implement risk/status policies in order. The first rule whose complete condition is true wins; otherwise use the specified fallback.
- Validate every array for uniqueness, exact length when constrained, requested sort order, and identifier formatting.

## Useful Schema Map

- Accounts and scope: `accounts(account_id, segment, tier, region, is_internal, is_test)`.
- Orders: `orders(order_id, account_id, campaign_id, warehouse_id, order_created_at, promised_at, currency, current_status, gross_amount_minor)`.
- Campaign windows: `campaigns(campaign_id, starts_at, ends_at)`.
- Shipments and carrier scans: `shipments(shipment_id, order_id, warehouse_id, promised_delivery_at, current_status)`, `carrier_scans(scan_row_id, shipment_id, raw_status, canonical_status, canonical_event_at, import_batch_id, corrected_at, correction_reason)`.
- Refunds/payments: `refund_attempts(refund_id, order_id, status, reason_code, amount_minor, currency, service_date, linked_refund_id)`, `payment_events(...)`, `fx_rates(rate_date, currency, usd_per_unit)`.
- Warehouse work: `warehouse_tasks(task_id, warehouse_id, assigned_employee_id, work_class, priority, created_at, due_at, current_status)`, `warehouse_task_events(task_id, event_type, event_at, units, productive_minutes)`, `employees(employee_id, warehouse_id, team_id)`.
- Support: `support_cases(case_id, account_id, priority, opened_at, current_status)`, `case_events(case_id, event_type, event_at, actor_type)`.
- Corrections: `correction_audit(audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor)`.

## Domain Recipes

### Fulfillment Scorecards

- Eligible production orders usually come from `orders` joined to `campaigns`, `accounts`, `warehouses`, `shipments`, and effective `carrier_scans`.
- For a campaign cohort, require the named `campaign_id` and `order_created_at` inside the campaign's official active window.
- A complete physical order has at least one shipment and every associated shipment has effective final carrier status `DELIVERED` by the cutoff.
- On-time completion requires every shipment delivery timestamp to be at or before that shipment's `promised_delivery_at`.
- Incomplete orders stay in the denominator for on-time rates.
- Severe exception logic often depends on incomplete shipments more than 24 hours past latest shipment promise, or completed shipments delivered more than 24 hours after promise. Apply the request's exact definition.
- For warehouse-region rollups, join `orders.warehouse_id` to `warehouses.region`. Rank worst regions by unrounded rate, then region label.

### Refund Reconciliation

- Scope by account production flags, requested tier/segment/region, and refund `service_date` range.
- Count logical refunds by distinct `refund_id` after deduping retry rows. Treat effective settled refunds as `status = 'SETTLED'` unless the request defines a different accepted status.
- Treat linked reversals as rows with a reversal status and `linked_refund_id` pointing to a settled logical refund. Subtract reversal USD from settled refund USD for net exposure and reason-code ranking.
- Convert each refund or reversal using `fx_rates.usd_per_unit` for that row's `service_date` and `currency`.
- For order gross comparisons, value `orders.gross_amount_minor` in the order currency using the refund service-date FX basis specified by the request.
- Leakage candidates commonly include orders where net refund USD exceeds gross order USD or where multiple unreversed settled refunds share a normalized reason code. Return distinct order IDs sorted by the request's rule.

### Carrier Quality Corrections

- Only perform a mutation when the task explicitly asks for an approved correction.
- Find the single source/canonical contradiction inside the requested `import_batch_id`, facility, cohort, and cutoff. Keep raw source fields and source identity fields unchanged.
- For backlog analysis, identify shipments with an effective scan in the named batch at or before cutoff, then classify each shipment by its effective final canonical carrier status at the cutoff.
- Apply the minimal canonical-field correction only. Insert exactly one audit row using the request's approved `audit_id`, `correction_key`, `reason_code`, `corrected_at`, and `actor`.
- After the transaction, query the corrected business row and `GET /api/correction-audit` or `correction_audit` to verify affected business rows, audit rows, and post-change canonical value. Return the request's success status only if its success rule is fully satisfied; otherwise return the request's failure status with the observed results.

### Warehouse Productivity

- Eligible tasks normally filter `warehouse_tasks` by `warehouse_id`, `work_class = 'PRODUCTION'`, and `created_at` window.
- Use deduped `warehouse_task_events` at or before the cutoff for completed units, productive minutes, completion state, and rework evidence.
- Completed production units are usually summed from `COMPLETED` events for eligible tasks. Units per hour is `sum(units) / sum(productive_minutes) * 60`.
- Rank employees by unrounded units per hour descending, then `employee_id` ascending.
- Count rework as distinct eligible tasks with a `REWORK` event at or before the cutoff unless the request defines another source.
- Delayed high-priority tasks have priority in the requested high-priority set, `due_at` before the cutoff under the requested strictness, and no completion by cutoff.
- Lowest-performing team uses completion rate by `employees.team_id`, ordered by unrounded completion rate ascending, then team ID.

### Support Health

- Eligible cases join `support_cases` to production `accounts` and filter by account segment/region plus `opened_at` window.
- Reconstruct case state at cutoff from deduped `case_events` when needed. Active states commonly include `OPEN`/`OPENED` and `REOPENED`; resolved state ends active time unless later reopened.
- For support active-time clocks, build an event timeline per case through the cutoff. Accumulate time while the case is the support team's active responsibility, pause intervals after `WAITING_CUSTOMER`, resume at `CUSTOMER_REPLIED` or `REOPENED`, and stop at `RESOLVED`; cap active unresolved cases at the cutoff.
- First-response breach compares active time from opening to first `AGENT_RESPONDED`, or to cutoff for cases without an agent response.
- Resolution breach compares active time to `RESOLVED`, or to cutoff for active cases.
- Severe active cases are active at cutoff, have the requested severe priorities, and exceed the resolution active-time threshold.
- Median resolved active hours should use only eligible cases resolved at the cutoff. For an even count, average the two central values, then round final output.
- Worst accounts rank by severe active case count descending, then active-clock breach count descending, then account ID ascending unless the request overrides this.

## Final Checks

- Compare aggregate identities before writing: numerator plus complement equals denominator, post-minus-pre equals delta, and rates match the raw counts.
- Re-run small verification SQL for every output array and top-N ordering.
- Serialize `answer.json` with JSON numbers, not strings, for numeric fields.
- Do not include explanatory text outside the JSON document.
