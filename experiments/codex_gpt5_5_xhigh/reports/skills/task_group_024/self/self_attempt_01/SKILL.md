---
name: engineering-ops-review
description: Solve engineering operations workspace JSON review tasks using remote API records, including portfolio work-mix reviews, reliability/security SLA aging snapshots, and release readiness risk rollups.
---

# Engineering Ops Review

Use this skill when a task asks for an engineering operations review JSON from a remote workspace API. Typical variants are portfolio work-mix, reliability/security SLA aging, and release readiness/gating rollups.

## Ground Rules

- Read the task prompt, `input/payloads/request_context.json`, and `input/payloads/answer_template.json` first.
- Read `environment_access.md` when present and use its base URL in place of `<TASK_ENV_BASE_URL>`.
- Use only public workspace API records and task input payloads. Do not inspect local environment source, evaluator files, gold answers, notes, previous runs, or a train-only judge.
- Return exactly one JSON object matching the answer template. Do not add markdown, comments, citations, or extra keys.
- Preserve the template's field names and container shape. If a template uses `bucket_rows`, use that; if it uses `category_mix`, use that. Do not normalize names across tasks.

## API Habits

- Endpoint responses usually have `{ "count": n, "results": [...] }`; singleton endpoints such as `/api/releases/{id}` may return the object directly.
- URL-encode product names in query strings.
- Prefer endpoint hints from `request_context.json`, but fetch related records needed to make hinted records coherent, such as per-work-item status history for release items missing from a product-scoped status-history response.
- Treat `status_history` as authoritative for as-of questions. `status_export` and `closed_date` can be stale or inconsistent.
- Reconstruct as-of status by sorting status events by timestamp and taking the last event at or before `as_of_date 23:59:59`.
- Exclude records with `created_date` after the as-of date from as-of populations.

Status conventions:

- Completed statuses: `Closed`, `Done`, `Verified`.
- Active statuses: `New`, `In Progress`, `Review`, `Blocked`.
- `Cancelled` is not completed delivery. Do not count it as completed portfolio/SLA work; in release readiness, keep it as a risk if it remains linked to an as-of milestone or critical dependency.

## Work Category Mapping

Assign each work item to one business category. Use `work_type` first:

- `NewFeature`: `Feature`, `Enhancement`, `Experiment`
- `TechDebt`: `Cleanup`, `Migration`, `Refactor`, `Platform`
- `Reliability`: `Reliability`, `Incident`, `Bug`
- `Security`: `Security`, `Compliance`, `Vulnerability`

If an unseen `work_type` appears, use labels/title/description as a fallback. Feature/customer/growth/workflow terms imply `NewFeature`; cleanup/migration/refactor/tech-debt/platform terms imply `TechDebt`; reliability/resiliency/SLO/incident/capacity terms imply `Reliability`; security/compliance/vulnerability/audit terms imply `Security`.

## Portfolio Work-Mix Reviews

Use this flow for quarter-end portfolio mix prompts.

1. Fetch scoped work items, product status history, portfolio targets, and teams.
2. Eligible work items are scoped to the requested product and quarter, created on or before the as-of date, and completed as of the as-of date.
3. Sort `eligible_work_item_ids` ascending and set `eligible_total` to their count.
4. Count eligible items by business category in the template/category order, usually `NewFeature`, `TechDebt`, `Reliability`, `Security`.
5. `actual_percentage` is `count / eligible_total * 100`, rounded to one decimal. Use `0.0` if the denominator is zero.
6. `target_percentage` comes from `/api/portfolio-targets`.
7. `gap_basis_points` is the actual percentage gap from target, in basis points, rounded to the nearest integer. Use the raw count share for the gap; `actual_percentage` is only the displayed one-decimal value.
8. `under_invested_categories` are categories with negative gap basis points, ordered by the template/category order.
9. `largest_negative_gap_category` is the category with the smallest gap basis points; use `null` when there are no negative gaps. Break ties by category order.
10. `follow_up_actions` contains one action per under-invested category, ordered by category order: `{ "category": category, "action": "IncreaseAllocation", "owner_team_id": product_team_id }`. Resolve `product_team_id` from `/api/teams.product_line`.
11. `evidence_sample_ids` maps every category to up to the first three eligible item IDs in that category, sorted ascending. Use empty arrays for categories without evidence.

Do not include incomplete work, work completed after the as-of date, or work from other quarters just because it belongs to a related release.

## Reliability/Security SLA Aging

Use this flow for SLA aging snapshots.

1. Fetch product work items, product status history, SLA policies, owners, and teams.
2. Classify items by business category and include only `Reliability` and `Security`.
3. Include an item when it was created on or before the as-of date and either:
   - it is active as of the as-of date, or
   - it reached a completed status inside the recent closed window.
4. A recent closed window of `N` days inclusive starts at `as_of_date - (N - 1) days` and ends on `as_of_date`. Completion on either boundary counts.
5. For active items, `end_date = as_of_date`. For recently completed items, `end_date` is the date of the completed status transition.
6. `age_days = end_date - created_date` as a date difference. Do not add one.
7. An item is overdue when `end_date > due_date`. If `due_date` is missing, derive it from `created_date + target_days` using `/api/sla-policies` by category and severity.
8. `included_work_item_ids` and `overdue_work_item_ids` are sorted ascending. Populate `included_count` and `overdue_count` only when those fields exist in the template.
9. Aging buckets count all included items by `age_days`: `0-7`, `8-14`, `15-30`, `31+`. Use the template shape, either an object such as `aging_bucket_counts` or an array such as `aging_buckets`.
10. `owner_hotspots` group overdue included items with a non-null `owner_id`. `team_hotspots` group overdue included items with a non-null `team_id`.
11. Hotspot rows contain `overdue_count` and `max_age_days` using the same `age_days` definition. Sort by `overdue_count` descending, then `max_age_days` descending, then ID ascending.
12. `missing_owner_work_item_ids` is every included item with null/missing `owner_id`, sorted ascending.
13. `escaped_severity_count` is the count of included items where `escaped` is true.
14. Duplicate cluster output includes clusters represented in the included population. For each cluster, sort included member IDs ascending, choose the first as `representative_work_item_id`, and put the sorted included IDs in `member_ids`. Sort clusters by `cluster_id`.

Do not de-duplicate the included population for counts. Duplicate clusters are reported for audit, but original work items remain countable records.

## Release Readiness Rollups

Use this flow for release readiness and gating risk tasks.

1. Fetch release metadata, milestones, milestone-items, release work items, status history, dependencies, active blockers, owners, and teams.
2. Build the release work-item map from `/api/work-items?release_id=...`. For as-of calculations, exclude work items created after the as-of date.
3. Reconstruct each release work item's as-of status from status history. Fetch per-work-item history if a release item is outside the product-scoped history.
4. Milestone completion:
   - For each milestone, use as-of milestone member work items only.
   - Numerator: members whose as-of status is `Closed`, `Done`, or `Verified`.
   - Denominator: all as-of members linked to that milestone.
   - `completion_percentage` is rounded to one decimal.
   - Sort milestone objects by `milestone_id` ascending and copy each milestone's `critical` boolean.
5. Active blockers:
   - Use blockers with `active: true`, `created_date <= as_of_date`, and no `resolved_date` on or before the as-of date.
   - Count only blockers attached to as-of release items or gated dependency-chain items.
   - Normalize blocker types by removing spaces to match keys such as `ExternalDependency`, `SecurityReview`, and `OwnershipGap`.
   - Initialize every blocker cause key shown in the template to zero.
6. Critical dependency chain:
   - Use dependencies with `critical: true`.
   - Direction is `upstream_id -> downstream_id`; output IDs in dependency order and do not sort the final chain.
   - Choose the longest critical path that intersects the release as-of graph. Include external release-linked nodes when they are in the critical path.
   - Return `[]` when no critical path is present.
7. Gating work items are the sorted union of:
   - incomplete items on critical milestones,
   - items with active blockers,
   - incomplete items labeled `release-gate` or `critical-path`,
   - incomplete or cancelled items on the critical dependency chain.
8. `owner_escalation_ids` are owners of gated items, sorted ascending. Include `UNASSIGNED` only when a gated item has no owner.
9. `risk_tier` and `ship_decision` should follow the evidence:
   - `Low` and `Ship`: no gating items, no active blockers, all critical milestones meet the release `readiness_target`.
   - `Medium` and `Hold`: non-critical gaps or moderate readiness misses without hard blockers.
   - `High` and `NoShip`: active blockers on release/gated work, incomplete critical milestones below target, or unresolved critical dependency-chain risk.

Do not use current `status_export` alone for readiness. A release item can look closed in export data while its as-of history is still blocked, or vice versa.

## Output Discipline

- Copy literal scope fields from the prompt/context/template: product, quarter, release ID, as-of date, and recent window days.
- Use empty arrays for no rows, zero counts for no matches, and `null` only where the template shows nullable scalar intent.
- Keep all ID lists sorted ascending unless the template explicitly says not to sort, as with `critical_dependency_chain`.
- Keep numeric types stable: percentages as JSON numbers, counts and basis points as integers.
- Validate the final JSON with a parser before returning it.
