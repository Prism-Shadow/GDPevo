# Calculation Rules

## Field Precedence

Use current authoritative work-item fields first:

- Status and completion: `status`, not `mirror_status`.
- Category: `work_type`, `labels`, and `title`; use `legacy_category` only as a last-resort tie-breaker when current signals are generic and the task requires every item to land in one category.
- Duplicates: `status == "Duplicate"` or non-null `duplicate_of`.
- Cancelled records: `status == "Cancelled"`.

Primary records are not duplicates and not cancelled.

## Status Sets

Use completed statuses for closed portfolio and release denominator work:

```text
Closed, Done, Verified, Deployed
```

Treat these as non-complete unless the prompt says otherwise:

```text
Backlog, In Progress, Review, Blocked, Reopened
```

`Duplicate` and `Cancelled` are exclusion statuses, not completion states.

## Portfolio Category Classification

Assign exactly one category in this order, using lowercase comparisons over `work_type`, `labels`, and `title`:

1. `Security`: strong security evidence, including work type `Security` or `Compliance`, labels/title terms such as `security`, `cve`, `encryption`, `compliance`, or authentication work that is not better explained as tech debt.
2. `Reliability`: reliability evidence, including work type `Reliability`, `Incident`, or reliability-flavored `Bug`; labels/title terms such as `reliability`, `incident`, `outage`, `latency`, or `flaky`.
3. `TechDebt`: maintenance evidence, including work type `Refactor`, `Chore`, or `Dependency`; labels/title terms such as `refactor`, `cleanup`, `migration`, or `dependency`.
4. `NewFeature`: product-building evidence, including work type `Feature` or `Enhancement`; labels/title terms such as `feature`, `rollout`, `experiment`, `launch`, or `customer-request`.

When signals conflict, prefer the more risk-oriented category over generic feature language: security before reliability before tech debt before new feature. A tech-debt work type with only weak security language such as an incidental `auth` term can remain `TechDebt`; explicit `security`, `cve`, `encryption`, or `compliance` moves it to `Security`.

For SLA tasks that ask for Security and Reliability categories, use the same classifier and include only primary records whose resolved category is in scope.

## Portfolio Mix

Use item counts as the denominator unless the prompt explicitly asks for story points.

```text
actual_pct = round(count / total_included * 100, 1)
target_pct = round(target_fraction * 100, 1)
gap_pct = round(actual_pct - target_pct, 1)
```

Use `0.0` percentages when the denominator is zero. Keep category rows in the template-requested order, commonly `NewFeature`, `TechDebt`, `Reliability`, `Security`.

## Dates

Quarter bounds are inclusive:

```text
Q1: Jan 1 through Mar 31
Q2: Apr 1 through Jun 30
Q3: Jul 1 through Sep 30
Q4: Oct 1 through Dec 31
```

For a recent closed window, include closed work where:

```text
as_of - recent_closed_window_days <= closed_at <= as_of
```

For overdue checks, a due date equal to the as-of date is not overdue.

## SLA Aging

Include primary open work plus primary work closed inside the recent window. Exclude duplicates from the primary population but report duplicate clusters when requested.

Overdue rules:

- Open item: `due_at < as_of`.
- Recently closed item: `closed_at > due_at`.

Age is measured in whole calendar days:

```text
age_days = min(closed_at, as_of) - created_at
```

Bucket using inclusive ranges:

```text
0-3, 4-7, 8-14, 15-30, 31+
```

Breach rate:

```text
round(overdue_primary_count / included_primary_count, 3)
```

Use `0.000` when there are no included primary records.

## Duplicate Clusters

For every duplicate in the scoped population, group by `duplicate_of`. The cluster shape is usually:

```json
{"primary_id": "canonical id", "duplicate_ids": ["duplicate id"]}
```

Sort duplicate IDs lexicographically. Sort clusters by `primary_id` unless the template says otherwise. Do not count duplicate records in primary totals, percentages, breach rates, or readiness scores.

## Release Readiness

Primary release denominator:

- `release_id` matches the target release.
- Record is not duplicate and not cancelled.
- Record belongs to one of the release milestones when milestone-level output is requested.

Milestone completion:

```text
complete_primary = count(primary release work in completed status)
primary_total = count(primary release work)
completion_pct = round(complete_primary / primary_total * 100, 1)
```

Readiness score:

```text
round(total_complete_primary / total_primary, 3)
```

Unresolved high-impact blockers have `resolved_at == null` and blocker severity `High` or `Critical`. Count exact `cause` strings. Use non-complete primary release items with such blockers as readiness gates.

Dependency chains should use the dependency graph direction `blocked_id -> depends_on_id`. Include a path only when it starts from blocked release work and reaches a non-complete dependency. If all dependencies in a chain are complete, omit it.
