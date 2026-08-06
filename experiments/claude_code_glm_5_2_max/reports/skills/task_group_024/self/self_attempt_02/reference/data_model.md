# Portfolio Environment — Data Model Reference

Authoritative schema of the shared portfolio environment, distilled from the live
endpoints. Use this as the field/enum dictionary when executing any task in this
family. Field names are identical across the JSON endpoints and the SQL tables.

This file holds **structural vocabulary only** (field names, enum value sets,
endpoint shapes, semantics). It deliberately contains no task-specific answer
values (no computed ids, counts, percentages, or decisions).

## Access

Read `environment_access.md` in the work root for the live base URL, token, and
allowed-endpoint list. Prompts write the base URL as the placeholder
`<TASK_ENV_BASE_URL>` — substitute the real base URL from the env file; never
hardcode it. Every request requires the header `X-Env-Token: <token>`.

Allowed endpoints:

| Method | Path | Notes |
|---|---|---|
| GET | `/api/work-items` | returns `{count, work_items:[...]}` |
| GET | `/api/work-items/{item_id}` | single item |
| GET | `/api/mix-targets` | `{mix_targets:[...]}` |
| GET | `/api/sla-policy` | `{sla_policy:[...]}` |
| GET | `/api/releases` | `{releases:[...]}` |
| GET | `/api/releases/{release_id}` | single release |
| GET | `/api/milestones` | `{milestones:[...]}` |
| GET | `/api/dependencies` | `{dependencies:[...]}` |
| GET | `/api/blockers` | `{blockers:[...]}` |
| POST | `/api/query` | read-only SQL (see below) |

### SQL query endpoint (`POST /api/query`)

- Body: `{"sql": "SELECT ..."}`. Only `SELECT` statements are allowed (no
  `PRAGMA`, `INSERT`, `UPDATE`, `DELETE`, DDL).
- Response: `{"columns": [...], "row_count": N, "rows": [[...]], "truncated": bool}`.
  Watch `truncated` — if true, narrow the query.
- Backend: SQLite. Tables: `work_items`, `mix_targets`, `sla_policy`, `releases`,
  `milestones`, `blockers`, `dependencies`.
- `work_items.labels` is stored as a JSON-encoded string in SQL
  (e.g. `'["security","cve"]'`). Filter with `labels LIKE '%"cve"%'` or parse in
  your own code after fetching via the REST endpoint.
- Use SQL for filtered counts/aggregates; use the REST endpoints for full-record
  fetching and for anything needing parsed `labels`.

## Tables and fields

### `work_items` (primary entity)

| field | kind | authoritative? | notes |
|---|---|---|---|
| `id` | string | yes | pattern `^WI-24024-[A-Z]?[0-9]{3}$` (optional single capital letter prefix, e.g. `WI-24024-P008`) |
| `title` | string | yes | free text; a category signal |
| `work_type` | enum | yes | a category signal (see enum) |
| `status` | enum | **yes (truth)** | authoritative lifecycle state |
| `mirror_status` | enum | **NO — stale** | export/mirror snapshot; disagrees with `status` on most rows; never use as truth |
| `legacy_category` | enum | **NO — stale** | old taxonomy; never use to derive portfolio category |
| `team` | string | yes | owning team |
| `owner` | string\|null | yes | assignee; `null` ⇒ UNASSIGNED / missing-owner |
| `product_area` | enum | yes | e.g. Identity, Checkout, Atlas Backend |
| `created_at` | date | yes | SLA clock start |
| `due_at` | date\|null | yes (planned) | item's planned due; **not** the SLA breach threshold |
| `closed_at` | date\|null | yes | populated exactly for terminal/reviewed states |
| `severity` | enum | yes | S1/S2/S3/S4 — selects SLA policy |
| `priority` | int | yes | 1..5 (1 = highest) — drives escalation order |
| `labels` | [string] | yes | a category signal (see enum) |
| `story_points` | int | yes | portfolio mix uses **item counts**, not story points |
| `release_id` | string\|null | yes | links to `releases.id` |
| `milestone_id` | string\|null | yes | links to `milestones.id` |
| `duplicate_of` | string\|null | yes | canonical id this record duplicates |

**`status` enum** (authoritative):
`Duplicate, Verified, In Progress, Deployed, Closed, Done, Reopened, Backlog, Review, Cancelled`

Closed/terminal states (have `closed_at`): `Closed, Done, Deployed, Verified`
(plus `Duplicate` and `Cancelled` also carry `closed_at` but are excluded — see
below). Open states (no `closed_at`): `Backlog, In Progress, Reopened, Review`.

**`work_type` enum**: `Incident, Refactor, Enhancement, Security, Reliability,
Feature, Bug, Dependency, Chore, Compliance`

**`severity` enum**: `S1, S2, S3, S4`

**`priority`**: integers 1–5; **lower number = higher priority**.

**`labels` universe**: `cleanup, incident, outage, feature, refactor, encryption,
auth, reliability, security, latency, flaky, rollout, cve, stale-export,
customer-request, papertrail, dependency, migration, follow-up, release,
compliance`. (`stale-export` is a tell that the record is a stale export/mirror —
treat such records with suspicion.)

### `mix_targets`

| field | kind | notes |
|---|---|---|
| `scope_id` | string | key; task scopes use literal ids like `train_001`, `train_004`; other rows use composite ids like `2025-Q4:CORE-SYSTEMS:RELEASE-TRAIN` |
| `quarter` | string | e.g. `2025-Q4` |
| `team_group` | string | human label of the team grouping |
| `product_area` | string | may be a compound label like `Atlas Backend + Identity` |
| `new_feature_pct` | number | **fraction 0–1** |
| `tech_debt_pct` | number | fraction 0–1 |
| `reliability_pct` | number | fraction 0–1 |
| `security_pct` | number | fraction 0–1 |

The four `*_pct` are **proportions (0–1)**. Convert to percentage points for the
answer: `target_pct = round(fraction * 100, 1)`. They sum to 1.0; the four
`target_pct` values therefore sum to 100.0 — use this as a sanity check.

Select the target row by exact `scope_id` match against the task's stated
`scope_id` / `target_scope_id`. Do not match on `product_area` or `team_group`
alone — multiple rows can share those.

### `sla_policy`

| field | kind | notes |
|---|---|---|
| `severity` | enum | S1/S2/S3/S4 |
| `days_to_due` | int | SLA clock budget |

Observed: `S1→3, S2→10, S3→21, S4→45` days. **SLA due date** for a work item =
`created_at + days_to_due[severity]`. This is the authoritative SLA breach
threshold — do **not** substitute the work item's `due_at` field (that is a
planned/negotiated date, not the SLA clock).

### `releases`

| field | kind |
|---|---|
| `id` | string (e.g. `REL-ORION-2026-02`) |
| `name` | string |
| `target_date` | date |
| `train` | string |

### `milestones`

| field | kind | notes |
|---|---|---|
| `id` | string | sort key |
| `name` | string | |
| `owner_team` | string | |
| `release_id` | string | links to `releases.id` |

Milestones carry **no status field** — completion is derived from the linked
work items (`work_items.milestone_id == milestones.id`): a milestone's
`primary_total` = count of primary work items linked to it; `complete_primary` =
those whose `status` is a completed state.

### `blockers`

| field | kind | notes |
|---|---|---|
| `id` | string | |
| `work_item_id` | string | blocked work item |
| `release_id` | string | scoped to a release |
| `severity` | enum | `Low, Medium, High, Critical` |
| `cause` | string | exact text — used as a grouping key verbatim |
| `status` | enum | `Open, Monitoring, Resolved` |
| `opened_at` | date | |
| `resolved_at` | date\|null | `null` ⇒ **unresolved** |

"High-impact" = severity `High` or `Critical`. "Unresolved" = `resolved_at` is
null (do not rely on `status` text alone — use `resolved_at`).

### `dependencies`

| field | kind | notes |
|---|---|---|
| `blocked_id` | string | the blocked work item |
| `depends_on_id` | string | the dependency (may itself be a work item id, incl. prefixed ids) |
| `relation` | enum | see below |

`relation` enum: `depends-on, blocks-release-readiness, security-review-required,
validation-required, implementation-dependency, audit-evidence-required`.

The gating/critical relations are `blocks-release-readiness,
security-review-required, validation-required, audit-evidence-required,
implementation-dependency` (relations that block readiness); `depends-on` is a
generic edge. A "critical dependency chain" is an ordered path of work-item ids
from blocked release work down to a non-complete dependency, following these
edges.

## Cross-field semantics that matter

### "Closed" portfolio work (mix tasks)

An item counts as closed portfolio work when `closed_at` falls inside the scope
quarter **and** `status` is a completed state (`Closed, Done, Deployed,
Verified`). `Reopened` is not closed. `Cancelled` and `Duplicate` are excluded
even though they carry `closed_at`.

### Duplicates (the trap)

`duplicate_of` and `status = Duplicate` are **not** perfectly aligned — this is
intentional. Treat an item as a duplicate (excluded from primary counts) when
**`status == Duplicate` OR `duplicate_of` is non-null**. Concretely you will
meet three shapes:
- `status=Duplicate` and `duplicate_of` set → duplicate; cluster under that
  `duplicate_of` (primary) id.
- `status=Duplicate` and `duplicate_of` null → duplicate; excluded from primary,
  but it has no canonical pointer so it cannot join a cluster (report as
  excluded, no primary_id).
- `status` completed (e.g. `Closed`) but `duplicate_of` set → "points at another
  work item"; excluded as a duplicate per the exclusion-flag definition, even
  though its own status looks completed.

`duplicate_clusters` are **reported but never counted as primary work**. The
canonical/primary record referenced by `duplicate_of` is the one that counts
(if it is itself in scope and primary).

### Authoritative vs stale (universal)

- Lifecycle truth = `status`. Never `mirror_status` (disagrees on most rows).
- Portfolio category = derived from `work_type` + `labels` + `title`. Never
  `legacy_category`.
- SLA breach threshold = `created_at + sla_policy.days_to_due[severity]`. Never
  the item's `due_at` field.
- Release truth = `releases`/`milestones`/`blockers`/`dependencies` tables and
  `work_items.status`. Never stale mirror/export fields (watch the
  `stale-export` label).
