---
name: portfolio-management-solver
description: Solve portfolio management tasks by querying a REST API environment with work items, mix targets, SLA policies, releases, milestones, blockers, and dependencies. Covers portfolio mix reviews, SLA aging audits, and release readiness assessments.
---

# Portfolio Management Solver

Use this guide to solve portfolio management, SLA, and release-readiness tasks against a shared REST API environment. Do not assume you are given a fixed dataset; query the live environment for every task.

## Environment Setup

Read the separately supplied `environment_access.md` for the base URL and auth token. The base URL is typically `<TASK_ENV_BASE_URL>` or a concrete host. Use the token as a header on every request:

```text
X-Env-Token: <token-value>
```

All endpoints return JSON and require this header. Use `curl` or equivalent to make requests. Always accept JSON: `Accept: application/json`.

## API Reference

All endpoints are rooted at the base URL. Endpoints available:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/api/work-items` | GET | List all work items (supports query params) |
| `/api/work-items/{item_id}` | GET | Single work item by id |
| `/api/mix-targets` | GET | Mix target policy rows (filter by `scope_id`) |
| `/api/sla-policy` | GET | SLA policy and thresholds |
| `/api/releases` | GET | All releases (filter by `release_id` or other params) |
| `/api/releases/{release_id}` | GET | Single release by id |
| `/api/milestones` | GET | Milestones (filter by `release_id`) |
| `/api/dependencies` | GET | Work-item dependency edges |
| `/api/blockers` | GET | Blocker records |
| `/api/query` | POST | Restricted SQL read-only query endpoint |

### Query Parameters

List endpoints accept query parameters. Common ones:

- `/api/work-items?status=Closed&quarter=<quarter>&team=<team>` — filter work items
- `/api/work-items?team=<team1>&team=<team2>` — multi-team filter
- `/api/mix-targets?scope_id=<scope_id>` — single target row
- `/api/milestones?release_id=<release_id>` — milestones for a release
- `/api/dependencies?blocked_id=<work_item_id>` — dependencies blocking a work item

When unsure about query parameters, retrieve the full collection and filter client-side. The datasets are small enough for this approach.

### SQL Query Endpoint

The `/api/query` endpoint accepts:

```json
{"sql": "SELECT ... FROM ... WHERE ..."}
```

Use it for cross-cutting queries that combine multiple entity types. Keep queries read-only. The work items table is typically named `work_items` and follows the same field naming as the REST responses (snake_case).

## Work Item Fields

A work item record has these key fields. Always trust the authoritative fields on the work item itself, not mirrored or derived fields on other records.

| Field | Description | Usage |
|---|---|---|
| `id` | Unique work item id, e.g. `<example_work_item_id>` | Primary identifier |
| `title` | Human-readable title | Used only for disambiguation |
| `type` | Work item type label | One source for category resolution |
| `category` | Portfolio category | **Authoritative** for portfolio classification |
| `status` | Current status (`Closed`, `Open`, `In Progress`, `Cancelled`, etc.) | Scope filtering |
| `team` | Owning team | Scope filtering |
| `product_area` | Product area label | Scope filtering |
| `quarter` | Planning quarter, e.g. `<year>-Q<number>` | Scope filtering |
| `closed_at` | ISO-8601 timestamp of closure | Ordering, aging |
| `created_at` | ISO-8601 creation timestamp | Aging calculations |
| `owner` | Assigned owner name or null | Hotspot analysis, missing-owner detection |
| `severity` | SLA severity, e.g. `S1`, `S2`, `S3`, `S4` | SLA classification |
| `sla_days` | SLA target in days | Overdue calculation |
| `release_id` | Linked release if any | Release readiness |
| `milestone_id` | Linked milestone if any | Milestone completion |
| `duplicate_of` | Id of the primary record if this is a duplicate | Primary/duplicate resolution |
| `mirror_status` | Stale mirrored status field | **Ignore for authoritative truth** |
| `legacy_category` | Stale mirrored category field | **Ignore for classification** |
| `is_primary` | Boolean or equivalent flag | Primary record identification |
| `labels` | Array of tag strings | May contain category-like labels; defer to `category` field |
| `priority` | Priority level | For escalation ordering when severity is equal |
| `sla_deadline` | Computed or stored SLA deadline date | Overdue detection against as-of date |
| `impact` | Blocker impact level (`high`, `medium`, `low`) | Blocker filtering |
| `cause` | Blocker cause text | Blocker classification |
| `depends_on_id` | Upstream dependency id | Dependency chains |
| `blocked_id` | Downstream blocked id | Dependency chains |
| `dependency_status` | Status of the dependency link | Whether the dependency is still active |

### Primary vs Duplicate Records

Some work items are duplicates that point at another work item as their primary. Detect duplicates through:

1. The `duplicate_of` field: if non-null, the record is a duplicate and the referenced id is its primary.
2. The `is_primary` field: if explicitly false, the record is not primary.
3. The `status` field: `Cancelled` records are not primary closed work.

**Rule**: Count and analyze only primary records for portfolio mix, SLA statistics, and release readiness. Report duplicate ids and cancelled ids separately in the appropriate exclusion/dedup fields. Never double-count a work item through both its primary and duplicate records.

### Category Resolution

When classifying a work item into exactly one of these portfolio categories: `NewFeature`, `TechDebt`, `Reliability`, `Security`:

1. **Use the `category` field on the work item as the authoritative source.**
2. Ignore `legacy_category` and `mirror_status` — these are stale.
3. If the `category` field is missing or ambiguous, check the `type` field as a secondary signal, then labels, then title keywords. But prefer the authoritative category field.
4. Every included work item maps to exactly one category.

### Overdue Calculation

For SLA aging tasks:

1. Retrieve the SLA policy from `/api/sla-policy` to understand severity-based SLA targets (days).
2. For each included primary work item, compute the age as of the as-of date: `age_days = as_of_date - created_at.date()` (or use `sla_deadline` if available).
3. A work item is overdue if `age_days > sla_days` (or if `as_of_date > sla_deadline`).
4. Recent-closed-window items (closed within the window from the as-of date) are included in the primary population but may affect breach rate differently depending on the task's rules. Read the prompt carefully for whether recently-closed items count toward the breach denominator.
5. Breach rate = overdue primary count / included primary count, rounded to 3 decimal places.

### Aging Bucket Assignment

Assign each overdue primary work item to one of these buckets based on its age in days: `0-3`, `4-7`, `8-14`, `15-30`, `31+`. Count items per bucket. Some tasks use a severity-based breakdown instead — follow the answer template.

### Escalation Ordering

When an escalation queue is required, order overdue primary work items by:
1. Severity descending (S1 first, then S2, S3, S4).
2. Within the same severity, by priority descending (highest priority first).
3. Within the same priority, by age descending (oldest first).
4. Within the same age, by id ascending.

## Portfolio Mix Tasks

### Target Mix Retrieval

For portfolio mix tasks, retrieve the target mix from `/api/mix-targets`, filtering by the `scope_id` given in the prompt. The target row provides target percentages for each of the four categories.

### Population Selection

1. Collect all closed work items matching the quarter, teams, and product areas from the prompt.
2. Exclude duplicates (records with a non-null `duplicate_of` field) and cancelled records. Report these in the exclusion fields.
3. Exclude distractor records — items that appear to match the scope (same quarter, teams, or product area) but are not primary closed portfolio work for the mix. These include open items, items in other quarters that were incorrectly scoped, or items whose `is_primary` flag is false for reasons other than being a duplicate.
4. The remaining records are the included population.

### Mix Computation

1. Count included items per category (`NewFeature`, `TechDebt`, `Reliability`, `Security`).
2. Compute actual percentages: `actual_pct = (count / total_included) * 100`, rounded to 1 decimal place.
3. Compute gaps: `gap_pct = actual_pct - target_pct`, rounded to 1 decimal place.
4. Identify under-invested categories (negative gap) ordered from most negative to least negative, or the single largest deficit category depending on the answer template.

### Follow-Up Action Selection

- If there are negative gaps: use `REBALANCE_CAPACITY` with the `LARGEST_NEGATIVE_GAP` rationale, pointing at the most under-invested category as primary and (if applicable) the second most under-invested as secondary.
- If there are no negative gaps: use `MAINTAIN_CURRENT_MIX` with `NO_NEGATIVE_GAPS`.
- If data quality issues are evident: use `INVESTIGATE_DATA_QUALITY` with `DATA_CONFLICT`.
- When `owner_team` is required, use the team with the largest capacity allocation to the recommended category, or the team with the most items in that category.

## SLA Aging Tasks

### Population Selection

1. Collect work items matching the teams and categories from the prompt.
2. Exclude duplicates and cancelled records.
3. Include only primary records in the counting population.

### Overdue Identification

1. Get the SLA policy thresholds.
2. For each primary item, compute whether it is overdue against the as-of date using its `sla_deadline` or `created_at` + `sla_days`.
3. Recent-closed items (closed within the recent window before the as-of date) are included in the primary count but check the task prompt for whether they are excluded from overdue counting.

### Hotspot Detection

1. Group overdue primary items by (team, owner).
2. The hotspot is the (team, owner) pair with the highest count.
3. If an owner is missing, label it as `UNASSIGNED`.
4. If multiple pairs tie, prefer the team that appears first alphabetically, then the owner that appears first alphabetically.

### Duplicate Clusters

1. For each primary record that has one or more duplicates, create a cluster: `{"primary_id": "...", "duplicate_ids": ["...", "..."]}`.
2. Sort clusters by `primary_id` ascending.
3. Sort `duplicate_ids` within each cluster ascending.
4. Report only clusters where the primary is part of the included population.

## Release Readiness Tasks

### Release Data Retrieval

1. Get the release record from `/api/releases/{release_id}`.
2. Get all milestones for the release from `/api/milestones?release_id=...`.
3. Get work items linked to the release (filter by `release_id`).
4. Get blockers linked to the release work items.
5. Get dependency chains from `/api/dependencies`.

### Milestone Completion

For each milestone:
- `primary_total` = count of primary work items assigned to this milestone.
- `complete_primary` = count of those with status `Closed` or `Done`.
- `completion_pct = (complete_primary / primary_total) * 100`, rounded to 1 decimal place.
- Sort milestones by `milestone_id` ascending.

### Ship Decision

- `SHIP`: All milestones at 100%, no open high-impact blockers, no gating incomplete work items.
- `SHIP_WITH_WATCH`: High completion (>= 85% readiness), minor gaps that are tracked but not blocking.
- `NO_SHIP`: Incomplete gating work items or high-impact unresolved blockers present.

Determine readiness based on the gating rule: a work item gates readiness if it is linked to the release, is not complete, and has unresolved high-impact blockers or incomplete upstream dependencies.

### Blocker Analysis

1. Filter blockers to those with `impact` = `high`.
2. Filter to unresolved blockers (status not `Resolved` or `Closed`).
3. Count by exact `cause` text.
4. Only include blockers linked to release work items.

### Critical Dependency Chains

1. For each gating work item, trace its dependency chain: follow `depends_on_id` links until you reach a work item with no incomplete upstream dependency.
2. Report the ordered path from the gating/release work item to the non-complete blocking dependency.
3. Sort chains lexicographically by the full path (join ids and compare).
4. If there are no critical chains, return an empty array.

### Readiness Score

`readiness_score = total_completed_primary / total_release_primary`, rounded to 3 decimal places. Count all primary work items linked to the release, including across all milestones.

## Field Mapping for Common Schemas

Not every task uses the same answer field names. Map the correct fields according to the provided `answer_template.json`. Common variants:

**Portfolio mix tasks** may use any of:
- `category_percentages` + `gap_table` + `under_invested_categories` + `follow_up_action`
- `mix_table` + `largest_deficit_category` + `recommended_action`
- `exclusion_flags` (with `excluded_duplicate_ids` and `excluded_cancelled_ids`) or `excluded_distractor_ids`

**SLA aging tasks** may use any of:
- `aging_bucket_counts` + `team_overdue_counts` + `top_hotspot`
- `overdue_counts_by_severity` + `escalation_queue_ids`

Always read the `answer_template.json` to determine the exact output shape.

## Sorting Conventions

Apply these ordering rules consistently across all tasks:

| Data | Order |
|---|---|
| Work item id lists | Lexicographically ascending (standard string sort) |
| Team lists in scope | Alphabetically ascending unless the answer template specifies a fixed order |
| Gap table rows | `NewFeature`, `TechDebt`, `Reliability`, `Security` |
| Milestone completion rows | By `milestone_id` ascending |
| Duplicate clusters | By `primary_id` ascending |
| Duplicate ids within a cluster | Lexicographically ascending |
| Critical dependency chains | Lexicographically by the joined path string |
| Under-invested categories | Most negative gap to least negative gap |
| Included work item ids | By `closed_at` ascending, then by id ascending (unless the template says otherwise) |

## Precision Rules

- Percentages: round to 1 decimal place (e.g., `66.7`, `0.0`, `100.0`).
- Breach rates and readiness scores: round to 3 decimal places (e.g., `0.545`, `0.688`).
- Gap values: round to 1 decimal place, can be negative.
- Counts: integers.

## Output Format

Produce exactly the JSON object described by the task's `answer_template.json`. The template is always available in `input/payloads/answer_template.json` and defines required fields, types, enums, and ordering constraints. Fill every required field. Do not include prose, markdown fences, or commentary outside the JSON object.

If the task prompt specifies `input/payloads/answer_template.json` as the format, read that file first and use it as the structural contract. The template may include JSON Schema, descriptive comments, or example shapes.

## Common Pitfalls

- **Stale mirror fields**: Never classify work items by `mirror_status` or `legacy_category`. Always use the authoritative `category` field on the work item itself.
- **Double-counting**: A work item and its duplicate are the same logical item. Count only the primary, report the duplicate separately.
- **Cancelled records**: These are excluded from mix populations and SLA statistics. Report them in the appropriate exclusion field.
- **Distractor records**: Items that share scope attributes but are not primary closed work. Check `status`, `is_primary`, and `duplicate_of`.
- **SLA denominator**: The denominator for breach rate is the included primary count, not the overdue count. Double-check the task rules for whether recently-closed items are included in the denominator.
- **Gap vs deficit**: A negative gap means under-investment. The "largest deficit" is the most negative gap.
- **Escalation order vs id sort**: Escalation queues use severity → priority → age ordering, not lexicographic id ordering. Regular id lists use lexicographic ordering.
