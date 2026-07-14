# Engineering Operations API Skill

## Base URL

`http://34.46.77.124:9024`

All endpoints are prefixed with `/api/`. Replace `<TASK_ENV_BASE_URL>` in task
prompts with this base URL. Do not use localhost or any other address.

---

## Endpoints

| Endpoint | Query Params | Returns |
|---|---|---|
| `/api/work-items` | `product`, `quarter`, `release_id` | Work items with `work_type`, `status_export`, `severity`, `due_date`, `closed_date`, `escaped`, `owner_id`, `team_id`, `duplicate_cluster`, `labels`, `release_ids` |
| `/api/status-history` | `product` | One entry per status transition: `work_item_id`, `status`, `timestamp` |
| `/api/portfolio-targets` | `product`, `quarter` | Per-category `target_percentage` (integer 0–100) |
| `/api/teams` | — | All teams: `team_id`, `product_line`, `name`, `director` |
| `/api/owners` | — | All owners: `owner_id`, `display_name`, `role`, `team_id` |
| `/api/sla-policies` | — | Per `category`+`severity`: `target_days` |
| `/api/releases/:id` | — | Release metadata: `release_id`, `name`, `product`, `release_date`, `readiness_target` |
| `/api/milestones` | `release_id` | Milestones: `milestone_id`, `name`, `critical`, `target_date` |
| `/api/milestone-items` | `release_id` | Mapping rows: `milestone_id` → `work_item_id` |
| `/api/blockers` | `active=true` | Active blockers: `blocker_id`, `blocker_type`, `work_item_id`, `severity`, `active` |
| `/api/dependencies` | — | All dependencies: `upstream_id`, `downstream_id`, `dependency_type`, `critical` |

---

## Source-of-Truth: Status History

**CRITICAL**: The `status_export` field on `/api/work-items` is often stale.
Always use `/api/status-history` to determine the **actual current status** of
a work item. The latest `status` in the history (by `timestamp`) is the true
status.

Terminal statuses (indicate completion): `Done`, `Closed`, `Verified`.

All other statuses (`New`, `In Progress`, `Review`, `Blocked`) are non-terminal
— the item is not yet complete.

---

## Work Type → Portfolio Category Mapping

Map every `work_type` to one of four portfolio categories:

| Portfolio Category | `work_type` values |
|---|---|
| **NewFeature** | `Feature`, `Experiment`, `Enhancement` |
| **TechDebt** | `Migration`, `Refactor`, `Cleanup`, `Platform`, `Bug` |
| **Reliability** | `Reliability`, `Incident` |
| **Security** | `Vulnerability`, `Compliance`, `Security` |

This mapping is deterministic and does NOT depend on `labels`, `owner_id`,
`team_id`, or any other field. Unknown `work_type` values should be treated as
an error — review the endpoint for new types before assuming a category.

---

## Task Type 1: Portfolio Work-Mix Review

**Task examples**: train_001 (Identity Platform Q4 2025), train_004 (Data Platform Q1 2026)

### Inputs
- `product`, `quarter`, `as_of_date`

### Steps

1. **Fetch work items**: `GET /api/work-items?product=...&quarter=...`
2. **Fetch status history**: `GET /api/status-history?product=...`
3. **Fetch portfolio targets**: `GET /api/portfolio-targets?product=...&quarter=...`
4. **Fetch teams**: `GET /api/teams`

### Eligibility Rule

A work item is **eligible** iff:
- It appears in the work-items response, AND
- Its **latest status in status-history** is a terminal status (`Done`, `Closed`, `Verified`), AND
- The **timestamp** of that terminal status entry is `≤ as_of_date`.

### Category Assignment

For each eligible item, map `work_type` → portfolio category using the table above.

### Computed Fields

- **`eligible_total`**: Count of eligible items.
- **`eligible_work_item_ids`**: List of eligible item IDs, sorted ascending.
- **`category_mix[i].count`**: Number of eligible items in that category.
- **`category_mix[i].actual_percentage`**: `round(count / eligible_total * 100, 1)` (one decimal place). If `eligible_total == 0`, use `0.0`.
- **`category_mix[i].target_percentage`**: From portfolio-targets response (as a number, not divided by 100).
- **`category_mix[i].gap_basis_points`**: `round((actual_percentage - target_percentage) * 100)`. Integer. A negative value means the category is under-invested relative to target.
- **`under_invested_categories`**: List of category names where `gap_basis_points < 0`, sorted by most negative gap first.
- **`largest_negative_gap_category`**: The first entry in `under_invested_categories`, or `null` if the list is empty.
- **`follow_up_actions`**: For each under-invested category, one entry with `category`, `action: "IncreaseAllocation"`, and `owner_team_id` set to the product's team (match `product_line` from `/api/teams`).
- **`evidence_sample_ids[category]`**: Up to 3 eligible work item IDs from each category, sorted ascending.

### Date Handling

`quarter` values like `"2025-Q4"` mean Oct 1 – Dec 31 2025. Use the `as_of_date` for eligibility cut-off, not the quarter end date — the two may differ.

---

## Task Type 2: SLA Aging Snapshot

**Task examples**: train_002 (Payments, as_of 2026-02-15), train_005 (Edge Services, as_of 2026-04-10)

### Inputs
- `product`, `as_of_date`, `recent_closed_window_days`

### Scope

**Only work items whose work_type maps to Reliability or Security categories**
are in scope. NewFeature and TechDebt items are excluded.

### Steps

1. **Fetch work items**: `GET /api/work-items?product=...`
2. **Fetch status history**: `GET /api/status-history?product=...`
3. **Fetch SLA policies**: `GET /api/sla-policies`
4. **Fetch teams**: `GET /api/teams`
5. **Fetch owners**: `GET /api/owners`

### Inclusion Rule (Recent Closed Window)

A scoped (Reliability/Security) work item is **included** iff:
- Its **latest status in status-history** is terminal (`Done`, `Closed`, `Verified`), AND
- The **timestamp** of that terminal status entry falls within the recent closed window:
  `as_of_date - recent_closed_window_days + 1 ≤ timestamp_date ≤ as_of_date` (inclusive both ends).

### Overdue Rule

An included item is **overdue** iff its `closed_date` (from work-items, or the terminal-status timestamp date) is **strictly after** its `due_date`.

### Aging Calculation

For each overdue item:
- **Age in days** = `(terminal_status_timestamp_date − due_date)`. Always compute as calendar days.
- Bucket into: `0-7`, `8-14`, `15-30`, `31+`.

### Computed Fields

- **`included_count`**: Count of included items.
- **`included_work_item_ids`**: Sorted ascending.
- **`overdue_count`**: Count of overdue among included.
- **`overdue_work_item_ids`**: Sorted ascending.
- **`aging_bucket_counts` / `aging_buckets`**: Count of **overdue** items per bucket. Items closed on or before their due date are not counted in any aging bucket (they are not overdue).
- **`owner_hotspots`**: For overdue items only — group by `owner_id`, compute `overdue_count` and `max_age_days`. Sort by `overdue_count` descending, then `max_age_days` descending. Include only owners with `overdue_count > 0`.
- **`team_hotspots`**: Same pattern grouped by `team_id`.
- **`duplicate_clusters` / `duplicate_cluster_representatives`**: For **included** items where `duplicate_cluster` is non-null — group by cluster ID. Pick the item with the **lowest ID** as `representative_work_item_id`. List all member IDs sorted ascending. Sort clusters by `cluster_id`.
- **`escaped_severity_count`**: Count of included items where `escaped == true`.
- **`missing_owner_work_item_ids`**: Included items where `owner_id` is `null`/`None`. Sorted ascending.

### SLA Policy Usage

The SLA policy endpoint provides `target_days` per `category` + `severity`. This
defines the maximum allowed cycle time for items. The SLA aging snapshot
measures *overdue* items against their due dates, not against SLA target_days
directly. The policies are informational for the aging review context.

---

## Task Type 3: Release Readiness Rollup

**Task example**: train_003 (REL-PAY-2026Q1, as_of 2026-02-28)

### Inputs
- `release_id`, `as_of_date`

### Steps

1. **Fetch release**: `GET /api/releases/:release_id`
2. **Fetch milestones**: `GET /api/milestones?release_id=...`
3. **Fetch milestone items**: `GET /api/milestone-items?release_id=...`
4. **Fetch work items**: `GET /api/work-items?release_id=...` AND `GET /api/work-items?product=...` (combine)
5. **Fetch status history**: `GET /api/status-history?product=...`
6. **Fetch blockers**: `GET /api/blockers?active=true`
7. **Fetch dependencies**: `GET /api/dependencies`
8. **Fetch owners**: `GET /api/owners`

### Milestone Completion Percentage

For each milestone:
- `completion_percentage` = `round(N_terminal / N_total * 100, 1)` rounded to one decimal place.
- `N_terminal`: count of items assigned to the milestone whose latest status-history status is terminal AND terminal timestamp ≤ as_of_date.
- `N_total`: all items assigned to the milestone (from milestone-items).
- If `N_total == 0`, completion is `100.0`.
- Sort milestone objects by `milestone_id` ascending.

### Gating Work Items

A work item is **gating** iff:
- It is associated with the release (appears in work-items for the release or in milestone-items), AND
- Its latest status-history status is **NOT terminal** at `as_of_date`, OR its terminal timestamp is after `as_of_date`.

Sort gating IDs ascending.

### Ship Decision

Derive from the overall picture:

| Condition | Decision |
|---|---|
| All critical milestones at 100% AND zero gating items AND no active blockers on release items | `Ship` |
| Some concerns but release date not passed; critical milestones near complete | `Hold` |
| Active blockers on critical-path items; multiple critical milestones incomplete; release date passed with open gates | `NoShip` |

Use the `release_date` and `readiness_target` from the release as additional
context. If `as_of_date ≥ release_date` and gating items remain, lean toward
`NoShip`.

### Risk Tier

| Condition | Tier |
|---|---|
| No active blockers, all critical milestones ≥ 90%, few or no gating items | `Low` |
| Some active blockers or 1–2 critical milestones incomplete | `Medium` |
| Multiple active blockers, critical milestones incomplete, release date passed with open gates | `High` |

### Blocker Cause Counts

For **all** active blockers where the `work_item_id` belongs to the release
scope (appears in work-items or milestone-items for this release), count by
`blocker_type`. The API returns types with spaces (e.g., `"External Dependency"`),
but the output JSON uses PascalCase without spaces. Map as follows:

| API `blocker_type` | Output Key |
|---|---|
| `External Dependency` | `ExternalDependency` |
| `Security Review` | `SecurityReview` |
| `Data Migration` | `DataMigration` |
| `Design Decision` | `DesignDecision` |
| `Ownership Gap` | `OwnershipGap` |
| `Environment` | `Environment` |
| `Capacity` | `Capacity` |
| `Vendor` | `Vendor` |

Include all eight keys in the output, with a count of 0 for any type that has
no matching blockers. If a new/unknown `blocker_type` appears, use the
PascalCase-without-spaces convention derived from the API value.

### Critical Dependency Chain

From the dependencies endpoint, filter to chains where either endpoint is a
release-scoped work item AND `critical == true`. Trace from upstream to
downstream, ordering so each item appears after its dependencies. The result
is a topologically sorted list of work item IDs. Do NOT re-sort — preserve
dependency order.

### Owner Escalations

For each gating work item, collect its `owner_id`. If `owner_id` is null/None,
use the literal string `"UNASSIGNED"`. Sort ascending. Deduplicate.

---

## General Rules and Pitfalls

### Always Use Status-History, Not status_export

The `status_export` field on work-items is a snapshot that is frequently
outdated. Never use it to determine whether an item is complete. Always
consult the `/api/status-history` endpoint and use the latest entry.

### Closed Date vs Terminal Timestamp

The `closed_date` field on work-items generally matches the date portion of the
terminal status timestamp from status-history. When they differ (rare), prefer
the status-history timestamp.

### Date Comparison Precision

- `as_of_date` comparisons are date-only (ignore time portions). An item with
  terminal timestamp `2025-12-31T23:59:00` is complete on `as_of_date = 2025-12-31`.
- Recent closed window boundaries are inclusive: items closed exactly on the
  window start or end date are included.

### Sorting Conventions

Unless explicitly stated otherwise (like critical dependency chain):
- Work item IDs, owner IDs, team IDs: **ascending alphanumeric** sort.
- Milestones: **ascending by milestone_id**.
- Categories/buckets: use the fixed order from the answer template.

### Work Items Not in Work-Items Response

If a work item ID appears in status-history, milestone-items, or dependencies
but NOT in the work-items response for the scoped product, it may still be
relevant (e.g., cross-team dependencies). Include it when the task context
calls for it (release readiness, dependency chains), but exclude it from
portfolio category counting and SLA scope.

### Duplicate Cluster Handling

Duplicate clusters link related work items (e.g., same customer signal). When
reporting clusters:
- Use the cluster ID from `duplicate_cluster` field.
- The representative is the item with the lowest alphanumeric ID in the cluster.
- Include ALL members of the cluster that are in the included/review population.
- Clusters with only one member in the population should still be reported.

### Team ID for Follow-Up Actions

Use the `product_line` field from `/api/teams` to match a product name to its
team. The `owner_team_id` in follow-up actions should be the team's `team_id`,
not an individual owner's ID.

### Basis Points Calculation

1 basis point = 0.01 percentage point.
`gap_basis_points = round((actual_pct - target_pct) * 100)`.
Example: actual 12.5%, target 15% → gap = -250 bps.

### Rounding

- Percentages: round to 1 decimal place using standard rounding (`round(x, 1)`).
- Basis points: round to integer.
- If `eligible_total == 0`, all percentages are `0.0` and gaps are `0`.

### Escaped Items

An `escaped` field of `true` means the item was discovered after causing
customer-visible impact. Count escaped items regardless of whether the item
is overdue.

### Missing Owners

Items with `owner_id: null` should be flagged in `missing_owner_work_item_ids`.
For hotspot arrays, null owners should be skipped (they appear in the missing
list instead). For owner escalations, use `"UNASSIGNED"` as the literal string.

### API Response Shapes

All list endpoints return `{ "count": N, "results": [...] }`. Single-resource
endpoints return the object directly. The status-history endpoint returns
`{ "results": [...] }` (no count wrapper for some products — always check).

### Filtering Work Items by Quarter vs Product

- `/api/work-items?product=X&quarter=Y` returns items assigned to that product+quarter.
- `/api/work-items?product=X` (no quarter) returns ALL items for that product.
- `/api/work-items?release_id=X` returns items associated with that release.
- For portfolio reviews, always include the `quarter` filter.
- For SLA/release tasks, fetch by `product` (no quarter) to get the full picture.

### Cross-Checking Work Items Across Endpoints

Items in milestone-items, blockers, or dependencies may reference work items
that aren't in the primary work-items response. Always fetch the full set:
use both `product` and `release_id` filters and merge results (by ID).
