---
name: engineering-ops-reviews
description: Solve Engineering Operations workspace review tasks that ask Codex to compute portfolio work-mix reviews, reliability/security SLA aging snapshots, and release readiness or gating rollups from workspace APIs. Use when prompts reference work items, status history, portfolio targets, SLA policies, milestones, releases, blockers, dependencies, owners, teams, as-of dates, quarters, recent closed windows, or exact JSON answer templates.
---

# Engineering Ops Reviews

## Core Workflow

1. Read the prompt, `request_context`, and answer template first.
2. Use the task-provided environment base URL and the endpoint hints from `request_context`; do not infer from local source files.
3. Fetch only the records needed for the requested scope. Common endpoints are work items, status history, portfolio targets, SLA policies, releases, milestones, milestone items, dependencies, blockers, owners, and teams.
4. Build the answer from the template shape exactly. Preserve key names, arrays vs objects, enum spelling, and any category/bucket order shown in the template.
5. Sort IDs ascending unless the template says not to, such as dependency chains.

Use `status_history` as the source of truth for as-of status. For each work item, take the latest history entry whose timestamp date is on or before the as-of date. Treat the as-of date as the end of that date. Fall back to `closed_date`/`status_export` only when there is no usable history for that work item.

Terminal statuses are `Closed`, `Done`, and `Verified`. Exclude `Cancelled` from completed-work calculations. Do not trust `status_export` when it conflicts with history.

## Category Mapping

Classify work into portfolio/SLA categories by work type first, with labels as backup:

- `Security`: `Vulnerability`, `Compliance`, `Security`, or labels such as `security`, `vulnerability`, `compliance`.
- `Reliability`: `Reliability`, `Incident`, `Bug`, or labels such as `reliability`, `slo`, `resiliency`, `capacity`, `incident`.
- `TechDebt`: `Migration`, `Refactor`, `Cleanup`, `Platform`, or labels such as `tech-debt`, `cleanup`, `migration`, `internal`, `platform`.
- `NewFeature`: `Feature`, `Enhancement`, `Experiment`, or feature/customer/workflow/growth labels.

When labels overlap, prefer the work-type intent. Security and Reliability take precedence over TechDebt for SLA aging.

## Portfolio Mix Reviews

For quarter/product portfolio reviews:

1. Fetch scoped work items, status history, portfolio targets, and teams.
2. Include scoped work items completed as of the review date. Completion means latest as-of status is terminal. Exclude open, blocked, in-progress, review, new, and cancelled items.
3. Use the broad scoped API population, including release/backlog records returned for the scope, unless the prompt explicitly excludes them.
4. Do not count duplicate customer-signal records in portfolio investment mix unless the task explicitly asks to include duplicate records.
5. Count completed items by category and compute actual percentages against the eligible total.
6. `gap_basis_points` is the actual percentage minus target percentage, multiplied by 100 and rounded to an integer.
7. `under_invested_categories` are categories with negative gaps, in the template's category order.
8. `largest_negative_gap_category` is the category with the most negative gap, or `null` if none.
9. `follow_up_actions` usually contains one `IncreaseAllocation` action for each under-invested category, using the product's owning team ID.
10. `evidence_sample_ids` should contain the first up to three eligible IDs in each category, sorted ascending.

Use one decimal for percentages when the template shows `0.0` or the prompt asks for one decimal. Keep target percentages as numeric values from the target endpoint.

## SLA Aging Reviews

For reliability/security aging snapshots:

1. Fetch work items, status history, SLA policies, owners, and teams.
2. Include work items in the target product whose category is Reliability or Security and whose created date is on or before the as-of date.
3. Include items that are open as of the date, plus items completed within the recent closed window. A recent closure is inclusive: `(as_of_date - completion_date).days <= recent_closed_window_days`.
4. Retain duplicate customer-signal records in the included population when the prompt asks for duplicate auditability or duplicate representatives.
5. Age in days is `(completion_date or as_of_date) - created_date` using date difference, not inclusive counting.
6. Buckets are `0-7`, `8-14`, `15-30`, and `31+`.
7. Use SLA policies by `(category, severity)` for target days. An item is overdue when `age_days > target_days`.
8. `owner_hotspots` group overdue items by non-null owner, with `overdue_count` and `max_age_days`; sort by descending overdue count, then owner ID.
9. `team_hotspots` group overdue items by team with the same max-age convention; sort by descending overdue count, then team ID.
10. `missing_owner_work_item_ids` are included items with null owner IDs, sorted ascending.
11. `escaped_severity_count` counts included items with `escaped: true` and severity `S1` or `S2`.

For duplicate cluster reporting, include only duplicate clusters represented in the included population. Use the lowest included work-item ID as `representative_work_item_id`; put all included member IDs in ascending order.

## Release Readiness Rollups

For release readiness/gating tasks:

1. Fetch the release, milestones, milestone items, release work items, product status history, dependencies, active blockers, owners, and teams.
2. Compute milestone completion from all milestone item links. A linked item is complete only if its latest as-of status is terminal; for cross-product items without history, fall back to `closed_date`/terminal export when the close date is on or before the as-of date.
3. Sort milestone objects by `milestone_id` and round `completion_percentage` to one decimal.
4. Filter blockers to active blockers created on or before the as-of date, unresolved as of that date, whose `work_item_id` is in the release work-item set.
5. `gating_work_item_ids` are the sorted release work item IDs with active blockers. Do not replace this with all incomplete critical-milestone items.
6. Normalize blocker cause names by removing spaces to match keys such as `SecurityReview`, `DesignDecision`, and `ExternalDependency`; include zeroes for all template keys.
7. `critical_dependency_chain` should follow critical dependencies upstream to downstream. Use a longest relevant critical path intersecting the release, and do not sort the returned chain.
8. `owner_escalation_ids` are owners of gating work items, sorted ascending. Include `UNASSIGNED` only if a gating item has no owner.

Decision convention:

- `Ship`: readiness is at or above target and there are no active gating blockers.
- `Hold`: before the release date, active blockers or incomplete gates prevent a clear ship decision.
- `NoShip`: on or after the release date, unresolved gating blockers or materially incomplete critical gates remain.
- `High` risk: active gating blockers, severe unresolved blockers, or failed critical milestones.
- `Medium` risk: below readiness target or non-critical concerns without hard gates.
- `Low` risk: no blockers and readiness is on target.

## Output and Exclusion Rules

- Return JSON only for solver tasks.
- Never add explanatory fields, markdown, citations, or comments.
- Match template-specific names exactly, such as `bucket_rows` vs `category_mix`, `aging_bucket_counts` vs `aging_buckets`, and `duplicate_clusters` vs `duplicate_cluster_representatives`.
- Preserve fixed category and bucket order from the template.
- Use `null` only where the template uses `null`; otherwise use empty arrays or zeroes as shown.
- Do not use any feedback or training-only endpoint while solving test tasks.
