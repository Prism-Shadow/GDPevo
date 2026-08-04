---
name: portfolio-review
description: Analyze engineering portfolio data for mix reviews, SLA aging, and release readiness using a shared REST + SQL environment. Use when the task involves portfolio mix categorization, SLA breach/aging calculations, release readiness assessments, or dependency/blocker analysis against work item datasets.
---

# Portfolio Review Skill

## Environment Access

The shared portfolio environment is accessed through a base URL (provided as `<TASK_ENV_BASE_URL>` or equivalent). Authentication for the SQL query endpoint uses the header `X-Env-Token: portfolio-readonly`. The available REST endpoints and query constraints are documented in `environment_access.md`.

### REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/work-items` | List all work items |
| GET | `/api/work-items/{item_id}` | Single work item |
| GET | `/api/mix-targets` | Portfolio mix targets |
| GET | `/api/sla-policy` | SLA severity-to-days mapping |
| GET | `/api/releases` | All releases |
| GET | `/api/releases/{release_id}` | Single release |
| GET | `/api/milestones` | All milestones |
| GET | `/api/dependencies` | Dependency relationships |
| GET | `/api/blockers` | Blocker records |
| POST | `/api/query` | Arbitrary SELECT / WITH queries |

### SQL Query Constraints

- Exactly one statement per request.
- Only `SELECT` or `WITH` statements allowed.
- `params` must be a JSON array.
- Maximum 1000 rows returned.
- Use `?` placeholders with corresponding `params` array entries.

## Work Item Data Model

Key fields on a work item:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (e.g., `WI-24024-001`) |
| `status` | **Authoritative** current state |
| `work_type` | Primary signal for portfolio category |
| `labels` | JSON array of tag strings |
| `legacy_category` | Stale/legacy classification (do not use as primary signal) |
| `mirror_status` | Stale mirror/export field (do not use as primary signal) |
| `duplicate_of` | If non-null, this item is a duplicate of the referenced id |
| `team` | Owning team |
| `product_area` | Product area |
| `severity` | S1, S2, S3, or S4 |
| `owner` | Assigned owner (null if unassigned) |
| `closed_at` | Closure timestamp (null if not closed) |
| `created_at` | Creation timestamp |
| `due_at` | Due date timestamp |
| `release_id` | Associated release |
| `milestone_id` | Associated milestone |
| `story_points` | Story point estimate |
| `priority` | Numeric priority |
| `title` | Human-readable title |

## Authoritative vs. Stale Fields

- **`status`** is authoritative for work item state. Ignore `mirror_status`.
- **`work_type`** is the primary signal for portfolio category. `legacy_category` is a stale field and must not be used as the primary classification.
- **Labels containing `stale-export`** flag records that may contain mirrored or exported data; treat these records with caution and verify against authoritative fields.

## Scope Filtering

When a task specifies scope constraints (teams, product areas, quarter, categories), filter work items exactly:

- **Teams**: Match `team` field against the specified list.
- **Product Areas**: Match `product_area` field against the specified list.
- **Quarter**: Filter by `closed_at` falling within the quarter's date range (Q1 = Jan–Mar, Q2 = Apr–Jun, Q3 = Jul–Sep, Q4 = Oct–Dec).
- **Categories**: For SLA/reliability tasks, restrict to items whose portfolio category (see below) matches the requested categories.

## Portfolio Category Classification

Every work item is assigned exactly one portfolio category: `NewFeature`, `TechDebt`, `Reliability`, or `Security`.

### Decision Order

1. **`work_type` is the primary signal.** Map it directly where clear:
   - `Feature` → `NewFeature`
   - `Enhancement` → `NewFeature`
   - `Bug` → `TechDebt`
   - `Chore` → `TechDebt`
   - `Refactor` → `TechDebt`
   - `Dependency` → `TechDebt`
   - `Incident` → `Reliability`
   - `Reliability` → `Reliability`
   - `Security` → `Security`
   - `Compliance` → `Security`

2. **Resolve conflicting signals.** When `work_type` maps to `NewFeature` or `TechDebt` but `labels` contain strong reliability or security indicators, the label signal takes precedence:
   - Labels containing `reliability`, `outage`, `incident`, or `latency` → override to `Reliability`
   - Labels containing `security`, `cve`, or `encryption` → override to `Security`

3. **Labels with `stale-export`** are unreliable and should not trigger overrides.

4. **Title hints.** When a title explicitly calls out a label as stale (e.g., "with stale security label"), do not use that label signal for classification.

## Duplicate and Cancelled Records

- **Duplicate**: Any item with `status` = `Duplicate` OR non-null `duplicate_of` is a duplicate. Exclude from primary counts. Report in `duplicate_clusters` or `exclusion_flags`.
- **Cancelled**: Any item with `status` = `Cancelled` is excluded from primary portfolio populations.
- When building duplicate clusters, the item referenced by `duplicate_of` is the primary; the item with the `duplicate_of` field set is the duplicate.


### Distractor Records

A **distractor** is a work item that partially matches scope criteria but does not satisfy all constraints simultaneously (e.g., `team` matches but `product_area` does not, or vice versa). Distractors must be excluded from the primary portfolio population and reported separately as `excluded_distractor_ids` when the answer template requires it.
## Portfolio Mix Analysis


For mix review tasks (comparing actual category distribution against targets):

1. **Define the closed population**: Items in scope with status in (`Closed`, `Deployed`, `Done`, `Verified`) and `closed_at` within the quarter.
2. **Exclude** duplicates and cancelled records.
3. **Classify** each remaining item into one portfolio category.
4. **Count** items per category (count-based, not story-point-based).
5. **Calculate percentages**: `(category_count / total_included) * 100`, rounded to 1 decimal place.
6. **Retrieve target mix** from `/api/mix-targets` using the specified `scope_id`.
7. **Compute gaps**: `gap_pct = actual_pct - target_pct`, rounded to 1 decimal place.
8. **Identify under-invested categories**: Those with negative `gap_pct`.
9. **Recommend follow-up**: One controlled action targeting the most under-invested category.

### Mix Table Output Order

Rows must appear in this fixed order: `NewFeature`, `TechDebt`, `Reliability`, `Security`.

## SLA Aging Analysis

For SLA audit tasks:

### SLA Policy

The SLA policy maps severity to maximum days allowed from creation to due date:

| Severity | Days to Due |
|----------|-------------|
| S1 | 3 |
| S2 | 10 |
| S3 | 21 |
| S4 | 45 |

Retrieve the current policy from `/api/sla-policy` (values may differ across environments).

### Primary SLA Population

1. Filter to in-scope teams and SLA-relevant categories (Reliability, Security).
2. Classify each item into a portfolio category; keep only those matching the SLA categories.
3. Exclude duplicates (status=`Duplicate` or non-null `duplicate_of`).
4. Include items that are:
   - **Not closed**: status is not in (`Closed`, `Deployed`, `Done`, `Verified`).
   - **Recently closed**: `closed_at` falls within `[as_of_date - recent_closed_window_days, as_of_date]`.

### Overdue Determination

An item in the primary population is **overdue** if:
- Its `due_at` date is strictly before the `as_of` date, AND
- The item is either not closed OR was closed after its `due_at` date.

### Aging Buckets

For overdue items, compute age as `as_of_date - due_at` in days. Bucket into: `0-3`, `4-7`, `8-14`, `15-30`, `31+`.

### Escalation Queue (Priority Order)

Sort overdue primary items by:
1. Severity ascending (S1 before S2 before S3 before S4)
2. Age descending (oldest first)
3. ID ascending (tiebreaker)

### SLA Breach Rate

`breach_rate = overdue_primary_count / included_primary_count`, rounded to exactly 3 decimal places.

### Duplicate Clusters

Group duplicates by their `duplicate_of` primary id. Each cluster contains the `primary_id` and a sorted list of `duplicate_ids`. Sort clusters by `primary_id` ascending.

## Release Readiness Assessment

For release review tasks:

### Data Sources

- `/api/releases/{release_id}` for release metadata.
- `/api/milestones` for milestones belonging to the release (filtered by `release_id`).
- Work items with `release_id` matching the target release.
- `/api/blockers` for blockers on the release.
- `/api/dependencies` for dependency relationships.

### Complete vs. Incomplete Statuses

**Complete** (terminal) statuses: `Closed`, `Deployed`, `Done`, `Verified`.
**Incomplete** (non-terminal) statuses: `Backlog`, `In Progress`, `Review`, `Reopened`.

Items with status `Duplicate` or `Cancelled` are excluded from primary counts.

### Milestone Completion

For each milestone in the release:
- `primary_total`: Count of primary work items (non-duplicate, non-cancelled) assigned to the milestone.
- `complete_primary`: Count of those with a complete status.
- `completion_pct`: `(complete_primary / primary_total) * 100`, rounded to 1 decimal place.
- Sort milestones by `milestone_id` ascending.

### Gating Work Items

Non-complete primary work items in the release. Sort IDs ascending, no duplicates.

### Blocker Analysis

- **Unresolved**: `status` is not `Resolved`.
- **High-impact**: `severity` is `High` or `Critical`.
- Count unresolved high-impact blockers grouped by exact `cause` string.

### Critical Dependency Chains

A critical chain exists when:
- A **gating** (non-complete) release work item depends on another item, AND
- The dependency item has a **non-complete** status (or is Duplicate/Cancelled).

Build ordered paths: `[blocked_release_item_id, dependency_id]`. For multi-hop chains, extend the path through intermediate dependencies. Sort chains lexicographically by the full path.

### Ship Decision

Use one of: `SHIP`, `SHIP_WITH_WATCH`, `NO_SHIP`.

Guidelines:
- `NO_SHIP`: Critical-severity unresolved blockers exist, OR readiness score below 0.70.
- `SHIP_WITH_WATCH`: High-severity unresolved blockers exist but no Critical, AND readiness score ≥ 0.70.
- `SHIP`: No unresolved High or Critical blockers, AND readiness score ≥ 0.85.

### Readiness Score

`readiness_score = complete_primary_count / primary_total`, rounded to 3 decimal places.

## Ordering Conventions

- **Work item ID lists**: Sort lexicographically (ascending).
- **Team lists**: Sort alphabetically.
- **Duplicate clusters**: Sort by `primary_id` ascending; `duplicate_ids` within each cluster sorted lexicographically.
- **Mix table rows**: Fixed order `NewFeature`, `TechDebt`, `Reliability`, `Security`.
- **Milestone lists**: Sort by `milestone_id` ascending.
- **Escalation queues**: Severity ascending, then age descending, then ID ascending.

## Output Format

Always match the provided `answer_template.json` exactly. Include all `required` fields. Do not include prose outside the JSON object.

## Common Pitfalls

- **Do not trust `mirror_status`** — use `status` for all state decisions.
- **Do not trust `legacy_category`** — use `work_type` plus labels for portfolio classification.
- **Labels with `stale-export`** indicate unreliable data that may need cross-verification.
- **Cross-mapped team/product pairs**: A work item may have a `team` and `product_area` that don't follow the typical mapping. Include items if both fields individually match the scope.
- **Late-closed items**: Items with `closed_at` outside the quarter window belong to a different reporting period.
- **Duplicate items that are themselves closed**: An item can have both `status=Closed` and a non-null `duplicate_of` — it is still a duplicate and must be excluded.
