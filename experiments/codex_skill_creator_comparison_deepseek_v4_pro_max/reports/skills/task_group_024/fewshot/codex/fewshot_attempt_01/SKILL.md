---
name: eng-portfolio-metrics
description: Engineering portfolio analysis for work-item-oriented REST environments. Covers portfolio mix classification (NewFeature/TechDebt/Reliability/Security) with target-gap analysis, SLA aging audits with breach-rate calculation and duplicate resolution, and release readiness assessments with milestone completion, blocker, and dependency-chain evaluation. Use when a task requires computing portfolio mix percentages and gaps against targets, auditing SLA compliance and overdue work items for specific teams and date windows, or determining ship readiness for a named release.
---

# Engineering Portfolio Metrics

## Overview

Analyze engineering work items exposed through a REST API environment. The three supported analyses are portfolio mix reviews, SLA aging audits, and release readiness assessments. Each analysis requires navigating a set of REST endpoints, resolving duplicate records against canonical primary work items, ignoring stale mirror/legacy fields, and producing a JSON answer that conforms to a supplied template.

## Environment and Endpoints

The task prompt supplies `<TASK_ENV_BASE_URL>` and the file `environment_access.md` lists the available endpoints. See [references/api-endpoints.md](references/api-endpoints.md) for endpoint details and example responses.

**Always read `environment_access.md` first** to confirm which endpoints are available for the current task. Not all endpoints appear in every task.

Common endpoints include:

- `GET /api/work-items` — paginated list of work items
- `GET /api/work-items/{item_id}` — single work item detail
- `GET /api/mix-targets` — portfolio mix targets by scope_id
- `GET /api/sla-policy` — SLA response-time thresholds by severity
- `GET /api/releases` — list of releases
- `GET /api/releases/{release_id}` — single release with milestones
- `GET /api/milestones` — milestone definitions
- `GET /api/dependencies` — work-item dependency relationships
- `GET /api/blockers` — blocker records with cause and impact
- `POST /api/query` — restricted SQL query endpoint (use only when the API endpoints don't directly provide the needed data)

## Core Rules for All Analyses

### Primary vs. Duplicate Records

Some work items are duplicates that point at a canonical (primary) work item. The relationship is expressed through a field such as `canonical_id`, `duplicate_of`, or a record status like `Duplicate`. Always:

1. Identify primary records (not duplicates themselves) as the counted population.
2. Report duplicate clusters separately (as `duplicate_clusters` or `excluded_duplicate_ids`) so they are not double-counted.
3. Never include a duplicate in `included_work_item_ids`, `included_primary_ids`, or any count denominator.

### Stale Mirror and Legacy Fields

The environment may include work items with fields like `mirror_status`, `export_status`, `legacy_category`, or similar mirror/export markers. The authoritative fields are the direct work-item fields:

- Use `status` (not `mirror_status`) for work-item lifecycle state.
- Use `portfolio_category` (not `legacy_category`) for portfolio classification.
- Use the work item's own `closed_at`, `created_at`, `team`, `owner`, `severity`, `product_area`, `milestone_id`, and `release_id` fields.

When a template field `ignored_mirror_status_and_legacy_category` is present, set it to `true`.

### Portfolio Category Classification

The four portfolio categories are always `NewFeature`, `TechDebt`, `Reliability`, and `Security`. The `portfolio_category` field on the work item is authoritative. If a work item is missing this field, do not infer a category from title or labels; exclude the item from classification.

### Rounding and Precision

- Percentages in mix tables and milestone completion: round to **1 decimal place**.
- Rates (breach rate, readiness score): round to **3 decimal places**.
- When computing percentages from integer counts, compute `round(100.0 * count / total, 1)` for 1-decimal results and `round(count / total, 3)` for 3-decimal rates.

### Stable Ordering

- Work-item ID lists: sort **lexicographically** (ascending string order).
- Team lists: sort **alphabetically**.
- Categories in tables: follow the fixed order `NewFeature`, `TechDebt`, `Reliability`, `Security` unless the template specifies a different order.
- Duplicate clusters: sort by `primary_id` lexicographically; `duplicate_ids` within each cluster sorted lexicographically.
- Milestone completion: sort by `milestone_id` ascending (lexicographic).
- Escalation queue: sort by severity (S1 first, then S2, S3, S4), then within each severity by `created_at` ascending (oldest first).

### ID Format

Work item IDs follow the pattern `WI-24024-` with a letter prefix and digits, e.g. `WI-24024-A001` or `WI-24024-XYZ`. Validate against any template regex before finalizing.

---

## Analysis 1: Portfolio Mix Review

Used for portfolio mix tasks where you compare actual close counts against target percentages.

### Workflow

1. Read the task prompt for scope: `quarter`, `teams`, `product_areas` (or `product_area`), and `scope_id`.
2. Fetch `/api/mix-targets` and locate the row where `scope_id` matches the task scope. Extract `target_pct` values for `NewFeature`, `TechDebt`, `Reliability`, `Security`.
3. Fetch work items in scope. Filter by `quarter`, `team` (in the task team list), and `product_area`. See [references/work-item-model.md](references/work-item-model.md) for field details.
4. Keep only items with authoritative `status` of `closed` or `Closed`. Do not use `mirror_status`.
5. Identify and set aside:
   - **Duplicates**: items whose `canonical_id` or `duplicate_of` points at another work item, or whose status is `Duplicate`. These go into `excluded_duplicate_ids` or `duplicate_clusters`.
   - **Cancelled**: items with status `cancelled` or `Cancelled`. These go into `excluded_cancelled_ids`.
   - **Distractors**: items that fall within the scope's time/team/product filters but are not primary closed portfolio work. These go into `excluded_distractor_ids` when the template calls for them.
6. For each included (primary, closed) work item, read `portfolio_category`. Count per category.
7. Compute `category_percentages`: `round(100.0 * count / total_included, 1)` for each category.
8. Build the `gap_table` (or `mix_table`): for each category in fixed order, include `count`, `actual_pct`, `target_pct`, and `gap_pct = actual_pct - target_pct`.
9. Identify under-invested categories: those with negative `gap_pct`, sorted from most negative to least negative.
10. Determine the follow-up action:
    - If any negative gap exists: `REBALANCE_CAPACITY`, `primary_category` is the one with largest negative gap, `rationale_code` is `LARGEST_NEGATIVE_GAP`.
    - If no negative gaps: `MAINTAIN_CURRENT_MIX`, `primary_category` is null, `secondary_category` is null, `rationale_code` is `NO_NEGATIVE_GAPS`.
    - If a data conflict is detected: `INVESTIGATE_DATA_QUALITY`, `rationale_code` is `DATA_CONFLICT`.
11. Sort `included_work_item_ids` by `closed_at` ascending, then `id` ascending for ties.

See [references/classification-guide.md](references/classification-guide.md) for category classification rules and examples.

---

## Analysis 2: SLA Aging Audit

Used for SLA audit tasks where you assess overdue reliability/security work items against SLA response-time thresholds.

### Workflow

1. Read the task prompt for scope: `teams`, `as_of` date, `recent_closed_window_days`, and `sla_categories` (or `categories`).
2. Fetch `/api/sla-policy` to get the SLA thresholds: max response days per severity level (S1, S2, S3, S4).
3. Fetch work items for the specified teams. Filter to the SLA categories (Reliability and/or Security). See [references/work-item-model.md](references/work-item-model.md) for field details.
4. Identify primary records (exclude duplicates using the same primary/duplicate logic as in Analysis 1). Report duplicate clusters separately.
5. Determine inclusion: a primary work item is included if it is not closed within the `recent_closed_window_days` before `as_of`. Items closed recently (within the window) are considered handled and excluded.
6. Determine overdue: an included primary work item is overdue if `created_at + SLA_threshold < as_of`. Use the item's `severity` to look up the threshold in the SLA policy. Items with missing `severity` should be treated with the most restrictive (shortest) threshold.
7. Compute `breach_rate`: `round(overdue_count / included_primary_count, 3)`.
8. Build aging buckets: compute `days_old = days_between(created_at, as_of)`. Bucket as `0-3`, `4-7`, `8-14`, `15-30`, `31+`.
9. Build `overdue_counts_by_severity` or `team_overdue_counts` as the template requires.
10. Identify the top hotspot: the `(team, owner)` pair with the most overdue primary records. For ties, pick the first lexicographically by team then owner. Treat missing owner as `UNASSIGNED`.
11. Build the escalation queue when required: overdue primary IDs sorted by severity (S1 first), then within each severity by `created_at` ascending (oldest first).

---

## Analysis 3: Release Readiness

Used for release readiness tasks where you determine whether a named release can ship.

### Workflow

1. Read the task prompt for the `release_id`.
2. Fetch `/api/releases/{release_id}` for release details including linked milestones.
3. Fetch `/api/milestones` and cross-reference with the release's milestones to get milestone IDs.
4. For each milestone, fetch the work items linked to it. Count primary items only. Count how many are in a completed/closed state. Compute `completion_pct = round(100.0 * complete_primary / primary_total, 1)`.
5. Determine the ship decision:
   - `SHIP`: all milestones have `completion_pct >= 80`.
   - `SHIP_WITH_WATCH`: all milestones have `completion_pct >= 60` and at least one is `< 80`.
   - `NO_SHIP`: any milestone has `completion_pct < 60`.
6. Identify gating work items: all non-complete release work items (primary only). Sort ascending. Remove duplicates.
7. Fetch `/api/blockers` for unresolved high-impact blockers. Build `blocker_cause_counts` keyed by exact cause text (string as-is from the API).
8. Fetch `/api/dependencies` for dependency chains. A critical dependency chain is an ordered path from a blocked release work item to a non-complete dependency work item. Sort chains lexicographically by the full path.
9. Compute `readiness_score`: `round(completed_primary / primary_total, 3)` across all milestones.

---

## Practical Tips

### When to Use POST /api/query

Use the `/api/query` endpoint only when the existing GET endpoints don't provide the data you need. The `/api/query` endpoint accepts a restricted SQL query. Prefer GET endpoints for work items, mix targets, SLA policy, releases, milestones, blockers, and dependencies.

### Pagination

The `/api/work-items` endpoint may be paginated. Always check response metadata for `next` links or `total` counts and fetch all pages before filtering.

### Missing Fields

- Work items missing `severity` should be treated with the most conservative SLA threshold.
- Work items missing `owner` should be counted as `UNASSIGNED` for hotspot calculations and listed in `missing_owner_ids`.
- Work items missing `portfolio_category` should be excluded from the classified population.

### Consistent Field Names

Field names from the API may vary. Always read the actual response JSON to determine exact field names. Common variations: `closedAt` vs `closed_at`, `createdAt` vs `created_at`, `productArea` vs `product_area`. Match what the API actually returns.

### Authoritative vs. Stale Fields

Always prefer `status` over `mirror_status`, `portfolio_category` over `legacy_category`, and the work item's own `closed_at` over any `mirror_closed_at`. Duplicates and cancelled items must be excluded from the primary population even if their mirror fields suggest otherwise.
