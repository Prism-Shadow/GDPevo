---
name: engineering-portfolio-analysis
description: Analyze engineering portfolio environments for exact JSON portfolio mix reviews, SLA aging audits, and release-readiness assessments. Use when a task provides a shared environment with work-item, mix-target, SLA-policy, release, blocker, dependency, or milestone APIs and asks for duplicate/cancelled exclusions, stale mirror-field handling, portfolio category classification, SLA breach calculations, or release readiness scoring.
---

# Engineering Portfolio Analysis

## Core Workflow

1. Read the user prompt, `environment_access.md`, and the requested answer template before calculating.
2. Replace `<TASK_ENV_BASE_URL>` with the base URL from `environment_access.md`.
3. Fetch only the documented endpoints needed for the task. Use `GET /api/work-items` for broad filtering and per-item endpoints only to verify specific records. Use `POST /api/query` only when direct endpoints are insufficient, and include the documented `X-Env-Token` header.
4. Treat the answer template as the output contract. Match required keys, ordering notes, enum values, rounding, and whether arrays are sorted by ID, date, category order, or priority.
5. Return only the JSON object unless the prompt explicitly allows prose.

## Authoritative Fields

- Use `status`, `created_at`, `closed_at`, `due_at`, `duplicate_of`, `team`, `product_area`, `work_type`, `labels`, `title`, `owner`, `severity`, `priority`, `release_id`, and `milestone_id` as source-of-truth fields.
- Ignore stale mirror/export fields such as `mirror_status` for state and `legacy_category` for portfolio category.
- Treat labels such as `stale-export` and `papertrail` as metadata, not category signals.
- Use these complete statuses when a task asks whether work is complete: `Closed`, `Done`, `Verified`, and `Deployed`.
- Treat `Duplicate`, any non-null `duplicate_of`, and `Cancelled` as non-primary records unless the output template asks to report them as exclusions or duplicate clusters.

## Primary Records And Exclusions

- A primary work item has `status` other than `Duplicate` or `Cancelled` and `duplicate_of == null`.
- A duplicate record is any item with `status == "Duplicate"` or a non-null `duplicate_of`. Report it in duplicate exclusions or clusters when it otherwise matches the task scope.
- A cancelled record is excluded from primary counts and reported separately when the template has a cancelled/distractor field.
- Build duplicate clusters as `{primary_id, duplicate_ids}` using `duplicate_of` as the canonical id; sort cluster primary ids and duplicate ids lexicographically unless the template says otherwise.

## Portfolio Category Resolver

Assign every primary portfolio item to exactly one category using this precedence. Check `work_type`, labels, and meaningful title tokens; do not use `legacy_category`.

1. `Security`: `work_type` is `Security` or `Compliance`, or labels/title contain security signals such as `security`, `auth`, `encryption`, `cve`, or `compliance`.
2. `Reliability`: `work_type` is `Reliability`, `Incident`, or `Bug`, or labels/title contain reliability signals such as `reliability`, `incident`, `outage`, `latency`, or `flaky`.
3. `TechDebt`: `work_type` is `Refactor`, `Dependency`, or `Chore`, or labels/title contain tech-debt signals such as `refactor`, `cleanup`, `migration`, or `dependency`.
4. `NewFeature`: `work_type` is `Feature` or `Enhancement`, or labels/title contain feature signals such as `feature`, `rollout`, or `customer-request`.

If signals conflict, keep the first category in the precedence list.

## Portfolio Mix Reviews

1. Parse the requested quarter, teams, product areas, and target `scope_id`.
2. Include primary work whose `team` and `product_area` are in scope, whose `closed_at` falls inside the requested quarter, and whose `status` is a complete status.
3. Order included ids by `closed_at` ascending then id ascending unless the template requires a different stable order.
4. Fetch the mix-target row by the requested `scope_id` when present. Target fields are fractions; convert them to percentage points before comparing.
5. Count included items by resolved category, not story points.
6. Compute actual percentage as `category_count / total_included * 100`, rounded as requested. Compute gap as `actual_pct - target_pct`.
7. List under-invested categories where gap is negative, ordered from most negative to least negative.
8. For rebalance recommendations, choose the largest negative gap as the primary category. If a secondary category is requested, use the next largest negative gap. Use a maintain-current-mix action only when there are no negative gaps, and a data-quality action only for unresolved scope/category conflicts.

## SLA Aging Audits

1. Parse scoped teams, category list, as-of date, and recent closed window.
2. Resolve each work item category with the portfolio category resolver, then keep scoped primary items whose category is in the SLA category list.
3. Include open primary items active as of the as-of date and primary items closed within the recent window ending on the as-of date. Use an inclusive window start of `as_of - recent_closed_window_days`.
4. For age calculations, use `as_of - created_at` for open items and `closed_at - created_at` for recently closed items.
5. Bucket age in days as `0-3`, `4-7`, `8-14`, `15-30`, and `31+`.
6. Mark an open item overdue when `due_at < as_of`. Mark a closed item overdue when `closed_at > due_at`.
7. Sort id lists lexicographically unless the template asks for an escalation queue.
8. For team overdue counts, group overdue primary records by team and sort teams alphabetically.
9. For owner/team hotspots, group by `(team, owner)`, using `UNASSIGNED` for missing owners. Choose the largest overdue count and break ties deterministically by team then owner.
10. Compute breach rate as `overdue_primary_count / included_primary_count`, rounded to the template precision.
11. For escalation queues, sort overdue primary work by severity rank `S1`, `S2`, `S3`, `S4`, then by earliest `due_at`, then lower numeric `priority`, then id.

## Release Readiness

1. Fetch releases, milestones, work items, blockers, and dependencies. Identify the requested release and its milestones from authoritative release and milestone data.
2. Build primary release work from work items assigned to the release or one of its milestones, excluding duplicate and cancelled records.
3. For each release milestone, count primary work assigned to that milestone. `complete_primary` is the count with a complete status; `primary_total` excludes duplicate and cancelled work. Sort milestone rows by milestone id and round completion percentages as requested.
4. Compute readiness score as total complete primary release work divided by total primary release work, rounded to the template precision.
5. Count unresolved high-impact blockers for the requested release where `resolved_at == null`, status is not resolved, and severity is `High` or `Critical`. Key counts by exact `cause` text.
6. Do not list every incomplete release item as gating by default. Gating ids are non-complete primary release items that have unresolved high-impact blockers or are blocked by a critical dependency chain.
7. Build critical dependency chains from dependency relations that indicate readiness, validation, security review, or audit evidence risk. Start from blocked primary release work, follow dependencies in order, ignore duplicate/cancelled terminal records, and include only chains that end at a non-complete primary dependency. Sort chains lexicographically by the full id path.
8. Use `NO_SHIP` when non-complete gating work or unresolved high-impact release blockers remain. Use `SHIP_WITH_WATCH` when no hard gate remains but incomplete primary work or unresolved lower-impact blockers still need monitoring. Use `SHIP` only when primary work is complete and no unresolved release blockers remain.

## Final Checks

- Re-read the template before finalizing to verify all required fields are present and no extra fields are included.
- Verify rounding by doing arithmetic from raw counts, not from previously rounded percentages.
- Verify duplicate/cancelled ids were not counted in primary denominators.
- Verify output ordering exactly matches the prompt or template.
