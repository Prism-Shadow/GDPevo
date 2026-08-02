---
name: portfolio-env-review
description: >-
  Answer portfolio-analytics tasks against the shared portfolio environment
  (work items, mix targets, SLA policy, releases, milestones, dependencies,
  blockers, and a restricted SQL query endpoint described in
  environment_access.md). Use for: quarterly portfolio-mix / investment-mix
  reviews against a target mix; SLA aging / breach / escalation audits; and
  release-readiness (ship decision) assessments. Handles the environment's
  authoritative-vs-stale field conventions, category classification, duplicate
  and cancelled exclusion, date windows, and produces a single JSON object that
  matches the task's answer_template.json.
---

# Portfolio environment review

Use this skill for any task that points at the shared portfolio environment
(its access notes live in `environment_access.md`) and asks for a JSON answer
built from work items, mix targets, SLA data, releases, milestones,
dependencies, or blockers. Three task families are covered:

- **A. Portfolio-mix review** — classify in-scope closed work into four
  investment categories and compare the actual mix to a target mix.
- **B. SLA-aging audit** — find the SLA population, overdue items, aging /
  severity distribution, hotspots, duplicates, and the breach rate.
- **C. Release readiness** — ship decision, milestone completion, gating work
  items, unresolved high-impact blockers, dependency chains, readiness score.

Identify the family from the task prompt and, decisively, from the
`answer_template.json` the task hands you — the template's keys tell you exactly
which recipe to run and what to emit.

## 0. Workflow

1. Read the task `prompt.txt` and its `payloads/answer_template.json` (some
   tasks reference it as `input/payloads/answer_template.json`). The template is
   the contract: match its structure, keys, enums, ordering, and rounding
   exactly, and output **only** JSON — no prose.
2. Read `environment_access.md` for the base URL, the allowed endpoints, and the
   `X-Env-Token` needed for `POST /api/query`.
3. Pull the data you need (see below), apply the **universal conventions**
   (§2), then the recipe for the family (§3).
4. Fill the template, self-check against §4, emit the JSON.

## 1. Reaching the environment

Endpoints (all `GET` unless noted):
`/api/work-items`, `/api/work-items/{id}`, `/api/mix-targets`,
`/api/sla-policy`, `/api/releases`, `/api/releases/{id}`, `/api/milestones`,
`/api/dependencies`, `/api/blockers`, and `POST /api/query` (SQL over the same
tables — send `{"sql": "..."}` with header `X-Env-Token: <token>`).

`POST /api/query` is the most efficient way to filter the ~239 work items. The
SQL tables are `work_items, mix_targets, sla_policy, releases, milestones,
dependencies, blockers`; `work_items.labels` is stored as JSON-array text.

A helper that parses `environment_access.md` and calls the API is provided:

```
python3 scripts/portfolio_api.py --access <path/to/environment_access.md> get /api/work-items
python3 scripts/portfolio_api.py --access <path/to/environment_access.md> sql "SELECT id,status,team FROM work_items WHERE release_id='...'"
```

You may also just `curl` the endpoints directly with the token header.

## 2. Universal conventions (apply to every family)

These are the crux of the environment and are detailed in
`references/conventions.md`. Summary:

- **Authoritative vs stale.** Trust `status`, `work_type`, `labels`, `title`,
  `team`, `product_area`, `owner`, `created_at`, `due_at`, `closed_at`,
  `severity`, `duplicate_of`, `release_id`, `milestone_id`. **Never** use
  `mirror_status` or `legacy_category` as truth — they are deliberately stale.
  Words like *stale/mirror/export/legacy* in titles/labels are decoys.
- **Completed statuses** = `Closed, Done, Deployed, Verified`.
  **Open/not-complete** = `Backlog, In Progress, Review, Reopened`.
  **Excluded** = `Cancelled`, and any duplicate.
- **Duplicate** = `status == 'Duplicate'` OR `duplicate_of` is non-null (test
  both — a "Closed" record can still be a duplicate). Its primary id is
  `duplicate_of`.
- **Category classification** (`NewFeature | TechDebt | Reliability | Security`):
  gather signals from `work_type` + `labels` + `title`, then take the
  **highest-precedence** category present:
  `Security > Reliability > TechDebt > NewFeature` (NewFeature is the default).
  This is how conflicting type/label/title signals are resolved. See the signal
  dictionary in `references/conventions.md` §3.
- **Quarter window** `YYYY-Qn` applies to `closed_at` (Q4 = Oct1–Dec31, etc.).
- **Recent-closed window of N days** relative to `as_of` filters **closed**
  items to `as_of - N days <= closed_at <= as_of`; **open** items are always
  included regardless of age.
- **Target mix** = the `mix_targets` row whose `scope_id` equals the scope_id
  named by the task, not the composite `quarter:group:area` key. Its `*_pct`
  values are fractions; ×100 for percentage points.

## 3. Recipes

### A. Portfolio-mix review
1. Include work items where team ∈ scope teams, product_area ∈ scope areas,
   `closed_at` in the quarter, `status` completed, not duplicate, not cancelled.
   Order ids by `closed_at` asc then `id` asc.
2. Classify each included item (§2 precedence) → `category_counts`.
3. `actual_pct` = count/total×100 (1 dp). Look up the target row by scope_id →
   `target_pct` (1 dp). `gap_pct = actual_pct - target_pct` (1 dp).
4. Under-invested / largest-deficit = negative gaps, most-negative first.
5. Action: negative gaps → `REBALANCE_CAPACITY` (primary = largest deficit,
   secondary = next, rationale `LARGEST_NEGATIVE_GAP`); none →
   `MAINTAIN_CURRENT_MIX` / `NO_NEGATIVE_GAPS`; contradictory data →
   `INVESTIGATE_DATA_QUALITY` / `DATA_CONFLICT`. If an `owner_team` is required,
   pick the in-scope team that closed the most items in the deficit category.
6. Exclusion flags: among records matching the scope but disqualified, list
   duplicate ids and cancelled/distractor ids as the template asks; set
   `ignored_mirror_status_and_legacy_category` = true when present.

### B. SLA-aging audit
1. Primary population = scope teams, scope categories (§2 classification),
   not duplicate/cancelled, and (open OR closed within the recent window).
   Sort id lists lexicographically.
2. Overdue: open → `due_at < as_of` (strict); closed → `closed_at > due_at`.
3. Emit whichever the template requires: `aging_bucket_counts` over **all**
   primary (age = (closed_at or as_of) − created_at → 0-3/4-7/8-14/15-30/31+);
   `overdue_counts_by_severity` over **overdue** items; `team_overdue_counts`
   (alphabetical); `top_hotspot` = busiest (team, owner) overdue pair, null
   owner → `UNASSIGNED`; `missing_owner_ids`; `escalation_queue_ids` = overdue
   sorted by severity (S1 first) then `due_at` asc then id.
4. `duplicate_clusters` = in-scope duplicates keyed by their `duplicate_of`
   primary, duplicate_ids sorted; clusters sorted by primary_id.
5. `breach_rate`/`sla_breach_rate` = overdue ÷ primary, **3 dp**.

### C. Release readiness
1. Scope = `release_id == <release>`; drop duplicates before counting.
2. Milestone completion per `milestone_id`: complete (completed status) /
   primary_total; `completion_pct` 1 dp; sort by milestone_id asc.
   `readiness_score` = total complete ÷ total primary, **3 dp**.
3. `blocker_cause_counts` = unresolved (`resolved_at` null) **High/Critical**
   blockers, counted by exact `cause`.
4. `gating_work_item_ids` = non-complete release items that are the subject of an
   unresolved high-impact blocker or the head of a critical dependency chain
   (sorted unique asc). Non-complete items without such a blocker/chain do not
   gate; blockers on already-complete items do not gate.
5. `critical_dependency_chains` = ordered id paths from a blocked non-complete
   release item along `depends_on` edges (esp. relation
   `blocks-release-readiness`) to a terminal dependency that is **itself
   non-complete**; sort lexicographically by full path (often empty).
6. `ship_decision`: `NO_SHIP` if any gating item, any unresolved Critical
   blocker, or any critical chain; `SHIP` if readiness = 1.0 with no high-impact
   blockers/gating/chains; else `SHIP_WITH_WATCH`.

## 4. Before returning

- Output is exactly one JSON object matching the template — correct keys, enum
  values, list ordering, and rounding (1 dp for percentages/gaps, 3 dp for
  rates/readiness). No text outside the JSON.
- Re-echo scope fields (teams, product areas, as_of, categories) in the order
  the template's descriptions specify (some alphabetical, some fixed).
- Percentages are **item counts**, not story points.
- Confirm you excluded every cancelled record and every duplicate
  (`duplicate_of` set OR status Duplicate), and used `status` — never
  `mirror_status`/`legacy_category`.
- Cross-check derived counts (e.g. category counts sum to total included;
  aging buckets sum to primary count; overdue ⊆ primary).
