# Release Readiness Task

Assess whether a release is ready to ship from authoritative release, milestone,
work-item, blocker, and dependency data. **Do not use stale mirror fields as
release truth** — use `status` (not `mirror_status`).

## Inputs

- A `release_id`.
- Milestones whose `release_id` matches.
- Work items whose `release_id` matches.
- Blockers whose `release_id` matches.
- Dependencies (all; filter by the release's work items).

## "Primary" and "complete"

- **Primary** work item: not a duplicate (`status != "Duplicate"` **and**
  `duplicate_of` is null). A `Duplicate` status with null `duplicate_of` is
  still a duplicate — exclude it from primary counts.
- **Complete**: `status ∈ {Closed, Done, Verified, Deployed}`.
- **Non-complete / gating**: any primary release work item not complete.

## Step 1 — Milestone completion

For each milestone of the release (sorted by `milestone_id` ascending):

- `primary_total` = count of primary release work items whose `milestone_id`
  equals this milestone.
- `complete_primary` = count of those that are complete.
- `completion_pct` = `complete_primary / primary_total * 100`, 1 decimal.

## Step 2 — Gating work items

`gating_work_item_ids`: the non-complete primary release work item ids, sorted
ascending, no duplicates. (These are the items that must still close for the
release.)

## Step 3 — Blocker cause counts

`blocker_cause_counts`: a map of exact blocker `cause` string → integer count,
over the release's blockers that are **unresolved** (`resolved_at` is null and
`status != "Resolved"`) **and high-impact** (`severity` is `High` or
`Critical`). Low/Medium severity blockers are excluded. Keys are the exact
cause strings.

## Step 4 — Critical dependency chains

`critical_dependency_chains`: ordered work-item-id paths from a blocked release
work item to a dependency it relies on that is **still incomplete**.

- Consider dependencies where `blocked_id` is a primary release work item and
  `depends_on_id` is a work item that is **not yet complete**.
- Treat a dependency as incomplete when its `status` is **active-incomplete**
  (`Backlog`, `In Progress`, `Review`, `Reopened`). Terminal non-complete
  states — `Duplicate` and `Cancelled` — are *not* "work still to finish"
  (a duplicate resolves to its primary; a cancelled item will never complete),
  so prefer to **exclude** them from chains. A dependency already
  `Closed`/`Done`/`Verified`/`Deployed` is complete and does not form a chain.
- Each chain is the 2-element path `[blocked_id, depends_on_id]`. Follow
  transitively only if the dependency itself has further outgoing dependencies
  (usually these are direct, single-hop).
- Sort the chains lexicographically by the full path.

This step is sensitive to two judgment calls — which dependency relations count
as "critical" and whether terminal non-complete states count — so re-derive
from the data and prefer the active-incomplete reading above.

## Step 5 — Readiness score

`readiness_score` = `complete_primary_work / primary_denominator`, rounded to
3 decimals, where the denominator is **all primary release work items**.

## Step 6 — Ship decision

`ship_decision` ∈ {`SHIP`, `SHIP_WITH_WATCH`, `NO_SHIP`}. Decide from the
readiness evidence:

- `NO_SHIP` when there is an unresolved **Critical** blocker, or readiness is
  below the ship threshold (a release well below complete, with gating work
  and/or critical dependency chains, does not ship).
- `SHIP_WITH_WATCH` when the release is substantially complete but carries
  unresolved **High** blockers or minor gating risk.
- `SHIP` when there are no unresolved High/Critical blockers and readiness is
  high.

A single unresolved Critical-severity blocker (e.g. an open CVE exception) is
sufficient grounds for `NO_SHIP`.

## Precision checklist

- `milestone_completion`: sorted by `milestone_id` ascending.
- `gating_work_item_ids`: sorted ascending, unique.
- `completion_pct`: 1 decimal.
- `readiness_score`: 3 decimals.
- `critical_dependency_chains`: sorted lexicographically by full path.
- `blocker_cause_counts`: keys are exact cause strings.
