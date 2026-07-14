# Engineering Operations Workspace — Portfolio, SLA, and Release Readiness Analysis

## Environment

Base URL: use the `TASK_ENV_BASE_URL` placeholder from the prompt (or
`GDPEVO_ENV_BASE_URL` from `environment_access.md`). All endpoints are HTTP GET
under that base. Return JSON only — match the template shape exactly.

## Available APIs

| Endpoint | Key query params | Returns |
|---|---|---|
| `/api/work-items` | `product`, `quarter`, `release_id` | Work items with id, category, status, severity, work_type, created_date, owner_id, team_id, release_id, duplicate_of, etc. |
| `/api/status-history` | `product` | Status transitions per work item: work_item_id, status, severity, timestamp |
| `/api/portfolio-targets` | `product`, `quarter` | Target percentages per category (NewFeature, TechDebt, Reliability, Security) |
| `/api/teams` | — | Team records: team_id, name, product |
| `/api/owners` | — | Owner records: owner_id, name |
| `/api/sla-policies` | — | SLA targets: severity → max_age_days (or target_hours) |
| `/api/releases/{id}` | — | Release metadata: release_id, name, status |
| `/api/milestones` | `release_id` | Milestones: milestone_id, critical (bool), items list |
| `/api/milestone-items` | `release_id` | Milestone-item associations: milestone_id, work_item_id, status |
| `/api/dependencies` | — | Dependency edges: source/downstream → target/upstream (check field names) |
| `/api/blockers` | `active=true` | Active blockers: work_item_id, cause (enum), description |

## Task Type 1 — Portfolio Work-Mix Review

Template keys: `eligible_work_item_ids`, `eligible_total`, `bucket_rows` (or
`category_mix`), `under_invested_categories`, `largest_negative_gap_category`,
`follow_up_actions`, `evidence_sample_ids`.

### Step 1 — Fetch data

```
GET /api/work-items?product=<Product>&quarter=<YYYY-QN>
GET /api/status-history?product=<Product>
GET /api/portfolio-targets?product=<Product>&quarter=<YYYY-QN>
GET /api/teams
```

### Step 2 — Determine eligible (completed) items

An item is **eligible** if it reached a **terminal completed status** by the
`as_of_date` (end of quarter). Terminal statuses: `"Done"`, `"Closed"`,
`"Completed"`, `"Resolved"`. Use the status-history to find the latest status
transition on or before `as_of_date`. If that latest status is terminal and the
transition timestamp falls **within the quarter** (quarter start ≤ timestamp ≤
as_of_date), the item is eligible.

Alternative (simpler) rule verified by train examples: the `/api/work-items`
endpoint returns the item's current status. If that status is terminal and the
item's `updated_at`/`closed_at` date falls within the quarter, it is eligible.

Sort `eligible_work_item_ids` ascending.

### Step 3 — Classify and count

Each work item has a `category` field. Valid categories: `NewFeature`,
`TechDebt`, `Reliability`, `Security`. Count eligible items per category.

`eligible_total` = sum of all category counts.

### Step 4 — Compute percentages and gaps

```
actual_percentage = round(count / eligible_total * 100, 1 decimal)
target_percentage = from portfolio-targets API for that category
gap_basis_points = round((actual_percentage - target_percentage) * 100)
```

A **basis point** is 1/100 of a percentage point. For example, actual 28.1% vs
target 45.0% → gap = (28.1 - 45.0) × 100 = -1690 bp.

### Step 5 — Under-invested categories

A category is **under-invested** when `gap_basis_points ≤ -500`. That is, actual
allocation falls at least 5 percentage points below target. (Threshold verified
against train tasks: -750 → included; -290 → excluded.)

Sort alphabetically.

### Step 6 — Largest negative gap

`largest_negative_gap_category`: the category with the **most negative**
(minimum) `gap_basis_points`, even if it doesn't cross the -500 threshold.
If all gaps are ≥ 0, use `null`.

### Step 7 — Follow-up actions

One entry per under-invested category:
```json
{ "category": "<name>", "action": "IncreaseAllocation", "owner_team_id": "<TEAM-ID>" }
```
The `owner_team_id` is the team from `/api/teams` whose `product` field matches
the review product. If the product has no owning team, use the team ID of the
team with the most eligible items.

If `under_invested_categories` is empty, `follow_up_actions` is `[]`.

### Step 8 — Evidence samples

For each category, take the **first 3** eligible work item IDs (sorted ascending
by ID) that belong to that category. Always 3 items per category — even for
under-invested categories.

### Pitfalls

- **Percentage rounding**: Always round to **1 decimal place**. 28.125… → 28.1,
  not 28.13 or 28.
- **Basis points are integers**: Round `gap_basis_points` to the nearest integer.
  ( (28.125 - 45.0) × 100 = -1687.5 → -1688 or -1690? Use round-half-up or match
  the API's rounding. Train gold outputs use whole-integer bp.)
- **Zero eligible items**: If eligible_total = 0, all percentages are 0.0, gaps
  are 0, under_invested is `[]`, largest_negative_gap is `null`.
- **Template key names vary**: Task 001/004 use `bucket_rows` vs `category_mix`.
  Always match the exact key from the answer template — never hardcode one name.
- **Category set is fixed**: NewFeature, TechDebt, Reliability, Security. Even if
  a category has 0 eligible items, include its row with count=0.

---

## Task Type 2 — SLA Aging Snapshot

Template keys: `included_work_item_ids`, `overdue_work_item_ids`,
`aging_bucket_counts` (or `aging_buckets`), `owner_hotspots`, `team_hotspots`,
`duplicate_clusters` (or `duplicate_cluster_representatives`),
`escaped_severity_count`, `missing_owner_work_item_ids`.

### Step 1 — Fetch data

```
GET /api/work-items?product=<Product>
GET /api/status-history?product=<Product>
GET /api/sla-policies
GET /api/owners
GET /api/teams
```

### Step 2 — Define the included population

Filter work items to those where:
- `work_type` is `"Reliability"` OR `"Security"`
- The item is **open/active** (status NOT in terminal set: Done, Closed,
  Completed, Resolved) **OR** it was closed within the `recent_closed_window_days`
  (i.e., closed_date ≥ as_of_date − window_days + 1, inclusive of both ends).

The "closed within window" check: examine status-history. If the item's latest
status is terminal and the transition timestamp falls within
`[as_of_date − window_days + 1, as_of_date]`, it is included.

Sort `included_work_item_ids` ascending.

`included_count` = length of that list.

### Step 3 — Compute age and bucket

For each included item, compute `age_days`:
```
age_days = (as_of_date − created_date).days
```
Use calendar days (date subtraction), not 24-hour periods. Include both start
and end? Train answers are consistent with: `as_of_date − created_date` in days
(fractional days truncated/floor, or simply date diff).

Buckets (inclusive on both ends):
| Bucket | Range |
|--------|-------|
| 0-7    | 0–7 days |
| 8-14   | 8–14 days |
| 15-30  | 15–30 days |
| 31+    | 31+ days |

The bucket label is the key: `"0-7"`, `"8-14"`, `"15-30"`, `"31+"`.

### Step 4 — Determine overdue

Fetch SLA policies. Each policy maps a `severity` (or `priority`) to a
`max_age_days` (or `target_hours` — convert to days by dividing by 24, ceiling).

An item is **overdue** when:
```
age_days >= sla_target_days
```
(Use `>=`, not `>`.)

Sort `overdue_work_item_ids` ascending.

### Step 5 — Aging buckets

Count included items in each aging bucket. The sum of all bucket counts must
equal `included_count`.

### Step 6 — Owner and team hotspots

For **overdue** items only:
- Group by `owner_id`. For each owner: `overdue_count` = number of overdue items,
  `max_age_days` = max age among those items.
- Filter out owners with `overdue_count == 0`.
- Sort descending by `overdue_count`, then descending by `max_age_days`.
- Do the same for `team_id` → team hotspots.

### Step 7 — Duplicate clusters

The API (or work-item data) provides duplicate cluster info. Each cluster has a
`cluster_id` (e.g., `"DUP-001"`), a `representative_work_item_id` (the canonical
item), and `member_ids` (all items in the cluster including the representative).

**Filter**: only include clusters where **at least one member** appears in
`included_work_item_ids`. When a cluster qualifies, include ALL its member_ids
in the output (not just the ones that are in the included set).

Sort clusters by `cluster_id` ascending.

Template key names match the template exactly: `duplicate_clusters` or
`duplicate_cluster_representatives`.

### Step 8 — Escaped severity count

An item's severity has **escaped** if its severity was **upgraded** (increased
in criticality) at any point in its lifecycle. Severity values are ordinal: lower
numeric value = more severe (P0 > P1 > P2 > P3, or Sev0 > Sev1 > Sev2).

Check status-history for each included item: if any transition shows a severity
that is **more severe** (lower ordinal) than the item's **initial** severity,
count it as escaped. The initial severity is the severity from the earliest
status-history record for that item.

`escaped_severity_count` = count of included items with at least one severity
upgrade.

### Step 9 — Missing owners

List `work_item_id`s from the included set that have **no owner** (`owner_id` is
null, empty, or `"UNASSIGNED"`). Sort ascending.

### Pitfalls

- **Window boundary**: "21 days inclusive" means the closed window is
  `[as_of_date − 20, as_of_date]` (21 calendar days including both ends). Verify
  against train examples which interpretation matches.
- **SLA target conversion**: If SLA policies return hours, convert to days with
  ceiling division: `ceil(target_hours / 24)`. Don't use float comparison.
- **Duplicate clusters include ALL members**: Even members not in the included
  population. Only the cluster-level filter (≥1 member in included) matters.
- **Owner hotspots only for overdue**: Not all included items. Hotspots are about
  overdue risk concentration.
- **Teams endpoint may return product-level teams**: Map team ownership via the
  `product` field or by looking at which team most items belong to.
- **Severity ordinal direction**: Lower number = more severe. Escaped = severity
  number decreased (got more critical). Check the actual data — some APIs use
  reverse ordering (higher = more severe). Trust the data, not assumptions.

---

## Task Type 3 — Release Readiness Rollup

Template keys: `release_id`, `as_of_date`, `ship_decision`, `risk_tier`,
`milestones`, `gating_work_item_ids`, `blocker_cause_counts`,
`critical_dependency_chain`, `owner_escalation_ids`.

### Step 1 — Fetch data

```
GET /api/releases/<release_id>
GET /api/milestones?release_id=<release_id>
GET /api/milestone-items?release_id=<release_id>
GET /api/work-items?release_id=<release_id>
GET /api/status-history?product=<Product>
GET /api/dependencies
GET /api/blockers?active=true
GET /api/owners
GET /api/teams
```

### Step 2 — Milestone completion

For each milestone (sorted by `milestone_id` ascending):
- `critical`: from the milestone record (boolean).
- `completion_percentage`: count of milestone-items with terminal status (Done,
  Closed, Completed) divided by total milestone-items × 100, **rounded to 1
  decimal place**.

Use `/api/milestone-items` to get the items per milestone and their statuses.

### Step 3 — Gating work items

A work item is **gating** if it has at least one **active blocker** (from
`/api/blockers?active=true`). Alternatively: items whose `is_gating` or
`blocks_release` field is true. Cross-reference with blockers API.

Sort `gating_work_item_ids` ascending.

### Step 4 — Blocker cause counts

For the active blockers on gating items, count by `cause`. The set of causes is
fixed: `ExternalDependency`, `Environment`, `SecurityReview`, `Capacity`,
`DesignDecision`, `DataMigration`, `Vendor`, `OwnershipGap`. Every cause must
appear in the output, even with count 0.

### Step 5 — Ship decision

| Condition | Decision |
|---|---|
| No gating items AND all critical milestones ≥ 90% complete | `"Ship"` |
| Some gating items OR critical milestones partially complete (50–90%) | `"Hold"` |
| Multiple active blockers on gating items AND critical milestones < 50% complete | `"NoShip"` |

The exact thresholds should be calibrated against the release record's own
status/hints. Use the release status field if present (e.g., `"Blocked"` →
NoShip). The train example (task 003) shows `"NoShip"` with 4 gating items and
critical milestones at 28.6%–83.3%.

Conservative rule: if any gating item has an active blocker, the minimum
decision is `"Hold"`. If multiple critical milestones are below 50%, it's
`"NoShip"`.

### Step 6 — Risk tier

| Condition | Tier |
|---|---|
| 0 gating items, all critical milestones ≥ 90% | `"Low"` |
| 1–2 gating items, critical milestones mostly ≥ 70% | `"Medium"` |
| 3+ gating items, OR any critical milestone < 50% | `"High"` |

### Step 7 — Critical dependency chain

From `/api/dependencies`, build the dependency graph. Identify the **longest
path** through gating work items (or through all release-scoped items if gating
items don't form a connected path). The chain goes from **upstream** (dependency)
to **downstream** (dependent).

Do **not** sort this list. It must reflect the actual dependency order.

If dependencies are expressed as `source → target` where `source` depends on
`target`, then the chain goes from the most upstream (root dependency) to the
most downstream (final dependent). Read the API field names carefully — some use
`upstream_id`/`downstream_id`, others use `depends_on`/`required_by`.

### Step 8 — Owner escalations

Collect the `owner_id` of every gating work item. If a gating item has no owner
(null, empty, `"UNASSIGNED"`), include the literal string `"UNASSIGNED"`.
Sort ascending. Deduplicate.

### Pitfalls

- **Milestone percentage**: Count terminal-status items / total items. Don't
  count "InProgress" or "Open" items as complete.
- **Dependency chain direction**: The output is upstream→downstream. If the
  dependency API says "A depends on B", then B is upstream, A is downstream.
  Chain order: B → A (upstream first).
- **Gating items may not be in the work-items list**: Cross-check blockers API
  against work items. A blocker may reference an item that isn't returned by the
  work-items query — include it anyway if it's blocking the release.
- **Blocker cause is an enum**: Include every cause key with count 0 if unused.
  The template has a fixed set of keys — don't omit any.
- **Milestone sorting**: Sort by milestone_id as a string (lexicographic), not
  by extracted numeric suffix. The IDs are formatted consistently so string sort
  matches numeric intent (e.g., MS-PAY2026Q1-01, MS-PAY2026Q1-02, …).

---

## Cross-Cutting Rules

### Date handling
- All dates are ISO 8601 (`YYYY-MM-DD`). Compute date differences using calendar
  days.
- Quarter boundaries: Q1 = Jan 1 – Mar 31, Q2 = Apr 1 – Jun 30, Q3 = Jul 1 –
  Sep 30, Q4 = Oct 1 – Dec 31.

### Percentage rounding
- Always round to **1 decimal place** using standard rounding (half-up or
  half-even — train outputs are consistent with whatever the environment API's
  numeric precision produces).
- Round only the final displayed value, not intermediate steps.

### Sorting
- Work item IDs: string sort ascending (lexicographic). Since IDs are
  zero-padded (`WI-0001`), this matches numeric order.
- Owner IDs, team IDs: string sort ascending.
- Milestone IDs: string sort ascending.
- Cluster IDs: string sort ascending.

### Template adherence
- **Always use the exact keys** from the provided `answer_template.json`. Key
  names vary between task variants (e.g., `bucket_rows` vs `category_mix`,
  `aging_bucket_counts` vs `aging_buckets`, `duplicate_clusters` vs
  `duplicate_cluster_representatives`).
- **Never add extra keys** beyond what the template defines.
- **Return JSON only** — no markdown fences, no commentary.

### Missing/empty data
- Empty arrays: `[]`, not `null` and not omitted.
- Nullable scalar fields (like `largest_negative_gap_category`): use JSON
  `null` when there is no meaningful value.
- Zero counts: output `0`, not `null` and not omitted.
