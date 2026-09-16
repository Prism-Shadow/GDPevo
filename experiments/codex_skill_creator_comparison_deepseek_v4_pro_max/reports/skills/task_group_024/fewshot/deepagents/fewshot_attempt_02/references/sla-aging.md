# SLA Aging Audit

## Workflow

1. Fetch the SLA policy via `GET /api/sla-policy`. The policy maps severity
   levels (`S1`-`S4`) to maximum allowed open durations.
2. Fetch all work items via `GET /api/work-items` or the SQL endpoint.
3. Identify the primary SLA population:
   - `category` is one of the scoped categories (e.g. `Reliability`, `Security`);
     use the authoritative `category` field, never `mirror_category`
   - `status` is NOT `closed`, `cancelled`, or `duplicate` (active work)
   - `team` matches one of the scoped teams
4. Separate primary items from duplicates:
   - Any item where `duplicate_of` is non-null is a duplicate. Do not count
     it in the primary population.
   - Group duplicates into clusters by `duplicate_of` (the primary id they
     point to). Report these as `duplicate_clusters`.
5. Determine SLA deadline for each primary item:
   - Map `severity` to the allowed window from the SLA policy.
   - `sla_deadline` may also be present directly on the work item; prefer the
     policy-derived deadline when both are available.
6. Compute aging for each primary item:
   - Age = `as_of_date` minus creation/open date (in days).
   - An item is **overdue** when `age > allowed_window`.
7. Compute aging distribution:
   - Bucket every primary item by age: `0-3`, `4-7`, `8-14`, `15-30`, `31+`.
   - Count items in each bucket.
8. Compute overdue team counts:
   - For each team, count overdue primary items. List teams alphabetically.
9. Identify the top overdue hotspot:
   - Group overdue primary items by `(team, owner)`.
   - Treat missing/null owner as `UNASSIGNED`.
   - The pair with the most overdue items is the hotspot.
   - Break ties by taking the first alphabetically by team, then by owner.
10. Build escalation queue (when the answer schema requires it):
    - Sort overdue primary items by severity (most critical first: S1, S2, S3,
      S4), then by age descending within each severity tier.
11. Compute breach rate:
    - `breach_rate = overdue_primary_count / included_primary_count`
    - Round to **exactly 3 decimal places** (e.g. `0.545`).

## Sorting

- `included_primary_ids`: lexicographic ascending.
- `overdue_primary_ids`: lexicographic ascending.
- `missing_owner_ids`: lexicographic ascending.
- `duplicate_clusters`: sorted by `primary_id` ascending; `duplicate_ids` within
  each cluster sorted lexicographically ascending.
- `team_overdue_counts`: teams listed alphabetically.
- `overdue_counts_by_severity`: always the fixed order `S1`, `S2`, `S3`, `S4`.
- `escalation_queue_ids`: severity descending then age descending.
- `recent_closed_window_days`: use recent closed work for determining which
  items should be considered "recently closed" for SLA exclusion (items closed
  within this window from the as-of date are generally excluded from the
  overdue population).

## Resolution Order for Conflicting Signals

When type, labels, and title suggest conflicting categories, use this priority:
1. The authoritative `category` field
2. The `type` field
3. The `labels` field
4. The `title` field

Ignore `mirror_status`, `mirror_category`, and any other mirror/export fields
for all classification and status decisions.
