# API Reference

## Base URL

Obtain the base URL from the environment access file (e.g. `environment_access.md`).
The task prompt will contain a `<TASK_ENV_BASE_URL>` placeholder.

## Authentication

The `/api/query` endpoint may require an authentication token. Check the
environment access file for credentials; most endpoints are open.

## Endpoints

### GET /api/work-items

Returns all work items. Commonly used as the starting point for any analysis.

**Key request parameters** (query string or the query endpoint):
- `quarter` — e.g. `2025-Q4`
- `team` — team name string
- `product_area` — product area string
- `status` — status filter (use authoritative status values)

**Key response fields per work item:**

| Field | Description |
|---|---|
| `id` | Work item identifier, format `WI-24024-...` |
| `title` | Short description |
| `type` | Item type (bug, feature, vulnerability, etc.) |
| `status` | **Authoritative** status. Trust this over `mirror_status`. |
| `portfolio_category` | **Authoritative** category: NewFeature, TechDebt, Reliability, Security. Trust this over `legacy_category`. |
| `team` | Owning team |
| `owner` | Assigned person (may be null/missing) |
| `quarter` | Planning quarter |
| `product_area` | Product area |
| `release_id` | Release this item belongs to (if any) |
| `milestone_id` | Milestone this item belongs to (if any) |
| `closed_at` | Timestamp when the item was closed |
| `created_at` | Timestamp when the item was created |
| `duplicate_of` | If non-null, this record is a duplicate pointing at a primary record |
| `severity` | S1, S2, S3, or S4 (used in SLA and readiness contexts) |
| `sla_deadline` or `sla_target_date` | The SLA target date (field name varies; inspect responses) |
| `mirror_status` | **Do not trust** — stale mirror field |
| `export_status` | **Do not trust** — stale export field |
| `legacy_category` | **Do not trust** — may disagree with `portfolio_category` |
| `mirror_category` | **Do not trust** — stale mirror field |
| `labels` or `tags` | Array of strings; fallback classification signals |

### GET /api/work-items/{item_id}

Returns a single work item by id. Use to inspect details of specific items
when the list endpoint omits fields.

### GET /api/mix-targets

Returns the target mix table. Each row specifies target percentages for the
four portfolio categories for a given scope.

**Key response fields per row:**

| Field | Description |
|---|---|
| `scope_id` | Matches the task's scope identifier |
| `quarter` | Planning quarter |
| `target_NewFeature` or `NewFeature` | Target percentage for NewFeature |
| `target_TechDebt` or `TechDebt` | Target percentage for TechDebt |
| `target_Reliability` or `Reliability` | Target percentage for Reliability |
| `target_Security` or `Security` | Target percentage for Security |

The exact field names vary; inspect the first response to determine whether
targets are prefixed with `target_` or appear as bare category names.

### GET /api/sla-policy

Returns SLA policy configuration. Provides target durations per category
and/or severity that determine when an item becomes overdue.

**Key response fields:**

| Field | Description |
|---|---|
| `category` | Portfolio category the policy applies to |
| `severity` | Severity band (S1–S4) |
| `target_days` or `sla_days` | Maximum allowed days before breach |

### GET /api/releases

Returns all releases. Use to discover releases or list them by quarter.

### GET /api/releases/{release_id}

Returns a single release with its milestone list, status, and metadata.

**Key response fields:**

| Field | Description |
|---|---|
| `id` | Release identifier (e.g. `REL-PLATFORM-2025-Q4`) |
| `name` | Human-readable release name |
| `status` | Release status |
| `milestones` | Array of milestone ids or objects in this release |
| `quarter` | Planning quarter |

### GET /api/milestones

Returns all milestones, or filter by release.

**Key response fields:**

| Field | Description |
|---|---|
| `id` | Milestone identifier (e.g. `MIL-PLATFORM-BETA`) |
| `release_id` | Parent release |
| `name` | Milestone name |
| `work_item_ids` or `items` | Work items associated with this milestone |

### GET /api/dependencies

Returns dependency relationships between work items.

**Key response fields:**

| Field | Description |
|---|---|
| `blocked_id` or `depends_on_id` | The item that is blocked / waiting |
| `blocking_id` or `required_by_id` | The item that must complete first |
| `status` | Dependency status (e.g. open, resolved) |

### GET /api/blockers

Returns blocker records. Blockers are issues preventing work item completion.

**Key response fields:**

| Field | Description |
|---|---|
| `work_item_id` | The blocked work item |
| `cause` | The blocker cause text — use this exact string for counts |
| `impact` | Impact level (e.g. high, medium, low) |
| `status` | Resolved or unresolved |
| `team` | Team responsible for resolution |

### POST /api/query

Restricted SQL-like query endpoint. May require a token from the access file.
Use when the list endpoints do not support the needed filtering directly.

Exact query syntax varies; inspect error responses to determine the supported
dialect. Typical patterns: `SELECT * FROM work_items WHERE ...` or a simpler
filter-object syntax.

## Data model notes

### Work item identity

The canonical identifier format is `WI-24024-{prefix}{number}`. The prefix
may be a letter (e.g. `P` for Platform, `S` for Security) or absent. Items
are unique by id.

### Status lifecycle

Work items progress through statuses such as: `open`, `in_progress`, `in_review`,
`closed`, `cancelled`. The exact status values depend on the environment
configuration. **Always use the authoritative status field**, not mirror-status.

- **Closed / complete** statuses indicate the work is done and count toward
  completion metrics.
- **Cancelled** items are excluded from all inclusive populations.
- **Open / in-progress** items are non-complete and may gate releases.

### Duplicate pattern

A duplicate record has `duplicate_of` set to another work item id. The
referenced id is the primary. When processing scoped results:

1. If `duplicate_of` points at an item **inside the current scope**, exclude
   the duplicate from primary counts and add it to the duplicate cluster for
   that primary.
2. If `duplicate_of` points at an item **outside the current scope**, treat
   the local record as primary for counting but note the cross-reference.
3. If `duplicate_of` is null, empty, or points at the record's own id, the
   record is primary.

### Portfolio category resolution

The authoritative `portfolio_category` field should be used whenever present.
When absent, resolve from type → labels → title. The four valid values are
`NewFeature`, `TechDebt`, `Reliability`, `Security` (exact casing).

Common type-to-category mappings observed in train data:
- `feature`, `enhancement`, `story` → NewFeature
- `refactor`, `tech-debt`, `chore` → TechDebt
- `bug`, `incident`, `reliability` → Reliability
- `vulnerability`, `security`, `compliance` → Security

These are not exhaustive; use the full signal chain when the category field
is absent.
