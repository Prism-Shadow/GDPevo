---
name: engineering-portfolio-auditor
description: Analyze engineering portfolio environments for closed-work mix, SLA aging, and release-readiness tasks. Use when a prompt asks Codex to inspect work items, mix targets, SLA policy, releases, milestones, blockers, or dependencies and return an exact JSON answer following a supplied template.
---

# Engineering Portfolio Auditor

## Core Workflow

1. Read the user prompt and answer template first. Treat the template as the output contract: exact keys, ordering notes, rounding precision, and no prose unless requested.
2. Read the runtime access notes supplied with the task and query the provided environment for the authoritative records needed by the prompt.
3. Build a small working table before calculating: include `id`, `status`, `duplicate_of`, `team`, `product_area`, `work_type`, `labels`, `title`, `owner`, `created_at`, `due_at`, `closed_at`, `severity`, `priority`, `release_id`, and `milestone_id` when present.
4. Use authoritative current fields. Do not use stale mirror/export fields or legacy category fields to decide inclusion, completion, or category.
5. Return only JSON matching the template. Sort and round exactly as the prompt says.

## Primary Records

- Treat records with `duplicate_of` set, or current `status` of `Duplicate`, as non-primary. Report them only in duplicate or exclusion fields when the template asks.
- Treat current `status` of `Cancelled` as non-primary unless the prompt explicitly asks for cancelled records. Report them as exclusions or distractors when requested.
- Do not exclude a record just because its ID format looks different from nearby records. If it matches the authoritative scope and is primary, count it.
- For completed work, prefer current `status` over mirror fields. Common complete statuses are `Done`, `Closed`, `Verified`, and `Deployed`.
- For closed-window tasks, use `closed_at` for quarter/window membership and for closed-date ordering.

## Portfolio Mix

Use item counts, not story points.

1. Filter by the prompt scope: quarter, teams, product areas, and any scope-specific target row.
2. Include primary records closed in the requested quarter/window.
3. Exclude duplicates and cancelled records, but list them in the requested exclusion or distractor fields.
4. Classify each included item into exactly one category:
   - `Security`: current security/compliance work, especially `work_type` of `Security` or `Compliance`, or non-stale title/label signals such as cve, security, encryption audit, auth security, or security exception.
   - `Reliability`: reliability or incident work, especially `work_type` of `Reliability` or `Incident`, or non-stale title/label signals such as outage, incident, latency, flaky reliability, postmortem, guardrail, or runbook.
   - `TechDebt`: refactor, chore, dependency, migration, cleanup, or maintenance work when stronger security/reliability signals do not define the item.
   - `NewFeature`: feature or enhancement work when stronger security/reliability signals do not define the item.
5. Resolve conflicts using current `work_type` plus the non-stale title. Labels help classify generic bugs, chores, compliance, and enhancements, but an isolated stale label or legacy category should not override clear current work intent.
6. Convert target fractions to percentage points. Round actual percentages and gaps to one decimal place. Compute `gap = actual_pct - target_pct`.
7. List under-invested categories as negative gaps ordered from most negative to least negative. For a rebalance recommendation, choose the largest deficit as the target category and the largest surplus as the source signal unless the prompt gives a different rule.

## SLA Aging

1. Filter primary work by the requested teams and portfolio categories.
2. Include work that is open as of the as-of date, plus primary work closed within the recent closed lookback window when the prompt includes one.
3. Keep duplicate clusters separate from the primary population. Group by canonical `duplicate_of`, sort cluster primary IDs and duplicate IDs lexicographically.
4. Use `due_at` as the breach boundary unless the prompt explicitly directs policy-derived due dates. An open item is overdue when `due_at` is before the as-of date. A closed item breached when `closed_at` is after `due_at`.
5. Treat items due exactly on the as-of date as due today, not overdue, unless the prompt states otherwise.
6. For aging buckets, count included primary records by age in days from `created_at` to `closed_at` for recently closed work, otherwise from `created_at` to the as-of date. Use the bucket boundaries exactly as named.
7. Count missing owners only among included primary records. Use `UNASSIGNED` for hotspot grouping when the owner is missing.
8. Compute breach rate as overdue primary count divided by included primary count, rounded to the requested precision.
9. For escalation queues, sort overdue primary work by severity (`S1` before `S2` before `S3` before `S4`), then priority number ascending, then due date ascending, then ID. If the prompt frames the queue as active follow-up, put still-open overdue work before recently closed breaches.

## Release Readiness

1. Use release membership from authoritative release/work item fields, not mirror fields.
2. Build milestone denominators from primary release work items. Exclude duplicate and cancelled release rows from primary totals.
3. Count complete work with current complete statuses such as `Done`, `Closed`, `Verified`, and `Deployed`.
4. Sort milestone rows by milestone ID. Round completion percentages to one decimal place.
5. Gating work item IDs are primary release work items that are not complete, sorted with no duplicates, unless the prompt narrows the definition.
6. Count unresolved high-impact blockers by exact cause text. Treat unresolved as not resolved; treat high impact as `High` and `Critical` unless the prompt defines another severity set.
7. Build dependency chains from release work toward dependencies whose authoritative status is not complete. Prefer readiness-blocking and validation relations when distinguishing critical chains. Sort paths lexicographically by the full ordered path.
8. Use `NO_SHIP` when unresolved high-impact blockers or non-complete readiness gates remain. Use `SHIP_WITH_WATCH` for only low-impact or monitoring concerns. Use `SHIP` only when primary work is complete and no unresolved readiness blockers remain.
9. Readiness score is completed primary release work divided by the primary denominator, rounded to three decimals unless the template says otherwise.

## Output Discipline

- Follow template-specific ordering even when it differs from these defaults.
- Sort ID lists lexicographically unless the prompt or template asks for closed-date ordering.
- Do not add fields, comments, markdown, or explanatory prose to the JSON answer.
