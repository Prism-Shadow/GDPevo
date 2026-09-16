---
name: portfolio-environment-analyst
description: Analyze the shared engineering portfolio task environment and produce strict JSON for portfolio-mix, SLA-aging, duplicate-cluster, hotspot, and release-readiness assessments. Use when a task references work items, mix targets, SLA policy, releases, milestones, blockers, dependencies, restricted SQL, or task environment base URLs.
---

# Portfolio Environment Analyst

## Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before querying. Treat the template as the output contract: preserve required keys, enum spellings, order notes, precision, nullability, and "JSON only" requirements.
2. Read `environment_access.md` for the base URL and allowed endpoints. Prefer REST endpoints. Use `POST /api/query` only when a valid query token is supplied; pass it as `X-Env-Token` and do not guess or brute-force tokens.
3. Fetch the needed data. For a reproducible local snapshot, run this from the directory containing this `SKILL.md`:

```bash
python scripts/fetch_snapshot.py --base-url "$TASK_ENV_BASE_URL" --out /tmp/portfolio_snapshot.json
```

4. Build all metrics from authoritative fields on records and first-class endpoint data. Do not trust stale mirrors: ignore `mirror_status` for state, ignore `legacy_category` for portfolio category, and ignore release mirror/export fields when release, milestone, blocker, and dependency endpoints exist.
5. Emit only the JSON object requested by the template. Do not add prose, comments, or extra keys.

## Work Item Ground Rules

Use `id`, `team`, `product_area`, `created_at`, `closed_at`, `due_at`, `status`, `duplicate_of`, `work_type`, `labels`, `title`, `owner`, `severity`, `priority`, `release_id`, and `milestone_id` as canonical work-item fields.

Treat a record as non-primary when `duplicate_of` is not null, `status` is `Duplicate`, or `status` is `Cancelled`. Exclude non-primary records from denominators and primary ID lists. When the template asks for duplicate clusters, group duplicate records by `duplicate_of` and sort cluster `primary_id` and `duplicate_ids` as instructed. When a duplicate lacks `duplicate_of`, report it only in a generic excluded/distractor list if the schema provides one.

Treat these statuses as complete for release and SLA closure logic: `Closed`, `Done`, `Verified`, `Deployed`. Treat `Backlog`, `In Progress`, `Review`, and `Reopened` as non-complete. Prefer date fields over status names when a task asks about recent closure or lateness.

## Portfolio Category Precedence

Classify each primary work item into exactly one portfolio category by applying this precedence to authoritative `work_type`, `labels`, and `title` text. Convert text to lowercase before matching.

1. `Security`: `work_type` is `Security` or `Compliance`, or text contains `security`, `cve`, `auth`, `encryption`, or `compliance`.
2. `Reliability`: `work_type` is `Reliability`, `Incident`, or `Bug`, or text contains `reliability`, `incident`, `outage`, `latency`, or `flaky`.
3. `TechDebt`: `work_type` is `Refactor`, `Dependency`, or `Chore`, or text contains `refactor`, `cleanup`, `migration`, `dependency`, `deprecate`, or `harden`.
4. `NewFeature`: `work_type` is `Feature` or `Enhancement`, or text contains `feature`, `rollout`, `experiment`, `polish`, or `customer-request`.

Do not use `legacy_category` to classify. Do not double count an item when labels conflict; the first matching category above wins.

## Portfolio Mix Tasks

For closed-work portfolio mix:

- Select the `mix_targets` row by the prompt's `scope_id`; convert target fractions to percentage points with `target_pct = fraction * 100`.
- Include primary work items whose `team` and `product_area` match prompt scope and whose `closed_at` falls in the requested quarter. Count items, not story points.
- Sort included IDs by `closed_at` ascending, then `id` ascending unless the template says otherwise.
- Count categories with the precedence rules. Actual percentage is `count / total * 100`, rounded to one decimal place. Gap is `actual_pct - target_pct`, rounded to one decimal place.
- Order mix/gap rows exactly as the template requires, commonly `NewFeature`, `TechDebt`, `Reliability`, `Security`.
- Under-invested categories are those with negative gap, sorted most negative to least negative.
- Use `REBALANCE_CAPACITY` when any category is under target. Use the largest deficit as the primary category and the next-largest deficit as a secondary category when the schema has one. Use `MAINTAIN_CURRENT_MIX` only when no gaps are negative. Use data-quality actions only for real conflicts such as missing/multiple target rows.

## SLA Aging Tasks

For SLA population tasks:

- Use the prompt's as-of date, not the current date. Include primary items in scoped teams whose resolved category is in the requested SLA categories and that are either non-complete as of the as-of date or completed inside the recent closed window ending on the as-of date.
- Use `due_at` when present. If `due_at` is missing, compute it from `created_at` plus the matching `sla_policy` `days_to_due` for the item's `severity`.
- An item is overdue when it is non-complete and `due_at` is before the as-of date, or when it completed after `due_at`. A due date equal to the as-of date is not overdue.
- Aging days are `closed_at - created_at` for included completed items, otherwise `as_of - created_at`. Bucket into `0-3`, `4-7`, `8-14`, `15-30`, and `31+`.
- Breach rate is `overdue primary count / included primary count`, rounded to three decimals. Use `0.000` when the denominator is zero.
- Missing-owner IDs are included primary records with null or empty `owner`, sorted as requested.
- For hotspot fields, group overdue primary items by `(team, owner)`, using `UNASSIGNED` for missing owner. Sort by overdue count descending, then team ascending, then owner ascending unless the template specifies another tie-breaker.
- For escalation queues, sort overdue primary work by severity rank `S1`, `S2`, `S3`, `S4`, then `due_at` ascending, then `priority` ascending, then `id` ascending.

## Release Readiness Tasks

For release assessments:

- Fetch the release, all milestones for that `release_id`, all primary release work items, blockers, and dependencies. Do not use mirror fields as release truth.
- For each milestone, count primary work items with that `milestone_id`. Completion count uses the complete statuses above. Sort milestone rows by `milestone_id`; round completion percentages to one decimal place.
- Release readiness score is completed primary release work divided by primary release work denominator, rounded to three decimals.
- Count blocker causes only for unresolved high-impact blockers: `resolved_at` is null, `status` is not `Resolved`, and blocker `severity` is `High` or `Critical`. Use exact `cause` strings as object keys.
- Critical dependency chains start at a primary release work item and follow dependency edges to a terminal primary dependency that is non-complete. Ignore dependency terminals that are duplicate or cancelled. Include ordered ID paths, avoid cycles, and sort chains lexicographically by the full path.
- Gating work item IDs are non-complete primary release items that have an unresolved high-impact blocker or a critical dependency chain. Sort unique IDs ascending.
- Use `NO_SHIP` when gating work or critical non-complete dependency chains remain. Use `SHIP_WITH_WATCH` when readiness is otherwise clear but unresolved watch items remain. Use `SHIP` only when primary release work is complete and no unresolved blockers or critical chains remain.

## Output Discipline

Follow every ordering and precision note in the template over these defaults. Validate the final object against the template manually: no extra keys, required keys present, arrays sorted as requested, percentages rounded at the last step, and enum values copied exactly.
