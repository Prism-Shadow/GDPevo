---
name: engineering-portfolio-env
description: Solve engineering portfolio task-environment audits that require exact JSON answers from work-item APIs, including portfolio mix, SLA aging and breach-rate analysis, duplicate handling, release readiness, milestones, blockers, dependencies, and ship decisions. Use when prompts mention the task environment base URL placeholder, mix targets, SLA policy, releases, milestones, work items, blockers, or dependencies.
---

# Engineering Portfolio Environment

Use this skill to solve JSON-only audit tasks over the shared engineering portfolio environment. Always treat the prompt and its `input/payloads/answer_template.json` as the output contract.

## First Pass

1. Read the prompt, the answer template, and the runtime access notes.
2. Resolve the base URL and fetch the necessary API data. If endpoint filters are unreliable, fetch the allowed endpoint and filter locally.
3. Normalize records before calculating: use `status`, `closed_at`, `created_at`, `due_at`, `duplicate_of`, `team`, `product_area`, `work_type`, `labels`, `severity`, `owner`, `release_id`, and `milestone_id` as the primary fields.
4. Ignore stale mirror/export fields such as `mirror_status` for status, completion, and inclusion. Do not let `legacy_category` override current work-type, label, and title evidence.
5. Return exactly one JSON object matching the template. Preserve required keys, requested ordering, numeric precision, and enum spellings. Do not add prose.

For detailed calculation rules, read [references/calculation-rules.md](references/calculation-rules.md).

## Optional Helper

Use [scripts/env_fetch.py](scripts/env_fetch.py) to fetch the environment with only the Python standard library:

```bash
python skill/scripts/env_fetch.py --base-url "$TASK_ENV_BASE_URL" --out /tmp/env.json
python skill/scripts/env_fetch.py --base-url "$TASK_ENV_BASE_URL" --ids WI-... WI-... --out /tmp/items.json
```

The helper also exposes reusable functions for category classification, primary-record checks, completion checks, quarter bounds, age buckets, and rounding. Read or import it when deterministic mechanics are more reliable than retyping them.

## Portfolio Mix Tasks

Filter work items to the prompted quarter, teams, and product area or areas. Include only primary closed portfolio work: a work item must be in a completed status, have a `closed_at` date in the quarter, and not be cancelled or a duplicate. Treat any record with `status == "Duplicate"` or non-null `duplicate_of` as a duplicate even if another status field looks closed.

Classify each included item into exactly one portfolio category using the conventions in the reference. Count items, not story points. Convert mix-target fractions to percentage points before comparison. Calculate:

- `actual_pct = count / total * 100`, rounded to one decimal place.
- `gap_pct = actual_pct - target_pct`, rounded to one decimal place.
- Under-invested or deficit categories are categories with negative gaps, ordered from most negative to least negative.

Sort included IDs by `closed_at` ascending, then `id` ascending unless the template says otherwise. Sort duplicate and cancelled exclusions by the ordering requested in the template.

When a controlled rebalance action is required, choose `REBALANCE_CAPACITY` for negative gaps. Use the largest negative gap as the primary category. If the template asks for a secondary category, use the next negative gap or `null` when none exists. If the template asks for an owner team, select the team most directly associated with the deficit category in the scoped evidence, breaking ties by prompt order.

## SLA Aging Tasks

Filter to prompted teams and SLA-relevant categories. Include primary work that is currently open, plus primary work closed inside the recent closed window. The recent window is inclusive of the as-of date and the date `window_days` before it.

An item is overdue when:

- It is open as of the as-of date and `due_at` is before the as-of date.
- It closed in the recent window and `closed_at` is after `due_at`.

For age buckets, measure age in calendar days from `created_at` through `min(closed_at, as_of)`. Use buckets `0-3`, `4-7`, `8-14`, `15-30`, and `31+` with inclusive endpoints.

Report duplicate clusters separately and never count duplicates as primary work. Missing owners are primary included items with `owner` null or empty. Use `UNASSIGNED` for missing-owner hotspot labels when the template asks for an owner name.

Calculate breach rate as overdue primary count divided by included primary count, rounded to three decimals. For escalation queues, sort overdue primary work by severity order `S1`, `S2`, `S3`, `S4`, then `due_at` ascending, then `id` ascending unless the prompt gives a different priority rule.

## Release Readiness Tasks

Use release and milestone endpoints as release truth; do not use mirror fields. Fetch the release, its milestones, release work items, blockers, and dependency records.

Primary release work excludes duplicates and cancelled records. Completed statuses are `Closed`, `Done`, `Verified`, and `Deployed`. Non-complete statuses include `Backlog`, `In Progress`, `Review`, `Blocked`, and `Reopened`.

For each milestone, count completed primary work and total primary work assigned to that milestone. Sort milestone rows by `milestone_id` ascending and round completion percentages to one decimal place. The release readiness score is completed primary work divided by total primary work, rounded to three decimals.

For blockers, count unresolved high-impact blockers only: `resolved_at` is null and blocker severity is `High` or `Critical`. Key blocker counts by exact cause text. Gating work item IDs are non-complete primary release work items with unresolved high-impact blockers, sorted ascending.

For dependency chains, start from blocked release work and follow dependency edges to non-complete dependencies. Emit ordered ID paths from the blocked release item to the non-complete dependency, omit paths that end in completed work, de-duplicate paths, and sort paths lexicographically.

Use `NO_SHIP` when gating work or unresolved critical/high-impact readiness blockers remain. Use `SHIP_WITH_WATCH` when no hard gate remains but incomplete or lower-impact risk remains. Use `SHIP` only when primary release work is complete and no unresolved readiness blocker or dependency risk remains.
