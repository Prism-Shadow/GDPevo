---
name: engineering-portfolio-env
description: Solve JSON audit tasks against the shared engineering portfolio task environment. Use for portfolio mix reviews, SLA aging and breach audits, release readiness assessments, milestone completion, blocker and dependency analysis, duplicate/cancelled exclusions, stale mirror/export field handling, and exact answer_template.json output from work-items, mix-targets, SLA policy, releases, milestones, blockers, dependencies, or restricted query endpoints.
---

# Engineering Portfolio Environment

Use this skill to solve tasks that ask for a JSON answer from the shared engineering portfolio environment. The recurring job is to query the environment, separate authoritative records from stale mirrors/distractors, compute the requested metrics, and emit exactly the schema in `input/payloads/answer_template.json`.

## First Pass

1. Read the user prompt and `input/payloads/answer_template.json`.
2. Read the task's runtime access file if supplied. Use its base URL when the prompt contains `<TASK_ENV_BASE_URL>`.
3. Fetch only the collections needed for the answer. Typical endpoints are:
   - `GET /api/work-items`
   - `GET /api/work-items/{item_id}`
   - `GET /api/mix-targets`
   - `GET /api/sla-policy`
   - `GET /api/releases`
   - `GET /api/releases/{release_id}`
   - `GET /api/milestones`
   - `GET /api/dependencies`
   - `GET /api/blockers`
   - `POST /api/query` only when the runtime file supplies the required token/header
4. Build a small local calculation script or notebook-style command when the task has many records. Prefer deterministic calculations over manual counting.
5. Return only the JSON object unless the prompt asks for prose.

## Authoritative Fields

Prefer the current authoritative work item fields:

- `status`, `closed_at`, `created_at`, `due_at`
- `duplicate_of`
- `team`, `product_area`, `release_id`, `milestone_id`
- `work_type`, `labels`, `title`
- `owner`, `severity`, `priority`

Treat `mirror_status`, `legacy_category`, stale exports, and labels such as `stale-export` as warning signals, not truth. Do not let stale mirror fields make an incomplete item complete, resurrect a duplicate, or override the category precedence below.

## Shared Work Item Rules

Use a primary record only when it is not cancelled or duplicate:

- Exclude any item with `status` equal to `Duplicate` or `Cancelled`.
- Exclude any item with a non-null `duplicate_of`, even when its `status` looks closed.
- Count items, not story points, unless the prompt explicitly says otherwise.

Treat these statuses as complete for readiness or closed-work denominators when paired with the relevant dates: `Closed`, `Done`, `Deployed`, `Verified`, and `Complete`. Treat `Backlog`, `In Progress`, `Review`, and `Reopened` as non-complete.

When reconstructing an as-of view, compare dates to the as-of date. If an item was created after the as-of date, exclude it. If it closed after the as-of date, treat it as still open at the as-of date.

## Portfolio Category Precedence

When the prompt says to resolve conflicting type, label, and title signals, classify from lowercased tokens in `work_type`, `labels`, and `title`. Apply this precedence, stopping at the first match:

1. `Security`: `security`, `cve`, `auth`, `encryption`, `compliance`
2. `Reliability`: `reliability`, `incident`, `outage`, `latency`, `flaky`
3. `TechDebt`: `tech-debt`, `tech debt`, `refactor`, `cleanup`, `migration`, `dependency`, `chore`
4. `NewFeature`: `feature`, `enhancement`, `rollout`, `customer-request`

This precedence is intentional: security/auth/encryption beats reliability, reliability beats cleanup/refactor/migration, and cleanup/migration beats generic feature/rollout wording. Use `legacy_category` only if the prompt explicitly asks for legacy data.

## Portfolio Mix Tasks

For closed portfolio mix reviews:

1. Filter work items to the prompt scope: quarter, teams, product area or areas, and any explicit scope conditions.
2. Include only primary records with `closed_at` inside the quarter and an authoritative complete status.
3. Sort included work item IDs as the template requests; common ordering is `closed_at` ascending, then `id` ascending.
4. Find the target mix from `/api/mix-targets`, preferring the explicit `scope_id` row when supplied. Convert target fractions to percentage points by multiplying by 100.
5. Compute category counts by item count.
6. Compute actual percentage as `count / total * 100`, rounded to one decimal place.
7. Compute gap as `actual_pct - target_pct`, rounded to one decimal place. Use the rounded one-decimal actual and target values when reproducing one-decimal tables.
8. List under-invested categories where `gap_pct` is negative, ordered from most negative to least negative.
9. For rebalancing recommendations, choose the largest negative gap as the primary category. Use the second negative gap as secondary when the schema has one; use `null` when there is no secondary deficit. If no categories are negative, use the schema's maintain/no-negative option when available.
10. If the recommendation schema requires an `owner_team`, choose an in-scope team with direct evidence in the deficient category, such as the team owning the only or most recent included item in that category. If there is no included item for that category, choose the team with the lowest included count in that category, using the template's allowed values and deterministic tie-breaks.
11. Report excluded duplicate, cancelled, or distractor IDs only when the schema asks. These should be same-scope records that looked eligible but failed primary closed-work rules; order them exactly as the template says.

## SLA Aging Tasks

For SLA population, use the prompt's teams, categories, as-of date, and recent closed window.

Include a primary work item when all are true:

- It is a primary record under the shared work item rules.
- Its team is in scope.
- Its category is in scope by the portfolio precedence.
- `created_at` is on or before the as-of date.
- It is open as of the as-of date, or it closed inside the recent closed window ending on the as-of date.

For each included item:

- Use `effective_date = closed_at` when `closed_at` is on or before the as-of date; otherwise use the as-of date.
- It is overdue when `effective_date > due_at`. Due on the as-of date is not overdue.
- Age in days is `effective_date - created_at`.
- Buckets are inclusive: `0-3`, `4-7`, `8-14`, `15-30`, `31+`.

Common SLA outputs:

- `included_primary_ids`: sort lexicographically unless the template says otherwise.
- `overdue_primary_ids`: lexicographic subset of included primary IDs.
- `missing_owner_ids`: included primary IDs where `owner` is missing/null.
- `breach_rate` or `sla_breach_rate`: `overdue_count / included_count`, rounded to three decimals.
- Team overdue counts: group overdue included primary records by team; list teams alphabetically.
- Top hotspot: group overdue included primary records by `(team, owner)`, using `UNASSIGNED` for missing owners; choose highest count, then deterministic alphabetical tie-breaks unless the prompt specifies another rule.
- Severity counts: count overdue included primary records by severity keys such as `S1` through `S4`, filling absent severities with zero when required.
- Escalation queue: order overdue primary IDs by severity rank `S1`, `S2`, `S3`, `S4`, then older `due_at`, then lower numeric `priority`, then `id`.
- Duplicate clusters: report excluded duplicate records whose `duplicate_of` points to an included primary. Sort clusters by `primary_id`, and sort `duplicate_ids` lexicographically.

## Release Readiness Tasks

For release assessments, query releases, milestones, work items, blockers, and dependencies.

1. Select work items by authoritative `release_id`; do not use stale mirror release/status fields as release truth.
2. Exclude duplicate/cancelled records from milestone denominators.
3. For each milestone in the release, count primary release work with matching `milestone_id`.
4. `complete_primary` is the number of primary milestone items with a complete authoritative status.
5. `primary_total` is the primary milestone denominator.
6. `completion_pct = complete_primary / primary_total * 100`, rounded to one decimal place.
7. Sort milestone rows by `milestone_id` ascending.
8. `readiness_score = total_complete_primary / total_primary`, rounded to three decimals.

For blockers:

- An unresolved blocker has `resolved_at` null and a non-resolved `status`.
- High-impact blockers are `High` or `Critical` severity unless the prompt defines a different set.
- Count unresolved high-impact blocker causes by exact `cause` text. Sort keys alphabetically when object order is visible and the prompt gives no other order.
- Gating work item IDs are non-complete primary release work items tied to unresolved high-impact blockers, plus any other non-complete work the prompt explicitly defines as gating. Sort and de-duplicate.

For dependency chains:

- Build a directed graph from `blocked_id` to `depends_on_id`.
- Start from gating non-complete release work unless the prompt broadens the start set.
- Follow dependency edges until a terminal dependency is reached or a cycle would repeat an ID.
- Include a chain only when it ends at a non-complete primary dependency. Omit chains that end only in complete, duplicate, cancelled, or out-of-scope non-gating records.
- Sort chains lexicographically by the full ordered ID path.

Ship decision policy must follow the prompt when supplied. A reliable default is:

- `NO_SHIP` if non-complete gating release work has unresolved High/Critical blockers or critical dependency chains.
- `SHIP_WITH_WATCH` if the release is otherwise complete enough to ship but has unresolved watch items, lower-impact blockers, or unresolved high-impact blockers only on completed work.
- `SHIP` only when primary release work is complete and no unresolved blocker/dependency risk remains.

## Output Discipline

Mirror the answer template exactly:

- Preserve required keys and nested shapes.
- Use arrays, numbers, booleans, and nulls with the JSON types requested by the template.
- Fill zero-count categories, severities, and teams when the template requires fixed keys.
- Use the ordering rules in the prompt/template over the defaults in this skill.
- Round only at the requested output precision.
- Validate by checking every included/excluded ID against the scope rules before finalizing.
