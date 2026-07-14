---
name: sql-database-analytics
description: Solve SCN_022-style SQL database analytics tasks through a remote operations analytics API. Use when Codex must inspect database schema, write SQLite queries, compute usage/support/incident metrics, apply approved data-quality corrections through simulation, and return a deterministic JSON object matching an answer template.
---

# SQL Database Analytics

## API Workflow

1. Read the task prompt and `input/payloads/answer_template.json` first. The template defines required keys, precision, ordering, and whether the task is a rollup, incident summary, or correction simulation.
2. Use the task-provided API base URL. Check `GET /`, `GET /health`, `GET /schema`, and `GET /tables`; sample only relevant tables with `GET /tables/<name>?limit=...`.
3. Use `POST /query` for read-only SQLite. Build queries as CTEs: `candidate`, `excluded_*`, `qualified`, then final aggregations. Keep sanity queries for row counts, account counts, and exclusions.
4. Use `POST /simulate` for correction tasks. Never mutate the source database directly; simulate the approved UPDATE on a temporary copy and run follow-up read-only queries against that copy.
5. Do not infer from local database files or environment source. Prefer the API schema, table samples, and `metric_notes`.

Useful API payloads:

```json
{"sql":"SELECT ...","params":[]}
```

```json
{
  "script": "UPDATE ...;",
  "queries": [
    {"name": "metric_name", "sql": "SELECT ...;"}
  ]
}
```

`/simulate` returns `changed_rows` plus named query results.

## Schema Conventions

Core tables are usually:

- `accounts(account_id, account_name, segment, region, account_status, is_internal)`
- `subscriptions(account_id, product_id, plan_code, subscription_status, start_date, end_date)`
- `usage_daily(usage_id, account_id, product_id, activity_date, environment, source_system, api_calls, compute_hours, is_backfill, audit_*)`
- `tickets(ticket_id, account_id, product_id, created_at, closed_at, status, severity, category, customer_impact, is_duplicate, duplicate_of, linked_incident_id, sla_due_at, audit_*)`
- `incidents(incident_id, product_id, started_at, resolved_at, severity, impacted_region)`
- `data_quality_cases(case_id, case_type, case_status, target_table, target_ids_csv, field_name, old_value, new_value, audit_reason, created_at)`

Views are convenient but can hide columns needed for exclusion counts or audit fields. Use base tables when validating candidates and exclusions.

## Business Filters

### Accounts and Subscriptions

- Usage and incident exposure for active customers: `a.is_internal = 0 AND a.account_status IN ('active','paused')`.
- Ticket rollups for external customers: `a.is_internal = 0 AND a.account_status <> 'test'`. Do not drop churned external accounts unless the prompt explicitly says active accounts.
- Enterprise account usage: require `a.segment = 'enterprise'`; when subscription qualification is involved, also require `s.plan_code = 'enterprise'`.
- Active subscription during a usage date: use `EXISTS`, not a direct join, to avoid duplicating usage rows:

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

Add `AND s.plan_code = 'enterprise'` only when the metric asks for enterprise subscriptions/accounts.

### Usage Metrics

Qualified usage generally means:

- requested `product_id`
- inclusive `activity_date` range
- `environment = 'production'`
- `is_backfill = 0`
- active external customer account
- active subscription window when the prompt mentions qualified customer usage, subscriptions, or incident exposure

Telemetry migration rule: do not exclude every `telemetry_v1` row. Exclude only `telemetry_v1` rows that overlap a `telemetry_v2` row for the same qualified candidate key, normally `(account_id, product_id, activity_date)`. Count these excluded rows when requested.

For incident usage exclusions, start from all product/date rows in the impacted region, then count reasons independently:

- non-production: `environment <> 'production'`
- backfill: `is_backfill = 1`
- internal or inactive account: `is_internal = 1 OR account_status NOT IN ('active','paused')`
- without active subscription: no active subscription `EXISTS` for that activity date
- telemetry overlap: overlapping `telemetry_v1` rows as above

Use the final qualified set after all exclusions for impacted accounts, API calls, compute hours, and highest-usage account.

### Ticket Metrics

Defect categories are:

```sql
category IN ('bug','outage','performance','data_loss')
```

Qualified defect tickets generally require:

- requested `product_id`
- created timestamp in the prompt window, using `created_at >= start` and `created_at < day_after_end` for date ranges
- external non-test account
- `customer_impact = 1`
- `status <> 'canceled'`
- not duplicate: `is_duplicate = 0 AND duplicate_of IS NULL`
- defect category set above

Excluded counts in defect rollups are independent counts over the product/window candidate set, not a sequential funnel:

- duplicate: `is_duplicate = 1 OR duplicate_of IS NOT NULL`
- canceled: `status = 'canceled'`
- internal/test account: `is_internal = 1 OR account_status = 'test'`
- non-customer-impact: `customer_impact = 0`
- non-defect category: category not in the defect set

SLA breach rate counts breached qualified tickets divided by all qualified tickets. Treat unresolved tickets as breached when they are past due; in these historical tasks this is usually:

```sql
COALESCE(closed_at, '9999-12-31') > sla_due_at
```

Median close hours is computed only for qualified tickets with `closed_at IS NOT NULL`, using `(julianday(closed_at) - julianday(created_at)) * 24.0`; for an even count, average the two middle durations.

Backlog means qualified defect tickets with `status IN ('open','in_progress')`. Include all severity keys `P1` through `P4`, even when zero. Highest severity priority is `P1`, `P2`, `P3`, `P4`.

Incident follow-up tickets use the incident record as authoritative:

- window: `created_at > resolved_at` and `created_at <= datetime(resolved_at, '+7 days')`
- same product and impacted region, unless region is `GLOBAL`
- external account
- exclude canceled/duplicate and non-customer-impact tickets
- do not add the defect-category filter unless the prompt asks for defects

## Correction and Simulation

For data-quality tasks:

1. Query `data_quality_cases` by the prompt's case id.
2. Require `case_status = 'approved'`, the expected `case_type`, `target_table`, and `field_name`.
3. Parse `target_ids_csv` into an explicit quoted `IN (...)` list. Do not update by broad product/date filters alone.
4. Include guards for current values, target table, approved case existence, and any product constraint from the prompt.
5. Populate `audit_reason` from the case and `audit_updated_at` from the case `created_at`.
6. Run the UPDATE through `/simulate`, then recompute every requested metric from simulated follow-up queries.

Usage product correction pattern:

```sql
UPDATE usage_daily
SET product_id = (SELECT new_value FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved'),
    audit_reason = (SELECT audit_reason FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved')
WHERE usage_id IN (...)
  AND product_id = (SELECT old_value FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved')
  AND EXISTS (
    SELECT 1 FROM data_quality_cases
    WHERE case_id = '<case_id>'
      AND case_status = 'approved'
      AND case_type = 'usage_product_correction'
      AND target_table = 'usage_daily'
      AND field_name = 'product_id'
  );
```

Ticket duplicate correction pattern:

```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = (SELECT new_value FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved'),
    audit_reason = (SELECT audit_reason FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved')
WHERE ticket_id IN (...)
  AND is_duplicate = 0
  AND duplicate_of IS NULL
  AND EXISTS (
    SELECT 1 FROM data_quality_cases
    WHERE case_id = '<case_id>'
      AND case_status = 'approved'
      AND case_type = 'ticket_duplicate_correction'
      AND target_table = 'tickets'
      AND field_name = 'duplicate_of'
  );
```

Return the deterministic correction SQL string exactly as simulated, plus `changed_rows` or the task-specific changed count.

## Output Rules

- Return only the JSON object requested by the template. No markdown, comments, or extra keys.
- Keep key order aligned with the answer template when practical.
- Use JSON numbers for numeric fields. Round compute hours and close durations to 2 decimals; round SLA rates to 4 decimals unless the template says otherwise.
- Always specify deterministic ordering:
  - IDs ascending for ID lists and account breakdowns unless another rule is given.
  - Regions alphabetically.
  - Top compute accounts: compute hours descending, then `account_id` ascending; rank 1-based.
  - Top ticket accounts: ticket count descending, then `account_id` ascending.
  - Backlog notification accounts: backlog count descending, highest severity priority ascending, then `account_id` ascending.
- Sort by unrounded aggregate values, then round for display.
- For timestamp windows, respect exclusive/inclusive wording exactly. For date-only inclusive end dates, prefer a half-open timestamp range ending at the next day.

## Common Mistakes

- Joining `subscriptions` directly and multiplying usage rows; use `EXISTS` or deduplicate first.
- Excluding all `telemetry_v1` usage instead of only overlapping `telemetry_v1` rows.
- Using active account filters for ticket rollups and accidentally dropping churned external customer tickets.
- Treating excluded counts as sequential when the template expects independent reason counts.
- Counting duplicates only by `is_duplicate`; also check `duplicate_of IS NOT NULL`.
- Forgetting to include zero-valued severities.
- Applying a correction without verifying the approved case metadata and target id list.
- Recomputing post-correction metrics on the original database instead of `/simulate` results.
