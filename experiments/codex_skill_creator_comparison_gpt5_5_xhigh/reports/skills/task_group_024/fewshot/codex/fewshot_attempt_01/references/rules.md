# Environment Rules

## Primary Records

Treat a work item as non-primary when `status` is `Duplicate` or `Cancelled`, or when `duplicate_of` points at another work item. Report duplicates separately when the template asks for duplicate clusters. Report cancelled records separately only when the template asks for them.

Completion statuses are `Closed`, `Done`, `Verified`, and `Deployed`. Use `status`, not `mirror_status`, for completion.

For portfolio closed-work scopes, include primary work with `closed_at` inside the requested quarter, matching all scoped teams and product areas. Order included ids by `closed_at` ascending, then id ascending, unless the template says otherwise.

For SLA scopes, include primary SLA-relevant work created on or before the as-of date that is either still open at the as-of date or closed within the recent closed window. Exclude records closed after the as-of date. Apply the same temporal and scope filter before building duplicate clusters.

## Portfolio Category Resolution

Classify each primary item into exactly one category using current fields only.

Use this precedence:

1. `Security` for explicit security work: `work_type` of `Security` or `Compliance`, labels/title containing `security`, `cve`, `compliance`, or AppSec evidence language.
2. `Reliability` for reliability work: `work_type` of `Incident`, `Reliability`, or `Bug`, or labels/title containing `reliability`, `incident`, `outage`, `latency`, or `flaky`.
3. `TechDebt` for maintenance work: `work_type` of `Refactor`, `Dependency`, or `Chore`, or labels/title containing `refactor`, `dependency`, `deprecate`, or cleanup/migration language when the item is not otherwise feature-like.
4. `Security` for identity/security fallback signals on otherwise feature-like work: product area `Identity` or `Security Operations`, team `AppSec`, or labels/title containing `auth`, `encryption`, or `consent`.
5. `NewFeature` for `Feature` or `Enhancement` work, or labels/title containing `feature` or `rollout`.

If a task's prompt states a different convention, follow the prompt. If the data is contradictory, prefer `work_type`, labels, title, team, and product area over `legacy_category`.

Portfolio targets in `mix_targets` are fractions. Convert to percentage points by multiplying by 100, then round target, actual, and gap values to one decimal place. Count items, not story points.

Under-invested categories are categories whose gap is negative, ordered from most negative to least negative. The default rebalance action is `REBALANCE_CAPACITY` toward the largest negative gap; use a secondary category for the next largest negative gap when the template asks for it.

## SLA Aging

SLA category membership is stricter than portfolio mix fallback. Count direct security work when `work_type` is `Security` or `Compliance`, or current labels/title contain `security`, `cve`, `compliance`, `auth`, or `encryption`. Count direct reliability work when `work_type` is `Incident`, `Reliability`, or `Bug`, or current labels/title contain `reliability`, `incident`, `outage`, `latency`, or `flaky`. Do not use product-area or team fallback alone for SLA relevance.

For each included primary item:

- The age end date is `closed_at` for records closed on or before the as-of date, otherwise the as-of date.
- `age_days = age_end_date - created_at`.
- Use aging buckets `0-3`, `4-7`, `8-14`, `15-30`, and `31+`, inclusive at both ends.
- An item is overdue when `due_at` is before the age end date. A due date equal to the age end date is not overdue.

For overdue summaries:

- Sort id lists lexicographically unless an escalation queue is requested.
- Build team overdue counts for scoped teams in alphabetical order.
- Group duplicate clusters by `duplicate_of`, with clusters sorted by `primary_id` and duplicate ids sorted lexicographically.
- Missing owners are included primary items with null, empty, or missing `owner`.
- Use `UNASSIGNED` only for owner/team hotspot grouping when the template requires a display value.
- Breach rate is `overdue primary count / included primary count`, rounded to three decimal places.

For escalation queues, sort overdue primary work by severity rank `S1`, `S2`, `S3`, `S4`, then by largest days overdue, then numeric priority ascending, then due date ascending, then id ascending.

## Release Readiness

For a release assessment:

1. Fetch the release detail, milestones, blockers, dependencies, and all work items for the release id.
2. Build the primary denominator from work items whose `release_id` matches and that are not duplicate/cancelled records.
3. Compute milestone totals from primary release work grouped by `milestone_id`; sort milestone rows by `milestone_id`.
4. A primary release item is complete when `status` is one of the completion statuses.
5. Count unresolved high-impact blockers where `release_id` matches, `resolved_at` is null, status is not resolved, and severity is `High` or `Critical`. Key blocker counts by exact `cause`.
6. Gating work item ids are non-complete primary release work items with unresolved high-impact blockers.
7. Critical dependency chains start at non-complete primary release work and follow dependency edges to a non-complete, non-duplicate dependency. Keep each chain as an ordered id path and sort chains lexicographically by the full path.
8. Readiness score is complete primary release work divided by primary release work, rounded to three decimal places.

Use `NO_SHIP` when high-impact gates or critical dependency chains remain. Use `SHIP_WITH_WATCH` when there are unresolved lower-impact blockers or incomplete non-gating work but no high-impact gates. Use `SHIP` only when the primary release work is complete and no unresolved blockers remain.
