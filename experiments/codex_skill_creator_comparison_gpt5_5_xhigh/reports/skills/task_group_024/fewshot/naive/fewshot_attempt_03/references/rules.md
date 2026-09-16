# Portfolio Environment Rules

Use these rules after reading the prompt and answer template.

## Data Access

- Use only endpoints allowed by the runtime access file.
- Do not call `/api/judge`.
- The GET endpoints return enough data for these tasks; SQL is optional for inspection.
- Treat `mirror_status` and `legacy_category` as stale mirror/export fields. Do not use them for status, closure, primary/duplicate, or category decisions.

## Primary Work And Status

- Primary work excludes any item whose `status` is `Duplicate` or `Cancelled`.
- Primary work also excludes any item with `duplicate_of` set, even if its current `status` looks closed.
- Complete statuses are `Closed`, `Done`, `Deployed`, and `Verified`.
- Non-complete statuses include `Backlog`, `In Progress`, `Review`, and `Reopened`.
- When a prompt is as-of dated, use dates as the temporal truth. A record closed after the as-of date is still open for that as-of analysis.

## Portfolio Category Precedence

Classify from authoritative `work_type`, `labels`, and `title`, not from legacy category fields. Use the first matching group:

1. `Security`: work type or terms such as `Security`, `Compliance`, `security`, `cve`, `auth`, `encryption`, `compliance`.
2. `Reliability`: work type or terms such as `Reliability`, `Incident`, `Bug`, `reliability`, `incident`, `outage`, `latency`, `flaky`.
3. `TechDebt`: work type or terms such as `Refactor`, `Chore`, `Dependency`, `refactor`, `cleanup`, `migration`, `dependency`, `tech debt`.
4. `NewFeature`: work type or terms such as `Feature`, `Enhancement`, `feature`, `rollout`, `customer-request`, `new`.

This precedence is important: security terms override reliability, reliability overrides tech debt, and tech debt overrides feature signals.

## Portfolio Mix

- Include closed primary items in the requested quarter, teams, and product area(s).
- Closed portfolio work requires `closed_at` inside the quarter and a complete status.
- Sort included IDs by `closed_at` ascending, then `id` ascending unless the template says otherwise.
- Use count-based mix, not story points.
- Category order is `NewFeature`, `TechDebt`, `Reliability`, `Security`.
- Convert mix target fractions to percentage points and round target, actual, and gap values to one decimal place.
- `gap_pct = actual_pct - target_pct`.
- Under-invested categories are those with negative gaps, ordered from most negative to least negative.
- Follow-up action should rebalance toward the largest negative gap. If a template asks for a secondary category, use the second-largest negative gap or `null` if none exists.
- Exclusion lists should report in-scope duplicate and cancelled records. For broad "distractor" fields, include duplicate, `duplicate_of`, and cancelled records in scope.

## SLA Aging

- Include primary records for the requested teams and categories that were created on or before the as-of date and are either open on the as-of date or closed within the recent closed window.
- Open on as-of means `closed_at` is missing or after the as-of date.
- Recently closed means `closed_at` is on or before as-of and on or after `as_of - recent_closed_window_days`.
- Determine overdue by authoritative `due_at`:
  - Open items are overdue when `as_of > due_at`.
  - Recently closed items are overdue when `closed_at > due_at`.
  - Due on the as-of date is not overdue.
- Aging bucket days are elapsed days from `created_at` to `as_of` for open items, or from `created_at` to `closed_at` for recently closed items.
- Use buckets `0-3`, `4-7`, `8-14`, `15-30`, and `31+`.
- Report duplicate clusters for in-scope duplicate records whose `duplicate_of` points at an included primary item. Sort clusters by `primary_id` and duplicate IDs lexicographically.
- Missing owner IDs are included primary records with no `owner`.
- Breach rate is overdue primary count divided by included primary count, rounded to three decimals.
- For escalation queues, sort overdue primary work by severity rank `S1`, `S2`, `S3`, `S4`, then by earliest `due_at`, then by ID.

## Release Readiness

- Use `release_id` on work items as release truth. Do not infer release membership from stale mirrors.
- Milestone denominators count primary release work in that milestone.
- Milestone complete counts use complete statuses among primary release work.
- Readiness score is total complete primary release work divided by total primary release work, rounded to three decimals.
- Count unresolved high-impact blockers when `severity` is `High` or `Critical`, `resolved_at` is missing, and `status` is not `Resolved`.
- Blocker cause counts use exact `cause` strings.
- Gating work item IDs are non-complete primary release work items with unresolved high-impact blockers.
- Critical dependency chains start from non-complete primary release work and follow readiness-critical relations such as `blocks-release-readiness`, `validation-required`, `security-review-required`, `audit-evidence-required`, and `implementation-dependency`. Ignore plain `depends-on` relations unless the prompt explicitly includes them.
- Emit dependency chains only when the dependency is a non-complete primary work item; ignore duplicate and cancelled dependency targets.
- Ship decision heuristic:
  - `NO_SHIP` if there are gating IDs, critical dependency chains, or readiness score below 0.8.
  - `SHIP_WITH_WATCH` if readiness is incomplete or unresolved blockers remain but there are no no-ship gates.
  - `SHIP` only when all primary work is complete and no unresolved blockers remain.
