# Scope Filtering and Exclusions

## Scope membership

A work item is in scope for a portfolio-mix or SLA task when **all** of the
scope dimensions match (conjunction, not union):

- **Team**: the item's `team` is one of the scope's teams.
- **Product area**: the item's `product_area` is one of the scope's product
  areas. (Scopes can span multiple teams and multiple product areas — parse the
  `team_group` and `product_area` strings from the `mix_targets` row, which may
  be `" + "`-joined lists.)
- **Time window**:
  - Portfolio mix (quarterly): `closed_at` falls inside the quarter
    (e.g. `2025-Q4` → Oct 1–Dec 31 of 2025).
  - SLA (as-of snapshot): `created_at <= as_of` (the item must have existed by
    the as-of date) **and** the item is either still open or closed within the
    recent-closed window (see `sla-aging.md`).

## What counts as "closed" / "complete"

Use the authoritative `status`:

- Closed/complete: `Closed`, `Done`, `Verified`, `Deployed`.
- Open: `Backlog`, `In Progress`, `Review`, `Reopened`.

Do **not** use `mirror_status` or `closed_at` alone to decide completeness —
a `Duplicate` record can have a `closed_at` but is not complete/primary.

## Exclusions (encountered in scope)

From the in-scope records, exclude:

- **Duplicates**: `status == "Duplicate"` **or** `duplicate_of` is not null.
  (A `Duplicate` status with null `duplicate_of` is still a duplicate —
  exclude it.)
- **Cancelled**: `status == "Cancelled"`.

The remaining records are the **included / primary** set.

## Duplicate handling by task type

- **Portfolio mix**: excluded duplicates and cancelled records are *reported*
  in the answer's exclusion field(s), but not counted in the mix.
- **SLA**: duplicates that would otherwise inflate the SLA population are
  reported as **duplicate clusters** (see `sla-aging.md`); the duplicate
  itself is never counted as primary. Its `duplicate_of` target (the primary)
  is counted once, if it is in scope and SLA-relevant.
- **Release readiness**: duplicates are excluded from primary counts; there is
  no separate duplicate-cluster field.

## Ordering of included/excluded ID lists

- Portfolio mix `included_work_item_ids` and any `excluded_*_ids`: order by
  `closed_at` ascending, then `id` ascending (unless the template says
  otherwise).
- SLA `included_primary_ids`, `overdue_primary_ids`, `missing_owner_ids`: sort
  lexicographically by id.
- Anywhere a template says "sorted lexicographically / ascending", sort the
  id strings directly (digits before letters).
