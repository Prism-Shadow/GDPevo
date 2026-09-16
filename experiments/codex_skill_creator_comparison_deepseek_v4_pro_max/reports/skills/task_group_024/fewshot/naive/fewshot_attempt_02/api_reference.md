# API Reference

Base URL is provided in the task prompt or `environment_access.md`. All endpoints are read-only.

## Authentication

Every request needs the header:

```
X-Env-Token: portfolio-readonly
```

## Endpoints

### GET /health
Returns `{"status": "ok"}`. Use to verify connectivity.

### GET /api/work-items
Returns an array of all work item objects. Key fields:

| Field | Description |
|-------|-------------|
| `id` | Work item ID (e.g., `WI-24024-P001`) |
| `title` | Title/summary |
| `status` | Authoritative status: `closed`, `open`, `in_progress`, `cancelled`, `duplicate`, etc. |
| `category` | Portfolio category (may be null/empty for some items) |
| `labels` | Array of label strings |
| `team` | Owning team |
| `product_area` | Product area |
| `quarter` | Planning quarter (e.g., `2025-Q4`) |
| `severity` | Severity level: `S1`, `S2`, `S3`, `S4` (for SLA-relevant items) |
| `owner` | Owner name (may be null/missing) |
| `created_at` | ISO 8601 creation date |
| `closed_at` | ISO 8601 close date (null if not closed) |
| `milestone_id` | Associated milestone |
| `release_id` | Associated release |
| `duplicate_of` | If status is duplicate, points to the primary item ID |
| `mirror_of` | If this is a mirror record, points to the authoritative item ID |

### GET /api/work-items/{item_id}
Returns a single work item object.

### GET /api/mix-targets
Returns an array of mix target rows. Each row has:

| Field | Description |
|-------|-------------|
| `scope_id` | Scope identifier matching the task scope |
| `NewFeature` | Target percentage for NewFeature |
| `TechDebt` | Target percentage for TechDebt |
| `Reliability` | Target percentage for Reliability |
| `Security` | Target percentage for Security |

### GET /api/sla-policy
Returns SLA threshold definitions. Key fields:

| Field | Description |
|-------|-------------|
| `severity` | Severity level this threshold applies to |
| `category` | Category this threshold applies to (may be null if severity-based) |
| `max_days` | Maximum days before breach |

### GET /api/releases
Returns an array of release objects.

| Field | Description |
|-------|-------------|
| `id` | Release ID |
| `name` | Release name |
| `status` | Release status |
| `quarter` | Target quarter |

### GET /api/releases/{release_id}
Returns a single release object.

### GET /api/milestones
Returns an array of milestone objects.

| Field | Description |
|-------|-------------|
| `id` | Milestone ID |
| `release_id` | Parent release ID |
| `name` | Milestone name |
| `target_date` | Target date |

### GET /api/dependencies
Returns dependency relationships between work items.

| Field | Description |
|-------|-------------|
| `source_id` | Work item that depends on another |
| `target_id` | Work item that blocks the source |

### GET /api/blockers
Returns blocker records.

| Field | Description |
|-------|-------------|
| `work_item_id` | Blocked work item |
| `cause` | Blocker cause text |
| `impact` | Impact level: `high`, `medium`, `low` |
| `resolved` | Whether resolved (boolean) |

### POST /api/query
Run a read-only SQL query. Request body:

```json
{"sql": "SELECT ... FROM ... WHERE ..."}
```

Include the `X-Env-Token` header. The exact table schemas depend on the environment; use `SELECT * FROM table LIMIT 1` to explore schema when needed.

## Common cURL Patterns

```bash
# List all work items
curl -s -H "X-Env-Token: portfolio-readonly" "$BASE/api/work-items"

# Get mix targets
curl -s -H "X-Env-Token: portfolio-readonly" "$BASE/api/mix-targets"

# Get SLA policy
curl -s -H "X-Env-Token: portfolio-readonly" "$BASE/api/sla-policy"

# SQL query
curl -s -X POST -H "X-Env-Token: portfolio-readonly" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM work_items"}' \
  "$BASE/api/query"

# Pipe through jq for filtering
curl -s -H "X-Env-Token: portfolio-readonly" "$BASE/api/work-items" | jq '.[] | select(.team == "Platform Core")'
```
