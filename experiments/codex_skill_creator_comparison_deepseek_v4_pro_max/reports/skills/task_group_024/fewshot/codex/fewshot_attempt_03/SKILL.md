---
name: portfolio-mgmt
description: Solve test-environment portfolio management tasks involving work item classification, mix analysis, SLA aging, release readiness, blockers, and dependencies. Use when the task asks you to interact with a shared portfolio REST API at a TASK_ENV_BASE_URL, classify work items into NewFeature/TechDebt/Reliability/Security categories, compute portfolio mix gaps, assess SLA breach rates, evaluate release readiness, or produce structured JSON answers following an answer template. Covers mix-target comparison, duplicate/cancelled/mirror-stale record detection, blocker cause analysis, and dependency chain tracing.
---

# Portfolio Management

Solve portfolio management tasks in a shared test environment. The environment exposes work items, mix targets, SLA policy, releases, milestones, blockers, and dependencies through REST endpoints and a read-only SQL query endpoint.

## Workflow

1. Read `environment_access.md` in the workspace for the base URL, allowed endpoints, and any required auth tokens.
2. Fetch reference data from the REST endpoints: work-items, mix-targets, sla-policy, releases, milestones, dependencies, blockers.
3. Use [POST /api/query](references/portfolio_api.md) (SQL) for filtered work-item queries when REST pagination or filtering is insufficient.
4. Classify work items using [category rules](references/category_rules.md).
5. Distinguish primary, duplicate, cancelled, and mirror-stale records using [data quality rules](references/data_quality.md).
6. Compute metrics with correct precision: percentages to 1 decimal place, rates to 3 decimal places.
7. Follow the answer template schema exactly. Produce valid JSON only.

## Essential Rules

### Precision

- Percentage points: round to **1 decimal place** (e.g. 66.7, 11.1).
- Rates (breach_rate, readiness_score): round to **3 decimal places** (e.g. 0.545, 0.688).
- Counts: integers.

### Sorting

- Work item ID lists: **lexicographically ascending** unless the task asks for closed_at-then-id ordering.
- Team lists: **alphabetically ascending**.
- Categories in gap/mix tables: always order **NewFeature, TechDebt, Reliability, Security**.
- Duplicate clusters: sort by `primary_id` ascending; `duplicate_ids` within each cluster sorted ascending.

### Work Item Authoritative Fields

- Use `status`, `work_type`, `labels`, `title`, `team`, `product_area`, `owner`, `severity`, `priority`, `closed_at`, `created_at`, `due_at`, `duplicate_of`, `milestone_id`, `release_id`.
- **Never** use `mirror_status` as the source of truth for a work item's real status.
- **Never** use `legacy_category` as the portfolio category. Classify using the rules in [category_rules.md](references/category_rules.md).
- `duplicate_of` being non-null means the item is a duplicate referencing a primary. Exclude duplicates from primary counts.
- `status` of "Cancelled" means the item is cancelled. Exclude cancelled items from primary counts.

### SQL Query Endpoint

- POST `/api/query` with header `X-Env-Token: portfolio-readonly`.
- Body: `{"sql": "<SELECT or WITH statement>", "params": []}`.
- Only SELECT and WITH statements are allowed.
- Returns `{"columns": [...], "rows": [[...], ...], "row_count": N, "truncated": false}`.
- Use SQL for cross-entity queries (e.g. work items filtered by team, quarter, status; joins with releases or milestones).

## Common Task Types

### Portfolio Mix Review

1. Fetch mix-targets, find the target row matching the given scope_id.
2. Query work items in the relevant quarter, teams, product areas with status not Duplicate/Cancelled.
3. Classify each included item into exactly one portfolio category.
4. Count per category, compute actual percentages, gap = actual - target.
5. Identify under-invested categories (negative gap).
6. Exclude duplicate and cancelled records; report them in exclusion flags.
7. Skip items whose `mirror_status` disagrees with their real `status` — flag `ignored_mirror_status_and_legacy_category: true`.

### SLA Aging Review

1. Fetch sla-policy for severity-to-days mapping.
2. Query primary work items matching the given teams and categories (Reliability, Security).
3. For each item, compute age: `as_of_date - created_at` in days.
4. Determine if overdue: `age > sla_policy[severity].days_to_due`.
5. Compute aging bucket distribution, team overdue counts, owner hotspot.
6. Identify duplicate clusters via `duplicate_of`.
7. Compute breach_rate = overdue_primary_count / included_primary_count (3 decimal places).

### Release Readiness

1. Fetch the release by ID, its milestones, and all work items on those milestones.
2. Count completed primary items per milestone; compute completion_pct.
3. Identify non-complete gating items (status not Closed/Verified/Done/Deployed).
4. Fetch unresolved high-impact blockers (severity High or Critical, status not Resolved).
5. Trace dependency chains from blocked release work items to non-complete dependencies.
6. Compute readiness_score = completed_primary / primary_total (3 decimal places).
7. Ship decision: SHIP if >= 0.95 and no high-impact blockers; SHIP_WITH_WATCH if >= 0.80 with blockers; NO_SHIP otherwise.

### Escalation Queue

- When building an escalation queue for SLA tasks, order overdue primary items by severity (S1 first, then S2, S3, S4), then by age descending within each severity tier.

## References

- [portfolio_api.md](references/portfolio_api.md) — Full API endpoint and SQL schema reference
- [category_rules.md](references/category_rules.md) — How to classify work items into portfolio categories
- [data_quality.md](references/data_quality.md) — Duplicate, cancelled, mirror-stale, and distractor detection

## Scripts

- [query_portfolio.py](scripts/query_portfolio.py) — Run a read-only SQL query against the task environment
