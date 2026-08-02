---
name: portfolio-environment-analysis
description: >-
  Answer engineering-portfolio review tasks that query a shared read-only work-items
  API/SQL environment and must return one strict JSON object matching a supplied
  answer_template.json. Covers the recurring task families: portfolio-mix reviews
  (count-based category mix vs. a target, gaps, rebalance), SLA-aging audits (primary
  vs. duplicate work, overdue/aging buckets, breach rate, hotspots), and release-readiness
  assessments (milestone completion, gating items, blockers, dependency chains, ship
  decision). Use whenever a task references work items, mix targets, SLA policy, releases,
  milestones, blockers, or dependencies, an X-Env-Token query token, and stale "mirror"
  or "legacy" fields to ignore.
---

# Portfolio Environment Analysis

A single shared environment (a small REST API backed by a read-only SQLite DB) holds an
engineering portfolio: work items plus mix targets, SLA policy, releases, milestones,
dependencies, and blockers. Tasks ask you to compute one deterministic **JSON answer**
about that data and return **nothing but the JSON**.

The scope, quarter, teams, dates, and answer shape change per task, but the data model and
the analysis rules below are stable. Treat this file as the operating manual; read the
`references/` files for the exhaustive field/enum tables and per-family recipes.

## 0. Golden rules (do these on every task)

1. **Read the task's own `answer_template.json`** (each task ships it at
   `input/payloads/answer_template.json`). It is the contract: keys, enums, `const`
   values, `additionalProperties:false`, ordering hints, and rounding all come from it.
   When this manual and the template disagree, the template wins.
2. **Get access from `environment_access.md`, not from memory.** It gives the base URL
   (prompts show it as `<TASK_ENV_BASE_URL>`), the endpoint list, and the query token.
   Use the network *only* as that file allows.
3. **Trust authoritative fields; discard stale/legacy ones.** `status` is truth;
   `mirror_status` is a stale mirror — ignore it. `legacy_category` is a stale export
   field — never categorize from it. `stale-export` / `papertrail` labels mark
   export-noise records.
4. **Separate primary work from noise before counting.** Exclude duplicates and cancelled
   records (and task-named "distractors") from the primary population; report them where
   the template asks.
5. **Compute with full precision; round only at output.** Verify every count two ways
   (SQL aggregate + a re-count in code). Percentages sum to ~100.
6. **Emit exactly one JSON object, no prose, no markdown fences.** Include precisely the
   template's required keys (no extras — schemas use `additionalProperties:false`).

## 1. Environment access

- Base URL: from `environment_access.md`. Read endpoints with `GET`. For anything needing
  filtering/joins/aggregation, use `POST /api/query` with header
  `X-Env-Token: <token from environment_access.md>` and body `{"sql":"<read-only SELECT>"}`.
- The query endpoint runs SQL over these tables (names are the API resources):
  `work_items, mix_targets, sla_policy, releases, milestones, dependencies, blockers`.
  It returns `{"columns":[...],"rows":[[...]],"row_count":N,"truncated":bool}`.
- SQL is convenient but the hygiene/classification rules below are *not* encoded in the DB —
  you must apply them yourself. A pragmatic pattern: pull the candidate rows with SQL, then
  classify/filter/aggregate in a script so the logic is auditable.
- A ready helper is in `scripts/query.py` (reads base URL + token from an
  `environment_access.md` you point it at). It is optional; plain `curl`/`requests` are fine.

## 2. Record hygiene — authoritative vs. stale/distractor

`work_items` fields and how to treat them (full table in `references/data-model.md`):

- **`status`** — authoritative lifecycle state. Completed/closed = `{Closed, Done, Verified,
  Deployed}` (these carry a `closed_at`). Open/non-complete = `{Backlog, In Progress, Review,
  Reopened}` (`closed_at` is null). Excluded = `{Duplicate, Cancelled}`.
- **`mirror_status`** — STALE mirror of status. Ignore entirely.
- **`legacy_category`** — STALE legacy/export category. Ignore for classification.
- **`duplicate_of`** — if non-null, the record duplicates / points at another item. A record
  is a **duplicate** when `status == "Duplicate"` OR `duplicate_of` is non-null; its canonical
  target is `duplicate_of`. Exclude from primary; report in duplicate clusters when asked.
- **`status == "Cancelled"`** — excluded as cancelled.
- **`labels`** — supporting signal; `stale-export` and `papertrail` flag export noise /
  distractor records.
- **`owner`** — may be null → render as `UNASSIGNED` (or list under missing-owner ids) per
  the template.
- **`id`** — `WI-24024-<optional single UPPERCASE letter><3 digits>`; plain, `P…`, and `S…`
  variants all exist and are all valid ids. Never include/exclude by prefix — filter on
  fields. (The `P`/`S` pools are where most duplicates/distractors live, but confirm by field.)

**Primary population** = records that are neither duplicates nor cancelled. Layer the
task-specific filters (scope, quarter, category, release, window) on top of that.

## 3. Portfolio category classification

Four categories, each item lands in **exactly one**: `NewFeature, TechDebt, Reliability,
Security`. The authoritative signal is **`work_type`**:

| work_type              | category    |
|------------------------|-------------|
| Feature, Enhancement   | NewFeature  |
| Refactor, Chore, Dependency | TechDebt |
| Reliability, Incident, Bug  | Reliability |
| Security, Compliance   | Security    |

"Resolve conflicting **type, label, and title** signals" means: **`work_type` wins.**
`labels`/`title` only corroborate; `legacy_category` is ignored. This map is total for the
observed `work_type` values.

Fallback only if `work_type` is missing/unmapped: pick the highest-priority category that has
a matching `labels`/`title` keyword, priority **Security > Reliability > TechDebt >
NewFeature**; if none match, default `NewFeature`. Keyword sets are in
`references/classification.md`.

## 4. Scope resolution

- **Quarter** is derived from `closed_at` (e.g. `2025-Q4` = 2025-10-01…2025-12-31), unless the
  template says otherwise.
- **Portfolio-mix in-scope item** = `team ∈ scope.teams` AND `product_area ∈
  scope.product_areas` AND closed in the target quarter AND **primary** AND **completed**.
- **Target mix** = the `mix_targets` row whose `scope_id` equals the task's scope id. **Fetch
  it at runtime — never hardcode target percentages.** Its `*_pct` values are fractions in
  0–1; multiply by 100 for percentage points.
- **SLA-aging in-scope item** = **primary** item whose `team ∈ scope.teams` and whose category
  (per §3) ∈ `scope.categories`, evaluated at the given `as_of` date within the stated recent
  closed window.
- **Release in-scope item** = work item with `release_id == <release>` (and/or a `milestone_id`
  belonging to that release).

## 5. Metric formulas

Percentages are **percentage points rounded to 1 decimal**; rates/scores rounded to **3
decimals**. Compute with full precision, round last.

- `actual_pct(cat) = 100 * count(cat) / total_included`
- `target_pct(cat) = 100 * mix_targets_fraction(cat)`
- `gap_pct(cat) = actual_pct - target_pct`; **under-invested** = `gap_pct < 0`, ordered most
  negative → least negative.
- Follow-up / recommended action: if any negative gap → action `REBALANCE_CAPACITY`, primary
  category = largest negative gap (rationale `LARGEST_NEGATIVE_GAP`); if no negative gaps →
  `MAINTAIN_CURRENT_MIX` / `NO_NEGATIVE_GAPS`; genuine data conflict →
  `INVESTIGATE_DATA_QUALITY` / `DATA_CONFLICT`. Use the exact enum values the template lists.
- **SLA:** the due date is the authoritative `due_at` field (do **not** recompute it from
  `sla_policy`; `sla_policy` gives `days_to_due` per severity for reference only). An overdue
  primary item is a primary SLA item still unresolved as of the date with `due_at` before the
  as-of date. `breach_rate = overdue_primary_count / included_primary_count` (3 decimals).
  Aging days = `as_of − due_at` (bucket per the template's boundaries). Hotspot = the
  `(team, owner|UNASSIGNED)` pair with the most overdue primary items.
- **Release readiness:** for each milestone, `primary_total` = primary release items with that
  `milestone_id`, `complete_primary` = those in a completed state, `completion_pct` (1 dec).
  `readiness_score` = total complete primary / total primary denominator (3 dec).
  `gating_work_item_ids` = non-complete primary release items. `blocker_cause_counts` = count
  of **unresolved** (`resolved_at` is null) **high-impact** (`severity ∈ {High, Critical}`)
  blockers for the release, keyed by exact `cause` string. `critical_dependency_chains` =
  ordered `blocked_id → … → depends_on_id` paths (from `dependencies`) ending at a non-complete
  dependency. `ship_decision` ∈ `{SHIP, SHIP_WITH_WATCH, NO_SHIP}` from readiness + unresolved
  high-impact blockers + gating items — honor any thresholds the task states; otherwise use the
  default heuristic in `references/task-recipes.md`.

## 6. Ordering, precision, and output

- **Always obey the template's stated order.** It varies: some fields are "sort alphabetically"
  / "lexicographically ascending", others fix an explicit order (e.g. a specific team ordering).
  Common defaults: id lists lexicographic ascending; included mix ids by `closed_at` asc then
  `id` asc; duplicate clusters sorted by `primary_id` with `duplicate_ids` lexicographic.
- Respect every `const`/`enum` exactly (e.g. a flag like
  `ignored_mirror_status_and_legacy_category` is `const:true` — set it true, having actually
  ignored those fields).
- **Self-check before emitting:** category percentages sum to ≈100; every included id is
  unique and matches the id pattern; excluded ids don't appear in included lists; counts
  reconcile between SQL and code; JSON has exactly the required keys and validates against the
  template.
- Print **only** the JSON object.

## Task families at a glance

- **Portfolio mix** (count-based category mix vs. target, gaps, rebalance, exclusion flags).
- **SLA aging** (primary vs. duplicate clusters, overdue/aging buckets, breach rate, hotspots,
  missing owners, escalation/priority ordering).
- **Release readiness** (milestone completion, gating ids, blocker cause counts, dependency
  chains, readiness score, ship decision).

Step-by-step recipes for each are in `references/task-recipes.md`.
