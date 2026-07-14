---
name: sql-database-analytics
description: Solve operations analytics tasks against a remote SQLite database API, especially usage rollups, support-ticket defect metrics, incident exposure summaries, and approved data-quality correction simulations. Use when a prompt provides an analytics API, SQL schema, answer template, and asks for JSON metrics with business filters, exclusion counters, deterministic ordering, or safe correction_sql.
---

# SQL Database Analytics

## API and Discovery Workflow

1. Read the task prompt, its answer template, and the documented remote API entrypoint. Use the remote HTTP API for database inspection.
2. Call `GET /` for endpoint syntax, `GET /health`, `GET /schema`, and `GET /tables`. Sample tables with `GET /tables/<name>?limit=100&offset=0` only when needed.
3. Use `POST /query` for read-only SQLite:

```bash
curl -sS -X POST "$BASE/query" \
  -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT name FROM sqlite_master ORDER BY name","params":[]}'
```

4. First query reference tables: `products`, `metric_notes`, `data_quality_cases`, and the schema SQL for views. Map product names to `product_id` from `products`.
5. Build metrics from CTEs: start with candidate rows, then add one exclusion predicate at a time. Query counts for each stage before producing final JSON.
6. For date ranges, treat prompt end dates as inclusive. For date columns use `BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`; for timestamps use `created_at >= '<start> 00:00:00' AND created_at < datetime('<end>', '+1 day')`.

## Transferable Business Filters

Use these defaults unless the prompt/template explicitly says otherwise:

- Customer accounts are external, non-test accounts: `is_internal = 0` and `account_status IN ('active','paused')`. The `active_customer_accounts` view applies this filter.
- "Enterprise accounts" means `accounts.segment = 'enterprise'`; only filter `subscriptions.plan_code = 'enterprise'` if the prompt says enterprise subscription/plan.
- Active product subscription on a usage date means same `account_id` and `product_id`, `start_date <= metric_date`, `(end_date IS NULL OR end_date >= metric_date)`, and `plan_code NOT IN ('trial','internal')`. Do not drop historically valid ended subscriptions solely because `subscription_status = 'ended'`.
- Region filters come from `accounts.region`. If an incident region is `GLOBAL`, do not filter to one region.
- Qualified production usage starts from `usage_daily` when exclusion counters are needed, or `production_usage_daily` for simple production-only reads. Include `environment = 'production'`, `is_backfill = 0`, active external account filters, requested product/segment/region filters, and active subscription filters when requested.
- Exclude telemetry v1 overlap rows when a `telemetry_v1` usage row has another non-v1 row for the same account, product, activity date, and environment after applying the same candidate filters. Keep the non-v1 rows; do not deduplicate same-source rows unless the task asks.
- Customer-impacting defect tickets use product/date filters plus `customer_impact = 1`, `status <> 'canceled'`, non-duplicate tickets, external customer accounts, and categories in `('bug','outage','performance','data_loss')`.
- Treat duplicates defensively as `is_duplicate = 1 OR duplicate_of IS NOT NULL`. For corrections, changed duplicate rows should have both `is_duplicate = 1` and `duplicate_of` populated.
- For backlog metrics, qualified tickets are usually `status IN ('open','in_progress')`; for created-period rollups include resolved tickets unless the template says backlog/open.
- SLA breach default: `COALESCE(closed_at, as_of_timestamp) > sla_due_at`, where `as_of_timestamp` is the task's reporting cutoff, not wall-clock now. For period reports, use the instant after the inclusive end date unless a different cutoff is specified. Compute breach rates as decimal ratios rounded to 4 places; return `0.0` for zero denominators.
- Median close hours should use only closed qualified tickets: `(julianday(closed_at)-julianday(created_at))*24`. For even counts, average the two middle values.

## Incident Exposure Pattern

1. Query the incident row by `incident_id`; use its `product_id`, `started_at`, `resolved_at`, `severity`, and `impacted_region`.
2. Usage exposure uses activity dates from `date(started_at)` through `date(resolved_at)` inclusive because usage is daily. Apply production, non-backfill, external active account, active subscription, region, and telemetry-v1-overlap exclusions.
3. Post-incident support signals use `created_at > resolved_at AND created_at <= datetime(resolved_at, '+7 days')`, same product, external customer accounts, and impacted region. Unless the template includes a non-defect exclusion counter, do not restrict these follow-up tickets to defect categories.
4. Count ticket exclusions separately for canceled/duplicate and non-customer-impact rows, using the same candidate window and region/product filters.

## Safe Correction and Simulation Workflow

Never execute correction updates through `/query`. Use `/simulate` with an UPDATE script and follow-up read-only queries:

```json
{
  "script": "UPDATE ...;",
  "queries": [
    {"name": "changed_check", "sql": "SELECT changes() AS changed_rows"},
    {"name": "metric_after_fix", "sql": "SELECT ..."}
  ]
}
```

Correction procedure:

1. Read the requested `data_quality_cases` row by case id.
2. Require `case_status = 'approved'`; reject draft/rejected cases. Verify `target_table`, `field_name`, `case_type`, `old_value`, and `new_value` match the prompt.
3. Parse `target_ids_csv` exactly. Pre-query the target rows and confirm they currently match the old value / null duplicate state.
4. Write one narrow, auditable UPDATE guarded by explicit ids, old-value predicates, and the approved case row. Populate `audit_reason` from the case. Use the case `created_at` as deterministic `audit_updated_at` unless the prompt gives another audit timestamp.
5. Simulate the script and use the simulated database results for all "after fix" metrics. Report the simulator's changed row count or an equivalent `SELECT changes()` result.

Patterns:

```sql
UPDATE usage_daily
SET product_id = '<new_product>',
    audit_reason = (SELECT audit_reason FROM data_quality_cases WHERE case_id = '<case_id>'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = '<case_id>')
WHERE usage_id IN (...)
  AND product_id = '<old_product>'
  AND EXISTS (
    SELECT 1 FROM data_quality_cases dq
    WHERE dq.case_id = '<case_id>'
      AND dq.case_status = 'approved'
      AND dq.target_table = 'usage_daily'
      AND dq.field_name = 'product_id'
  );
```

```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = '<primary_ticket_id>',
    audit_reason = (SELECT audit_reason FROM data_quality_cases WHERE case_id = '<case_id>'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = '<case_id>')
WHERE ticket_id IN (...)
  AND is_duplicate = 0
  AND (duplicate_of IS NULL OR duplicate_of = '')
  AND EXISTS (
    SELECT 1 FROM data_quality_cases dq
    WHERE dq.case_id = '<case_id>'
      AND dq.case_status = 'approved'
      AND dq.target_table = 'tickets'
      AND dq.field_name = 'duplicate_of'
  );
```

## Output Habits

- Return only the JSON object requested by the answer template. Do not include markdown, comments, SQL logs, or explanatory text.
- Mirror template keys exactly. Include required zero-valued keys such as all severity buckets `P1` through `P4`.
- JSON numbers should be numbers, not strings. Round compute hours to 2 decimals and rates to 4 decimals when requested.
- Put an `ORDER BY` on every array-producing query. Common orders: ids ascending; regions alphabetically; top accounts by descending metric then ascending `account_id`; severity priority `P1`, `P2`, `P3`, `P4`.
- Use `ROW_NUMBER() OVER (ORDER BY metric DESC, account_id ASC)` for stable ranks.
- For top-N arrays, apply the template's limit after grouping and deterministic ordering.
- If a value can be absent, return the template's natural empty value (`[]`, `{}` with zero buckets, `0`, or `null`) rather than omitting the key.

## Common Mistakes to Avoid

- Bypassing the documented remote API for database inspection.
- Applying draft or rejected data-quality cases, or updating rows beyond the case's target ids.
- Mutating the live database instead of using `/simulate` for correction tasks.
- Treating inclusive end dates as midnight-only timestamp filters.
- Filtering historical subscriptions by current `subscription_status` and accidentally excluding subscriptions that were active on the metric date.
- Counting internal/test accounts, canceled tickets, duplicates, non-customer-impact tickets, backfills, staging/sandbox/internal usage, or telemetry-v1 overlap rows as qualified.
- Computing exclusion counters from different candidate scopes than the final metric.
- Comparing open-ticket SLA status to wall-clock now instead of the task reporting cutoff.
- Returning rounded values as strings or relying on unstated row ordering.
