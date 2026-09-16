## Environment Endpoints

Base URL is supplied as `<TASK_ENV_BASE_URL>` in the task prompt. Set the
`TASK_ENV_BASE_URL` env var so [scripts/query.py](../scripts/query.py) can
find it, or use the urllib pattern from that script directly.

### Token

`POST /api/query` requires header `X-Env-Token: portfolio-readonly`.
All other endpoints are unauthenticated.

### Endpoints

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/work-items` | All work items |
| GET | `/api/work-items/{item_id}` | Single work item |
| GET | `/api/mix-targets` | All mix target rows |
| GET | `/api/sla-policy` | SLA policy document |
| GET | `/api/releases` | All releases |
| GET | `/api/releases/{release_id}` | Single release |
| GET | `/api/milestones` | All milestones |
| GET | `/api/dependencies` | All dependency records |
| GET | `/api/blockers` | All blocker records |
| POST | `/api/query` | SQL query (body: `{"sql": "...", "params": [...]}`) |

### Work Item Fields (observed)

Work items carry at minimum these fields across the task environment:

- `id` — unique identifier (e.g. `WI-YYYY-SSS-NNN`)
- `status` — lifecycle status: `closed`, `open`, `in_progress`, `cancelled`, etc.
- `closed_at` — ISO-8601 timestamp when closed, or null
- `team` — owning team name
- `owner` — assigned owner display name, may be null/empty
- `title` — short description
- `type` — work item type (`bug`, `task`, `story`, `epic`, etc.)
- `labels` — array of label strings
- `category` — portfolio category (`NewFeature`, `TechDebt`, `Reliability`, `Security`) or legacy value
- `severity` — severity level (`S1`-`S4`) used for SLA classification
- `sla_deadline` — deadline timestamp for SLA calculations
- `duplicate_of` — id of the primary work item this duplicates, or null
- `mirror_status` — mirror/export status field; do not use as source of truth for real status
- `mirror_category` — mirror/export category field; do not use for classification

Always use the authoritative `status`, `category`, `type`, `labels`, and `title`
fields directly. Ignore `mirror_status`, `mirror_category`, and any similar
export-only fields for decisions.

### Mix Target Fields

- `scope_id` — scope key
- `NewFeature` — target percentage (number)
- `TechDebt` — target percentage (number)
- `Reliability` — target percentage (number)
- `Security` — target percentage (number)

### SLA Policy

Contains severity-to-deadline mappings. The policy document defines the
maximum allowed age for work items by severity level.

### Release Fields

- `id` — release identifier (e.g. `REL-YYYY-MM-NN`)
- `milestone_ids` — array of milestone ids belonging to this release

### Milestone Fields

- `id` — milestone identifier (e.g. `MIL-YYY-GA`)
- `release_id` — parent release

### Dependency Fields

- `from_id` — work item that depends on something
- `to_id` — work item it depends on

### Blocker Fields

- `work_item_id` — blocked work item
- `cause` — exact cause text string
- `impact` — severity indicator (`high`, `medium`, `low`)
- `resolved` — boolean

### SQL Query Capability

The `POST /api/query` endpoint accepts read-only `SELECT` and `WITH`
statements. Use positional `$1`, `$2` … parameters. Example:

```json
{"sql": "SELECT id, status FROM work_items WHERE team = $1", "params": ["<a-team-name>"]}
```
