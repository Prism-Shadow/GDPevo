---
name: sql-database-analytics
description: Solve SQL database analytics tasks through a constrained remote operations analytics API. Use when Codex must inspect a SQLite-like schema, compute usage/ticket/incident rollups, apply approved data-quality corrections via simulation, and return exact JSON from a prompt/template.
---

# SQL Database Analytics

## Workflow

1. Read the task prompt and answer template first. Treat the template as the output contract: exact keys, numeric precision, arrays, and ordering.
2. Read the local environment access file for the API base URL and allowed endpoints. Use only the remote API; do not look for local database or environment source.
3. Discover before querying:
   - `GET /` for endpoint shape.
   - `GET /schema` for tables, views, columns, constraints, and view definitions.
   - `GET /tables` and small `GET /tables/<name>` samples for values.
   - Query `products`, `metric_notes`, relevant `incidents`, and `data_quality_cases` rows explicitly.
4. Build SQL with CTEs: `candidate` -> `flags` -> `qualified` -> aggregates. Keep diagnostics for row counts and exclusion counts so mistakes are visible.
5. Use `EXISTS` for subscription eligibility instead of joining subscriptions directly; accounts can have multiple subscriptions and joins can double-count usage or tickets.
6. Return only the JSON object requested. Do not include explanation, SQL diagnostics, or extra keys.

## Shared Business Rules

Use the prompt wording to choose scope, then apply these defaults unless contradicted by the template or notes.

- External customer accounts: `accounts.is_internal = 0`, `segment <> 'internal'`, and `account_status IN ('active','paused')`. Exclude test, internal, churned, and inactive accounts from customer metrics.
- Product scope: filter by `products.product_id`, not product display name.
- Product-specific "enterprise customer/account" usually means an active subscription for that same product with `plan_code = 'enterprise'`, active on the usage/ticket date. If the prompt clearly asks for account segment rather than product-plan eligibility, use `accounts.segment = 'enterprise'`.
- Active subscription on a date: `subscription_status IN ('active','paused')`, `start_date <= metric_date`, and `(end_date IS NULL OR end_date >= metric_date)`.
- Usage qualification: product/date scope, external active customer account, `environment = 'production'`, `is_backfill = 0`, and active product subscription when requested.
- Telemetry migration de-dupe: exclude a `telemetry_v1` usage row only when a non-v1 row exists in the already-filtered candidate set for the same `(account_id, product_id, activity_date, environment)`. Do not exclude all v1 rows blindly.
- Usage exclusion counters, when requested, are raw counts over the candidate set for each reason, not mutually exclusive waterfall counts.
- Defect tickets: categories `bug`, `outage`, `performance`, and `data_loss`; `customer_impact = 1`; `is_duplicate = 0`; `status <> 'canceled'`; external customer account.
- Ticket date windows using dates are inclusive with `date(created_at) BETWEEN start AND end`. Timestamp windows keep exact boundary semantics from the template, e.g. `created_at > resolved_at` and `created_at <= datetime(resolved_at, '+7 days')`.
- SLA breach for a period rollup: count qualified tickets where `COALESCE(closed_at, period_end_timestamp) > sla_due_at`; compute the rate over the qualified ticket denominator and round to 4 decimals.
- Median close hours: compute only over closed qualified tickets with `(julianday(closed_at) - julianday(created_at)) * 24`, ordered numerically, rounded to 2 decimals.
- Incident exposure: use the incident row as authoritative for product, timestamps, severity, and impacted region. Daily usage exposure covers `date(started_at)` through `date(resolved_at)`. For non-GLOBAL incidents, filter accounts to `impacted_region`.
- Incident follow-up support signals: use the seven-day timestamp window after resolution, same product and impacted region, external customer accounts, not canceled/duplicate, and customer-impacting. Do not add defect-category filters unless asked.
- Backlog metrics: first build the qualified period ticket set. For backlog as of period end, include tickets with `closed_at IS NULL OR closed_at > period_end_timestamp`, not merely tickets whose current status is `open` or `in_progress`.

## Safe Correction And Simulation

1. Query the exact `data_quality_cases` row. Require `case_status = 'approved'`, expected `case_type`, `target_table`, `field_name`, `old_value`, `new_value`, and `target_ids_csv`.
2. Write a narrow SQLite update that:
   - Updates only IDs listed in the approved case.
   - Checks the expected old value or current duplicate state in `WHERE`.
   - Populates `audit_reason` from the case and a deterministic `audit_updated_at` such as the case `created_at`.
   - For usage product corrections, changes only `usage_daily.product_id`.
   - For ticket duplicate corrections, sets both `tickets.is_duplicate = 1` and `tickets.duplicate_of = new_value`.
3. Run correction tasks with `POST /simulate`, passing the update script and read-only follow-up queries. Use `changed_rows` or `SELECT changes()` to report changed counts.
4. Recompute all requested metrics inside the simulated database state. Do not use pre-fix query results except for diagnostics.

## Output Habits

- Preserve the answer template shape exactly. Use numbers for numeric fields, not strings.
- Round compute-hour and duration values to 2 decimals; rates to 4 decimals.
- Include zero-valued severity keys (`P1`, `P2`, `P3`, `P4`) when the schema asks for a severity object.
- Deterministic ordering:
  - IDs: ascending lexical order.
  - Top lists: metric descending, then `account_id` ascending unless the template says otherwise.
  - Regions: alphabetic.
  - Account breakdowns: `account_id` ascending unless the template gives a ranking rule.
  - Backlog notify lists: backlog count descending, highest severity priority `P1` to `P4`, then `account_id` ascending.
- Use `COUNT(DISTINCT account_id)` for account counts and plain `COUNT(*)` for row/ticket counts.

## Common Mistakes

- Treating product-plan "enterprise" as account segment, or vice versa, without checking wording and subscriptions.
- Double-counting because of direct subscription joins.
- Excluding every `telemetry_v1` row instead of only overlapping v1 rows.
- Reporting disjoint exclusion waterfall counts when the template expects raw reason counts.
- Using current ticket status for backlog instead of an as-of period-end definition.
- Ignoring exact timestamp inclusivity for incident follow-up windows.
- Forgetting `is_duplicate`, `duplicate_of`, `status = 'canceled'`, internal/test accounts, or non-customer-impact filters on ticket work.
- Returning diagnostics, SQL, or extra prose outside the requested JSON.
