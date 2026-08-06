# Portfolio Engineering Skill

Solve portfolio-mix, SLA-aging, and release-readiness assessment tasks against a shared API environment containing work items, targets, policies, releases, milestones, blockers, and dependencies.

## Entry Checklist

Before building an answer, read these three inputs:

1. **Task prompt** (`input/prompt.txt`) — scope, domain, target date or quarter, the specific question to answer.
2. **Answer template** (`input/payloads/answer_template.json`) — the exact JSON schema the answer must match. Every `required` field must be present. Every `enum` or `const` must be respected. Sort orders, rounding rules, and field descriptions in the schema are binding.
3. **Environment access** (`environment_access.md` at the project root) — base URL, available endpoints, any required headers or tokens.

## Environment and Data Sources

All tasks share a REST API at the base URL from the environment access file. Use only the endpoints listed there. The data model includes these entities:

| Endpoint | Returns |
|---|---|
| `GET /api/work-items` | All work items with their full record |
| `GET /api/mix-targets` | Target portfolio-mix percentages per scope |
| `GET /api/sla-policy` | SLA days-to-due by severity band |
| `GET /api/releases` | All releases |
| `GET /api/releases/{id}` | One release with its milestones and blockers |
| `GET /api/milestones` | All milestones |
| `GET /api/dependencies` | All dependency relationships |
| `GET /api/blockers` | All blocker records |
| `POST /api/query` | Restricted SQL query (requires token) |

### Work Item Fields (authoritative)

| Field | Meaning |
|---|---|
| `id` | Unique work item identifier |
| `status` | Authoritative lifecycle state: Backlog, In Progress, Review, Done, Verified, Deployed, Closed, Duplicate, Cancelled, Reopened |
| `work_type` | Primary work classification: Feature, Enhancement, Refactor, Chore, Dependency, Bug, Incident, Reliability, Security, Compliance |
| `labels` | Array of tag strings (e.g. `["security","cve","rollout"]`) |
| `title` | Human-readable summary — may contain hints when labels are stale |
| `team` | Owning engineering team |
| `product_area` | Owning product area |
| `closed_at` | ISO date when item reached a terminal state; `null` if still open |
| `due_at` | SLA deadline date |
| `created_at` | Creation date |
| `severity` | S1, S2, S3, or S4 |
| `owner` | Assigned person; `null` means unassigned |
| `duplicate_of` | If set, this item is a duplicate of the referenced primary item |
| `milestone_id` | Milestone this item belongs to |
| `release_id` | Release this item belongs to |
| `mirror_status` | Stale mirror/export status — **ignore this field** |
| `legacy_category` | Pre-portfolio classification — **ignore this field** |

### Key Status Groups

- **Complete / Closed** (terminal): `Done`, `Verified`, `Deployed`, `Closed`
- **Not complete**: `Backlog`, `In Progress`, `Review`, `Reopened`
- **Excluded from primary counts**: `Duplicate`, `Cancelled`

## Portfolio Category Classification

Every work item must be assigned to exactly one of four portfolio categories: `NewFeature`, `TechDebt`, `Reliability`, `Security`. Use the **work-type-first with label overrides** convention:

### Step 1 — Security override always wins

If `"security"` is in the item's `labels` array, classify as **Security**.  
If `work_type` is `"Security"`, classify as **Security**.

### Step 2 — Map by work_type

| work_type | Default category |
|---|---|
| `Feature`, `Enhancement` | **NewFeature** |
| `Refactor`, `Chore`, `Dependency` | **TechDebt** |
| `Bug`, `Incident`, `Reliability` | **Reliability** |
| `Compliance` | **Security** if `"security"` in labels, else **TechDebt** |

### Step 3 — Label overrides for TechDebt types

For items whose work_type would default to TechDebt:
- If labels contain `"reliability"`, reclassify as **Reliability**.

### Resolving conflicting signals

When labels and work_type point in different directions, the priority order is:

1. `"security"` in labels → Security (highest priority)
2. `"reliability"` in labels AND work_type is Refactor/Chore/Dependency → Reliability
3. Otherwise, work_type determines the category

The `title` field may contain hints like "with stale security label" — use these to confirm when a label should be disregarded, but do not base primary classification on title alone.

## Task Type 1 — Portfolio Mix Review

**Goal**: Compare the actual category mix of closed work items against a target mix, identify under-invested categories, and recommend a rebalance action.

### Scope

Find the target mix row whose `scope_id` matches the task's scope. The target row provides percentage targets for each category.

### Filtering work items

1. **Team and product area**: Filter by the team and product_area values specified in the task scope. When the scope names multiple teams or product areas (e.g. "Atlas Backend + Identity"), match items where `team` is in the team set AND `product_area` is in the area set.
2. **Quarter filter**: Keep only items whose `closed_at` falls within the calendar quarter. Q4 2025 = 2025-10-01 through 2025-12-31.
3. **Exclude non-closed**: Keep only items whose `status` is in the Complete/Closed group.
4. **Exclude distractor records**: Remove items with `status` = `"Duplicate"`, `status` = `"Cancelled"`, or a non-null `duplicate_of` field. These go into the exclusion lists.

### Computing the mix

- Count items in each of the four categories.
- Divide each count by total included items to get actual percentages.
- Round all percentages to **1 decimal place**.
- `gap_pct = actual_pct − target_pct` (both in percentage points).

### Under-invested categories

Categories where `gap_pct < 0`, sorted from **most negative** gap to least negative.

### Follow-up action

- `REBALANCE_CAPACITY` when under-invested categories exist. `primary_category` is the largest-deficit category, `secondary_category` the next, `rationale_code` = `"LARGEST_NEGATIVE_GAP"`.
- `MAINTAIN_CURRENT_MIX` when no negative gaps exist.

### Exclusion flags

- `excluded_duplicate_ids`: items in scope with `status = "Duplicate"` OR a non-null `duplicate_of`.
- `excluded_cancelled_ids`: items in scope with `status = "Cancelled"`.
- `ignored_mirror_status_and_legacy_category`: always `true` — mirror_status and legacy_category are stale and must not influence decisions.

### Sorting within the answer

- `included_work_item_ids`: sort by `closed_at` ascending, then by `id` ascending.
- Exclusion list IDs: sort lexicographically.
- `gap_table` rows: always in order NewFeature, TechDebt, Reliability, Security.
- Team and product area arrays: sort alphabetically.

## Task Type 2 — SLA Aging Audit

**Goal**: Review the SLA status of reliability and security work items, identify overdue items, compute aging distribution and breach rate, and report duplicate clusters.

### SLA Policy

The SLA policy maps severity to allowed days-to-due:

| Severity | Days to Due |
|---|---|
| S1 | 3 |
| S2 | 10 |
| S3 | 21 |
| S4 | 45 |

An item's `due_at` field is authoritative for determining whether SLA was met. Do not recalculate due_at from created_at and the policy; use `due_at` as given.

### Scoping the population

1. Filter work items by the specified team(s).
2. Classify each item using the portfolio category convention — keep only those classified as **Security** or **Reliability**.
3. Separate primary from duplicate: items with `status = "Duplicate"` or a non-null `duplicate_of` are **not primary**.

### Included primary IDs

The primary SLA population consists of all Security/Reliability items in scope that are not duplicates. Sort lexicographically.

### Overdue determination

An item is overdue when:
- `due_at` < `as_of` date (the SLA deadline has passed), AND
- The item is **not yet closed** as of the as_of date (i.e. `closed_at` is `null` or `closed_at` > `as_of`).

Items already closed before their due date are not overdue. Items closed after their due date but before the as_of date are late closures — include them as overdue.

### Aging buckets

For each overdue item, calculate `aging_days = as_of − due_at` (for open items) or `aging_days = closed_at − due_at` (for closed-late items). Bucket into:

| Bucket | Days past due |
|---|---|
| 0-3 | 0–3 |
| 4-7 | 4–7 |
| 8-14 | 8–14 |
| 15-30 | 15–30 |
| 31+ | ≥31 |

### Overdue by team and hotspot

- Count overdue items per team. List teams alphabetically.
- Find the `(team, owner)` pair with the most overdue items. If owner is `null`, use `"UNASSIGNED"`.

### Duplicate clusters

For every primary item that has duplicates, report a cluster with:
- `primary_id`: the canonical work item ID
- `duplicate_ids`: the duplicate item IDs sorted lexicographically

Sort clusters by `primary_id`.

### Missing owners

IDs of primary items where `owner` is `null`, sorted lexicographically.

### Breach rate

`breach_rate = overdue_count / included_primary_count`, rounded to **3 decimal places**.

### Escalation queue

When the answer template requires an escalation queue, sort overdue primary items by priority order:
1. Severity (S1 first, then S2, S3, S4)
2. Then by `due_at` ascending (earliest deadline first)

## Task Type 3 — Release Readiness Assessment

**Goal**: Evaluate whether a release is ready to ship by examining milestone completion, gating work items, unresolved blockers, and critical dependency chains.

### Data sources for a release

1. Fetch the release by ID (`GET /api/releases/{id}`) — this returns the release record plus its milestones and blockers.
2. Fetch all work items and filter to those with `release_id` matching the target release.
3. Fetch all dependencies.

### Milestone completion

For each milestone in the release (sorted by `milestone_id` ascending):

1. Count work items assigned to that milestone.
2. Exclude items with `status = "Duplicate"` from the primary count.
3. `complete_primary` = count of primary items with status in `{Done, Verified, Deployed}`.
4. `primary_total` = total primary items in the milestone.
5. `completion_pct` = `(complete_primary / primary_total) × 100`, rounded to **1 decimal place**.

### Gating work item IDs

Non-complete, non-duplicate release work items, sorted ascending with no duplicates. An item gates readiness if its status is not in the Complete set.

### Blocker cause counts

Consider only blockers for the target release. A blocker is counted when:
- `severity` is `"Critical"` or `"High"` (high-impact), AND
- `status` is not `"Resolved"` (still open or in monitoring).

Count by exact `cause` string.

### Critical dependency chains

Look at all dependencies where `relation` = `"blocks-release-readiness"`. For each such dependency where the **blocked** work item is a release work item and the **depends-on** work item is not complete, report the chain as `[blocked_id, depends_on_id]`.

Sort chains lexicographically by the full path.

A dependency is satisfied (not critical) when the depends-on item has a Complete status.

### Readiness score

`readiness_score = completed_primary_count / primary_total`, where:
- Primary items = all release work items excluding those with `status = "Duplicate"`
- Completed = items with status in `{Done, Verified, Deployed}`
- Round to **3 decimal places**.

### Ship decision

Use the readiness score together with blocker severity:
- `NO_SHIP` when unresolved Critical or High blockers exist, or readiness is critically low.
- `SHIP_WITH_WATCH` when readiness is moderate and no Critical blockers are open.
- `SHIP` when all milestones are complete and no unresolved blockers exist.

## Validation Before Submitting

Run these checks against every answer before finalizing:

1. **Schema compliance**: Every `required` field present. Every `const` value matches. No `additionalProperties` violations.
2. **Rounding**: Percentages to 1 decimal place. Rates/scores to 3 decimal places.
3. **Sort order**: IDs and strings sorted as specified in the answer template (lexicographic, ascending, or by a date-then-id compound key).
4. **No duplicates**: ID arrays contain each ID at most once.
5. **Counts sum correctly**: Category counts sum to `total_included`. Percentages sum to approximately 100%.
6. **Duplicate handling**: No item appears in both `included` and `excluded` lists. Items with `duplicate_of` set should be in the duplicate exclusion list, not the included set.
7. **Status authority**: Use `status` field, not `mirror_status`, for all state decisions.
8. **Category authority**: Use the portfolio classification convention; do not use `legacy_category`.

## Common Pitfalls

- **Stale mirror_status**: The `mirror_status` field can disagree with `status`. Always use `status` as the authoritative field.
- **Duplicate but not marked**: Some items have `status = "Duplicate"` without a `duplicate_of` reference. They are still duplicates and should be excluded from primary counts.
- **Closed after due date but before as_of**: These items were late (breached SLA) and should be counted as overdue.
- **Quarter boundary precision**: Q4 = October through December. An item closed on September 30 is Q3, not Q4. An item closed on January 1 is Q1 of the next year.
- **Dependencies outside the release**: When tracing dependency chains, the depends-on item may belong to a different release or no release at all. Check its status from the global work items list.
- **Cancelled items**: Even if `closed_at` falls in the target quarter, Cancelled items are never included in primary counts.
- **Compliance work_type with security label**: Classify as Security, not TechDebt.
- **Incident with feature label**: Classify as Reliability (Incident trumps feature label). Use the work_type, not the label, for Bug/Incident.
