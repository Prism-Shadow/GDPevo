# Engineering Operations Workspace — Solver Skill

## Environment

```
Base URL: http://34.46.77.124:9024
```

All tasks use this remote API. Never use localhost. The request_context payload in each task provides endpoint hints and business context.

---

## Task Types & Solution Workflows

There are three distinct task types. Identify which one you're solving from the prompt and `request_context.json`.

### Type A: Portfolio Work-Mix Review

**What it asks:** Compare completed work against target allocation percentages for a product+quarter, identify under-invested categories, propose follow-up actions.

**API calls (in order):**

1. `GET /api/work-items?product=<Product>&quarter=<Quarter>` — scoped work items
2. `GET /api/status-history?product=<Product>` — per-item status timeline
3. `GET /api/portfolio-targets?product=<Product>&quarter=<Quarter>` — target % per category
4. `GET /api/teams` — team→product_line mapping for owner_team_id

**Work-item response fields (every task type):**
| Field | Type | Notes |
|---|---|---|
| `id` | string | e.g. `"WI-0001"` |
| `work_type` | string | `Feature`, `Experiment`, `Enhancement`, `Reliability`, `Incident`, `Bug`, `Vulnerability`, `Compliance`, `Security`, `Migration`, `Refactor`, `Cleanup`, `Platform` |
| `labels` | string[] | Category hints: `"feature"`, `"tech-debt"`, `"reliability"`, `"reliability-review"`, `"security"`, `"vulnerability"`, `"compliance"`, plus topic labels |
| `severity` | string | `S1`–`S4` |
| `status_export` | string | Current status: `New`, `In Progress`, `Blocked`, `Review`, `Verified`, `Closed`, `Done` |
| `created_date` | string | `YYYY-MM-DD` |
| `closed_date` | string or null | `YYYY-MM-DD` |
| `updated_date` | string | `YYYY-MM-DD` |
| `due_date` | string | `YYYY-MM-DD` |
| `duplicate_cluster` | string or null | e.g. `"DUP-024"` |
| `escaped` | boolean | Severity was upgraded post-triage |
| `customer_impact` | boolean | |
| `owner_id` | string or null | |
| `team_id` | string | |
| `product` | string | |
| `quarter` | string | e.g. `"2025-Q4"` |
| `release_ids` | string[] | |
| `target_area` | string | |
| `title` | string | |
| `description` | string | |

**Eligibility for portfolio mix:**
- Items are **eligible** if their terminal status (from status-history) is `Done`, `Closed`, or `Verified` **by the as_of_date**.
- Status-history returns `{work_item_id, status, timestamp, source}` entries sorted chronologically. The last status entry on or before the as_of_date determines the item's effective status.
- **Duplicate handling:** Items in the same `duplicate_cluster` are deduplicated. Only the lowest-ID item per cluster that meets the eligibility status is included; all other cluster members are excluded even if they individually meet the status criterion. If no member of a cluster meets the status requirement, the entire cluster is excluded.
- `eligible_work_item_ids`: sorted ascending.

**Category classification:**
Each eligible item maps to one of four categories: `NewFeature`, `TechDebt`, `Reliability`, `Security`. Derive this from the item's `work_type` and `labels` fields:

| Category | Primary work_type values | Primary label signals |
|---|---|---|
| NewFeature | `Feature`, `Experiment`, `Enhancement` | `"feature"` (and NO stronger signal present) |
| TechDebt | `Migration`, `Refactor`, `Cleanup`, `Platform` | `"tech-debt"` (and NO stronger signal present) |
| Reliability | `Reliability`, `Incident`, `Bug` | `"reliability"`, `"reliability-review"`, `"slo"` |
| Security | `Vulnerability`, `Compliance`, `Security` | `"security"`, `"vulnerability"`, `"compliance"` |

**Priority when labels conflict across categories:**
Security > Reliability > TechDebt > NewFeature

Example: an item with labels `["reliability", "tech-debt"]` → Reliability wins over TechDebt. An item with `["reliability", "security"]` → Security wins.

**Important edge case:** Certain topic labels (like `"token-rotation"`) act as Security signals even when the primary `work_type` is feature-like. The presence of `"compliance"` or `"vulnerability"` in labels always signals Security. When in doubt, Security-tagged labels take precedence over all others.

**Portfolio-targets response:** Returns `{category, product, quarter, target_percentage}` entries. The `target_percentage` is a whole number (e.g. `45` meaning 45%).

**Calculations:**
- `count`: number of eligible items in the category
- `eligible_total`: sum of all category counts
- `actual_percentage`: `round(count / eligible_total * 100, 1)` — one decimal place
- `target_percentage`: from the portfolio-targets API for that category
- `gap_basis_points`: `round((actual_percentage - target_percentage) * 100)` — integer. One basis point = 0.01 percentage point.

**Under-invested rule:**
`under_invested_categories` = categories where `gap_basis_points ≤ -500` (at least 5 percentage points under target). Sorted by gap ascending (most negative first).

**largest_negative_gap_category:** The single category with the most negative `gap_basis_points`, regardless of whether it meets the -500 threshold. If no category has a negative gap, this is `null`.

**follow_up_actions:** For each `under_invested_categories` entry, create:
```json
{"category": "<name>", "action": "IncreaseAllocation", "owner_team_id": "<TEAM-ID>"}
```
The `owner_team_id` is the team whose `product_line` matches the task's product (from `/api/teams`). If no under-invested categories, this is `[]`.

**evidence_sample_ids:** For each of the four categories, include up to 3 eligible item IDs (the first 3 by ascending ID order).

### Type B: SLA Aging Snapshot

**What it asks:** For a given product, review reliability/security work items, flag overdue items against SLA targets, produce aging buckets, owner/team hotspots, duplicate clusters, escaped-severity count, and missing-owner items.

**API calls:**
1. `GET /api/work-items?product=<Product>` — all items (no quarter filter for SLA tasks)
2. `GET /api/status-history?product=<Product>`
3. `GET /api/sla-policies` — SLA target_days by (category, severity)
4. `GET /api/teams`
5. `GET /api/owners`

**SLA-policies response schema:**
```json
{"category": "Reliability", "severity": "S2", "target_days": 5, "applies_to_status": [...]}
```
Categories: `NewFeature`, `TechDebt`, `Reliability`, `Security`. Severities: `S1`–`S4`. Look up each item's SLA target by its **category** (derived as in Type A) and **severity**.

**Inclusion rule:**
An item is **included** in the review if it is NOT permanently closed before the recent-closed window. Specifically:
- If `closed_date` is set AND `as_of_date - closed_date > recent_closed_window_days` → **excluded** (closed too long ago)
- Otherwise → **included** (still open, or recently closed within the window)

`included_count` = number of included items. `included_work_item_ids` sorted ascending.

**Overdue rule:**
An item is **overdue** if its **age at closure** (for closed items) or **current age** (for open items) exceeds its SLA `target_days`:
- Open items: `age = as_of_date - created_date` (days)
- Closed items: `age = closed_date - created_date` (days)
- Overdue if `age > target_days`

`overdue_count` and `overdue_work_item_ids` (sorted ascending).

**Aging buckets (for all included items):**
Bucket every included item by its age in days:
- Open items: `age = as_of_date - created_date`
- Closed items: `age = closed_date - created_date` (the age at which it resolved)
- For items with `closed_date` set but `closed_date > as_of_date`, treat as open (use `as_of_date - created_date`)
- `0-7`: age ≤ 7
- `8-14`: 8 ≤ age ≤ 14
- `15-30`: 15 ≤ age ≤ 30
- `31+`: age ≥ 31

The template key may be `aging_bucket_counts` (object) or `aging_buckets` (array of `{bucket, count}`). Match the template's exact shape.

**Owner hotspots:** Group overdue items by `owner_id` (skip null owners). For each owner: `overdue_count` and `max_age_days`. Sort by `overdue_count` descending, then by `owner_id` ascending as tiebreaker. Include only owners with `overdue_count > 0`.

**Team hotspots:** Same as owner hotspots but grouped by `team_id`.

**Duplicate clusters:** From `duplicate_cluster` field on work items. For each cluster that has at least one member in the **included** population, output:
```json
{"cluster_id": "<DUP-NNN>", "representative_work_item_id": "<lowest-ID>", "member_ids": ["<all members sorted ascending>"]}
```
The representative is the lowest-ID member of that cluster within the included set.

**Escaped severity:** Count of included items where `escaped = true`.

**Missing owners:** List of included item IDs where `owner_id` is null, sorted ascending.

### Type C: Release Readiness & Gating Rollup

**What it asks:** For a given release, assess milestone completion, identify gating work items, count blocker causes, trace the critical dependency chain, and produce a ship decision.

**API calls:**
1. `GET /api/releases/<release_id>` — release metadata (name, product, release_date, readiness_target)
2. `GET /api/milestones?release_id=<release_id>` — milestones with `critical` flag
3. `GET /api/milestone-items?release_id=<release_id>` — work-item→milestone assignments
4. `GET /api/work-items?release_id=<release_id>` — release-scoped work items
5. `GET /api/status-history?product=<Product>` — for checking item completion
6. `GET /api/dependencies` — all dependency edges
7. `GET /api/blockers?active=true` — only active (unresolved) blockers
8. `GET /api/owners`
9. `GET /api/teams`

**Milestone completion percentage:**
For each milestone, determine which of its assigned work items are "complete". An item is complete if its latest status (from status-history, on or before as_of_date) is `Done`, `Closed`, or `Verified`.
```
completion_percentage = round(complete_count / total_assigned * 100, 1)
```
Sort milestone objects by `milestone_id` ascending.

**Gating work items:**
Items in the release scope that have at least one active blocker (from `/api/blockers?active=true`). The item's own status does not matter — an item can be Done/Closed yet still gating if its blocker remains unresolved. Sort ascending.

**Blocker cause counts:**
Count active blockers by `blocker_type`, mapped to these keys:

| API `blocker_type` | Output key |
|---|---|
| `External Dependency` | `ExternalDependency` |
| `Environment` | `Environment` |
| `Security Review` | `SecurityReview` |
| `Capacity` | `Capacity` |
| `Design Decision` | `DesignDecision` |
| `Data Migration` | `DataMigration` |
| `Vendor` | `Vendor` |
| `Ownership Gap` | `OwnershipGap` |

Only count blockers whose `work_item_id` belongs to the release scope (check against work items from step 4). All 8 keys must be present with 0 for unused causes.

**Critical dependency chain:**
From `/api/dependencies`, find dependency edges where a **gating item** is the `upstream_id`. For each such edge, include both the upstream gating item and the downstream item (which may or may not be gating itself). Construct the chain by following these edges: start at the most-upstream item (the one that no other release item depends on) and walk downstream. The chain is ordered upstream-to-downstream; do **not** sort this list.

If multiple disjoint sub-chains exist, concatenate them in upstream-to-downstream order. An empty chain is `[]`.

**Ship decision:**
| Decision | When |
|---|---|
| `Ship` | All critical milestones ≥ readiness_target (default 0.92), no active blockers on gating items |
| `Hold` | Some critical milestones below target OR minor blockers, but recoverable |
| `NoShip` | Multiple critical milestones far below target, active blockers on release items, or gating items with unresolved dependencies |

**Risk tier:**
| Tier | When |
|---|---|
| `Low` | All critical milestones ≥ 80% complete, no active blockers |
| `Medium` | Most critical milestones ≥ 60%, some blockers but non-critical |
| `High` | Critical milestones < 60%, active blockers on gating items, or critical dependency chain involves incomplete items |

**Owner escalation IDs:**
Owners of gating items (from `owner_id` field). Include `"UNASSIGNED"` if any gating item has `owner_id: null`. Sort ascending.

---

## General Rules (All Task Types)

### Date Handling
- All dates are `YYYY-MM-DD` strings. Compute day differences with `(date2 - date1).days` in Python.
- The `as_of_date` is the cutoff: only consider status-history entries with `timestamp ≤ as_of_date`.
- `recent_closed_window_days` means: items closed within this many days before `as_of_date` are considered "recent."

### Duplicate Clusters
- `duplicate_cluster` on a work item is either `null` or a string like `"DUP-024"`.
- Portfolio tasks: only the lowest-ID completed item per cluster is eligible.
- SLA tasks: report each cluster with members in the included population.

### Status Lifecycle
Status values: `New` → `In Progress` → `Blocked` / `Review` → `Verified` → `Closed` / `Done`
- "Complete" / "Done" terminal states: `Done`, `Closed`, `Verified`
- `Blocked` is NOT a terminal state; blocked items are still active
- `Review` is NOT terminal

### API Response Shape
All list endpoints return `{count: <int>, results: <array>}`. Always iterate `results`.

### Sorting Conventions
- Work item IDs: always sort alphanumerically ascending
- Owner/team IDs: sort alphanumerically ascending
- Milestone IDs: sort alphanumerically ascending

### Output Format
- Return valid JSON only — no markdown, no commentary, no extra keys
- Match the answer template's key names EXACTLY (the template IS the output schema)
- Integer fields must be integers (not floats)
- Percentage fields: round to 1 decimal place
- Null vs empty: use `null` for absent singletons, `[]` for empty arrays, `0` for zero counts

### Common Pitfalls
- **Stale status_export:** The `status_export` field on work items is a point-in-time export and may not reflect the as_of_date. Always use `/api/status-history` filtered by `timestamp ≤ as_of_date` for the authoritative status.
- **Closed but overdue:** An item closed within the recent window can still be overdue if it was overdue at the time of closure. Calculate age at closure, not current age, for closed items.
- **Duplicate cluster low-ID rule:** When picking the representative for a duplicate cluster, use the lowest alphanumeric ID among INCLUDED members, not necessarily the lowest among all members.
- **Empty dependency chains:** If no critical dependency path connects gating items, the chain is `[]`.
- **All-zero blockers:** All 8 blocker cause keys must appear even when counts are 0.
- **Team lookup by product_line:** Teams have a `product_line` field matching product names. Match the task's product to this field, not `name`.
