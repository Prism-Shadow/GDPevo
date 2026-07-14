# Engineering Operations Review Skill

## Environment

- Base URL: provided via `<TASK_ENV_BASE_URL>` in the prompt or `environment_access.md`.
- All data comes from REST APIs returning JSON with `{ "count": N, "results": [...] }`.
- Use query parameters to scope results; always use URL-encoded values (e.g., `Identity%20Platform`).

## Three Review Types

| Type | Template signature | Tasks |
|------|-------------------|-------|
| Portfolio Mix Review | `eligible_work_item_ids`, `bucket_rows`/`category_mix`, `gap_basis_points` | 001, 004 |
| SLA Aging Snapshot | `included_work_item_ids`, `overdue_work_item_ids`, `aging_bucket_counts`/`aging_buckets` | 002, 005 |
| Release Readiness Rollup | `ship_decision`, `milestones`, `gating_work_item_ids`, `blocker_cause_counts`, `critical_dependency_chain` | 003 |

---

## Portfolio Mix Review (Tasks 001, 004)

### Required API Calls

1. `GET /api/work-items?product={Product}&quarter={YYYY-QN}` — scoped work items
2. `GET /api/portfolio-targets?product={Product}&quarter={YYYY-QN}` — target allocation % per category
3. `GET /api/teams` — owning team lookup for follow-up actions

### Classification Rule

Classify each work item into exactly one category **by `work_type`**, ignoring labels:

| work_type | Category |
|-----------|----------|
| Feature, Enhancement, Experiment | **NewFeature** |
| Migration, Refactor, Cleanup, Platform | **TechDebt** |
| Reliability, Incident, Bug | **Reliability** |
| Vulnerability, Compliance, Security | **Security** |

If a work_type is not in this table, skip the item (should not happen in valid data).

### Eligibility (Completed Items)

A work item is eligible (counted as completed) when **all** of:
1. `status_export` ∈ `{Closed, Done, Verified}`
2. `closed_date` is non-null
3. `closed_date` ≤ `as_of_date`

Items with `closed_date: null` are **never** eligible, regardless of `status_export`.

### Gap Calculation

```
actual_pct = (category_count / eligible_total) × 100
gap_basis_points = round((actual_pct - target_percentage) × 100)
```

Round to nearest integer. Basis points are 1/100th of a percent, so a 5% gap = 500 bp.

### Under-Invested Categories

- `under_invested_categories`: all categories where `gap_basis_points < 0`, sorted by gap ascending (most negative first)
- `largest_negative_gap_category`: category with the most negative `gap_basis_points`, or `null` if none are negative

### Follow-Up Actions

For each under-invested category, produce one entry:
```json
{ "category": "<name>", "action": "IncreaseAllocation", "owner_team_id": "<team_id>" }
```
- `owner_team_id`: use the product's team from `/api/teams` (match `product_line` to the task `product`).

### Evidence Samples

`evidence_sample_ids`: For each category (all four, not just under-invested), include up to 3 work item IDs from the eligible set that belong to that category. Sort IDs ascending.

### Output Shape Notes

- Template may use key `bucket_rows` (task 001) or `category_mix` (task 004) — use whichever the answer template shows.
- `eligible_work_item_ids`: sorted ascending.
- `eligible_total`: count (not string).

---

## SLA Aging Snapshot (Tasks 002, 005)

### Required API Calls

1. `GET /api/work-items?product={Product}` — all work items for the product
2. `GET /api/sla-policies` — SLA target_days per (category, severity)
3. `GET /api/teams` — team lookup
4. `GET /api/owners` — owner identity for hotspot entries

### Scope Filter

Only include work items whose `work_type` is in the SLA scope:

| work_type | SLA Category |
|-----------|-------------|
| Reliability, Incident, Bug | **Reliability** |
| Vulnerability, Compliance, Security | **Security** |

Items with other work_types (Feature, Enhancement, Experiment, Migration, Refactor, Cleanup, Platform) are **excluded** from SLA reviews entirely.

### Included Population

An SLA-scoped item is **included** if either:
- It is **still open**: `closed_date` is null, OR `closed_date` > `as_of_date`
- It was **recently closed**: `closed_date` ∈ [`as_of_date − window_days`, `as_of_date`] (inclusive both ends)

Items closed before the window start are excluded from the review.

The 21-day window is inclusive: if `as_of_date = 2026-02-15` and `window = 21`, the window is `2026-01-25` through `2026-02-15`.

### Overdue Determination

An included item is **overdue** when **all** of:
1. It is still open as of `as_of_date` (not closed, or closed after `as_of_date`)
2. `due_date` < `as_of_date`

Items closed on or before `as_of_date` cannot be overdue (they were resolved).

### Aging Buckets

For each overdue item, compute age in days:
```
age_days = as_of_date − created_date
```

Bucket the age:

| Bucket | Condition |
|--------|-----------|
| `0-7` | age ≤ 7 |
| `8-14` | 8 ≤ age ≤ 14 |
| `15-30` | 15 ≤ age ≤ 30 |
| `31+` | age ≥ 31 |

### Owner Hotspots

Group overdue items by `owner_id`. For each owner:
- `overdue_count`: number of overdue items they own
- `max_age_days`: maximum age among their overdue items

Items with `owner_id: null` should appear as a separate entry with `owner_id: "UNASSIGNED"` (or use the key `"UNASSIGNED"`).

Sort entries by `owner_id` ascending.

### Team Hotspots

Same as owner hotspots but grouped by `team_id`. Sort by `team_id` ascending.

### Duplicate Clusters

Group **included** items by `duplicate_cluster` field. For each cluster that has ≥1 member in the included set:

- `cluster_id`: the `duplicate_cluster` value (e.g., `DUP-001`)
- `representative_work_item_id`: the **lowest-sorting** work item ID among included members
- `member_ids`: all work item IDs in the cluster that are in the included set, sorted ascending

Only report clusters with members present in the included population.

The template key may be `duplicate_clusters` (task 002) or `duplicate_cluster_representatives` (task 005) — use whichever matches the answer template.

### Escaped Severity

Count of included items where `escaped` is `true`.

### Missing Owners

Sorted list of work item IDs from the **included** set where `owner_id` is `null`.

### SLA Policies Reference

SLA target days by (category, severity) — use these to look up target_days when needed for calculations:

| Category | S1 | S2 | S3 | S4 |
|----------|----|----|----|-----|
| NewFeature | 30 | 45 | 75 | 90 |
| TechDebt | 14 | 30 | 45 | 60 |
| Reliability | 2 | 5 | 10 | 21 |
| Security | 3 | 7 | 14 | 30 |

---

## Release Readiness Rollup (Task 003)

### Required API Calls

1. `GET /api/releases/{release_id}` — release metadata (name, readiness_target, release_date)
2. `GET /api/milestones?release_id={release_id}` — milestone list with critical flags
3. `GET /api/milestone-items?release_id={release_id}` — work items assigned to each milestone
4. `GET /api/work-items?release_id={release_id}` — all work items in the release
5. `GET /api/blockers?active=true` — all active (unresolved) blockers
6. `GET /api/dependencies` — dependency graph
7. `GET /api/owners` — owner lookup for escalations

### Milestone Completion

For each milestone (sorted by `milestone_id` ascending):
1. Gather all work item IDs assigned to it from `/api/milestone-items`
2. Look up each work item's `status_export` from the release work items
3. Count how many have `status_export` ∈ `{Closed, Done, Verified}`
4. Compute: `completion_percentage = round(count_completed / total_assigned × 100, 1)`

Include `critical` boolean from the milestone record.

If zero items are assigned to a milestone, `completion_percentage` = `0.0`.

### Gating Work Items

A work item is a **gating item** when **all** of:
1. It is in the release's work items
2. It has `"release-gate"` in `labels` OR `"critical-path"` in `labels`
3. Its `status_export` ∉ `{Closed, Done, Verified}`

Output `gating_work_item_ids` sorted ascending.

### Blocker Cause Counts

1. Filter `/api/blockers?active=true` to only blockers whose `work_item_id` appears in the release's work item set
2. Group by `blocker_type` and count

Map API `blocker_type` values to canonical keys by removing spaces:

| API value | Canonical key |
|-----------|--------------|
| External Dependency | ExternalDependency |
| Security Review | SecurityReview |
| Design Decision | DesignDecision |
| Data Migration | DataMigration |
| Ownership Gap | OwnershipGap |
| Environment | Environment |
| Capacity | Capacity |
| Vendor | Vendor |

Include ALL 8 canonical keys in the output, using `0` for any that have no active blockers.

### Critical Dependency Chain

1. Filter all dependencies to only those with `critical: true`
2. Further filter to only dependencies where the work item IDs are in the release's work item set (either upstream or downstream)
3. Build a directed graph: edge from `upstream_id` → `downstream_id`
4. Trace the **longest connected path** through the graph, outputting work item IDs in upstream-to-downstream order
5. **Do not sort** this list — preserve dependency order

### Ship Decision

Evaluate against the release's `readiness_target` (a float like `0.92`):

| Decision | Criteria |
|----------|----------|
| **Ship** | All critical milestones ≥ readiness_target × 100% AND `gating_work_item_ids` is empty AND `risk_tier` is Low |
| **NoShip** | Overall critical milestone average < 50% OR >5 active blockers on release items OR any critical milestone at 0% |
| **Hold** | Everything else — some concerns but not blocking |

### Risk Tier

| Tier | Criteria |
|------|----------|
| **Low** | Critical milestone average ≥ 85% AND ≤2 active blockers AND 0 gating items |
| **Medium** | Critical milestone average ≥ 60% AND ≤5 active blockers |
| **High** | Critical milestone average < 60% OR >5 active blockers OR any critical milestone at 0% |

### Owner Escalation IDs

Collect `owner_id` for every **gating** work item. If a gating item has `owner_id: null`, add `"UNASSIGNED"`. Sort ascending.

---

## General Patterns

### Date Handling

- All dates are ISO 8601 (`YYYY-MM-DD`).
- When computing date ranges, use `datetime.date` objects and `timedelta`.
- Date comparisons are inclusive of both endpoints unless noted.
- When `closed_date` is `null`/`None`, treat the item as not yet closed.

### Sorting Conventions

- Work item IDs: sort alphanumerically ascending (e.g., `WI-0001` < `WI-0002` < `WI-0341`).
- Milestone IDs: sort alphanumerically ascending.
- Category lists (under_invested_categories): sort by gap_basis_points ascending (most negative first).
- Owner/team hotspot lists: sort by the ID/key ascending.

### Rounding

- Portfolio percentages: compute gap_basis_points as `round((actual_pct − target_pct) × 100)`.
- Milestone completion: `round(completed / total × 100, 1)` — one decimal place.
- Aging bucket boundaries: use integer day counts with standard ≤ comparisons.

### Null Handling

- `largest_negative_gap_category`: `null` when no categories are under-invested.
- `owner_id: null` → use `"UNASSIGNED"` as the key in hotspot/ escalation lists.
- `duplicate_cluster: null` → the item is NOT part of any duplicate cluster.
- `closed_date: null` → the item has never been closed; treat as open.

### Edge Cases

- **Zero eligible items in portfolio review**: all percentages are 0%, gaps = −target × 100 bp, all categories under-invested.
- **No overdue items**: all aging buckets are 0, owner/team hotspots are empty arrays.
- **Release with 0 blockers**: all blocker_cause_counts values are 0 (never omit keys).
- **Duplicate cluster with mixed inclusion**: only members that pass the inclusion filter appear in `member_ids`.
- **Items closed on the window boundary**: included (window is inclusive).
- **Items with `status_export=Closed` but no `closed_date`**: NOT eligible (require both).

### Common Pitfalls

1. **Classifying by labels instead of work_type**: labels are supplementary metadata; classification is strictly by `work_type`.
2. **Using wrong date for eligibility**: always compare `closed_date` (not `updated_date` or `created_date`) to `as_of_date`.
3. **Missing URL encoding**: product names with spaces must be URL-encoded (`Identity%20Platform`, not `Identity Platform`).
4. **Forgetting the 21-day inclusive window**: both boundary dates are inclusive.
5. **Omitting blocker types with zero count**: the answer template expects all 8 blocker-type keys present.
6. **Sorting the critical dependency chain**: preserve topological order, do not sort.
7. **Including non-SLA work types in SLA aging**: only Reliability/Incident/Bug and Vulnerability/Compliance/Security are in scope.
8. **Counting items closed after as_of_date as completed**: only items with `closed_date` ≤ `as_of_date` are eligible/completed.
