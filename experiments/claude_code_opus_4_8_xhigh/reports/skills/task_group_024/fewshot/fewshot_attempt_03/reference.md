# Reference: environment data model & decision rules

This file documents the shared environment behind every task so the rules in
`SKILL.md` are unambiguous. It describes conventions of the environment, not any
task's answer.

## Endpoints (from `environment_access.md`)

Base URL and the `X-Env-Token` value are given in `environment_access.md`; read
them at runtime. All GET endpoints are read-only and unauthenticated; only
`POST /api/query` needs the header.

| Endpoint | Returns |
|---|---|
| `GET /api/work-items` | `{count, work_items:[...]}` — the whole backlog |
| `GET /api/work-items/{id}` | one work item |
| `GET /api/mix-targets` | `{mix_targets:[...]}` — target portfolio mix rows |
| `GET /api/sla-policy` | `{sla_policy:[{severity, days_to_due}]}` |
| `GET /api/releases` / `/api/releases/{id}` | releases |
| `GET /api/milestones` | milestones (each has `release_id`, `owner_team`) |
| `GET /api/dependencies` | `{dependencies:[{blocked_id, depends_on_id, relation}]}` |
| `GET /api/blockers` | `{blockers:[{id, work_item_id, release_id, cause, severity, status, opened_at, resolved_at}]}` |
| `POST /api/query` | `{sql}` → `{columns, rows, row_count, truncated}`; needs `X-Env-Token`. Table name: `work_items`. |

## Work item fields

Authoritative: `id`, `status`, `work_type`, `labels`, `title`, `team`,
`product_area`, `owner`, `severity`, `priority`, `created_at`, `closed_at`,
`due_at`, `duplicate_of`, `release_id`, `milestone_id`, `story_points`.

**Stale / mirror — never use as truth:** `mirror_status`, `legacy_category`.
Tasks call these out explicitly ("do not use stale mirror fields", the
`ignored_mirror_status_and_legacy_category` flag). They are export leftovers that
disagree with the authoritative fields on purpose.

### Status vocabulary

- **Complete/done set** (work is finished): `Closed`, `Done`, `Deployed`,
  `Verified`.
- **Not complete**: `Backlog`, `In Progress`, `Review`, `Reopened`.
- **Duplicate**: `status == "Duplicate"` **or** `duplicate_of` is non-null →
  excluded from primary work; the `duplicate_of` value is the canonical/primary id.
- **Cancelled**: `status == "Cancelled"` → excluded from primary work.

## Portfolio category classification

Four categories. Collect every category signalled by the item's `work_type`,
`labels`, and `title`, then keep the **highest-precedence** one:

```
precedence (high → low):  Security  >  Reliability  >  TechDebt  >  NewFeature
```

`NewFeature` is the fallback when nothing else is signalled.

**work_type → category**

| work_type | category |
|---|---|
| Security, Compliance | Security |
| Incident, Reliability, Bug | Reliability |
| Refactor, Chore, Dependency | TechDebt |
| Feature, Enhancement | NewFeature |

**keyword → category** (case-insensitive substring over `labels` + `title`)

| category | keywords |
|---|---|
| Security | security, cve, auth, encryption, compliance, vuln |
| Reliability | reliability, incident, outage, latency, flaky |
| TechDebt | cleanup, refactor, migration, dependency, chore, tech-debt |
| NewFeature | feature, enhancement, rollout |

Noise labels that carry no category signal: `customer-request`, `follow-up`,
`papertrail`, `release`, `stale-export`.

Example of precedence in action: an item with `work_type=Feature` but a
`security` label classifies as **Security** (Security outranks NewFeature); an
item with `work_type=Chore` and a `reliability` label classifies as
**Reliability** (Reliability outranks TechDebt).

## SLA policy

`sla_policy` maps severity → allowed `days_to_due`. In this environment each work
item's `due_at` is already computed, so overdue is judged directly from
`due_at` / `closed_at` / the as-of date (the policy table is informational).

- **Overdue**: closed item → `closed_at > due_at`; open item → `due_at < as_of`
  (strictly before; `due_at == as_of` is *not* overdue).
- **Age (for aging buckets)**: `(closed_at or as_of) - created_at`, in days.
  Buckets (inclusive): `0-3`, `4-7`, `8-14`, `15-30`, `31+`.
- **Days overdue (for escalation priority)**: `(closed_at or as_of) - due_at`.
- **Escalation order**: severity ascending (`S1 < S2 < S3 < S4`), then days
  overdue descending, then id ascending.
- **Breach rate**: overdue primary count ÷ primary count, rounded to 3 decimals.

## Release readiness decision

- **milestone primary** = release work items with that `milestone_id`, excluding
  duplicates and cancelled. **complete** uses the done set on `status`.
- **readiness_score** = total complete primary ÷ total primary across the
  release's milestones, 3 decimals.
- **unresolved high-impact blocker** = blocker for the release with
  `severity ∈ {High, Critical}` and `resolved_at` null (status not `Resolved`).
- **gating_work_item_ids** = non-complete primary release items that carry an
  unresolved high-impact blocker.
- **critical_dependency_chains** = starting from each gating item, follow
  `dependencies` edges (`blocked_id → depends_on_id`) to any **non-complete**
  dependency; the path `[gating_id, …, non_complete_dep_id]` is a chain. If every
  dependency of every gating item is complete, the list is empty.
- **ship_decision**: `NO_SHIP` if there are gating items, critical chains, or any
  unresolved Critical blocker; `SHIP` only if readiness is 1.0 with no unresolved
  high-impact blockers and nothing gating; otherwise `SHIP_WITH_WATCH`.
