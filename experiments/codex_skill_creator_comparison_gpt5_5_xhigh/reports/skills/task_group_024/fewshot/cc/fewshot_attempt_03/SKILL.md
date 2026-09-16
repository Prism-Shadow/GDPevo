---
name: engineering-portfolio-auditor
description: Solve endpoint-backed engineering portfolio audit tasks that ask for JSON calculations over work items, portfolio mix targets, SLA aging, duplicate clusters, blockers, dependencies, milestones, or release readiness. Use this skill whenever the prompt mentions a shared task environment, work items, mix targets, SLA policy, release readiness, portfolio categories, stale mirror fields, or duplicate/cancelled engineering records.
---

# Engineering Portfolio Auditor

Use this skill to produce exact JSON answers for engineering portfolio tasks backed by a small REST environment. The recurring hazards are stale mirror/export fields, duplicate records that should be reported but not counted, category signals that conflict, and strict ordering/rounding rules in the answer template.

## First Pass

1. Read the user prompt and `input/payloads/answer_template.json` before calculating. Treat the template as the final output contract.
2. Read the runtime access file only for the base URL, credentials, and endpoint list. Replace any `<TASK_ENV_BASE_URL>` placeholder with that base URL.
3. Fetch authoritative data from the REST endpoints. Use `/api/query` only for filtered inspection when REST responses are too broad.
4. Build a scratch table of candidate records with `id`, `team`, `product_area`, `status`, `created_at`, `closed_at`, `due_at`, `duplicate_of`, `work_type`, `labels`, `title`, `owner`, `severity`, `priority`, `release_id`, and `milestone_id`.
5. Produce only the JSON object requested by the template. Do not include explanation text.

The bundled helper can do the repeatable calculations:

```bash
python skill/scripts/portfolio_env_helper.py portfolio-mix --base-url "$TASK_ENV_BASE_URL" --scope-id SCOPE --quarter 2025-Q4 --teams "Team A" "Team B" --product-areas "Area A" "Area B"
python skill/scripts/portfolio_env_helper.py sla-aging --base-url "$TASK_ENV_BASE_URL" --as-of 2026-01-15 --recent-closed-window-days 14 --teams "Team A" "Team B" --categories Reliability Security
python skill/scripts/portfolio_env_helper.py release-readiness --base-url "$TASK_ENV_BASE_URL" --release-id REL-ID
```

The helper prints canonical calculation JSON. Reconcile field names, nesting, and optional sections against the task's template before answering.

## Authoritative Fields

Prefer current work-item fields:

- Use `status`, not `mirror_status`, for completion, duplicate, and cancellation decisions.
- Use `work_type`, `labels`, and `title` for category classification. Ignore `legacy_category` for final classification unless the prompt explicitly asks to audit stale exports.
- Treat `duplicate_of` as authoritative duplicate linkage, even when `status` or mirror fields look closed.
- Treat records with `status` of `Duplicate`, `Cancelled`, or `Canceled`, or with non-null `duplicate_of`, as non-primary.
- Treat `Closed`, `Done`, `Verified`, `Deployed`, `Complete`, and `Completed` as complete statuses for primary work.

## Portfolio Categories

Classify each primary item into exactly one category using signal priority. Check normalized `work_type`, `labels`, and `title` text; earlier categories win:

1. `Security`: security, cve, auth, encryption, compliance, audit, vulnerability.
2. `Reliability`: reliability, incident, outage, latency, flaky, bug.
3. `TechDebt`: tech debt, tech-debt, refactor, cleanup, migration, chore, dependency, deprecate, maintenance.
4. `NewFeature`: feature, enhancement, rollout, launch, experiment, new.

If no signal matches, choose the most defensible category from the prompt context and record rationale in scratch notes only.

## Portfolio Mix Tasks

For closed-work mix reviews:

- Filter primary work by prompt scope: quarter, teams, product area(s), and closed/completed status.
- Include only records whose `closed_at` falls within the requested quarter.
- Count items, not story points.
- Fetch the mix target row for the requested `scope_id`; target values may be fractions, so convert values at or below `1.0` to percentage points.
- Compute actual percentage as `count / total * 100`, rounded to one decimal place.
- Compute gap as `actual_pct - target_pct`, rounded to one decimal place.
- Order categories as `NewFeature`, `TechDebt`, `Reliability`, `Security` unless the template says otherwise.
- Order included IDs by `closed_at` ascending, then `id` ascending, unless the template says lexicographic ordering.
- Report duplicate and cancelled same-scope records separately when the template has exclusion fields.
- Under-invested categories are negative gaps sorted from most negative to least negative.
- Rebalance recommendations should target the largest negative gap. If a team owner is required, choose the team most associated with that deficit category in the included records; use prompt domain context as the tie breaker.

## SLA Aging Tasks

For SLA audits:

- Filter by prompt teams and requested categories after applying the category classifier.
- Include primary records created on or before the requested as-of date that are still active as of that date.
- Also include primary records completed inside the recent closed window. Use an inclusive window from `as_of - recent_closed_window_days` through `as_of`.
- Exclude duplicates from the primary denominator, but group duplicate records by `duplicate_of` when the duplicate points to an included primary record.
- Age open records from `created_at` through `as_of`; age closed records from `created_at` through `closed_at`.
- Bucket age days into `0-3`, `4-7`, `8-14`, `15-30`, and `31+`.
- A primary item is overdue when an active item has `due_at < as_of`, or a completed item has `closed_at > due_at`. Due on the as-of date is not overdue.
- Breach rate is `overdue_primary_count / included_primary_count`, rounded to three decimal places.
- Missing owners are included primary IDs where `owner` is null or blank.
- For team overdue counts, sort teams alphabetically.
- For top owner/team hotspot, count overdue primary records by `(team, owner)` and use `UNASSIGNED` for missing owner.
- For escalation queues, sort overdue primary records by severity rank `S1`, `S2`, `S3`, `S4`, then `due_at` ascending, `priority` ascending, and `id` ascending.

## Release Readiness Tasks

For release assessments:

- Fetch the release, release milestones, release work items, blockers, and dependencies.
- Use `release_id` and `milestone_id` from work items as release truth. Do not use stale mirror fields.
- Exclude duplicate/cancelled records from milestone denominators and readiness scoring.
- For each milestone, count complete primary work over primary total and round `completion_pct` to one decimal place. Sort milestones by `milestone_id`.
- Overall readiness score is complete primary release work divided by primary release work, rounded to three decimals.
- Count unresolved high-impact blockers by exact `cause`. High impact means blocker severity `High` or `Critical`; unresolved means no `resolved_at` and a status that is not resolved/closed/done.
- Include blocker cause counts even when the blocked work item is already complete if the template asks for unresolved high-impact blocker counts.
- Gating work item IDs are non-complete primary release items with unresolved high-impact blockers or critical dependency chains.
- For critical dependency chains, start from non-complete primary release work and follow dependency relations whose names indicate release blocking, security review, validation, or audit evidence. Include paths that end at a non-complete dependency item. Sort paths lexicographically by the full path.
- Use `NO_SHIP` when non-complete gating work, critical dependency chains, or unresolved critical blockers remain. Use `SHIP_WITH_WATCH` for residual non-critical risk after primary readiness is otherwise acceptable. Use `SHIP` only when primary release work is complete and no unresolved high-impact release risks remain.

## Output Checks

Before answering:

- Verify every required template key is present and no extra keys are present.
- Verify sort orders from the template, not from habit.
- Verify one-decimal and three-decimal rounding with numeric JSON values.
- Verify all ID lists are unique where the template expects sets.
- Verify duplicate/cancelled records are not counted in primary denominators.
- Verify no train/example IDs or scratch notes leak into the final JSON.
