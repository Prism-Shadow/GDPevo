---
name: portfolio-env-review
description: Use when answering engineering portfolio environment tasks that require JSON-only portfolio mix, SLA aging, or release readiness analysis from work item, mix target, SLA, release, milestone, blocker, dependency, and restricted SQL endpoints.
---

# Portfolio Environment Review

Use this skill for tasks that ask for a structured JSON answer from the shared engineering portfolio environment. The common task families are portfolio-mix reviews, SLA aging audits, and release-readiness assessments.

## Core Workflow

1. Read the user prompt, every file in the current task input payloads, and the answer template/schema before querying data.
2. Read the runtime access file for the environment base URL, token, and allowed endpoints. Do not hardcode training-run values.
3. Fetch authoritative data from the API. Prefer endpoint JSON for full objects; use `POST /api/query` with body `{"sql": "SELECT ..."}` for focused filters or joins. The query endpoint accepts only SELECT statements and returns `columns`, `rows`, `row_count`, and `truncated`.
4. Treat `work_items.status`, `closed_at`, `duplicate_of`, `release_id`, `milestone_id`, labels, and `work_type` as authoritative. Ignore `mirror_status` and `legacy_category` for truth unless the prompt explicitly asks to audit stale fields.
5. Build the requested answer from current environment data, then validate it exactly against the provided template: required keys, enum values, ordering, rounding precision, and JSON-only output.

## Work Item Conventions

Primary work item:
- `duplicate_of` is null.
- `status` is not `Duplicate`.
- `status` is not `Cancelled`.

Complete status:
- `Closed`, `Done`, `Verified`, or `Deployed`.

Non-complete status:
- Any status outside the complete set, after excluding duplicate/cancelled records where the task asks for primary work.

Duplicate records:
- Any item with `duplicate_of` populated or `status == "Duplicate"`.
- Group duplicate clusters by `duplicate_of`; sort primary IDs and duplicate ID lists lexicographically unless the template says otherwise.

Date handling:
- Parse dates as calendar dates.
- For a quarter like `YYYY-Qn`, include dates from the first day of that quarter through the day before the next quarter.
- For "recent closed window N days", include closed work where `as_of - N days <= closed_at <= as_of`.

## Portfolio Category Classification

When a task asks for portfolio categories and no authoritative category field exists, classify from current `work_type`, current `labels`, and title tokens. Do not use `legacy_category`.

Apply this precedence, stopping at the first match:

1. `Security`: `work_type` is `Security` or `Compliance`, or tokens include `security`, `cve`, `auth`, `encryption`, or `compliance`.
2. `Reliability`: `work_type` is `Reliability`, `Incident`, or `Bug`, or tokens include `reliability`, `incident`, `outage`, `latency`, `flaky`, `bug`, `crash`, or `retry`.
3. `TechDebt`: `work_type` is `Refactor`, `Chore`, or `Dependency`, or tokens include `refactor`, `cleanup`, `migration`, `migrate`, `deprecate`, `dependency`, `chore`, or `contract`.
4. `NewFeature`: `work_type` is `Feature` or `Enhancement`, or tokens include `feature`, `rollout`, `launch`, `experiment`, `dashboard`, or `polish`; otherwise use `NewFeature` as the fallback category.

For percentage mix:
- Count items, not story points, unless the prompt says otherwise.
- Category order is usually `NewFeature`, `TechDebt`, `Reliability`, `Security`.
- `actual_pct = count / total * 100`, rounded to one decimal place.
- Mix targets are stored as fractions; multiply by 100 for percentage points.
- `gap_pct = actual_pct - target_pct`, rounded to one decimal place.
- Under-invested categories have negative gaps; order them from most negative to least negative.

For portfolio exclusions:
- Included mix items are in-scope, closed in the requested date range, primary records.
- Exclusion lists usually contain in-scope duplicate and cancelled records that otherwise match the same date/scope filters.
- If the template separates duplicates from cancelled records, put duplicate records with duplicate flags in the duplicate list and cancelled records in the cancelled list.

For rebalance recommendations:
- If any category has a negative gap, recommend rebalancing toward the category with the largest negative gap; use the next negative category as secondary when the template asks for one.
- If there are no negative gaps, return the template's maintain-current-mix form.
- If an owner team is required, use the team most clearly associated with the deficit category from the scoped data or prompt context; break ties deterministically.

## SLA Aging Workflow

Use the portfolio category classifier to find SLA-relevant categories, typically reliability and security.

Primary SLA population:
- Team is in scope.
- Category is in scope.
- Item is primary.
- Item was created on or before `as_of`.
- Include open/non-complete items as of `as_of`.
- Include complete items only when `closed_at` falls inside the recent closed window and is not after `as_of`.

SLA due and overdue:
- Use `due_at` from the work item when present. Fetch SLA policy data, but do not override an explicit `due_at`; use policy only to explain/fill missing due dates if needed.
- An open/non-complete item is overdue when `due_at < as_of`.
- A complete item is overdue when `due_at < closed_at`.
- A due date equal to `as_of` or `closed_at` is not overdue.

Aging buckets:
- Age each included primary item from `created_at` to `closed_at` for completed items, otherwise to `as_of`.
- Count ages in buckets `0-3`, `4-7`, `8-14`, `15-30`, and `31+` calendar days.

SLA aggregations:
- Sort ID lists lexicographically unless a template defines another order.
- Missing-owner IDs are included primary IDs where `owner` is null or empty.
- Team overdue counts include the scoped teams in the requested or alphabetical order.
- Hotspots group overdue primary items by `(team, owner)`, using `UNASSIGNED` for missing owners; choose the highest count and break ties deterministically by team then owner.
- Breach rate is `overdue_primary_count / included_primary_count`, rounded to three decimals.
- If an escalation queue is requested, order overdue primary items by severity (`S1`, `S2`, `S3`, `S4`), then by largest days overdue/late, then priority ascending, then ID ascending.

## Release Readiness Workflow

Release primary population:
- Work items with `release_id` matching the release under review.
- Exclude duplicate and cancelled records.
- Use `status`, not `mirror_status`, for completion truth.

Milestone completion:
- Include every milestone for the release.
- For each milestone, denominator is primary release items with that `milestone_id`.
- Completed count uses the complete-status set.
- `completion_pct = complete_primary / primary_total * 100`, rounded to one decimal place. Use `0.0` if the denominator is zero.
- Sort milestone rows by `milestone_id` unless the template says otherwise.

Readiness score:
- `completed_primary_release_items / total_primary_release_items`, rounded to three decimals.

Blockers and gating:
- Unresolved blockers have `resolved_at` null and are not `Resolved`.
- High-impact blockers are severity `High` or `Critical`.
- Count blocker causes by exact `cause` text for unresolved high-impact blockers.
- Gating work item IDs are unresolved high-impact blocker work items that are primary release work and non-complete.

Critical dependency chains:
- Build a graph from `dependencies.blocked_id -> depends_on_id`.
- Start from non-complete primary release work.
- Traverse dependency paths while avoiding cycles.
- Ignore missing, duplicate, and cancelled dependency targets as primary blockers.
- Emit a chain when the path reaches a non-complete dependency target; include the ordered work item ID path.
- Sort chains lexicographically by the full path.

Ship decision, when no stricter prompt rule is provided:
- `NO_SHIP` if there is any gating work item, unresolved Critical blocker, or critical dependency chain.
- `SHIP_WITH_WATCH` if there is no no-ship condition but readiness is below 1.0 or unresolved lower-impact blockers remain.
- `SHIP` only when all primary release work is complete and no unresolved blockers or critical chains remain.

## Final Checks

- Return only the JSON object when the task asks for JSON-only output.
- Preserve the template's exact key names and structural shape.
- Do not copy values from training answers or prior examples; recompute from the current environment.
- Apply the prompt's ordering instructions over these defaults.
- Use numeric JSON values for rounded percentages/rates, not strings, unless the template requires strings.
