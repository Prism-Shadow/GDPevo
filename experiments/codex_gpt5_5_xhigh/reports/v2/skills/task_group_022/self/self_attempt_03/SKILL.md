---
name: sql-database-analytics
description: Solve SCN_022 operations analytics tasks against the remote SQLite API, including usage rollups, defect/support metrics, incident exposure, and approved data-quality correction simulations.
---

# SQL Database Analytics

Use this skill for operations analytics tasks that provide a prompt, an answer template, and a remote API base URL for a SQLite-backed database.

## API Workflow

1. Read the prompt and answer template first. Treat the template as the exact output contract.
2. Use only the remote API:
   - `GET /` for endpoint instructions.
   - `GET /schema` and `GET /tables` for object discovery.
   - `GET /tables/<name>?limit=...&offset=...` for small samples.
   - `POST /query` with `{"sql":"SELECT ...","params":[]}` for read-only SQL.
   - `POST /simulate` with `{"script":"UPDATE ...;","queries":[{"name":"q","sql":"SELECT ...","params":[]}]}` for temporary-copy corrections.
3. Query `metric_notes`, `products`, and any task-specific record tables (`incidents`, `data_quality_cases`) before writing final SQL.
4. Build one qualifying CTE and reuse it for all totals, breakdowns, exclusions, and rankings. Run small audit queries that count candidates at each exclusion step.

## Core Tables And Joins

- `accounts`: external customer filter is `is_internal = 0` and `account_status IN ('active','paused')`. `segment` distinguishes enterprise/commercial/startup/internal. `region` is `NA`, `EMEA`, `APAC`, or `LATAM`.
- `products`: product IDs are uppercase identifiers such as `ATLASDB` and `HELIOSYNC`; resolve from product names instead of guessing.
- `usage_daily`: one account/product/date/environment/source observation. Use this base table when exclusions must be counted.
- `tickets`: support tickets with status, severity, category, customer impact, duplicate fields, SLA fields, and audit fields.
- `subscriptions`: use `EXISTS`, not a plain join, when checking active subscriptions so duplicate subscription rows do not multiply usage.
- Views (`active_customer_accounts`, `production_usage_daily`, `customer_support_tickets`) are useful for quick checks, but base tables are safer when excluded counts are required.

## Usage Metrics

Default qualified production usage:

```sql
WITH overlap_v1 AS (
  SELECT u.usage_id
  FROM usage_daily u
  WHERE u.source_system = 'telemetry_v1'
    AND EXISTS (
      SELECT 1
      FROM usage_daily newer
      WHERE newer.account_id = u.account_id
        AND newer.product_id = u.product_id
        AND newer.activity_date = u.activity_date
        AND newer.environment = u.environment
        AND newer.source_system <> 'telemetry_v1'
    )
),
qualified_usage AS (
  SELECT u.*, a.account_name, a.segment, a.region
  FROM usage_daily u
  JOIN accounts a ON a.account_id = u.account_id
  WHERE u.product_id = :product_id
    AND u.activity_date BETWEEN :start_date AND :end_date
    AND u.environment = 'production'
    AND u.is_backfill = 0
    AND a.is_internal = 0
    AND a.account_status IN ('active','paused')
    AND NOT EXISTS (SELECT 1 FROM overlap_v1 ov WHERE ov.usage_id = u.usage_id)
)
SELECT * FROM qualified_usage;
```

Add filters exactly when requested:

- Enterprise customer accounts usually means `a.segment = 'enterprise'`; do not confuse it with `subscriptions.plan_code = 'enterprise'` unless the prompt says plan.
- Region requests use `a.region = :region`. For incident rows, if `impacted_region = 'GLOBAL'`, do not region-filter.
- Active subscription exposure uses:

```sql
AND EXISTS (
  SELECT 1
  FROM subscriptions s
  WHERE s.account_id = u.account_id
    AND s.product_id = u.product_id
    AND s.subscription_status = 'active'
    AND s.start_date <= u.activity_date
    AND (s.end_date IS NULL OR s.end_date >= u.activity_date)
)
```

Count `telemetry_v1` overlap exclusions from the same candidate scope used by the metric, before removing those rows. Count backfill, non-production, inactive/internal accounts, and missing active subscriptions from clearly named candidate CTEs so the meaning of each exclusion is auditable.

## Ticket And Defect Metrics

Candidate tickets are normally selected by product and timestamp window. For date prompts, use a half-open timestamp range:

```sql
t.created_at >= :start_date || ' 00:00:00'
AND t.created_at < date(:end_date, '+1 day')
```

Customer-impacting defect qualification:

- External customer account: `accounts.is_internal = 0` and `account_status IN ('active','paused')`.
- Defect categories: `category IN ('bug','outage','performance','data_loss')`.
- Customer impact: `customer_impact = 1`.
- Exclude canceled tickets: `status <> 'canceled'`.
- Exclude duplicates: `is_duplicate = 0` (also inspect `duplicate_of` after corrections).

SLA and duration habits:

- SLA breach for a closed ticket: `closed_at > sla_due_at`.
- For open/in-progress period rollups, use the period end timestamp as the as-of time unless the prompt gives another as-of.
- Median close hours is for closed qualified tickets only: `24.0 * (julianday(closed_at) - julianday(created_at))`.
- For backlog tasks, backlog means qualified tickets with `status IN ('open','in_progress')` unless the prompt defines it differently.

Excluded counts may be independent diagnostics rather than mutually exclusive buckets. Do not force them to sum to total excluded unless the template requires that.

## Incident Exposure

1. Load the incident row by ID; use its `product_id`, `started_at`, `resolved_at`, `impacted_region`, and `severity`.
2. Usage exposure is daily-grain: `activity_date BETWEEN date(started_at) AND date(resolved_at)`.
3. Apply production usage qualification, active external accounts, region/global logic, active subscription check, `is_backfill = 0`, and telemetry-v1 overlap exclusion.
4. Follow-up support window is usually `created_at > resolved_at AND created_at <= datetime(resolved_at, '+7 days')`.
5. For incident follow-up support signals, filter product and impacted external-customer region, exclude canceled/duplicate and non-customer-impact tickets. Do not apply defect-category filtering unless the prompt asks for defects.

## Safe Correction And Simulation

Approved data-quality corrections come from `data_quality_cases`. Never apply an update through `/query`; only simulate.

Workflow:

1. Query the case by prompt `case_id`.
2. Require `case_status = 'approved'`, expected `target_table`, expected `case_type`, expected `field_name`, and matching `old_value`/`new_value`.
3. Parse `target_ids_csv` into an explicit ID list for the output SQL.
4. Build a deterministic SQLite update that:
   - Touches only target IDs from the approved case.
   - Checks the current old value before changing it.
   - Writes the new value.
   - Populates `audit_reason` from the case and `audit_updated_at` with the case `created_at` or another deterministic case timestamp.
5. POST the same SQL string to `/simulate` with follow-up metric queries. Use `changed_rows` from the simulation response for changed-row counts.

Usage product correction pattern:

```sql
UPDATE usage_daily
SET product_id = '<new_value>',
    audit_reason = '<audit_reason>',
    audit_updated_at = '<case_created_at>'
WHERE usage_id IN (<quoted_target_ids>)
  AND product_id = '<old_value>'
  AND EXISTS (
    SELECT 1
    FROM data_quality_cases
    WHERE case_id = '<case_id>'
      AND case_status = 'approved'
      AND case_type = 'usage_product_correction'
      AND target_table = 'usage_daily'
      AND field_name = 'product_id'
      AND old_value = '<old_value>'
      AND new_value = '<new_value>'
  );
```

Ticket duplicate correction pattern:

```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = '<new_value>',
    audit_reason = '<audit_reason>',
    audit_updated_at = '<case_created_at>'
WHERE ticket_id IN (<quoted_target_ids>)
  AND is_duplicate = 0
  AND (duplicate_of IS NULL OR duplicate_of = '')
  AND EXISTS (
    SELECT 1
    FROM data_quality_cases
    WHERE case_id = '<case_id>'
      AND case_status = 'approved'
      AND case_type = 'ticket_duplicate_correction'
      AND target_table = 'tickets'
      AND field_name = 'duplicate_of'
      AND new_value = '<new_value>'
  );
```

After simulation, recompute all requested metrics inside the simulated copy. If the task asks for a `correction_sql` string, return exactly the SQL you simulated.

## Output Habits

- Return only the JSON object. No markdown, comments, or extra text.
- Preserve every required key from the template, including zero-valued severity keys and empty arrays.
- Use JSON numbers for numeric values. Round compute hours and durations to 2 decimals, SLA rates to 4 decimals, or whatever precision the template states.
- Use `COALESCE` so empty aggregates become `0`, not `null`.
- Use deterministic ordering:
  - Explicit template ordering always wins.
  - Top accounts: primary metric descending, then `account_id` ascending; include rank if requested.
  - Account breakdowns and ID lists: `account_id` or ID ascending.
  - Regions: alphabetical.
  - Severity objects: keys `P1`, `P2`, `P3`, `P4` in that order.
  - Notification/backlog lists: backlog count descending, severity priority `P1` to `P4`, then `account_id` ascending.
- Use `EXISTS` for eligibility checks and pre-aggregate before joining when a table can have multiple matching rows.

## Common Mistakes

- Using anything beyond the prompt, template, and remote API instead of deriving the answer through SQL.
- Running updates through `/query` or using nondeterministic timestamps like `datetime('now')` in correction SQL.
- Counting staging/sandbox/internal usage as production exposure.
- Forgetting to exclude backfills and overlapping `telemetry_v1` rows.
- Treating `enterprise` segment and subscription `plan_code` as interchangeable.
- Multiplying usage rows by joining directly to multiple active subscriptions.
- Dropping `internal_test` tickets via a view before computing excluded category counts.
- Applying defect-category filters to incident follow-up tickets when the prompt only asks for support signals.
- Using inclusive timestamp `BETWEEN` for month-end ticket windows; prefer half-open ranges.
- Omitting zero severity keys, returning strings for numbers, or leaving arrays unordered.
