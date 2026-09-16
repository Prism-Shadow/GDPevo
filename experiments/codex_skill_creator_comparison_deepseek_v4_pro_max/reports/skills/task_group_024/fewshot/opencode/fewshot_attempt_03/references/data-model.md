# API Data Model Reference

This reference catalogs the fields returned by each endpoint in the shared engineering work-item API. Use it when you need to understand what fields are available, what they mean, and how to use them correctly.

## `/api/work-items` and `/api/work-items/{item_id}`

Returns an array of work-item objects (list endpoint) or a single work-item object (detail endpoint).

### Work Item Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier, format `WI-24024-...` |
| `team` | string | Owning engineering team |
| `product_area` | string | Product area the work belongs to |
| `portfolio_category` | string | Canonical category: `NewFeature`, `TechDebt`, `Reliability`, or `Security` |
| `legacy_category` | string | **STALE** — old classification; ignore in favor of `portfolio_category` |
| `status` | string | Lifecycle status: `open`, `in_progress`, `closed`, `cancelled`, etc. |
| `mirror_status` | string | **STALE** — denormalized copy of status; ignore in favor of `status` |
| `type` | string | `primary` or `duplicate` |
| `duplicate_of` | string\|null | When type is `duplicate`, the id of the primary record this points at |
| `owner` | string\|null | Assigned owner display name, or null when unassigned |
| `severity` | string | `S1`, `S2`, `S3`, or `S4` |
| `sla_deadline` | string\|null | ISO date string for SLA deadline, or null if none set |
| `created_at` | string | ISO datetime string for creation |
| `updated_at` | string | ISO datetime string for last update |
| `closed_at` | string\|null | ISO datetime string for closure, or null if not closed |
| `title` | string | Free-text title |
| `description` | string | Free-text description |
| `labels` | string[] | Array of label strings |
| `release_id` | string\|null | Release this item belongs to, if any |
| `milestone_id` | string\|null | Milestone this item belongs to, if any |
| `quarter` | string | Quarter label, e.g. `2025-Q1` |
| `scope_id` | string | Scope grouping identifier |

### Query Parameters (GET /api/work-items)

The list endpoint supports filtering via query parameters:

- `team` — filter by team name
- `product_area` — filter by product area
- `portfolio_category` — filter by category
- `status` — filter by status
- `type` — filter by `primary` or `duplicate`
- `quarter` — filter by quarter
- `scope_id` — filter by scope

Combine parameters to narrow results. Example: `GET /api/work-items?team=Team+Alpha&quarter=2025-Q1&status=closed`

## `/api/mix-targets`

Returns an array of mix target objects. Each defines the desired category distribution for a scope.

### Mix Target Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Row identifier |
| `scope_id` | string | Which scope this target applies to |
| `quarter` | string | Quarter label |
| `NewFeature` | number | Target percentage for NewFeature (percentage points) |
| `TechDebt` | number | Target percentage for TechDebt (percentage points) |
| `Reliability` | number | Target percentage for Reliability (percentage points) |
| `Security` | number | Target percentage for Security (percentage points) |

The four category percentages typically sum to 100.

## `/api/sla-policy`

Returns the SLA deadline policy configuration. The exact shape depends on the environment, but typically includes:

- Severity-to-deadline mappings (e.g., S1 → 3 days, S2 → 7 days)
- Category-specific overrides
- Any global SLA window definition

## `/api/releases` and `/api/releases/{release_id}`

Returns an array of release objects or a single release.

### Release Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Release identifier, format `REL-...` |
| `name` | string | Human-readable release name |
| `status` | string | Release status |
| `milestone_ids` | string[] | Milestones belonging to this release |
| `target_date` | string\|null | Planned ship date |

## `/api/milestones`

Returns an array of milestone objects.

### Milestone Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Milestone identifier, format `MIL-...` |
| `name` | string | Human-readable milestone name |
| `release_id` | string | Parent release id |
| `order` | integer | Sequence order within the release |

## `/api/dependencies`

Returns an array of dependency objects — directed edges between work items.

### Dependency Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Row identifier |
| `from_id` | string | The dependent work item (blocked by the dependency) |
| `to_id` | string | The prerequisite work item (must complete first) |
| `type` | string | Dependency type descriptor |

A dependency means `from_id` cannot complete until `to_id` completes. When tracing chains, follow `from_id` → `to_id` outward.

## `/api/blockers`

Returns an array of blocker objects.

### Blocker Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Row identifier |
| `work_item_id` | string | The blocked work item |
| `cause` | string | Exact cause text describing the block |
| `impact` | string | Impact level: `high`, `medium`, `low` |
| `resolved` | boolean | Whether the blocker has been resolved |
| `created_at` | string | ISO datetime when blocker was reported |

Only unresolved high-impact blockers typically gate release readiness.

## `/api/query` (POST)

Accepts a JSON body with a `sql` field containing a restricted SQL query. The dialect supports basic SELECT, WHERE with IN, AND, OR, != operators, and ORDER BY. JOINs may or may not be supported depending on the environment.

```json
{"sql": "SELECT * FROM work_items WHERE team = 'Team X' AND status != 'cancelled' ORDER BY closed_at ASC"}
```

Use this endpoint when you need to combine filters that the GET endpoint parameters don't support directly, such as filtering by multiple categories simultaneously while excluding a status.
