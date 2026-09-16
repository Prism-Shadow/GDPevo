---
name: engineering-portfolio-environment
description: Solve engineering portfolio environment tasks that require producing strict JSON from read-only work item data, mix targets, SLA policy, releases, milestones, blockers, dependencies, or the restricted SQL endpoint. Use for portfolio-mix reviews, SLA aging audits, release-readiness assessments, duplicate/cancelled exclusion reports, and similar tasks that reference TASK_ENV_BASE_URL, environment_access.md, or input/payloads/answer_template.json.
---

# Engineering Portfolio Environment

## Core Workflow

1. Read the user prompt, `environment_access.md`, and the answer template before querying data.
2. Use the base URL and token exactly as supplied by `environment_access.md`; never call `/api/judge`.
3. Fetch authoritative records through the business endpoints or `POST /api/query`.
4. Build the answer from source-of-truth fields, then validate it against the template shape.
5. Return only the requested JSON when the prompt says not to include prose.

Useful endpoint set:

- `GET /api/work-items`
- `GET /api/work-items/{item_id}`
- `GET /api/mix-targets`
- `GET /api/sla-policy`
- `GET /api/releases`
- `GET /api/releases/{release_id}`
- `GET /api/milestones`
- `GET /api/dependencies`
- `GET /api/blockers`
- `POST /api/query` with `{"sql":"SELECT ...","params":[]}` and the required token header

Prefer SQL for scoped joins and reproducible filtering. Use only `SELECT` or `WITH` statements.

## Source-Of-Truth Rules

- Trust `status`, `closed_at`, `created_at`, `due_at`, `work_type`, `labels`, `title`, `team`, `product_area`, `release_id`, `milestone_id`, `duplicate_of`, `severity`, `priority`, and `owner`.
- Treat `mirror_status` and `legacy_category` as stale export fields. Do not use them to decide current status, completion, inclusion, or category when authoritative fields disagree.
- Treat a record as duplicate when `duplicate_of` is non-null or `status` is `Duplicate`. Exclude duplicates from primary denominators and report them only in duplicate fields when requested.
- Treat `status: Cancelled` as non-primary. Exclude it from primary denominators and report it only in cancelled/distractor fields when requested.
- Treat complete primary statuses as `Closed`, `Done`, `Verified`, and `Deployed`. Treat all other non-duplicate, non-cancelled statuses as non-complete unless the prompt defines a different rule.
- Parse `labels` as a list, not as an opaque string.
- Use item counts for portfolio mix unless the prompt explicitly asks for story points.

## Category Resolution

Classify each primary work item into exactly one portfolio category. Resolve conflicting signals in this priority order:

1. `Security`: `work_type` is `Security` or `Compliance`, or labels/title contain security-specific terms such as `security`, `cve`, `auth`, `encryption`, or `compliance`.
2. `Reliability`: `work_type` is `Reliability`, `Incident`, or `Bug`, or labels/title contain reliability terms such as `reliability`, `incident`, `outage`, `latency`, `flaky`, or `retry`.
3. `TechDebt`: `work_type` is `Refactor`, `Chore`, or `Dependency`, or labels/title contain debt terms such as `cleanup`, `refactor`, `migration`, `deprecate`, or `dependency`.
4. `NewFeature`: `work_type` is `Feature` or `Enhancement`, or labels/title contain product terms such as `feature`, `rollout`, or `customer-request`.

Use the first matching category in that order. If no signal matches, choose the closest category by title semantics and document only through the requested JSON fields, not extra prose.

## Portfolio Mix Tasks

1. Identify scope from the prompt: quarter/date range, teams, product areas, and target `scope_id`.
2. Select in-scope work items by authoritative `team`, `product_area`, and closed date within the quarter. Use closed primary work only.
3. Exclude duplicates and cancelled/distractor records from the included set. Keep their IDs for any requested exclusion fields.
4. Classify included items with the category-resolution rules.
5. Fetch the `mix_targets` row matching the target `scope_id`.
6. Convert target decimals to percentage points. For each category:
   - `count = included item count`
   - `actual_pct = round(count / total_included * 100, 1)`; use `0.0` when the denominator is zero
   - `target_pct = round(target_decimal * 100, 1)`
   - `gap_pct = round(actual_pct - target_pct, 1)`
7. Category row order is usually `NewFeature`, `TechDebt`, `Reliability`, `Security`; follow the template if it specifies otherwise.
8. Sort included IDs by `closed_at` ascending, then ID ascending, unless the template says another order.
9. Under-invested categories are categories with negative gaps, ordered from most negative to least negative.
10. For rebalance fields, choose the largest negative gap as the primary/largest deficit category. Use the next negative gap as secondary when requested. If no category has a negative gap, use the template's maintain-current-mix option if available.
11. For an owner-team recommendation, choose the in-scope team most associated with the deficit category, usually the team with the most included primary work in that category. Break ties by the template or stable alphabetical order.

## SLA Aging Tasks

1. Identify teams, category set, `as_of` date, and recent closed window from the prompt.
2. Classify work items with the category-resolution rules and keep only requested SLA categories, usually `Security` and `Reliability`.
3. Primary SLA population:
   - `created_at <= as_of`
   - not duplicate and not cancelled
   - in requested teams and categories
   - active as of `as_of` (`closed_at` is null or after `as_of`) or closed within the recent window ending on `as_of`
4. Duplicate clusters:
   - Apply the same scope, category, and time-window logic to duplicate records.
   - Group by `duplicate_of`.
   - Sort clusters by `primary_id`; sort each `duplicate_ids` list ascending.
5. Due date:
   - Prefer authoritative `due_at`.
   - If `due_at` is missing, compute it from `created_at` plus `sla_policy.days_to_due` for the item's `severity`.
6. Overdue rule:
   - Active item: overdue when `due_at < as_of`.
   - Closed item: overdue when `closed_at > due_at`.
   - A due date equal to `as_of` or a close date equal to `due_at` is not overdue.
7. Age for bucket counts:
   - Use days from `created_at` to `closed_at` when the item closed on or before `as_of`.
   - Otherwise use days from `created_at` to `as_of`.
   - Bucket inclusively into `0-3`, `4-7`, `8-14`, `15-30`, and `31+`.
8. Breach rate is `overdue_primary_count / included_primary_count`, rounded to three decimals; use `0.000` when the denominator is zero.
9. Sort ID lists lexicographically unless the template defines a priority order.
10. For team overdue counts, list requested teams in template order or alphabetical order and count overdue primary items only.
11. For hotspot fields, group overdue primary items by team and owner, using `UNASSIGNED` for missing owner. Pick the largest count; break ties by team then owner.
12. For escalation queues, order overdue primary items by severity rank `S1`, `S2`, `S3`, `S4`; then by days overdue descending; then by lower numeric priority; then by ID ascending.

## Release Readiness Tasks

1. Fetch the release, all milestones for that release, work items with matching `release_id`, blockers, and dependencies.
2. Primary release denominator excludes duplicates and cancelled records.
3. Milestone completion:
   - For each milestone in the release, count primary release work with that `milestone_id`.
   - `complete_primary` uses the complete status set.
   - `completion_pct = round(complete_primary / primary_total * 100, 1)`; use `0.0` for empty milestones.
   - Sort rows by `milestone_id` unless the template says otherwise.
4. Readiness score is total complete primary work divided by total primary denominator, rounded to three decimals.
5. Unresolved blockers have `resolved_at` null and a non-resolved status. High-impact blockers have severity `High` or `Critical`.
6. Count unresolved high-impact blocker causes by exact `cause` text for the release, including blockers attached to complete work.
7. Gating work item IDs are non-complete primary release items that have unresolved high-impact blockers or are blocked by critical non-complete dependencies. Sort unique IDs ascending.
8. Critical dependency chains:
   - Build directed paths from `blocked_id` to `depends_on_id`.
   - Start from primary release work.
   - Follow readiness-impacting relations such as `blocks-release-readiness`, `security-review-required`, `validation-required`, `audit-evidence-required`, and implementation dependencies when the prompt treats them as critical.
   - Stop at the first non-complete primary dependency and output the ordered ID path.
   - Do not treat duplicate or cancelled dependency records as primary non-complete blockers unless the prompt asks for data-quality reporting.
   - Sort chains lexicographically by the full path.
9. Ship decision:
   - `NO_SHIP` when unresolved high-impact blockers, gating work, or critical non-complete dependency chains remain.
   - `SHIP_WITH_WATCH` when no hard gate remains but lower-severity unresolved blockers, watch items, or incomplete non-gating work remain.
   - `SHIP` when primary release work is complete and no unresolved blockers or critical dependencies remain.

## JSON Assembly

- Match the answer template exactly: field names, nesting, enums, required keys, and array/object shapes.
- Preserve specified ordering rules even when JSON object order is not semantically important.
- Round only at the final metric step and use the precision requested by the template.
- Use `null` only when the template allows it.
- Do not include explanatory prose outside the JSON if the prompt asks for JSON only.
