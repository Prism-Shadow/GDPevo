---
name: portfolio-work-auditor
description: Analyze engineering portfolio work-item datasets for portfolio mix, SLA aging, duplicate handling, and release readiness. Use when Codex must produce schema-constrained JSON answers from provided work-item, mix-target, SLA-policy, release, milestone, blocker, or dependency data while avoiding stale mirror/export fields.
---

# Portfolio Work Auditor

## Core Workflow

1. Read the prompt and the answer template before querying data. Treat the template as the output contract.
2. Load the authoritative task data made available by the user or runtime notes. Use structured parsing for JSON and SQL results.
3. Ignore stale mirror/export fields for business truth unless the prompt explicitly asks to report them. Prefer current work item fields such as `status`, `closed_at`, `duplicate_of`, `work_type`, `labels`, `title`, `release_id`, and `milestone_id`.
4. Build the analysis cohort first, then calculate metrics from that set. Do not calculate from story points unless the prompt explicitly asks for story-point weighting.
5. Sort and round exactly as requested by the template. Return only the requested JSON when the prompt says not to include prose.

## Portfolio Category Classification

Classify each primary work item into exactly one category.

Use these signals in order, while treating labels or titles containing `stale`, `mirror`, or `export` as warnings that the signal may be a trap:

1. `Security`: security/compliance work, including real vulnerability, CVE, auth, encryption, compliance, audit-evidence, or security-review intent. `Security` and `Compliance` work types usually land here. Generic feature/refactor/dependency work can still be security if the title and labels show a genuine security purpose.
2. `Reliability`: reliability, incident, bug, outage, latency, flaky, postmortem, recovery, retry, guardrail, or operational repair work. This can override generic `Feature`, `Enhancement`, or `Chore` types when the item is clearly about reliability work.
3. `TechDebt`: refactor, dependency, migration, cleanup, deprecation, chore, and maintenance work when there is no stronger security or reliability purpose.
4. `NewFeature`: feature, enhancement, rollout, customer-facing capability, and product polish work when no stronger category applies.

When security and reliability signals conflict, prefer the category that is the actual work objective in the title, not a stale or incidental label.

## Closed Portfolio Mix

Use this procedure for quarter-based closed-work mix reviews:

1. Filter by the prompt's quarter using `closed_at`.
2. Filter by the exact teams and product areas in scope.
3. Include primary closed work only: non-null `closed_at`, status not `Duplicate` or `Cancelled`, and no `duplicate_of`.
4. Include all rows that satisfy the real scope. Do not discard ordinary-looking same-scope rows just because other rows have generated-looking IDs.
5. Exclude same-scope duplicates, records pointing at another work item, and cancelled records from the denominator. Report them in the requested exclusion or distractor fields.
6. Count items by category. Compute actual percentages as `count / total * 100`.
7. Convert mix target fractions to percentage points before calculating gaps. `gap = actual_pct - target_pct`.
8. Round percentages and gaps to one decimal place unless the template says otherwise.
9. List under-invested categories with negative gaps from most negative to least negative. Break ties in the template's category order.
10. For rebalance actions, use the largest negative gap as the primary category. If a secondary/source category is requested, use the largest positive gap. If an owner team is requested, use team-level category evidence from the included work and the wording of the prompt to choose the team responsible for correcting that deficit.

## SLA Aging Audits

Use this procedure for SLA reliability/security audits:

1. Filter by the prompt's teams.
2. Classify category from authoritative work-item fields using the category rules above; include only the requested SLA categories.
3. Exclude cancelled records and duplicate records from the primary population. Treat any record with `duplicate_of` as a duplicate even if its `status` is not `Duplicate`.
4. Include primary work that was open as of the audit date, regardless of age: `created_at <= as_of` and either `closed_at` is missing or `closed_at > as_of`.
5. Also include primary work closed in the recent closed window, inclusive of both the window start and the audit date.
6. For closed items, evaluate overdue status at `closed_at`. For open-as-of items, evaluate overdue status at `as_of`.
7. A due date equal to the evaluation date is not overdue. Use `due_at < evaluation_date`.
8. Compute breach rate as `overdue_primary_count / included_primary_count`, rounded to three decimals.
9. For aging buckets, age each included primary item from `created_at` to `closed_at` for recent closed items, otherwise from `created_at` to `as_of`.
10. Count missing owners among included primary records with no owner.
11. Build duplicate clusters from duplicate records in the same SLA scope and time population. Group by canonical `duplicate_of`, sort clusters by `primary_id`, and sort duplicate IDs.
12. Team overdue counts include overdue primary records and are sorted alphabetically by team.
13. Hotspots are team-owner pairs with the most overdue primary records. Use `UNASSIGNED` for missing owners.
14. Escalation queues should include overdue primary work in severity order (`S1`, `S2`, `S3`, `S4`), then earliest `due_at`, then stable ID order unless the prompt specifies a different priority rule.

## Release Readiness

Use this procedure for release-readiness assessments:

1. Use release, milestone, work item, blocker, and dependency records as separate authoritative sources. Do not use stale mirrored release fields as truth.
2. Primary release work excludes duplicates, cancelled items, and records pointing at another primary via `duplicate_of`.
3. Treat `Closed`, `Done`, `Verified`, and `Deployed` as complete statuses. Treat `Backlog`, `In Progress`, `Review`, and `Reopened` as non-complete.
4. For each milestone, count complete primary work and total primary work, then compute `completion_pct = complete / total * 100`, rounded to one decimal.
5. Compute release readiness score as all complete primary release work divided by all primary release work, rounded to three decimals.
6. Gating work item IDs are sorted non-complete primary release work item IDs unless the prompt narrows the gating definition.
7. Count unresolved high-impact blockers by exact cause text. Use unresolved records with no resolution and severity equivalent to high or critical impact.
8. For critical dependency chains, start from release work and follow dependency relations that indicate readiness blocking or validation-critical work. Include ordered paths that end at a non-complete dependency target; omit paths ending at complete dependencies. Sort chains lexicographically by the full path.
9. Use `NO_SHIP` when unresolved critical/high blockers or non-complete gating work remain. Use `SHIP_WITH_WATCH` for lower-impact unresolved risk with otherwise complete readiness. Use `SHIP` only when the primary work is complete and no unresolved readiness blockers remain.

## Output Discipline

- Match the template keys exactly and avoid additional properties when a schema forbids them.
- Sort ID lists lexicographically unless the template requests chronological ordering.
- For chronological ordering, sort by date first and ID second.
- Preserve exact cause strings, category names, team names, and enum values from the data or template.
- Use JSON booleans and nulls, not string equivalents.
