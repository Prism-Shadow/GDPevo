 # Engineering Portfolio Analysis

 Analyze engineering portfolio data from a shared REST + SQL environment. Use this skill when the task involves portfolio mix reviews, SLA aging audits, or release readiness assessments against a portfolio environment.

 ## Environment Access

 The portfolio environment base URL is provided as `<TASK_ENV_BASE_URL>` in the prompt. All endpoints are listed in `environment_access.md`. The environment offers:

 - REST endpoints for work items, mix targets, SLA policies, releases, milestones, blockers, and dependencies
 - A restricted SQL query endpoint at `POST /api/query` requiring header `X-Env-Token: portfolio-readonly`

 Always inspect the live environment — never rely solely on prompt text, as the environment is the authoritative data source.

 ## Data Model

 ### Work Items (`GET /api/work-items`, `GET /api/work-items/{item_id}`)

 Key fields: `id`, `team`, `owner`, `category`, `status`, `severity`, `product_area`, `quarter`, `release_id`, `milestone_id`, `closed_at`, `created_at`, `due_date`, `duplicate_of`, `sla_deadline`, `mirror_status`, `legacy_category`.

 ### Mix Targets (`GET /api/mix-targets`)

 Each row has a `scope_id` and target percentages per category (`NewFeature`, `TechDebt`, `Reliability`, `Security`). Use the row whose `scope_id` matches the task scope.

 ### SLA Policy (`GET /api/sla-policy`)

 Defines SLA deadlines by severity and category.

 ### Releases (`GET /api/releases`, `GET /api/releases/{release_id}`)

 Fields: `id`, `milestones`, `status`.

 ### Milestones (`GET /api/milestones`)

 Fields: `id`, `release_id`, `work_item_ids`.

 ### Blockers (`GET /api/blockers`)

 Fields: `work_item_id`, `cause`, `impact` (high/low), `resolved`.

 ### Dependencies (`GET /api/dependencies`)

 Fields: `source_id` (depends-on), `target_id` (blocked-by).

 ## Analysis Patterns

 ### Portfolio Mix Review

 1. Fetch work items filtered to the given quarter, teams, and product areas. Use `POST /api/query` with a SELECT filtering on `team IN (…)` and `quarter = ?` and `product_area IN (…)`.
 2. Exclude items with status `cancelled`. Exclude duplicate items (those whose `duplicate_of` field points to another item). Record these in exclusion lists.
 3. Ignore `mirror_status` and `legacy_category` fields — they may be stale. Use the item's own `status` and `category`.
 4. Classify each remaining closed item into exactly one of {NewFeature, TechDebt, Reliability, Security} using the authoritative `category` field.
 5. Fetch the mix target row from `GET /api/mix-targets` matching the task's `scope_id`.
 6. Compute category counts (item counts, not story points), actual percentages (count / total × 100, rounded to 1 decimal), and gap percentages (actual − target, rounded to 1 decimal).
 7. Identify under-invested categories: those with negative gap, ordered from most negative to least negative.
 8. Produce a follow-up action:
    - `REBALANCE_CAPACITY` with `LARGEST_NEGATIVE_GAP` if there are under-invested categories;
    - `MAINTAIN_CURRENT_MIX` with `NO_NEGATIVE_GAPS` if all gaps are zero or positive;
    - `INVESTIGATE_DATA_QUALITY` with `DATA_CONFLICT` if data conflicts prevent reliable computation.
 9. Order included work item IDs by `closed_at` ascending, then by `id` ascending.

 ### SLA Aging Audit

 1. Fetch work items for the given teams and SLA-relevant categories. Filter to primary records only — exclude any item where `duplicate_of` is non-null.
 2. Determine overdue status: an item is overdue if its `due_date` (or `sla_deadline`) is before the as-of date and its status is not closed (or closed after the as-of date).
 3. Compute aging buckets (0-3, 4-7, 8-14, 15-30, 31+ days past due) based on days between due date and as-of date.
 4. Compute team overdue counts (one row per team, alphabetically ordered).
 5. Find the top hotspot: the (team, owner) pair with the most overdue primary records. If owner is null/empty, use `UNASSIGNED`.
 6. Identify missing-owner primary IDs (owner is null, empty, or whitespace).
 7. Detect duplicate clusters: for each primary item, find all items whose `duplicate_of` points to it. Sort clusters by `primary_id` ascending; sort `duplicate_ids` lexicographically.
 8. Compute breach rate: overdue primary count ÷ total primary count, rounded to 3 decimal places.
 9. For escalation: order overdue primary IDs by severity (S1 first, then S2, S3, S4), with ties broken by due date ascending, then id ascending.

 ### Release Readiness Assessment

 1. Fetch the release by ID, then fetch its milestones and all associated work items.
 2. For each milestone, count completed primary work items (status is a terminal complete state) and total primary work items. Compute completion percentage rounded to 1 decimal. Sort milestones by `milestone_id` ascending.
 3. Identify gating work item IDs: non-complete primary work items in the release, sorted ascending, no duplicates.
 4. Examine blockers: count unresolved high-impact blockers, keyed by exact cause string. Ignore resolved or low-impact blockers.
 5. Trace critical dependency chains: for each gating work item blocked by another non-complete work item, trace the dependency path. Sort chains lexicographically by the full path string.
 6. Compute readiness score: completed primary count ÷ total primary count, rounded to 3 decimal places.
 7. Determine ship decision:
    - `SHIP` if readiness ≥ 0.90, no gating items, and no unresolved high-impact blockers;
    - `SHIP_WITH_WATCH` if readiness ≥ 0.75 but some concerns remain;
    - `NO_SHIP` if readiness < 0.75 or critical unresolved blockers exist.

 ## Edge Cases & Conventions

 ### Duplicate Handling
 A work item is a duplicate if its `duplicate_of` field is non-null and points to another work item ID. The target of `duplicate_of` is the primary/canonical record. Duplicates must be excluded from all primary counts, percentages, and metrics. List them separately in `excluded_duplicate_ids`, `duplicate_clusters`, or similar fields.

 ### Cancelled Records
 Work items with `status` equal to `cancelled` (case-insensitive) must be excluded from the primary portfolio mix. List them separately.

 ### Stale Mirror / Legacy Fields
 The fields `mirror_status` and `legacy_category` may contain outdated data from a prior export. Always use the authoritative `status` and `category` fields from the work item itself. Set `ignored_mirror_status_and_legacy_category` to `true` when these fields exist but are not used.

 ### Distractor Records
 Some work items may appear in-scope by team, quarter, or product area but are distractors that should not be counted. Common distractor patterns: items from a different quarter but returned in results, items with no relevant category, items that are duplicates or cancelled. Exclude them and list in `excluded_distractor_ids`.

 ### Missing Owners
 Treat `null`, empty string, and whitespace-only owner values as missing. Report these items in `missing_owner_ids`. For hotspot analysis, use `UNASSIGNED` as the owner label.

 ### Category Resolution
 When a work item's `category` field is present and one of {NewFeature, TechDebt, Reliability, Security}, use it directly. If `category` is missing or ambiguous, resolve using `type` first, then `labels`, then `title` keywords — applying portfolio category conventions (e.g., "bug" or "incident" → Reliability, "vulnerability" or "cve" → Security, "feature" or "story" → NewFeature, "refactor" or "cleanup" → TechDebt). Do not use `legacy_category`.

 ## Ordering Rules

 - **Work item ID lists**: `closed_at` ascending then `id` ascending for portfolio mix; lexicographically ascending for SLA and release analyses.
 - **Team lists**: alphabetically.
 - **Category rows**: fixed order: NewFeature, TechDebt, Reliability, Security.
 - **Milestone lists**: `milestone_id` ascending.
 - **Duplicate clusters**: sorted by `primary_id` ascending; `duplicate_ids` within each cluster sorted lexicographically.
 - **Escalation queues**: severity descending (S1 before S2 before S3 before S4), then due date ascending, then id ascending.
 - **Dependency chains**: sorted lexicographically by the joined path string.

 ## Precision Rules

 - Percentages (completion, mix shares, gaps): rounded to **1 decimal place**.
 - Rates and scores (breach rate, readiness score): rounded to **3 decimal places**.
 - All counts: exact integers.

 ## Enum Reference

 **Categories**: `NewFeature`, `TechDebt`, `Reliability`, `Security`

 **Actions**: `REBALANCE_CAPACITY`, `INVESTIGATE_DATA_QUALITY`, `MAINTAIN_CURRENT_MIX`

 **Rationale codes**: `LARGEST_NEGATIVE_GAP`, `NO_NEGATIVE_GAPS`, `DATA_CONFLICT`

 **Ship decisions**: `SHIP`, `SHIP_WITH_WATCH`, `NO_SHIP`

 **Severities**: `S1`, `S2`, `S3`, `S4`

 ## Answer Format

 Always return a single JSON object matching the provided answer template exactly. Do not include prose, explanations, or markdown outside the JSON. Use the exact field names, types, and required constraints from the template.

 Before finalizing, validate:
 - All required fields are present.
 - Ordering rules are followed.
 - Precision rules are applied.
 - Enum values match exactly (case-sensitive).
 - Exclusion lists are populated when applicable.
