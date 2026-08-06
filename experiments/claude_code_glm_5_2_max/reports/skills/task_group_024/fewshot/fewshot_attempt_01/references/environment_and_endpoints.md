# Environment access & endpoint catalog

## Reading `environment_access.md`
`environment_access.md` contains, in order:
- `GDPEVO_ENV_BASE_URL=...` — the base URL (e.g. `http://task-env:9024/`). Prefix every endpoint
  with it. The prompt writes this as `<TASK_ENV_BASE_URL>`; substitute the value from this file.
- `X-Env-Token: ...` — the token. Send as the `X-Env-Token` request header on **every** request.
- `Allowed endpoints:` — the allowlist of `METHOD /path` entries. Do not call any endpoint not
  listed.

> The endpoint list and field shapes below are the environment's own schema (stable across tasks),
> not task-specific answer data. Always confirm against the live response — vocabularies may grow.

## Allowed endpoints
| Method | Path | Returns |
|---|---|---|
| GET | `/api/work-items` | all work items → `{count, work_items:[...]}` |
| GET | `/api/work-items/{item_id}` | one work item → `{work_item:{...}}` |
| GET | `/api/mix-targets` | all mix-target rows → `{mix_targets:[...]}` |
| GET | `/api/sla-policy` | SLA policy rows → `{sla_policy:[...]}` |
| GET | `/api/releases` | all releases → `{releases:[...]}` |
| GET | `/api/releases/{release_id}` | one release **+ its milestones + its blockers** → `{release, milestones, blockers}` |
| GET | `/api/milestones` | all milestones → `{milestones:[...]}` |
| GET | `/api/dependencies` | all dependency edges → `{dependencies:[...]}` |
| GET | `/api/blockers` | all blockers → `{blockers:[...]}` |
| POST | `/api/query` | read-only SQL result (see below) |

## Read-only SQL endpoint — `POST /api/query`
- **Body:** `{"sql": "SELECT ..."}`. The field name is `sql` (a string) — *not* `query`.
- **Only `SELECT`** is allowed; anything else returns `{"error":"only SELECT statements are allowed"}`.
- **Response:** `{"columns":[...], "row_count":N, "rows":[[...],...], "truncated":bool}`. `rows` are
  positional arrays aligned to `columns`. If `truncated` is true, narrow the query.
- **Queryable tables (7):** `work_items`, `mix_targets`, `sla_policy`, `releases`, `milestones`,
  `dependencies`, `blockers` (discover with
  `SELECT name FROM sqlite_master WHERE type='table'`).
- `labels` is stored as a **JSON-text array** (e.g. `["security","cve"]`); parse it in code. To
  filter on labels in SQL, use `LIKE` against the text, then parse to confirm.
- Great for scoped/aggregated pulls, e.g.
  `SELECT id,status,team,product_area,closed_at,severity,due_at FROM work_items WHERE team IN ('...','...')`.

## Record field names

### `work_items` — authoritative fields
`id, title, work_type, status, team, owner, product_area, created_at, due_at, closed_at, severity,
priority, labels, story_points, release_id, milestone_id, duplicate_of, mirror_status,
legacy_category`

| field | meaning / handling |
|---|---|
| `id` | work-item identifier (e.g. `WI-24024-...`). |
| `status` | **authoritative** lifecycle status. Vocabulary observed: `Backlog, Cancelled, Closed, Deployed, Done, Duplicate, In Progress, Reopened, Review, Verified`. |
| `mirror_status` | **stale mirror/export status — IGNORE.** |
| `legacy_category` | **stale legacy category — IGNORE** for portfolio classification. |
| `duplicate_of` | **authoritative duplicate signal.** Non-null ⇒ this record is a duplicate of the named primary id (even if `status` is `Closed`). |
| `work_type` | type signal (e.g. `Feature, Bug, Refactor, Security, Reliability, Incident, Enhancement, Dependency, Chore, Compliance`). |
| `labels` | JSON-text array of label strings (e.g. `security, cve, auth, encryption, reliability, latency, outage, incident, flaky, cleanup, refactor, migration, feature, rollout`). |
| `severity` | `S1` / `S2` / `S3` / `S4`. |
| `priority` | integer (lower = more urgent). |
| `owner` | name, or `null` (missing owner). |
| `closed_at`, `due_at`, `created_at` | `YYYY-MM-DD`; `closed_at` may be `null`. |
| `release_id`, `milestone_id` | link to release / milestone, or `null`. |
| `team`, `product_area`, `story_points` | scope/classification attributes. |

### `mix_targets`
`scope_id, quarter, team_group, product_area, new_feature_pct, tech_debt_pct, reliability_pct,
security_pct`
- The four `*_pct` fields are **fractions in 0–1** (e.g. `0.34` = 34%). Convert to percentage points
  by ×100. Select the row whose `scope_id` equals the task's target scope id.

### `sla_policy`
`severity, days_to_due` — per-severity SLA horizon in days. Read live; current policy is
`S1=3, S2=10, S3=21, S4=45` days. Used to decide whether a primary item is overdue as of the as-of
date (compare `due_at` — adjusted by `days_to_due` where the task calls for it — against the as-of
date).

### `releases`
`id, name, target_date, train`

### `milestones`
`id, name, owner_team, release_id`

### `dependencies`
`blocked_id, depends_on_id, relation` — an edge "`blocked_id` depends-on `depends_on_id`". Build
chains by following `depends_on_id` forward from blocked release work to a non-complete dependency.

### `blockers`
`id, work_item_id, release_id, severity, cause, status, opened_at, resolved_at`
- `severity` vocabulary includes `Critical, High, Low` (read live). **High-impact = `Critical` or
  `High`.**
- `status` vocabulary includes `Open, Monitoring` (read live). **Unresolved = `resolved_at` is
  `null`.**
- `cause` is the exact free-text string — use it verbatim as the key in blocker-cause counts.

## Practical request pattern
```bash
B="<base url from environment_access.md>"   # e.g. http://task-env:9024
T="<token from environment_access.md>"      # X-Env-Token value
curl -s -H "X-Env-Token: $T" "$B/api/work-items"
curl -s -H "X-Env-Token: $T" -H "Content-Type: application/json" \
  -X POST "$B/api/query" -d '{"sql":"SELECT id,status,team FROM work_items WHERE status=\"Cancelled\""}'
```
