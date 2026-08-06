# Release Readiness Reference

## Ship Decision Logic

```
IF any high-impact unresolved blockers exist:
    NO_SHIP
ELSE IF readiness_score < 1.0:
    SHIP_WITH_WATCH
ELSE:
    SHIP
```

High-impact = severity is "High" or "Critical" AND status is not "Resolved".

## Milestone Completion

For each milestone associated with the release:
- Count primary work items (non-duplicate, non-cancelled, no `duplicate_of`)
- Count completed items (status in: Verified, Done, Closed, Deployed)
- `completion_pct` = completed / total × 100, rounded to 1 decimal place
- Sort milestones by `milestone_id` ascending

## Gating Work Items

Non-complete primary release work items. These are the items blocking full readiness.

## Blocker Cause Counts

Only count **high-impact unresolved** blockers:
- Severity ∈ {High, Critical}
- Status ≠ Resolved

Group by exact `cause` string, count occurrences.

## Critical Dependency Chains

An ordered list of work item IDs forming a path from a release work item to a non-complete dependency:
1. Start from any release work item that appears as `blocked_id` in the dependencies data
2. Follow `depends_on_id` edges
3. If the dependency is "non-complete" (status not in complete set), the chain ends
4. If the dependency is complete, continue following transitively
5. A chain is: `[release_work_item_id, intermediate_id?, non_complete_dependency_id]`
6. Sort chains lexicographically by the full path

Note: Include chains starting from ALL release work items (not just non-complete/gating ones), since even a completed release item may depend on non-complete work that affects readiness.

## Readiness Score

`completed_primary / total_primary`, rounded to 3 decimal places.

Where "primary" = release work items that are not duplicates or cancelled.
