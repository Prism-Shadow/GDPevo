# Environment Reference

## Access

Read `environment_access.md` from the working directory. It contains:

- `GDPEVO_ENV_BASE_URL` — the base URL of the running environment.
- `X-Env-Token:` — the header value for the read access token.
- An allowed-endpoint list.

Reach the environment **only** through this file. Do not hardcode the base URL
or token in outputs — read them at runtime. All requests are read-only GETs plus
one restricted POST; do not attempt writes.

## Endpoints

REST (GET):

- `/api/work-items` — list all work items.
- `/api/work-items/{item_id}` — single work item (wrapped as `{"work_item": {...}}`).
- `/api/mix-targets` — target mix rows (one per scope).
- `/api/sla-policy` — SLA policy rows.
- `/api/releases` — releases.
- `/api/releases/{release_id}` — single release.
- `/api/milestones` — milestones.
- `/api/dependencies` — dependency edges.
- `/api/blockers` — blocker records.
- `POST /api/query` — restricted SQL passthrough.

### SQL passthrough

`POST /api/query` with body `{"sql": "<SELECT statement>"}` returns:

```json
{"columns": [...], "row_count": N, "rows": [[...], ...], "truncated": false}
```

- Each row is a positional array aligned to `columns`.
- Check `truncated`; if true, narrow the query (filter/limit) and re-run.
- Some SQL functions (e.g. `pragma_table_info`) are blocked — if a query returns
  `{"error": "not authorized"}`, rewrite it without that function.
- Backing tables: `work_items`, `mix_targets`, `sla_policy`, `releases`,
    `milestones`, `dependencies`, `blockers`.
- SQL string values use double quotes inside the statement (the JSON is
  single-quoted at the shell layer).

## Data model

### work_items (the core table)

| field | type | notes |
|---|---|---|
| `id` | string | work item id, e.g. `WI-...` |
| `status` | string | **authoritative** status (see vocabulary below) |
| `mirror_status` | string | **STALE — ignore** |
| `work_type` | string | classification signal (see classification.md) |
| `labels` | array | classification signal |
| `title` | string | classification signal (substring match) |
| `legacy_category` | string | **STALE — ignore** |
| `duplicate_of` | string\|null | **authoritative** duplicate linkage; non-null ⇒ duplicate |
| `closed_at` | date\|null | set when the item is closed |
| `created_at` | date | creation date |
| `due_at` | date\|null | SLA due date (governs overdue) |
| `owner` | string\|null | null ⇒ missing owner / `UNASSIGNED` |
| `team` | string | owning team |
| `product_area` | string | product area |
| `severity` | string | `S1`–`S4` |
| `priority` | integer | escalation ordering |
| `milestone_id` | string\|null | milestone link (release readiness) |
| `release_id` | string\|null | release link |
| `story_points` | integer | **not used** for mix (mix is count-based) |

**Status vocabulary:** `In Progress`, `Closed`, `Done`, `Verified`,
`Duplicate`, `Deployed`, `Review`, `Backlog`, `Cancelled`, `Reopened`.

- Terminal / complete: `Closed`, `Done`, `Verified`, `Deployed`.
- Non-terminal: `In Progress`, `Review`, `Backlog`, `Reopened`.
- `Duplicate` ⇒ duplicate record (also check `duplicate_of`).
- `Cancelled` ⇒ cancelled record (excluded from primary counts).

### mix_targets

One row per scope. Fields are **fractions** (0.34 = 34%):
`new_feature_pct`, `tech_debt_pct`, `reliability_pct`, `security_pct`,
plus `scope_id`, `quarter`, `product_area`, `team_group`. Select the target row
whose `scope_id` matches the task's scope.

### sla_policy

`severity` → `days_to_due` (`S1`=3, `S2`=10, `S3`=21, `S4`=45). This is
reference context for severity-based SLA targets. **Overdue is determined from
each item's authoritative `due_at` field, not from a policy-derived date.**

### releases / milestones

`releases`: `id`, `name`, `target_date`, `train`.
`milestones`: `id`, `name`, `owner_team`, `release_id`. A release has multiple
milestones; milestone ordering is by `id` ascending.

### blockers

`id`, `release_id`, `work_item_id`, `cause` (exact text), `severity`
(`Low`/`Medium`/`High`/`Critical`), `status` (`Open`/`Monitoring`/`Resolved`),
`opened_at`, `resolved_at`. **Unresolved** = `status` in `{Open, Monitoring}`
(`resolved_at` null). **High-impact** = `severity` in `{High, Critical}`.

### dependencies

Directed edges: `blocked_id` → `depends_on_id`, with a `relation`
(`depends-on`, `blocks-release-readiness`, `validation-required`,
`security-review-required`, `implementation-dependency`,
`audit-evidence-required`). Used to build dependency chains for release
readiness.
