# Engineering Operations Workspace — Solver Skill

## Overview

This skill covers three task types served by a remote engineering-operations HTTP API:

1. **Portfolio Work-Mix Review** — category distribution of completed quarterly work vs targets
2. **SLA Aging Snapshot** — aging analysis of open reliability/security work items
3. **Release Readiness Rollup** — milestone progress, blockers, ship/hold decision

The base URL is given by the task (use `<TASK_ENV_BASE_URL>`; override with `environment_access.md` if present). All tasks require producing a JSON object matching the answer template in `input/payloads/answer_template.json`.

---

## Workflow for Every Task

1. **Read `input/payloads/request_context.json`** — extracts scope (product, quarter, as_of_date, release_id) and endpoint hints.
2. **Read `input/payloads/answer_template.json`** — the exact output shape; never add or rename keys.
3. **Fetch data from API endpoints** (see below).
4. **Compute and fill the template.** Return JSON only — no markdown, prose, or extra keys.

---

## API Endpoint Reference

All endpoints are prefixed with `<TASK_ENV_BASE_URL>`.

| Endpoint | Key query params | Used by |
|---|---|---|
| `GET /api/work-items` | `product`, `quarter`, `release_id` | All |
| `GET /api/status-history` | `product` | All |
| `GET /api/portfolio-targets` | `product`, `quarter` | Portfolio |
| `GET /api/sla-policies` | — | SLA Aging |
| `GET /api/teams` | — | All |
| `GET /api/owners` | — | SLA Aging, Release |
| `GET /api/releases/{release_id}` | — | Release |
| `GET /api/milestones` | `release_id` | Release |
| `GET /api/milestone-items` | `release_id` | Release |
| `GET /api/dependencies` | — | Release |
| `GET /api/blockers` | `active=true` | Release |

---

## Task Type 1: Portfolio Work-Mix Review

**Example tasks:** train_001 (Identity Platform 2025-Q4), train_004 (Data Platform 2026-Q1)

### Scope & eligibility

Items are eligible when:
- They belong to the target `product`.
- Their `quarter` field matches the target quarter.
- Their **terminal completed status** was reached on or before `as_of_date` (check `status-history` for the latest status entry timestamp ≤ as_of_date; the item must be in a completed terminal state like `Done`, `Completed`, or `Closed`).

### Category classification

Each work item has a `category` field. The four standard categories are:

| Category | Description |
|---|---|
| `NewFeature` | New feature work |
| `TechDebt` | Technical debt reduction |
| `Reliability` | Reliability improvements |
| `Security` | Security work |

If the API returns additional category values, only these four appear in the output template; if a work item has a different category, either map it to the closest standard category or exclude it (check the gold answers: all eligible items in the train tasks map to these four).

### Computing bucket counts and percentages

1. Count eligible items per category → `count`.
2. `eligible_total` = sum of all `count` values.
3. `actual_percentage` = `(count / eligible_total) * 100`, rounded to **1 decimal place**.
4. Fetch portfolio targets from `/api/portfolio-targets?product=X&quarter=Y`. The response gives `target_percentage` per category.
5. `gap_basis_points` = `round((actual_percentage - target_percentage) * 100)` — an integer. Negative values mean the category is under-invested relative to target.

### Under-investment rule

A category is **under-invested** when its gap is **≤ −500 basis points** (i.e., the actual percentage is at least 5 percentage points below target).

- Categories with a gap between −500 and 0 (exclusive) are NOT classified as under-invested — they are within tolerance. Example from train_004: NewFeature at −290 bp, TechDebt at −170 bp, Security at −180 bp — none marked under_invested.
- Categories with actual ≥ target (gap ≥ 0) are never under-invested.

**`under_invested_categories`**: list of category name strings for every category meeting the ≤ −500 bp rule. Sorted the same order as the template's category rows. Empty array `[]` if none.

**`largest_negative_gap_category`**: the single category with the most negative gap. `null` if no category has a negative gap.

### Follow-up actions

For each category in `under_invested_categories`, produce a follow-up action:
- `category`: the category name
- `action`: `"IncreaseAllocation"`
- `owner_team_id`: the team ID responsible for the product (from `/api/teams`, match the team whose `product` field equals the target product)

If `under_invested_categories` is empty, `follow_up_actions` is an empty array `[]`.

### Evidence samples

`evidence_sample_ids` is an object keyed by category. For each category, pick up to 3 eligible work item IDs (sorted ascending) as representative evidence.

---

## Task Type 2: SLA Aging Snapshot

**Example tasks:** train_002 (Payments, as_of 2026-02-15), train_005 (Edge Services, as_of 2026-04-10)

### Scope & eligibility

Items are **included** when:
- They belong to the target `product`.
- Their `type` is `Reliability` or `Security` (case-insensitive match).
- They are **currently open** as of `as_of_date`: the latest status in `status-history` with a timestamp ≤ `as_of_date` is NOT a terminal/closed state (`Done`, `Completed`, `Closed`, `Resolved`).
- **Important**: items that were closed within `recent_closed_window_days` (inclusive) before `as_of_date` are ALSO included as "recently addressed" — they're part of the review population.

Sort `included_work_item_ids` ascending.

### SLA overdue determination

1. Fetch `/api/sla-policies`. Each policy maps a work item `type` to a `max_days` target.
2. For each included item, compute `age_days` = `as_of_date − created_date` (the item's creation date from the work-items response). Use calendar days.
3. An item is **overdue** when `age_days > sla_max_days` for its type.
4. Sort `overdue_work_item_ids` ascending.

### Aging buckets

Distribute ALL included items (not just overdue) into age buckets based on `age_days`:

| Bucket | Range |
|---|---|
| `0-7` | 0 ≤ age ≤ 7 |
| `8-14` | 8 ≤ age ≤ 14 |
| `15-30` | 15 ≤ age ≤ 30 |
| `31+` | age ≥ 31 |

The template may use `aging_bucket_counts` (object with these keys) or `aging_buckets` (array of `{bucket, count}`) — match the template shape exactly.

### Owner hotspots

Group overdue items by `owner_id` (from work items). For each owner with overdue items:
- `owner_id`: the owner ID string
- `overdue_count`: number of overdue items assigned to this owner
- `max_age_days`: maximum `age_days` among those overdue items

Sort by `overdue_count` descending, then `max_age_days` descending. If no owners have overdue items, the template likely expects the field to be `[]` (check template).

### Team hotspots

Same logic as owner hotspots but grouped by `team_id`. Sort by `overdue_count` descending, then `max_age_days` descending.

### Duplicate clusters

The API returns duplicate cluster information (likely embedded in work item data or a separate field). For each duplicate cluster where **at least one member** appears in `included_work_item_ids`:
- `cluster_id`: the cluster identifier
- `representative_work_item_id`: the lowest-ID member in the cluster (by string sort of WI-XXXX)
- `member_ids`: all member work item IDs in the cluster, sorted ascending

The field name varies: `duplicate_clusters` (train_002) vs `duplicate_cluster_representatives` (train_005). Match the template.

### Escaped severity

An item has "escaped severity" when its `severity` in `status-history` changed from a lower level to a higher level (e.g., `low` → `medium`, `medium` → `high`, `low` → `high`). Count included items where at least one severity increase occurred in their history at or before `as_of_date`.

`escaped_severity_count` is the count of such items.

### Missing owners

`missing_owner_work_item_ids`: included items whose `owner_id` is `null`, empty string, or missing. Sorted ascending.

---

## Task Type 3: Release Readiness Rollup

**Example task:** train_003 (REL-PAY-2026Q1, as_of 2026-02-28)

### Data fetching

1. `GET /api/releases/{release_id}` — release metadata
2. `GET /api/milestones?release_id=X` — list of milestones
3. `GET /api/milestone-items?release_id=X` — work items assigned to each milestone (maps milestone → items)
4. `GET /api/work-items?release_id=X` — work items associated with the release
5. `GET /api/status-history?product=Y` — status transitions
6. `GET /api/dependencies` — dependency graph between work items
7. `GET /api/blockers?active=true` — active blockers on release work items

### Milestone completion

For each milestone:
- `milestone_id`: from API, sorted ascending
- `critical`: `true` if the milestone's `critical` field is true, else `false`
- `completion_percentage`: `(number of milestone items in a completed terminal state as of as_of_date / total milestone items) * 100`, rounded to **1 decimal place**

### Ship decision

Evaluate the release holistically:

| Decision | Conditions |
|---|---|
| `Ship` | All critical milestones ≥ 90%, no active blockers, no gating items |
| `Hold` | Most critical milestones ≥ 70% but some gaps; minor blockers that can be resolved |
| `NoShip` | One or more critical milestones < 50%, active blockers present, gating items exist |

In practice: if ANY critical milestone has < 50% completion OR active blockers exist on gating items → `NoShip`. If all critical milestones ≥ 90% AND no blockers AND no gating items → `Ship`. Otherwise → `Hold`.

### Risk tier

| Tier | Conditions |
|---|---|
| `Low` | All milestones on track, no blockers, no gating items |
| `Medium` | Minor concerns — some milestones behind but not critically, few non-blocking issues |
| `High` | Multiple critical milestones significantly behind, active blockers on release items, security review blockers, vendor blockers |

### Gating work item IDs

Work items that have an active blocker AND are part of a critical milestone. Alternatively, work items whose status is NOT completed and that are blocking the release (check if they are listed as blockers or are dependencies of blocked items).

Sort ascending. Empty array `[]` if none.

### Blocker cause counts

Count active blockers by `cause` field. The template specifies these cause keys: `ExternalDependency`, `Environment`, `SecurityReview`, `Capacity`, `DesignDecision`, `DataMigration`, `Vendor`, `OwnershipGap`. Only include causes that appear in the template. Default to 0 for absent causes.

### Critical dependency chain

From `/api/dependencies`, trace the longest or most critical dependency chain through work items associated with the release. The chain goes from upstream (dependency) to downstream (dependent). Work items in the chain appear in dependency order — do NOT sort. If a work item depends on X and X depends on Y, the order is: Y, X, work-item.

### Owner escalation

`owner_escalation_ids`: owner IDs of gating work items (items with active blockers). Include `"UNASSIGNED"` if a gating item has no owner. Sort ascending (UNASSIGNED sorts after regular IDs or per string sort). Deduplicate — each owner appears once.

---

## Cross-Cutting Rules & Pitfalls

### Date handling

- All dates are `YYYY-MM-DD` strings. Parse with a date library or manual parse — do NOT use timezone-ambiguous parsing.
- **Inclusive window**: "21 days inclusive" means `as_of_date − 21 days` to `as_of_date` (both endpoints included). Compute as: `closed_date >= (as_of_date − 21 days) AND closed_date <= as_of_date`.
- **Status as-of check**: when determining state at `as_of_date`, find the latest status-history entry with `timestamp ≤ as_of_date`. The item's state at that point is what the history entry says.

### Rounding

- Percentages: round to **1 decimal place** (e.g., `28.1`, `58.3`, `32.1`). Use `Math.round(value * 10) / 10` or equivalent.
- Basis points: `Math.round((actual - target) * 100)` → integer.
- Never round intermediate values — only round the final displayed value.

### Sorting conventions

- Work item IDs and owner IDs: lexicographic/string sort ascending (e.g., `"OWN-PAY-2" < "OWN-PAY-3"`).
- Milestone IDs: string sort ascending.
- Owner/team hotspots: by `overdue_count` descending, then `max_age_days` descending.
- `critical_dependency_chain`: dependency order (not sorted) — upstream first, downstream last.

### Template matching

- The answer template's key names are **authoritative**. Same task type may use different key names across instances (e.g., `bucket_rows` vs `category_mix`, `aging_bucket_counts` vs `aging_buckets`, `duplicate_clusters` vs `duplicate_cluster_representatives`).
- Always read `answer_template.json` and use its exact key names, nesting, and value types.
- If the template has a placeholder value like `"TEAM-ID"` or `"OWNER-ID"`, replace it with real data. If the template has a placeholder array/dict with a sample entry, replicate the structure with real computed data.
- Empty collections: use `[]` for arrays, `{}` for objects — never `null` unless the template explicitly uses `null`.

### Products and teams

- Team-to-product mapping comes from `/api/teams`. A team's `product` field indicates ownership. Use this to determine `owner_team_id` for follow-up actions.
- If `/api/teams` returns multiple teams for a product, pick the one whose product field matches. If still ambiguous, prefer the team with the most work items for that product.

### Status values

Common terminal/closed statuses: `Done`, `Completed`, `Closed`, `Resolved`. Treat any of these as "closed" for eligibility purposes. Common open statuses: `Open`, `InProgress`, `In Review`, `Blocked`, `ToDo`.

### Severity escalation

When checking for severity changes in status history:
- Parse severity levels as an ordered scale: `low` < `medium` < `high` < `critical`.
- An escalation means the severity at some later timestamp is strictly greater than the severity at an earlier timestamp.
- Only count items where the escalation happened on or before `as_of_date`.

### Duplicate cluster representative

The representative is the **lowest-ID member** (string sort) of the cluster. This is consistent across train_002 and train_005.

### Under-investment threshold

The threshold is **−500 basis points** (−5 percentage points). This is calibrated from:
- train_001: NewFeature (−1690 bp) and TechDebt (−750 bp) → under-invested
- train_004: NewFeature (−290 bp), TechDebt (−170 bp), Security (−180 bp) → NOT under-invested

Threshold is somewhere between −750 and −290; −500 is the natural round cutoff.

### Empty vs missing fields

- If no items qualify, return empty arrays `[]`, zero counts, and `null` for scalar fields that the template shows as nullable (e.g., `largest_negative_gap_category`).
- `follow_up_actions`: `[]` when no categories are under-invested.
- `owner_hotspots` / `team_hotspots`: `[]` when no overdue items exist. But note the template may show a placeholder entry — check whether to keep the placeholder structure or return empty.

### API error resilience

- If an endpoint returns an empty list or 404, treat it as empty data (empty array `[]`), not an error.
- Always URL-encode query parameter values containing spaces (e.g., `Identity%20Platform`, `Data%20Platform`, `Edge%20Services`).

### Summary of computation order

**Portfolio Mix:**
1. Fetch work items, status history, portfolio targets, teams
2. Filter eligible items (product + quarter match, completed ≤ as_of_date)
3. Classify by category, compute counts and percentages
4. Compare with targets, compute gaps
5. Determine under-invested, largest negative gap
6. Build follow-up actions and evidence samples

**SLA Aging:**
1. Fetch work items, status history, SLA policies, owners, teams
2. Filter included items (product match, Reliability/Security, open or recently closed)
3. Compute age_days, determine overdue
4. Bucket by age
5. Build owner/team hotspots
6. Identify duplicate clusters, escaped severity, missing owners

**Release Readiness:**
1. Fetch release, milestones, milestone items, work items, status history, dependencies, blockers
2. Compute milestone completion percentages
3. Determine gating items (items with active blockers in critical milestones)
4. Count blockers by cause
5. Trace critical dependency chain
6. Determine ship decision and risk tier
7. Collect owner escalation IDs
