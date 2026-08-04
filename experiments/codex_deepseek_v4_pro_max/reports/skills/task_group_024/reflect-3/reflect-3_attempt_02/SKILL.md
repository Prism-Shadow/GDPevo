## When to Use

Use this skill when working with a read-only portfolio-management HTTP API that exposes work items, mix targets, SLA policies, releases, milestones, blockers, and dependencies through REST endpoints and a SQL query endpoint. Typical tasks include portfolio-mix readouts, SLA aging audits, and release-readiness assessments.

## Environment Assumptions

- A base URL is supplied in the task prompt or an `environment_access.md` file.
- The API supports `GET /api/{resource}` list endpoints and `GET /api/{resource}/{id}` detail endpoints.
- A `POST /api/query` endpoint accepts JSON `{"sql": "...", "params": [...]}` with header `X-Env-Token` whose value is supplied in the access notes. Only `SELECT` and `WITH` statements are allowed.
- Responses are JSON arrays or objects. List endpoints typically return a wrapper with a `count` and a resource-keyed array (e.g., `{"count": N, "work_items": [...]}`).
- At most 1000 rows are returned per query.

## Core Data Model

### Work Item Fields

Every work item has these fields. Always use the **authoritative** fields: `status`, `work_type`, `labels`, `duplicate_of`, `closed_at`, `due_at`. Treat `mirror_status` and `legacy_category` as stale and ignore them for classification and status decisions.

| Field | Description |
|---|---|
| `id` | Unique identifier (e.g., `WI-24024-001`). |
| `status` | Authoritative status: `Closed`, `Done`, `Verified`, `Deployed`, `In Progress`, `Review`, `Backlog`, `Reopened`, `Duplicate`, `Cancelled`. Items with `status IN ('Duplicate','Cancelled')` are never counted as primary portfolio work. |
| `team` | Owning engineering team. |
| `product_area` | Product area (e.g., `Atlas Backend`, `Identity`, `Checkout`). |
| `work_type` | Primary type signal: `Feature`, `Enhancement`, `Security`, `Reliability`, `Refactor`, `Chore`, `Dependency`, `Incident`, `Bug`, `Compliance`, etc. |
| `labels` | JSON array of strings. |
| `severity` | `S1` through `S4`. |
| `owner` | Owner name or `null` when missing. |
| `duplicate_of` | When set, this item is a duplicate of another work item. Exclude it from primary populations. |
| `closed_at` | ISO-8601 date (or `null`). |
| `due_at` | ISO-8601 date (or `null`). |
| `milestone_id` | Associated milestone, if any. |
| `release_id` | Associated release, if any. |
| `mirror_status` | Stale mirror field — ignore. |
| `legacy_category` | Stale legacy field — ignore. |
| `title` | Free-text title; can contain domain hints (e.g., "stale security label", "stale-export"). |

### Portfolio Categories

Every work item belongs to exactly one of these four portfolio categories: `NewFeature`, `TechDebt`, `Reliability`, `Security`.

**Classification rules (apply in order, first match wins):**

1. If `work_type` is `Security` → `Security`.
2. If `work_type` is `Reliability` → `Reliability`.
3. If `work_type` is `Feature` or `Enhancement` → `NewFeature`, unless labels contain a definitive override:
   - Labels containing `reliability` or `outage` override to `Reliability`.
   - Labels containing `security` override to `Security`.
4. If `work_type` is `Refactor`, `Chore`, or `Dependency` → `TechDebt`, unless labels contain:
   - `reliability` → `Reliability`.
   - `security` or `cve` → `Security`.
5. If `work_type` is `Incident` or `Bug` → classify from labels:
   - Labels containing `reliability` or `outage` → `Reliability`.
   - Labels containing `security` or `cve` → `Security`.
   - Labels containing `feature` → `NewFeature`.
   - Otherwise → `TechDebt`.
6. If `work_type` is `Compliance` → classify from labels:
   - Labels containing `security` → `Security`.
   - Otherwise → `TechDebt`.
7. If `work_type` is `Enhancement` and labels contain `reliability` or `outage` → `Reliability`.
8. Any remaining items → `TechDebt`.

**Special signals in titles:**
- If the title contains "stale security label" or similar, the `security` label is stale and should be ignored in favour of the primary `work_type`.
- If the title contains "stale-export" in labels, the duplicate/reliability signals may be stale.

### Duplicates and Cancelled Items

- Items with `status = 'Duplicate'` are always excluded from primary populations.
- Items with `duplicate_of` set to a non-null value are duplicates and must be excluded from primary populations, even if their `status` is not `Duplicate`.
- Items with `status = 'Cancelled'` are always excluded.
- Duplicate clusters should be reported separately: a cluster is a `primary_id` (the item pointed to by `duplicate_of`) and a list of `duplicate_ids` pointing to it.
- When building duplicate clusters for a scope, include any cluster where the duplicate item belongs to one of the scoped teams.

### SLA Policy

The `/api/sla-policy` endpoint returns an array with `severity` and `days_to_due`:

| Severity | Default days to due |
|---|---|
| S1 | 3 |
| S2 | 10 |
| S3 | 21 |
| S4 | 45 |

## Task Recipe: Portfolio Mix Readout

**When to use:** The task asks for a quarterly "closed-work portfolio mix" comparing actual category counts against target percentages.

**Steps:**

1. Read the `scope_id`, `quarter`, `teams`, and `product_areas` from the prompt.
2. Fetch the target mix: `GET /api/mix-targets`, find the row where `scope_id` matches. The target percentages are fractions (e.g., `0.34` means 34%). When filling answer templates that use "percentage points", multiply by 100 and round to one decimal place.
3. Query work items with `SQL`:
   - Filter by `team IN (...)` and `product_area IN (...)`.
   - For Q4: `closed_at >= '{year}-10-01' AND closed_at < '{year+1}-01-01'`.
4. Exclude items with `status IN ('Duplicate','Cancelled')` or `duplicate_of IS NOT NULL`.
5. Classify each remaining item into exactly one portfolio category using the rules above.
6. Compute counts per category. Compute actual percentages as `count / total * 100`, rounded to one decimal place.
7. Build a gap table: `gap_pct = actual_pct - target_pct`.
8. Under-invested categories: those with negative `gap_pct`, ordered from most negative to least negative. When gaps are equal, prefer the category that appears first in the canonical order: NewFeature, TechDebt, Reliability, Security — but check scoring feedback for tie-breaking.
9. Follow-up action: use `REBALANCE_CAPACITY` with `primary_category` set to the most under-invested category. Rationale code: `LARGEST_NEGATIVE_GAP`.
10. Exclusion flags: list `excluded_duplicate_ids`, `excluded_cancelled_ids`, and set `ignored_mirror_status_and_legacy_category: true`.

## Task Recipe: SLA Aging Audit

**When to use:** The task asks for SLA aging analysis — overdue work items, aging buckets, breach rate.

**Steps:**

1. Read `teams`, `as_of` date, `recent_closed_window_days`, and SLA-relevant `categories` from the prompt.
2. Fetch SLA policy: `GET /api/sla-policy`.
3. Query all work items for the scoped teams (exclude `Duplicate` and `Cancelled` statuses).
4. Classify each item into a portfolio category. Keep only items whose category is in the SLA-relevant `categories`.
5. Determine the primary population:
   - Include items that are **open** (no `closed_at`, or `closed_at` is after `as_of`).
   - Also include items **recently closed** (`closed_at >= as_of - recent_closed_window_days` AND `closed_at <= as_of`).
   - Exclude items closed before the recent window.
6. Identify overdue items: `due_at < as_of` AND the item was not closed before its due date.
   - For open items: `due_at < as_of` → overdue.
   - For closed items: `due_at < as_of` AND `closed_at > due_at` → overdue (breached SLA before closing).
7. Compute aging buckets: days past due = `as_of - due_at`. Bucket into: 0-3, 4-7, 8-14, 15-30, 31+.
8. Team overdue counts: group overdue items by team, alphabetically.
9. Top hotspot: the `(team, owner)` pair with the most overdue items. Treat `null` owner as `UNASSIGNED`. If tied, prefer the team that comes first alphabetically.
10. Duplicate clusters: find all items in the scoped teams with `status = 'Duplicate'` or `duplicate_of IS NOT NULL`. Report clusters sorted by `primary_id`.
11. Missing owners: primary items where `owner IS NULL`, sorted.
12. Breach rate: `overdue_count / primary_count`, rounded to exactly three decimal places.
13. Escalation queue (for tasks that require one): list overdue primary IDs in priority order — typically highest severity first (S1 before S2), then by days past due descending.

## Task Recipe: Release Readiness Assessment

**When to use:** The task asks for a ship/no-ship decision for a specific release.

**Steps:**

1. Read the `release_id` from the prompt.
2. Fetch release details: `GET /api/releases/{release_id}`.
3. Fetch milestones: `GET /api/milestones`, filter by `release_id`.
4. Fetch blockers: `GET /api/blockers` (or query), filter by `release_id`.
5. Fetch dependencies: `GET /api/dependencies`.
6. Query work items for the release (`WHERE release_id = ...`). Exclude `status = 'Duplicate'` from primary counts.
7. Milestone completion: for each milestone (sorted by `milestone_id` ascending):
   - `complete_primary`: count of items where `status IN ('Done','Verified','Deployed','Closed')`.
   - `primary_total`: count of non-duplicate items for that milestone.
   - `completion_pct`: `complete_primary / primary_total * 100`, rounded to one decimal place.
8. Gating work item IDs: non-complete release items, sorted ascending, no duplicates.
9. Blocker cause counts: count unresolved blockers with `severity IN ('Critical','High')` and `resolved_at IS NULL`, grouped by exact `cause` string.
10. Critical dependency chains:
    - Build a directed graph from the dependencies endpoint.
    - For each non-complete release work item, follow `blocks-release-readiness` and `depends-on` edges.
    - A chain is critical if the dependency at the end is not complete (`status NOT IN ('Done','Verified','Deployed','Closed')`).
    - Report each chain as an ordered array `[blocked_item, ..., non_complete_dependency]`.
    - Sort chains lexicographically by the full path.
11. Readiness score: `completed_primary / total_primary`, rounded to three decimal places .
12. Ship decision:
    - `NO_SHIP` if there are unresolved Critical or High blockers.
    - `SHIP_WITH_WATCH` if there are gating items or Medium blockers.
    - `SHIP` otherwise.

## Data Quality Signals

- **"stale-export" in labels:** The item's labels or duplicate_of may be stale. Prefer `status` and `work_type` for classification. In portfolio mix tasks, these are typically excluded if they have `duplicate_of` set.
- **"stale security label" in title:** The `security` label is misleading; trust `work_type` instead.
- **mirror_status vs status:** Always use `status` (authoritative). `mirror_status` is a stale mirror.
- **legacy_category:** Ignore; use `work_type` and `labels` for portfolio classification.

## Answer Construction Rules

- Always match the answer template schema exactly. Required fields are mandatory.
- Sort ID lists as specified: typically lexicographically/ascending.
- Sort team lists alphabetically.
- Round percentages to the specified precision (usually 1 decimal place for percentages, 3 decimal places for rates/scores).
- Do not include prose outside JSON answers.
- When a template field is a `const`, use the exact value shown.

## Query Patterns

### Filtering work items by quarter
```sql
SELECT ... FROM work_items
WHERE closed_at >= '2025-10-01' AND closed_at < '2026-01-01'
  AND team IN ('Platform Core','Identity Services')
  AND product_area IN ('Atlas Backend','Identity')
  AND status NOT IN ('Duplicate','Cancelled')
ORDER BY closed_at, id
```

### Finding items for SLA scope
```sql
SELECT ... FROM work_items
WHERE team IN ('Infra Reliability','Data Platform')
  AND status NOT IN ('Duplicate','Cancelled')
ORDER BY team, id
```

### Finding items for a release
```sql
SELECT ... FROM work_items
WHERE release_id = 'REL-ORION-2026-02'
  AND status != 'Duplicate'
ORDER BY id
```

### Checking specific dependencies
```sql
SELECT id, status, work_type FROM work_items
WHERE id IN ('WI-24024-094','WI-24024-053','WI-24024-112')
ORDER BY id
```

## Common Pitfalls

- **Counting duplicates as primary:** Always check both `status = 'Duplicate'` AND `duplicate_of IS NOT NULL`.
- **Trusting mirror_status:** Use `status`, ignore `mirror_status`.
- **Using legacy_category for classification:** Use `work_type` and `labels` instead.
- **Missing recently-closed items in SLA primary:** Include items closed within the `recent_closed_window_days` window, not just open items.
- **Wrong quarter boundaries:** Q4 = October through December inclusive.
- **Overdue calculation:** An item is overdue if `due_at < as_of` AND it was not resolved (`closed_at` is null or `closed_at > due_at`).
- **Escalation ordering:** Prioritize by severity (S1 first), then by days past due descending.
