---
name: scn-022-sql-database-analytics
description: Solve SCN_022 operations analytics tasks that require querying a shared SQLite database through the remote HTTP API, producing JSON rollups for usage, tickets, incidents, and approved data-quality corrections. Use when prompts mention AtlasDB, HelioSync, usage_daily, support tickets, incidents, data_quality_cases, correction_sql, telemetry overlap, qualified accounts, defect rollups, backlog, or operations analytics API.
---

# SCN_022 SQL Database Analytics

## API workflow

Use the task-provided API base URL. Start with:

```bash
curl -sS "$BASE/"
curl -sS "$BASE/schema"
curl -sS "$BASE/tables"
curl -sS "$BASE/tables/metric_notes?limit=100&offset=0"
```

Run read-only SQL with:

```bash
curl -sS -X POST "$BASE/query" \
  -H 'Content-Type: application/json' \
  --data-binary '{"sql":"SELECT ...","params":[]}'
```

Use `POST /simulate` for correction tasks. Its shape is:

```json
{
  "script": "UPDATE ...;",
  "queries": [
    {"name": "check", "sql": "SELECT ..."}
  ]
}
```

The main schema objects are `accounts`, `products`, `subscriptions`, `usage_daily`, `tickets`, `incidents`, `data_quality_cases`, and `metric_notes`. Helper views are useful for orientation only: `production_usage_daily` still includes backfills and telemetry overlaps; `customer_support_tickets` only removes `internal_test` category; `active_customer_accounts` means external accounts with `account_status IN ('active','paused')`.

Build one CTE pipeline per answer:

1. Define the broad candidate population from the prompt's product/date/region scope.
2. Add boolean flags for each business exclusion requested by the template.
3. Define `qualified` by applying all inclusion rules.
4. Aggregate from `qualified`, and compute exclusion counters from the same candidate scope.
5. Cross-check totals against detail rows before writing final JSON.

## Core business filters

Product names map to IDs such as `ATLASDB` and `HELIOSYNC`; verify in `products`.

For usage metrics:

- Use `usage_daily.activity_date` for date windows. Calendar ranges are inclusive: `activity_date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`.
- Qualified customer usage normally requires `environment = 'production'`, `is_backfill = 0`, and an external customer account.
- External active customer accounts are `accounts.is_internal = 0`, `accounts.segment <> 'internal'`, and `accounts.account_status IN ('active','paused')`.
- Add `accounts.segment = 'enterprise'` only when the prompt asks for enterprise accounts. Add `accounts.region = ...` only when requested or implied by an incident.
- Add active product subscription filtering only when the prompt says active subscription, entitlement, subscribed customer, or incident exposure:

```sql
EXISTS (
  SELECT 1
  FROM subscriptions s
  WHERE s.account_id = u.account_id
    AND s.product_id = u.product_id
    AND s.start_date <= u.activity_date
    AND (s.end_date IS NULL OR s.end_date >= u.activity_date)
    AND s.subscription_status IN ('active','paused')
)
```

Use `EXISTS`, not a plain join, because accounts can have multiple overlapping subscriptions and a join can duplicate usage rows.

For telemetry overlap:

- Exclude only `telemetry_v1` rows that overlap a `telemetry_v2` row for the same `account_id`, `product_id`, and `activity_date` in production non-backfill data.
- Keep the v2 row. Count excluded overlap rows before dropping them if the output asks for a telemetry-v1 counter.

```sql
u.source_system = 'telemetry_v1'
AND EXISTS (
  SELECT 1
  FROM usage_daily x
  WHERE x.account_id = u.account_id
    AND x.product_id = u.product_id
    AND x.activity_date = u.activity_date
    AND x.environment = 'production'
    AND x.is_backfill = 0
    AND x.source_system = 'telemetry_v2'
)
```

For support defect metrics:

- Use `tickets.created_at` for ticket windows. For month/date prompts, use half-open timestamp bounds: `created_at >= '<start-date>' AND created_at < '<day-after-end-date>'`.
- Defect categories are `bug`, `outage`, `performance`, and `data_loss`.
- Customer-impacting defect tickets require `customer_impact = 1`, defect category, `status <> 'canceled'`, `is_duplicate = 0`, and an external non-test account.
- For ticket account exclusions, follow the template wording. `internal_or_test_account` usually means `a.is_internal = 1 OR a.segment = 'internal' OR a.account_status = 'test'`; do not exclude churned accounts unless the prompt says active accounts.
- Backlog means unresolved tickets, normally `status IN ('open','in_progress')`, after all defect/customer/duplicate/canceled filters.
- P1/P2 open counts use `severity IN ('P1','P2') AND status IN ('open','in_progress')`.
- SLA breach is usually `COALESCE(closed_at, <as_of>) > sla_due_at`; use the period end or requested follow-up end as `<as_of>` when no current/as-of timestamp is given.

For incidents:

- Query the authoritative incident row by `incident_id`.
- Use `date(started_at)` through `date(resolved_at)` inclusive for daily usage exposure.
- Apply impacted region unless it is `GLOBAL`.
- Follow-up ticket windows are usually `created_at > resolved_at AND created_at <= datetime(resolved_at, '+7 days')`.
- For exposure, combine production non-backfill usage, external active accounts, active product subscription during `activity_date`, and telemetry-v1 overlap exclusion.
- For follow-up support signals, filter to external customer accounts in the impacted region, same product unless the prompt says otherwise, non-canceled, non-duplicate, and customer-impacting tickets.

For exclusion counts:

- Unless the template explicitly says exclusions are mutually exclusive, count each named exclusion independently over the same broad candidate population.
- If the template includes `candidate_rows`, report the broad product/date/region rows before quality filters.
- Do not force exclusion counters to add up to the number of discarded rows unless the prompt requests a partition.

## Correction and simulation workflow

For every correction task:

1. Query `data_quality_cases` by the requested `case_id`.
2. Proceed only when `case_status = 'approved'`, `target_table`, `field_name`, `old_value`, and `new_value` match the prompt.
3. Expand `target_ids_csv` into the exact target ID list. Inspect target rows before writing SQL.
4. Write a narrow, idempotent update that:
   - Filters by the exact target IDs.
   - Checks the expected old value.
   - Verifies the approved case with `EXISTS`.
   - Sets `audit_reason` from the case and populates `audit_updated_at`.
5. Run it through `/simulate`; use the simulated database results for all "after fix" metrics.
6. Report the API `changed_rows` count or a simulated follow-up count, not a pre-update guess.

Usage product correction pattern:

```sql
UPDATE usage_daily
SET product_id = '<new_value>',
    audit_reason = '<audit_reason>',
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = '<case_id>')
WHERE usage_id IN ('...')
  AND product_id = '<old_value>'
  AND EXISTS (
    SELECT 1 FROM data_quality_cases c
    WHERE c.case_id = '<case_id>'
      AND c.case_status = 'approved'
      AND c.target_table = 'usage_daily'
      AND c.field_name = 'product_id'
  );
```

Ticket duplicate correction pattern:

```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = '<new_value>',
    audit_reason = '<audit_reason>',
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = '<case_id>')
WHERE ticket_id IN ('...')
  AND is_duplicate = 0
  AND (duplicate_of IS NULL OR duplicate_of = '')
  AND EXISTS (
    SELECT 1 FROM data_quality_cases c
    WHERE c.case_id = '<case_id>'
      AND c.case_status = 'approved'
      AND c.target_table = 'tickets'
      AND c.field_name = 'duplicate_of'
  );
```

Never apply draft or rejected cases. Never update rows beyond the approved ID list. After a duplicate correction, recompute ticket metrics with `is_duplicate = 0` so corrected rows drop out.

## Aggregation patterns

Use stable SQL ordering in every detail query:

- Top usage accounts: `ORDER BY compute_hours DESC, account_id ASC`.
- Top ticket accounts: `ORDER BY ticket_count DESC, account_id ASC`.
- Account breakdowns: `ORDER BY account_id ASC`.
- Regional breakdowns: `ORDER BY region ASC`.
- Severity priority: `CASE severity WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 WHEN 'P4' THEN 4 END`.
- Accounts to notify for backlog: descending backlog count, ascending highest-severity priority, then ascending `account_id`.

Use `COUNT(DISTINCT account_id)` for account counts. Use `ROUND(SUM(...), 2)` for compute hours and `ROUND(1.0 * numerator / NULLIF(denominator,0), 4)` for rates. Do not round intermediate row-level values before summing.

Median close hours pattern:

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

For JSON objects that must include all severities, left join against an inline severity list so zero-valued `P1`, `P2`, `P3`, and `P4` keys are present.

## Output habits

Return exactly one JSON object matching the template. Keep numeric fields as JSON numbers, not strings. Preserve requested key names and nested shapes. Use deterministic array ordering even when the template only implies it. Include empty arrays or zero-valued severity keys when required by the schema.

Before final output, verify:

- Detail rows sum to reported totals.
- `qualified_*_count` matches the number of rows after all filters.
- Top account rows are consistent with account breakdown rows.
- Exclusion counts use the same product/date/region candidate scope as the qualified metric.
- Simulated "after fix" metrics were computed in `/simulate`, not from the unmodified database.

## Common mistakes

- Using helper views alone and forgetting backfill, account status, subscription, or telemetry overlap rules.
- Joining `subscriptions` directly and duplicating rows.
- Treating every "enterprise" task as subscription-plan enterprise; usually it is `accounts.segment = 'enterprise'` unless the prompt asks for subscription/plan entitlement.
- Requiring active subscriptions for ordinary usage rollups when the prompt only asks for enterprise customer accounts.
- Excluding churned ticket accounts when the output asks only for internal/test-account exclusion.
- Counting telemetry-v1 overlap after the v1 rows have already been filtered out.
- Using `BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'` on timestamp fields, which misses most of the end date.
- Applying correction SQL through `/query` or applying draft/rejected data-quality cases.
- Omitting `is_duplicate = 1` when marking duplicate tickets.
- Returning rows in database-default order or rounding totals inconsistently with detail rows.
