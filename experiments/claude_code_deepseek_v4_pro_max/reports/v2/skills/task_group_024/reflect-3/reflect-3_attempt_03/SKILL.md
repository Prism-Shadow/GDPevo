# Engineering Operations Portfolio Analysis Skill

## Overview

Use the engineering-operations workspace HTTP API to compute portfolio work-mix
reviews, SLA aging snapshots, and release-readiness rollups from work-item and
related records.  The environment is stateless — every answer is derived from
live API responses.

---

## Core Principle: Status History Is Authoritative

Always derive completion / terminal-state determinations from the **last entry
in the status-history timeline**, not from `status_export` on the work-item
record.  `status_export` may lag or disagree with the timeline.

```
GET /api/status-history?product=<ProductName>
```

For each work item, take the entry with the **latest `timestamp`** — its
`status` field is the current status.

### Terminal Statuses

These three statuses mean the item is **complete**:

- `Closed`
- `Done`
- `Verified`

All other statuses (`New`, `In Progress`, `Review`, `Blocked`) mean the item
is **still open**.

---

## Task Type 1: Portfolio Work-Mix Review

**When you see**: "portfolio work-mix", "portfolio targets", quarter-end review
with as_of_date, category-mix buckets (NewFeature / TechDebt / Reliability /
Security), `eligible_work_item_ids`, `gap_basis_points`.

### Endpoints

| Endpoint | Parameters |
|---|---|
| `/api/work-items` | `product`, `quarter` |
| `/api/status-history` | `product` |
| `/api/portfolio-targets` | `product`, `quarter` |
| `/api/teams` | (none) |

### Eligibility Rule

A work item is **eligible** when its **final status-history status** is one of
`{Closed, Done, Verified}` **and** that terminal-status timestamp is on or
before the `as_of_date`.

### Category Classification

Map work-item `work_type` to the four portfolio categories as follows:

| work_type | Category |
|---|---|
| `Feature`, `Enhancement`, `Experiment` | **NewFeature** |
| `Migration`, `Refactor`, `Cleanup`, `Platform`, `Bug` | **TechDebt** |
| `Reliability`, `Incident` | **Reliability** |
| `Vulnerability`, `Compliance`, `Security` | **Security** |

**Do not use labels for category assignment** — use `work_type`.  Labels can be
misleading (e.g. a `Migration` item may carry a `tech-debt` label *and* a
`reliability-review` label).

### Derived Fields

- **`actual_percentage`**: `round(count / eligible_total * 100, 1)`
- **`gap_basis_points`**: `int(round((actual_pct - target_pct) * 100))`
  (1 bp = 0.01 percentage point)
- **`under_invested_categories`**: categories where `gap_basis_points < 0`
- **`largest_negative_gap_category`**: the under-invested category with the
  most-negative `gap_basis_points`
- **`follow_up_actions`**: one entry per under-invested category, with
  `action: "IncreaseAllocation"` and `owner_team_id` set to the product's team
  (look up in `/api/teams` by `product_line`)
- **`evidence_sample_ids`**: up to 3 work-item IDs per category from the
  eligible set

### Pitfalls

1. **Do not exclude duplicate-cluster items** from the eligible set.  Items
   with a non-null `duplicate_cluster` still count toward portfolio mix.
2. **Do not use `status_export`** for terminal-status decisions.
3. **The as_of_date precision is day-level**.  Compare `timestamp <=
   "{as_of_date}T23:59:59"`.

---

## Task Type 2: SLA Aging Snapshot

**When you see**: "SLA aging", "aging snapshot", "aging buckets" (0-7, 8-14,
15-30, 31+), `recent_closed_window_days`, `overdue_work_item_ids`,
`owner_hotspots`, `duplicate_clusters`, `escaped_severity_count`.

### Endpoints

| Endpoint | Parameters |
|---|---|
| `/api/work-items` | `product` |
| `/api/status-history` | `product` |
| `/api/sla-policies` | (none) |
| `/api/owners` | (none) |
| `/api/teams` | (none) |

### Scope Filter

Include **only** work items whose `work_type` maps to **Reliability** or
**Security** (i.e. `Reliability`, `Incident`, `Vulnerability`, `Compliance`,
`Security`).  Items of other work types (Feature, Enhancement, etc.) are out of
scope for an SLA aging review.

### Included Items

The **included** population is the full reliability+security scope (all items
matching the filter, regardless of status).

### Overdue Items

An included item is **overdue** when:
1. Its final status-history status is **not** terminal (not Closed / Done /
   Verified), **AND**
2. Its `due_date` is strictly before the `as_of_date`.

### Aging Buckets

For each **overdue** item, compute age as `as_of_date - created_date` in days:

| Age (days) | Bucket |
|---|---|
| 0 – 7 | `0-7` |
| 8 – 14 | `8-14` |
| 15 – 30 | `15-30` |
| 31+ | `31+` |

Bucket boundaries are **inclusive**.

### Owner / Team Hotspots

Aggregate overdue items by `owner_id` and `team_id`.  For each group report
`overdue_count` and `max_age_days` (max age across overdue items in that
group).  If `owner_id` is null, use `"UNASSIGNED"` as the key.

### Duplicate Clusters

Report each distinct `duplicate_cluster` value found among the **included**
population.  The representative is the alphabetically-first work-item ID in the
cluster.  Include all member IDs sorted ascending.

### Escaped & Missing Owners

- **`escaped_severity_count`**: count of included items where `escaped` is
  `true`.
- **`missing_owner_work_item_ids`**: included items where `owner_id` is null.

### Pitfalls

1. **Do not filter "included" to only open items** — the full reliability+
   security scope is the included set.
2. **Overdue** is determined from final history status (not `status_export`).
3. **Aging age** is `as_of_date − created_date` (not `due_date`).
4. **The `recent_closed_window_days` field** is an output metadata field, not a
   filter on inclusion.  It documents the window but does not change which
   items are in scope.

---

## Task Type 3: Release Readiness Rollup

**When you see**: "release readiness", "gating rollup", `ship_decision`,
`risk_tier`, `milestones` with `completion_percentage`, `gating_work_item_ids`,
`blocker_cause_counts`, `critical_dependency_chain`, `owner_escalation_ids`.

### Endpoints

| Endpoint | Parameters |
|---|---|
| `/api/releases/{release_id}` | — |
| `/api/milestones` | `release_id` |
| `/api/milestone-items` | `release_id` |
| `/api/work-items` | `release_id` |
| `/api/status-history` | `product` |
| `/api/dependencies` | (none) |
| `/api/blockers` | `active=true` |
| `/api/owners` | (none) |
| `/api/teams` | (none) |

### Milestone Completion

For each milestone, compute `completion_percentage` as:

```
completed = count of milestone items whose final history status is terminal
total    = count of all milestone items for that milestone
pct      = round(completed / total * 100, 1)
```

Milestone rows must be sorted by `milestone_id` ascending.

### Gating Items

**Gating items** are the work-item IDs across **all** milestones (from
`/api/milestone-items`) whose final status-history status is **not** terminal
(i.e. still open).  Sort ascending.

### Blocker Cause Counts

For each gating work item, look up active blockers (`/api/blockers?active=true`)
and count by `blocker_type`.  The canonical type keys are:

```
ExternalDependency, Environment, SecurityReview, Capacity,
DesignDecision, DataMigration, Vendor, OwnershipGap
```

Map raw blocker-type strings (e.g. `"External Dependency"` → `ExternalDependency`,
`"Security Review"` → `SecurityReview`) by removing spaces.

### Critical Dependency Chain

From `/api/dependencies`, select only **critical** dependencies where **both**
the upstream and downstream work-item IDs appear in the milestone-items set.
Build the chain by finding the root(s) — items that appear as upstream but
never as downstream — then walk downstream in sorted order.  The chain lists
work-item IDs from upstream to downstream; **do not sort the resulting chain**.

### Owner Escalations

Collect the `owner_id` of every gating work item.  If an item has a null owner,
include the literal string `"UNASSIGNED"`.  Sort the list ascending.

### Ship Decision & Risk Tier

Derive from overall readiness (completed milestone items / total milestone
items) compared to the release's `readiness_target`.  Specific thresholds may
vary; always cross-reference the target from `/api/releases/{release_id}`.

### Pitfalls

1. **Milestone items span all milestones**, not just critical ones.
2. **Gating items include items from non-critical milestones.**  Filter only by
   terminal vs. non-terminal — not by milestone criticality.
3. **Blocker types need space-stripping** to match the canonical keys.
4. **Dependency chain includes terminal items too** — the chain documents
   structure, not just unresolved items.
5. **Unmapped work types in blocker/gating analysis** should still have their
   owners included in escalation lists even if the item is from another team.

---

## General API Patterns

### Query Parameters

- **Product filter**: use `product=<Name>` (URL-encode spaces as `%20`).
- **Quarter filter**: use `quarter=2025-Q4` format.
- **Release filter**: use `release_id=<REL-ID>`.
- **Active blockers**: always pass `active=true`.

### Date and Window Handling

- All dates are in `YYYY-MM-DD` format.
- Timestamps in status history are ISO-8601 (`YYYY-MM-DDTHH:MM:SS`).
- When comparing against an `as_of_date`, use `T23:59:59` as the cutoff.
- "Inclusive" date windows include both the start and end dates.
- Day-count windows: a "21-day inclusive window" ending on date D starts at
  `D − 20` days.

### Numeric Precision

- Percentages: round to **1 decimal place** using `round(x, 1)`.
- Basis points: round to **integer** using `int(round(x))`.
- Do not use floating-point for accumulation; compute from integer counts.

### Team Lookup

The `/api/teams` endpoint returns all teams.  Match by `product_line` to find
the correct `team_id` for `follow_up_actions` and `team_hotspots`.

### Handling Null Owners

- In portfolio tasks: null owners are fine; the item still counts.
- In SLA / release tasks: treat null `owner_id` as `"UNASSIGNED"` and report in
  `missing_owner_work_item_ids`.

---

## Quick Reference: work_type → Category

| work_type | Portfolio Category |
|---|---|
| Feature | NewFeature |
| Enhancement | NewFeature |
| Experiment | NewFeature |
| Migration | TechDebt |
| Refactor | TechDebt |
| Cleanup | TechDebt |
| Platform | TechDebt |
| Bug | TechDebt |
| Reliability | Reliability |
| Incident | Reliability |
| Vulnerability | Security |
| Compliance | Security |
| Security | Security |

## Quick Reference: Status Lifecycle

```
New → In Progress → Review → Closed|Done|Verified
                           ↘ Blocked (may resolve to any later status)
```

Only `Closed`, `Done`, and `Verified` are terminal.  `Review` is **not**
terminal — an item in Review may still need rework.
