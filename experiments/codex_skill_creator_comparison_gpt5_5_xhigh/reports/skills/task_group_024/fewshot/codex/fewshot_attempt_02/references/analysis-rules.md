# Engineering Portfolio Analysis Rules

Use these rules after reading the prompt and answer template. Template descriptions and explicit prompt instructions override any default here.

## Endpoint Map

Documented GET endpoints normally provide all required data:

- `/api/work-items`: work items with `id`, `status`, `duplicate_of`, `team`, `product_area`, `work_type`, `labels`, `title`, `owner`, `severity`, `priority`, `created_at`, `due_at`, `closed_at`, `release_id`, `milestone_id`, `mirror_status`, and `legacy_category`.
- `/api/mix-targets`: target rows keyed by `scope_id`, with category target fractions.
- `/api/sla-policy`: severity-to-days policy. Prefer a work item's `due_at` when present; use policy only when due dates must be derived.
- `/api/releases`, `/api/milestones`, `/api/dependencies`, `/api/blockers`: release readiness data.

If the API returns wrapper keys such as `work_items`, `mix_targets`, `sla_policy`, `releases`, `milestones`, `dependencies`, or `blockers`, unwrap them before analysis.

## Primary Records

- Treat a record as a duplicate when `duplicate_of` is non-null or `status` is `Duplicate`. Exclude it from primary denominators and counts.
- Treat `status` `Cancelled` as excluded work unless the template asks to report it.
- Treat `Closed`, `Done`, `Verified`, and `Deployed` as complete statuses.
- Treat statuses such as `Backlog`, `In Progress`, `Review`, `Reopened`, and `Blocked` as not complete.
- Use `status`, `closed_at`, `due_at`, `release_id`, and `milestone_id` as authoritative. Do not use `mirror_status` as truth.
- Do not use `legacy_category` as portfolio truth unless the prompt explicitly says to.

## Category Resolution

Classify each included item into exactly one portfolio category when a mix or SLA task needs categories. Use `work_type`, `labels`, and `title` together.

- Security signals: `Security`, `Compliance`, `security`, `cve`, `auth`, `encryption`, `compliance`.
- Reliability signals: `Reliability`, `Incident`, `Bug` with reliability context, `reliability`, `incident`, `outage`, `latency`, `flaky`.
- Tech debt signals: `Refactor`, `Dependency`, `Chore` with debt context, `refactor`, `cleanup`, `migration`, `dependency`, `deprecate`, `tech-debt`.
- New feature signals: `Feature`, `Enhancement`, `feature`, `rollout`, `customer-request`.

When signals conflict, prefer the signal that best explains the concrete work item instead of blindly counting keywords. Direct `work_type` values that already name a category are strong evidence. Security and reliability labels commonly override generic feature or enhancement wording. Refactor and dependency work commonly remain tech debt unless the item is clearly security or reliability work. Ignore stale mirror/export category fields.

## Portfolio Mix

1. Filter primary work to the prompt scope: quarter, teams, product areas, and closed work. For calendar quarters, include `closed_at` dates from the first day through the last day of the quarter.
2. Use item counts, not story points, unless the prompt explicitly asks for points.
3. Read target percentages from the `mix_targets` row named by the prompt's `scope_id` or target scope. Target fields are fractions; multiply by 100 for percentage-point output.
4. Count included items by category. Compute actual percentage as `count / total_included * 100`, rounded as requested.
5. Compute gap as `actual_pct - target_pct`, rounded to the requested precision.
6. Order category rows exactly as the template says. If the template is silent, use `NewFeature`, `TechDebt`, `Reliability`, `Security`.
7. Order included IDs by `closed_at` ascending, then `id` ascending, unless the template says to sort lexicographically.
8. Under-invested categories have negative gaps. Sort them from most negative to least negative.
9. For rebalance actions, choose the largest negative gap as the primary category. If the template asks for a secondary category, use the next negative gap or `null` when none exists. If no negative gaps exist, use the template's maintain-current-mix option when available.
10. For exclusion fields, include in-scope duplicate and cancelled or otherwise distracting records that looked related to the primary closed mix but were excluded. Use the ordering requested by the template.

## SLA Aging

1. Filter to primary records in the scoped teams and SLA categories.
2. Include open primary SLA work and primary SLA work closed within the recent closed window ending on the as-of date. Treat the window as inclusive unless the prompt says otherwise.
3. Determine overdue or breached work:
   - Open work is overdue when `due_at` is before the as-of date.
   - Closed work is a breach when `closed_at` is after `due_at`.
   - A due date equal to the as-of date is not overdue.
4. Compute age in days from `created_at` to `closed_at` for closed included work, otherwise from `created_at` to the as-of date.
5. Bucket ages inclusively as `0-3`, `4-7`, `8-14`, `15-30`, and `31+` when those buckets appear.
6. Compute breach rate as `overdue_or_breached_primary_count / included_primary_count`, rounded to the template precision.
7. Missing owner IDs are included primary records with null, empty, or absent owner.
8. Duplicate clusters report duplicate records in scope grouped by their `duplicate_of` primary ID. Sort clusters by `primary_id` and duplicate IDs lexicographically unless the template says otherwise.
9. For team overdue counts, group overdue primary records by team. For hotspots, group by team plus owner, using `UNASSIGNED` for missing owner. Break ties by team and owner lexicographically unless the prompt gives another rule.
10. For escalation queues, sort overdue primary work by severity order `S1`, `S2`, `S3`, `S4`, then earliest `due_at`, then ascending numeric priority, then ID.

## Release Readiness

1. Filter primary work where `release_id` matches the release under review. Exclude duplicates and cancelled records.
2. For each milestone in the release, count primary work assigned to that milestone. `complete_primary` is the count in complete statuses; `primary_total` is all primary work in that milestone.
3. Completion percentage is `complete_primary / primary_total * 100`, rounded as requested. When the denominator is zero, use `0.0` unless the prompt specifies otherwise.
4. Readiness score is completed primary release work divided by total primary release work, rounded as requested.
5. Count unresolved high-impact blockers by exact `cause` text. Treat blockers as unresolved when `resolved_at` is null and status is not closed or resolved. Treat `High` and `Critical` as high impact unless the prompt defines a different set.
6. Gating work item IDs are non-complete primary release work items that block readiness through unresolved high-impact blockers or critical dependency paths. Sort and deduplicate them.
7. For dependency chains, build a directed graph from `blocked_id` to `depends_on_id`. Start from blocked release work. Include ordered ID paths that end at a non-complete dependency relevant to readiness. Do not include paths whose terminal dependency is complete. Avoid cycles and sort paths lexicographically by the full path.
8. Ship decision defaults:
   - `NO_SHIP` when unresolved high-impact gating work or non-complete critical dependency chains remain.
   - `SHIP_WITH_WATCH` when readiness is otherwise acceptable but unresolved watch items or lower-impact blockers remain.
   - `SHIP` when primary work is complete and no readiness blockers remain.

## JSON Output

- Emit only the JSON answer.
- Use arrays in the exact order required by the template.
- Use exact enum strings from the template.
- Use JSON numbers for numeric fields, not strings, unless the template explicitly wants a string.
- Round only at the output boundary so internal calculations do not compound rounding error.
