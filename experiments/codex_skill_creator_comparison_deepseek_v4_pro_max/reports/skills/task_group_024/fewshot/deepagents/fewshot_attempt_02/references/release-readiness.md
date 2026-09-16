# Release Readiness Assessment

## Workflow

1. Fetch the target release via `GET /api/releases/{release_id}`.
2. Fetch all milestones via `GET /api/milestones`, filtered to the
   `milestone_ids` listed on the release.
3. Fetch all work items via `GET /api/work-items` or the SQL endpoint.
4. Fetch blockers via `GET /api/blockers`.
5. Fetch dependencies via `GET /api/dependencies`.
6. Determine the ship decision:
   - `SHIP`: all release work items complete and no unresolved high-impact
     blockers.
   - `SHIP_WITH_WATCH`: all release work items complete but unresolved
     high-impact blockers exist, or nearly all items complete with minimal
     gating work and no critical blockers.
   - `NO_SHIP`: incomplete release work items directly gate readiness, or
     unresolved high-impact blockers with incomplete milestones.
7. Compute milestone completion:
   - For each milestone, count primary work items (exclude duplicates and
     cancelled items) associated with that milestone.
   - Primary items are those where `status` is not `cancelled` and
     `duplicate_of` is null.
   - `complete_primary` = count of primary items with `status` == `closed`.
   - `primary_total` = total primary items for the milestone.
   - `completion_pct = (complete_primary / primary_total) * 100`, rounded to
     **1 decimal place**.
   - Sort milestone completion rows by `milestone_id` ascending.
8. Identify gating work items:
   - Non-complete primary work items in the release that gate readiness.
   - Exclude duplicates, cancelled items, and items completed by a
     duplicate/dependency resolution.
   - Sorted ascending with no duplicates.
9. Blocker cause counts:
   - Only count **unresolved** (`resolved` == false) blockers with
     **high impact**.
   - Key by exact `cause` string as it appears in the blocker record.
10. Critical dependency chains:
    - Start from blocked release work items (items with unresolved high-impact
      blockers).
    - Follow `from_id` -> `to_id` through the dependency graph.
    - A chain is critical when the dependency (`to_id`) is a non-complete work
      item.
    - Each chain is an ordered path `[blocked_item, dep_1, dep_2, ...,
      non_complete_end]`.
    - Sort chains lexicographically by the full path.
11. Compute readiness score:
    - `readiness_score = completed_primary_items / total_primary_items`, where
      total excludes duplicates and cancelled.
    - Round to **exactly 3 decimal places**.

## Sorting and Ordering

- `milestone_completion`: sort by `milestone_id` ascending.
- `gating_work_item_ids`: sorted ascending (lexicographic), no duplicates.
- `blocker_cause_counts` keys: use exact cause strings as they appear in data.
- `critical_dependency_chains`: sorted lexicographically by the full path array.

## Important Rules

- Never use `mirror_status` or `mirror_category` for any decision. Use only
  authoritative work item fields (`status`, `category`, `type`, `labels`,
  `title`).
- Use release and milestone data to determine which items belong to each
  milestone; do not rely on guesswork from item titles.
- When a blocker and dependency both point to the same item, treat blocker data
  as the primary signal for blocking and dependency data as the supporting
  signal for chain traversal.
