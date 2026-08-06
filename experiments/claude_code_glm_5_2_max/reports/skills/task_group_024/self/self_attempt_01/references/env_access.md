# Environment access

Source of truth: `environment_access.md` in the work root. **Re-read it each run; do not
hardcode the base URL or token.**

## Auth
- Base URL: the value on the `GDPEVO_ENV_BASE_URL=…` line. Prompts write this as
  `<TASK_ENV_BASE_URL>`.
- Header: `X-Env-Token: <value from environment_access.md>` on every request.

## GET endpoints
- `/api/work-items` → `{"work_items": […]}`. One record per work item.
- `/api/work-items/{id}` → single work item.
- `/api/mix-targets` → `{"mix_targets": […]}`. Target **fractions (0–1)** per `scope_id`:
  `new_feature_pct`, `tech_debt_pct`, `reliability_pct`, `security_pct`, plus `quarter`,
  `product_area`, `team_group`, `scope_id`. Convert to percentage points (×100) before
  comparing/reporting.
- `/api/sla-policy` → `{"sla_policy": [{severity, days_to_due}]}`.
- `/api/releases` → `{"releases": […]}`. Fields: `id`, `name`, `target_date`, `train`.
- `/api/releases/{id}` → single release.
- `/api/milestones` → `{"milestones": […]}`. Fields: `id`, `name`, `owner_team`, `release_id`.
- `/api/dependencies` → `{"dependencies": […]}`. Fields: `blocked_id`, `depends_on_id`, `relation`.
- `/api/blockers` → `{"blockers": […]}`. Fields: `cause`, `id`, `opened_at`, `release_id`,
  `resolved_at`, `severity`, `status`, `work_item_id`.

## Restricted SQL endpoint
- `POST /api/query` with JSON body `{"sql": "<SELECT statement>"}`.
- Returns `{"columns", "row_count", "rows", "truncated"}`. `rows` is a list of arrays in
  `columns` order.
- **Only `SELECT` is allowed** — `PRAGMA`, `INSERT`, DDL, etc. are rejected.
- Tables: `work_items`, `mix_targets`, `sla_policy`, `releases`, `milestones`,
  `dependencies`, `blockers`.
- Use it to filter/aggregate server-side (by team, quarter, product_area, status, scope_id,
  release_id, …). Always check `truncated`; if true, add a `LIMIT`/narrower filter and
  re-query until you have the full set.

## work_items record fields
`id`, `title`, `work_type`, `status`, `team`, `owner`, `product_area`, `created_at`,
`due_at`, `closed_at`, `severity`, `priority`, `labels` (array), `story_points`,
`release_id`, `milestone_id`, `duplicate_of`, `mirror_status`, `legacy_category`.

Notable observed vocabularies (re-confirm from live data each run):
- `status`: In Progress, Closed, Done, Verified, Duplicate, Deployed, Review, Backlog,
  Cancelled, Reopened. Terminal/closed set = Closed, Done, Verified, Deployed.
- `work_type`: Security, Bug, Feature, Enhancement, Refactor, Reliability, Incident,
  Dependency, Chore, Compliance.
- `severity`: S1, S2, S3, S4 (mapped by `sla_policy.days_to_due`).
- `mirror_status` and `legacy_category` are present but **must be ignored** (see
  `data_quality.md`).
