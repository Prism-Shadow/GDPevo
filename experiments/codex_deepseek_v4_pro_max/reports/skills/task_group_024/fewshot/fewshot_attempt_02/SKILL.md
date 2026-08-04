 # Enterprise Portfolio Analysis Skill

 Analyze work-item portfolios through a REST + SQL API combining work items,
 mix targets, SLA policies, releases, milestones, blockers, and dependencies.

 ## Environment Setup

 The environment provides a base URL through `<TASK_ENV_BASE_URL>` or similar
 prompt placeholders. Runtime access details including the query token and
 endpoint list are supplied in a separate `environment_access.md` file.

 - **Base URL**: read from the prompt placeholder or access file.
 - **Auth header**: `X-Env-Token: portfolio-readonly` on `/api/query` requests.
 - **Content-Type**: `application/json` for POST bodies.

 ## Endpoints

 | Method | Path | Description |
 |--------|------|-------------|
 | GET | `/api/work-items` | List all work items (paginated JSON with `count` + `work_items` array). |
 | GET | `/api/work-items/{id}` | Single work item by ID. |
 | GET | `/api/mix-targets` | All portfolio mix targets. |
 | GET | `/api/sla-policy` | SLA severity-to-days mapping. |
 | GET | `/api/releases` | All releases. |
 | GET | `/api/releases/{id}` | Single release with its milestones and blockers. |
 | GET | `/api/milestones` | All milestones. |
 | GET | `/api/dependencies` | All dependency edges. |
 | GET | `/api/blockers` | All blocker records. |
 | POST | `/api/query` | Run a restricted SQL query (see below). |

 ### SQL Query Endpoint

 - Method: `POST /api/query`
 - Headers: `Content-Type: application/json`, `X-Env-Token: portfolio-readonly`
 - Body: `{"sql": "<single SELECT or WITH statement>", "params": ["<value>", ...]}`
 - Constraints: exactly one statement, SELECT/WITH only, max 1000 rows.
 - Use parameterized queries with `?` placeholders and the `params` array.
 - Table name for work items is `work_items`. Column names match JSON field names
   returned by the REST endpoints (snake_case where applicable).

 Prefer the SQL endpoint for filtered/scoped queries. Use REST endpoints for
 reference data (mix targets, SLA policy, releases, milestones).

 ## Data Model

 ### Work Item Fields

 | Field | Type | Notes |
 |-------|------|-------|
 | `id` | string | Primary identifier, e.g. `WI-24024-P001`. |
 | `title` | string | Human-readable title; may contain classification hints. |
 | `work_type` | string | Enum: Feature, Bug, Chore, Refactor, Enhancement, Incident, Security, Reliability, Compliance, Dependency. |
 | `status` | string | Enum: Backlog, In Progress, Review, Done, Deployed, Verified, Closed, Duplicate, Cancelled, Reopened. **Authoritative** status. |
 | `team` | string | Owning engineering team. |
 | `owner` | string or null | Assigned individual. |
 | `product_area` | string | Product area (e.g. Atlas Backend, Identity, Checkout). |
 | `created_at` | date | YYYY-MM-DD. |
 | `due_at` | date or null | YYYY-MM-DD. |
 | `closed_at` | date or null | YYYY-MM-DD; null while not closed. |
 | `severity` | string | S1, S2, S3, or S4. |
 | `priority` | integer | 1-5 scale. |
 | `labels` | JSON array of strings | e.g. `["security","cve","rollout"]`. Used for category classification. |
 | `story_points` | integer | Estimation metric. |
 | `release_id` | string or null | Associated release. |
 | `milestone_id` | string or null | Associated milestone. |
 | `duplicate_of` | string or null | If non-null, this item is a duplicate of the referenced item. |
 | `mirror_status` | string | **Untrusted** — a stale mirror/export field. Never use for status decisions. |
 | `legacy_category` | string | **Untrusted** — a legacy field. Never use for category classification. |

 ### Mix Target Fields

 | Field | Type | Notes |
 |-------|------|-------|
 | `scope_id` | string | Unique identifier; matched to the task prompt scope. |
 | `quarter` | string | e.g. `2025-Q4`. |
 | `team_group` | string | e.g. `Platform Core + Identity Services`. |
 | `product_area` | string | e.g. `Atlas Backend + Identity`. |
 | `new_feature_pct` | float | Target share as decimal (0.34 = 34%). |
 | `tech_debt_pct` | float | Target share as decimal. |
 | `reliability_pct` | float | Target share as decimal. |
 | `security_pct` | float | Target share as decimal. |

 To convert to percentage points: multiply by 100.

 ### SLA Policy

 | Severity | `days_to_due` |
 |----------|---------------|
 | S1 | 3 |
 | S2 | 10 |
 | S3 | 21 |
 | S4 | 45 |

 An item is overdue when its `due_at` is before the as-of date and it is not in a
 completed terminal status, OR when it was closed after its `due_at`
 (closed-late). The SLA due date for calculating overdue status is derived from
 `created_at + days_to_due` for the item's severity.

 ### Release, Milestone, Blocker, Dependency

 - **Release**: `id`, `name`, `target_date`, `train`.
 - **Milestone**: `id`, `name`, `owner_team`, `release_id`.
 - **Blocker**: `id`, `cause`, `severity` (Low/Medium/High/Critical), `status`
   (Open/Monitoring/Resolved), `work_item_id`, `release_id`, `opened_at`,
   `resolved_at`.
 - **Dependency**: `blocked_id`, `depends_on_id`, `relation`
   (e.g. `blocks-release-readiness`, `depends-on`, `validation-required`,
   `security-review-required`).

 ## Portfolio Category Classification

 Every work item maps to exactly one of four portfolio categories:
 **NewFeature**, **TechDebt**, **Reliability**, **Security**.

 Classification uses a signal-priority chain: **work type → labels → title**.
 When signals conflict, the highest-priority signal wins according to the rules
 below. The title is only consulted as a tiebreaker or to detect stale/misleading
 labels (e.g. a title containing "stale security label" means the `security`
 label should be ignored for that item).

 ### Step 1 — Default by work_type

 | work_type | Default Category |
 |-----------|-----------------|
 | `Feature` | NewFeature |
 | `Bug` | TechDebt |
 | `Chore` | TechDebt |
 | `Refactor` | TechDebt |
 | `Dependency` | TechDebt |
 | `Enhancement` | Security |
 | `Incident` | Reliability |
 | `Reliability` | Reliability |
 | `Security` | Security |
 | `Compliance` | Security |

 ### Step 2 — Label override (first match wins, checked in this order)

 1. **Reliability keywords**: `reliability`, `outage`, `latency`, `incident`,
    `flaky` → **Reliability**.
 2. **TechDebt keywords**: `cleanup`, `refactor`, `migration` →
    **TechDebt** (only if no Reliability keyword matched first).
 3. **Security keywords**: `security`, `cve`, `encryption` →
    **Security** (only if no Reliability or TechDebt keyword matched first).

 ### Step 3 — Title tiebreaker

 - If the title contains a keyword like `stale` adjacent to a category label
   word (e.g. "stale security label"), discard the corresponding label signal
   and fall back to the work_type default or next label match.
 - Otherwise, titles do not override labels; they only resolve ambiguities
   when labels provide no clear signal.

 ### Note on SLA-scoped classification

 When a task scopes categories to only Security and Reliability (typical for SLA
 audits), classify items into those two buckets only. Items whose classification
 would land in NewFeature or TechDebt are excluded from the SLA population.

 ## Primary vs. Duplicate / Distractor Records

 ### Authoritative status

 Use the `status` field for all status decisions. **Never use `mirror_status`**
 — it is a stale export/mirror column that may disagree with `status`.

 ### Duplicate records

 - An item where `duplicate_of` is non-null is a duplicate. The item referenced
   by `duplicate_of` is the primary/canonical record.
 - An item with `status = "Duplicate"` is also a duplicate even if
   `duplicate_of` is null.
 - Duplicates are **excluded from primary counts** (portfolio mix totals, SLA
   primary population, release readiness primary denominators).
 - Duplicates should still be **reported in `duplicate_clusters`** or
   `exclusion_flags` sections.
 - Build duplicate clusters by grouping items by their `duplicate_of` value:
   the target is the `primary_id`, and all items pointing to it are
   `duplicate_ids`. Sort each cluster's `duplicate_ids` lexicographically.

 ### Cancelled records

 - Items with `status = "Cancelled"` are excluded from all primary analysis.
   Report them in the exclusion flags.

 ### Scope filtering

 For a given scope, include an item in the primary population only when:
 1. The item's `team` is in the scope's team list.
 2. The item's `product_area` is in the scope's product area list.
 3. The item's `status` is not Duplicate or Cancelled.
 4. `duplicate_of` is null (unless it is the canonical record for a duplicate
    cluster included in scope).
 5. For quarter-scoped tasks: `closed_at` falls within the calendar quarter.

 ### Stale mirror fields

 The `mirror_status` and `legacy_category` columns are unreliable. Ignore them
 completely. When a prompt warns about "stale mirror fields," it means some
 records have `mirror_status` values that contradict the authoritative `status`.
 Always read `status` directly.

 ## Workflow 1 — Closed-Work Portfolio Mix

 Use this workflow when the task asks for a portfolio mix analysis comparing
 actual category distribution against targets.

 ### Steps

 1. **Fetch the mix target**: Query `/api/mix-targets` and locate the row where
    `scope_id` matches the prompt's target scope.
 2. **Collect in-scope items**: Use the SQL endpoint to filter work items by
    `team IN (...)` AND `product_area IN (...)` AND `closed_at` between the
    quarter start and end dates.
 3. **Exclude non-primary records**: Remove Duplicate status, Cancelled status,
    and items where `duplicate_of` is non-null (unless they are the primary for
    an in-scope duplicate).
 4. **Classify each included item**: Apply the portfolio category classification
    rules above to assign exactly one category per item.
 5. **Count by category**: Produce `category_counts` as integer counts.
 6. **Compute percentages**: For each category: `(count / total) * 100`, rounded
    to 1 decimal place.
 7. **Build gap table**: For each category in fixed order (NewFeature, TechDebt,
    Reliability, Security):
    - `target_pct` = target decimal × 100, rounded to 1 decimal.
    - `actual_pct` = computed percentage, rounded to 1 decimal.
    - `gap_pct` = `actual_pct - target_pct`, rounded to 1 decimal.
 8. **Identify under-invested categories**: Categories with negative `gap_pct`,
    ordered from most negative to least negative.
 9. **Recommend action**: Based on the largest negative gap, recommend
    REBALANCE_CAPACITY targeting the most under-invested category.

 ### Sorting conventions

 - Included work item IDs: by `closed_at` ascending, then `id` ascending
   (lexicographic).
 - Team arrays: alphabetically.
 - Gap table rows: NewFeature, TechDebt, Reliability, Security (fixed order).

 ## Workflow 2 — SLA Aging Audit

 Use this workflow when the task asks for SLA breach analysis for reliability
 and security work.

 ### Steps

 1. **Fetch SLA policy**: GET `/api/sla-policy`.
 2. **Collect candidate items**: Use SQL to find work items for the specified
    teams with work types and labels in the reliability/security domain.
    Filter to the categories specified in the prompt (typically Security and
    Reliability).
 3. **Identify primary population**: Exclude Duplicate and Cancelled items.
 4. **Detect duplicates**: Build duplicate clusters from the `duplicate_of`
    field. Only include clusters where the primary item is in-scope.
 5. **Classify as overdue**: An item is overdue when:
    - It is in the primary population.
    - It is NOT in a completed terminal status (Done, Deployed, Verified,
      Closed), AND its `due_at` is strictly before the as-of date.
    - OR it IS in a completed status but was closed after its `due_at`
      (closed-late), AND closed within the recent-closed window.
 6. **Compute aging buckets**: For overdue items, bucket by days between
    `created_at` and as-of date: 0-3, 4-7, 8-14, 15-30, 31+.
 7. **Find team and owner hotspots**: Count overdue items per team and per
    owner. The hotspot is the (team, owner) pair with the most overdue items.
 8. **Identify missing owners**: Primary items where `owner` is null.
 9. **Build escalation queue**: Overdue items ordered by severity (S1 first,
    then S2, S3, S4), then by `due_at` ascending within each severity tier.
 10. **Calculate breach rate**: `overdue_count / primary_total`, rounded to
     exactly 3 decimal places.

 ### Sorting conventions

 - ID lists: lexicographically ascending.
 - Teams: alphabetically.
 - Duplicate clusters: sorted by `primary_id` ascending; `duplicate_ids` within
   each cluster sorted lexicographically.
 - Aging buckets: in the fixed order 0-3, 4-7, 8-14, 15-30, 31+.

 ## Workflow 3 — Release Readiness Assessment

 Use this workflow when the task asks whether a release is ready to ship.

 ### Steps

 1. **Fetch release data**: GET `/api/releases/{release_id}` for the release
    object, its milestones, and its blockers. Also GET `/api/dependencies` and
    `/api/work-items` or use SQL to get all work items for the release.
 2. **Identify primary work items**: All work items where `release_id` matches
    the target release, excluding Duplicate and Cancelled statuses.
 3. **Milestone completion**: For each milestone of the release, count:
    - `complete_primary`: items in terminal statuses (Done, Deployed, Verified,
      Closed).
    - `primary_total`: all primary items assigned to that milestone.
    - `completion_pct = (complete_primary / primary_total) * 100`, rounded to 1
      decimal.
 4. **Gating work items**: Non-complete primary items that have at least one
    unresolved High or Critical blocker. Unresolved means blocker `status` is not
    `Resolved`.
 5. **Blocker cause counts**: Count unresolved High and Critical blockers,
    grouped by exact `cause` string. Exclude Low and Medium severity blockers.
 6. **Critical dependency chains**: For each gating work item, trace dependency
    paths through the dependency graph. A critical chain exists when a gating
    item depends on a work item that is itself non-complete. Follow transitive
    chains (A depends on B, B depends on non-complete C → path is A, B, C).
    Exclude chains where any node is a duplicate.
 7. **Ship decision**:
    - `SHIP`: all milestones ≥ 95% complete, zero gating items, zero critical
      dependency chains.
    - `SHIP_WITH_WATCH`: all milestones ≥ 80% complete, ≤ 2 gating items,
      zero critical chains.
    - `NO_SHIP`: anything below SHIP_WITH_WATCH thresholds.
 8. **Readiness score**: `completed_primary_items / total_primary_items`, rounded
    to 3 decimal places.

 ### Sorting conventions

 - `milestone_completion`: sorted by `milestone_id` ascending.
 - `gating_work_item_ids`: sorted ascending, no duplicates.
 - `blocker_cause_counts`: keys are exact cause strings from blocker records.
 - `critical_dependency_chains`: sort chains lexicographically by the full
   ordered path (compare path arrays element by element).

 ## Common Patterns & Conventions

 ### Sorting

 - Work item ID lists: lexicographic ascending (string sort).
 - When ordering by date then ID: `ORDER BY closed_at ASC, id ASC`.
 - Team arrays: alphabetical.
 - Duplicate cluster contents: `primary_id` ascending at top level,
   `duplicate_ids` lexicographically ascending within each cluster.

 ### Rounding

 - Percentages (mix, completion): round to **1 decimal place**.
 - Rates (breach rate, readiness score): round to **3 decimal places**.
 - Use standard rounding (half-up / round-half-even depending on language
   default; consistency with answer key is what matters).

 ### Detecting stale labels and mirror fields

 - **`mirror_status`**: ignore entirely. Some items have `mirror_status = "Open"`
   while `status = "Closed"` — the `status` field is authoritative.
 - **`legacy_category`**: ignore entirely. Use work_type + labels for
   classification.
 - **Stale labels in titles**: When a title contains the word "stale" adjacent to
   a label keyword (e.g. "stale security label", "stale-export"), treat the
   referenced label as untrustworthy for that item. Do not let it override the
   work_type default.

 ### Quarter date ranges

 - Q1: Jan 1 – Mar 31
 - Q2: Apr 1 – Jun 30
 - Q3: Jul 1 – Sep 30
 - Q4: Oct 1 – Dec 31

 ### SQL query construction

 Prefer parameterized queries:
 ```sql
 SELECT id, work_type, labels, title, team, product_area, status,
        duplicate_of, closed_at, created_at, due_at, severity, owner
 FROM work_items
 WHERE team IN (?, ?) AND closed_at >= ? AND closed_at <= ?
 ORDER BY closed_at, id
 ```

 The `labels` column is returned as a JSON string; parse it into an array
 before matching label keywords.

 ### Terminal / completed statuses

 These statuses indicate a work item is done: `Done`, `Deployed`, `Verified`,
 `Closed`. All others (`Backlog`, `In Progress`, `Review`, `Reopened`) indicate
 the item is not yet complete.

 ## Output Guidance

 - Always return a single JSON object, no prose outside the JSON.
 - Follow the exact schema provided in the task's `answer_template.json`.
 - Use stable, deterministic ordering as described above.
 - Round all computed numbers to the specified precision.
 - When the task provides an answer template, treat its `const` and `enum`
   constraints as the authoritative schema.
