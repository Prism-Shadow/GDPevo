---
name: portfolio-environment-analysis
description: Use for engineering portfolio environment tasks that require JSON answers from work items, mix targets, SLA policy, releases, milestones, blockers, dependencies, or the restricted SQL query endpoint. Covers portfolio mix reviews, SLA aging/breach audits, and release-readiness assessments.
---

# Portfolio Environment Analysis

## Start Every Task

1. Read the user's prompt and any supplied answer template/schema. The template is the output contract; match its keys, ordering notes, constants, rounding, and "JSON only" requirements exactly.
2. Read the runtime access file for the environment base URL, token, and allowed endpoints. Use only those access details for network calls.
3. Fetch authoritative data from the environment. Prefer endpoint JSON for clarity; use `POST /api/query` with `{"sql": "..."}` when a scoped SQL query is simpler.
4. Treat `status`, `closed_at`, `duplicate_of`, `work_type`, `labels`, `title`, `team`, `product_area`, `release_id`, and `milestone_id` as authoritative. Ignore stale/export fields such as `mirror_status` and `legacy_category` unless the prompt explicitly asks to report that they were ignored.

Expected endpoint families:

- `/api/work-items`: work items with ids, dates, status, duplicate link, team, product area, release/milestone ids, owner, severity, priority, work type, labels, title, and stale mirror/export fields.
- `/api/mix-targets`: target mix rows with `scope_id`, quarter, product area/team group, and category percentages stored as decimals.
- `/api/sla-policy`: severity-to-days policy. Use it only when an item lacks an authoritative `due_at`.
- `/api/releases`, `/api/releases/{release_id}`, `/api/milestones`, `/api/blockers`, `/api/dependencies`: release readiness data.

## Canonical Work Items

Use primary records for denominators and counts:

- Exclude records whose `status` is `Duplicate` or whose `duplicate_of` is populated.
- Exclude `Cancelled` records from primary populations unless the template asks for excluded/cancelled ids.
- If reporting duplicates, group them by `duplicate_of` when present and sort cluster `primary_id` values and `duplicate_ids` lexicographically. If a duplicate lacks a canonical id, report it only in the requested exclusion list.
- Complete statuses are `Closed`, `Done`, `Verified`, `Deployed`, and `Complete`. Treat `In Progress`, `Review`, `Backlog`, `Reopened`, `Blocked`, duplicates, and cancelled records as non-complete unless a task gives a narrower rule.

## Portfolio Category Resolution

When category signals conflict, classify from authoritative `work_type`, `labels`, and `title`; do not use `legacy_category` or `mirror_status`. Normalize strings to lowercase. Apply this precedence so each included item gets exactly one category:

1. `Security`: `work_type` is `Security` or `Compliance`, or labels/title include security signals such as `security`, `cve`, `auth`, `encryption`, or `compliance`.
2. `Reliability`: `work_type` is `Reliability`, `Incident`, or `Bug`, or labels/title include reliability signals such as `reliability`, `incident`, `outage`, `latency`, or `flaky`.
3. `TechDebt`: `work_type` is `Refactor`, `Chore`, or `Dependency`, or labels/title include debt signals such as `cleanup`, `refactor`, `migration`, `dependency`, `tech-debt`, or `legacy`.
4. `NewFeature`: `work_type` is `Feature` or `Enhancement`, or labels/title include feature signals such as `feature`, `rollout`, `enhancement`, or `customer-request`.

If no rule matches, inspect the item title/labels and choose the least surprising portfolio category, documenting nothing in the final JSON unless the schema asks for a flag.

## Portfolio Mix Reviews

Use this workflow for closed-work mix, target-gap, and rebalance tasks:

1. Parse the quarter, teams, product area(s), scope id, and target scope id from the prompt/template.
2. Convert the quarter to an inclusive closed-date range.
3. Select primary work items whose `team` and `product_area` match the scope, whose `closed_at` falls in the quarter, and whose authoritative status is complete.
4. Put excluded same-scope records in the requested flags/lists:
   - duplicate exclusions: `status == "Duplicate"` or `duplicate_of` populated;
   - cancelled exclusions: `status == "Cancelled"`;
   - other distractors: same-scope records that fail the primary closed-work rule.
5. Order included ids by `closed_at` ascending, then id ascending, unless the template says otherwise.
6. Count items by category. Use item counts, not story points.
7. Load the mix target row for the requested scope id. Convert decimal targets to percentage points by multiplying by 100.
8. For the standard categories in the order requested by the template, compute:
   - `actual_pct = count / total * 100`, rounded to 1 decimal;
   - `gap_pct = actual_pct - target_pct`, rounded to 1 decimal.
9. Under-invested categories are categories with negative gaps, sorted from most negative to least negative.
10. For rebalance recommendations, choose `REBALANCE_CAPACITY` when any gap is negative; the primary category is the largest deficit, and the secondary category is the next-largest deficit when the schema has room for one. If an `owner_team` is required, choose the team with the clearest responsibility for increasing that category from the scoped evidence, often the team already delivering that category or the team whose charter/name best matches the deficit.

## SLA Aging And Breach Audits

Use this workflow for SLA population, overdue, aging bucket, hotspot, duplicate cluster, missing owner, breach-rate, and escalation tasks:

1. Parse teams, categories, as-of date, and recent closed window from the prompt/template.
2. Select primary work items whose team is in scope, whose resolved portfolio category is in scope, and whose `created_at` is on or before the as-of date.
3. Include an item in the primary SLA population when, as of the snapshot, it is active or recently closed:
   - active: `closed_at` is null or after the as-of date;
   - recently closed: `closed_at` is between `as_of - recent_closed_window_days` and `as_of`, inclusive.
4. Exclude duplicates/cancelled records from the primary population, but report matching duplicate clusters when requested.
5. For each included primary item, set the resolution/snapshot date to `closed_at` if it is on or before the as-of date, otherwise the as-of date.
6. An item is overdue when `due_at` is before the resolution/snapshot date. If `due_at` is missing, compute it as `created_at + days_to_due` from the SLA policy for the item's severity. Due today is not overdue.
7. Aging bucket days are calendar days from `created_at` to the resolution/snapshot date. Use buckets `0-3`, `4-7`, `8-14`, `15-30`, and `31+`.
8. Sort id lists lexicographically unless the template defines another order.
9. Team overdue counts should include every scoped team requested by the template when possible, ordered as instructed, commonly alphabetically.
10. Hotspots are grouped by `(team, owner)` over overdue primary items; use `UNASSIGNED` for missing owners. Choose the largest count, then break ties deterministically by worse severity mix, earlier due date, team, owner.
11. Missing-owner ids are included primary items whose owner is null or blank.
12. Breach rate is `overdue_primary_count / included_primary_count`, rounded to 3 decimals.
13. Escalation queues should order overdue primary work by severity rank `S1`, `S2`, `S3`, `S4`, then earliest `due_at`, then priority number, then id.

## Release Readiness

Use this workflow for ship decisions, milestone completion, gating work, blockers, dependency chains, and readiness score:

1. Parse the release id. Fetch the release detail, milestones, blockers, dependencies, and all work items for the release.
2. Primary release work is `release_id` matching the release and not duplicate, not linked as a duplicate, and not cancelled.
3. For each milestone in the release, count primary work assigned to that milestone. `complete_primary` is the count with a complete authoritative status; `primary_total` is the denominator. `completion_pct` is rounded to 1 decimal. Sort milestone rows by `milestone_id` unless the template says otherwise.
4. Readiness score is total complete primary work divided by total primary work, rounded to 3 decimals.
5. Unresolved blockers have no `resolved_at` and status other than `Resolved`. High-impact blockers are severity `Critical` or `High`. Count high-impact unresolved blockers by exact `cause` text.
6. Gating work item ids are primary release work items that are non-complete and are blocked by a high-impact unresolved blocker or by a critical dependency chain. Sort and de-duplicate.
7. Critical dependency chains start at non-complete primary release work and follow dependency records whose relation indicates readiness/security/validation impact, such as `blocks-release-readiness`, `security-review-required`, `validation-required`, or `audit-evidence-required`. Stop and emit a path when the terminal dependency is non-complete and not duplicate/cancelled. Avoid cycles and sort paths lexicographically by the full id sequence.
8. Ship decision defaults:
   - `NO_SHIP` when high-impact unresolved blockers, gating work, or critical dependency chains remain.
   - `SHIP_WITH_WATCH` when no hard gate remains but readiness is below complete or lower-impact unresolved blockers remain.
   - `SHIP` when primary work is complete and no unresolved blockers or critical dependencies remain.
   Follow stricter task-specific decision criteria when supplied.

## Final JSON Discipline

- Return one JSON object and no prose when the task asks for JSON only.
- Preserve schema constants, required keys, array ordering rules, and category order exactly.
- Use JSON numbers for rounded numeric fields. Do not quote numbers unless the template explicitly requires strings.
- For empty results, output the schema-appropriate empty array/object rather than omitting the key.
