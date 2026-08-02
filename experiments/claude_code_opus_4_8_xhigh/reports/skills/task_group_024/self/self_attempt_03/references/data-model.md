# Data model reference

The environment exposes seven tables (identical names via GET resources and the
`POST /api/query` SQL endpoint). Field notes below are the reusable semantics — treat
authoritative vs. stale exactly as marked. Do not hardcode row values; fetch at runtime.

## work_items
Fields: `id, title, team, product_area, work_type, labels, legacy_category, status,
mirror_status, severity, priority, owner, story_points, created_at, closed_at, due_at,
duplicate_of, milestone_id, release_id`.

| field | role | notes |
|-------|------|-------|
| `id` | key | `WI-24024-<optional UPPERCASE letter><3 digits>`. Plain, `P…`, `S…` variants all valid. Filter on fields, never on prefix. |
| `status` | **authoritative** lifecycle | see state sets below |
| `mirror_status` | **stale** | ignore entirely |
| `work_type` | **authoritative** category signal | maps 1→1 to a portfolio category (see classification.md) |
| `legacy_category` | **stale** | never categorize from it |
| `labels` | supporting signal | `stale-export`, `papertrail` = export-noise markers |
| `title` | weak tiebreak signal | keyword corroboration only |
| `owner` | may be null | null → `UNASSIGNED` / missing-owner list |
| `severity` | S1–S4 | used for SLA policy lookup / severity buckets |
| `due_at` | **authoritative** SLA due date | do NOT recompute from policy (it is set independently) |
| `closed_at` | terminal timestamp | present iff status is a terminal state; source of the quarter |
| `duplicate_of` | duplicate pointer | non-null ⇒ duplicate; value is the canonical target id |
| `milestone_id` / `release_id` | release linkage | may be null |

### status state sets (authoritative `status`)
- **Completed / closed** (carry `closed_at`): `Closed, Done, Verified, Deployed`
- **Open / non-complete** (`closed_at` null): `Backlog, In Progress, Review, Reopened`
- **Excluded from primary**: `Duplicate`, `Cancelled` (both carry `closed_at`, so a bare
  "has closed_at" test is NOT enough — always drop Duplicate/Cancelled first)

A record is a **duplicate** when `status == "Duplicate"` OR `duplicate_of` is non-null.
A record is **cancelled** when `status == "Cancelled"`.
**Primary** = neither.

## mix_targets
Fields: `scope_id, quarter, team_group, product_area, new_feature_pct, tech_debt_pct,
reliability_pct, security_pct`. The `*_pct` values are fractions in 0–1 (×100 for points).
Select the row by the task's `scope_id`.

## sla_policy
Fields: `severity, days_to_due`. Reference table mapping each severity to an SLA window in
days. `due_at` on work items is authoritative and generally does NOT equal
`created_at + days_to_due`, so treat this table as reference, not as the due-date source.

## releases
Fields: `id, name, train, target_date`.

## milestones
Fields: `id, name, owner_team, release_id`. A release has one or more milestones.

## dependencies
Fields: `blocked_id, depends_on_id, relation`. Directed edge: `blocked_id` depends on
`depends_on_id`. Relations observed include `depends-on, blocks-release-readiness,
validation-required, security-review-required, implementation-dependency,
audit-evidence-required`. Build dependency chains by following `blocked_id → depends_on_id`.

## blockers
Fields: `id, work_item_id, release_id, cause, severity, status, opened_at, resolved_at`.
- **Unresolved** ⇔ `resolved_at` is null (equivalently `status != "Resolved"`; open states seen:
  `Open`, `Monitoring`).
- **Severity** ∈ `{Low, Medium, High, Critical}`; **high-impact** = `{High, Critical}`.
- `cause` is free text — when a template keys counts by cause, use the exact string verbatim.
