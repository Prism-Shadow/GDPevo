# Reference — portfolio environment

Companion to `SKILL.md`. Environment schema, vocabularies, classification detail,
and SQL recipes. These are environment invariants (the same across tasks), not the
answer to any one task — always compute the actual answer from live data.

## Endpoints (from the runtime-access file)

```
GET  /api/work-items                 GET /api/releases            GET /api/milestones
GET  /api/work-items/{item_id}       GET /api/releases/{id}       GET /api/dependencies
GET  /api/mix-targets                GET /api/sla-policy          GET /api/blockers
POST /api/query   (header X-Env-Token: <token>; SQLite SQL over the tables below)
```

## Field dictionary

**work_items** (`id`, e.g. `WI-24024-070`, `WI-24024-S004`, `WI-24024-P069`):
- `status` — **authoritative** state. Vocabulary: `Backlog, In Progress, Review,
  Reopened, Verified, Done, Deployed, Closed, Duplicate, Cancelled`.
  Terminal-completed = `Closed, Deployed, Done, Verified`. `Duplicate`/`Cancelled`
  are exclusions. `Backlog/In Progress/Review/Reopened` are not complete.
- `mirror_status` — **STALE, ignore.** (`Open, Done, Complete, Closed, Blocked,
  Backlog, In Progress, Review, Verified` — deliberately inconsistent with `status`.)
- `work_type` — **authoritative** type signal: `Feature, Enhancement, Refactor,
  Chore, Dependency, Bug, Incident, Reliability, Security, Compliance`.
- `legacy_category` — **STALE, ignore.** (`admin, bug, feature, incident,
  maintenance, new, quality, release, security, tech-debt`.)
- `labels` — array of tags (see keyword sets). `title` — free text with keywords.
- `duplicate_of` — canonical id this record duplicates, or null.
- `owner` — person or null (null → missing owner / UNASSIGNED).
- `severity` — `S1, S2, S3, S4`. `closed_at`, `created_at`, `due_at` — ISO dates
  (or null). `team`, `product_area`, `release_id`, `milestone_id`, `priority`,
  `story_points`.

**mix_targets**: `scope_id`, `quarter`, `team_group`, `product_area`,
`new_feature_pct`, `tech_debt_pct`, `reliability_pct`, `security_pct`
(fractions in [0,1]; ×100 → percentage points). Tasks reference a row **by its
`scope_id`** (e.g. the task's own scope id).

**sla_policy**: rows `{severity, days_to_due}`. Deadline = `created_at +
days_to_due[severity]`.

**releases**: `id, name, train, target_date`.
**milestones**: `id, name, owner_team, release_id`.
**blockers**: `id, work_item_id, release_id, cause, severity (Critical/High/
Medium/Low), status (Open/Monitoring/Resolved), opened_at, resolved_at`.
High-impact + unresolved = `severity ∈ {Critical, High}` AND `resolved_at IS NULL`.
**dependencies**: `blocked_id, depends_on_id, relation`. Relations:
`depends-on, blocks-release-readiness, security-review-required,
validation-required, audit-evidence-required, implementation-dependency`.

## Classification keyword sets (conflict tiebreak — precedence high→low)

Primary rule is the `work_type` map in SKILL.md §4. When `work_type` is generic or
labels/title conflict, pick the **highest-precedence** category with any matching
signal:

1. **Security** — work_type Security/Compliance; labels/title: `security, cve, auth,
   encryption, compliance, audit, vuln, patch, token, secret`.
2. **Reliability** — work_type Reliability/Incident/Bug; labels/title: `reliability,
   incident, outage, latency, flaky, slo, availability, stabilize, replay, degradation`.
3. **TechDebt** — work_type Refactor/Chore/Dependency; labels/title: `tech-debt,
   cleanup, refactor, migrate, deprecate, chore, dependency, upgrade`.
4. **NewFeature** — work_type Feature/Enhancement; labels/title: `feature,
   enhancement, rollout, launch, new` (also the default when nothing else matches).

Apply identically to every item. `legacy_category` is never a signal.

## SLA computation

- Deadline (authoritative) = `date(created_at, '+' || days_to_due || ' days')`
  via the `sla_policy` row for the item's `severity`.
- Overdue / breach: `closed_at > deadline` (resolved late), or for unresolved
  items `as_of > deadline`.
- Days overdue = `julianday(closed_at) − julianday(deadline)` (floor at 0); bucket
  per the template labels (e.g. `0-3, 4-7, 8-14, 15-30, 31+`) or by severity.
- `due_at` deviates widely from policy (mirror-like) — do not use it as the
  deadline unless a task explicitly designates it authoritative.
- `breach_rate = overdue_primary_count / included_primary_count`, 3 dp.

## Duplicate clusters

Union of duplicate signals for exclusion: `status='Duplicate' OR duplicate_of IS NOT NULL`
(the two only partly overlap — some Duplicate-status rows have null pointer, some
pointered rows have another status). Build clusters by grouping duplicate records on
their `duplicate_of` value → that value is the `primary_id`; sort `duplicate_ids`
lexicographically, clusters by `primary_id`.

## SQL recipes (generic — fill in scope values from the task)

```sql
-- distinct vocabulary of any column
SELECT DISTINCT status FROM work_items ORDER BY status;

-- in-scope closed portfolio candidates (portfolio-mix family)
SELECT id, work_type, labels, title, status, closed_at, team, product_area
FROM work_items
WHERE team IN (<teams>) AND product_area IN (<areas>)
  AND status IN ('Closed','Deployed','Done','Verified')
  AND closed_at BETWEEN '<q_start>' AND '<q_end>'
ORDER BY closed_at, id;

-- target row for a scope
SELECT new_feature_pct, tech_debt_pct, reliability_pct, security_pct
FROM mix_targets WHERE scope_id = '<scope_id>';

-- SLA-relevant recently-closed primary candidates (SLA family)
SELECT w.id, w.severity, w.owner, w.created_at, w.closed_at, w.work_type, w.labels, w.title,
       date(w.created_at, '+' || p.days_to_due || ' days') AS deadline
FROM work_items w JOIN sla_policy p ON w.severity = p.severity
WHERE w.team IN (<teams>)
  AND w.status <> 'Duplicate' AND w.status <> 'Cancelled' AND w.duplicate_of IS NULL
  AND w.closed_at BETWEEN date('<as_of>', '-<window> days') AND '<as_of>'
ORDER BY w.id;

-- unresolved high-impact blockers for a release, grouped by exact cause
SELECT cause, COUNT(*) FROM blockers
WHERE release_id = '<release>' AND resolved_at IS NULL
  AND severity IN ('Critical','High')
GROUP BY cause;

-- release work items and their milestone/status (release-readiness family)
SELECT id, milestone_id, status FROM work_items WHERE release_id = '<release>' ORDER BY id;
```

Do category classification (labels/title parsing) in code after pulling rows —
keep the SQL to filtering/aggregation.
