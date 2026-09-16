# SLA Aging Methodology Reference

This reference deepens the SLA aging procedures from the main SKILL.md with annotated examples, edge-case guidance, and computation walkthroughs. All examples are illustrative patterns, not specific to any particular task.

## SLA policy

The SLA policy endpoint returns a fixed mapping from severity to days-to-due:

| Severity | Days to due |
|---|---|
| S1 | 3 |
| S2 | 10 |
| S3 | 21 |
| S4 | 45 |

The `days_to_due` is the expected maximum time from creation to completion. The actual due date on each work item (`due_at`) is set according to this policy. Use `due_at` for overdue calculations; the policy values help validate expectations but the field value is authoritative.

## Overdue determination

A work item is overdue when its `due_at` is before the as-of date AND the work is not complete (or was completed after the due date). The precise logic:

```
is_overdue = (due_at < as_of_date) AND (
    status NOT IN completed_terminal_states
    OR (status IN completed_terminal_states AND closed_at > due_at)
)
```

Where `completed_terminal_states` = `{Closed, Done, Deployed, Verified}`.

**Late-closed items**: A work item that was closed after its due date counts as overdue even though it is now in a terminal state. The breach occurred when it missed the deadline; the later completion does not erase the breach.

**Items not yet due**: An open item whose `due_at >= as_of_date` is not overdue. It may become overdue if not completed by its due date.

### Pattern: overdue identification walkthrough

Given an as-of date and a set of primary work items, classify each:

| Case | Status | due_at vs as_of | Closed? | Overdue? | Why |
|---|---|---|---|---|---|
| Open past-due | In Progress | due < as_of | No | Yes | Past deadline, not complete |
| Closed on time | Closed | due < as_of | closed_at <= due_at | No | Completed before or on deadline |
| Closed late | Closed | due < as_of | closed_at > due_at | Yes | Completed after deadline (breach) |
| Not yet due | Backlog | due >= as_of | No | No | Deadline still in future |
| Closed before as_of | Verified | due < as_of | closed_at < as_of | No | Completed before review date |

Always compute `due_at < as_of_date` first. If true, check whether completion happened on time.

## Aging bucket computation

`aging_days = as_of_date - created_at`. Compute in calendar days.

Buckets:
- 0-3: aging <= 3
- 4-7: 4 <= aging <= 7
- 8-14: 8 <= aging <= 14
- 15-30: 15 <= aging <= 30
- 31+: aging >= 31

Count every primary included item into exactly one bucket.

## Escalation queue ordering

When the task requires an escalation queue, build it from overdue primary items sorted by:

1. Severity: S1 first, then S2, S3, S4.
2. Within each severity tier, by `due_at` ascending (oldest/most overdue first).

This means the most critical, most overdue items appear first. S1 items always precede S2 items regardless of due date.

### Pattern: escalation ordering

Given overdue items with mixed severities:

| ID | Severity | due_at |
|---|---|---|
| Item-A | S1 | 2026-01-12 |
| Item-B | S2 | 2026-01-10 |
| Item-C | S1 | 2026-01-18 |

Correct order: Item-A (S1, Jan 12), Item-C (S1, Jan 18), Item-B (S2, Jan 10).

Item-A and Item-C are S1 so they come first, ordered by due_at. Item-B is S2 so it follows all S1 items.

## Breach rate precision

`breach_rate = overdue_count / included_primary_count`, rounded to exactly 3 decimal places using standard rounding (half-up).

Example: if 2 out of 7 items are overdue, compute `2 / 7 = 0.28571...` and round to `0.286`.

Another example: if 3 out of 7 items are overdue, compute `3 / 7 = 0.42857...` and round to `0.429`.

Always compute from the final counts after all exclusions, not from intermediate values.

## Duplicate cluster construction

Scope the duplicate search to work items belonging to the same teams as the primary population. A duplicate record has:
- `status == "Duplicate"`
- `duplicate_of` is non-null

Each cluster groups duplicates by their `duplicate_of` value:

```json
{
  "primary_id": "<duplicate_of target>",
  "duplicate_ids": ["<duplicate item id>", "..."]
}
```

Sort clusters by `primary_id` lexicographically. Sort `duplicate_ids` lexicographically within each cluster.

Only include duplicate records that belong to the scope teams. If a duplicate belongs to a different team, it is out of scope.

## Missing owner identification

For every primary included work item, check `owner`. If `owner` is `null`, the item goes in `missing_owner_ids`. Sort ascending lexicographically.

Missing owners are identified in the primary population only, not in duplicates or excluded items.

## Team overdue hotspot

To find the top hotspot (team/owner pair with the most overdue items):

1. Group overdue primary items by (team, owner).
2. When owner is `null`, treat it as the string `"UNASSIGNED"`.
3. Find the pair with the highest count.
4. If multiple pairs tie, use the first alphabetically by team, then by owner.

## Team overdue counts

Count overdue primary items per team. List teams alphabetically. Each team appears exactly once in the output array, even if its overdue count is zero.
