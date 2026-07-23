# SLA Aging / Breach Audit Task

Audit reliability & security work against SLA due dates as of a snapshot date.

## Inputs

- Teams (scope), as-of date, recent-closed window (days), and SLA categories
  (Reliability + Security).
- SLA policy: `days_to_due` per severity (S1, S2, S3, S4). **Note**: overdue is
  determined by the work item's `due_at` (and `closed_at` for resolved items),
  not by recomputing a deadline from `days_to_due`. The SLA policy is context;
  the `due_at` field is the authoritative SLA clock.

## Step 1 — SLA population (`included_primary_ids`)

From in-scope teams, keep items with `created_at <= as_of`, then:

1. Drop `Cancelled`.
2. Drop duplicates (`status == "Duplicate"` or `duplicate_of` not null) — they
   go to duplicate clusters, not the population.
3. Keep only **Reliability** and **Security** items (classify via
   `classification.md`).
4. Keep only items that are **active as of the snapshot**:
   - **Open** (`Backlog`, `In Progress`, `Review`, `Reopened`), OR
   - **Recently closed**: `closed_at` within the recent-closed window
     (`as_of − window_days ≤ closed_at ≤ as_of`), where closed status is
     `Closed`/`Done`/`Verified`/`Deployed`.

Sort `included_primary_ids` lexicographically.

## Step 2 — Overdue (`overdue_primary_ids`)

A primary item is **overdue** when it missed its `due_at`:

- **Open** item: `as_of > due_at` (strictly past due).
- **Closed** item: `closed_at > due_at` (resolved after it was due).

Sort lexicographically. (Title phrases like "overdue", "not overdue",
"boundary due", "closed before due", "closed late" are hints that confirm this
`due_at`-based logic.)

## Step 3 — Aging distribution (if the template asks)

`aging_bucket_counts` over the population, buckets
`0-3`, `4-7`, `8-14`, `15-30`, `31+` (age in days):

- **Open** items: age = `as_of − created_at`.
- **Closed** items: age = `closed_at − created_at` (frozen at resolution — do
  **not** count days after closure).

This closed-item distinction matters: a recently-closed item's age is its
resolution time, not its age at the snapshot.

## Step 4 — Overdue by severity and escalation (if asked)

- `overdue_counts_by_severity`: count of overdue items per `S1, S2, S3, S4`.
- `escalation_queue_ids`: the overdue primary ids in **priority order** =
  severity ascending (`S1` first), then `due_at` ascending (most-overdue first),
  then `priority` ascending, then `id`. (Escalate the most severe and most
  overdue first.)

## Step 5 — Team / owner hotspots (if asked)

- `team_overdue_counts`: overdue count per team, teams listed alphabetically.
- `top_hotspot`: the `(team, owner)` pair with the most overdue primary items;
  `overdue_count` is that max. Use `owner = "UNASSIGNED"` when the owner is
  missing/null.

## Step 6 — Missing owners

`missing_owner_ids`: included primary items with null/missing `owner`, sorted
lexicographically.

## Step 7 — Duplicate clusters

Report duplicates that **would otherwise inflate the SLA population** — i.e.
duplicates that are themselves population-eligible (open, or closed within the
recent-closed window) and SLA-relevant (Reliability/Security), and that point
at a primary (`duplicate_of` not null):

- Group by `duplicate_of` (the primary id).
- Each cluster: `{ "primary_id": <primary>, "duplicate_ids": [<dups>] }`.
- `duplicate_ids` sorted lexicographically; clusters sorted by `primary_id`.

Duplicates closed **outside** the recent-closed window, or with no
`duplicate_of`, are simply not counted and not reported (they wouldn't be in
the population anyway). The primary of a cluster is counted once in the
population (if in scope and SLA-relevant).

## Step 8 — Breach rate

`sla_breach_rate` (or `breach_rate`) = `overdue_primary_count /
included_primary_count`, rounded to **3 decimals**.

## Precision checklist

- `breach_rate` / `sla_breach_rate`: exactly 3 decimals.
- ID lists: lexicographic.
- `scope` block: use the teams/categories in the order the template shows
  (some templates list teams in a fixed, non-alphabetical order).
- `recent_closed_window_days`: integer from the task.
