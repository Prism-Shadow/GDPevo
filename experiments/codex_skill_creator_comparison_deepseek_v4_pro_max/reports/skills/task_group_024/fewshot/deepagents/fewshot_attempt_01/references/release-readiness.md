# Release Readiness Assessment

## Data Sources

1. `/api/releases` — list all releases. Find the target release by ID.
2. `/api/releases/{release_id}` — release details.
3. `/api/milestones` — milestones filtered by `release_id`.
4. `/api/work-items` — work items filtered by `release_id` and `milestone_id`.
5. `/api/blockers` — blockers filtered by `release_id`.
6. `/api/dependencies` — dependency edges. Build chains from blocked release
   work items to non-complete dependency leaves.

## Primary Work Set

For each milestone, collect all work items with that `milestone_id`. Then:

1. Exclude `status == "Duplicate"` and `status == "Cancelled"` items.
2. If `duplicate_of` is non-null and status is not Duplicate, still treat as
   duplicate — exclude from primary.
3. The remaining items are the primary set for that milestone.

## Completion Status

An item is **complete** when its `status` is one of:

- `Done`
- `Closed`
- `Deployed`
- `Verified`

All other statuses (`Backlog`, `In Progress`, `Review`, `Reopened`) are
**not complete**.

**Mirror trap**: Never use `mirror_status` to determine completion. The
`mirror_status` field is a stale export artefact. Use `status` exclusively.

## Milestone Completion

```
complete_primary = count of primary items with complete status
primary_total    = count of all primary items in the milestone
completion_pct   = round((complete_primary / primary_total) * 100, 1)
```

Sort milestones by `milestone_id` ascending in output.

## Gating Work Items

A gating work item is a non-complete primary release item that blocks readiness.
An item qualifies as gating when at least one of:

1. It has an **open high-impact blocker** (see below).
2. It has an unresolved **critical dependency** — a `depends_on_id` that is
   itself not complete. Trace the dependency chain; a non-complete leaf means
   the item is gated.

Collect gating work item IDs, sort ascending, remove duplicates.

## Blocker Analysis

A **high-impact blocker** is one where:

- `severity` is `Critical` or `High`
- `status` is NOT `Resolved`

Count blockers by exact `cause` text. The cause strings are verbatim from the
blocker data. Use them as keys without normalisation.

Blockers with `severity` of `Low` or `Medium` are not high-impact and do not
factor into the ship decision, even if they are unresolved. However, all
blockers on release work items should be inspected for completeness.

## Dependency Chains

A **critical dependency chain** starts at a release work item (`blocked_id`)
that is blocked by a `depends_on_id` (the dependency). Follow the chain:

1. For each release work item, find all dependencies where it is `blocked_id`.
2. For each `depends_on_id`, check if that work item is complete.
3. If the dependency is not complete, record a chain `[blocked_id, depends_on_id]`.
4. If the dependency has its own dependencies, extend the chain: follow until
   a complete item or a leaf with no further dependencies.
5. Only include chains where the leaf dependency is **not complete**.

Sort chains lexicographically by the full path.

## Ship Decision

The ship decision is one of `SHIP`, `SHIP_WITH_WATCH`, or `NO_SHIP`.

### NO_SHIP

Return `NO_SHIP` when:

- Any unresolved high-impact (Critical/High) blocker exists on a release work
  item, OR
- Any milestone has completion below a reasonable threshold (e.g. 100% for
  critical milestones), OR
- Critical dependency chains exist that block release readiness.

### SHIP_WITH_WATCH

Return `SHIP_WITH_WATCH` when:

- No high-impact blockers exist AND
- All milestones meet minimum completion thresholds AND
- Only minor, non-critical issues remain (e.g. one milestone at 60-80%).

### SHIP

Return `SHIP` when all milestones are at 100% completion and no open blockers
exist on any release work item.

The exact threshold depends on the release context and blocker severity. When in
doubt, prefer `NO_SHIP` over `SHIP_WITH_WATCH` and `SHIP_WITH_WATCH` over
`SHIP`.

## Readiness Score

```
readiness_score = total_completed_primary / total_primary
```

Where `total_completed_primary` is the sum of `complete_primary` across all
milestones and `total_primary` is the sum of `primary_total` across all
milestones. Round to exactly 3 decimal places.

## Ordering

- `milestone_completion`: sort by `milestone_id` ascending.
- `gating_work_item_ids`: sort ascending, no duplicates.
- `blocker_cause_counts`: use exact cause strings as keys.
- `critical_dependency_chains`: sort lexicographically by the full path.
