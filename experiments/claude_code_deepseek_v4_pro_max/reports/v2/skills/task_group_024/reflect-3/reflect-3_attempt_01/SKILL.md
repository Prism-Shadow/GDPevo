# Engineering Operations Portfolio & Release Analytics Skill

## Overview

This skill covers three task types in an engineering operations workspace:
1. **Portfolio work-mix review** — classify completed work into investment categories and compare against targets
2. **SLA aging snapshot** — identify open work items past their SLA targets and surface hotspots
3. **Release readiness rollup** — assess milestone completion, blockers, and gating items for a release

The workspace exposes REST APIs at `<TASK_ENV_BASE_URL>`. All data is retrieved via GET requests. The answer is a single JSON object matching the provided answer template.

---

## Data Model

### Core entities

| Entity | Key fields |
|--------|-----------|
| Work item | `id`, `product`, `quarter`, `work_type`, `status_export`, `severity`, `labels[]`, `created_date`, `closed_date`, `due_date`, `owner_id`, `team_id`, `escaped`, `duplicate_cluster`, `release_ids[]` |
| Status history | `work_item_id`, `status`, `timestamp`, `source` |
| Portfolio target | `category`, `product`, `quarter`, `target_percentage` |
| SLA policy | `category`, `severity`, `target_days` |
| Team | `team_id`, `product_line`, `director` |
| Owner | `owner_id`, `display_name`, `role`, `team_id` |
| Release | `release_id`, `name`, `product`, `release_date`, `readiness_target` |
| Milestone | `milestone_id`, `release_id`, `critical`, `target_date` |
| Milestone item | `milestone_id`, `work_item_id` |
| Blocker | `blocker_id`, `work_item_id`, `blocker_type`, `active`, `severity` |
| Dependency | `upstream_id`, `downstream_id`, `dependency_type`, `critical` |

### Terminal statuses

A work item is **completed** when its latest status in status history is one of: `Closed`, `Verified`, `Done`.

**Important:** Do not rely on `status_export` alone — it may not reflect the true latest status. Always consult the status-history endpoint and take the entry with the latest `timestamp` (up to the as-of date for time-bounded queries).

---

## Classification Rules

Every work item must be classified into one of four portfolio categories: `NewFeature`, `TechDebt`, `Reliability`, `Security`.

### Primary rule: label-based with priority order

Classify using the item's `labels` array. Check in this priority order:

1. **Security** — labels contain: `security`, `compliance`, `vulnerability`
2. **Reliability** — labels contain: `reliability`, `reliability-review`, `slo`, `resiliency`, `capacity`, `timeout-spike`
3. **TechDebt** — labels contain: `tech-debt`, `migration`, `cleanup`, `internal`, `platform`
4. **NewFeature** — everything else (items with `feature`, `enhancement`, `workflow`, `customer`, `growth`, etc.)

### Key classification rules

- When an item has labels from multiple categories, the higher-priority category wins. For example, an item with both `reliability` and `tech-debt` labels is **Reliability**.
- `reliability-review` → **Reliability** (not TechDebt). This label indicates the work was a reliability review, which counts as reliability investment.
- `timeout-spike` → **Reliability**.
- `compliance-evidence-gap` alone does NOT trigger Security by default — it needs `compliance` or `security` in the label set. However, when the item's `work_type` is `Vulnerability`, `Compliance`, or `Security`, classify as Security regardless of labels.
- Items with `work_type` of `Incident` or `Bug` and no explicit category labels fall to the label-based check. When labels are ambiguous, the `work_type` can serve as a tiebreaker: `Vulnerability`/`Compliance`/`Security` → Security; `Reliability`/`Bug`/`Incident` → Reliability.

### SLA-specific classification

For SLA aging tasks, use the same classification rules. The SLA target lookup key is `(category, severity)`. SLA policies define `target_days` per category+severity combination.

---

## Task Type 1: Portfolio Work-Mix Review

### Eligibility

A work item is **eligible** (counts toward the portfolio mix) when:
1. It belongs to the scoped product and quarter (use the API filter parameters).
2. Its latest status-history entry (by timestamp, up to the as-of date) is one of `Closed`, `Verified`, `Done`.
3. **Do not exclude duplicates** — items with a `duplicate_cluster` value still count toward the mix.

### Computing the mix

- `eligible_total` = count of eligible items
- For each category: `count` = number of eligible items classified into that category
- `actual_percentage` = `round(count / eligible_total * 100, 1)`
- `gap_basis_points` = `int(round((target_percentage - actual_percentage) * 100))`
  - Positive gap = under-invested (actual below target)
  - Negative gap = over-invested (actual above target)

### Derived fields

- **under_invested_categories**: all categories where `gap_basis_points > 0` (actual below target)
- **largest_negative_gap_category**: the under-invested category with the largest positive gap_basis_points. If no category is under-invested, use `null`.
- **follow_up_actions**: one entry per under-invested category, with `action: "IncreaseAllocation"` and `owner_team_id` set to the team whose `product_line` matches the scoped product.
- **evidence_sample_ids**: for each category, the first 3 eligible work item IDs sorted ascending.

---

## Task Type 2: SLA Aging Snapshot

### Scope / included population

The included population consists of work items that:
1. Belong to the scoped product.
2. Have the `sla-review` label OR are part of a duplicate cluster (`duplicate_cluster` is set and `duplicate` is in labels).
3. Were created on or before the as-of date.
4. Are **either**:
   - **Open**: latest status from history (up to as-of date) is **not** one of `Closed`, `Verified`, `Done`.
   - **Recently closed**: latest status IS completed AND `closed_date` falls within the recent-closed window (as_of_date − window_days to as_of_date, inclusive).

### Age computation

- For **open** items: `age = as_of_date − created_date` (in days)
- For **recently closed** items: `age = closed_date − created_date` (in days)

### Overdue determination

An item is **overdue** when `age > sla_target_days`, where `sla_target_days` comes from the SLA policy matching the item's category and severity.

### Aging buckets

Count included items into buckets by their age (in days):
- `0-7`: age ≤ 7
- `8-14`: 8 ≤ age ≤ 14
- `15-30`: 15 ≤ age ≤ 30
- `31+`: age ≥ 31

### Hotspots

- **owner_hotspots**: for each owner with at least one overdue item, report `overdue_count` and `max_age_days`. Sort by `owner_id`.
- **team_hotspots**: same pattern by `team_id`.

### Duplicate clusters

For each `duplicate_cluster` value present in the included population, report:
- `cluster_id`: the cluster identifier
- `representative_work_item_id`: the lowest-sorted work item ID in the cluster
- `member_ids`: all work item IDs in the cluster, sorted ascending

### Other fields

- **escaped_severity_count**: count of included items where `escaped` is `true`.
- **missing_owner_work_item_ids**: included items where `owner_id` is `null` or missing, sorted ascending.

---

## Task Type 3: Release Readiness Rollup

### Milestone completion

For each milestone associated with the release:
- Get the set of work item IDs from the milestone-items endpoint.
- Count how many are completed (latest status from history up to as-of date is `Closed`/`Verified`/`Done`).
- `completion_percentage = round(completed / total * 100, 1)`, or `0.0` if the milestone has no items.
- Sort milestone objects by `milestone_id` ascending.

### Overall completion & ship decision

- Compute overall completion as `completed_items / total_items` across all work items in the release.
- `readiness_target` comes from the release object.
- **Ship decision**:
  - `"Ship"` if overall_completion ≥ readiness_target
  - `"Hold"` if overall_completion is below readiness_target but not severely (e.g., ≥ readiness_target − 0.15)
  - `"NoShip"` otherwise

### Gating work items

Gating items are work items that have the `release-gate` or `critical-path` label AND are **not completed** as of the as-of date. Sort ascending.

### Blocker cause counts

Query active blockers. For each blocker whose `work_item_id` belongs to the release's work items, increment the count for its `blocker_type`. Map the type strings:

| API blocker_type | Template key |
|---|---|
| `External Dependency` | `ExternalDependency` |
| `Environment` | `Environment` |
| `Security Review` | `SecurityReview` |
| `Capacity` | `Capacity` |
| `Design Decision` | `DesignDecision` |
| `Data Migration` | `DataMigration` |
| `Vendor` | `Vendor` |
| `Ownership Gap` | `OwnershipGap` |

### Critical dependency chain

1. Filter the dependencies endpoint to entries where `critical` is `true` AND both `upstream_id` and `downstream_id` are work items in the release.
2. Build a directed graph (upstream → downstream).
3. Perform a topological sort (Kahn's algorithm) to produce the chain in dependency order from upstream to downstream. Break ties by sorting node IDs ascending at each step.
4. **Do not sort the final list** — it must reflect actual dependency order.

### Owner escalation IDs

Collect owner IDs for:
- Gating work items (items with `release-gate` or `critical-path` labels, not completed)
- Work items that have active blockers

For items with no owner, use `"UNASSIGNED"`. Sort the final list ascending.

### Risk tier

- `"High"` if ship decision is `"NoShip"` or there are ≥ 3 active blocker causes
- `"Medium"` if ship decision is `"Hold"` or there is ≥ 1 active blocker
- `"Low"` otherwise

---

## General Pitfalls

1. **Never use `status_export` as the sole completion indicator.** The status-history endpoint provides the authoritative state. `status_export` can be stale or reflect a different snapshot.

2. **Date boundaries are inclusive.** When filtering by as-of date, use `timestamp <= as_of_date + "T23:59:59"`. When filtering by creation date, use `created_date <= as_of_date`.

3. **Do not exclude duplicate-cluster items from portfolio eligibility.** They represent real work that consumed capacity.

4. **Label-matching is substring-exact.** `compliance-evidence-gap` does not match the keyword `compliance` unless you split on hyphens or check for the full string. Match against the exact label strings present in the array.

5. **Round to one decimal place for percentages.** Use `round(value, 1)`. For gap_basis_points, round to integer: `int(round((target - actual) * 100))`.

6. **Sorting conventions:**
   - Work item IDs, owner IDs, team IDs, milestone IDs: sort ascending (lexicographic/default string sort).
   - Dependency chains: topological order (not sorted).
   - Category arrays: use the fixed order `NewFeature`, `TechDebt`, `Reliability`, `Security`.
   - Aging buckets: use the fixed order `0-7`, `8-14`, `15-30`, `31+`.

7. **Null handling:**
   - `largest_negative_gap_category`: `null` when no category is under-invested.
   - `owner_id`: use `"UNASSIGNED"` (string) in escalation lists, but exclude from owner_hotspots (only report owners with actual IDs).
   - `duplicate_cluster`: only include clusters that have members in the included population.

8. **SLA target selection:** The SLA policy is matched by `(category, severity)`. If an item's category+severity combination has no policy entry, the SLA target is undefined — treat it as not overdue.

9. **Answer JSON must match the template exactly.** Do not add extra fields, change key names, or nest objects differently than the template.
