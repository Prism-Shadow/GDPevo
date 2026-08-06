# Portfolio environment — data model & field reference

This is the shared read-only environment behind every task in this family. Endpoints,
field names, and enum vocabularies are stable across tasks; only the *scope* (teams,
areas, quarter, as-of date, release, scope_id) changes per task. Re-verify anything
below against the live environment at the start of each run — treat it as a map, not as
cached truth.

## Access

- Base URL: from `environment_access.md` (task prompts use the placeholder
  `<TASK_ENV_BASE_URL>`). Substitute the real base URL from that file.
- Auth: header `X-Env-Token: <token>` (currently `portfolio-readonly`) is **required for
  `POST /api/query`** and harmless on GETs.
- `GET /` and unknown paths return `{"error": "not found"}` — there is no docs/schema
  endpoint; the model below is derived by inspection.

### Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/work-items` | `{count, work_items:[...]}` — the whole item table |
| `GET /api/work-items/{id}` | `{work_item:{...}}` |
| `GET /api/mix-targets` | `{mix_targets:[...]}` — target investment mix rows |
| `GET /api/sla-policy` | `{sla_policy:[{severity, days_to_due}]}` |
| `GET /api/releases` / `/{id}` | release header rows |
| `GET /api/milestones` | milestone rows (each tied to a release) |
| `GET /api/dependencies` | `{dependencies:[{blocked_id, depends_on_id, relation}]}` |
| `GET /api/blockers` | `{blockers:[...]}` |
| `POST /api/query` | restricted SQL over the tables below; body `{"sql":"..."}`; returns `{columns, rows, row_count, truncated}` |

`POST /api/query` exposes these tables: `work_items, mix_targets, sla_policy, releases,
milestones, dependencies, blockers`. SQL is the fastest way to filter/aggregate; use
double-quoted identifiers and escape quotes in the JSON body. `labels` is stored as a
JSON string inside a text column.

## work_items — field authority map

Every item carries both **authoritative** operational fields and **decoy** fields that
mirror or predate them. Trust the authoritative column; never let a decoy drive a
decision.

| Field | Role | Authority |
|---|---|---|
| `id` | e.g. `WI-24024-070`, `WI-24024-P006`, `WI-24024-S002` — optional single-letter class prefix before 3 digits | key |
| `status` | lifecycle state | **AUTHORITATIVE** for completion/closure |
| `work_type` | item type | **AUTHORITATIVE** for portfolio category |
| `owner` | assignee (may be `null`) | authoritative |
| `team`, `product_area` | org scope | authoritative |
| `closed_at`, `created_at`, `due_at` | dates (`YYYY-MM-DD`) | authoritative; `due_at` is the SLA deadline |
| `severity` | `S1..S4` | authoritative |
| `duplicate_of` | canonical id this record duplicates (or `null`) | authoritative dedup signal |
| `milestone_id`, `release_id` | release linkage (may be `null`) | authoritative |
| `labels`, `title` | free-text signals | secondary; **noisy/adversarial** |
| `priority`, `story_points` | numeric | context only (counts are by item, not points) |
| `mirror_status` | replica of status from an export | **STALE DECOY — ignore** |
| `legacy_category` | old category taxonomy | **LEGACY DECOY — ignore** |

`status` vocabulary: `Backlog, In Progress, Review, Reopened, Done, Deployed, Closed,
Verified, Duplicate, Cancelled`.
`mirror_status` uses a *different* set (`Open, Blocked, Complete, ...`) and frequently
disagrees with `status` — that disagreement is the trap.
`legacy_category`: `admin, bug, feature, incident, maintenance, new, quality, release,
security, tech-debt` — does **not** align with `work_type` and must not be used to
classify.

### Status groupings (authoritative `status`)

- **COMPLETE / closed-successfully:** `Closed, Done, Deployed, Verified`
- **ACTIVE / not-complete:** `Backlog, In Progress, Review, Reopened`
- **EXCLUDE from primary work entirely:** `Duplicate`, `Cancelled`
  (report separately where the template asks; never count as primary)

## Portfolio category conventions (the four buckets)

Portfolio categories are exactly: **NewFeature, TechDebt, Reliability, Security**.

Classify by **`work_type` (authoritative)** using this canonical map:

| work_type | Portfolio category |
|---|---|
| Feature, Enhancement | NewFeature |
| Refactor, Chore, Dependency | TechDebt |
| Bug, Incident, Reliability | Reliability |
| Security, Compliance | Security |

Rules for resolving conflicting **type / label / title** signals:

1. `work_type` decides the category. `labels` and `title` are deliberately misleading
   (e.g. a `Feature` item tagged `incident,outage`, or titled `... with stale security
   label`) — they do **not** override the type.
2. Use `labels`/`title` only to break a genuine ambiguity when `work_type` alone is
   insufficient; when you must, apply a fixed category precedence
   **Security > Reliability > TechDebt > NewFeature** so ties resolve deterministically.
3. Never classify from `legacy_category` or `mirror_status`.
4. Apply the same map consistently to every item in every task.

## Duplicates & clusters

An item is a **duplicate** when `status = 'Duplicate'` **or** `duplicate_of IS NOT NULL`
(a Duplicate can even carry a non-Duplicate status; a non-null `duplicate_of` on any
status still marks it a duplicate). Cluster duplicates by their `duplicate_of` value: the
canonical `primary_id` plus its sorted `duplicate_ids`. Some Duplicate records have a null
`duplicate_of` (no canonical recorded) — they cannot form a cluster; just exclude them.

## mix_targets

Rows keyed by `scope_id`. A task names its `scope_id` directly (e.g. `train_001`); look up
that exact row. Percentage fields are **fractions in [0,1]** and must be ×100 for
percentage points:

`new_feature_pct → NewFeature`, `tech_debt_pct → TechDebt`,
`reliability_pct → Reliability`, `security_pct → Security`
(plus `quarter, team_group, product_area` describing the scope).

## sla_policy

`[{severity, days_to_due}]` (e.g. S1→3, S2→10, S3→21, S4→45). **`due_at` on the work item
is the authoritative deadline** and is *not* recomputed from this policy (the two do not
match in the data). Treat `sla_policy` as reference/context, not as a source to derive
due dates — confirm per run.

## releases / milestones

- `releases`: `{id, name, target_date, train}`.
- `milestones`: `{id, name, owner_team, release_id}` — a release has several milestones.
- A release's work items link via `release_id` (and each also carries a `milestone_id`).

## blockers

`{id, work_item_id, release_id, cause, severity, status, opened_at, resolved_at}`.
- `severity`: `Critical, High, Medium, Low`. **High-impact = {Critical, High}.**
- **Unresolved = `resolved_at IS NULL`** (status may be `Open` or `Monitoring`; both are
  unresolved while `resolved_at` is null).
- `cause` is free text — use exact strings as keys when the template asks for cause counts.

## dependencies

`{blocked_id, depends_on_id, relation}`. Relation vocabulary includes
`blocks-release-readiness, validation-required, depends-on, security-review-required,
implementation-dependency, audit-evidence-required`. For release-readiness gating chains,
`blocks-release-readiness` is the release-gating relation; follow edges
`blocked_id → depends_on_id` to build ordered paths.

## Distractor / trap catalog (seen across tasks)

- **Stale mirror**: `mirror_status` disagreeing with `status` (e.g. `status=Cancelled`,
  `mirror_status=Done`). Ignore `mirror_status`.
- **Legacy category**: `legacy_category` conflicting with `work_type`. Ignore it.
- **Adversarial labels/titles**: security/incident words on a Feature; `stale-export`,
  `papertrail` labels; titles containing "stale", "mirror", "duplicate ... export".
  Classify by `work_type`, and treat these as duplicates/decoys where marked.
- **Class-prefixed ids** (`-P###`, `-S###`): additional scenario/distractor records that
  live in the same teams/areas as plain ids. Include or exclude them by the *same*
  scope + primary rules as any other item — a prefix is not itself a reason to exclude,
  and the item-id pattern in answer templates explicitly allows an optional letter.
- **Out-of-window closed work**: items closed outside the quarter (mix) or the recent
  closed window (SLA) are out of scope even though team/area match.
