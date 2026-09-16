# SLA Aging Methodology

## SLA Policy

Fetch `/api/sla-policy`. The policy maps severity to `days_to_due`:

| Severity | Days to Due |
|----------|-------------|
| S1       | 3           |
| S2       | 10          |
| S3       | 21          |
| S4       | 45          |

## Scope Filtering

1. Filter work items by `team` (the teams listed in the task scope).
2. Filter by SLA-relevant categories: Security and Reliability. Classify every
   item using the classification rules and keep only Security + Reliability
   items.
3. Separate primary from duplicate/cancelled per standard exclusion rules.

## Primary vs Duplicate

- `status == "Duplicate"` or `duplicate_of` is non-null → exclude from primary
  set. Record as a duplicate cluster member referencing `duplicate_of`.
- `status == "Cancelled"` → exclude entirely.
- All other statuses → primary (subject to category/team/date filters).

An item is included in `included_primary_ids` when:
- It is in the correct team(s)
- It is in an SLA-relevant category (Security or Reliability)
- Its status is NOT Duplicate or Cancelled
- AND one of:
  - Its `created_at` is on or before `as_of` and `closed_at` is null, OR
  - Its `closed_at` falls within the recent closed window (`as_of - window_days` ≤ `closed_at` ≤ `as_of`)

## Overdue Calculation

An item is **overdue** when:

```
created_at + days_to_due < as_of
  AND
(closed_at is null OR closed_at > as_of)
```

Where `days_to_due` comes from the SLA policy for the item's severity.

Items closed within the recent close window are NOT overdue even if they were
past due at close. They count as recently closed and are included in the primary
set but not in the overdue set.

## Aging Buckets

For every open (non-closed) primary item, compute age:

```
age = (as_of - created_at).days
```

Bucket assignments:

| Age (days) | Bucket |
|------------|--------|
| 0-3        | 0-3    |
| 4-7        | 4-7    |
| 8-14       | 8-14   |
| 15-30      | 15-30  |
| 31+        | 31+    |

Count the number of items in each bucket. The sum of bucket counts may exceed
the overdue count because not all open items are overdue.

## Breach Rate

```
breach_rate = len(overdue_primary_ids) / len(included_primary_ids)
```

Round to exactly 3 decimal places (e.g. 0.545).

When `included_primary_ids` is empty, breach rate is 0.000.

## Hotspot (Owner/Team Overdue Analysis)

Count overdue items by team and by owner. The **top hotspot** is the
(team, owner) pair with the most overdue items. When the owner field is null,
use `"UNASSIGNED"`.

If multiple owner/team pairs tie for the maximum, choose the first in
alphabetical team order, then alphabetical owner order.

## Escalation Queue

For SLA audits that require an escalation queue, sort overdue primary items
by:

1. Severity priority: S1 first, then S2, S3, S4
2. Within the same severity, descending by age (oldest first)
3. Within the same severity and age, ascending by ID

## Missing Owner

Scan `included_primary_ids` for items where `owner` is null or empty. Report
these IDs sorted ascending.
