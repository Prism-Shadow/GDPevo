---
name: portfolio-environment-review
description: Produce schema-constrained JSON answers for task-env engineering portfolio reviews that require querying work items, mix targets, SLA policy, releases, milestones, blockers, and dependencies. Use for portfolio mix readouts, SLA aging and breach audits, and release-readiness assessments where prompts mention authoritative environment fields, stale mirror/export fields, duplicate clusters, cancelled/distractor records, exact ordering, and precise rounding.
---

# Portfolio Environment Review

## Core Workflow

1. Read the user prompt and the answer template before querying data. Treat the template as the output contract; emit no prose when the prompt asks for JSON only.
2. Read `environment_access.md` for `GDPEVO_ENV_BASE_URL`, allowed endpoints, and the `X-Env-Token` value for restricted SQL. Do not use endpoints outside that file.
3. Query narrow slices whenever possible. Use direct GET endpoints for small reference sets and `POST /api/query` with `{"sql":"..."}` for filtered work-item slices.
4. Build all calculations from authoritative current fields such as `status`, `closed_at`, `created_at`, `due_at`, `duplicate_of`, `work_type`, `labels`, `release_id`, and `milestone_id`.
5. Ignore stale mirror/export fields as truth. `mirror_status`, `legacy_category`, and labels like `stale-export` are useful only when the template asks for acknowledgement flags or excluded distractors.
6. Exclude non-primary work from denominators: records with `status = "Duplicate"`, any non-null `duplicate_of`, and `status = "Cancelled"`. Report them only in the template fields that ask for duplicates, cancelled IDs, exclusion flags, or distractors.
7. Validate the completed object against the template shape: required keys, no extra keys when the schema says `additionalProperties: false`, exact enum strings, requested ordering, and requested decimal precision.

Useful query pattern:

```bash
curl -sS -H "X-Env-Token: <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"sql":"select id,status,closed_at,work_type,labels,duplicate_of from work_items where ..."}' \
  "<BASE_URL>/api/query"
```

## Shared Field Rules

Use these status sets unless a prompt gives a different definition:

- Complete statuses: `Closed`, `Done`, `Deployed`, `Verified`.
- Non-complete statuses: `Backlog`, `In Progress`, `Review`, `Reopened`.
- Excluded statuses: `Duplicate`, `Cancelled`.

Sort stable outputs exactly as requested. Common defaults are lexicographic ID order for ID sets, chronological order by `closed_at` then `id` for closed portfolio lists, category order `NewFeature`, `TechDebt`, `Reliability`, `Security`, and severity order `S1`, `S2`, `S3`, `S4`.

Round only at the requested output boundary:

- Percentage-point outputs: `100 * numerator / denominator`, rounded to 1 decimal place unless specified otherwise.
- Target mix fields from `mix_targets` are decimal fractions; convert to percentage points before comparing.
- Gap percentage points: `actual_pct - target_pct`, rounded to the requested precision.
- Rates and readiness scores: raw fraction rounded to the requested decimals.

## Portfolio Categories

Classify every primary work item into exactly one portfolio category. Use current `work_type`, current `labels`, and the title together; do not let `legacy_category`, `mirror_status`, or stale-export labels override current signals.

Start with this mapping:

- `Security`: explicit security/compliance work, including `work_type` values such as `Security` and `Compliance`, and strong current signals such as `security`, `cve`, `compliance`, `auth`, or `encryption` when they are not stale distractors.
- `Reliability`: reliability and operational incident work, including `work_type` values such as `Reliability` and `Incident`, and strong current signals such as `reliability`, `incident`, `outage`, `latency`, or `flaky`.
- `TechDebt`: cleanup, refactor, migration, dependency, and maintenance work, including `work_type` values such as `Refactor`, `Chore`, and `Dependency`.
- `NewFeature`: feature and enhancement work, including `work_type` values such as `Feature` and `Enhancement`, and signals such as `feature`, `rollout`, or customer-facing enhancement language.

When signals conflict, prefer the category supported by the strongest current evidence. A direct `work_type` normally beats stray labels. A generic type such as `Bug`, `Chore`, or `Enhancement` may be resolved by repeated current labels and title evidence. Treat explicit stale wording or stale-export markers as evidence not to use that conflicting signal.

## Portfolio Mix Reviews

1. Extract scope from the prompt: quarter, teams, product area or areas, and target `scope_id`.
2. Fetch the target row from `mix_targets` using the requested scope ID. Use that row even if other rows match the same quarter or product area.
3. Select in-scope closed primary work:
   - `team` is in scope.
   - `product_area` is in scope.
   - `closed_at` falls inside the requested quarter.
   - `status` is complete.
   - record is not duplicate, duplicate-of, or cancelled.
4. Keep excluded same-scope records separately when requested: duplicates, records with `duplicate_of`, cancelled records, and other related records that fail primary closed-work rules.
5. Count included items by portfolio category. Use item counts, not story points.
6. Build actual percentages, target percentages, gaps, and under-invested categories from those counts. Under-invested means a negative gap; order deficits from most negative to least negative, using category order as the tie-breaker.
7. Choose follow-up actions from the template enum:
   - Use `REBALANCE_CAPACITY` when at least one category is under target.
   - Use `MAINTAIN_CURRENT_MIX` when no gaps are negative.
   - Use `INVESTIGATE_DATA_QUALITY` only when authoritative fields conflict enough that the denominator or category assignment cannot be determined.
8. If the template asks for an owner team for rebalancing, choose the in-scope team with the weakest actual contribution to the deficit category; break ties by prompt-specified order, then alphabetically.

## SLA Aging Reviews

1. Extract teams, category scope, as-of date, and recent closed window from the prompt.
2. Fetch `sla_policy` and relevant work items. Use `due_at` as the authoritative due date; use policy rows by severity to sanity-check missing or suspect due dates.
3. Select primary SLA population:
   - `team` is in scope.
   - category classification is in the requested SLA categories, usually `Reliability` and `Security`.
   - `created_at` is on or before the as-of date.
   - item is open as of the as-of date, or closed within the recent closed window.
   - item is not duplicate, duplicate-of, or cancelled.
4. For duplicate clusters, group excluded duplicate records by their `duplicate_of` primary ID. Sort primary IDs and duplicate IDs lexicographically unless the template says otherwise.
5. Determine breach/overdue status with an effective evaluation date:
   - For open work as of the as-of date, use the as-of date.
   - For work closed on or before the as-of date, use `closed_at`.
   - Treat a due date equal to the evaluation date as due today, not overdue, unless the prompt states an inclusive rule.
   - A record is overdue or breached when `due_at` is before the evaluation date.
6. Compute aging buckets from `created_at` through the same effective evaluation date. Use inclusive bucket ranges such as `0-3`, `4-7`, `8-14`, `15-30`, and `31+` when those are in the template.
7. Group overdue counts by requested dimensions such as team, severity, owner, or owner/team hotspot. Use `UNASSIGNED` for missing owners when the template expects an owner string.
8. Build escalation queues from overdue primary work only. Unless the prompt gives another priority order, sort by severity rank, then numeric `priority`, then oldest `due_at`, then ID.
9. Compute breach rate as `overdue_or_breached_primary_count / included_primary_count`, rounded to the requested precision.

## Release Readiness

1. Fetch the release record, all milestones for that release, release work items, blockers, and dependencies.
2. Use release and milestone fields as release truth. Do not use mirror status or stale export fields as release truth.
3. Build the primary release denominator from work items whose `release_id` matches and that are not duplicate, duplicate-of, or cancelled.
4. For every milestone in the release, count primary work assigned to that `milestone_id`; report complete primary count, primary total, and completion percentage. Include milestones even when their count is zero if the template asks for every milestone.
5. Gating work item IDs are non-complete primary release work items, sorted uniquely as requested.
6. Count unresolved high-impact blockers from blocker records for the release:
   - unresolved means `resolved_at` is null and status is not `Resolved`.
   - high-impact means severities such as `High` and `Critical`, unless the prompt defines a different set.
   - keys must be exact `cause` strings.
7. Build critical dependency chains from dependency records that gate readiness, especially relation `blocks-release-readiness`. Start paths at release work items and follow dependencies until the first non-complete dependency. Output ordered ID paths and sort chains lexicographically by the full path.
8. Readiness score is `complete_primary / primary_total`, rounded as requested.
9. Choose ship decision conservatively:
   - `NO_SHIP` when unresolved high-impact blockers, non-complete critical dependency chains, or high-risk gating work remain.
   - `SHIP_WITH_WATCH` when primary work is complete enough to ship but low-impact unresolved blockers or monitor-only concerns remain.
   - `SHIP` when all primary readiness work is complete and no unresolved blockers or critical dependencies remain.

## Output Discipline

Use the template’s exact field names and enum strings. Replace placeholder strings in skeleton templates with actual JSON values of the correct type. For formal JSON Schemas, satisfy constants and required fields exactly. Do not include task-local final answers, explanatory prose, comments, markdown fences, or trailing commas in the final JSON unless the user explicitly asks for analysis instead of the answer.
