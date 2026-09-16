# Portfolio API Reference

## REST Endpoints

All endpoints are relative to `<TASK_ENV_BASE_URL>` from `environment_access.md`.

### GET /api/work-items

Returns `{"count": N, "work_items": [...]}`. Each work item has these fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Work item ID (e.g. WI-24024-P001, WI-24024-075) |
| `title` | string | Free-text title |
| `status` | string | Authoritative status: Open, InProgress, Closed, Verified, Done, Cancelled, Duplicate |
| `work_type` | string | Incident, Task, Enhancement, Refactor, Bug |
| `team` | string | Owning team |
| `product_area` | string | Product area |
| `owner` | string or null | Owner name, null when unassigned |
| `severity` | string | S1, S2, S3, S4 |
| `priority` | integer | 1-5 |
| `labels` | array of strings | e.g. ["auth", "security", "feature"] |
| `created_at` | string | ISO date YYYY-MM-DD |
| `closed_at` | string or null | ISO date YYYY-MM-DD |
| `due_at` | string or null | ISO date YYYY-MM-DD |
| `duplicate_of` | string or null | If non-null, this item is a duplicate of the given primary ID |
| `milestone_id` | string or null | Milestone assignment |
| `release_id` | string or null | Release assignment |
| `story_points` | integer | Story point estimate |
| `legacy_category` | string | **DO NOT USE** — stale field (bug, new, maintenance, security, etc.) |
| `mirror_status` | string | **DO NOT USE** — may disagree with real `status` |

### GET /api/work-items/{item_id}

Single work item by ID. Same shape as an element of the work-items array.

### GET /api/mix-targets

Returns `{"mix_targets": [...]}`. Each target row:

| Field | Type | Description |
|---|---|---|
| `scope_id` | string | Unique target identifier |
| `quarter` | string | e.g. 2025-Q4 |
| `team_group` | string | Team grouping |
| `product_area` | string | Product area |
| `new_feature_pct` | number | Target percentage for NewFeature (0-100 scale, e.g. 34.0) |
| `tech_debt_pct` | number | Target percentage for TechDebt |
| `reliability_pct` | number | Target percentage for Reliability |
| `security_pct` | number | Target percentage for Security |

Match on `scope_id` to find the target mix for a given task.

### GET /api/sla-policy

Returns `{"sla_policy": [...]}`. Each row:

| Field | Type | Description |
|---|---|---|
| `severity` | string | S1, S2, S3, S4 |
| `days_to_due` | integer | Maximum days from creation to closure |

### GET /api/releases

Returns `{"releases": [...]}`. Each row:

| Field | Type | Description |
|---|---|---|
| `id` | string | Release ID (e.g. REL-ORION-2026-02) |
| `name` | string | Human-readable name |
| `target_date` | string | ISO date YYYY-MM-DD |
| `train` | string | Train name |

### GET /api/releases/{release_id}

Single release by ID.

### GET /api/milestones

Returns `{"milestones": [...]}`. Each row:

| Field | Type | Description |
|---|---|---|
| `id` | string | Milestone ID (e.g. MIL-ORION-GA) |
| `name` | string | Human-readable name |
| `release_id` | string | Parent release |
| `owner_team` | string | Responsible team |

### GET /api/dependencies

Returns `{"dependencies": [...]}`. Each row:

| Field | Type | Description |
|---|---|---|
| `blocked_id` | string | The work item that is blocked |
| `depends_on_id` | string | The work item it depends on |
| `relation` | string | Relationship type: depends-on, blocks-release-readiness, security-review-required, validation-required, implementation-dependency, audit-evidence-required |

### GET /api/blockers

Returns `{"blockers": [...]}`. Each row:

| Field | Type | Description |
|---|---|---|
| `id` | string | Blocker ID (e.g. BLK-24024-006) |
| `work_item_id` | string | The blocked work item |
| `release_id` | string | Associated release |
| `cause` | string | Exact cause text |
| `severity` | string | Low, Medium, High, Critical |
| `status` | string | Open, Monitoring, Resolved |
| `opened_at` | string | ISO date YYYY-MM-DD |
| `resolved_at` | string or null | ISO date YYYY-MM-DD |

## POST /api/query (SQL)

Read-only SQL queries against the portfolio database.

**Auth**: Header `X-Env-Token: portfolio-readonly`

**Request body**:
```json
{"sql": "SELECT ... FROM work_items WHERE ...", "params": []}
```

**Response**:
```json
{"columns": ["col1", "col2"], "rows": [["val1", "val2"]], "row_count": N, "truncated": false}
```

**Constraints**:
- Only SELECT and WITH (CTE) statements allowed
- No INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA
- Tables: `work_items`, `mix_targets`, `sla_policy`, `releases`, `milestones`, `dependencies`, `blockers`

## SQL Table Schemas

### work_items

| Column | Type |
|---|---|
| `id` | TEXT PK |
| `title` | TEXT |
| `status` | TEXT |
| `work_type` | TEXT |
| `team` | TEXT |
| `product_area` | TEXT |
| `owner` | TEXT |
| `severity` | TEXT |
| `priority` | INTEGER |
| `labels` | TEXT (JSON array stored as text) |
| `created_at` | TEXT (YYYY-MM-DD) |
| `closed_at` | TEXT (YYYY-MM-DD) |
| `due_at` | TEXT (YYYY-MM-DD) |
| `duplicate_of` | TEXT |
| `milestone_id` | TEXT |
| `release_id` | TEXT |
| `story_points` | INTEGER |
| `legacy_category` | TEXT |
| `mirror_status` | TEXT |

### mix_targets

| Column | Type |
|---|---|
| `scope_id` | TEXT |
| `quarter` | TEXT |
| `team_group` | TEXT |
| `product_area` | TEXT |
| `new_feature_pct` | REAL |
| `tech_debt_pct` | REAL |
| `reliability_pct` | REAL |
| `security_pct` | REAL |

### sla_policy

| Column | Type |
|---|---|
| `severity` | TEXT (S1/S2/S3/S4) |
| `days_to_due` | INTEGER |

### releases

| Column | Type |
|---|---|
| `id` | TEXT PK |
| `name` | TEXT |
| `target_date` | TEXT |
| `train` | TEXT |

### milestones

| Column | Type |
|---|---|
| `id` | TEXT PK |
| `name` | TEXT |
| `release_id` | TEXT |
| `owner_team` | TEXT |

### dependencies

| Column | Type |
|---|---|
| `blocked_id` | TEXT |
| `depends_on_id` | TEXT |
| `relation` | TEXT |

### blockers

| Column | Type |
|---|---|
| `id` | TEXT PK |
| `work_item_id` | TEXT |
| `release_id` | TEXT |
| `cause` | TEXT |
| `severity` | TEXT |
| `status` | TEXT |
| `opened_at` | TEXT |
| `resolved_at` | TEXT |

## SQL Filtering Patterns

### Work items by quarter

Work item quarter is not stored as a field. Infer it from `closed_at`:
- 2025-Q4: `closed_at >= '2025-10-01' AND closed_at < '2026-01-01'`

### Labels matching

Labels are stored as a JSON text array. Use `LIKE` for pattern matching:
```sql
SELECT * FROM work_items WHERE labels LIKE '%"security"%'
```

### Avoiding duplicate/cancelled

```sql
WHERE status NOT IN ('Duplicate', 'Cancelled')
  AND duplicate_of IS NULL
```
