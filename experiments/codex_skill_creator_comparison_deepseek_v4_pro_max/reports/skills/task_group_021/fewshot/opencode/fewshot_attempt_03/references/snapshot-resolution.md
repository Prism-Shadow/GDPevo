# Snapshot Resolution

Every Asteria Fleet DQ Hub task involves overlapping records from multiple
source snapshots. Establishing the authoritative view is the first analysis
step, before any counts, quarantines, or totals.

## Finding the authoritative snapshot

1. Call `GET /api/source-snapshots` to list all snapshots with their `status`,
   `collection_id`, and `row_count`.

2. Filter to snapshots whose `collection_id` matches the task's collection.

3. The snapshot with `status: "CERTIFIED"` is authoritative. If multiple
   certified snapshots exist for the same collection (rare), prefer the one
   with `source_system` matching the task's domain.

4. The authoritative snapshot ID is reported in the audit summary (fields like
   `authoritative_snapshot_id`).

## Deduplication algorithm

```
For each logical record ID (stable transaction/event/charge/row ID):
  - Collect all raw rows with that ID across all snapshots in the collection
  - If exactly one row exists: it is retained as-is
  - If multiple rows exist:
      - Retain the row from the certified snapshot
      - All other rows are "duplicate raw rows"
      - Count: duplicate_raw_count = total raw rows - unique logical IDs
```

The retained row's snapshot is recorded in `retained_snapshot_id` for duplicate
groups.

## Common snapshot naming

Collections typically have exactly two snapshots:

- `{collection_id}-certified` (authoritative)
- `{collection_id}-provisional` (overlapping, lower priority)

Some collections may also have deprecated snapshots — ignore them entirely
unless the task explicitly includes them.

## What depends on snapshot resolution

- **All counts**: `raw_row_count`, `logical_X_count`, `valid_X_count`
- **Quarantine eligibility**: quarantine is assessed on retained rows only
- **Normalized totals**: use retained rows, then exclude quarantined ones
- **Decision panels**: scoped IDs are looked up in the retained working set
- **Focus clusters and anchored cases**: seed/anchor rows may appear in both
  snapshots; always use the retained (certified) row's field values

## Retained snapshot for duplicates

When a record appears in both certified and provisional snapshots with the
same logical ID, the certified snapshot is `retained_snapshot_id`. This
applies to `duplicate_groups` entries in maintenance and freight tasks.
