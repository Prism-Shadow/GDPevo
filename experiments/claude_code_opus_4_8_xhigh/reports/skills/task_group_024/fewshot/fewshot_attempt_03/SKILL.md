---
name: portfolio-env-analysis
description: >-
  Answer read-only analysis questions against the shared engineering-portfolio
  environment (work items, mix targets, SLA policy, releases, milestones,
  blockers, dependencies). Covers three task families — portfolio-mix reviews,
  SLA aging/breach reviews, and release-readiness assessments — each returning a
  single JSON object that must match the task's own answer_template.json. Use
  whenever a task points at that environment and asks for a portfolio mix vs a
  target, an SLA/overdue/escalation readout, or a ship decision.
---

# Portfolio environment analysis

One environment backs every task. Each task gives you a **scope** (in its
`prompt.txt`) and an exact **output shape** (in its `payloads/answer_template.json`).
Your job: pull the data over HTTP, apply the shared rules below, and emit a single
JSON object matching that template. Output JSON only — no prose.

`reference.md` holds the full data model and decision tables.
`portfolio_toolkit.py` implements every rule; prefer it over re-deriving the math.

## Workflow

1. **Read the task**, not your memory of past tasks. From the task `prompt.txt`
   extract the scope parameters (scope_id, quarter, teams, product areas,
   categories, as-of date, recent-window days, release id — whichever apply).
   From `payloads/answer_template.json` extract the exact keys, ordering rules,
   rounding, and enum values the answer must use. Different tasks in the same
   family use different key names and different subsets of fields — follow the
   template in front of you.
2. **Get access**: read `environment_access.md` for the Base URL and
   `X-Env-Token`. GET endpoints are open; only `POST /api/query` needs the token.
3. **Fetch** the collections you need (usually just `GET /api/work-items` plus
   one or two others). `portfolio_toolkit.fetch_all()` grabs them all.
4. **Classify & filter** using the shared conventions (below).
5. **Compute** with the matching task-family entry point.
6. **Format** the result into the template's exact keys, order, and rounding.
   Copy nothing from any example answer — every value is derived from the live
   data for the scope you were given.

Fast path:

```python
import portfolio_toolkit as pt
data = pt.fetch_all()                 # reads ./environment_access.md
res  = pt.portfolio_mix(data, scope_id=SCOPE, teams=TEAMS,
                        product_areas=AREAS, quarter=QUARTER)
# map res -> the keys/order this task's answer_template.json requires
```

## Shared conventions (apply to every family)

- **Authoritative fields only.** Use `status`, `work_type`, `labels`, `title`,
  `team`, `product_area`, `owner`, `severity`, `created_at`, `closed_at`,
  `due_at`, `duplicate_of`, `release_id`, `milestone_id`. **Never** trust
  `mirror_status` or `legacy_category` — they are stale mirror/export fields kept
  to mislead. (The portfolio template's `ignored_mirror_status_and_legacy_category`
  flag is always `true`.)
- **Complete/done** = `status ∈ {Closed, Done, Deployed, Verified}`. Everything
  else (`Backlog`, `In Progress`, `Review`, `Reopened`) is not complete.
- **Duplicate** = `status == "Duplicate"` **or** `duplicate_of` set → excluded
  from primary work; `duplicate_of` names its canonical id.
- **Cancelled** = `status == "Cancelled"` → excluded from primary work.
- **Category classification**: gather category signals from `work_type` + `labels`
  + `title`, keep the highest-precedence one, precedence
  `Security > Reliability > TechDebt > NewFeature` (NewFeature = fallback). Full
  work_type map and keyword lists are in `reference.md` / `classify()`.

## Family A — portfolio-mix review

Scope: `scope_id`, `quarter`, `teams`, `product_area(s)`. Target mix = the
`mix_targets` row whose `scope_id` equals the task's scope_id (percentages are
stored as fractions 0–1 → ×100).

- **In scope** = team in scope, product_area in scope, `closed_at` inside the
  quarter (Q4 = Oct 1–Dec 31, etc.).
- Split in-scope records: duplicates and cancelled are **excluded** and reported
  (as `excluded_duplicate_ids` / `excluded_cancelled_ids`, or combined as
  `excluded_distractor_ids` — whichever the template names). Remaining records
  with a done status are the **included mix**.
- Classify each included item; counts are **item counts, not story points**.
- `actual_pct = count / total_included × 100` (1 dp); `gap_pct = actual − target`
  (1 dp). **Under-invested / deficit** = categories with negative gap, ordered
  most-negative first. **largest_deficit_category** = the most-negative gap.
- Follow-up / recommendation:
  - Any negative gaps → `REBALANCE_CAPACITY`, primary = largest negative gap,
    secondary = next negative (or null), rationale `LARGEST_NEGATIVE_GAP`.
  - No negative gaps → `MAINTAIN_CURRENT_MIX`, rationale `NO_NEGATIVE_GAPS`.
  - When a template wants `owner_team`, use the team owning the most included
    work in the deficit category (ties alphabetical).
- **Ordering**: `included_work_item_ids` (and excluded lists) by `closed_at`
  ascending then id ascending; category tables in the fixed order
  NewFeature, TechDebt, Reliability, Security; team/area lists per the template's
  stated order (some say alphabetical, some give an explicit order).

Entry point: `portfolio_mix(data, scope_id, teams, product_areas, quarter)` →
included ids, counts, percentages, per-category table, under-invested list,
deficit category, follow-up action, owner team, and the excluded id lists.

## Family B — SLA aging review

Scope: `teams`, `categories` (Reliability/Security), `as_of` date, recent closed
`window_days`.

- **Primary population** = team in scope, `classify() ∈ categories`, not
  cancelled, `created_at ≤ as_of`, and **either still open or closed within
  `[as_of − window_days, as_of]`**. Duplicates split off into
  `duplicate_clusters` keyed by their `duplicate_of`; the rest are primary.
- **Overdue**: closed → `closed_at > due_at`; open → `due_at < as_of` (strict).
- **Aging buckets** on age `= (closed_at or as_of) − created_at`:
  `0-3, 4-7, 8-14, 15-30, 31+` (inclusive), computed over all primary items.
- **breach_rate** = overdue primary ÷ primary, **3 decimals**.
- **team_overdue_counts** (teams alphabetical); **overdue_counts_by_severity**
  (S1–S4); **top_hotspot** = (team, owner) pair with most overdue, owner
  `UNASSIGNED` if missing; **missing_owner_ids** = primary with no owner.
- **escalation_queue_ids** = overdue primary in priority order: severity ascending
  (S1 first), then days-overdue `(closed_at or as_of) − due_at` descending, then
  id ascending.
- **Ordering**: id lists lexicographic unless a field defines its own order
  (escalation queue); clusters sorted by `primary_id`, `duplicate_ids` sorted.

Entry point: `sla_aging(data, teams, categories, as_of, window_days)` → primary
ids, overdue ids, aging buckets, team counts, severity counts, hotspot,
escalation queue, missing-owner ids, clusters, breach rate.

## Family C — release-readiness assessment

Scope: a `release_id`. Build only from authoritative status/blocker/dependency
data (ignore mirror fields).

- **milestone_completion** (sorted by `milestone_id` asc): per milestone, primary
  = release items with that milestone_id excluding duplicates/cancelled;
  `complete_primary` uses the done set; `completion_pct` 1 dp.
- **readiness_score** = total complete primary ÷ total primary across milestones,
  3 dp.
- **blocker_cause_counts**: unresolved high-impact blockers only
  (`severity ∈ {High, Critical}`, `resolved_at` null), keyed by exact `cause`.
- **gating_work_item_ids**: non-complete primary release items that have an
  unresolved high-impact blocker (sorted, unique).
- **critical_dependency_chains**: from each gating item follow `dependencies`
  edges to any non-complete dependency; each path
  `[gating_id, …, non_complete_dep_id]`; sort lexicographically. Empty when every
  gating item's dependencies are already complete.
- **ship_decision**: `NO_SHIP` if any gating items, critical chains, or unresolved
  Critical blocker; `SHIP` only when readiness is 1.0 with no unresolved
  high-impact blockers and nothing gating; else `SHIP_WITH_WATCH`.

Entry point: `release_readiness(data, release_id)` returns exactly these fields.

## Output discipline

- Emit **one JSON object** matching the task's `answer_template.json` — its keys,
  nesting, enums, ordering, and rounding. Nothing extra, no prose.
- Respect each template's rounding (mix/gaps 1 dp as percentage points; breach and
  readiness 3 dp) and its stated sort orders.
- Recompute everything from the live environment for the given scope. Do **not**
  copy ids, counts, percentages, or scope values from any example — they belong to
  other scopes and will be wrong here.
