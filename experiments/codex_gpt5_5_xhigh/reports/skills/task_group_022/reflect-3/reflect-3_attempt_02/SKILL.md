---
name: sql-database-analytics
description: Solve SQL database analytics tasks through a remote HTTP API, including operations usage rollups, customer-impacting defect metrics, incident exposure summaries, active-subscription filtering, and approved data-quality correction simulations. Use when Codex must inspect staged prompts/templates, discover a live SQLite-like schema, query via API endpoints, and return deterministic JSON analytics.
---

# SQL Database Analytics

## Core Workflow

1. Read the task prompt and answer template first. Treat the template as the output contract: exact keys, numeric precision, array ordering, required zero values, and date/window semantics.
2. Discover the API and schema before querying:
   - Call the root or health endpoint for API shape.
   - Fetch `/schema` and `/tables`.
   - Query reference tables such as products, metric notes, incidents, data-quality cases, and small samples of fact tables.
3. Build SQL with named CTEs for each layer: candidates, exclusions, qualified rows, aggregates, and final ordering. Keep diagnostic queries separate from final answer queries.
4. Prefer `EXISTS` for subscription qualification. Direct joins to `subscriptions` can duplicate fact rows when an account has multiple subscriptions for the same product.
5. For date columns stored as `YYYY-MM-DD`, use inclusive date predicates. For timestamp columns, use half-open month windows (`>= start` and `< next_month`) or explicit exclusive/inclusive windows from the prompt.
6. Recompute final aggregates from the same qualified CTE used for detail arrays. Do not mix totals from one filter set with breakdowns from another.

## Business Filters

**Usage rows**

- Start from raw `usage_daily` when exclusion counts or audit fields matter; views can hide necessary fields.
- Qualified usage usually requires: requested `product_id`, requested `activity_date` range, `environment = 'production'`, `is_backfill = 0`, external customer account, and requested region/segment.
- Treat active customer usage accounts as `is_internal = 0` and `account_status IN ('active','paused')` unless the prompt explicitly broadens the population.
- For active subscription exposure, require an `EXISTS` subscription with matching account/product, active status, `start_date <= activity_date`, and `end_date IS NULL OR end_date >= activity_date`. Use `plan_code = 'enterprise'` only when the prompt asks for enterprise plans/subscriptions; use account `segment = 'enterprise'` when it asks for enterprise accounts.
- Telemetry v1 overlap means a `telemetry_v1` row with another source for the same account/product/date/environment. Count and exclude only those overlap rows unless the prompt explicitly says to drop all telemetry v1.
- Count usage exclusions independently from the candidate set when the template has separate exclusion fields: non-production, backfill, internal/inactive account, missing active subscription, and telemetry-v1 overlap.

**Support tickets**

- Customer-impacting defect categories are `bug`, `outage`, `performance`, and `data_loss`.
- Qualified defect tickets usually require: requested product/date window, `customer_impact = 1`, `status <> 'canceled'`, `is_duplicate = 0`, external/non-test account, and a defect category.
- For support rollups, external customer accounts are non-internal and non-test; do not drop churned accounts unless the prompt or an exclusion bucket says inactive accounts are excluded.
- Count duplicate, canceled, internal/test, non-customer-impact, and non-defect exclusions independently unless the prompt explicitly asks for mutually exclusive reasons.
- SLA breach: resolved tickets breach when `closed_at > sla_due_at`; unresolved open/in-progress tickets breach when their due time has passed relative to the task/as-of time.
- Median close hours uses only closed qualified tickets: `(julianday(closed_at) - julianday(created_at)) * 24`.
- Backlog means unresolved qualified tickets (`open` or `in_progress`). Include all severity keys `P1` through `P4`, even when zero.

**Incidents**

- Use the incident row as authoritative for product, started/resolved timestamps, severity, and impacted region.
- For usage exposure, use incident-window dates inclusive (`date(started_at)` through `date(resolved_at)`), then apply production, backfill, external active account, active subscription, and telemetry-overlap filters.
- For follow-up tickets, use the requested post-resolution window exactly, commonly `created_at > resolved_at` and `created_at <= datetime(resolved_at, '+7 days')`.
- Tie follow-up support signals to the incident product and impacted region unless the prompt clearly requests all products.

## Safe Correction And Simulation

1. Query the requested `data_quality_cases` row. Proceed only if it is approved and its target table, field, old value, new value, and target IDs match the prompt.
2. Write correction SQL as a guarded update:
   - Restrict to the case target IDs.
   - Require the current old value where applicable.
   - Require an `EXISTS` approved-case check.
   - Populate audit fields (`audit_reason` and a deterministic `audit_updated_at`, usually the case timestamp).
3. For usage product corrections, update `usage_daily.product_id` and audit fields.
4. For ticket duplicate corrections, set `tickets.is_duplicate = 1`, `duplicate_of = case.new_value`, and audit fields.
5. Use the API simulation endpoint with the correction script and follow-up read queries. Report the simulated changed-row count and recompute all requested metrics from the simulated database state.
6. Never manually add correction deltas to pre-fix totals when a simulated recomputation is possible.

## Output Habits

- Return only the JSON object requested by the template.
- Preserve exact key names and nesting. Use JSON numbers, not strings, for counts, totals, and rates.
- Round compute-hour values to 2 decimals and ratio/rate values to 4 decimals unless the template says otherwise.
- Use deterministic ordering:
  - IDs ascending for explicit ID lists and account breakdowns.
  - Rankings by descending metric, then ascending ID for ties.
  - Regions alphabetically.
  - Severities in `P1`, `P2`, `P3`, `P4` order.
- Include zero-valued severity buckets and exclusion counters when required.
- For top-N arrays, include exactly the requested N; if no N is specified, include the full qualified ranking only when the template implies a complete breakdown.

## Common Mistakes

- Duplicating usage rows by joining subscriptions directly instead of using `EXISTS`.
- Filtering timestamp months with `BETWEEN 'YYYY-MM-01' AND 'YYYY-MM-31'` when timestamps include times; use `< next_month`.
- Applying exclusion counters sequentially when the template expects independent counts.
- Dropping all telemetry v1 rows when only overlap rows should be excluded.
- Treating account segment and subscription plan as interchangeable without checking prompt wording.
- Forgetting canceled tickets and duplicates before defect/support aggregations.
- Omitting audit fields or approved-case guards in correction SQL.
- Computing detail arrays with different filters than the headline totals.
