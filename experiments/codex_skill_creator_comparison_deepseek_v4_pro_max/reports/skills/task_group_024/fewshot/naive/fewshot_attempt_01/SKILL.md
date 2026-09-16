---
name: portfolio-review
description: Solve engineering portfolio review tasks (mix analysis, SLA aging, release readiness) against a shared REST API with work items, milestones, blockers, dependencies, mix targets, and SLA policy data. Use when the task requires classifying work items into portfolio categories, computing mix gaps, auditing SLA compliance, or assessing release readiness.
---

# Portfolio Review Skill

## Overview

This skill solves engineering portfolio review tasks that query a shared REST API
and produce structured JSON answers. Three task families are covered: portfolio
mix analysis, SLA aging audits, and release readiness assessments.

The API is accessed at a base URL supplied in the task prompt (typically as
`<TASK_ENV_BASE_URL>` or similar token). Endpoint and credential details are
provided in an `environment_access.md` file staged alongside the task. The API
returns JSON; all data extraction uses `curl` piped to `jq`.

## Environment Setup

Before any query, read `environment_access.md` from the task working directory.
Extract:

- `BASE_URL`: the root URL (e.g. `http://task-env:9007`)
- `TOKEN_HEADER`: the header name and value for the read-only SQL endpoint
  (e.g. `X-Env-Token: portfolio-readonly`)

Verify connectivity with `curl -s "$BASE_URL/health"`. Set these as shell
variables for the session.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Connectivity check |
| GET | `/api/work-items` | List work items (supports `?team=`, `?product_area=`, `?status=`, `?quarter=` filters) |
| GET | `/api/work-items/{item_id}` | Single work item detail |
| GET | `/api/mix-targets` | Target portfolio mix percentages by scope |
| GET | `/api/sla-policy` | SLA deadline rules by category and severity |
| GET | `/api/releases` | List releases |
| GET | `/api/releases/{release_id}` | Single release detail |
| GET | `/api/milestones` | List milestones (filter by `?release_id=`) |
| GET | `/api/dependencies` | Dependency edges between work items |
| GET | `/api/blockers` | Blocker records on work items |
| POST | `/api/query` | Read-only SQL queries; include the token header from environment_access.md |

All GET endpoints return JSON arrays or objects. Use `curl -s` and pipe through
`jq` for filtering and transformation.

## Work Item Data Model

Work items have these fields relevant across all task families:

- `id`: string identifier (e.g. `WI-24024-P001`)
- `title`: human-readable summary
- `type`: work-item type string
- `status`: authoritative current state (`Closed`, `In Progress`, `Open`, `Cancelled`, etc.)
- `category`: the portfolio category assigned to this item
- `team`: owning team
- `owner`: assigned person (may be null)
- `product_area`: product area label
- `quarter`: planning quarter (e.g. `2025-Q4`)
- `closed_at`: ISO-8601 timestamp when closed, or null
- `sla_deadline`: ISO-8601 deadline for SLA purposes, or null
- `severity`: severity level (`S1`, `S2`, `S3`, `S4`), or null
- `duplicate_of`: if this item is a duplicate, the id of the canonical primary item
- `release_id`: associated release, or null
- `milestone_id`: associated milestone, or null

### Authoritative vs. Stale Fields

The API may include mirror or legacy fields (e.g. `mirror_status`,
`legacy_category`, `export_status`). These are stale and must not be used.
Always read the authoritative field directly:

- Use `status` for item state, never `mirror_status`
- Use `category` (after classification) for portfolio category, never `legacy_category`
- Use `closed_at` for closure timestamp, never derived or mirrored timestamps

### Primary vs. Duplicate Records

A work item with a non-null `duplicate_of` field points to another canonical
item. The canonical item is the **primary**; the pointing item is the
**duplicate**. Duplicates must be:

- Excluded from all counts, percentages, and statistics
- Reported separately in `duplicate_clusters` or `excluded_duplicate_ids`

Build the primary population by filtering out any item where `duplicate_of` is
non-null. If an item is itself a primary (others point to it), it stays in the
primary population.

### Cancelled Items

Work items with `status` equal to `Cancelled` are excluded from the closed
portfolio population. Report them in `excluded_cancelled_ids`.

## Portfolio Category Classification

Every included work item must be classified into exactly one of these four
categories:

1. `Security`
2. `Reliability`
3. `TechDebt`
4. `NewFeature`

Resolve the category using this priority chain:

1. **Direct category field**: If the work item has an explicit `category` field
   matching one of the four values, use it.
2. **Type-to-category mapping**: Map the work item `type` field:
   - Types containing `security`, `vuln`, `cve`, `appsec` → `Security`
   - Types containing `reliability`, `sre`, `incident`, `resilience` → `Reliability`
   - Types containing `debt`, `refactor`, `cleanup`, `techdebt` → `TechDebt`
   - Types containing `feature`, `enhancement`, `story` → `NewFeature`
3. **Label conventions**: If labels are present, match against the same keyword
   patterns.
4. **Title keyword matching**: Scan the `title` for the same keyword families as
   a last resort.

When signals conflict (e.g. type says `feature` but title mentions `security`),
the higher-priority category wins: Security > Reliability > TechDebt > NewFeature.
A security signal from any source overrides a lower-category signal.

## Task Family 1: Portfolio Mix Analysis

### Workflow

1. **Retrieve the target mix**: `GET /api/mix-targets`, filter by
   `scope_id` to find the target row. Extract `target_pct` for each of the four
   categories.

2. **Fetch in-scope work items**: Query `/api/work-items` with filters matching
   the scope (team, product_area, quarter, status=Closed).

3. **Filter primary population**: Remove duplicates (non-null `duplicate_of`),
   cancelled items, and distractor records that appear in scope but do not
   belong to the primary closed portfolio.

4. **Classify each item**: Apply the portfolio category classification rules
   above.

5. **Compute counts and percentages**: Count items per category. Compute
   `actual_pct = (count / total_included) * 100`. Round to 1 decimal place.

6. **Build the gap table**: For each category in fixed order (NewFeature,
   TechDebt, Reliability, Security), compute `gap_pct = actual_pct - target_pct`.
   Round to 1 decimal place. The `target_pct` values come from the target mix
   row.

7. **Identify under-invested categories**: Categories with negative `gap_pct`,
   sorted from most negative to least negative.

8. **Determine follow-up action**:
   - If any category has negative gap: `action = "REBALANCE_CAPACITY"`,
     `primary_category` = most negative gap category,
     `secondary_category` = second most negative (or null if only one),
     `rationale_code = "LARGEST_NEGATIVE_GAP"`.
   - If no negative gaps: `action = "MAINTAIN_CURRENT_MIX"`,
     `primary_category` = null, `secondary_category` = null,
     `rationale_code = "NO_NEGATIVE_GAPS"`.
   - If data quality issues are suspected: `action = "INVESTIGATE_DATA_QUALITY"`,
     `rationale_code = "DATA_CONFLICT"`.

9. **Collect exclusion flags**: Separate arrays for duplicate ids and cancelled
   ids, sorted ascending. Set `ignored_mirror_status_and_legacy_category` to
   `true`.

10. **Assemble the answer**: Follow the answer template schema exactly. The
    `scope` block must match the task scope parameters. `included_work_item_ids`
    sorted by `closed_at` ascending then `id` ascending. Team names
    alphabetically.

## Task Family 2: SLA Aging Audit

### Workflow

1. **Fetch SLA policy**: `GET /api/sla-policy` to understand SLA deadline rules
   by category and severity.

2. **Fetch in-scope work items**: Query `/api/work-items` with team and
   category filters matching the task scope. Include open and in-progress items;
   also include closed items whose `closed_at` falls within the recent-closed
   window so recently-resolved items can be counted.

3. **Build the primary SLA population**: Remove duplicates (non-null
   `duplicate_of`). The remaining items form `included_primary_ids`. Sort
   lexicographically.

4. **Determine overdue items**: An item is overdue if:
   - Its SLA deadline is before the as-of date, AND
   - It is not closed, OR it was closed but within the recent-closed window
     (i.e. it was overdue when it closed).
   - Use `sla_deadline < as_of_date` as the primary check.

5. **Compute aging buckets**: For each overdue item, compute days overdue as
   `as_of_date - sla_deadline` in whole days. Bucket into:
   - `0-3`: 0 to 3 days
   - `4-7`: 4 to 7 days
   - `8-14`: 8 to 14 days
   - `15-30`: 15 to 30 days
   - `31+`: 31 or more days

6. **Compute team overdue counts**: Group overdue primary items by team. List
   teams alphabetically with their overdue counts.

7. **Identify the top hotspot**: Group overdue primary items by `(team, owner)`
   pairs. The pair with the highest count is the top hotspot. If owner is null,
   use `"UNASSIGNED"`. If there's a tie, pick the first alphabetically by team,
   then by owner.

8. **Build duplicate clusters**: For each primary item that has duplicates
   pointing to it, create a cluster `{primary_id, duplicate_ids: [...]}`.
   Sort clusters by `primary_id` ascending. Sort `duplicate_ids`
   lexicographically within each cluster.

9. **Identify missing-owner items**: Primary items where `owner` is null or
   empty. List their ids sorted ascending.

10. **Calculate breach rate**: `breach_rate = overdue_count /
    included_primary_count`. Round to exactly 3 decimal places.

11. **If the task asks for an escalation queue** (severity-weighted ordering):
    Sort overdue primary items by severity priority (S1 > S2 > S3 > S4), then
    by days overdue descending within each severity band. Output the ordered id
    list as `escalation_queue_ids`.

12. **If the task asks for overdue counts by severity**: Count overdue primary
    items per severity level (S1, S2, S3, S4).

## Task Family 3: Release Readiness Assessment

### Workflow

1. **Fetch the release**: `GET /api/releases/{release_id}`.

2. **Fetch milestones**: `GET /api/milestones?release_id={release_id}`.

3. **Fetch work items for the release**: Query work items by `release_id`.
   Build the primary population (exclude duplicates).

4. **Fetch blockers**: `GET /api/blockers`, filter to those on release work
   items that are unresolved and high-impact.

5. **Fetch dependencies**: `GET /api/dependencies`, filter to edges where the
   source is a release work item.

6. **Compute milestone completion**: For each milestone, count primary work
   items associated with it. `complete_primary` = items with status `Closed` or
   equivalent terminal state. `primary_total` = all primary items in the
   milestone. `completion_pct = (complete_primary / primary_total) * 100`,
   rounded to 1 decimal place. Sort milestones by `milestone_id` ascending.

7. **Identify gating work items**: Non-complete primary release work items that
   block readiness. These are items whose incomplete state prevents shipping.
   Sort ascending, no duplicates.

8. **Count blocker causes**: For unresolved high-impact blockers on release
   work items, count by exact `cause` string. Only include blockers that are
   not resolved/closed.

9. **Trace critical dependency chains**: For release work items that are blocked
   by dependencies, follow `depends_on` edges to find the non-complete item at
   the end of each chain. Build ordered paths `[blocked_work_item, ...,
   non_complete_dependency]`. Sort chains lexicographically by the full path
   string representation.

10. **Compute readiness score**: `completed_primary_work / total_primary_work`,
    rounded to 3 decimal places. Count across all milestones.

11. **Determine ship decision**:
    - `SHIP`: readiness_score = 1.0, zero gating items, zero unresolved
      high-impact blockers.
    - `SHIP_WITH_WATCH`: readiness_score >= 0.85, manageable gating items,
      no critical unresolved blockers.
    - `NO_SHIP`: readiness_score < 0.85, significant gating items, or
      unresolved high-impact blockers.

## Common Output Rules

### Sorting

- Work item id lists: lexicographically ascending (string sort)
- Team names: alphabetically ascending
- Duplicate clusters: by `primary_id` ascending; `duplicate_ids` lexicographically
- Milestones: by `milestone_id` ascending
- Dependency chains: lexicographically by the full path representation
- Gap table rows: fixed category order: NewFeature, TechDebt, Reliability, Security
- Mix table rows: same fixed category order
- Under-invested categories: most negative gap first

### Rounding

- Percentages (completion_pct, actual_pct, target_pct, gap_pct): 1 decimal place
- Rates and scores (breach_rate, readiness_score): 3 decimal places
- Use standard rounding (half-up) in all calculations

### JSON Output

- Produce exactly one JSON object or array as specified by the answer template
- No prose, explanation, or markdown outside the JSON
- Follow the answer template's key names, types, and required fields exactly
- Use `jq` to validate structure before final output

### SQL Queries

When the REST endpoints do not provide sufficient filtering, use
`POST /api/query`:

```bash
curl -s -X POST "$BASE_URL/api/query" \
  -H "Content-Type: application/json" \
  -H "X-Env-Token: portfolio-readonly" \
  -d '{"query": "SELECT ..."}'
```

The SQL schema mirrors the work item data model. Use parameterized filters in
the SQL string. Prefer REST endpoints when they support the needed filters;
fall back to SQL only when the REST API is insufficient.

## Validation Checklist

Before submitting the answer, verify:

- [ ] `environment_access.md` was read and BASE_URL / TOKEN_HEADER extracted
- [ ] All REST calls use `curl -s` with appropriate query parameters
- [ ] Duplicate items (non-null `duplicate_of`) are excluded from primary counts
- [ ] Stale mirror/legacy fields are ignored; authoritative fields used
- [ ] Cancelled items excluded from closed portfolio populations
- [ ] Category classification follows the priority chain: Security > Reliability > TechDebt > NewFeature
- [ ] Sorting follows the conventions for each list type
- [ ] Rounding follows the 1-decimal (percentages) / 3-decimal (rates) rule
- [ ] The output is a single JSON value matching the answer template schema
- [ ] No prose, markdown, or commentary appears outside the JSON
