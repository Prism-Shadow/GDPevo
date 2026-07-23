# Portfolio Engineering Environment — Reusable Skill

## Overview

This skill covers interacting with a shared portfolio-management REST API to produce:
- **Portfolio mix reviews** — classify closed work items into investment categories, compare actual mix against targets, identify gaps, and recommend rebalancing actions.
- **SLA aging audits** — identify primary SLA-eligible work, detect overdue items, compute aging distributions, surface owner/team hotspots, flag duplicate clusters, and calculate breach rates.
- **Release readiness assessments** — evaluate milestone completion, identify gating work items, count unresolved high-impact blockers, trace critical dependency chains, and compute readiness scores.

---

## Environment Connection

### Base URL

All API calls go to the base URL supplied in the task's `<TASK_ENV_BASE_URL>` placeholder (provided at runtime by `environment_access.md`). That file supplies:

```
base_url:       e.g. http://task-env:9024/
credentials:
  api_query_header: X-Env-Token
  api_query_token:  <token-value>
allowed_endpoints:
  - GET  /api/work-items
  - GET  /api/work-items/{item_id}
  - GET  /api/mix-targets
  - GET  /api/sla-policy
  - GET  /api/releases
  - GET  /api/releases/{release_id}
  - GET  /api/milestones
  - GET  /api/dependencies
  - GET  /api/blockers
  - POST /api/query
```

### Authentication

The only endpoint requiring authentication is `POST /api/query`. Send the header:

```
X-Env-Token: <api_query_token>
```

All `GET` endpoints are unauthenticated.

---

## API Reference

### GET /api/work-items

Returns all work items with pagination metadata.

**Response shape:**
```json
{
  "count": <integer>,
  "work_items": [ <work_item_object>, ... ]
}
```

### GET /api/work-items/{item_id}

Returns a single work item.

**Response shape:**
```json
{
  "work_item": { <work_item_object> }
}
```

### Work Item Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier, e.g. `WI-24024-P001` |
| `title` | string | Human-readable title |
| `work_type` | string | One of: `Feature`, `Refactor`, `Incident`, `Security`, `Reliability`, `Compliance`, `Bug`, `Dependency`, `Chore`, `Enhancement` |
| `status` | string | One of: `Closed`, `Done`, `Deployed`, `Verified`, `Review`, `In Progress`, `Backlog`, `Duplicate`, `Cancelled`, `Reopened` |
| `team` | string | Owning engineering team |
| `owner` | string or null | Person assigned; `null` means unassigned |
| `product_area` | string | Product area this work belongs to |
| `created_at` | string (date) | Creation date, format `YYYY-MM-DD` |
| `due_at` | string (date) | SLA due date, format `YYYY-MM-DD` |
| `closed_at` | string (date) or null | Close date, format `YYYY-MM-DD`; null if still open |
| `severity` | string | `S1`, `S2`, `S3`, or `S4` |
| `priority` | integer | 1 (highest) to 5 (lowest) |
| `labels` | array of strings | Free-form tags, e.g. `["security","cve","rollout"]` |
| `story_points` | integer | Effort estimate |
| `release_id` | string or null | Release this item belongs to |
| `milestone_id` | string or null | Milestone this item belongs to |
| `duplicate_of` | string or null | If status is `Duplicate`, points to the canonical/primary work item id |
| `mirror_status` | string | **STALE FIELD** — do not use as source of truth. Use `status` instead. |
| `legacy_category` | string | **STALE FIELD** — do not use for portfolio classification. Use authoritative signals instead. |

### GET /api/mix-targets

Returns all portfolio mix target rows.

**Response shape:**
```json
{
  "mix_targets": [
    {
      "scope_id": "train_001",
      "quarter": "2025-Q4",
      "team_group": "Platform Core + Identity Services",
      "product_area": "Atlas Backend + Identity",
      "new_feature_pct": 0.34,
      "tech_debt_pct": 0.24,
      "reliability_pct": 0.22,
      "security_pct": 0.20
    }
  ]
}
```

Target percentages are expressed as decimals (0.34 = 34%). When presenting results, convert to percentage points (multiply by 100) and round to 1 decimal place.

### GET /api/sla-policy

Returns SLA due-date rules keyed by severity.

**Response shape:**
```json
{
  "sla_policy": [
    { "severity": "S1", "days_to_due": 3 },
    { "severity": "S2", "days_to_due": 10 },
    { "severity": "S3", "days_to_due": 21 },
    { "severity": "S4", "days_to_due": 45 }
  ]
}
```

An item is **overdue** when `as_of_date - created_at > days_to_due` for its severity AND the item is not closed (or was closed after the as-of date, or was closed recently within the `recent_closed_window_days` window — see SLA methodology below).

### GET /api/releases

Returns all releases.

**Response shape:**
```json
{
  "releases": [
    {
      "id": "REL-ORION-2026-02",
      "name": "Orion February portfolio train",
      "target_date": "2026-02-20",
      "train": "Orion"
    }
  ]
}
```

### GET /api/releases/{release_id}

Returns a single release with its embedded milestones and blockers.

**Response shape:**
```json
{
  "release": { <release_object> },
  "milestones": [ <milestone_object>, ... ],
  "blockers": [ <blocker_object>, ... ]
}
```

### GET /api/milestones

Returns all milestones across all releases.

**Response shape:**
```json
{
  "milestones": [
    {
      "id": "MIL-ORION-BETA",
      "name": "Orion beta freeze",
      "owner_team": "Release Engineering",
      "release_id": "REL-ORION-2026-02"
    }
  ]
}
```

### GET /api/dependencies

Returns all dependency edges between work items.

**Response shape:**
```json
{
  "dependencies": [
    {
      "blocked_id": "WI-24024-010",
      "depends_on_id": "WI-24024-009",
      "relation": "blocks-release-readiness"
    }
  ]
}
```

Relation types include: `depends-on`, `blocks-release-readiness`, `security-review-required`, `validation-required`, `implementation-dependency`, `audit-evidence-required`.

### GET /api/blockers

Returns all blocker records.

**Response shape:**
```json
{
  "blockers": [
    {
      "id": "BLK-24024-001",
      "work_item_id": "WI-24024-010",
      "release_id": "REL-ORION-2026-02",
      "cause": "open reliability rehearsal gap",
      "severity": "High",
      "status": "Open",
      "opened_at": "2026-02-06",
      "resolved_at": null
    }
  ]
}
```

Blocker severities: `Critical`, `High`, `Medium`, `Low`.  
Blocker statuses: `Open`, `Monitoring`, `Resolved`.

### POST /api/query

Run SQL queries against the work items data. Requires the auth header.

**Request:**
```json
{
  "sql": "SELECT id, status, team FROM work_items WHERE team = 'AppSec'"
}
```

**Response shape:**
```json
{
  "columns": ["id", "status", "team"],
  "rows": [ [...], ... ],
  "row_count": <integer>,
  "truncated": false
}
```

The table name is `work_items`. Available columns match the work item object fields listed above. Use this endpoint for filtered queries that would be inefficient via the GET list endpoint.

**Querying tip:** The JSON label array is stored as a JSON string in the SQL backend. Use `LIKE '%"security"%'` patterns to filter by label value.

---

## Portfolio Category Classification

Every included work item must be classified into exactly one of four portfolio categories:

| Category | Code |
|----------|------|
| New Feature | `NewFeature` |
| Technical Debt | `TechDebt` |
| Reliability | `Reliability` |
| Security | `Security` |

### Signal Sources (in priority order)

1. **Labels array** — the strongest signal. Each label token maps to a category convention.
2. **Work type** — the second signal. Used as default when labels are ambiguous or silent.
3. **Title** — can disambiguate when labels and work_type conflict (e.g., a title noting a label is "stale").

### Classification Methodology

When classifying a work item:

1. **Extract all signals** from labels, work_type, and title.
2. **Resolve conflicts** using the portfolio category conventions. When multiple categories are signaled by labels, the one with the strongest signal wins. When labels give no clear category signal, fall back to work_type. When work_type is also ambiguous, inspect the title.
3. **Every item gets exactly one category.** No item is double-counted or left unclassified.
4. **Verify your counts** against the target mix. If the target says 34% NewFeature and you have 0%, re-examine your classification of items whose work_type is `Feature` or `Enhancement` but whose labels push them elsewhere.

Common label-to-category associations visible in the training data:
- Labels containing `security` or `cve` → Security
- Labels containing `reliability`, `incident`, `outage`, or `latency` → Reliability
- Labels containing `refactor`, `cleanup`, or `migration` → TechDebt
- Labels containing `feature` → NewFeature (when no higher-priority signal exists)
- Labels like `auth`, `encryption`, `rollout`, `flaky` appear across categories — resolve by priority and adjacent signals.

---

## Task Type 1: Portfolio Mix Review

### Purpose
Compare the count-based distribution of closed work items across the four portfolio categories against a target mix, identify under-invested categories, and recommend a follow-up action.

### Step-by-Step Method

1. **Fetch the mix target.** Query `/api/mix-targets` and locate the row whose `scope_id` matches the task's scope. Convert the decimal target percentages to percentage points (multiply by 100, round to 1 decimal).

2. **Identify in-scope work items.** Use `/api/work-items` or `POST /api/query` to find items matching the scope's teams AND product areas. Filter to the correct quarter (closed_at within the quarter).

3. **Separate primary from excluded records:**
   - **Duplicates:** Items with `status = "Duplicate"` and a non-null `duplicate_of` field. Exclude from the portfolio count. Track their ids.
   - **Cancelled:** Items with `status = "Cancelled"`. Exclude from the portfolio count. Track their ids.
   - **Distractors:** Items that match scope on teams/product_area/quarter but have a `duplicate_of` pointing to an item in a different scope, or items whose `mirror_status` contradicts `status`. Exclude these and track their ids.

4. **Classify each included item** into one of the four categories using the classification methodology above.

5. **Compute counts and percentages:**
   - `category_counts`: integer count per category.
   - `category_percentages`: `(count / total_included) * 100`, rounded to 1 decimal place.

6. **Build the gap table.** For each category (ordered: NewFeature, TechDebt, Reliability, Security):
   - `target_pct`: from the mix target row (as percentage points, 1 decimal).
   - `actual_pct`: from step 5.
   - `gap_pct`: `actual_pct - target_pct`, rounded to 1 decimal.

7. **Identify under-invested categories.** Categories where `gap_pct < 0`. Sort from most negative to least negative gap.

8. **Determine the follow-up action:**
   - If any under-invested categories exist → `REBALANCE_CAPACITY`, primary = category with largest negative gap, secondary = next largest, rationale = `LARGEST_NEGATIVE_GAP`.
   - If no under-invested categories → `MAINTAIN_CURRENT_MIX`, primary and secondary = null, rationale = `NO_NEGATIVE_GAPS`.
   - If data conflicts are found (e.g., mirror_status contradicting status across multiple records) → `INVESTIGATE_DATA_QUALITY`, rationale = `DATA_CONFLICT`.

9. **Populate exclusion flags:**
   - `excluded_duplicate_ids`: sorted list of duplicate record ids.
   - `excluded_cancelled_ids`: sorted list of cancelled record ids.
   - `ignored_mirror_status_and_legacy_category`: always `true`.

10. **Verify.** Confirm `sum(category_counts) == total_included`. Confirm percentages sum to approximately 100.0% (may be 99.9 or 100.1 due to rounding). Confirm gap_pct values: `sum(gap_pct)` should be approximately 0.0.

### Ordering Conventions
- Work item IDs in `included_work_item_ids`: sort by `closed_at` ascending, then by `id` ascending.
- Exclusion IDs: sort by `closed_at` ascending, then by `id` ascending.
- Teams and product areas in scope: sort alphabetically.
- Gap table rows: NewFeature, TechDebt, Reliability, Security (fixed order).
- Under-invested categories: most negative gap first.

---

## Task Type 2: SLA Aging Audit

### Purpose
Audit SLA compliance for reliability and security work items, identifying overdue items, aging distributions, team/owner hotspots, duplicate clusters, and breach rates.

### Step-by-Step Method

1. **Fetch SLA policy.** `GET /api/sla-policy` — maps severity to `days_to_due`.

2. **Identify the SLA-eligible population.** Query work items where:
   - `team` matches the scope's teams.
   - The item belongs to the SLA-relevant categories (e.g., Reliability, Security). Use the portfolio category classification to determine category.
   - Exclude items with `status = "Duplicate"` or `status = "Cancelled"`.

3. **Separate primary from duplicate records:**
   - Primary: items where `duplicate_of` is null (or status is not Duplicate).
   - Duplicate clusters: group items where `duplicate_of` points to a primary id, or where `status = "Duplicate"`. Each cluster has one `primary_id` (the canonical item) and a list of `duplicate_ids`.
   - The `included_primary_ids` list contains only primary records.

4. **Determine overdue status.** For each primary item:
   - Compute age: `as_of_date - created_at` in days.
   - Look up `days_to_due` from SLA policy by the item's severity.
   - An item is **overdue** if `age > days_to_due` AND the item is not already closed. However, items closed within the `recent_closed_window_days` of the as-of date should be treated as **still open** for SLA purposes (they were recently resolved and count toward the active SLA population). Items closed before the recent window are considered closed and not overdue.
   - **Key distinction:** Use `status` (not `mirror_status`) to determine if an item is closed. A closed/completed status (`Closed`, `Done`, `Deployed`, `Verified`) with a `closed_at` date before `as_of_date - recent_closed_window_days` means the item is genuinely closed and not overdue.

5. **Populate `overdue_primary_ids`.** Subset of `included_primary_ids` that are overdue. Sort lexicographically.

6. **Compute aging buckets.** For each included primary item, compute age in days (from `created_at` to `as_of_date`). Count into buckets: `0-3`, `4-7`, `8-14`, `15-30`, `31+`. Include ALL primary items, not just overdue ones.

7. **Compute team overdue counts.** For each team (alphabetical order), count overdue primary items assigned to that team.

8. **Find the top hotspot.** The (team, owner) pair with the most overdue primary items. When owner is null/absent, use `UNASSIGNED`. If multiple pairs tie, pick the first alphabetically by team, then by owner.

9. **Identify duplicate clusters.** Group duplicate records by their `primary_id` (the `duplicate_of` value). Each cluster has a `primary_id` and sorted `duplicate_ids`. Sort clusters by `primary_id`.

10. **Identify missing-owner items.** Primary included items where `owner` is null. Sort ids lexicographically.

11. **Calculate breach rate.** `overdue_primary_ids.length / included_primary_ids.length`. Round to exactly 3 decimal places.

### Ordering Conventions
- All ID lists: sorted lexicographically (ascending).
- Teams in `team_overdue_counts`: sorted alphabetically.
- Duplicate clusters: sorted by `primary_id`. Within each cluster, `duplicate_ids` sorted lexicographically.
- `breach_rate`: 3 decimal places.

### Escalation Queue (when required)
When the answer template includes an escalation queue, order overdue primary items by:
1. Severity (S1 first, then S2, S3, S4).
2. Within the same severity, by age descending (oldest first).
3. Within same age, by id ascending.

---

## Task Type 3: Release Readiness Assessment

### Purpose
Evaluate whether a release is ready to ship by assessing milestone completion, gating work items, blocker counts, and dependency chains.

### Step-by-Step Method

1. **Fetch release data.** `GET /api/releases/{release_id}` returns the release object, its milestones array, and its blockers array.

2. **Identify release work items.** Query work items where `release_id` matches the target release. These are the primary work items for the release.

3. **For each milestone, compute completion:**
   - `primary_total`: count of primary release work items assigned to this milestone (`milestone_id` matches).
   - `complete_primary`: subset of those where status indicates completion. Completed statuses are: `Closed`, `Done`, `Deployed`, `Verified`. Items with status `Duplicate`, `Cancelled`, `In Progress`, `Backlog`, `Review`, `Reopened` are NOT complete.
   - `completion_pct`: `(complete_primary / primary_total) * 100`, rounded to 1 decimal place. If `primary_total == 0`, `completion_pct = 0.0`.
   - Sort `milestone_completion` by `milestone_id` ascending.

4. **Identify gating work items.** Primary release work items that are NOT complete. These gate the release readiness. Exclude duplicates and cancelled items. Sort ids ascending, no duplicates.

5. **Count unresolved high-impact blockers.** From the release's blockers, filter to:
   - `severity` is `High` or `Critical`.
   - `status` is NOT `Resolved` (i.e., `Open` or `Monitoring`).
   - Count by exact `cause` string. Use the cause text verbatim as the key.

6. **Trace critical dependency chains.** Use `GET /api/dependencies` to find chains where:
   - The `blocked_id` is a release work item (gating or otherwise).
   - Follow `depends_on_id` links until reaching a non-complete dependency or a terminal item.
   - A chain is "critical" if it blocks a release work item and the dependency at the end is not complete.
   - Each chain is an ordered array of work item ids: `[release_work_item, ..., non_complete_dependency]`.
   - Sort chains lexicographically by the full path (join with a delimiter, sort, then split back).

7. **Compute readiness score.** `total_complete_primary / total_primary_release_items`, rounded to 3 decimal places. Count only primary items (exclude duplicates and cancelled).

8. **Determine ship decision:**
   - `SHIP`: readiness_score >= 0.95 AND no gating work items AND no unresolved Critical/High blockers.
   - `SHIP_WITH_WATCH`: readiness_score >= 0.80 AND ≤ 3 gating items AND no Critical unresolved blockers.
   - `NO_SHIP`: anything below SHIP_WITH_WATCH thresholds, OR any Critical unresolved blocker, OR any incomplete milestone where completion_pct < 50.0.

### Ordering and Precision
- `milestone_completion`: sorted by `milestone_id` ascending.
- `gating_work_item_ids`: sorted ascending, no duplicates.
- `blocker_cause_counts`: keys are exact cause strings (verbatim from the API).
- `critical_dependency_chains`: sorted lexicographically by the string representation of the full path array.
- `completion_pct`: 1 decimal place.
- `readiness_score`: 3 decimal places.

---

## Cross-Cutting Conventions

### Stale Field Handling

Two fields in work items are **not authoritative** and must be ignored for decision-making:

1. **`mirror_status`** — This is a stale export/sync field that may not reflect the true current status. Always use `status` instead.
2. **`legacy_category`** — This is a deprecated classification. Always use the portfolio category classification methodology (labels + work_type + title) instead.

When an answer template includes `ignored_mirror_status_and_legacy_category`, set it to `true` to confirm you disregarded these fields.

### Primary vs. Duplicate Records

- A work item is a **duplicate** when `status = "Duplicate"` and `duplicate_of` is non-null.
- A work item is **primary** when it is not a duplicate and not cancelled.
- Duplicate items should never be counted in portfolio mixes, SLA populations, or release metrics. Track them separately in exclusion/cluster lists.
- Some items may have `status = "Closed"` (or other non-Duplicate status) but still have a non-null `duplicate_of` — treat these as distractors/duplicates and exclude them.

### Date Handling

- All dates are in `YYYY-MM-DD` format.
- Compute day differences using Python's `datetime` module: `(date2 - date1).days`.
- Quarter filtering: `closed_at` must fall within the quarter's date range (e.g., 2025-Q4 = 2025-10-01 through 2025-12-31).

### Rounding Rules

| Metric | Precision |
|--------|-----------|
| Portfolio percentages (actual, target, gap) | 1 decimal place |
| Milestone completion_pct | 1 decimal place |
| Breach rate | 3 decimal places |
| Readiness score | 3 decimal places |

Use standard rounding (round half up). In Python: `round(value, decimals)`.

### Sort Orderings

| List | Order |
|------|-------|
| Work item IDs (general) | Lexicographic ascending (standard string sort) |
| Work item IDs (by close date) | `closed_at` ascending, then `id` ascending |
| Teams | Alphabetical ascending |
| Product areas | Alphabetical ascending |
| Gap table / mix table rows | Fixed order: NewFeature, TechDebt, Reliability, Security |
| Under-invested categories | Most negative gap to least negative gap |
| Duplicate clusters | By `primary_id` ascending |
| Duplicate ids within cluster | Lexicographic ascending |
| Milestone completion | By `milestone_id` ascending |
| Escalation queue | Severity (S1→S4), then age descending, then id ascending |

---

## Common Pitfalls

1. **Trusting `mirror_status` over `status`.** Always use `status` as the authoritative field. The mirror_status field is deliberately stale in the data.

2. **Using `legacy_category` for classification.** It does not follow the portfolio category conventions. Always classify from labels, work_type, and title.

3. **Including duplicate or cancelled items in counts.** These must be tracked separately and excluded from all primary metrics.

4. **Double-counting items that appear in multiple queries.** Deduplicate by `id`.

5. **Misclassifying Feature/Enhancement work_type items.** Not all `Feature` items are `NewFeature` — labels can override this. The same applies to `Enhancement` items.

6. **Using the wrong denominator.** Portfolio percentages use count of included items (not story points). Readiness score uses primary release items only.

7. **Incorrect SLA overdue logic.** Items closed very recently (within the recent window) still count as active for SLA purposes. Use `status` and `closed_at` together to determine if an item is truly closed.

8. **Forgetting to sort.** Every list field has a required sort order. Applying the wrong sort will cause validation failures.

9. **Not fetching all data before computing.** Some relationships (dependencies, blockers, duplicate_of chains) require joining data across multiple endpoints. Fetch all relevant data first, then compute.

---

## Tools and Commands Cheat Sheet

```bash
# Fetch all work items
curl -s http://task-env:9024/api/work-items

# Fetch single work item
curl -s http://task-env:9024/api/work-items/WI-24024-P001

# Fetch mix targets
curl -s http://task-env:9024/api/mix-targets

# Fetch SLA policy
curl -s http://task-env:9024/api/sla-policy

# Fetch all releases
curl -s http://task-env:9024/api/releases

# Fetch single release with milestones and blockers
curl -s http://task-env:9024/api/releases/REL-ORION-2026-02

# Fetch all milestones
curl -s http://task-env:9024/api/milestones

# Fetch all dependencies
curl -s http://task-env:9024/api/dependencies

# Fetch all blockers
curl -s http://task-env:9024/api/blockers

# SQL query (requires auth header)
curl -s -X POST http://task-env:9024/api/query \
  -H 'X-Env-Token: <token>' \
  -H 'Content-Type: application/json' \
  -d '{"sql": "SELECT id, status, team FROM work_items WHERE team = '\''Platform Core'\''"}'

# Filter by quarter via SQL
curl -s -X POST http://task-env:9024/api/query \
  -H 'X-Env-Token: <token>' \
  -H 'Content-Type: application/json' \
  -d '{"sql": "SELECT * FROM work_items WHERE closed_at >= '\''2025-10-01'\'' AND closed_at <= '\''2025-12-31'\''"}'

# Filter by label substring via SQL
curl -s -X POST http://task-env:9024/api/query \
  -H 'X-Env-Token: <token>' \
  -H 'Content-Type: application/json' \
  -d '{"sql": "SELECT * FROM work_items WHERE labels LIKE '\''%\"security\"%'\''"}'
```

---

## Output Format

All tasks require a **single JSON object** as output with no prose outside the JSON. Follow the answer template schema provided in the task's `input/payloads/answer_template.json` exactly. Every required field must be present. Every `const` value in the schema must match. Enum values must be selected from the allowed set. Array ordering must follow the conventions documented above.
