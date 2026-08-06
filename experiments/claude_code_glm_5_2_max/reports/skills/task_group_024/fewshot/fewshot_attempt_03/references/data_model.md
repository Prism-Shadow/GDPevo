# Data Model — Shared Portfolio Environment

The environment exposes 7 tables over both typed GET endpoints and the
`POST /api/query` SQL endpoint. This document lists every table's columns,
semantics, and observed value spaces so you can write correct filters and joins.

> Always read `environment_access.md` for the live base URL, token, and
> endpoint list. Send the `X-Env-Token` header on every request.

## SQL query endpoint

`POST /api/query` with JSON body `{"sql": "<read-only SELECT>"}`.

Response shape:
```json
{"columns": ["..."], "row_count": N, "rows": [[...], ...], "truncated": false}
```

- `rows` is an array of arrays (positional, in `columns` order) — not objects.
- `truncated: true` means results were cut off; re-query with a tighter
  `WHERE`/`LIMIT`.
- Read-only `SELECT` only (across the 7 tables below). `PRAGMA table_info` is
  **not** supported — inspect columns with `SELECT * FROM <t> LIMIT 1` or via the
  matching GET endpoint.
- All 7 tables: `work_items`, `mix_targets`, `sla_policy`, `releases`,
  `milestones`, `dependencies`, `blockers`.

## work_items

GET `/api/work-items` (list), `/api/work-items/{id}` (single, wrapped as
`{"work_item": {...}}`). Table `work_items`.

| field | type | semantics |
|---|---|---|
| `id` | string | Work-item id, pattern `WI-24024-...`. Primary key. |
| `team` | string | Owning team. Used for scope filtering. |
| `product_area` | string | Product area. Used for scope filtering. |
| `status` | string | **Authoritative** status. See value space below. |
| `mirror_status` | string | **Stale mirror/export status — ignore.** Diverges from `status`. |
| `work_type` | string | Type signal for category resolution (e.g. `Security`, `Reliability`, `Feature`, `Refactor`, `Incident`). |
| `labels` | array[string] | Keyword tags. Strongest signal for category resolution. |
| `title` | string | Free text; scanned for category keywords. |
| `legacy_category` | string | **Deprecated — ignore.** Free-text category that conflicts with reality. |
| `severity` | string | `S1`/`S2`/`S3`/`S4`. |
| `priority` | integer | Priority integer (1 is highest). |
| `owner` | string\|null | Owner name; `null` = missing owner (report as `UNASSIGNED`). |
| `created_at` | date\|null | `YYYY-MM-DD`. |
| `due_at` | date\|null | `YYYY-MM-DD`. **Overdue = `as_of > due_at`.** |
| `closed_at` | date\|null | `YYYY-MM-DD`. Used for aging basis and closed-window filtering. |
| `duplicate_of` | string\|null | Canonical primary id this duplicates. Non-null ⇒ duplicate. |
| `milestone_id` | string\|null | Links to `milestones.id`. |
| `release_id` | string\|null | Links to `releases.id`. |
| `story_points` | integer | Story points. **Not used** — portfolio mix is item-count-based, not points. |

**`status` value space** (authoritative):
`Backlog`, `Cancelled`, `Closed`, `Deployed`, `Done`, `Duplicate`,
`In Progress`, `Reopened`, `Review`, `Verified`.

- Terminal / closed / complete set: `Closed`, `Done`, `Deployed`, `Verified`.
- Non-terminal: `Backlog`, `In Progress`, `Review`, `Reopened`.
- Excluded from primary population: `Cancelled`, `Duplicate`.

**`mirror_status` value space** (stale — do not use as truth): includes
`Backlog`, `Blocked`, `Closed`, `Complete`, `Done`, `In Progress`, `Open`,
`Review`, `Verified`. Note values like `Open`, `Complete`, `Blocked` do not even
exist in the authoritative `status` set.

**`work_type` value space:** `Bug`, `Chore`, `Compliance`, `Dependency`,
`Enhancement`, `Feature`, `Incident`, `Refactor`, `Reliability`, `Security`.

**`legacy_category` value space** (ignore): `admin`, `bug`, `feature`,
`incident`, `maintenance`, `new`, `quality`, `release`, `security`, `tech-debt`.

**`severity` value space:** `S1`, `S2`, `S3`, `S4`.

## mix_targets

GET `/api/mix-targets`. Table `mix_targets`. One row per scope; **keyed by
`scope_id`** (the prompt names the target `scope_id`).

| field | type | semantics |
|---|---|---|
| `scope_id` | string | Key used to select the target row (e.g. a train/test scope id). |
| `quarter` | string | e.g. `2025-Q4`. |
| `team_group` | string | Display grouping of teams. |
| `product_area` | string | Product area for the target. |
| `new_feature_pct` | number | Target fraction for NewFeature (0–1). ×100 ⇒ percentage points. |
| `tech_debt_pct` | number | Target fraction for TechDebt (0–1). |
| `reliability_pct` | number | Target fraction for Reliability (0–1). |
| `security_pct` | number | Target fraction for Security (0–1). |

The four target fractions sum to 1.0. Convert to percentage points by ×100 and
round to 1 decimal place for `target_pct`.

## sla_policy

GET `/api/sla-policy`. Table `sla_policy`. Severity → SLA allowance.

| field | type | semantics |
|---|---|---|
| `severity` | string | `S1`/`S2`/`S3`/`S4`. |
| `days_to_due` | integer | SLA day allowance for the severity. |

Observed policy: `S1=3`, `S2=10`, `S3=21`, `S4=45` days. (Read the table at run
time; do not assume.) Note: in the SLA-aging archetype, **overdue is determined
by `as_of > due_at`, not by comparing an age to `days_to_due`** — see
`archetypes.md`. The policy table is reference data describing the SLA framework.

## releases

GET `/api/releases`, `/api/releases/{id}`. Table `releases`.

| field | type | semantics |
|---|---|---|
| `id` | string | Release id, e.g. `REL-<TRAIN>-YYYY-MM`. The prompt names the `release_id`. |
| `name` | string | Display name. |
| `target_date` | date | Target ship date. |
| `train` | string | Release train name. |

## milestones

GET `/api/milestones`. Table `milestones`.

| field | type | semantics |
|---|---|---|
| `id` | string | Milestone id, e.g. `MIL-...`. Sort `milestone_completion` by this ascending. |
| `name` | string | Display name. |
| `owner_team` | string | Team that owns the milestone. |
| `release_id` | string | Links to `releases.id`. Filter milestones by the release under review. |

Release work items link to milestones via `work_items.milestone_id`.

## dependencies

GET `/api/dependencies`. Table `dependencies`.

| field | type | semantics |
|---|---|---|
| `blocked_id` | string | Work-item id that is blocked. |
| `depends_on_id` | string | Work-item id it depends on (the dependency). |
| `relation` | string | Relation type. |

**`relation` value space:** `audit-evidence-required`,
`blocks-release-readiness`, `depends-on`, `implementation-dependency`,
`security-review-required`, `validation-required`.

A **critical dependency chain** is an ordered work-item-id path from a blocked
release work item to a **non-complete** dependency (follow `blocked_id →
depends_on_id` edges; the chain is critical only if it terminates at a
non-complete item). See `archetypes.md` §C.

## blockers

GET `/api/blockers`. Table `blockers`.

| field | type | semantics |
|---|---|---|
| `id` | string | Blocker id, e.g. `BLK-...`. |
| `cause` | string | Exact cause text. Used as the key in `blocker_cause_counts`. |
| `severity` | string | `Critical`/`High`/`Medium`/`Low`. "High-impact" = `High` or `Critical`. |
| `status` | string | `Open`/`Monitoring`/`Resolved`. "Unresolved" = anything ≠ `Resolved`. |
| `opened_at` | date | When the blocker opened. |
| `resolved_at` | date\|null | When resolved; `null` while unresolved. |
| `release_id` | string | Links to `releases.id`. |
| `work_item_id` | string | The work item the blocker is against. |

**`blocker_cause_counts`** counts **unresolved high-impact** blockers
(`status != Resolved` AND `severity ∈ {High, Critical}`) for the release, keyed
by the exact `cause` string.
