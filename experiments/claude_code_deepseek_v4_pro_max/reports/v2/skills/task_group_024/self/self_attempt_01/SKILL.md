# Engineering Operations Workspace — Solver Skill

## Task types

The environment exposes three review/report tasks:

1. **Portfolio work-mix review** — compare completed work in a quarter against a
   target category mix, flag under-invested areas, and propose follow-up actions.
2. **SLA aging snapshot** — review open (and recently closed) reliability /
   security work items against SLA target days, surface overdue items, aging
   buckets, owner/team hotspots, and duplicate clusters.
3. **Release readiness rollup** — produce a Ship/Hold/NoShip decision for a
   release from milestone completion, gating work items, blocker causes, and
   critical dependency chains.

All data comes from the remote engineering-operations HTTP API. There is no
local database.

---

## Remote API entrypoint

```
BASE=http://34.46.77.124:9024
```

All endpoints return `{"count": N, "results": [...]}`. Pagination is not
exposed; every endpoint returns the full result set in one response.

### Endpoint reference

| Endpoint | Key query params | Notes |
|---|---|---|
| `GET /api/work-items` | `product`, `quarter`, `release_id` | `quarter` is optional; omit it to get all items for a product. |
| `GET /api/status-history` | `product` | Returns every status transition for every item in that product. Always fetch this — `status_export` on the work-item is a point-in-time snapshot and may be stale. |
| `GET /api/portfolio-targets` | `product`, `quarter` | One row per category. `target_percentage` is a whole number (e.g. 45 means 45 %). |
| `GET /api/teams` | — | Maps `team_id` → `name`, `product_line`, `director`. |
| `GET /api/owners` | — | Maps `owner_id` → `display_name`, `role`, `team_id`. |
| `GET /api/sla-policies` | — | One row per `(category, severity)` pair. `target_days` is the SLA deadline in days from creation. |
| `GET /api/releases/{id}` | — | Release metadata: `name`, `product`, `release_date`, `readiness_target` (0–1). |
| `GET /api/milestones` | `release_id` | Milestones with `critical` (bool), `target_date`. |
| `GET /api/milestone-items` | `release_id` | Maps `milestone_id` → `work_item_id`. |
| `GET /api/dependencies` | — | Global list. Filter in memory by the work-item IDs you care about. |
| `GET /api/blockers` | `active=true` | Only active blockers. Use `active=true` — resolved blockers are filtered server-side. |

### Fetching strategy

For any task, figure out which endpoints you need from the `endpoint_hints` in
`request_context.json`, then fetch them **all in parallel** (the API is
stateless — no ordering dependencies). After fetching, join and compute in
memory.

---

## Work-item fields (from `/api/work-items`)

```
id               : string   "WI-NNNN"           unique identifier
title            : string
description      : string
product          : string   "Identity Platform", "Payments", …
quarter          : string   "2025-Q4"           assigned quarter; may be null
work_type        : string   see classification below
status_export    : string   point-in-time status — prefer status-history
created_date     : string   "YYYY-MM-DD"
closed_date      : string   "YYYY-MM-DD" or null
updated_date     : string   "YYYY-MM-DD"
due_date         : string   "YYYY-MM-DD" or null
owner_id         : string   "OWN-…" or null
team_id          : string   "TEAM-…"
severity         : string   "S1" | "S2" | "S3" | "S4"
labels           : [string]
duplicate_cluster: string   "DUP-NNN" or null
escaped          : bool     true if the issue escaped to production
customer_impact  : bool
release_ids      : [string]
target_area      : string
```

---

## Status values and terminal states

Status values observed in `status-history` and `status_export`:

| Status | Terminal? | Meaning for aging / portfolio |
|---|---|---|
| `New` | No | Just created, not started |
| `In Progress` | No | Active work |
| `Blocked` | No | Cannot proceed |
| `Review` | No | Under review |
| `Verified` | **Yes** | Completed and verified |
| `Closed` | **Yes** | Formally closed |
| `Done` | **Yes** | Work complete |

**Key rule**: Always derive the true status at a point in time from
`status-history`, not from `status_export`. The `status_export` field is the
last recorded status overall and may be later than your as-of date. Query
`status-history`, filter to timestamps ≤ as_of_date, and take the latest
transition per work item.

---

## Classification: work_type → category

Every work item maps to exactly one of four portfolio categories. Use
`work_type` (not labels) as the primary classifier:

| work_type | Category |
|---|---|
| `Feature`, `Enhancement`, `Experiment` | **NewFeature** |
| `Refactor`, `Migration`, `Cleanup`, `Platform` | **TechDebt** |
| `Reliability`, `Bug`, `Incident` | **Reliability** |
| `Vulnerability`, `Compliance`, `Security` | **Security** |

Labels provide additional context (e.g. `tech-debt`, `sla-review`,
`release-gate`) but do **not** override the `work_type` → category mapping.

---

## Task 1: Portfolio work-mix review

### Goal

For a given `(product, quarter, as_of_date)`, count completed work items by
category, compare actual percentages against portfolio targets, compute gap in
basis points, and identify under-invested categories with follow-up actions.

### Eligibility

A work item is **eligible** when **all** of these hold:
1. `product` matches the review product.
2. `quarter` matches the review quarter (the `quarter` field on the item).
3. `closed_date` is not null **and** falls within the quarter's date range
   (inclusive of both start and end dates).

   Quarter date ranges:
   - Q1: Jan 1 – Mar 31
   - Q2: Apr 1 – Jun 30
   - Q3: Jul 1 – Sep 30
   - Q4: Oct 1 – Dec 31

4. The item reached a **terminal status** (Verified, Closed, or Done) on or
   before the as_of_date. Use `status-history` to confirm: filter transitions
   to ≤ as_of_date, take the latest, and check that its status is terminal.

Items that have a `closed_date` but whose latest status as of as_of_date is
still non-terminal (New / In Progress / Blocked / Review) are **not** eligible.

### Computing the mix

1. Classify each eligible item into one of 4 categories (see classification
   table above).
2. Count items per category → `count`.
3. `actual_percentage` = `count / eligible_total * 100`, rounded to **one
   decimal place**.
4. `target_percentage` comes from `/api/portfolio-targets` for the same
   `(product, quarter)`.
5. `gap_basis_points` = `(actual_percentage - target_percentage) * 100`,
   rounded to the **nearest integer** (a basis point is 1/100th of a
   percentage point).

   Example: actual = 22.2%, target = 30% → gap = (22.2 - 30) * 100 = -780.

### Under-invested categories

A category is **under-invested** when `gap_basis_points < 0` (actual below
target). List these in `under_invested_categories` as an array of category
name strings.

`largest_negative_gap_category` is the single category string with the most
negative `gap_basis_points`. If no category has a negative gap, use `null`. If
multiple tie for the most negative, pick the one that appears first in the
canonical order: NewFeature, TechDebt, Reliability, Security.

### Follow-up actions

For **each** under-invested category, generate one follow-up action:
```json
{
  "category": "<category>",
  "action": "IncreaseAllocation",
  "owner_team_id": "<team_id>"
}
```

`owner_team_id` is the team that owns the product. Look up the team from
`/api/teams` by matching `product_line` to the review product. If multiple
teams match, use the first.

### Evidence samples

For each of the 4 categories, populate `evidence_sample_ids` with up to 5
eligible work-item IDs from that category, sorted ascending. If a category has
no eligible items, use an empty array `[]`.

Pick the **first 5** by `id` (lexicographic sort). Do NOT pick randomly or by
date.

---

## Task 2: SLA aging snapshot

### Goal

For a given `(product, as_of_date, recent_closed_window_days)`, review
reliability and security work items that carry the `sla-review` label,
determine which are overdue, bucket them by age, and surface hotspots.

### Scope

Include work items where **all** of these hold:
1. `product` matches.
2. `labels` contains `"sla-review"`.
3. The item is **not** in a terminal state (Verified / Closed / Done) with a
   `closed_date` **before** the start of the recent-closed window.

   The window is: `[as_of_date - recent_closed_window_days + 1, as_of_date]`
   inclusive on both ends.

   Concretely:
   - Item in terminal state AND `closed_date` is before the window start →
     **exclude** (resolved too long ago).
   - Item in terminal state AND `closed_date` is within the window →
     **include** (recently resolved, still relevant for review).
   - Item NOT in terminal state → **include** regardless of closed_date.

   Determine terminal state as of `as_of_date` by consulting `status-history`.
   If the latest status as of `as_of_date` is Verified/Closed/Done, the item
   is terminal; otherwise it is open.

### Included items

`included_count` = number of items after applying the scope filter.
`included_work_item_ids` = their IDs, sorted ascending.

### Overdue determination

An included item is **overdue** when:
1. It is **not** in a terminal state as of `as_of_date` (it is still open), AND
2. `days_open > sla_target_days`, where:
   - `days_open` = difference in calendar days between `as_of_date` and
     `created_date`. Count the day of creation as day 0. So an item created on
     Feb 10 with as_of_date Feb 15 has `days_open = 5`.
   - `sla_target_days` comes from `/api/sla-policies`, matched on
     `(category, severity)`.

To find the SLA target:
1. Classify the work item into a category (using the `work_type` → category
   mapping).
2. Look up the SLA policy where `category` and `severity` match.
3. Use `target_days` from that policy.

Items in terminal state (Verified/Closed/Done) are **never** overdue — even if
they were closed after their SLA target.

`overdue_count` and `overdue_work_item_ids` (sorted ascending) capture the
overdue items.

### Aging buckets

For **included** items, compute `age_days = as_of_date - created_date` (same
day-counting rule as above) and assign to buckets:

| Bucket | Age range |
|---|---|
| `0-7`   | 0 – 7 days   |
| `8-14`  | 8 – 14 days  |
| `15-30` | 15 – 30 days |
| `31+`   | 31+ days     |

Count items in each bucket. Note: the template may use `aging_bucket_counts`
(object with keys `"0-7"`, `"8-14"`, `"15-30"`, `"31+"`) or `aging_buckets`
(array of `{"bucket": "0-7", "count": N}` objects). Match the template shape
exactly.

### Owner hotspots

For included items, group by `owner_id`. For each owner, compute:
- `overdue_count`: how many of that owner's included items are overdue.
- `max_age_days`: maximum `age_days` among that owner's included items.

Only include owners with `overdue_count > 0` in the hotspots array. Sort
ascending by `owner_id`. If no owners have overdue items, return an empty
array `[]`.

Items with `owner_id: null` are tracked separately (see "Missing owners"
below) and do **not** contribute to owner hotspots.

### Team hotspots

Same as owner hotspots, but grouped by `team_id`. Only include teams with
`overdue_count > 0`. Sort ascending by `team_id`.

### Duplicate clusters

Group included items by `duplicate_cluster` where the value is non-null (e.g.
`"DUP-001"`).

For each cluster:
- `cluster_id`: the `duplicate_cluster` value.
- `representative_work_item_id`: the item in the cluster with the **lowest**
  `id` (lexicographic sort, e.g. `"WI-0275" < "WI-0276"`).
- `member_ids`: all member item IDs, sorted ascending.

Sort clusters ascending by `cluster_id` in the output.

### Escaped severity count

Count included items where `escaped == true`. This is `escaped_severity_count`.

### Missing owners

`missing_owner_work_item_ids`: included items where `owner_id` is `null`.
Sorted ascending.

---

## Task 3: Release readiness rollup

### Goal

For a given `(release_id, as_of_date)`, produce a Ship/Hold/NoShip decision
with risk tier, milestone completion, gating work items, blocker breakdown,
critical dependency chain, and owner escalations.

### Data to fetch

1. `/api/releases/{release_id}` → release metadata
2. `/api/milestones?release_id=…` → milestones
3. `/api/milestone-items?release_id=…` → which items belong to which milestone
4. `/api/work-items?release_id=…` → all work items in the release
5. `/api/status-history?product=…` → status transitions (use the product from
   the release or from request_context)
6. `/api/dependencies` → all dependencies (filter in memory)
7. `/api/blockers?active=true` → active blockers (filter in memory)
8. `/api/owners` → owner lookup
9. `/api/teams` → team lookup

### Ship decision

The decision is `Ship`, `Hold`, or `NoShip`. Determine by:

1. Compute **milestone completion**: for each milestone, what percentage of
   its work items have reached a **terminal status** (Verified/Closed/Done) as
   of `as_of_date`? Use `status-history` to determine status at as_of_date.

   `completion_percentage` = `(items in terminal status / total items in milestone) * 100`,
   rounded to one decimal place.

2. Compute **overall readiness**: average completion across all milestones
   (unweighted), or the minimum across critical milestones.

3. Identify **gating work items**: items with label `"release-gate"` OR
   `"critical-path"` that are NOT in a terminal state as of as_of_date. These
   block the release.

4. Decision rules:
   - `Ship` when overall readiness ≥ `readiness_target` AND there are zero
     gating items still open.
   - `Hold` when there are open gating items BUT overall readiness is still
     ≥ `readiness_target * 0.8` (or some reasonable threshold), or when
     readiness is below target but recoverable.
   - `NoShip` when there are open gating items AND readiness is well below
     target, or when critical milestones are incomplete.

   **Practical heuristic**:
   - If zero open gating items AND all critical milestones are ≥ 100% →
     `Ship`.
   - If any open gating items OR any critical milestone < 100% → `Hold`.
   - If multiple open gating items AND critical milestone completion is very
     low → `NoShip`.
   - Default conservative choice when uncertain: `Hold`.

### Risk tier

- `Low`: zero gating items, all critical milestones at 100%, readiness ≥
  target.
- `Medium`: some open gating items or critical milestones not at 100%, but
  progress is reasonable.
- `High`: many open gating items, critical milestones well below 100%, or
  high-severity active blockers on gating items.

### Milestones

Sort by `milestone_id` ascending. For each:
- `milestone_id`: as returned by the API.
- `critical`: as returned by the API.
- `completion_percentage`: computed as described above (rounded to 1 decimal).

### Gating work items

IDs of items with label `"release-gate"` OR `"critical-path"` that are NOT in
terminal state as of as_of_date. Sort ascending.

### Blocker cause counts

For **gating work items only** (not all items in the release), look up active
blockers from `/api/blockers?active=true` where `work_item_id` matches a
gating item. Count by `blocker_type`.

The expected `blocker_type` values are:
`ExternalDependency`, `Environment`, `SecurityReview`, `Capacity`,
`DesignDecision`, `DataMigration`, `Vendor`, `OwnershipGap`.

Map the API's `blocker_type` field to these keys. The API returns values like
`"External Dependency"` (with a space) — map this to `"ExternalDependency"`
(without space). Similarly: `"Security Review"` → `"SecurityReview"`,
`"Design Decision"` → `"DesignDecision"`, `"Data Migration"` →
`"DataMigration"`, `"Ownership Gap"` → `"OwnershipGap"`, `"External Dependency"`
→ `"ExternalDependency"`.

If a blocker type seen in the API doesn't map to any known key, log a warning
and skip it.

Include all 8 keys in the output, even those with count 0.

### Critical dependency chain

Find the longest critical dependency path among gating items.

Algorithm:
1. From `/api/dependencies`, filter to edges where `critical == true` AND both
   `upstream_id` and `downstream_id` are gating work items (or items in the
   release scope).
2. Build a directed graph: `upstream_id → downstream_id` means upstream must
   complete before downstream.
3. Find the longest path from any source (node with no incoming edges in this
   subgraph) to any sink (node with no outgoing edges).
4. Output the IDs in dependency order (upstream → downstream). Do NOT sort
   this list; preserve topological order.

If there are multiple longest paths of equal length, prefer the one whose IDs
are lexicographically smallest at the earliest position where they differ.

If no critical dependencies exist among gating items, return an empty array
`[]`.

### Owner escalations

Collect `owner_id` for every **gating work item** (not all items). If a gating
item has `owner_id: null`, include the string `"UNASSIGNED"`. Sort ascending
(string sort). Deduplicate.

---

## Date handling rules

- All dates in the API are strings in `"YYYY-MM-DD"` format (dates) or ISO
  8601 `"YYYY-MM-DDTHH:MM:SS"` format (timestamps in status-history).
- When computing date differences (age, overdue), use **calendar days**, not
  24-hour periods. `2026-02-15 - 2026-02-10 = 5`.
- The day of creation counts as day 0. An item created on the as_of_date has
  `age_days = 0`.
- When filtering by date ranges, use **inclusive** bounds on both ends unless
  the task explicitly says otherwise.
- Quarter boundaries: Q1 = Jan–Mar, Q2 = Apr–Jun, Q3 = Jul–Sep, Q4 = Oct–Dec.

---

## Common pitfalls

1. **Using `status_export` instead of `status-history`**. `status_export` is
   the current overall status, which may be after your as_of_date. Always
   reconstruct status as of the as_of_date from `status-history`.

2. **Forgetting to filter status-history by as_of_date**. If you don't
   truncate at as_of_date, you'll see future transitions and misclassify open
   items as closed.

3. **Classification by labels instead of work_type**. The `work_type` field
   is the canonical category classifier. Labels like `"tech-debt"` or
   `"feature"` are supplementary signals but do not determine the category.

4. **Including non-terminal items in portfolio eligibility**. Items in
   Review/In Progress/Blocked are not "completed" even if they have a
   `closed_date`.

5. **Wrong gap sign convention**. Gap = actual − target. Negative means
   under-invested. Multiply by 100 for basis points.

6. **Not rounding consistently**. `actual_percentage` and
   `completion_percentage` round to 1 decimal place. `gap_basis_points`
   rounds to the nearest integer.

7. **SLA category matching**. When looking up SLA `target_days`, use the
   item's classified category (from `work_type`), not its labels. Match on
   both `category` and `severity`.

8. **Blocker type name mismatch**. The API returns blocker types with spaces
   (`"External Dependency"`, `"Security Review"`, etc.). The answer template
   expects CamelCase without spaces (`"ExternalDependency"`,
   `"SecurityReview"`, etc.). Always normalize.

9. **Duplicate cluster representatives**. The representative is the
   **lowest ID** in the cluster by string sort, not the earliest-created or
   the most severe.

10. **Owner hotspots include only overdue items**. An owner with included
    items but zero overdue items does NOT appear in `owner_hotspots`.

11. **Critical dependency chain ordering**. Preserve upstream → downstream
    order. Do not sort this list. The direction is: upstream completes before
    downstream can start.

12. **Sorting rules**. Most ID lists are sorted ascending (string/numeric
    sort — `"WI-0005" < "WI-0010"`). The critical dependency chain is the
    exception — preserve dependency order.

---

## Response format

All tasks require **JSON only** as the response. No markdown fences, no prose,
no commentary. The JSON must exactly match the keys and types in the provided
`answer_template.json`. Do not add extra keys. Do not omit keys even if their
value is 0, null, or empty array.

Use the template from `input/payloads/answer_template.json` as the definitive
shape reference.
