---
name: atlas-commerce-ops
description: Use for Atlas Commerce Operations workplace tasks that require reading local prompt and payload JSON files, using environment_access.md to query the authenticated Atlas service, computing cutoff-based operations metrics or reconciliations with SQL, optionally applying an approved audited canonical correction, and writing answer.json exactly matching the supplied answer_template.json.
---

# Atlas Commerce Operations

## Core Workflow

1. Read `prompt.txt` and every file in `input/payloads/` before querying. Treat the request payload as the business contract and `answer_template.json` as the output contract.
2. Read `environment_access.md` for the base URL, authorization header, and allowed endpoints. Do not use other network locations or hard-code credentials.
3. Fetch `GET /api/schema` and `GET /api/data-dictionary` before writing substantive SQL. The service is SQLite-style: timestamps are ISO-8601 UTC text, dates are `YYYY-MM-DD`, integer booleans use `0`/`1`, and monetary minor amounts must be converted through `fx_rates`.
4. Use `POST /api/sql` for read-only analysis. Use `POST /api/sql/transaction` only when the task explicitly requests an approved correction.
5. Build the result from queries and request rules, then write only `answer.json`. The JSON must contain exactly the required fields, no commentary, no extra keys, arrays in the requested order, and final rounding only.

Useful shell pattern:

```bash
BASE_URL=$(awk -F= '/^GDPEVO_ENV_BASE_URL=/{print $2}' environment_access.md)
AUTH_VALUE=$(awk -F': ' '/^Authorization:/{print $2}' environment_access.md)

curl -sS -H "Authorization: $AUTH_VALUE" "${BASE_URL%/}/api/schema"
curl -sS -H "Authorization: $AUTH_VALUE" "${BASE_URL%/}/api/data-dictionary"

SQL='SELECT COUNT(*) AS n FROM orders'
jq -nc --arg sql "$SQL" '{sql:$sql}' |
  curl -sS -H "Authorization: $AUTH_VALUE" -H 'Content-Type: application/json' \
    -X POST "${BASE_URL%/}/api/sql" -d @-
```

The SQL response shape is `columns`, `rows`, `row_count`, and `truncated`; keep queries narrow enough that `truncated` is false for answer-bearing detail.

## Query Principles

- Prefer event history over denormalized `current_status` when the request says "at cutoff", "by cutoff", or gives an as-of timestamp.
- Apply production scope explicitly. For production accounts/customers/orders, join `accounts` and require `is_internal = 0` and `is_test = 0`. For warehouse work, require `warehouse_tasks.work_class = 'PRODUCTION'` when requested.
- Honor exact boundaries from the request. Use `BETWEEN` only for inclusive windows; use `<` for "strictly before"; use `<=` for "by/no later than cutoff".
- Keep unrounded values for ranking and status classification. Round only the final reported number of decimal places.
- Sort identifier arrays in the requested order, usually ascending. For ranked outputs, apply all specified tie-breakers before limiting.
- Treat source identity fields (`source_system`, `external_event_id`, raw source values, source row IDs) as immutable.

Many imported tables can contain retried source rows. Build an effective-row CTE before aggregation when a table has `source_system`, `external_event_id`, and `ingested_at`:

```sql
WITH effective_rows AS (
  SELECT *
  FROM (
    SELECT t.*,
           ROW_NUMBER() OVER (
             PARTITION BY source_system, external_event_id
             ORDER BY ingested_at DESC, <stable_primary_key> DESC
           ) AS rn
    FROM <imported_table> AS t
  )
  WHERE rn = 1
)
```

For cutoff state from append-only events, first filter effective events to `event_at <= :cutoff`, then take the last event per business entity ordered by event time and stable event ID.

## Domain Patterns

### Fulfillment and Shipments

- Eligible campaign orders usually join `orders`, `accounts`, `campaigns`, `shipments`, `carrier_scans`, and `warehouses`.
- Verify a campaign's active window from `campaigns`; use the request's campaign and creation-window policy.
- An order is complete only if it has at least one shipment and every associated shipment has an effective delivered carrier state by the cutoff.
- A complete order is on time only if every shipment was delivered no later than its own `promised_delivery_at`.
- Severe late/incomplete logic is order-level: completed orders severe if any shipment delivery is more than the request's grace period after promise; incomplete orders severe only when the cutoff is beyond the latest shipment promise plus the grace period.
- Regional rates use the order's assigned warehouse region and keep incomplete orders in the denominator unless the request says otherwise.

### Refund Reconciliation

- Scope production accounts by `accounts.tier`, production flags, and the service-date window in the request.
- Deduplicate source retries first, then identify the latest effective attempt for each logical `refund_id`.
- Count effective settled logical refunds from latest logical refunds whose status is settled and that are not reversal rows.
- Treat rows with `linked_refund_id` as linked reversals; count effective linked reversals separately and subtract their USD value from the linked refund/order exposure.
- Convert money as `(amount_minor / 100.0) * fx_rates.usd_per_unit` using the refund or reversal `service_date` and row currency. When comparing to order gross, convert `orders.gross_amount_minor` using the same service date as the settled refund candidate.
- Normalize reason codes with `UPPER(TRIM(reason_code))`. Rank reasons by effective net refund USD descending, then normalized reason ascending.
- Leakage candidates are distinct orders satisfying any request rule, commonly net refund USD greater than order gross USD or multiple unreversed settled logical refunds with the same normalized reason.

### Warehouse Productivity

- Eligible tasks come from `warehouse_tasks` filtered by warehouse, created window, and `work_class = 'PRODUCTION'` when requested.
- Determine completion by effective `warehouse_task_events` with `event_type = 'COMPLETED'` at or before the state cutoff, not by future events.
- Sum completed units and productive minutes from completed task events attached to eligible completed tasks.
- Employee productivity is `total_completed_units / total_productive_minutes * 60`; exclude zero-minute employees from rate ranking unless the request specifies a zero-rate fallback.
- Rework task count is distinct eligible tasks with an effective `REWORK` event at or before cutoff, or the request's explicit rework definition.
- Delayed high-priority tasks are high/urgent tasks with `due_at` strictly before cutoff and no completed event by cutoff.
- Team completion rates use eligible tasks as denominator and the same completion definition as the facility rate.

### Support Health

- Scope cases by `support_cases.opened_at`, production account flags, account segment, and account regions.
- Reconstruct case state at cutoff from effective `case_events` when possible. Active-at-cutoff cases are those whose latest state is open or reopened according to the request policy.
- First response breach: compute active support time from opening until the first `AGENT_RESPONDED`; if there is no response by cutoff, compute active elapsed time through cutoff.
- Resolution breach: for resolved cases, compute active support time from opening to resolution; for active cases, compute active elapsed time through cutoff.
- Support active time pauses while the case is waiting on the customer and resumes on customer reply or reopen events. Use ordered events to build active intervals; clamp every interval to the cutoff.
- Severe active cases are active at cutoff, priority urgent/high, and beyond the request's active-time resolution threshold.
- Median active resolution hours uses resolved eligible cases at cutoff; for an even count, average the two central values before final rounding.

SQLite median pattern:

```sql
WITH ranked AS (
  SELECT value,
         ROW_NUMBER() OVER (ORDER BY value) AS rn,
         COUNT(*) OVER () AS cnt
  FROM values_to_rank
)
SELECT AVG(value) AS median_value
FROM ranked
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2);
```

### Carrier Quality Corrections

- Use corrections only for tasks that explicitly request them. Start with read-only queries that identify exactly one target row and capture the pre-change value.
- For carrier batches, cohort membership commonly means shipments with an effective scan in the named `import_batch_id` at or before the cutoff. Backlog is based on the effective final carrier status not being delivered.
- Find raw/canonical contradictions by deriving the expected canonical status from the raw status or dominant raw-to-canonical mapping, then locate the single row whose canonical value conflicts.
- Preserve raw values, source identity, timestamps, and unrelated business rows. Update only the approved canonical field and correction metadata explicitly allowed by the request.
- Insert exactly one `correction_audit` row using the request's audit fields. Use a guarded `WHERE` clause that includes the target primary key and old value so the update cannot affect an unexpected row.
- After transaction commit, verify row counts, the corrected canonical value, backlog before/after counts, and the audit record via `GET /api/correction-audit` or a read-only SQL query.
- Report `APPLIED` only if the task's success rule is satisfied; otherwise report `NOT_APPLIED` with observed counts and state.

## Final Answer Assembly

- Validate required fields and `additionalProperties`/`additional_properties` manually against `answer_template.json`.
- Emit JSON numbers, not strings, for numeric fields. Use the requested precision: counts as integers, money commonly two decimals, rates commonly four decimals, hours commonly two decimals.
- Re-run a compact verification query for every count, rate denominator, ranked list, and mutation/audit count before writing `answer.json`.
- Do not copy prior training answers or task-local example values into a new answer. Recompute from the live environment and the current request payload every time.
