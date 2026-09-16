## Environment API Reference

The task environment provides a REST API at `<TASK_ENV_BASE_URL>`. No credentials
are required. Every endpoint returns JSON. All list endpoints support the
`scope_id` query parameter for scoping results.

### Work Items

**`GET /api/work-items`** — List all work items, optionally scoped with
`?scope_id=<id>`. Returns an array of work-item objects.

**`GET /api/work-items/{item_id}`** — Single work item by its identifier.

### Mix Targets

**`GET /api/mix-targets`** — Returns mix-target rows. Each row maps a `scope_id`
to target percentages for the four portfolio categories (NewFeature, TechDebt,
Reliability, Security). Use the row whose `scope_id` matches the task's scope.

### Releases

**`GET /api/releases`** — List releases.

**`GET /api/releases/{release_id}`** — Single release including its milestone
references, status, and associated work item ids.

### Milestones

**`GET /api/milestones`** — List milestones. Each milestone references its parent
release and contains a list of work item ids.

### Dependencies

**`GET /api/dependencies`** — Returns dependency records linking work items.
Each record has `from_id` (blocks) and `to_id` (blocked).

### Blockers

**`GET /api/blockers`** — Returns blocker records. Each has a work item
reference, cause text, impact level, and resolution status.

### SLA Policy

**`GET /api/sla-policy`** — Returns SLA policy configuration including severity
levels, target resolution durations, and category-to-severity mappings.

### Restricted SQL Query

**`POST /api/query`** — Accepts a JSON body with a `query` field containing a
SQL SELECT statement. The SQL dialect is SQLite-compatible. Use this only when
standard endpoints are insufficient for a cross-entity join or aggregation.

Tables available for querying:

- `work_items` — id, title, status, type, category, severity, team, owner,
  product_area, scope_id, quarter, created_at, closed_at, updated_at,
  mirror_status, legacy_category, duplicate_of, release_id, milestone_id
- `mix_targets` — scope_id, NewFeature, TechDebt, Reliability, Security
- `releases` — id, name, status, quarter
- `milestones` — id, name, release_id, work_item_ids (JSON array as text)
- `blockers` — id, work_item_id, cause, impact, resolved
- `dependencies` — id, from_id, to_id

Always prefer the standard REST endpoints over SQL queries. Use POST /api/query
only for cross-entity operations that would otherwise require N+1 API calls.

### General API Usage Notes

- All IDs are case-sensitive strings.
- Dates are ISO-8601 strings (e.g., `2025-07-15`).
- Null fields are JSON `null`, not the string "null" or omitted.
- When an endpoint returns a list and the task needs a specific subset,
  filter client-side after fetching. Do not assume server-side filtering works
  on every field.
