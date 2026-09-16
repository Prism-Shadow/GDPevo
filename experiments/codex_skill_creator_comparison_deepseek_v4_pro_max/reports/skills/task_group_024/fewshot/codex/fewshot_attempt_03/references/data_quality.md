# Data Quality Rules

## Primary vs Non-Primary Records

Every work item falls into one of these categories for portfolio computation:

### Primary

A work item is **primary** when:

- `status` is **not** `Duplicate` or `Cancelled`
- `duplicate_of` is **null**

Primary items are the ones counted in portfolio metrics (mix, SLA, release readiness).

### Duplicate

A work item is a **duplicate** when:

- `duplicate_of` is **non-null** — regardless of what `status` says.
- `status` is `Duplicate` — even if `duplicate_of` is null.

Duplicate items point at another work item (the primary). Exclude them from primary counts but report them in exclusion lists or duplicate clusters.

Build duplicate clusters by grouping duplicates by their `duplicate_of` value. For each cluster, `primary_id` is the `duplicate_of` target, and `duplicate_ids` are the IDs of all items pointing to that primary.

### Cancelled

A work item is **cancelled** when `status` is `Cancelled`. Exclude from primary counts. Report in exclusion lists when the task requires it.

### Distractor

A distractor is an in-scope record (matching teams, quarter, product areas) that should not be counted as a primary closed portfolio item because:

- It is a duplicate
- It is cancelled
- It has `duplicate_of` non-null even with status `Closed` or `Verified`

## Mirror Status and Legacy Category

### Mirror Status

The `mirror_status` field is a stale mirror/export field that may disagree with the authoritative `status`. **Always use `status` as the source of truth.**

When a task asks for `ignored_mirror_status_and_legacy_category`, set it to `true` to confirm that `mirror_status` was not used for classification or inclusion decisions.

### Legacy Category

The `legacy_category` field (bug, new, maintenance, security, quality, tech-debt) is a stale pre-migration field. **Never use it for portfolio category classification.** Use the classification rules in [category_rules.md](category_rules.md) instead.

## Quarter Assignment

Work item quarter is derived from `closed_at`:

- 2025-Q3: `closed_at` from 2025-07-01 to 2025-09-30
- 2025-Q4: `closed_at` from 2025-10-01 to 2025-12-31
- 2026-Q1: `closed_at` from 2026-01-01 to 2026-03-31

A work item's `closed_at` must fall within the task's quarter to be included in a portfolio mix review.

## SLA Age Calculation

Age in days = `as_of_date - created_at` (date difference, not including time).

An item is **overdue** when `age > sla_policy[severity].days_to_due`.

Items closed within the recent_closed_window_days are excluded from SLA aging analysis.

## Work Item Status Values

Authoritative `status` values:

- `Open` — Not yet started
- `InProgress` — Work is active
- `Closed` — Work is complete and closed
- `Verified` — Work is verified (equivalent to complete)
- `Done` — Work is done (equivalent to complete)
- `Deployed` — Work is deployed (equivalent to complete)
- `Duplicate` — This is a duplicate of another item
- `Cancelled` — Work was cancelled

For release readiness and completion checks:
- **Complete** statuses: `Closed`, `Verified`, `Done`, `Deployed`
- **Non-complete** statuses: `Open`, `InProgress`, `Duplicate`, `Cancelled`
