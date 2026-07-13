---
name: engineering-ops-json-reviews
description: Solve engineering operations workspace API tasks that require exact JSON reviews for portfolio work mix, SLA aging, release readiness, blocker/gating risk, work-item status history, owners, teams, dependencies, and duplicate clusters. Use when prompts provide an engineering ops base URL placeholder, request_context endpoint hints, and an answer_template JSON shape.
---

# Engineering Ops JSON Reviews

## Core Workflow

1. Read the prompt, `request_context.json`, and `answer_template.json`.
2. Read `environment_access.md` for the remote base URL and replace `<TASK_ENV_BASE_URL>`.
3. Fetch only the endpoints needed from the context hints. Normalize API responses shaped as `{count, results}` to the `results` array.
4. Build indexes by `work_item_id`, `owner_id`, `team_id`, milestone, blocker, dependency, and duplicate cluster.
5. Use status history as the source of truth. Treat `status_export` and `closed_date` as hints/fallbacks only.
6. Return JSON only, with exactly the template keys, field names, array-vs-object choices, and scalar types. Remove placeholder objects when there are no rows.

Use `Closed`, `Done`, and `Verified` as complete terminal statuses. Treat `Cancelled` as excluded from completion denominators and eligible populations unless the task explicitly says otherwise. Treat `Blocked`, `Review`, `In Progress`, and `New` as incomplete/open.

## Status And Dates

- Sort status history by timestamp per work item.
- For an as-of calculation, use the last event at or before the as-of date unless the field is a release milestone lifecycle completion, where the task family expects the visible lifecycle status and excludes only cancelled milestone items.
- For work-item closure, use the terminal status event date when present. Fall back to `closed_date` only if status history is unavailable.
- For a recent-closed window of `N` days, include closed items whose terminal date satisfies `0 <= as_of_date - terminal_date <= N`; this includes items closed exactly `N` days before the as-of date.
- Age in days is a plain date difference: terminal date minus created date for recently closed included items; as-of date minus created date for items still open as of the review.

## Category Inference

Infer one portfolio/SLA category per work item from labels, work type, title, and description. Prefer explicit labels over `work_type`; use this priority:

1. `Security`: labels or work types such as `security`, `vulnerability`, `compliance`, credential, access-control, audit evidence, token/credential rotation, token refresh, or security review.
2. `Reliability`: `reliability`, `reliability-review`, `incident`, `slo`, `resiliency`, `capacity`, failover, timeout, cache, latency, or work types `Reliability`, `Incident`, `Bug`.
3. `TechDebt`: `tech-debt`, `cleanup`, `migration`, `platform`, `refactor`, modernization, or related work types.
4. `NewFeature`: `feature`, `enhancement`, `experiment`, `customer`, `growth`, `workflow`, or product-delivery work types.

Security overrides reliability when both appear. Reliability overrides tech debt. For duplicate customer-signal records without explicit `security` or `reliability` labels, infer from the signal/work type: vulnerability/compliance/token/audit signals are security; incident/failover/cache/timeout signals are reliability.

## Portfolio Mix Reviews

Use the scoped `/api/work-items?...product...quarter...`, `/api/status-history?...`, `/api/portfolio-targets?...`, and `/api/teams` records.

Eligibility:

- Include scoped work items that reached `Closed`, `Done`, or `Verified` on or before the as-of date.
- Exclude cancelled items and items that have not reached a complete terminal status by the as-of date.
- Sort eligible IDs ascending.

Calculations:

- Count eligible items by category in the category order shown by the template or target records.
- `actual_percentage` = round `count / eligible_total * 100` to one decimal place. Use a JSON integer when the rounded value is whole.
- `gap_basis_points` = `(actual_percentage - target_percentage) * 100`, rounded to an integer.
- `under_invested_categories` contains categories at least 500 basis points below target (`gap_basis_points <= -500`), in category/template order.
- `largest_negative_gap_category` is the category with the most negative gap, even if it is inside the 500 bps tolerance. Use `null` only when there is no negative gap.
- `follow_up_actions` contains one `{category, action: "IncreaseAllocation", owner_team_id}` row per under-invested category. Use the product-line team ID from `/api/teams`. If no category breaches the threshold, output `[]`.
- `evidence_sample_ids` contains up to the first three sorted eligible work item IDs per category.

Respect template naming differences: some tasks use `bucket_rows`, others use `category_mix`; some place product/quarter/as-of under `scope`.

## SLA Aging Reviews

Use the product work-items, status history, SLA policies, owners, and teams.

Included population:

- Include reliability and security category work items created on or before the as-of date.
- Include open items as of the as-of date.
- Include completed items only if they closed within the recent-closed window.
- Exclude cancelled items and items completed before the recent window.
- Include duplicate customer-signal cluster members when they are in the included population; do not collapse them out of the audit population.

SLA and aging:

- Pick the SLA policy by inferred category and severity.
- An item is overdue only when `age_days > target_days`; equality is not overdue.
- Aging buckets count all included items, not only overdue items:
  - `0-7`
  - `8-14`
  - `15-30`
  - `31+`

Output conventions:

- Sort `included_work_item_ids`, `overdue_work_item_ids`, and `missing_owner_work_item_ids` ascending.
- Populate `included_count` and `overdue_count` only when those fields exist in the template.
- Build owner hotspots from overdue items with a non-null owner. Group by owner, count overdue items, and set `max_age_days` to the maximum raw age among that owner’s overdue items.
- Build team hotspots from all overdue items, including missing-owner items.
- Sort hotspots by `overdue_count` descending, then `max_age_days` descending, then ID ascending.
- `missing_owner_work_item_ids` contains overdue included items with no owner.
- `escaped_severity_count` counts included items where `escaped` is true.
- Duplicate clusters include each cluster with at least two included members. Sort clusters by `cluster_id`; use the lowest sorted member ID as `representative_work_item_id`; sort `member_ids`.

Respect template variants: `aging_bucket_counts` may be an object, while `aging_buckets` may be an array of `{bucket, count}`. Duplicate rows may be named `duplicate_clusters` or `duplicate_cluster_representatives`.

## Release Readiness Reviews

Use release metadata, milestones, milestone items, release-scoped work items, status history, dependencies, active blockers, owners, and teams.

Milestones:

- Group `/api/milestone-items` by milestone.
- Exclude cancelled milestone items from the denominator.
- Count `Closed`, `Done`, and `Verified` items as complete using status history when available; fall back to exported status only when necessary.
- `completion_percentage` = round `complete / denominator * 100` to one decimal place. Use `0` if the denominator is zero.
- Sort milestone rows by `milestone_id` ascending and preserve the `critical` flag from `/api/milestones`.

Gating and blockers:

- `gating_work_item_ids` are release-associated work items with active blockers. Include items associated by `release_ids` or by milestone membership. Sort ascending.
- Count blocker causes only for gating items. Normalize blocker type keys by removing spaces, e.g. `Security Review` -> `SecurityReview`, `External Dependency` -> `ExternalDependency`.
- Emit all cause keys shown in the template, with zero for absent causes.
- `owner_escalation_ids` is the sorted set of owner IDs for gating items. Add `UNASSIGNED` only when a gating item has no owner.

Dependencies:

- Build dependency edges from `upstream_id` to `downstream_id`.
- For `critical_dependency_chain`, output IDs in dependency order, never sorted alphabetically.
- Prefer the longest chain that involves a gating item and incomplete release/milestone item; prioritize `blocks` and `requires` edges. If no relevant chain exists, output `[]`.

Decision fields:

- Use `NoShip` and `High` when active gating blockers exist or a critical release gate is blocked.
- Use `Hold` and usually `Medium` when no hard blocker exists but readiness is below the release target or critical milestones remain incomplete.
- Use `Ship` and `Low` only when there are no active gating blockers and readiness meets the release target.

## General Output Rules

- Preserve IDs exactly as strings.
- Sort ordinary ID lists lexicographically ascending unless the template says not to sort.
- Do not add explanations, markdown, citations, comments, or extra keys.
- Do not leave template placeholder rows such as `OWNER-ID`, `TEAM-ID`, or enum examples in the output.
- Use `[]` for empty arrays and `null` only where the template expects a nullable scalar.
- Validate the final object by comparing its keys and container types to `answer_template.json` before responding.
