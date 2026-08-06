# Environment data model

Reference for the seven tables in the shared environment. Field names and value
vocabularies are stable; verify with `SELECT * FROM <table> LIMIT 1` if a task
behaves unexpectedly.

## `work_items` — the core table

| column           | type           | notes                                                                 |
|------------------|----------------|-----------------------------------------------------------------------|
| `id`             | string         | work item id, format `WI-24024-NNN` (may include a letter prefix)                                     |
| `title`          | string         | free text; used as a category signal                                  |
| `work_type`      | string         | see vocabulary below; authoritative for category                      |
| `status`         | string         | **authoritative** status; see vocabulary/class table below            |
| `team`           | string         | owning team                                                           |
| `owner`          | string \| null | owner name; **null ⇒ missing owner / UNASSIGNED**                     |
| `product_area`   | string         | product area                                                          |
| `created_at`     | date           | creation date; basis for SLA due date                                 |
| `due_at`         | date           | nominal due date                                                      |
| `closed_at`      | date \| null   | populated exactly for resolved states (see class table)               |
| `severity`       | string         | `S1` / `S2` / `S3` / `S4`                                             |
| `priority`       | integer        | 1 = highest                                                           |
| `labels`         | array<string>  | tag list; used as a category signal                                   |
| `story_points`   | integer        | **not used** for portfolio counts (counts are item counts)            |
| `release_id`     | string \| null | links to `releases.id`                                                |
| `milestone_id`   | string \| null | links to `milestones.id`                                              |
| `duplicate_of`   | string \| null | when set, this record is a duplicate pointing at the canonical primary |
| `mirror_status`  | string         | **stale — ignore** as status truth                                    |
| `legacy_category`| string         | **stale — ignore** for portfolio category                             |

### `status` vocabulary and class

| status                                       | closed_at | class                |
|----------------------------------------------|-----------|----------------------|
| `Closed`, `Done`, `Deployed`, `Verified`     | set       | completed / terminal |
| `Cancelled`                                  | set       | excluded (cancelled) |
| `Duplicate`                                  | set       | excluded (duplicate) |
| `Backlog`, `In Progress`, `Review`, `Reopened` | null    | open / active        |

`closed_at IS NOT NULL` is a reliable secondary signal that a record has reached
a resolved state — but `Cancelled` and `Duplicate` also carry `closed_at`, so
always combine it with the `status` class.

### Duplicate signal
- `duplicate_of IS NOT NULL` ⇒ the record is a duplicate; the value is the
  canonical `primary_id` it points at.
- `status = "Duplicate"` corroborates. A record with `status = "Duplicate"` but
  `duplicate_of` null is an **orphan duplicate**: exclude from primary counts,
  but it has no primary to cluster under.
- **Primary** = not duplicate and not cancelled.

### `work_type` vocabulary
`Feature`, `Enhancement`, `Refactor`, `Bug`, `Chore`, `Security`, `Reliability`,
`Incident`, `Compliance`, `Dependency`.

### `severity` vocabulary
`S1` (highest) → `S2` → `S3` → `S4` (lowest).

### `legacy_category` vocabulary (stale — do not use)
`bug`, `new`, `security`, `maintenance`, `quality`, `feature`, `tech-debt`,
`admin`, `release`, `incident`.

### `mirror_status` vocabulary (stale — do not use)
`Open`, `Done`, `Complete`, `Closed`, `Blocked`, `In Progress`, `Verified`,
`Review`, `Backlog`.

## `mix_targets`

| column             | type   | notes                                              |
|--------------------|--------|----------------------------------------------------|
| `scope_id`         | string | matches the `scope_id` named in the prompt         |
| `quarter`          | string | e.g. `2025-Q4`                                     |
| `team_group`       | string | human-readable team grouping                       |
| `product_area`     | string | product area for the target                        |
| `new_feature_pct`  | number | **fraction 0–1**; × 100 for percentage points      |
| `tech_debt_pct`    | number | fraction 0–1                                       |
| `reliability_pct`  | number | fraction 0–1                                       |
| `security_pct`     | number | fraction 0–1                                       |

Select the target row by `scope_id`. The four fractions sum to 1.0.

## `sla_policy`

| column        | type    | notes                                            |
|---------------|---------|--------------------------------------------------|
| `severity`    | string  | `S1` / `S2` / `S3` / `S4`                        |
| `days_to_due` | integer | SLA budget from `created_at` (S1=3, S2=10, S3=21, S4=45) |

SLA due date = `created_at + days_to_due(severity)`.

## `releases`

| column        | type   |
|---------------|--------|
| `id`          | string | format `REL-<TRAIN>-YYYY-MM` |
| `name`        | string |
| `target_date` | date   |
| `train`       | string |

## `milestones`

| column        | type   | notes                          |
|---------------|--------|--------------------------------|
| `id`          | string | format `MIL-<TRAIN>-<STAGE>`            |
| `name`        | string |                                |
| `owner_team`  | string |                                |
| `release_id`  | string | links to `releases.id`         |

Filter milestones for a release by `release_id`.

## `dependencies`

| column          | type   | notes                                                       |
|-----------------|--------|-------------------------------------------------------------|
| `blocked_id`    | string | work item that is blocked                                   |
| `depends_on_id` | string | work item it depends on                                     |
| `relation`      | string | edge type (see vocabulary)                                  |

`relation` vocabulary: `blocks-release-readiness`, `validation-required`,
`depends-on`, `security-review-required`, `implementation-dependency`,
`audit-evidence-required`. Follow `depends_on_id` edges to build dependency
chains from blocked release work to non-complete dependencies.

## `blockers`

| column        | type        | notes                                              |
|---------------|-------------|----------------------------------------------------|
| `id`          | string      | format `BLK-24024-NNN`                               |
| `cause`       | string      | **exact** text used as the cause-count key         |
| `opened_at`   | date        |                                                    |
| `release_id`  | string      | links to `releases.id`                             |
| `resolved_at` | date \| null| **null ⇒ unresolved**                              |
| `severity`    | string      | `Low` / `Medium` / `High` / `Critical`             |
| `status`      | string      | `Open` / `Monitoring` / `Resolved`                 |
| `work_item_id`| string      | affected work item                                 |

For release-readiness blocker cause counts: unresolved (`resolved_at` null) **and**
high-impact (`severity` `High` or `Critical`), keyed by exact `cause`.
