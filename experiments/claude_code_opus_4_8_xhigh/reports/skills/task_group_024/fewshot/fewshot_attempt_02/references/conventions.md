# Portfolio environment — data conventions reference

This file expands the rules summarized in `SKILL.md`. Every rule below was
derived so that following it reproduces the authoritative answers for this
environment. Values shown are *conventions/formulas*, never task answers.

## 1. Fields on a work item

`GET /api/work-items` (or SQL `work_items`) returns these columns:

```
id, title, work_type, status, team, owner, product_area,
created_at, due_at, closed_at, severity, priority, labels (JSON array text),
story_points, release_id, milestone_id, duplicate_of, mirror_status, legacy_category
```

Authoritative fields: `status`, `work_type`, `labels`, `title`, `team`,
`product_area`, `owner`, `created_at`, `due_at`, `closed_at`, `severity`,
`duplicate_of`, `release_id`, `milestone_id`.

**Stale / decoy fields — never use as truth:** `mirror_status` and
`legacy_category`. They are deliberately inconsistent with the authoritative
`status`/category. Titles/labels containing words like `stale`, `mirror`,
`export`, `legacy` are decoys — they do **not** change the classification;
resolve everything through the precedence in §3. `closed_at` can occasionally
sit in the future or disagree with `status`; trust `status` for completion.

## 2. Status semantics (authoritative `status`)

- **Complete / closed** = `Closed`, `Done`, `Deployed`, `Verified`.
- **Not complete / open** = `Backlog`, `In Progress`, `Review`, `Reopened`.
- **Cancelled** = `Cancelled` → always excluded from primary work.
- **Duplicate** = `status == 'Duplicate'` **OR** `duplicate_of` is non-null →
  excluded from primary work; its canonical/primary id is `duplicate_of`.

A record can have `status == 'Closed'` yet still be a duplicate because
`duplicate_of` is set — always test `duplicate_of` too, not just the status.

## 3. Portfolio category classification (universal)

Four categories: `NewFeature`, `TechDebt`, `Reliability`, `Security`.

Collect category *signals* from three sources — `work_type`, each token in
`labels`, and words in `title` — then pick the **highest-precedence category
that has any signal**:

```
Security  >  Reliability  >  TechDebt  >  NewFeature
```

`NewFeature` is the default: it wins only when no Security/Reliability/TechDebt
signal is present. This precedence is exactly how conflicting type/label/title
signals are resolved (e.g. a `Feature` work_type carrying a `security` label
classifies as Security; an `Enhancement` whose title says "cleanup"
classifies as TechDebt).

Signal dictionary (case-insensitive substring/token match):

| Category    | work_type                    | label / title tokens |
|-------------|------------------------------|----------------------|
| Security    | Security, Compliance         | security, cve, auth, encryption, compliance, audit, exception, vuln |
| Reliability | Reliability, Incident, Bug   | reliability, incident, outage, latency, flaky, slo, availability, rehearsal, guardrail |
| TechDebt    | Refactor, Chore, Dependency  | tech-debt, refactor, cleanup, migration, migrate, chore, debt, deprecate |
| NewFeature  | Feature, Enhancement         | feature, rollout, launch, new, experiment, polish |

Notes:
- `work_type` is only one signal; a label or title token of a higher-precedence
  category overrides it (that is the whole point of the precedence).
- `Bug` alone is weak — decide from its labels/title; if nothing stronger,
  treat as Reliability.
- Ignore `legacy_category` completely when classifying.

## 4. Date windows

- **Quarter** `YYYY-Qn` → a calendar range applied to `closed_at`:
  Q1 = Jan1–Mar31, Q2 = Apr1–Jun30, Q3 = Jul1–Sep30, Q4 = Oct1–Dec31.
- **Recent-closed window of N days** relative to `as_of`:
  a *closed* item qualifies when `as_of - N days <= closed_at <= as_of`.
  This window filters **closed** items only. **Open** items (no `closed_at`)
  are always in the population regardless of age.

## 5. SLA rules

`GET /api/sla-policy` maps severity → `days_to_due` (reference only; each item
already carries an absolute `due_at`, so compute overdue from `due_at`).

- **Overdue, open item** (`closed_at` null): `due_at < as_of` (strict — an item
  due exactly on `as_of` is *not* overdue).
- **Overdue, closed item**: `closed_at > due_at` (closed late = SLA breach).
- **Aging age (days)** for the aging-bucket distribution:
  `age = (closed_at if closed else as_of) - created_at`, in whole days.
  Buckets: `0-3`, `4-7`, `8-14`, `15-30`, `31+`. Every **primary** item lands
  in exactly one bucket (the aging distribution covers all primary items, not
  just overdue ones).
- **breach_rate / sla_breach_rate** = overdue-primary-count ÷ primary-count,
  rounded to **3 decimals**.
- **overdue_counts_by_severity** counts only the **overdue** items by their
  `severity` (S1..S4).
- **Escalation order** = overdue primary sorted by: severity most-severe first
  (S1 < S2 < S3 < S4), then `due_at` ascending (earliest first), then `id`
  ascending as a final tiebreak.
- **Missing owner** = primary included items whose `owner` is null/empty.
- **Team overdue counts** = overdue primary grouped by `team` (teams listed
  alphabetically).
- **Top hotspot** = the `(team, owner)` pair with the most overdue primary
  items; a null owner is reported as `UNASSIGNED`.

### SLA primary population
Items that are (a) in the scope teams, (b) classify into a scope category
(usually Security/Reliability), (c) **not** duplicates or cancelled, and (d)
either still open or closed inside the recent-closed window. Duplicates that
otherwise match scope are reported as `duplicate_clusters` (keyed by their
`duplicate_of` primary) but never counted as primary.

## 6. Portfolio-mix rules

**Included primary items** for a mix review:
- `team` in scope teams AND `product_area` in scope product area(s),
- `closed_at` inside the quarter window,
- `status` is a completed status (§2),
- not a duplicate and not cancelled.
Order the id list by `closed_at` ascending, then `id` ascending.

**Target mix** comes from the `mix_targets` row whose `scope_id` equals the
scope_id named in the task (match that exact key), not the composite
`quarter:group:area` key. Fields `new_feature_pct`,
`tech_debt_pct`, `reliability_pct`, `security_pct` are fractions → multiply by
100 for percentage points.

**Actual mix** = category count ÷ total included × 100, one decimal.
**Gap** = `actual_pct - target_pct`, one decimal. Negative gap = under-invested.
`under_invested`/`largest_deficit` = categories with negative gap, most-negative
first.

**Action:**
- If there is ≥1 negative gap → `REBALANCE_CAPACITY`; primary category = the
  most-negative gap, secondary = next most-negative; rationale
  `LARGEST_NEGATIVE_GAP`.
- If no negative gaps → `MAINTAIN_CURRENT_MIX`, categories null, rationale
  `NO_NEGATIVE_GAPS`.
- If the data is internally contradictory → `INVESTIGATE_DATA_QUALITY`,
  rationale `DATA_CONFLICT`.
- `owner_team` (when the template asks for one) = the in-scope team that closed
  the most items in the deficit category; tie-break by most in-scope closed
  items overall, then alphabetical.

**Exclusion reporting:** among records that match the scope (team+area+quarter)
but were disqualified, report duplicate ids (`duplicate_of` set or
`status=Duplicate`), cancelled ids (`status=Cancelled`), and any "distractor"
ids as the template requests. Set `ignored_mirror_status_and_legacy_category`
to `true` when present.

## 7. Release-readiness rules

Scope = work items with `release_id == <release>`. Drop duplicates before
counting (they are not primary).

- **Milestone completion** per `milestone_id`: `primary_total` = primary items
  in that milestone; `complete_primary` = those with a completed status (§2);
  `completion_pct = complete/total*100` (1 dp). Sort by `milestone_id` asc.
- **readiness_score** = total complete primary ÷ total primary across the
  release (3 dp).
- **Unresolved high-impact blockers** = blockers with `resolved_at == null` AND
  `severity in (High, Critical)`. `blocker_cause_counts` = counts keyed by the
  exact `cause` string. Low/Medium or resolved blockers are excluded.
- **gating_work_item_ids** = the **non-complete** release primary items that are
  the `work_item_id` of an unresolved high-impact blocker, or the head of a
  critical dependency chain. A non-complete item with no such blocker/chain does
  **not** gate. Sorted unique ascending. (A high-impact blocker on an
  already-complete item does not gate.)
- **critical_dependency_chains** = for each gated/blocked non-complete release
  item, follow `dependencies` (`depends_on_id`, especially relation
  `blocks-release-readiness`) to a terminal dependency that is itself
  non-complete; emit the ordered id path `[start, ..., dependency]`. Include
  only chains whose terminal dependency is non-complete (if the dependency is
  already complete there is no chain). Sort lexicographically by the full path.
  This list is often empty.
- **ship_decision**:
  - `NO_SHIP` if there is any gating work item, any unresolved **Critical**
    blocker, or any critical dependency chain.
  - `SHIP` if `readiness_score == 1.0`, no unresolved high-impact blockers, and
    no gating items or critical chains.
  - `SHIP_WITH_WATCH` otherwise (incomplete work or low/medium blockers, but
    nothing gating).
