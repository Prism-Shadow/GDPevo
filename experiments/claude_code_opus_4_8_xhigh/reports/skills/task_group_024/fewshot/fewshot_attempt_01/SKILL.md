---
name: portfolio-mix-sla-release-analysis
description: >-
  Answer engineering-portfolio review tasks that run against the shared
  read-only work-item API (endpoints + query token in environment_access.md).
  Covers three task families that share one data model: (A) quarterly
  portfolio-mix vs target, (B) reliability/security SLA aging & breach, and
  (C) release-readiness rollups. Use when a task asks for closed-work category
  mix, SLA overdue/aging/escalation, or a ship decision, and provides an
  answer_template.json to fill.
---

# Portfolio mix / SLA aging / release readiness

These tasks all read one environment (work items + related tables) and return a
single JSON object matching the task's `input/payloads/answer_template.json`.
The wording, scope, and exact field names change per task, but the underlying
data model and business conventions are constant. Learn the conventions below,
compute the primitives (the helper script does this), then map them into the
exact template the task ships.

## Workflow

1. **Read the task prompt and `answer_template.json` first.** The template is
   authoritative for field names, enums, ordering, rounding, and `const`
   values. Different tasks in the same family use different field names (e.g.
   one mix task nests everything under `scope` with `gap_table`; another uses
   flat keys with a `mix_table` that includes per-row `count`). Never invent
   fields; never copy values from any example — recompute from the live API.
2. **Get access from `environment_access.md`** (do not hard-code): `Base URL`
   and the `X-Env-Token` (needed only for `POST /api/query`). Endpoints:
   `GET /api/work-items[/{id}]`, `/api/mix-targets`, `/api/sla-policy`,
   `/api/releases[/{id}]`, `/api/milestones`, `/api/dependencies`,
   `/api/blockers`, and `POST /api/query` (restricted read-only SQL over the
   same tables, `X-Env-Token` header required).
3. **Identify the family** from the ask: category *mix vs target* → A;
   *SLA / overdue / breach / aging / escalation* → B; *ship decision /
   milestones / blockers / dependencies* → C.
4. **Compute** with `scripts/portfolio_analysis.py` (it applies every
   convention below and prints the primitives as JSON), or replicate its logic.
5. **Assemble** the answer strictly per the template, apply the required
   ordering/rounding, and emit **JSON only — no prose**.

```
python scripts/portfolio_analysis.py mix     --scope-id <id> --quarter 2025-Q4 \
       --teams "<T1,T2>" --product-areas "<PA1,PA2>"
python scripts/portfolio_analysis.py sla     --teams "<T1,T2>" \
       --categories "Security,Reliability" --as-of <YYYY-MM-DD> --window <days>
python scripts/portfolio_analysis.py release --release-id <REL-ID>
```

## Work-item data model & shared conventions

Each work item has: `id`, `team`, `product_area`, `work_type`, `labels[]`,
`title`, `status`, `severity` (S1–S4), `owner` (may be null), `priority`,
`created_at`, `due_at`, `closed_at`, `milestone_id`, `release_id`,
`duplicate_of`, plus **`mirror_status`** and **`legacy_category`**.

- **Stale/export fields are never authoritative.** Ignore `mirror_status` and
  `legacy_category` entirely, and treat a `stale-export` label as noise. Use
  only real fields (`status`, `work_type`, `labels`, `title`, `due_at`, …).
  Mix answers often surface this via an `ignored_mirror_status_and_legacy_category: true` flag.
- **Completed / terminal statuses** = `Closed`, `Verified`, `Done`,
  `Deployed`. Anything else that is not an explicit exclusion is **open**.
  (`In Progress`, `Backlog`, `Review`, `Reopened` are open.)
- **Exclusions:** a record is a **duplicate** if `status == "Duplicate"` **or**
  `duplicate_of` is non-null (report it, and its `duplicate_of` target is the
  cluster's `primary_id`); a record is **cancelled** if `status == "Cancelled"`.
  Duplicates and cancelled records are never primary/counted work.

### Portfolio category classification (the core convention)

Every item maps to exactly one of `NewFeature`, `TechDebt`, `Reliability`,
`Security`. Read signals from `work_type`, `labels`, and `title` only, and
resolve conflicts by **risk-first precedence**:

> **Security > Reliability > TechDebt > NewFeature**

Assign the highest-precedence category for which *any* signal matches:

| Category | `work_type` | label / title keywords |
|---|---|---|
| **Security** | Security, Compliance | security, cve, encryption, auth, compliance |
| **Reliability** | Reliability, Incident | reliability, incident, outage, latency, flaky |
| **TechDebt** | Refactor, Chore, Dependency | cleanup, refactor, migration, dependency, debt |
| **NewFeature** | Feature, Enhancement | feature, rollout, customer-request |

A `work_type: Bug` with no other signal → **Reliability**; if nothing matches
at all → **NewFeature**. This precedence is why, e.g., a `Feature`-typed item
carrying a `security`/`auth` label classifies as **Security**, and a feature
whose title says "cleanup …" classifies as **TechDebt** — signals in labels and
title override a benign `work_type`.

## Family A — quarterly portfolio mix vs target

**Scope filter:** `team ∈ task.teams` **AND** `product_area ∈ task.product_areas`
(both are sets; a team may appear under any listed product area). **Quarter**
is the quarter of `closed_at` (this is *closed* work). Drop items not closed in
the target quarter.

**Include** = in scope, closed in quarter, completed status, not duplicate, not
cancelled. Order included ids by `closed_at` asc, then `id` asc. Report the
excluded duplicates and cancelled separately (some templates merge them into a
single `excluded_distractor_ids` list, still ordered by `closed_at` then `id`).

**Mix vs target:** `category_counts` are **item counts** (not story points).
`actual_pct = count / total_included * 100`, rounded to 1 dp. Target comes from
the `mix_targets` row whose `scope_id` equals the task's target scope id; its
fractions (`new_feature_pct`, `tech_debt_pct`, `reliability_pct`,
`security_pct`) are ×100 → percentage points (1 dp). `gap_pct = actual_pct −
target_pct` (1 dp). Rows/keys always in order NewFeature, TechDebt,
Reliability, Security.

**Under-invested** = categories with negative gap, ordered most-negative first.
**Recommendation:** if any negative gap → `REBALANCE_CAPACITY` targeting the
largest-deficit category (rationale `LARGEST_NEGATIVE_GAP`; a secondary slot, if
present, is the next-most-negative). If no negative gaps → `MAINTAIN_CURRENT_MIX`
/ `NO_NEGATIVE_GAPS`; use `INVESTIGATE_DATA_QUALITY` / `DATA_CONFLICT` only when
the data genuinely conflicts. When a template needs an `owner_team`, pick the
in-scope team most associated with the deficit category (most included items in
it; break ties toward the team with the smaller current share, then
alphabetical) — verify against the data.

## Family B — reliability/security SLA aging

**Population (primary):** `team ∈ task.teams` **AND** `classify(item) ∈
task.categories` (usually Security & Reliability), not cancelled, not duplicate,
**created on/before `as_of`**, and either **open** or **closed within the recent
window** (`0 ≤ as_of − closed_at ≤ window_days`). Items created after `as_of`
don't exist yet at the snapshot — exclude them. Duplicates are pulled out into
`duplicate_clusters` (`primary_id` = their `duplicate_of`).

**Overdue** (uses the item's own `due_at`):
- open item → overdue iff `as_of > due_at` (strictly; equal is *not* overdue);
- closed item → overdue iff `closed_at > due_at` (closed after its due date).

`sla_policy` maps severity → `days_to_due` (S1=3, S2=10, S3=21, S4=45); the
per-item `due_at` already encodes this, so compare against `due_at` directly.

**Aging** = age in days from `created_at` to the reference date (`closed_at`
for closed-as-of items, else `as_of`), bucketed inclusively:
`0-3`, `4-7`, `8-14`, `15-30`, `31+`.

**Other outputs:** `overdue_counts_by_severity` over overdue items;
`team_overdue_counts` per scope team (teams alphabetical); `top_hotspot` = the
(team, owner) pair with the most overdue items, `owner = "UNASSIGNED"` when
null; `missing_owner_ids` = primary items with no owner; `breach_rate =
overdue / included`, rounded to **3 dp**. **Escalation order** = severity
ascending (S1 first), then `due_at` ascending, then `id`. Plain id lists are
sorted lexicographically; duplicate clusters sorted by `primary_id` with
`duplicate_ids` sorted.

## Family C — release readiness

Use authoritative fields only (not mirror fields). "Release work items" =
items with `release_id == target release`.

- **`milestone_completion`** (sorted by `milestone_id`): for each milestone of
  the release, `primary_total` = primary items (exclude duplicate/cancelled)
  with that `milestone_id`; `complete_primary` = those in a completed status;
  `completion_pct = complete/total*100` (1 dp).
- **`readiness_score`** = Σ complete_primary / Σ primary_total across the
  release's milestones, rounded to **3 dp**.
- **`blocker_cause_counts`**: count only **unresolved** (`resolved_at` is null)
  **high-impact** (`severity ∈ {Critical, High}`) blockers on the release,
  keyed by the exact `cause` string.
- **`gating_work_item_ids`**: release work items that are non-complete **and**
  are the `work_item_id` of an unresolved high-impact blocker (a completed item
  with a blocker does not gate). Sorted unique.
- **`critical_dependency_chains`**: starting from each gating item, follow
  `dependencies` edges (`blocked_id → depends_on_id`) and emit the ordered id
  path to any **non-complete** dependency reached (paths sorted
  lexicographically). Empty when every dependency of the gating items is
  complete.
- **`ship_decision`**: `NO_SHIP` if there are any gating items, unresolved
  high-impact blockers, or critical dependency chains; else `SHIP` when
  readiness is complete (score ≥ 1.0); otherwise `SHIP_WITH_WATCH`.

## Output discipline

- Emit only the JSON object the template defines — no surrounding prose,
  markdown, or comments.
- Honor every `const`/`enum`, `minItems`/`maxItems`, id `pattern`, key order,
  sort order, and decimal precision in the template.
- Recompute all values from the live environment for the task's own scope;
  do not carry over numbers or ids from any example.

`scripts/portfolio_analysis.py` implements all of the above; its output is a
superset of primitives you slot into whichever template the task provides.
