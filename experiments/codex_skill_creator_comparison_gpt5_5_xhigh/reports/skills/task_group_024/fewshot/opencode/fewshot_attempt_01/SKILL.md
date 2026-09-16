---
name: engineering-portfolio-env
description: Solve JSON-only engineering portfolio analysis tasks against the shared task environment. Use this skill when a prompt mentions work items, portfolio mix targets, SLA aging, release readiness, milestones, blockers, dependencies, duplicate clusters, stale mirror/export fields, or asks for an answer matching input/payloads/answer_template.json from <TASK_ENV_BASE_URL>.
---

# Engineering Portfolio Environment

Use this skill to answer data-analysis prompts over the shared engineering portfolio API. The task usually asks for a single JSON object matching `input/payloads/answer_template.json`; build the answer from the environment, not from stale mirror/export fields.

## Workflow

1. Read the user prompt and the local `input/payloads/answer_template.json` before querying data. Treat the template as the required output contract: field names, enum values, ordering, rounding, and whether prose is forbidden.
2. Read `environment_access.md` only for the base URL, endpoint list, and any query-token instructions. Replace `<TASK_ENV_BASE_URL>` with that base URL.
3. Fetch the narrowest useful data. Prefer direct endpoints such as `/api/work-items/{item_id}` and `/api/releases/{release_id}` when IDs are known. If using collection endpoints, filter immediately by the prompt scope.
4. Use canonical fields from API records. For work items, prefer `status`, `closed_at`, `duplicate_of`, `team`, `product_area`, `release_id`, `milestone_id`, `work_type`, `labels`, `title`, `owner`, `severity`, `priority`, `created_at`, and `due_at`. Do not let `mirror_status` or `legacy_category` override canonical fields; only mention/report them when the answer schema explicitly asks for an ignored-stale-fields flag.
5. Separate primary records from duplicate/cancelled/distractor records before computing counts. A primary record has no `duplicate_of`, is not in `Duplicate` or `Cancelled` status, and belongs to the prompt's scope.
6. Compute using exact arithmetic, then round only at the output boundary. Emit JSON only when requested; do not include explanatory prose.

Complete statuses for this environment are `Closed`, `Done`, `Verified`, and `Deployed`. Treat `Open`, `Backlog`, `In Progress`, `Review`, `Blocked`, `Duplicate`, and `Cancelled` as non-complete or excluded according to the task.

## Portfolio Mix Tasks

Use this path for prompts about Q4/Qx portfolio mix, target mix, category counts, gaps, or rebalancing.

1. Define the scope from the prompt: quarter date range, teams, product areas, and target `scope_id`.
2. Fetch mix targets and select the target row whose `scope_id` matches the prompt. Use target percentages as percentage points.
3. Include closed primary portfolio work where:
   - `team` and `product_area` match the scope;
   - `closed_at` falls inside the quarter, inclusive;
   - `status` is one of the complete statuses;
   - `duplicate_of` is null and status is not `Duplicate` or `Cancelled`.
4. Track excluded records separately when the template asks: duplicates (`duplicate_of` present or `status == "Duplicate"`), cancelled records, and other same-scope distractors that look related but are not primary closed work.
5. Classify each included item into exactly one portfolio category. Resolve conflicts from canonical `work_type`, `labels`, and `title`; ignore `legacy_category`. Treat generic `feature` and `rollout` labels as weak signals because the environment uses them on non-feature work.

Category precedence:

- `Security`: strongest signal. Use for `work_type` values such as `Security` or `Compliance`, or labels/title containing security-specific terms such as `security`, `cve`, or `encryption`. Sensitive-domain title words such as auth, consent, payment, or billing can support Security when the canonical work type is not a plain `Feature`.
- `Reliability`: use for `Reliability`, `Incident`, or `Bug` work types, or labels/title containing `reliability`, `incident`, `outage`, `latency`, or `flaky`, unless a stronger Security signal is present.
- `TechDebt`: use for `Refactor`, `Chore`, or `Dependency` work types, or labels/title containing `refactor`, `cleanup`, `migration`, or `dependency`, unless Security or Reliability wins.
- `NewFeature`: use for canonical `Feature` work only after stronger Security, Reliability, and TechDebt signals are ruled out. Do not count an `Enhancement` as NewFeature just because it has generic `feature` or `rollout` labels; classify it from the remaining labels/title context.

Portfolio calculations:

- Counts are item counts, not story points.
- `actual_pct = count / total_included * 100`, rounded to one decimal place.
- `gap_pct = actual_pct - target_pct`, rounded to one decimal place.
- Under-invested/deficit categories are negative gaps, ordered from most negative to least negative.
- For a rebalance action, choose the largest negative gap as primary. If a secondary is required, use the next negative gap. If the template asks for an owner team, choose the in-scope team most associated with the deficient category or with the least represented primary work; break ties deterministically by the prompt/template ordering.
- Order included IDs by `closed_at` ascending, then `id` ascending unless the template says otherwise.

## SLA Aging Tasks

Use this path for prompts about SLA aging, breach rate, overdue primary IDs, missing owners, duplicate clusters, hotspots, or escalation queues.

1. Define scope from the prompt: teams, relevant categories, as-of date, and recent closed window in days.
2. Fetch `/api/sla-policy` and relevant work items. Use each work item's `due_at` as the authoritative SLA deadline; if `due_at` is missing, derive it from `created_at` plus the policy row matching `severity`.
3. Build the primary SLA population:
   - primary only: no duplicate/cancelled records;
   - team in scope;
   - category resolves to one of the requested SLA categories using the portfolio category rules;
   - include open/non-complete items as of the as-of date;
   - include complete items only when `closed_at` is within the recent closed window ending on the as-of date, inclusive.
4. Report duplicate clusters but do not count duplicates as primary work. Group duplicates by `duplicate_of`/canonical primary ID and sort duplicate IDs lexicographically.
5. Mark an item overdue when:
   - non-complete and `due_at` is before the as-of date; or
   - complete and `closed_at` is after `due_at`.
   A due date equal to the as-of date is not overdue.
6. Age each primary item in whole days from `created_at` to `closed_at` for complete items, otherwise to the as-of date. Bucket into `0-3`, `4-7`, `8-14`, `15-30`, and `31+`.
7. Compute breach rate as `overdue_primary_count / included_primary_count`, rounded to three decimals.

SLA ordering:

- Sort ordinary ID lists lexicographically unless the template gives another order.
- List teams alphabetically when producing team counts.
- Choose the top overdue hotspot by `(team, owner)` count descending; use `UNASSIGNED` for missing owner; break ties by team then owner alphabetically.
- Sort escalation queues by severity `S1`, `S2`, `S3`, `S4`, then `due_at` ascending, then `priority` ascending, then `id` ascending. Include closed-late primary work if the template treats it as overdue follow-up.

## Release Readiness Tasks

Use this path for prompts about a release ID, ship decision, milestone completion, blockers, dependencies, critical chains, or readiness score.

1. Fetch `/api/releases/{release_id}` first. It returns authoritative release metadata plus milestones and blockers for that release.
2. Fetch release work items and dependencies as needed. Use `release_id` and `milestone_id` from work item records as canonical release membership; do not use stale mirror fields as release truth.
3. For each release milestone, count primary work items assigned to that milestone. Exclude duplicates and cancelled records from denominators.
4. A primary work item is complete when `status` is in the complete-status set. For each milestone:
   - `complete_primary`: completed primary count;
   - `primary_total`: primary denominator;
   - `completion_pct = complete_primary / primary_total * 100`, rounded to one decimal place.
5. Readiness score is total completed primary work divided by total primary denominator across release milestones, rounded to three decimals.
6. For blocker cause counts, include unresolved high-impact blockers only: `resolved_at` is null or status is not resolved/closed, and severity is `High` or `Critical`. Count by exact `cause` string.
7. Gating work item IDs are non-complete primary release work that blocks shipping because of unresolved high-impact blockers and/or critical dependency chains requested by the prompt. Sort IDs ascending with no duplicates.
8. For critical dependency chains, traverse dependency records from blocked release work to the non-complete dependency. Emit ordered ID paths and sort chains lexicographically by the full path. Exclude chains whose terminal dependency is complete unless the prompt explicitly asks for all chains.
9. Choose ship decision conservatively:
   - `NO_SHIP` when unresolved Critical/High blockers affect non-complete release work, critical dependency chains remain, or readiness is materially below release expectations.
   - `SHIP_WITH_WATCH` when primary work is effectively ready but low-impact blockers, monitoring items, or recently closed risks need attention.
   - `SHIP` only when primary release work is complete and there are no unresolved high-impact blockers or critical dependency chains.

## Final JSON Checks

Before answering:

- Validate every required template field is present and no extra fields are added when the schema says `additionalProperties: false`.
- Confirm all lists use the ordering requested by the prompt/template.
- Confirm percentages and rates use the requested precision.
- Confirm duplicates/cancelled records are excluded from denominators but still reported when requested.
- Confirm `mirror_status` and `legacy_category` did not change inclusion, completion, release, or category decisions.
