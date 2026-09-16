# Work Item Data Model

## Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Canonical identifier, e.g. `WI-24024-P001` |
| `title` | string | Human-readable title |
| `status` | string | Authoritative lifecycle state: `Open`, `In Progress`, `Closed`, `Cancelled`, `Duplicate` |
| `portfolio_category` | string | One of `NewFeature`, `TechDebt`, `Reliability`, `Security` |
| `severity` | string | `S1`, `S2`, `S3`, `S4`, or null |
| `team` | string | Owning team name |
| `product_area` | string | Product area assignment |
| `owner` | string or null | Assigned owner name |
| `quarter` | string | Planning quarter, e.g. `2025-Q4` |
| `created_at` | ISO-8601 | Creation timestamp |
| `closed_at` | ISO-8601 or null | Closure timestamp |
| `release_id` | string or null | Associated release |
| `milestone_id` | string or null | Associated milestone |

## Duplicate Resolution Fields

| Field | Type | Description |
|-------|------|-------------|
| `duplicate_of` | string or null | ID of the primary work item this record duplicates |
| `canonical_id` | string or null | Alternative name for `duplicate_of` |

A work item is a duplicate if:
- Its `status` is `Duplicate`, OR
- `duplicate_of` or `canonical_id` is non-null and points to another work item ID

The target of these fields is the primary (canonical) record. Only primary records count toward analyses.

## Stale Fields (Ignore)

| Field | Why ignored |
|-------|-------------|
| `mirror_status` | Mirrored/exported copy of status; may lag or disagree with authoritative `status` |
| `legacy_category` | Deprecated classification field; `portfolio_category` is authoritative |
| `mirror_closed_at` | Stale copy of `closed_at` from a mirror system |

Always use `status`, `portfolio_category`, and `closed_at` directly. When a template provides `ignored_mirror_status_and_legacy_category`, set it to `true`.

## Status Transitions

Items that matter for each analysis:

- **Portfolio mix**: `Closed` only (primary, not duplicate, not cancelled)
- **SLA audit**: All non-closed, plus closed older than the recent window. Primary only.
- **Release readiness**: Items linked to release milestones. Primary only.

Cancelled items are always excluded from primary populations. They may be reported separately in `excluded_cancelled_ids`.
