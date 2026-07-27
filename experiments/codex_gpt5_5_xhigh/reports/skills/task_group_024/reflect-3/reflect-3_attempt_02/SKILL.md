---
name: engineering-portfolio-audits
description: Analyze engineering portfolio work-item datasets for portfolio mix, SLA aging, and release-readiness answers. Use when Codex must produce strict JSON from work items, mix targets, SLA policy data, releases, milestones, blockers, and dependencies, especially when records contain duplicates, cancelled items, stale mirror fields, or conflicting category signals.
---

# Engineering Portfolio Audits

## Core Workflow

1. Read the user prompt and the supplied answer template before calculating. Match the template exactly: required keys, casing, ordering, precision, and no extra prose.
2. Load the relevant runtime access notes and retrieve the authoritative records named by the prompt. Prefer structured queries for cross-checking filters and joins.
3. Build the primary population from explicit scope fields such as team, product area, release, quarter, as-of date, and category. Do not infer scope from ID prefixes.
4. Exclude non-primary records before calculating metrics:
   - Exclude `status == "Duplicate"` and any record with `duplicate_of` set.
   - Exclude `status == "Cancelled"`.
   - Report duplicates, cancellations, or distractors only when the template asks for them.
5. Use authoritative fields for truth. Treat `mirror_status` and `legacy_category` as stale/export fields unless the prompt explicitly asks to flag that they were ignored.

## Portfolio Mix

Use this for closed-work mix reviews.

1. Filter by the prompt's quarter using `closed_at`, with quarter start inclusive and next quarter start exclusive.
2. Require the scoped teams and product areas. Include every matching primary closed item, including non-prefixed IDs.
3. Order included IDs by `closed_at` ascending, then `id` ascending, unless the template says otherwise.
4. Count items, not story points. Compute actual percentages as `count / total * 100`, rounded to one decimal place.
5. Convert target fractions to percentage points. Compute `gap_pct = actual_pct - target_pct`.
6. Under-invested categories are categories with negative gaps, ordered from most negative to least negative.
7. Recommend rebalancing toward the largest negative gap. If a secondary category is required, use the next negative gap. If an owner team is required, infer it from the prompt's team responsibilities and the category/product deficit, not from stale legacy fields.

### Category Resolution

Assign each primary item to exactly one category. Use current `work_type`, labels, and title together; use stale fields only as tie-breaker evidence if the prompt allows it.

- `Security`: security audits, CVE work, compliance/security evidence, auth/encryption work when the item's main intent is security. `work_type` values such as `Security` and security-labeled `Compliance` usually land here.
- `Reliability`: incidents, outages, latency/flaky repair, reliability guardrails, postmortems, and recovery work. `work_type` values such as `Reliability` and `Incident` usually land here.
- `TechDebt`: refactor, migration, cleanup, dependency, deprecation, and chore work when the main intent is maintainability rather than security or reliability.
- `NewFeature`: feature, rollout, enhancement, polish, and user/product capability work when security/reliability terms are incidental or stale.

When signals conflict, prefer the item's main operational intent over a single stale-looking label. For example, a feature rollout with an incidental security label stays `NewFeature`, while a CVE/security patch delivered via dependency work stays `Security`.

## SLA Aging

Use this for security/reliability SLA audits.

1. Build the SLA population from primary Security/Reliability work in the scoped teams.
2. For an as-of audit, include items created on or before the as-of date that are active as of that date, plus primary items closed inside the recent closed window. Treat items closed after the as-of date as active at the as-of date.
3. Exclude records created after the as-of date.
4. Use `due_at` for breach status when present. Use SLA policy only to derive or verify due dates when the prompt or data requires it.
5. Treat open/active work as overdue when `due_at` is before the as-of date. A due date equal to the as-of date is due, not overdue.
6. Treat recently closed work as breached when `closed_at` is after `due_at`.
7. Breach rate is `overdue_or_breached_primary_count / included_primary_count`, rounded to three decimal places.
8. Missing-owner lists include included primary records whose `owner` is null.
9. Duplicate clusters group duplicate IDs under their canonical `duplicate_of` primary ID, with both clusters and duplicate IDs sorted as the template requires.
10. For aging buckets, calculate item age consistently from `created_at` to the as-of date for active items. If the template asks for resolved age, use `closed_at` for recently closed items.
11. Escalation queues should prioritize active overdue work by `priority` ascending, then severity (`S1` before `S2` before `S3` before `S4`), then oldest `due_at`, then `id`. Include closed breaches in the queue only if the template defines the queue as all overdue primary IDs.

## Release Readiness

Use this for release ship/no-ship assessments.

1. Primary release work is work with the target `release_id`, excluding duplicates and cancellations.
2. Complete statuses are `Closed`, `Done`, `Verified`, and `Deployed`. Non-complete statuses include `Backlog`, `In Progress`, `Review`, and `Reopened`.
3. Milestone completion uses all milestones for the release, sorted by milestone ID. For each milestone, count complete primary work and total primary work, then round completion percentage to one decimal place.
4. Gating work item IDs are non-complete primary release items, sorted with no duplicates.
5. Unresolved high-impact blocker counts include blockers with no resolution and high-impact severities such as `High` or `Critical`. Count by exact `cause` text.
6. Dependency chains are ordered paths from release work to a non-complete dependency when dependency records indicate release readiness, validation, security review, audit evidence, or an explicit blocking relationship. Sort chains lexicographically by the full path.
7. Readiness score is complete primary release work divided by primary release work, rounded to three decimal places.
8. Use `NO_SHIP` when critical/high-impact unresolved blockers or non-complete readiness gates remain. Use `SHIP_WITH_WATCH` for low-risk unresolved watch items, and `SHIP` only when primary work is complete and no readiness blockers remain.

## Output Discipline

- Return exactly the JSON object requested by the template.
- Preserve enum casing such as `NewFeature`, `TechDebt`, `Reliability`, and `Security`.
- Use lexicographic ID ordering unless the template specifies date ordering.
- Round only at the output boundary.
- Do not include source notes, calculations, or prose outside the JSON.
