---
name: scn-022-sql-database-analytics
description: Solve SCN_022 operations analytics tasks against the remote SQLite API, including usage rollups, defect/support rollups, incident exposure summaries, and approved data-quality correction simulations.
---

# SCN_022 SQL Database Analytics

Use this skill for single-task solvers that must return one JSON object from the shared operations analytics SQLite database exposed through the remote HTTP API.

## API Workflow

1. Read the task prompt and `input/payloads/answer_template.json` first. The template defines exact keys, rounding, sorting, and whether corrections are required.
2. Read `environment_access.md` for `GDPEVO_ENV_BASE_URL`. Use only the HTTP API:
   - `GET /` for endpoint instructions.
   - `GET /health`, `GET /schema`, `GET /tables`.
   - `GET /tables/<name>?limit=100&offset=0` for small samples/reference rows.
   - `POST /query` with `{"sql":"SELECT ...","params":[]}` for read-only SQL.
   - `POST /simulate` with `{"script":"UPDATE ...;","queries":[{"sql":"SELECT ...","params":[]}]}` for correction tasks.
3. Inspect schema before querying. Common objects:
   - `accounts`: segment, region, status, `is_internal`.
   - `subscriptions`: product, plan, status, active date range.
   - `usage_daily`: product usage, environment, source system, backfill, audit fields.
   - `tickets`: support tickets, category, impact, duplicate flags, SLA fields, audit fields.
   - `incidents`: authoritative incident windows and impacted region.
   - `data_quality_cases`: approved correction metadata and target IDs.
   - Views `active_customer_accounts`, `production_usage_daily`, `customer_support_tickets` are useful, but use base tables when audit fields or excluded-row counters are needed.
4. Build one candidate CTE for the requested product/date/window, add boolean flags for each exclusion, then derive included metrics and excluded counters from that same CTE. Run detail queries for IDs and aggregate queries to reconcile totals before producing JSON.

## Usage Qualification

For customer production usage metrics, start from `usage_daily` joined to `accounts`.

Default production usage filters:
- Use `activity_date` for usage periods, not `recorded_at`.
- Use inclusive date windows: `activity_date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`.
- Require `environment = 'production'`.
- Exclude backfills with `is_backfill = 0`.
- External active customer accounts are `accounts.is_internal = 0` and `accounts.account_status IN ('active','paused')`.
- Apply requested `product_id`, `region`, and `segment` filters exactly.

Subscription rules:
- When the prompt says active subscriptions or qualified product usage, require an active subscription for that account/product on the usage date with `EXISTS`, not a join:

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

- When the prompt says enterprise accounts, also require `accounts.segment = 'enterprise'`. If it asks for enterprise product usage, require `s.plan_code = 'enterprise'` inside the `EXISTS`.
- Do not join subscriptions directly for eligibility; overlapping subscription rows can duplicate usage.

Telemetry overlap:
- Do not exclude every `telemetry_v1` row.
- Exclude a `telemetry_v1` usage row only when a non-v1 row exists for the same account, product, activity date, production environment, and non-backfill state:

```sql
NOT (
  u.source_system = 'telemetry_v1'
  AND EXISTS (
    SELECT 1
    FROM usage_daily u2
    WHERE u2.account_id = u.account_id
      AND u2.product_id = u.product_id
      AND u2.activity_date = u.activity_date
      AND u2.environment = u.environment
      AND u2.is_backfill = 0
      AND u2.source_system <> 'telemetry_v1'
  )
)
```

- When asked for a telemetry-v1 overlap exclusion counter, count exactly the rows matching the inner overlap condition among otherwise qualified usage candidates.

## Ticket Qualification

For customer-impacting defect/support metrics, start from `tickets` joined to `accounts`.

Default ticket filters:
- Use `date(created_at)` for monthly ticket windows unless the prompt gives timestamp boundaries.
- Apply `product_id` exactly.
- External customer accounts: `accounts.is_internal = 0` and `accounts.account_status <> 'test'`. Add active-status filters only if the prompt asks for active accounts.
- Exclude duplicates with both `is_duplicate = 0` and `duplicate_of IS NULL`.
- Exclude canceled tickets with `status <> 'canceled'`.
- Customer-impacting means `customer_impact = 1`.
- Defect categories are `('bug','outage','performance','data_loss')`. Do not apply this category filter to generic incident follow-up support signals unless the prompt says defect.

Excluded counters are usually independent counts over the same product/date candidate set, not sequential leftovers:
- duplicate: `is_duplicate = 1 OR duplicate_of IS NOT NULL`
- canceled: `status = 'canceled'`
- internal/test account: `is_internal = 1 OR account_status = 'test'`
- non-customer impact: `customer_impact = 0`
- non-defect category: `category NOT IN ('bug','outage','performance','data_loss')`

SLA and backlog:
- SLA breach: closed tickets breach when `closed_at > sla_due_at`; open/in-progress tickets with `closed_at IS NULL` count as breached unless an explicit as-of rule says otherwise.
- SLA breach rate is `breach_count * 1.0 / qualified_count`, rounded to the requested precision.
- Backlog means `status IN ('open','in_progress')`.
- Severity priority is P1, P2, P3, P4. Include zero-valued severity keys when the template requires them.
- Median close hours uses closed qualified tickets only: `(julianday(closed_at) - julianday(created_at)) * 24`, sorted numerically, averaging the middle two for even counts.

## Incident Exposure

Use the incident row as authoritative for `product_id`, `started_at`, `resolved_at`, `severity`, and `impacted_region`.

Usage exposure:
- Use usage dates from `date(started_at)` through `date(resolved_at)` inclusive unless the template asks for timestamp-level logic.
- Apply production usage filters, telemetry overlap exclusion, and active product subscription eligibility.
- If `impacted_region <> 'GLOBAL'`, require `accounts.region = impacted_region`; for `GLOBAL`, include all regions.

Post-incident support signals:
- Seven-day follow-up window is `created_at > resolved_at` and `created_at <= datetime(resolved_at, '+7 days')`.
- Use external customer accounts in the impacted region, excluding canceled and duplicate tickets.
- Apply `customer_impact = 1` for customer-impacting signals. Apply defect category filtering only when requested.

## Approved Correction Workflow

Never run real updates through `/query`. For correction tasks:

1. Query `data_quality_cases` for the named case and verify:
   - `case_status = 'approved'`
   - expected `case_type`
   - expected `target_table`
   - expected `field_name`
   - target IDs in `target_ids_csv`
2. Query target rows before writing SQL. Confirm current values match `old_value`, and count the intended rows.
3. Create a single safe `UPDATE` script that:
   - restricts to the exact target IDs from the approved case,
   - restricts to the expected old value or duplicate state,
   - uses `EXISTS` against `data_quality_cases` for the approved case/type/table,
   - writes `audit_reason` and `audit_updated_at` from the case metadata,
   - changes no rows when the case is draft/rejected or the row state is already changed.
4. Send the script to `/simulate` with follow-up read-only metric queries. Use `changed_rows` from the response for the changed count.
5. Return the exact correction SQL string in JSON and the metrics recomputed from the simulated database results.

The patterns below use placeholders for readability. The final returned `correction_sql` must be runnable SQLite with the actual case ID and target IDs from `data_quality_cases`.

Usage product correction pattern:

```sql
UPDATE usage_daily
SET product_id = (SELECT new_value FROM data_quality_cases WHERE case_id = :case_id AND case_status = 'approved'),
    audit_reason = (SELECT audit_reason FROM data_quality_cases WHERE case_id = :case_id AND case_status = 'approved'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = :case_id AND case_status = 'approved')
WHERE usage_id IN (...)
  AND product_id = (SELECT old_value FROM data_quality_cases WHERE case_id = :case_id AND case_status = 'approved')
  AND EXISTS (
    SELECT 1 FROM data_quality_cases
    WHERE case_id = :case_id
      AND case_status = 'approved'
      AND case_type = 'usage_product_correction'
      AND target_table = 'usage_daily'
  );
```

Ticket duplicate correction pattern:

```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = (SELECT new_value FROM data_quality_cases WHERE case_id = :case_id AND case_status = 'approved'),
    audit_reason = (SELECT audit_reason FROM data_quality_cases WHERE case_id = :case_id AND case_status = 'approved'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = :case_id AND case_status = 'approved')
WHERE ticket_id IN (...)
  AND is_duplicate = 0
  AND duplicate_of IS NULL
  AND EXISTS (
    SELECT 1 FROM data_quality_cases
    WHERE case_id = :case_id
      AND case_status = 'approved'
      AND case_type = 'ticket_duplicate_correction'
      AND target_table = 'tickets'
  );
```

## Output Habits

- Return only the JSON object requested by the template. No prose, Markdown, or extra keys.
- Use JSON numbers for counts and metrics, not strings.
- Round only final numeric values to the requested precision: compute hours usually 2 decimals; rates usually 4 decimals.
- Preserve required object keys even when values are zero or arrays are empty.
- Deterministic ordering:
  - IDs ascending when listing IDs or account breakdowns unless template says otherwise.
  - Regions alphabetically.
  - Top accounts by descending requested metric, then ascending `account_id`.
  - Account notification lists by the template's stated metric, then severity priority P1-P4 when applicable, then `account_id`.
- For ties not specified by the template, use ascending stable identifiers (`account_id`, `ticket_id`, `usage_id`).

## Common Mistakes

- Excluding all `telemetry_v1` usage instead of only overlapping v1 rows.
- Joining to `subscriptions` and accidentally multiplying usage rows; use `EXISTS`.
- Counting exclusions sequentially when the template expects independent excluded counts.
- Using `recorded_at` instead of `activity_date` for usage periods.
- Treating paused customer accounts as non-customers; `active_customer_accounts` includes active and paused external accounts.
- Applying defect category filters to incident follow-up tickets when the prompt asks for broader support signals.
- Counting duplicate tickets using only one duplicate column; check both `is_duplicate` and `duplicate_of`.
- Building correction SQL from assumptions instead of the approved `data_quality_cases` row.
- Reporting pre-fix metrics after a correction task; recompute metrics from `/simulate` results.
