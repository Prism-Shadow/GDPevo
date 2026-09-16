---
name: engineering-portfolio
description: >-
  Perform engineering portfolio management tasks using a shared task-environment
  API. Use this skill whenever the user asks you to prepare a portfolio mix
  review, SLA aging audit, or release readiness assessment that involves
  querying work items, mix targets, SLA policies, releases, milestones, blockers,
  or dependencies. Also use this when the user mentions closed-work portfolio
  analysis, overdue SLA work, ship decisions, milestone completion, blocker
  cause counts, or dependency chains. This skill covers portfolio mix
  classification, SLA breach rate calculation, and release readiness scoring
  across engineering teams, quarters, and product areas.
---

# Engineering Portfolio Management

Analyze engineering work-item portfolios against an environment API. The API
exposes work items, mix targets, SLA policy, releases, milestones, blockers,
and dependencies through REST endpoints and supports a restricted SQL query
endpoint.

## Task Types

Three core task types appear in this domain. Read the user's prompt to identify
which is being asked.

### 1. Portfolio Mix Review

Classify closed work items into four portfolio categories, compare against
target mix percentages, and produce rebalancing recommendations.

### 2. SLA Aging Audit

Identify primary SLA-relevant work items, determine overdue status against SLA
policy, compute breach rate, and surface hotspots, missing owners, and
duplicate clusters.

### 3. Release Readiness Assessment

Evaluate a release using milestone data, work-item statuses, blockers, and
dependencies. Produce a ship decision, readiness score, and gating-item list.

## API Reference

The environment base URL is provided as `<TASK_ENV_BASE_URL>` in the user
prompt. The runtime-access notes (typically `environment_access.md`) list the
available endpoints and any token needed for SQL queries.

### REST Endpoints

- `GET /api/work-items` — list all work items
- `GET /api/work-items/{item_id}` — single work item
- `GET /api/mix-targets` — all mix target rows
- `GET /api/sla-policy` — SLA severity-to-days mapping
- `GET /api/releases` — all releases
- `GET /api/releases/{release_id}` — single release with its milestones and blockers
- `GET /api/milestones` — all milestones
- `GET /api/dependencies` — all dependency records
- `GET /api/blockers` — all blocker records
- `POST /api/query` — restricted SQL endpoint (may require `X-Env-Token` header)

### Work-Item Schema

```json
{
  "id": "WI-24024-P001",
  "title": "...",
  "status": "Closed | Verified | Done | Deployed | Review | In Progress | Backlog | Duplicate | Cancelled | ...",
  "work_type": "Feature | Enhancement | Refactor | Bug | Chore | Dependency | Security | Reliability | Incident | Compliance",
  "labels": ["array", "of", "strings"],
  "legacy_category": "bug | new | security | tech-debt | maintenance | quality | admin | incident | ...",
  "mirror_status": "Closed | Open | Done | In Progress | Blocked | ... (UNRELIABLE - IGNORE THIS FIELD)",
  "team": "string",
  "product_area": "string",
  "owner": "string or null",
  "priority": "integer 1-5",
  "severity": "S1 | S2 | S3 | S4",
  "story_points": "integer",
  "created_at": "YYYY-MM-DD",
  "due_at": "YYYY-MM-DD",
  "closed_at": "YYYY-MM-DD | null",
  "duplicate_of": "string work-item id or null",
  "release_id": "string or null",
  "milestone_id": "string or null"
}
```

### Mix-Target Schema

```json
{
  "scope_id": "string",
  "quarter": "string",
  "team_group": "string",
  "product_area": "string",
  "new_feature_pct": "float (fraction, multiply by 100 for percentage points)",
  "tech_debt_pct": "float",
  "reliability_pct": "float",
  "security_pct": "float"
}
```

### SLA Policy Schema

```json
{
  "severity": "S1",
  "days_to_due": 3
}
```

The policy array has four entries: S1 (3 days), S2 (10 days), S3 (21 days),
S4 (45 days).

### Release Schema (from `/api/releases/{release_id}`)

Returns a `release` object plus arrays of `milestones` and `blockers` for that
release.

### Milestone Schema

```json
{
  "id": "MIL-...",
  "name": "string",
  "owner_team": "string",
  "release_id": "string"
}
```

### Blocker Schema

```json
{
  "id": "BLK-...",
  "cause": "string",
  "severity": "Low | Medium | High | Critical",
  "status": "Open | Monitoring | Resolved",
  "work_item_id": "string",
  "release_id": "string"
}
```

### Dependency Schema

```json
{
  "blocked_id": "string",
  "depends_on_id": "string",
  "relation": "depends-on | blocks-release-readiness | validation-required | ..."
}
```

## Core Workflow

All three task types follow this general approach:

1. Fetch data from the environment API endpoints relevant to the task.
2. Filter to the task's scope (teams, product areas, quarter, release, as-of
   date).
3. Classify each included work item, excluding Duplicate/Cancelled records and
   identifying distractor records.
4. Compute the required metrics (percentages, gaps, breach rates, readiness
   scores).
5. Return the answer JSON matching the provided answer template.

### Step-by-Step API Data Gathering

Always start by fetching the primary collection:

1. `GET /api/work-items` to get all work items.
2. Depending on the task type, also fetch:
   - **Mix review**: `GET /api/mix-targets`
   - **SLA audit**: `GET /api/sla-policy`
   - **Release assessment**: `GET /api/releases/{release_id}` (provides
     release, milestones, and blockers in one call), then `GET
     /api/dependencies` for dependency records

You may also inspect individual work items with `GET
/api/work-items/{item_id}` when you need to double-check data for specific
items. Batch reading the full work-items list is preferred over individual
fetches.

### Authoritative Field Resolution

The environment has stale or legacy fields that must not be used as truth:

- **`status`** is authoritative for work state. **`mirror_status`** is stale
  and must always be ignored.
- **`work_type`** and **`labels`** are authoritative for classification.
  **`legacy_category`** is a weaker fallback only.
- **`severity`** is authoritative for SLA severity.
- **`due_at`** is authoritative for SLA due-date calculations.
- **`closed_at`** is authoritative for when an item was closed.
- **`duplicate_of`** points to the primary/canonical work item. When an item
  has `status: "Duplicate"` and a `duplicate_of` value, the `duplicate_of`
  item is the primary. When an item has `status: "Closed"` but `duplicate_of`
  is non-null, treat it as an effective duplicate that should be excluded.

### Inclusion Rules (All Task Types)

A work item is **included as primary** when:

- It matches the task scope (teams, product areas, quarter/release,
  categories).
- Its `status` is NOT "Duplicate" and NOT "Cancelled".
- It is not a distractor record (stale mirror, wrong scope, stale-export
  artifact).

A work item is **excluded** when:

- `status` is "Duplicate" — flag as excluded (duplicate), note the
  `duplicate_of` pointer.
- `status` is "Cancelled" — flag as excluded (cancelled).
- It is in scope but is a stale-mirror record, legacy-export artifact, or
  otherwise not a genuine primary work record. Items with labels like
  `stale-export` or with `status: "Closed"` but `duplicate_of` pointing at a
  primary should be treated as duplicates rather than primaries.

### Ordering Conventions

Apply these ordering rules consistently across all answer outputs:

- Work-item ID lists: sort lexicographically (standard string sort, e.g.,
  Python `sorted()` with default string comparison).
- Team lists: sort alphabetically.
- Duplicate clusters: sort by `primary_id` ascending, with `duplicate_ids`
  sorted lexicographically within each cluster.
- Milestone lists: sort by `milestone_id` ascending.
- Gap table rows: present in fixed category order: NewFeature, TechDebt,
  Reliability, Security.
- Under-invested categories: order from most negative gap to least negative
  gap.
- Escalation queue: order by severity S1 first, then `due_at` ascending within
  each severity tier.

---

## Task 1: Portfolio Mix Review

### Scope Identification

Extract from the user prompt:

- `scope_id` — the identifier for this analysis
- `quarter` — e.g., "2025-Q4"
- `teams` — the list of team names in scope
- `product_areas` — the list of product areas in scope (may be a single
  product area or multiple)
- Target mix: find the `mix_targets` row where `scope_id` matches the given
  scope id

### Work-Item Filtering

From all work items, select those where:

- `team` is in the scope teams list
- `product_area` is in the scope product areas list
- `closed_at` falls within the scope quarter (for Q4 2025: months 10, 11, 12)
- `status` is NOT "Duplicate" and NOT "Cancelled"

### Portfolio Category Classification

Classify each included work item into exactly one of: **NewFeature**,
**TechDebt**, **Reliability**, **Security**.

Use this priority-ranked resolution rule to resolve conflicting signals:

**Security** — when any of these is true:

- `work_type` is "Security" or "Compliance"
- `labels` contain `security`, `cve`, `auth`, or `encryption`
- `legacy_category` is "security"
- When `work_type` is "Feature", "Enhancement", or "Dependency" and labels or
  legacy_category point to security

**Reliability** — when any of these is true:

- `work_type` is "Reliability" or "Incident"
- `labels` contain `reliability`, `outage`, `incident`, `latency`, or `flaky`
- `legacy_category` is "incident"

**TechDebt** — when any of these is true:

- `work_type` is "Refactor", "Bug", "Chore", or "Dependency"
- `legacy_category` is "tech-debt", "bug", "maintenance", "admin", or
  "cleanup"
- `work_type` is "Feature" or "Enhancement" but labels include `migration` or
  `cleanup` (indicating maintenance work rather than new features)

**NewFeature** — when:

- `work_type` is "Feature" or "Enhancement" AND no stronger signal pushes it
  into another category
- `legacy_category` is "new" AND no contradictory label or work_type signal
  exists

**Tie-breaking**: When multiple signals point to different categories, resolve
by evidence weight: a matching `work_type` or `labels` signal beats a matching
`legacy_category`. When signals are equally specific, prefer the one that best
describes the work's primary nature. If still ambiguous, read the item's
`title` for context.

A signal is stronger when it is more specific. For example, `work_type:
"Security"` is unambiguous and should dominate any label or legacy signal.
`labels: ["security"]` is strong but could be stale; cross-check with
`work_type` and `legacy_category`. `legacy_category: "security"` alone is the
weakest security signal and should only classify an item as Security when
`work_type` and `labels` are silent or ambiguous.

### Identifying Distractors and Exclusions

In addition to Duplicate and Cancelled items, identify distractor records that
should be excluded:

- Items whose `duplicate_of` points at a primary item even if their own
  `status` is not "Duplicate" (check for items Closed but with `duplicate_of`
  set, where the Closed status may be stale).
- Items with labels like `stale-export` that indicate they are mirror
  artifacts.
- Items that match the scope teams/product_areas but have `closed_at` outside
  the quarter.

For each excluded item, determine the exclusion reason: duplicate, cancelled,
or distractor.

### Computing the Mix

1. Count items per category to produce `category_counts`.
2. Compute `category_percentages`: (count_in_category / total_included) * 100,
   rounded to 1 decimal place.
3. Build `gap_table`: for each category in order NewFeature, TechDebt,
   Reliability, Security:
   - `target_pct` from the mix-targets row (multiply by 100: e.g., 0.34
     becomes 34.0)
   - `actual_pct` from step 2
   - `gap_pct` = `actual_pct - target_pct`, rounded to 1 decimal place
4. Identify `under_invested_categories`: categories with negative `gap_pct`,
   sorted from most negative to least.
5. Determine recommended action:
   - If there are negative gaps: action = REBALANCE_CAPACITY,
     primary_category = the most under-invested category, secondary_category =
     the second most under-invested (or null if only one), rationale_code =
     LARGEST_NEGATIVE_GAP
   - If all gaps are non-negative: action = MAINTAIN_CURRENT_MIX,
     primary_category = null, secondary_category = null, rationale_code =
     NO_NEGATIVE_GAPS

### Ordering

- `included_work_item_ids`: sorted by `closed_at` ascending, then by `id`
  ascending for ties.
- `excluded_*_ids`: sorted by `closed_at` ascending, then by `id` ascending.

---

## Task 2: SLA Aging Audit

### Scope Identification

Extract from the user prompt:

- `teams` — the list of team names
- `as_of` date — the date for aging calculations
- `recent_closed_window_days` — items closed within this many days before
  `as_of` are still considered recent closures, not overdue
- `categories` or `sla_categories` — e.g., ["Security", "Reliability"]

### Work-Item Classification for SLA

An item is SLA-relevant if its portfolio category (as determined by the Task 1
classification rules above) matches one of the specified SLA categories.

For SLA-specific tasks that only ask about Reliability and Security, use the
same classification rules narrowed to those two categories: any item that
would classify as Reliability or Security under the full rules is included.

### Identifying Primary vs. Duplicate

- If `status` is "Duplicate" and `duplicate_of` is set: the item is a
  duplicate. The `duplicate_of` item is the primary.
- If `status` is "Duplicate" but `duplicate_of` is null: treat as an anomalous
  record; exclude from primary set.
- Items with `status` "Cancelled" are excluded from the primary set.

Build `duplicate_clusters`: for each primary that has one or more duplicates
pointing at it, list the `primary_id` and the sorted `duplicate_ids`. Include
clusters even when the primary id itself is in the primary set (the duplicate
should still be reported). Sort clusters by `primary_id`.

### SLA Overdue Calculation

1. Parse `due_at` and `as_of` as dates using Python's `datetime.date` or
   `datetime.fromisoformat`.
2. Compute aging days: `aging_days = (as_of - due_at).days`. If `as_of` is
   before `due_at`, `aging_days` is negative and the item is not yet due.
3. Look up the SLA policy from `GET /api/sla-policy`. Map severity to
   `days_to_due`:
   - S1: 3 days
   - S2: 10 days
   - S3: 21 days
   - S4: 45 days
4. An item is **overdue** when `aging_days > sla_policy[severity].days_to_due`
   AND the item has not been recently closed.
5. **Recent closure check**: if an item's `closed_at` is not null and
   `(as_of - closed_at).days <= recent_closed_window_days`, the item was
   recently closed and is NOT overdue, regardless of aging days.

### Aging Buckets

Distribute included primary items into aging buckets based on `aging_days =
(as_of - due_at).days`:

- **0-3**: 0 <= aging_days <= 3
- **4-7**: 4 <= aging_days <= 7
- **8-14**: 8 <= aging_days <= 14
- **15-30**: 15 <= aging_days <= 30
- **31+**: aging_days >= 31

Count items in each bucket. If aging_days is negative (item not yet due),
place in the 0-3 bucket (or 0 depending on convention — follow the answer
template's field definitions).

### Team Overdue Counts

For each team in scope, count the number of included primary items that are
overdue. List teams alphabetically.

### Top Hotspot

Find the owner/team pair with the most overdue primary records. If there's a
tie, choose the pair with the highest-severity overdue items (most S1 items
first, then S2, etc.). Report:

- `team`: the team name
- `owner`: the owner name, or "UNASSIGNED" when owner is null/missing
- `overdue_count`: the count

### Missing Owner IDs

List all included primary ids where `owner` is null/null-like. Sort
lexicographically.

### Breach Rate

`breach_rate = len(overdue_primary_ids) / len(included_primary_ids)`, rounded
to exactly 3 decimal places. Use Python's `round(breach_rate, 3)`.

### Escalation Queue (when required)

Order overdue primary ids by priority for escalation:

1. Highest severity first (S1, then S2, then S3, then S4)
2. Within same severity: earliest `due_at` first (oldest due date is most
   urgent)
3. Within same due_at: lexicographic by id

### Overdue Counts by Severity (when required)

Count overdue primary items grouped by severity tier (S1, S2, S3, S4). Each
count is an integer.

---

## Task 3: Release Readiness Assessment

### Scope Identification

Extract the `release_id` from the user prompt.

### Data Gathering

1. `GET /api/releases/{release_id}` — returns the release object, its
   milestones, and its blockers in a single response.
2. `GET /api/dependencies` — all dependency records (filter to those involving
   the release's work items).
3. `GET /api/work-items` — all work items (filter to those with `release_id`
   matching the target release).

### Work-Item Filtering

Identify all work items where `release_id` matches the target release. These
are the release's primary work items. Treat every such work item as primary
unless its `status` is "Duplicate" or "Cancelled".

### Milestone Completion

For each milestone associated with the release:

- `complete_primary`: count of primary work items in this milestone with
  `status` in {"Done", "Verified", "Deployed", "Closed"} (any status
  indicating completion).
- `primary_total`: total primary work items in this milestone.
- `completion_pct`: (complete_primary / primary_total) * 100, rounded to 1
  decimal place. If `primary_total` is 0, use 0.0.

Sort the `milestone_completion` array by `milestone_id` ascending.

### Ship Decision

Determine the ship decision using this logic:

- **SHIP**: All milestones have `completion_pct >= 100.0` AND there are no
  unresolved blockers with severity "High" or "Critical" for this release.
- **SHIP_WITH_WATCH**: At least one milestone has `completion_pct >= 100.0`
  AND the average completion across all milestones is >= 70.0%, AND there are
  no unresolved blockers with severity "Critical". May have unresolved
  "High"-severity blockers.
- **NO_SHIP**: Otherwise — incomplete milestones with low completion,
  unresolved "Critical" blockers, or a combination that prevents ship.

"Unresolved" blockers have `status` NOT "Resolved" (i.e., "Open" or
"Monitoring").

### Gating Work Items

List all primary work items for the release that are NOT in a completed state.
A work item is "complete" when its `status` is "Done", "Verified", "Deployed",
or "Closed". Sort the list lexicographically with no duplicates.

### Unresolved High-Impact Blocker Causes

Count blockers for the release where:

- `severity` is "High" or "Critical"
- `status` is NOT "Resolved" (i.e., "Open" or "Monitoring")

Group by exact `cause` text. Key the counts by the cause string exactly as it
appears in the API.

The data is most reliably read from the per-release endpoint (`GET
/api/releases/{release_id}`) which returns blockers already scoped to the
release.

### Critical Dependency Chains

A critical dependency chain exists when:

- A non-complete release work item (`blocked_id`) appears in a dependency
  record
- The `depends_on_id` work item is also non-complete

Build chains as ordered paths: `[blocked_id, depends_on_id]`. If the
dependency's `depends_on_id` itself appears as a `blocked_id` in another
dependency record whose target is also non-complete, extend the chain.

Sort chains lexicographically by the full path (compare first element, then
second, etc.).

If there are no critical dependency chains, return `[]`.

### Readiness Score

`readiness_score = total_completed_primary / total_primary`, rounded to 3
decimal places.

Where "completed" means `status` in {"Done", "Verified", "Deployed", "Closed"}
and "total_primary" is the count of all non-Duplicate, non-Cancelled release
work items.

---

## Common Pitfalls

1. **Mirror Field Confusion**: `mirror_status` is stale. Never use it. Always
   read `status` for the real work state.

2. **Legacy Category Overreliance**: `legacy_category` is a weak fallback. Use
   `work_type` and `labels` as primary classification signals. Only fall back
   to `legacy_category` when `work_type` and `labels` are silent.

3. **Duplicate Handling**: When `status` is "Duplicate", the item must be
   excluded from primary counts. The `duplicate_of` pointer identifies the
   primary item — make sure that primary item itself is included if it meets
   scope criteria. An item that is "Closed" but has `duplicate_of` set is
   effectively a duplicate.

4. **Date Arithmetic**: When computing aging, use proper date subtraction.
   `aging_days = (as_of - due_at).days` using Python's `datetime`. If
   `closed_at` is null, `aging_days` = `(as_of - due_at).days` directly.

5. **Percentage Rounding**: Mix percentages to 1 decimal place. Breach rates
   and readiness scores to 3 decimal places. Use Python's built-in `round()`
   function.

6. **Gap Table Order**: Always present categories in the fixed order:
   NewFeature, TechDebt, Reliability, Security — regardless of what order the
   API data uses.

7. **Sort Stability**: For ID lists, use lexicographic string sort. Do not
   sort by numeric substring, do not strip the prefix. "WI-24024-007" sorts
   before "WI-24024-012" and "WI-24024-P001" sorts after both because "P" >
   "0" in ASCII/Unicode string comparison.

8. **Closed-at Window for SLA**: In SLA audits, items with `closed_at` within
   the recent window of `as_of` are not overdue. Check `closed_at` before
   computing overdue status.

9. **Escalation Queue Ordering**: Priority is severity first (S1 > S2 > S3 >
   S4), then `due_at` ascending within the same severity.

10. **Scope Precision for Quarters**: For portfolio mix reviews with quarter
    scoping, only count items whose `closed_at` falls within that quarter's
    months. For Q4 2025: months 10, 11, 12 (October through December). Check
    `closed_at[:7]` or parse the date.

11. **Distractor Identification**: Items that match scope teams/areas but have
    stale labels, wrong quarters, or are mirror artifacts must be excluded and
    listed separately. Look for labels like `stale-export`, or items whose
    `duplicate_of` field reveals they are not genuine primaries.

12. **Percentages Sum Check**: After computing mix percentages, verify that
    the four category percentages sum to approximately 100.0 (allow 0.2
    tolerance for rounding). If they deviate significantly, recheck your
    counts.

## Answer Template Adherence

The user provides an answer template (`answer_template.json` or equivalent
schema). Your output must follow it exactly — every required field present, no
extra fields, enum values matching the allowed set, types matching the schema
constraints.

Before returning the final JSON:

- Verify all required fields are present.
- Check that enum values match the allowed set.
- Verify counts sum correctly to the total included.
- Verify percentages sum to approximately 100% (allow for 0.2 rounding
  tolerance).
- Verify sorting conventions are followed.
- Double-check that Duplicate and Cancelled items are excluded from primary
  counts and listed in the exclusion fields.

Return only the JSON object. Do not include prose, markdown fences, or
commentary outside the JSON unless the answer template explicitly allows prose
fields.

See [references/classification-guide.md](references/classification-guide.md)
for worked examples of the portfolio classification rules across the five
training scenarios.
