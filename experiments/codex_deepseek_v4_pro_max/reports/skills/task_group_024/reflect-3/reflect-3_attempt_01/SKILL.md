 # Portfolio Engineering Analysis Skill

 This skill provides instructions for interacting with a portfolio engineering REST API to perform three types of analysis: portfolio-mix reviews, SLA aging audits, and release-readiness assessments.

 ## Environment Setup

 The environment base URL is provided in the task prompt as <TASK_ENV_BASE_URL> or similar. Runtime access details are in `environment_access.md` which lists available endpoints and required tokens.

 ### Default Endpoints
 - `GET /api/work-items` — list all work items
 - `GET /api/work-items/{item_id}` — single work item
 - `GET /api/mix-targets` — portfolio mix targets
 - `GET /api/sla-policy` — SLA policy by severity
 - `GET /api/releases` — all releases
 - `GET /api/releases/{release_id}` — single release with milestones
 - `GET /api/milestones` — all milestones
 - `GET /api/dependencies` — dependency edges
 - `GET /api/blockers` — blocker records
 - `POST /api/query` — restricted SQL, requires header `X-Env-Token` (value from `environment_access.md`)

 ### SQL Query Endpoint
 ```
 POST /api/query
 Content-Type: application/json
 X-Env-Token: <token>
 Body: {"sql": "<SELECT or WITH>", "params": ["val1", ...]}
 ```
 Constraints: single SELECT/WITH statement, params as JSON array, max 1000 rows.

 ## Work Item Schema

 Each work item has these fields:
 - `id` (string, e.g. "WI-24024-001" or "WI-24024-P001")
 - `title` (string)
 - `work_type` (enum: Feature, Security, Reliability, Refactor, Bug, Incident, Enhancement, Chore, Dependency, Compliance)
 - `status` (enum: Closed, Verified, Done, Deployed, In Progress, Review, Backlog, Reopened, Duplicate, Cancelled)
 - `team` (string)
 - `owner` (string or null)
 - `product_area` (string)
 - `created_at`, `due_at`, `closed_at` (dates or null)
 - `severity` (S1–S4)
 - `priority` (integer)
 - `labels` (JSON array of strings)
 - `story_points` (integer)
 - `release_id`, `milestone_id` (string or null)
 - `duplicate_of` (work item id or null)
 - `mirror_status` (may be stale; do not use for decisions)
 - `legacy_category` (ignore; the mirror/legacy fields are not authoritative)

 ## Portfolio Category Classification

 Classify each work item into one of: `NewFeature`, `TechDebt`, `Reliability`, `Security`.

 ### Decision Rules (apply in order)

 1. **Direct work_type mapping:**
    - `Feature` → NewFeature
    - `Security` → Security
    - `Reliability` → Reliability
    - `Refactor` → TechDebt
    - `Chore` → TechDebt
    - `Dependency` → TechDebt

 2. **Label-based resolution for ambiguous types** (Enhancement, Bug, Incident, Compliance):
    - Labels containing `security`, `cve`, `encryption`, or `auth` → Security
    - Labels containing `reliability`, `outage`, `incident`, or `latency` → Reliability
    - Labels containing `feature` or `rollout` → NewFeature
    - Labels containing `cleanup`, `refactor`, or `migration` → TechDebt

 3. **Stale-signal detection in titles:**
    - If the title contains "stale security label", do NOT classify as Security; fall through to the next applicable rule.
    - If the title contains "with auth title", the "auth" signal in the title is misleading; rely on other signals.

 4. **Stale-export label:**
    - If labels include `stale-export`, the label set is unreliable. Fall back to work_type only: `Incident` → Reliability; everything else → not SLA-relevant.

 5. **Tie-breaking:** When both Security and Reliability signals are present, classify as Security.

 ## Portfolio Mix Analysis

 ### Steps
 1. Query `mix_targets` for the row matching the given `scope_id` to get target percentages.
 2. Query work items matching the scope filters (teams, product areas, quarter date range) using SQL.
 3. Exclude items with `status = 'Duplicate'` or `status = 'Cancelled'`.
 4. Exclude items with `duplicate_of` set (they reference another primary item).
 5. Classify each remaining closed work item into a portfolio category.
 6. Count items per category, compute percentages (rounded to 1 decimal), compute gaps (actual − target).
 7. Identify under-invested categories (negative gap, sorted most-negative first).
 8. Recommend a follow-up action targeting the largest deficit.

 ### Answer Format Notes
 - `included_work_item_ids`: sorted by `closed_at` ascending, then `id` ascending.
 - `category_percentages` and `gap_table` values: rounded to 1 decimal place (percentage points).
 - `under_invested_categories`: ordered from most negative gap to least negative.
 - `exclusion_flags.ignored_mirror_status_and_legacy_category`: always `true`.
 - `exclusion_flags.excluded_duplicate_ids`: items excluded for duplicate status or duplicate_of.
 - `exclusion_flags.excluded_cancelled_ids`: items excluded for Cancelled status.

 ## SLA Aging Audit

 ### Steps
 1. Query `sla-policy` to get `days_to_due` per severity.
 2. Query work items for the given teams using SQL. Filter to items created on or before the as-of date. Exclude `status = 'Duplicate'`.
 3. Classify items as SLA-relevant (Reliability or Security only) using the portfolio category conventions.
 4. The primary SLA population consists of items that are:
    - SLA-relevant (Reliability or Security)
    - Not closed within the recent window (closed_at is null OR closed_at < as_of − window_days)
    - Not a duplicate (no duplicate_of set)
 5. For each primary item, compute age:
    - Open items: age = as_of_date − created_at
    - Closed items: age = closed_at − created_at
 6. An item is overdue if age > SLA `days_to_due` for its severity.
 7. Bucket ages into: 0-3, 4-7, 8-14, 15-30, 31+ days.
 8. Count overdue items per team.
 9. Identify the owner/team pair with the most overdue primary records. Use "UNASSIGNED" when owner is null.
 10. Collect duplicate clusters: for each primary item that has duplicates pointing to it, list primary_id with its duplicate_ids sorted lexicographically.
 11. List primary items with null owner as `missing_owner_ids`.
 12. Breach rate = overdue count / primary count, rounded to 3 decimal places.

 ### Answer Format Notes
 - All ID lists sorted lexicographically (ascending).
 - Teams listed alphabetically.
 - `duplicate_clusters` sorted by `primary_id`, with `duplicate_ids` sorted lexicographically.
 - `breach_rate`: exactly 3 decimal places.
 - For the escalation queue (train_005 variant): sort overdue primary items by severity (S1 first) then by age descending within the same severity.

 ## Release Readiness Assessment

 ### Steps
 1. Query the release by ID to get target_date and milestones.
 2. Query all work items for the release using SQL: `WHERE release_id = ?`.
 3. Exclude duplicate items (`status = 'Duplicate'` or `duplicate_of` set).
 4. For each milestone, count completed primary work items:
    - Completed statuses: `Closed`, `Verified`, `Done`, `Deployed`
    - Not completed: `In Progress`, `Review`, `Backlog`, `Reopened`
 5. Compute `completion_pct` = complete / total × 100, rounded to 1 decimal.
 6. `gating_work_item_ids`: non-complete release work items that have unresolved blockers.
 7. `blocker_cause_counts`: count unresolved high-impact (Critical or High severity) blockers, keyed by exact `cause` text.
 8. `critical_dependency_chains`: for each release work item that has a dependency, trace to non-complete dependencies. Each chain is an ordered list `[blocked_release_work_id, ..., non_complete_dep_id]`. Sort chains lexicographically by the full path.
 9. `readiness_score`: completed primary count / primary total, rounded to 3 decimal places.
 10. `ship_decision`:
     - `NO_SHIP` if any Critical or High severity unresolved blocker exists.
     - `SHIP_WITH_WATCH` if only Medium/Low blockers exist but non-complete items remain.
     - `SHIP` if all primary items are complete and no unresolved blockers.

 ### Answer Format Notes
 - `milestone_completion` sorted by milestone_id ascending.
 - `gating_work_item_ids` sorted ascending, no duplicates.
 - `blocker_cause_counts` keys must be exact cause strings.
 - `critical_dependency_chains` sorted lexicographically by the full path.

 ## General Conventions

 - **Authoritative fields**: Use `status`, `work_type`, `labels`, `title`, `closed_at`, `created_at`, `severity`, `duplicate_of`. Do NOT rely on `mirror_status` or `legacy_category`.
 - **ID ordering**: Lexicographic (ASCII) ordering unless otherwise specified.
 - **Rounding**: Use Python's `round()` or equivalent; percentage points to 1 decimal, rates to 3 decimals.
 - **SQL queries**: Always use parameterized queries with `?` placeholders and a `params` array. Include an `ORDER BY` clause.
 - **Date filtering**: Use ISO 8601 date strings (`YYYY-MM-DD`) in SQL comparisons.
 - **Duplicate handling**: Items with `duplicate_of` set OR `status = 'Duplicate'` are duplicates. Report them but exclude from primary counts.
 - **Cancelled items**: Items with `status = 'Cancelled'` are excluded from primary counts.
