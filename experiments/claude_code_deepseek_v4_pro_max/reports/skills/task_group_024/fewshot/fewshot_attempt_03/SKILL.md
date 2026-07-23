# Portfolio Engineering Operations Skill

## Overview

This skill provides reusable instructions for operating against a portfolio engineering REST API that exposes work items, mix targets, releases, milestones, SLA policies, blockers, and dependencies. It covers three common analytical workflows: **portfolio mix review**, **SLA aging analysis**, and **release readiness assessment**.

## Environment

The environment is accessed at `<TASK_ENV_BASE_URL>`. All endpoints are relative to this base URL.

### Authentication

For `POST /api/query` only, send the header:

```
X-Env-Token: portfolio-readonly
```

All `GET` endpoints are unauthenticated.

### Available Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/work-items` | List all work items |
| GET | `/api/work-items/{item_id}` | Get a single work item by ID |
| GET | `/api/mix-targets` | List portfolio mix target percentages per scope |
| GET | `/api/sla-policy` | List SLA policy rules |
| GET | `/api/releases` | List all releases |
| GET | `/api/releases/{release_id}` | Get a single release by ID |
| GET | `/api/milestones` | List all milestones |
| GET | `/api/dependencies` | List work item dependency chains |
| GET | `/api/blockers` | List blocker records |
| POST | `/api/query` | Run a restricted SQL query (requires auth header) |

## Domain Model

### Work Items

Work items are the central entity. Each has:

- **id**: A unique string identifier (e.g., `WI-24024-P001`, `WI-24024-075`, `WI-24024-S001`)
- **Type signals**: A work item may have a `type` field, label tags, and a title. These can conflict — use the **portfolio category conventions** (see below) to resolve conflicting signals.
- **Status**: open, closed, cancelled, etc. Only **closed** items count toward the closed portfolio mix.
- **Team**: The owning engineering team.
- **Product area**: The product area the work belongs to.
- **Owner**: The person assigned to the work item. May be empty/missing.
- **Quarter**: The quarter the work belongs to (e.g., `2025-Q4`).
- **closed_at**: Timestamp when the work item was closed.
- **created_at**: Timestamp when the work item was created.
- **SLA-related fields**: deadline, severity (S1-S4), aging days.
- **Duplicate/primary relationship**: A work item may be a **duplicate** pointing at a **primary** (canonical) record, or may itself be a primary record that duplicates reference.
- **Mirror/export fields**: Some work items contain stale mirror or export status fields. These should be **ignored**; always use the authoritative top-level status field.

### Portfolio Categories

Every work item maps to exactly one of four portfolio categories:

| Category | Description |
|----------|-------------|
| `NewFeature` | New feature development |
| `TechDebt` | Technical debt reduction |
| `Reliability` | Reliability, resilience, and operational improvements |
| `Security` | Security hardening and vulnerability remediation |

#### Category Resolution Rules

When a work item has conflicting category signals (e.g., its `type` field says one thing but its labels or title suggest another), resolve using these conventions:

1. **Type field** takes priority over labels and title hints.
2. If the type field is ambiguous or absent, check **labels** next.
3. If still ambiguous, inspect the **title** for category-indicating keywords.
4. Known legacy categories or mirror-category fields are **ignored** — only the resolved category according to the above rules is authoritative.

### Mix Targets

Mix target records map a `scope_id` to target percentage allocations across the four portfolio categories. Each target row contains:

- `scope_id`: The scope identifier this target applies to.
- Target percentages for `NewFeature`, `TechDebt`, `Reliability`, `Security` (summing to 100%).

Use the mix target row whose `scope_id` matches the task's scope.

### Releases and Milestones

- **Release**: Has an ID (e.g., `REL-ORION-2026-02`), a set of associated milestones, and a list of assigned work item IDs.
- **Milestone**: Has an ID (e.g., `MIL-ORION-BETA`), belongs to a release, and has associated work item IDs. Milestones define gates within a release.

### Blockers

Blocker records associate a work item ID with a cause string and an impact level. For release readiness:

- Only **unresolved** blockers matter.
- Only **high-impact** blockers are counted in `blocker_cause_counts`.
- The exact cause string from the environment is the key — do not normalize or rewrite.

### Dependencies

Dependency records define chains between work items. A dependency chain is an **ordered list** of work item IDs from a blocked release work item to the non-complete blocking dependency.

### SLA Policy

SLA policy records define the maximum allowed aging days for work items, typically scoped by category and/or severity. Compare each work item's current aging days against the applicable SLA threshold to determine overdue status.

## Common Conventions

### Ordering

- **Team names**: Sort alphabetically (A-Z).
- **Product area names**: Sort alphabetically (A-Z).
- **Work item ID lists**: Sort lexicographically unless a different order is specified (e.g., `closed_at` ascending then ID ascending for included work items).
- **Duplicate clusters**: Sort by `primary_id` lexicographically. Within each cluster, sort `duplicate_ids` lexicographically.
- **Milestone completion**: Sort by `milestone_id` ascending (lexicographic).
- **Gap table / mix table rows**: Always in this fixed order: `NewFeature`, `TechDebt`, `Reliability`, `Security`.
- **Under-invested categories**: Most negative gap to least negative gap (i.e., most under-invested first).
- **Escalation queue**: Ordered by severity priority (S1 first, then S2, S3, S4) and then by aging days descending within each severity tier.

### Rounding and Precision

- **Percentages** (completion_pct, actual_pct, target_pct, gap_pct): Round to **1 decimal place**. These are percentage points (not fractions), e.g., `66.7` not `0.667`.
- **Rates and scores** (breach_rate, readiness_score): Round to **3 decimal places**. These are ratios in the range [0, 1], e.g., `0.545`.
- **Gap**: Always `actual_pct − target_pct`. A negative gap means under-investment; a positive gap means over-investment.

### Primary vs. Duplicate Records

- **Primary records**: Canonical work items that represent the real work. Counted in all metrics (mix, SLA, readiness).
- **Duplicate records**: Non-canonical work items that point to a primary record. **Excluded** from primary counts and metrics. Report them in `duplicate_clusters` or `excluded_duplicate_ids`.
- When a duplicate references a primary, the primary ID is the cluster key. A primary may have zero or more duplicates pointing at it.

### Exclusion Rules

The following records must be **excluded** from primary analysis:

| Exclusion Type | Condition | Reporting Location |
|---------------|-----------|-------------------|
| Duplicate | Record is a duplicate pointing to another primary | `excluded_duplicate_ids` or `duplicate_clusters` |
| Cancelled | Record status is cancelled | `excluded_cancelled_ids` |
| Distractor | Record matches scope (team/quarter/product area) but should not be counted as primary closed portfolio work (e.g., closed outside the quarter window, or has an invalid status for the analysis) | `excluded_distractor_ids` |
| Mirror/legacy | Stale mirror fields or legacy category fields exist on the record but should not influence classification | `ignored_mirror_status_and_legacy_category: true` |

### Stale Mirror Fields

Some work items carry mirror or export-level status and category fields that are out of sync with the authoritative fields. Always use the **top-level status field** as the source of truth. Do not use mirrored fields to determine status, category, or any other computed metric.

## Workflow 1: Portfolio Mix Review

Use this workflow for Q4 portfolio mix readouts, closed-work mix reviews, and similar tasks that compare actual category distribution against target mix percentages.

### Steps

1. **Fetch mix targets**: `GET /api/mix-targets` — locate the row with the matching `scope_id`. Record the target percentages for all four categories.

2. **Fetch work items**: `GET /api/work-items` — filter to in-scope items by quarter, team, and product area. Alternative: use `POST /api/query` for filtered retrieval.

3. **Classify included items**: For each closed work item in scope, resolve its portfolio category using the category resolution rules. Skip items that are duplicates, cancelled, or distractor records — log them in the exclusion lists.

4. **Compute category counts**: Count primary included work items per category.

5. **Compute actual percentages**: For each category, `(count / total_included) × 100`, rounded to 1 decimal place.

6. **Compute gap table**: For each category, `gap_pct = actual_pct − target_pct` (both rounded to 1 decimal place).

7. **Identify under-invested categories**: Categories with negative `gap_pct`, ordered from most negative to least negative.

8. **Determine follow-up action**:
   - If any category has a negative gap: `REBALANCE_CAPACITY`, with `primary_category` = the category with the largest negative gap and `secondary_category` = the next most negative (or `null` if none). `rationale_code`: `LARGEST_NEGATIVE_GAP`.
   - If no negative gaps: `MAINTAIN_CURRENT_MIX`, with `null` categories and `rationale_code`: `NO_NEGATIVE_GAPS`.
   - If data conflicts prevent a clear determination: `INVESTIGATE_DATA_QUALITY` with `rationale_code`: `DATA_CONFLICT`.

9. **Assemble the JSON answer** following the provided answer template schema.

### Key Output Fields

- `scope`: scope_id, quarter, teams (alphabetical), product_areas (alphabetical), target_scope_id, total_included
- `included_work_item_ids`: primary closed work items; ordered by `closed_at` ascending, then ID ascending
- `category_counts`: integer counts per category
- `category_percentages` or `mix_table`: actual vs target percentages with gaps
- `under_invested_categories` or `largest_deficit_category`: the most under-invested
- `follow_up_action` or `recommended_action`: rebalance recommendation
- `exclusion_flags` or `excluded_distractor_ids`: what was excluded and why

## Workflow 2: SLA Aging Analysis

Use this workflow to audit SLA compliance, identify overdue work items, compute breach rates, and surface hotspots.

### Steps

1. **Fetch SLA policy**: `GET /api/sla-policy` — understand the SLA thresholds by category and/or severity.

2. **Fetch work items**: `GET /api/work-items` — filter by team, category (Reliability and/or Security), and other scope constraints.

3. **Separate primary from duplicate**: Identify primary records (counted in SLA metrics) and duplicate clusters (reported but not counted).

4. **Compute aging**: For each primary work item, determine its current age in days (difference between as-of date and `created_at`, or as reported in an aging field). Items closed within the recent closed window are not overdue.

5. **Determine overdue status**: Compare each primary item's age against the applicable SLA threshold. An item is overdue if its age exceeds the SLA deadline.

6. **Bucket aging distribution**: Count primary items by age bucket (0-3, 4-7, 8-14, 15-30, 31+ days).

7. **Compute team overdue counts**: Group overdue primary items by team; list teams alphabetically.

8. **Identify top hotspot**: Find the (team, owner) pair with the most overdue primary records. If an owner is missing for an overdue item, treat the owner as `UNASSIGNED` for hotspot aggregation. If multiple pairs tie, the hotspot counts as the one found.

9. **Identify missing owners**: Primary included records with no owner assigned.

10. **Compute breach rate**: `overdue_primary_count / included_primary_count`, rounded to 3 decimal places.

11. **Build escalation queue** (when applicable): Order overdue primary items by severity (S1 first) then by aging days descending within each severity tier.

### Key Output Fields

- `included_primary_ids`: all primary work items in scope, sorted lexicographically
- `overdue_primary_ids`: overdue primary items, sorted lexicographically
- `aging_bucket_counts`: counts per age bucket
- `team_overdue_counts`: per-team overdue counts, teams alphabetical
- `top_hotspot`: team, owner, overdue_count
- `duplicate_clusters`: primary_id → [duplicate_ids], sorted by primary_id
- `missing_owner_ids`: primary items with no owner, sorted lexicographically
- `breach_rate` or `sla_breach_rate`: ratio rounded to 3 decimal places

## Workflow 3: Release Readiness Assessment

Use this workflow to assess whether a release is ready to ship based on milestone completion, blocker status, and dependency health.

### Steps

1. **Fetch release data**: `GET /api/releases/{release_id}` — get the release, its milestone IDs, and its assigned work item IDs.

2. **Fetch milestones**: `GET /api/milestones` — get milestone completion data. For each milestone, identify which of its work items are complete (closed) and which are primary.

3. **Compute milestone completion**: For each milestone, `completion_pct = (complete_primary / primary_total) × 100`, rounded to 1 decimal place. Sort milestones by `milestone_id` ascending.

4. **Identify gating work items**: Primary release work items that are **not complete**. These block readiness. Sort ascending, no duplicates.

5. **Fetch blockers**: `GET /api/blockers` — filter to unresolved, high-impact blockers associated with the release's work items. Count by exact cause string. Do not normalize cause text.

6. **Fetch dependencies**: `GET /api/dependencies` — find chains from blocked release work items to non-complete dependencies. Each chain is an ordered list of work item IDs. Sort chains lexicographically by the full path.

7. **Determine ship decision**:
   - `SHIP`: All milestones substantially complete, zero gating items, no unresolved high-impact blockers, no critical dependencies.
   - `SHIP_WITH_WATCH`: Near-complete with minor open items or low-impact blockers only. Some risk but acceptable.
   - `NO_SHIP`: Significant incomplete milestones, unresolved high-impact blockers, or critical dependency chains exist.

8. **Compute readiness score**: `completed_primary_work_items / total_primary_work_items`, rounded to 3 decimal places.

### Key Output Fields

- `release_id`: the release under review
- `ship_decision`: SHIP, SHIP_WITH_WATCH, or NO_SHIP
- `milestone_completion`: per-milestone completion metrics sorted by milestone_id
- `gating_work_item_ids`: non-complete work items blocking readiness
- `blocker_cause_counts`: unresolved high-impact blocker counts by exact cause
- `critical_dependency_chains`: ordered dependency paths
- `readiness_score`: ratio rounded to 3 decimal places

## Using POST /api/query

The `POST /api/query` endpoint accepts a restricted SQL query. Send a JSON body with the query, including the `X-Env-Token: portfolio-readonly` header. This is useful for:

- Filtering work items by multiple criteria (team, quarter, category, status)
- Aggregating counts and computing derived fields
- Joining work items with releases, milestones, or blockers

The SQL dialect and schema depend on the environment. Start with `GET` endpoints to understand the schema, then use `POST /api/query` for efficient filtered retrieval.

## Error Handling and Edge Cases

- **Missing data**: If a required endpoint returns empty or an entity is not found, note it explicitly rather than guessing. A missing mix target means no gap analysis is possible.
- **Zero denominators**: When `total_included = 0`, percentages are undefined. Report 0 counts and note the empty scope.
- **Conflicting signals**: When a work item's type, labels, and title disagree on category, apply the resolution rules consistently: type → labels → title, ignoring mirror fields.
- **Duplicates referencing non-existent primaries**: If a duplicate points to a primary not in the fetched work item set, still report the cluster — list the duplicate in `duplicate_ids` and use the referenced primary ID as the cluster key.
- **Multiple duplicates for the same primary**: Group them under a single cluster entry.
- **Ties in hotspot detection**: Multiple (team, owner) pairs may have the same overdue count. Report the one encountered via the ordered traversal (teams alphabetically, then owners alphabetically).

## Summary Checklist

Before submitting any answer:

1. **Classification**: Every included work item has exactly one resolved portfolio category.
2. **Exclusions**: Duplicates, cancelled, and distractor records are in the appropriate exclusion lists, not in the primary counts.
3. **Ordering**: Teams alphabetical, IDs lexicographic (unless `closed_at` ordering applies), gap/mix table rows in fixed category order.
4. **Rounding**: Percentages to 1 decimal place, rates/scores to 3 decimal places.
5. **Mirror fields ignored**: No metric depends on a stale mirror or legacy field.
6. **Schema compliance**: The output JSON matches the provided answer template exactly — no extra fields, no missing required fields, correct enum values.
