---
name: sql-database-analytics
description: Use for SCN_022 operations analytics tasks that require querying the task-provided remote SQLite database API, computing customer/product usage or support-ticket rollups, simulating approved data-quality corrections, and returning strict JSON answers from task templates.
---

# SQL Database Analytics

## Workflow

1. Read the prompt and `input/payloads/answer_template.json`. Extract the exact product, date or timestamp window, region, segment, incident ID, data-quality case ID, requested precision, and ordering rules.
2. Use the task-provided API base URL. Start with `GET /`, `GET /schema`, and targeted `GET /tables/<name>?limit=100&offset=0` samples only when useful. Use `POST /query` for read-only SQL:

```json
{"sql":"SELECT ...","params":[]}
```

3. Query `metric_notes`, `products`, and any relevant `incidents` or `data_quality_cases` rows before writing final SQL. Treat database rows as authoritative over prompt paraphrases.
4. Build SQL with CTEs named like `candidate`, `excluded_counts`, `qualified`, and `rollup`. Keep the candidate universe separate from the qualified set so exclusion counters are auditable.
5. Prefer `EXISTS` for subscriptions to avoid multiplying usage rows. Use joins to `accounts` only once per candidate set.
6. Run cross-check queries: candidate count, each exclusion count, qualified count, top-row tie order, and final aggregate totals. Then assemble one JSON object matching the template exactly.

## Schema Conventions

- Core tables: `accounts`, `subscriptions`, `usage_daily`, `tickets`, `incidents`, `data_quality_cases`, `products`, `metric_notes`.
- Useful views: `active_customer_accounts` excludes internal accounts and keeps `account_status IN ('active','paused')`; `production_usage_daily` keeps `environment='production'`; `customer_support_tickets` excludes only `category='internal_test'`.
- Use base tables, not views, when the answer needs exclusion counts for rows hidden by a view, audit fields, environment, or update targets.
- Date strings are ISO text. For date columns use inclusive `BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`. For timestamp end dates, prefer `created_at >= start AND created_at < date(end, '+1 day')` unless the template specifies an inclusive timestamp.

## Transferable Filters

### Accounts and Subscriptions

- External customer account: `accounts.is_internal = 0` and `accounts.account_status <> 'test'`. If the task says active customer, require `account_status IN ('active','paused')`.
- Enterprise account tasks usually require both `accounts.segment = 'enterprise'` and an active same-product subscription with `plan_code = 'enterprise'` when the metric is subscription-scoped.
- Active product subscription on a usage date:

```sql
EXISTS (
  SELECT 1
  FROM subscriptions s
  WHERE s.account_id = u.account_id
    AND s.product_id = u.product_id
    AND s.subscription_status = 'active'
    AND s.start_date <= u.activity_date
    AND (s.end_date IS NULL OR s.end_date >= u.activity_date)
)
```

### Usage Metrics

- Qualified customer usage normally starts from `usage_daily` joined to `accounts`, filtered to product, activity-date window, prompted region or segment, external or active customer status, active subscription, and `environment = 'production'`.
- For incident exposure, read the incident row for `started_at`, `resolved_at`, `product_id`, `impacted_region`, and severity. Include usage dates from `date(started_at)` through `date(resolved_at)`; if `impacted_region = 'GLOBAL'`, do not apply a region filter.
- Exclude telemetry migration double-counts: when a `telemetry_v1` row overlaps a newer source for the same `account_id`, `product_id`, `activity_date`, and `environment`, do not count the v1 row. The usual predicate is `u.source_system = 'telemetry_v1' AND EXISTS (SELECT 1 FROM usage_daily x WHERE x.account_id = u.account_id AND x.product_id = u.product_id AND x.activity_date = u.activity_date AND x.environment = u.environment AND x.source_system <> 'telemetry_v1')`. Report the v1 overlap counter when requested.
- Treat `is_backfill = 1` as excluded when the prompt or template asks for backfill exclusions, especially incident exposure. For ordinary period rollups, do not silently drop or include backfills; check `metric_notes`, source-system intent, and requested exclusion counters.

### Support Tickets

- Defect categories are `bug`, `outage`, `performance`, and `data_loss`.
- Qualified customer-impacting defect tickets generally require: product and created window, `status <> 'canceled'`, `is_duplicate = 0`, external or non-test account, `customer_impact = 1`, and category in the defect set.
- Backlog means unresolved operational work: `status IN ('open','in_progress')`. Do not count resolved tickets in backlog-by-severity or notification lists unless the prompt defines backlog differently.
- P1/P2 open counts use `severity IN ('P1','P2')` plus open or in-progress status.
- SLA breach counts use `closed_at > sla_due_at` for closed tickets and treat open/in-progress tickets as breached if no explicit as-of timestamp says otherwise: `COALESCE(closed_at, '9999-12-31') > sla_due_at`.
- Median close hours is for closed qualified tickets only:

```sql
WITH durations AS (
  SELECT (julianday(closed_at) - julianday(created_at)) * 24.0 AS hours
  FROM qualified
  WHERE closed_at IS NOT NULL
),
ordered AS (
  SELECT hours,
         ROW_NUMBER() OVER (ORDER BY hours) AS rn,
         COUNT(*) OVER () AS n
  FROM durations
)
SELECT ROUND(AVG(hours), 2) AS median_close_hours
FROM ordered
WHERE rn IN ((n + 1) / 2, (n + 2) / 2);
```

### Exclusion Counts

- Exclusion counts in templates are usually independent diagnostics over the candidate set, not a sequential funnel. Count each reason with its own `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` unless the template explicitly describes ordered exclusions.
- For ticket exclusions, use raw `tickets` joined to `accounts`; views can hide `internal_test` rows and undercount non-defect categories.
- For usage exclusions, compute non-production, backfill, internal/inactive, no-active-subscription, and telemetry-v1-overlap counts from the same candidate universe used by the template.

## Safe Correction and Simulation

1. Query `data_quality_cases` for the requested case. Require `case_status = 'approved'`, the expected `case_type`, `target_table`, and `field_name`. Never apply draft or rejected cases.
2. Expand only the case row's `target_ids_csv` into the update target list. The correction SQL must be narrow and idempotent:
   - Restrict to `WHERE id IN (...)`.
   - Guard the old/current value, such as `product_id = old_value` for usage product fixes, or `is_duplicate = 0 AND duplicate_of IS NULL` for ticket duplicate fixes.
   - Add an `EXISTS` subquery for the approved case and expected target metadata.
   - Populate `audit_reason` from `data_quality_cases.audit_reason` and `audit_updated_at` from `data_quality_cases.created_at`.
3. Use `POST /simulate`; it runs the update on a temporary copy and then executes read-only follow-up queries:

```json
{
  "script": "UPDATE ...;",
  "queries": [
    {"name":"metric_after_fix","sql":"SELECT ...","params":[]}
  ]
}
```

4. Use the response `changed_rows` plus follow-up query results for the answer. Return the same safe SQL string in `correction_sql`; do not report metrics from a separate pre-fix `/query` call.

## Output Rules

- Return only one JSON object with exactly the template keys. Use numbers for numeric fields, not strings.
- Round compute hours and close-hour values with `ROUND(..., 2)` and rates with the template precision, commonly `ROUND(1.0 * numerator / denominator, 4)`.
- Include required zero-valued buckets, especially severity keys `P1`, `P2`, `P3`, `P4`.
- Use deterministic ordering:
  - IDs ascending for ID arrays and account breakdowns unless specified otherwise.
  - Regions alphabetically.
  - Top accounts by descending metric, then ascending `account_id`.
  - Notification lists by descending backlog count, severity priority `P1`, `P2`, `P3`, `P4`, then ascending `account_id`.
- For follow-up incident tickets, use `(resolved_at, resolved_at + 7 days]`: `created_at > resolved_at AND created_at <= datetime(resolved_at, '+7 days')`.

## Common Mistakes

- Using the placeholder API URL literally instead of the task-provided base URL.
- Joining `subscriptions` directly and duplicating usage rows; use `EXISTS` unless intentionally reporting subscription rows.
- Computing exclusion counts after qualification instead of from the candidate universe.
- Forgetting active same-product subscription checks for usage exposure.
- Counting `telemetry_v1` rows that overlap newer telemetry for the same usage key.
- Applying defect category filters to incident follow-up support signals when the template only asks for customer-impacting support activity.
- Treating all qualified tickets as backlog tickets.
- Omitting zero severity buckets or changing the template's key names.
- Returning explanatory markdown, extra fields, or rounded numbers as strings.
