# Engineering Operations Workspace — Reusable Skill

## Core Principle: Status History Is the Source of Truth

The `status_export` field on work items is **stale in places**. Always determine
the current status of a work item from the **last entry** in
`/api/status-history?product=<name>`, filtered to timestamps on or before the
as-of date. Do not rely on `status_export` for eligibility, completion checks,
or aging calculations.

**Terminal statuses** are `Closed`, `Done`, and `Verified`. All other status
values (`New`, `In Progress`, `Blocked`, `Review`, `Cancelled`) are non-terminal.

## Work-Type → Portfolio/SLA Category Mapping

Every work item has a `work_type` field. Map it to one of four categories:

| work_type                              | Category      |
|----------------------------------------|---------------|
| Feature, Enhancement, Experiment       | NewFeature    |
| Refactor, Migration, Cleanup, Platform | TechDebt      |
| Reliability, Incident, Bug             | Reliability   |
| Vulnerability, Compliance, Security    | Security      |

This mapping is used consistently across portfolio-mix reviews, SLA aging
snapshots, and any report that groups items by these four categories.

## Portfolio Work-Mix Review Rules

### Eligibility

An item is eligible if its **last status-history entry** (timestamp ≤ as-of
date) is a terminal status (`Closed`, `Done`, `Verified`). Items that are still
in a non-terminal state as of the review date are excluded from the mix.

### Gap Calculation

- `actual_percentage` = `count / eligible_total * 100`, rounded to one decimal.
- `gap_basis_points` = `round((actual_percentage - target_percentage) * 100)`.
  Compute the gap from the rounded actual percentage, not the raw ratio.

### Follow-Up Actions

For every **under-invested category** (negative gap), emit a follow-up action
with `"action": "IncreaseAllocation"` and the product's primary `team_id`.

### Evidence Sample IDs

For each category, include up to three eligible work-item IDs (sorted
ascending) as representative samples.

## SLA Aging Snapshot Rules

### Inclusion

Include every work item in the scoped product whose category is `Reliability`
or `Security`, **except** items whose **first** status-history entry has a
timestamp **after** the as-of date. Items that did not yet exist at the
snapshot date must be excluded.

### Overdue Determination

1. Compute **age in days**:
   - If the item reached a terminal status on or before the as-of date: age =
     days from the first `New` history entry to that terminal-status timestamp.
   - Otherwise (item is still open): age = days from the first `New` history
     entry to the as-of date.
   - Always use the **first `New` entry in status history** as the created
     date, not the work-item `created_date` field, because the history
     timestamp is authoritative.

2. Look up the **SLA target** from `/api/sla-policies` using the item's
   (category, severity) tuple.

3. The item is **overdue** if `age > target_days` (strictly greater).

### Aging Buckets

Distribute overdue items into buckets by age: `0–7`, `8–14`, `15–30`, `31+`
days. Boundaries are inclusive on both ends.

### Owner / Team Hotspots

For each owner (using `owner_id`; use `"UNASSIGNED"` when `null`) and each
team, count overdue items and track the maximum age. Emit one entry per
owner/team that has at least one overdue item.

### Duplicate Clusters

Among **included** items (not just overdue), group by `duplicate_cluster`.
For each cluster, use the **lowest sorted member ID** as the representative.

### Escaped and Missing Owner

- `escaped_severity_count`: count of included items where `escaped` is `true`.
- `missing_owner_work_item_ids`: sorted IDs of included items where `owner_id`
  is `null`.

## Release Readiness Rules

### Milestone Completion

For each milestone, count items whose **status as of the as-of date** (from
history) is terminal. `completion_percentage` = `completed / total * 100`,
rounded to one decimal.

### Gating Work Items

**Gating items** = items that are (a) assigned to a **critical** milestone,
(b) **not** in a terminal status as of the as-of date, AND (c) have at least
one **active blocker** from `/api/blockers?active=true`. Sort ascending.

### Blocker Cause Counts

Map blocker types from the API to template keys. The API uses spaced names
(`"Security Review"`, `"External Dependency"`, `"Design Decision"`,
`"Data Migration"`, `"Ownership Gap"`); the template uses PascalCase
(`"SecurityReview"`, `"ExternalDependency"`, `"DesignDecision"`,
`"DataMigration"`, `"OwnershipGap"`). `"Environment"`, `"Capacity"`, and
`"Vendor"` are identical in both.

Only count blockers whose `work_item_id` belongs to the release's work items.

### Critical Dependency Chain

From `/api/dependencies`, select edges where `critical` is `true` AND at least
one of `upstream_id`/`downstream_id` belongs to the release's work items.
Order IDs from upstream to downstream. Do **not** sort the list
alphabetically — preserve the topological dependency order.

### Owner Escalation IDs

Collect `owner_id` from every **gating** work item. Use `"UNASSIGNED"` when
the owner is `null`. Sort ascending.

### Ship Decision

Compare weighted milestone completion against `readiness_target` from the
release object. Critical milestones count more heavily. If blocked gating
items remain at the as-of date (which is often the release date), lean toward
`NoShip` or `Hold`.

## General Pitfalls

1. **Never trust `status_export` alone.** Always cross-check with status
   history. The `status_export` field can be stale — e.g., an item may show
   `"Closed"` in `status_export` but have `"In Progress"` as its last history
   entry.

2. **Exclude future items.** Items whose first history entry is after the
   as-of date did not exist at review time and must be excluded from all
   populations.

3. **"Cancelled" is not terminal.** Only `Closed`, `Done`, and `Verified` end
   an item's lifecycle.

4. **Use status-history timestamps for age computation**, not the work-item
   `closed_date` or `created_date` fields. Those can disagree with the
   authoritative transition log.

5. **Compute gap from the rounded actual percentage**, not from the raw
   floating-point ratio, to avoid off-by-one basis-point errors.

6. **For duplicate clusters**, the representative is the lowest sorted member
   ID within the **included** population, not across all items in the system.

7. **Blocker type strings differ** between the API (spaced) and answer
   templates (PascalCase). Always map explicitly; never pass through
   unmodified.
