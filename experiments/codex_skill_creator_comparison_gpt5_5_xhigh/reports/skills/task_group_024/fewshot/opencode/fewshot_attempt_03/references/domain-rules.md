# Domain Rules

These rules are distilled from the portfolio environment examples. Apply the user prompt and `answer_template.json` first; use these conventions when the prompt leaves mechanics implicit.

## API Shape

Common GET endpoints return wrapper objects:

- `/api/work-items` -> `{"count": ..., "work_items": [...]}`
- `/api/work-items/{item_id}` -> `{"work_item": {...}}`
- `/api/mix-targets` -> `{"mix_targets": [...]}`
- `/api/sla-policy` -> `{"sla_policy": [...]}`
- `/api/releases` -> `{"releases": [...]}`
- `/api/releases/{release_id}` -> release details with release, milestones, and blockers
- `/api/milestones` -> `{"milestones": [...]}`
- `/api/dependencies` -> `{"dependencies": [...]}`
- `/api/blockers` -> `{"blockers": [...]}`

The SQL/query endpoint may require an `X-Env-Token`. If the runtime access notes do not provide one, solve from the GET endpoints.

## Canonical Work Item Rules

Use `status`, not `mirror_status`, to decide state. Treat these statuses as complete for denominator/completion logic:

```text
Closed, Done, Verified, Deployed
```

Treat these records as non-primary unless a task explicitly asks to report them:

- `status == "Duplicate"`
- `status == "Cancelled"`
- `duplicate_of` is not null

For duplicate reporting, group duplicate rows by `duplicate_of` and sort duplicate IDs as requested. If a prompt asks for distractors, include same-scope duplicate/cancelled/non-primary records that look like they belong to the scope but fail the primary inclusion rules.

## Portfolio Category Resolution

Classify each primary work item into exactly one category by checking authoritative `work_type`, `labels`, and `title`. Ignore `legacy_category`.

Use the first matching category in this precedence order:

1. `Security`: `work_type` is `Security` or `Compliance`, or labels/title include signals such as `security`, `cve`, `auth`, `encryption`, `consent`, or `appsec`.
2. `Reliability`: `work_type` is `Reliability`, `Incident`, or `Bug`, or labels/title include `reliability`, `incident`, `outage`, `latency`, `flaky`, `retry`, or `rehearsal`.
3. `TechDebt`: `work_type` is `Refactor`, `Chore`, or `Dependency`, or labels/title include `cleanup`, `refactor`, `migration`, `dependency`, `deprecate`, or `maintenance`.
4. `NewFeature`: `work_type` is `Feature` or `Enhancement`, or labels/title include `feature`, `rollout`, `customer-request`, `polish`, or `experiment`.

This precedence matters: for example, a feature-like item with auth/security signals is Security, and a feature-like item with only cleanup/migration signals is TechDebt.

## Portfolio Mix Reviews

Primary included work:

1. Match the prompt's quarter, teams, product area, and scope.
2. Include only primary records with a complete status and `closed_at` inside the quarter date range.
3. Exclude duplicates, records with `duplicate_of`, cancelled records, and stale mirror/export distractors from primary counts.
4. Order included IDs by `closed_at` ascending, then ID ascending, when the template asks for portfolio closed-work ordering.

Mix calculation:

- Use item counts, not story points.
- Match the mix target by the requested `scope_id`.
- Convert target fractions to percentage points by multiplying by 100.
- Compute `actual_pct = count / total_included * 100`.
- Compute `gap_pct = actual_pct - target_pct`.
- Round displayed percentage-point values to one decimal.
- List mix rows in the category order requested by the template; otherwise use `NewFeature`, `TechDebt`, `Reliability`, `Security`.
- Under-invested categories are categories with negative gaps, ordered from most negative to least negative.
- The largest deficit category is the most negative gap.

Recommendation fields:

- Use a rebalance action when any gap is negative.
- Use the largest negative gap as the primary category; use the second-largest negative gap as a secondary category when the template has one.
- If the template asks for an owner team, choose the team most directly associated with the deficit category in the scoped work or candidate backlog; use prompt/template tie-breaking when present.
- Use a maintain-current-mix style action only when no category is under target.
- Use a data-quality action only when authoritative fields conflict so badly that the population or target cannot be trusted.

## SLA Aging Audits

Primary SLA population:

1. Match scoped teams.
2. Resolve category with the portfolio category resolver, then keep only requested SLA categories, usually `Security` and `Reliability`.
3. Exclude duplicates, records with `duplicate_of`, and cancelled records from primary counts.
4. Include primary records that are not complete.
5. Also include primary complete records whose `closed_at` falls in the recent closed window ending on the as-of date.

SLA dates and aging:

- Use the work item's `due_at` as the SLA due date when present. Use `/api/sla-policy` only to interpret or reconstruct missing SLA due dates.
- For open/non-complete records, age is `as_of - created_at` in whole calendar days.
- For complete recently closed records, age is `closed_at - created_at`.
- Bucket ages with inclusive ranges: `0-3`, `4-7`, `8-14`, `15-30`, `31+`.

Overdue logic:

- A non-complete item is overdue only when `due_at < as_of`.
- A complete item is overdue only when `closed_at > due_at`.
- Due today is not overdue.

SLA outputs:

- Sort primary and overdue ID lists lexicographically unless a queue field defines a priority order.
- Missing owner IDs are included primary records with `owner` null or empty.
- Team overdue counts count overdue primary records and are sorted by team name unless the template says otherwise.
- For owner/team hotspots, use `UNASSIGNED` for missing owners and pick the owner/team pair with the highest overdue count. Tie-break by team then owner for stability.
- Breach rate is `overdue_primary_count / included_primary_count`, rounded to three decimals.
- Escalation queues order overdue primary work by severity (`S1`, `S2`, `S3`, `S4`), then `due_at` ascending, then numeric `priority` ascending, then ID.

## Release Readiness

Release truth:

- Use `/api/releases/{release_id}` plus `/api/milestones`, `/api/work-items`, `/api/blockers`, and `/api/dependencies`.
- Treat a work item as release work when `release_id` matches the release or its `milestone_id` belongs to the release.
- Exclude duplicate/cancelled/non-primary records from milestone denominators.
- Do not use mirror fields as release truth.

Milestone completion:

- For every milestone in the release, count primary release work assigned to that milestone.
- `complete_primary` is the count with a complete status.
- `primary_total` is the primary denominator for that milestone.
- `completion_pct = complete_primary / primary_total * 100`, rounded to one decimal.
- Sort milestone rows by `milestone_id` ascending.

Readiness and blockers:

- `readiness_score = total_complete_primary / total_primary`, rounded to three decimals.
- High-impact blockers are unresolved blockers with severity `High` or `Critical`. Treat a blocker as unresolved when `resolved_at` is null and status is not a resolved/closed status.
- `blocker_cause_counts` counts unresolved high-impact blockers by exact `cause` string for the release.
- `gating_work_item_ids` are non-complete primary release work items that have an unresolved high-impact blocker or a dependency chain to a non-complete dependency.

Dependency chains:

- Build directed edges from `blocked_id` to `depends_on_id`.
- Start from non-complete primary release work.
- Follow dependency edges until you reach a non-complete dependency, avoiding cycles.
- Emit each path as an ordered ID array from release work to the non-complete dependency.
- Sort chains lexicographically by the full path.

Ship decision:

- Use `NO_SHIP` when there are non-complete gating work items caused by high-impact blockers or critical dependency chains.
- Use `SHIP_WITH_WATCH` when there are no no-ship gates but readiness is below 1.0 or unresolved lower-impact blockers/dependencies remain.
- Use `SHIP` when all primary release work is complete and no unresolved blockers/dependency gates remain.

## Output Discipline

Keep the final answer as JSON only. Preserve required key names from the template, use arrays/objects exactly as shaped, and do not include example IDs or values from prior tasks. If the template is a schema, obey `additionalProperties`, `const`, enum, ordering, and required-field constraints. If the template uses placeholder strings, replace them with correctly typed JSON values.
