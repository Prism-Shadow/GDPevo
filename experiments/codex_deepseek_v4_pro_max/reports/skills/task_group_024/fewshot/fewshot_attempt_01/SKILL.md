 # Engineering Portfolio Analysis Skill

 Analyze engineering portfolio data from a shared REST+SQL environment. Use this skill when asked to perform portfolio mix reviews, SLA aging audits, or release readiness assessments against work-item and portfolio-management data served by a task environment.

 ## Environment connection

 Read `environment_access.md` (or equivalent runtime access notes) provided alongside the task. It contains:
 - **Base URL** — the root of the REST API.
 - **Allowed endpoints** — the available `GET` and `POST` routes.
 - **SQL query endpoint** — `POST /api/query` with required headers and body shape.
 - **Auth token** — the value for the `X-Env-Token` header (typically `portfolio-readonly`).

 Replace the placeholder `<TASK_ENV_BASE_URL>` in prompts with the actual base URL from the access notes.

 ## Data model

 The environment exposes these entities:

 | Entity | Endpoint(s) | Key fields |
 |---|---|---|
 | Work items | `GET /api/work-items`, `GET /api/work-items/{id}` | `id`, `title`, `team`, `owner`, `status`, `closed_at`, `category`, `portfolio_category`, `severity`, `sla_target_date`, `release_id`, `milestone_id`, `mirror_of`, `is_duplicate`, `duplicate_of` |
 | Mix targets | `GET /api/mix-targets` | `scope_id`, `NewFeature_pct`, `TechDebt_pct`, `Reliability_pct`, `Security_pct` |
 | SLA policy | `GET /api/sla-policy` | `category`, `severity`, `max_days` |
 | Releases | `GET /api/releases`, `GET /api/releases/{id}` | `release_id`, `name`, `status` |
 | Milestones | `GET /api/milestones` | `milestone_id`, `release_id`, `name` |
 | Blockers | `GET /api/blockers` | `work_item_id`, `cause`, `impact`, `resolved` |
 | Dependencies | `GET /api/dependencies` | `source_id`, `target_id`, `status` |

 Use `POST /api/query` with SQL for cross-entity filtering, aggregation, and complex conditions. SQL must be a single `SELECT` or `WITH` statement. Pass parameters as a JSON array to avoid injection.

 ## Discovery workflow

 1. **Fetch reference data first.** Call the simple `GET` endpoints to understand available records, field names, and value domains before writing SQL.
 2. **Inspect a few work items individually** (`GET /api/work-items/{id}`) to see exact field names and value formats.
 3. **Write targeted SQL** for the specific scope, using `WHERE` clauses for the teams, quarters, categories, or release IDs stated in the task prompt.
 4. **Validate by spot-checking** a few returned rows against the individual item endpoints.

 ## Work item ID conventions

 IDs follow the pattern `WI-24024-{prefix}{NNN}` or `WI-24024-{NNN}`. Common prefixes include:
 - `P` — Platform Core items
 - `S` — Security / SLA items
 - No prefix — general items

 Treat IDs as opaque strings. Sort lexicographically unless the task specifies another ordering (e.g. by `closed_at`).

 ## Data quality rules (always apply)

 - **Primary vs duplicate**: When a work item has `mirror_of`, `is_duplicate`, or `duplicate_of` fields, only the canonical/primary record counts toward the main analysis. List duplicates separately in `duplicate_clusters` or `exclusion_flags`.
 - **Ignore mirror/export fields**: Fields like `mirror_status` or `legacy_category` are stale; use the authoritative fields (`status`, `portfolio_category`, `category`) on the primary record.
 - **Cancelled items**: Exclude cancelled work items from the primary population. Report them under exclusion flags when the template requires it.
 - **Distractor records**: Records that appear in-scope by team or product area but belong to a different scope/quarter/release are excluded. List them when the template asks for `excluded_distractor_ids`.
 - **Missing owner**: An empty or null `owner` field is `UNASSIGNED` / missing. Report these IDs separately.

 ## Portfolio mix analysis

 Use for tasks asking about closed-work portfolio mix by category.

 ### Steps

 1. **Get the target mix.** Query `GET /api/mix-targets` and filter to the `scope_id` given in the prompt. Extract target percentages for NewFeature, TechDebt, Reliability, Security.
 2. **Fetch closed in-scope work items.** Use SQL to select work items matching the required teams, quarter (`closed_at` range), and product areas. Exclude cancelled, duplicates, mirrors, and distractor records.
 3. **Classify each item.** Use the `portfolio_category` field (or `category` if the former is absent). Every item maps to exactly one of: NewFeature, TechDebt, Reliability, Security.
 4. **Count by category.** Produce item counts (not story points) per category.
 5. **Calculate percentages.** `actual_pct = (count / total_included) * 100`, rounded to 1 decimal place.
 6. **Compute gaps.** `gap_pct = actual_pct - target_pct`, rounded to 1 decimal place.
 7. **Identify under-invested categories.** Those with negative `gap_pct`, ordered from most negative to least negative.
 8. **Determine the follow-up action.** If any gaps are negative, recommend `REBALANCE_CAPACITY` for the category with the largest negative gap. If no negative gaps, `MAINTAIN_CURRENT_MIX`. If data conflicts exist, `INVESTIGATE_DATA_QUALITY`.

 ### Output conventions

 - Sort team and product area names alphabetically.
 - Order included work item IDs by `closed_at` ascending, then `id` ascending.
 - In gap/mix tables, list categories in this fixed order: NewFeature, TechDebt, Reliability, Security.
 - Round all percentages to 1 decimal place.

 ## SLA aging audit

 Use for tasks asking about overdue SLA work items and breach rates.

 ### Steps

 1. **Fetch SLA policy.** Query `GET /api/sla-policy` to get `max_days` per category and severity.
 2. **Identify in-scope work items.** Use SQL to select work items matching the given teams and SLA-relevant categories (typically Reliability and Security). Filter to primary records only (exclude duplicates and mirrors).
 3. **Determine overdue status.** An item is overdue if its `sla_target_date` is before the as-of date and the item is not closed within the recent-closed window (i.e., not `closed_at` within the last N days, or still open).
 4. **Calculate age buckets.** For each included primary item, compute `age = as_of_date - sla_target_date` in days. Bucket into: 0-3, 4-7, 8-14, 15-30, 31+.
 5. **Identify duplicate clusters.** Group items where `duplicate_of` points to a primary ID. Report each cluster as `{primary_id, [duplicate_ids]}`.
 6. **Find missing owners.** Primary items with null/empty `owner`.
 7. **Compute breach rate.** `overdue_primary_count / included_primary_count`, rounded to 3 decimal places.
 8. **Build escalation queue.** Sort overdue primary items by severity (S1 highest priority), then by age descending. (Adjust priority ordering if the task prompt specifies a different scheme.)

 ### Output conventions

 - Sort ID lists lexicographically (ascending string order).
 - List teams alphabetically.
 - Sort duplicate clusters by `primary_id`, with `duplicate_ids` sorted lexicographically.
 - Round `breach_rate` to exactly 3 decimal places.
 - For severity-based tasks: count overdue items per severity (S1, S2, S3, S4).

 ## Release readiness assessment

 Use for tasks asking whether a release is ready to ship.

 ### Steps

 1. **Fetch the release.** `GET /api/releases/{release_id}` for release metadata.
 2. **Fetch milestones.** `GET /api/milestones` filtered to the release.
 3. **Fetch release work items.** Use SQL to find work items associated with the release or its milestones. Separate primary from duplicate/mirror records.
 4. **Compute milestone completion.** For each milestone, count completed primary work items vs. total primary work items. `completion_pct = (complete / total) * 100`, rounded to 1 decimal place.
 5. **Identify gating items.** Non-complete primary work items that block release readiness.
 6. **Fetch blockers.** `GET /api/blockers` for high-impact, unresolved blockers on release work items. Count by exact cause string.
 7. **Fetch dependencies.** `GET /api/dependencies` for chains from blocked release items to non-complete dependencies. Build ordered paths.
 8. **Compute readiness score.** `completed_primary_count / total_primary_count`, rounded to 3 decimal places.
 9. **Determine ship decision.**
    - `SHIP` — readiness score high with no critical blockers.
    - `SHIP_WITH_WATCH` — readiness score acceptable but with watch items.
    - `NO_SHIP` — readiness score too low or critical blockers exist.

 ### Output conventions

 - Sort `milestone_completion` by `milestone_id` ascending.
 - Sort `gating_work_item_ids` ascending with no duplicates.
 - `blocker_cause_counts` keys must be exact cause strings from the blocker records.
 - Sort `critical_dependency_chains` lexicographically by the full path.
 - `completion_pct` rounded to 1 decimal place.
 - `readiness_score` rounded to 3 decimal places.

 ## SQL query patterns

 Use `POST /api/query` with:
 ```
 Content-Type: application/json
 X-Env-Token: portfolio-readonly
 {"sql": "<SQL>", "params": ["val1", "val2"]}
 ```

 Common query shapes:

 **Filter by team and quarter:**
 ```sql
 SELECT * FROM work_items WHERE team IN (?, ?) AND closed_at BETWEEN ? AND ?
 ```

 **Exclude non-primary records:**
 ```sql
 AND (mirror_of IS NULL OR mirror_of = '')
 AND (duplicate_of IS NULL OR duplicate_of = '')
 AND status != 'Cancelled'
 ```

 **Join with milestones:**
 ```sql
 SELECT wi.* FROM work_items wi JOIN milestones m ON wi.milestone_id = m.milestone_id WHERE m.release_id = ?
 ```

 ## General output rules

 - Return a single JSON object matching the provided answer template exactly.
 - Do not include prose, explanations, or markdown fences outside the JSON.
 - Follow all `required`, `additionalProperties`, `const`, and `enum` constraints from the template.
 - Use the ordering and rounding rules specified in the template descriptions and in this skill.
 - When a template field has a `description` annotation, treat it as a binding instruction.
