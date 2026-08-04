## Portfolio Engineering Analysis

This skill covers querying and analyzing a portfolio engineering environment via REST APIs and a restricted SQL endpoint. It supports portfolio-mix reviews, SLA aging audits, and release-readiness assessments.

### Environment access

The environment exposes REST endpoints at a base URL provided in the task prompt. Available endpoints typically include:

- `GET /api/work-items` and `GET /api/work-items/{id}` — full work-item catalogue
- `GET /api/mix-targets` — target portfolio mix percentages per scope
- `GET /api/sla-policy` — severity-to-days SLA policy
- `GET /api/releases` and `GET /api/releases/{id}` — release metadata including blockers and milestones
- `GET /api/milestones` — milestone definitions
- `GET /api/dependencies` — directed dependency edges between work items
- `GET /api/blockers` — blocker records attached to work items
- `POST /api/query` — restricted SQL (`SELECT` / `WITH` only, max 1000 rows)

Use the SQL endpoint for filtering, sorting, and joining. The `POST /api/query` endpoint requires header `X-Env-Token: portfolio-readonly` and a JSON body `{"sql": "...", "params": [...]}`. Explore column names with `SELECT * FROM work_items LIMIT 1` before writing targeted queries.

### Work-item data model

Key columns in `work_items`:

| Column | Meaning |
|---|---|
| `id` | Unique identifier (e.g. `WI-24024-001`) |
| `title` | Human-readable title |
| `work_type` | Type classification (Feature, Security, Reliability, Incident, Refactor, Enhancement, Chore, Bug, Dependency, Compliance) |
| `status` | Current lifecycle state (Review, In Progress, Backlog, Done, Verified, Deployed, Closed, Cancelled, Duplicate, Reopened) |
| `team` | Owning team |
| `owner` | Person responsible; may be null |
| `product_area` | Product area |
| `created_at` / `due_at` / `closed_at` | ISO-8601 date strings; `closed_at` is null while open |
| `severity` | S1–S4 severity |
| `priority` | Integer 1–5 (1 is highest) |
| `labels` | JSON array of string tags |
| `story_points` | Integer estimate |
| `release_id` / `milestone_id` | Foreign keys |
| `duplicate_of` | ID of the canonical record when this item is a duplicate |
| `mirror_status` | Stale/exported status — **do not use for authoritative state** |
| `legacy_category` | Deprecated category field — **do not use for portfolio classification** |

### Authoritative vs stale fields

Always use the authoritative fields (`status`, `work_type`, `title`, `labels`) for classification and filtering. Ignore `mirror_status` and `legacy_category`. The `mirror_status` field may contain stale values like "Closed" for in-progress items, and `legacy_category` may conflict with the actual portfolio convention.

### Portfolio category classification

Every work item in a portfolio-mix task must be assigned to exactly one of four categories: **NewFeature**, **TechDebt**, **Reliability**, **Security**. Use this priority order to resolve conflicting signals from `work_type`, `labels`, and `title`:

1. **Security**: `work_type` is `Security`, OR labels contain `security`/`cve`/`encryption` and `work_type` is not explicitly `Feature`/`Enhancement` with a title that marks the security signal as stale.
2. **Reliability**: `work_type` is `Reliability` or `Incident`, OR labels contain `reliability`/`outage`/`latency` without a stronger Security signal and without a title override.
3. **NewFeature**: `work_type` is `Feature` or `Enhancement`, provided no higher-priority Security or Reliability signal applies.
4. **TechDebt**: `work_type` is `Refactor`, `Chore`, `Bug`, `Dependency`, or `Compliance`, provided no higher-priority signal applies. `Enhancement` items whose title starts with "Cleanup" or whose labels are dominated by `cleanup`/`refactor`/`migration` may also fall here.

When a `work_type` of `Compliance` appears, check labels: if they contain `security`-themed tags, classify as Security; otherwise treat as TechDebt.

**Title override**: If the title explicitly declares a label stale ("stale security label", "stale export"), ignore that label's signal and fall back to `work_type`.

### Duplicates, cancellations, and distractor records

- **Duplicates**: Any item with `status = 'Duplicate'` or `duplicate_of IS NOT NULL` must be excluded from primary counts. A `Closed` item that nonetheless has a non-null `duplicate_of` is still a duplicate and must be excluded.
- **Cancelled**: Items with `status = 'Cancelled'` must be excluded from primary counts.
- **Distractors** (portfolio-mix tasks): Same-scope records that match the team/product-area/quarter filters but must not count as primary closed work. This includes duplicates and cancelled items within the quarter window, plus items whose `mirror_status` implies completion while `status` is still open (stale mirror traps).

Duplicate clusters (SLA / release tasks) are formed by grouping each set of `duplicate_ids` under their `primary_id` (the value of `duplicate_of`). Sort clusters by `primary_id` ascending and `duplicate_ids` within each cluster ascending.

### Quarter and date-window filtering

For Q4 2025, the window is **2025-10-01 through 2025-12-31**. Filter with `closed_at >= '2025-10-01' AND closed_at <= '2025-12-31'` when the task calls for "closed-work" review.

For SLA aging with an as-of date, include items where `created_at <= <as_of>` and neither cancelled nor duplicate. Do not include items created after the as-of date.

The "recent closed window" (e.g. 14 or 21 days) is the number of days before the as-of date. Items closed within this window may affect breach-rate calculations differently than older closures.

### Portfolio-mix computation

1. Query the `mix_targets` row matching the task's `scope_id` for `new_feature_pct`, `tech_debt_pct`, `reliability_pct`, `security_pct`. These sum to 1.0.
2. Filter in-scope work items (team, product_area, quarter window), exclude duplicates and cancelled, and classify each included item into one of the four categories.
3. Count items per category. Compute actual percentages as `(count / total) * 100`, rounded to 1 decimal place.
4. Compute gaps as `actual_pct - target_pct` (in percentage points), rounded to 1 decimal place.
5. Under-invested categories are those with negative gap, ordered from most negative to least negative.
6. The recommended action `REBALANCE_CAPACITY` targets the category with the largest negative gap. Use `LARGEST_NEGATIVE_GAP` as the rationale code. Set `secondary_category` to the second most-negative category, or `null` if only one is under-invested.

### SLA aging and breach rate

1. Identify the primary SLA population: all in-scope work items (teams and categories) created on or before the as-of date, excluding duplicates.
2. An item is **overdue** if `due_at < <as_of>` AND it is not resolved by the as-of date (`closed_at IS NULL` or `closed_at > <as_of>`). Items resolved after their due date but before the as-of date are not counted as currently overdue.
3. **Aging buckets** measure days from `created_at` to as-of date: 0–3, 4–7, 8–14, 15–30, 31+. Count each overdue primary item into its bucket.
4. **Team overdue counts**: group overdue items by team and count. List teams alphabetically.
5. **Top hotspot**: the `(team, owner)` pair with the most overdue records. When owner is null, use `"UNASSIGNED"`. Break ties by picking the first alphabetically by team, then by owner.
6. **Breach rate**: `overdue_count / included_primary_count`, rounded to exactly 3 decimal places.
7. **Escalation queue**: list overdue primary IDs ordered by severity (S1 first), then by `due_at` ascending, then by `id` ascending.
8. **Missing owners**: primary IDs where `owner IS NULL`, sorted ascending.

### Release-readiness assessment

1. Fetch the release by ID to get its milestones, work items, and blockers.
2. For each milestone, count `complete_primary` (items with status `Done`, `Deployed`, or `Verified`) and `primary_total` (all primary items in that milestone, excluding duplicates). Compute `completion_pct` as `(complete_primary / primary_total) * 100`, rounded to 1 decimal place.
3. **Gating work items**: non-complete release items plus any complete items that have an unresolved high-impact blocker (severity `High` or `Critical`). Sort IDs ascending.
4. **Blocker cause counts**: count unresolved blockers with severity `High` or `Critical`, keyed by exact `cause` text. Ignore `Low` severity.
5. **Critical dependency chains**: For each dependency edge where `blocked_id` is a release work item, check the `depends_on_id` item status. If `depends_on_id` is not complete (`Done`, `Deployed`, `Verified`), form a chain `[blocked_id, depends_on_id]`. If `depends_on_id` itself has dependencies on non-complete items, extend the chain recursively. Sort chains lexicographically by the full path.
6. **Readiness score**: `complete_primary / total_primary` (excluding duplicates), rounded to 3 decimal places.
7. **Ship decision**: `SHIP` when all milestones are 100% and no gating items; `SHIP_WITH_WATCH` when readiness score ≥ 0.67 and gating items exist; `NO_SHIP` otherwise.

### Sorting conventions

- ID lists: ascending lexicographic order (natural string sort).
- Team lists: alphabetical.
- Milestone tables: by `milestone_id` ascending.
- Gap table rows: NewFeature, TechDebt, Reliability, Security (fixed order).
- Items within a date: by `closed_at` ascending, then `id` ascending.
- Duplicate clusters: by `primary_id` ascending.

### Rounding

- Percentages in portfolio mix: 1 decimal place.
- Completion percentages: 1 decimal place.
- Readiness score: 3 decimal places.
- Breach rate: 3 decimal places.
- Gaps (percentage points): 1 decimal place.
