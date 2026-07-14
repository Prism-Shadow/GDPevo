# Engineering Operations Review Solver

Use this skill for tasks that ask for engineering operations JSON reviews from a remote workspace API: portfolio work-mix reviews, reliability/security SLA aging snapshots, and release readiness or gating-risk rollups.

## Required Inputs

- Read the task prompt, `input/payloads/request_context.json`, and `input/payloads/answer_template.json`.
- Read `environment_access.md` when present and use its base URL in place of `<TASK_ENV_BASE_URL>`.
- Use the endpoint hints from the request context. Do not inspect environment source code, evaluator files, gold answers, previous runs, notes, or train-only judges.
- Return only JSON matching the answer template exactly: same keys, nesting, data types, bucket/category order, and no extra commentary.

## API Habits

- Most collection endpoints return an object with `count` and `results`; operate on `results`, not on the wrapper itself.
- Single-record endpoints, such as a release lookup, may return a bare object.
- URL-encode product names and quote URLs in shell commands.
- Check whether `count` matches the number of returned results. If it does not, retrieve the complete result set before computing.
- Treat the task `as_of_date` as the end of that calendar day. Never use today's date.
- Reconstruct item state from `/api/status-history` whenever history is available:
  - Group events by `work_item_id`.
  - Sort by `timestamp`.
  - The status as of the task date is the latest event with `timestamp <= as_of_date 23:59:59`.
  - Terminal statuses are `Closed`, `Done`, and `Verified`.
- Do not trust `status_export`, `closed_date`, or `updated_date` over status history. They can be stale or inconsistent.
- If a release-scoped item has no status-history row because it belongs to another product, fall back conservatively:
  - If `created_date` is after the as-of date, treat it as not started and incomplete.
  - If `closed_date <= as_of_date` and `status_export` is terminal, treat it as complete.
  - Otherwise use `status_export` as the best available current status.

## Work Category Mapping

Use `work_type` as the primary category source. Labels are only a fallback if a previously unseen work type appears.

- `NewFeature`: `Feature`, `Enhancement`, `Experiment`
- `TechDebt`: `Refactor`, `Migration`, `Cleanup`, `Platform`
- `Reliability`: `Reliability`, `Incident`, `Bug`
- `Security`: `Security`, `Vulnerability`, `Compliance`

When a work item has labels from multiple categories, prefer the `work_type` mapping.

## Portfolio Work-Mix Reviews

Use this procedure for quarterly portfolio mix or allocation follow-up tasks.

1. Fetch scoped work items, status history for the product, portfolio targets for the product and quarter, and teams.
2. Eligible work items are scoped items whose reconstructed status is terminal as of the review date. Do not require `status_export` to be terminal if history says the item completed. Do not collapse duplicate customer-signal records unless the prompt explicitly says to.
3. Sort `eligible_work_item_ids` ascending.
4. Count eligible items by mapped category using the template category order, usually `NewFeature`, `TechDebt`, `Reliability`, `Security`.
5. `actual_percentage` is `count / eligible_total * 100`, rounded to one decimal place. If the total is zero, use `0.0`.
6. `target_percentage` comes from `/api/portfolio-targets`.
7. `gap_basis_points` is the exact actual share minus target share in basis points: `round((count / eligible_total - target_percentage / 100) * 10000)`. If the total is zero, use `0`.
8. `under_invested_categories` are categories with negative gap basis points, in template category order.
9. `largest_negative_gap_category` is the category with the most negative gap; use `null` if no category is under target. Break ties by template order.
10. `follow_up_actions` contains one action per under-invested category, in template order, with `action: "IncreaseAllocation"` and `owner_team_id` set to the team whose `product_line` matches the scoped product.
11. `evidence_sample_ids` should contain the first three sorted eligible IDs per category. Include fewer than three when fewer exist. Only include all IDs if the prompt explicitly asks for full evidence.

Preserve the template's field spelling: some tasks use `bucket_rows`, others use `category_mix`, and some put product/quarter/date under a `scope` object.

## SLA Aging Reviews

Use this procedure for reliability and security aging snapshots.

1. Fetch product work items, product status history, SLA policies, owners, and teams.
2. Include only items mapped to `Reliability` or `Security`.
3. The included review population is:
   - items open as of the task date, meaning reconstructed status is non-terminal; plus
   - items whose first terminal transition is within the recent closed window.
4. The recent closed window is inclusive. For a 21-day window ending on the as-of date, the start date is `as_of_date - 20 days`.
5. Keep duplicate/original records auditable: include each work item separately in counts and ID lists.
6. For open items, `age_days = as_of_date - created_date`. For recently closed items, `age_days = terminal_date - created_date`. Use date differences, not inclusive day counts.
7. Match SLA policy by mapped category and severity. An item is overdue when `age_days > target_days`.
8. Sort `included_work_item_ids`, `overdue_work_item_ids`, and `missing_owner_work_item_ids` ascending.
9. Aging buckets (`0-7`, `8-14`, `15-30`, `31+`) are based on raw `age_days` for all included items, not just overdue days. Preserve the template's bucket shape: either an object such as `aging_bucket_counts` or an array such as `aging_buckets`.
10. `owner_hotspots` aggregate overdue included items with non-null `owner_id`. `team_hotspots` aggregate overdue included items by `team_id`. Each row uses `overdue_count` and the maximum raw `age_days` among that group's overdue items.
11. Sort hotspot rows by `overdue_count` descending, then `max_age_days` descending, then ID ascending. Include only groups with at least one overdue item.
12. `duplicate_clusters` or `duplicate_cluster_representatives` group included items with a non-null `duplicate_cluster`. Include every represented cluster. Use the lexicographically smallest included work item ID as `representative_work_item_id`, and put all included member IDs for that cluster in `member_ids`, sorted ascending.
13. `escaped_severity_count` is the count of included items with `escaped == true`, unless the prompt gives a stricter severity definition.
14. `missing_owner_work_item_ids` are included items with null or empty `owner_id`; do not also create an owner hotspot for `UNASSIGNED` unless the template explicitly asks for that.

## Release Readiness Rollups

Use this procedure for release go/no-go, release readiness, or gating-risk tasks.

1. Fetch the release record, milestones, milestone-items, release-scoped work items, status history for the main product, dependencies, active blockers, owners, and teams.
2. Build an item lookup from release-scoped work items. Milestone items should be evaluated even if some are cross-product; use the status fallback rules when product-scoped history is missing.
3. For each milestone:
   - Use all `/api/milestone-items` rows for the release.
   - Completion is `terminal_count / total_count * 100`, rounded to one decimal place.
   - Sort milestone output objects by `milestone_id` ascending.
4. Active blockers must be filtered as of the task date: `active == true`, `created_date <= as_of_date`, and no `resolved_date <= as_of_date`.
5. Normalize blocker causes to the template keys by removing spaces from `blocker_type`, for example `Security Review` -> `SecurityReview`. Initialize every blocker cause key shown in the template to zero.
6. Gating work items are release or milestone items that meet any of these conditions:
   - incomplete on a critical milestone;
   - have an active blocker as of the task date;
   - are incomplete and participate in a critical dependency chain relevant to the release.
7. Sort `gating_work_item_ids` ascending.
8. Build `critical_dependency_chain` from dependencies with `critical == true` whose endpoints are in the release or milestone scope. Order the list from upstream to downstream. Do not sort this list. If there are multiple chains, choose the longest chain that contains an unresolved or gated item; break ties lexicographically by the chain tuple.
9. `owner_escalation_ids` are the unique owner IDs for gated work items, sorted ascending. Include `UNASSIGNED` only if at least one gated item has a missing owner.
10. Count blocker causes for active blockers on release-scoped gated items.
11. Use the release `readiness_target` when present:
   - `Ship` / `Low`: no active blockers, no unresolved critical dependency chain, and all critical milestones meet or exceed the target.
   - `Hold` / `Medium`: no hard blockers, but readiness is below target or noncritical risk remains.
   - `NoShip` / `High`: active blockers, unresolved critical dependencies, or critical milestones below target at the as-of date.
   If the prompt gives explicit decision thresholds, those override these defaults.

## Output Conventions

- Keep arrays sorted ascending unless the template or prompt gives another order. The dependency chain is the main exception: preserve upstream-to-downstream order.
- Keep category and bucket rows in the exact order shown by the template.
- Use integers for counts and basis points.
- Use one-decimal numbers for percentages when the template asks for percentages.
- Use `null` only where the template uses `null` or the field definition requires it.
- Use empty arrays or zero-filled objects when there is no matching data.
- Do not include citations, markdown, explanatory prose, or fields absent from the template in the final answer.

## Common Pitfalls

- Treating `status_export` as authoritative even when status history shows a different as-of status.
- Forgetting to filter active blockers by the task as-of date; the active blocker endpoint can include blockers created after older review dates.
- Using a non-inclusive recent closed window.
- Using labels instead of `work_type` for primary categorization.
- Collapsing duplicate clusters before counting included work items.
- Computing SLA buckets from days overdue instead of raw item age.
- Counting null owners as owner hotspots instead of reporting them in `missing_owner_work_item_ids`.
- Sorting `critical_dependency_chain`; it must remain dependency ordered.
- Adding extra keys, changing template shapes, or returning prose around the JSON.
