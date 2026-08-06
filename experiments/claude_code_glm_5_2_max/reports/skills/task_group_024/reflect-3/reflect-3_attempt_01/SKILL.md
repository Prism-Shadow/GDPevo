---
name: portfolio-work-review
description: Compute portfolio-mix, SLA-aging, and release-readiness reviews from a shared work-item environment. Use when a task asks for a closed-work portfolio mix vs target, an SLA breach/aging audit, or a release ship-readiness assessment, and points at a shared environment with work items, mix targets, SLA policy, releases, milestones, dependencies, and blockers.
---

# Portfolio Work Review

This skill produces a single JSON answer for three kinds of engineering-portfolio
review tasks against a shared work-item environment:

1. **Portfolio mix** — closed work in a scope, classified into portfolio
   categories, compared to a target mix, with a rebalance recommendation.
2. **SLA aging / breach audit** — reliability & security work tracked against
   SLA due dates, with overdue items, aging, duplicate clusters, and breach rate.
3. **Release readiness** — a release's milestone completion, gating work,
   blockers, dependency chains, and a ship decision.

The environment, the available endpoints, and any access token are supplied
separately at solve time (e.g. an `environment_access.md` file). Read that file
to learn how to reach the environment. **Do not call any judge/evaluation
endpoint while solving** — produce the best answer directly from the
environment data.

## Shared method (all task types)

1. **Pull the raw data** from the environment: work items, mix targets, SLA
   policy, releases, milestones, dependencies, blockers. A restricted SQL
   endpoint (SELECT only) may also be available and is useful for cross-checks.
2. **Use authoritative fields, not stale mirrors.** Each work item has an
   authoritative `status` plus a stale `mirror_status`, and an authoritative
   `work_type`/`labels`/`title` plus a stale `legacy_category`. Always use the
   authoritative fields; ignore `mirror_status` and `legacy_category`.
3. **Classify** each work item into one of four portfolio categories
   (NewFeature, TechDebt, Reliability, Security) using the convention in
   [`classification.md`](./classification.md). This convention is shared across
   all task types.
4. **Filter to scope** and **exclude** duplicates and cancelled records
   consistently (see [`scope-and-exclusions.md`](./scope-and-exclusions.md)).
5. **Compute** the task-specific metrics following the per-type reference below.
6. **Order and round** exactly as each task's template specifies — ordering and
   precision are scored.

## Per-type references

- Portfolio mix → [`portfolio-mix.md`](./portfolio-mix.md)
- SLA aging / breach audit → [`sla-aging.md`](./sla-aging.md)
- Release readiness → [`release-readiness.md`](./release-readiness.md)

## Status vocabulary (authoritative `status`)

- **Closed/done set** (counts as complete/closed): `Closed`, `Done`, `Verified`, `Deployed`.
- **Open set** (still in flight): `Backlog`, `In Progress`, `Review`, `Reopened`.
- **Duplicate**: `status == "Duplicate"` (regardless of whether `duplicate_of` is set).
- **Cancelled**: `status == "Cancelled"`.

A record is a **duplicate** when `status == "Duplicate"` **or** `duplicate_of`
is not null. A record is **primary** when it is neither a duplicate nor
cancelled. (A `Duplicate` status with a null `duplicate_of` is still a
duplicate — exclude it; it is not primary.)

## Ordering and precision (universal)

- Work-item ID lists: sort **lexicographically as strings** unless the task
  says otherwise (digits sort before letters, so an id ending in `099`
  precedes one ending in `S001`).
- "closed_at ascending, then id ascending" is the default ordering for
  portfolio work.
- Percentages: percentage points rounded to **1 decimal**.
- Rates (breach, readiness): rounded to **3 decimals**.
- Dates are ISO `YYYY-MM-DD`. Date comparisons are calendar-day comparisons.

## Worked discipline

- Re-derive every value from the environment data; do not hand-wave.
- After computing, re-check that every required field from the task's
  `answer_template.json` is present with the right type and key names, and that
  no extra fields are added (`additionalProperties: false` is common).
- If the task gives a `scope_id`, look up the matching row in `mix_targets` to
  recover the intended team_group and product_area for the scope.
