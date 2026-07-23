# Data Quality & Exclusion Rules

## Duplicate Records

A work item is a **duplicate** if ANY of these are true:
1. `status == "Duplicate"`
2. `duplicate_of` is not null (points at another work item)

Duplicates are excluded from primary counts and reported separately.

Some items have `status` = "Closed" but still have `duplicate_of` set. These are also duplicates — always check the `duplicate_of` field regardless of status.

## Cancelled Records

Items with `status == "Cancelled"` are excluded from primary counts.

## Distractor Records

Distractors are in-scope items that appear to be valid closed work but should not be counted as primary portfolio work:
- Items with `duplicate_of` set but status ≠ "Duplicate" (e.g., status = "Closed" but pointing at another item)
- Items whose mirror_status disagrees with actual status (stale mirror data)

Report distractor IDs in the dedicated `excluded_distractor_ids` field where the schema provides one.

## Stale Mirror Fields

`mirror_status` and `legacy_category` can contradict the authoritative `status` and `work_type` fields. Always use the authoritative fields:
- Use `status`, not `mirror_status`
- Use `work_type` (with label resolution), not `legacy_category`

## Completed/Closed Statuses

These statuses indicate a work item is "complete":
- Verified
- Done
- Closed
- Deployed

Everything else (In Progress, Review, Backlog, Reopened, Duplicate, Cancelled) is "not complete".

## Common Pitfalls

1. **Including future-dated items**: An item with `created_at` after the as-of date should not be in the SLA population.
2. **Double-counting duplicates**: If an item has `duplicate_of` set, it's a duplicate regardless of its `status`.
3. **Using due_at instead of SLA deadline**: The SLA deadline is `created_at + sla_days[severity]`, which may differ from the `due_at` field.
4. **Mixing mirror and authority data**: Always prefer authoritative fields over mirror/export fields.
5. **Forgetting recently-closed overdue items**: Items closed within the recent-closed window that breached their SLA deadline should be counted as overdue.
