Release Readiness Reference

This reference provides deeper guidance for release readiness assessments beyond the essentials in SKILL.md. All examples use generic patterns, not specific task results.

Entity relationships

A release has:
- Milestones (via release_id on milestones)
- Work items (via release_id on work items)
- Blockers (via release_id on blockers; each blocker also references a work_item_id)

Work items also reference milestones via milestone_id.

Blockers reference work items via work_item_id.

Dependencies link two work items: blocked_id (the one being blocked) and depends_on_id (the one it depends on), with a relation field.

Milestone completion

For each milestone belonging to the release:

1. Find all work items with milestone_id matching the milestone.
2. Exclude items with status "Duplicate" or status "Cancelled".
3. Count as primary_total.
4. Count items whose status is in {Closed, Done, Deployed, Verified} as complete_primary.
5. completion_pct = round((complete_primary / primary_total) * 100, 1).

Sort milestones by milestone_id ascending.

If primary_total is 0 for a milestone, completion_pct is 0.0 (though in practice every milestone should have work items).

Ship decision framework

The three possible decisions, from best to worst:

SHIP: All milestones at 100% completion. No unresolved blockers with severity High or Critical. All gating work items are in terminal completed states.

SHIP_WITH_WATCH: Most milestones at or near completion. Some lower-severity unresolved blockers exist but have manageable impact. A watch item is identified (usually the lowest-completion milestone). The release can proceed but requires active monitoring.

NO_SHIP: One or more critical milestones incomplete. Unresolved high-impact blockers present. Gating work items not in terminal state. The release cannot proceed safely.

The decision is based on the actual data in the environment, not a hard-coded formula. Key signals for NO_SHIP:
- Any milestone below roughly 70% completion with open work items
- Any unresolved blocker with severity High or Critical
- Work items with status not in terminal states that gate release readiness

Gating work items

A work item gates a release when:
- Its release_id matches the release under review.
- Its status is NOT in a completed terminal state ({Closed, Done, Deployed, Verified}).
- It is not a Duplicate or Cancelled.

Collect all such items, sort lexicographically, deduplicate.

No gating work items means all release-scoped primary work is in a terminal state.

Blocker analysis

Filter blockers to those relevant for the release readiness assessment:
- release_id matches the release under review.
- status is not "Resolved" (unresolved blockers).
- Usually, all severities are counted; the severity field helps determine ship impact but all unresolved blockers tied to the release are reported.

Count by exact cause string. The cause string is taken verbatim from the blocker record. Each distinct cause becomes a key in the blocker_cause_counts object, with the count of unresolved blockers having that exact cause.

Resolved blockers (status "Resolved") are excluded entirely.

Dependency chains

A critical dependency chain exists when a release-scoped work item (the blocked item) depends on another work item that is not in a completed terminal state.

To build chains:

1. Start from work items on the release whose status is not in a completed terminal state.
2. For each such item, check dependencies where blocked_id matches the item.
3. If the depends_on_id work item is not in a completed terminal state, build the chain.
4. A chain can extend: if the dependency itself depends on another non-complete item, extend the chain.
5. Format each chain as an ordered list: [blocked_work_item, first_dep, second_dep, ...].

Sort chains lexicographically by the full path representation (compare each element lexicographically in sequence).

Only include chains where the final dependency is non-complete. If the dependency is itself complete (in a terminal state), the chain is resolved and should not appear.

Empty chains

When all release work items are complete, or when all dependencies are satisfied (the depends_on items are in terminal states), critical_dependency_chains is an empty array [].

Readiness score

readiness_score = completed_primary / total_primary_on_release, rounded to 3 decimal places.

- completed_primary: number of work items on the release in terminal states (Closed, Done, Deployed, Verified), excluding Duplicate and Cancelled.
- total_primary_on_release: all work items on the release, excluding Duplicate and Cancelled.

If total_primary_on_release is 0, the readiness score is 0.0 (though a release should always have work items).

Work item status authority on releases

The same data-quality rules from SKILL.md apply. The mirror_status field is stale. Use status for all release-readiness decisions. A work item whose mirror_status says "Closed" but status says "In Progress" is in progress, not closed.

Blockers vs. work items

Blockers are separate records linked to work items. A blocker on a work item does not necessarily mean the work item itself is blocked from release; it means a process blocker exists. For release readiness, count blockers and assess their impact. The combination of blocker severity and work item status determines ship impact.

A resolved blocker (status "Resolved") should not influence the ship decision. Only unresolved blockers matter.
