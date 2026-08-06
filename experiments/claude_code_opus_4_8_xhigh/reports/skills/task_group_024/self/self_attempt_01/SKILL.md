---
name: portfolio-env-analysis
description: >-
  Answer analytics questions against the shared read-only "portfolio" HTTP
  environment (work items, mix targets, SLA policy, releases, milestones,
  blockers, dependencies) and return a single strict-JSON answer matching a
  provided answer_template.json. Use for the three recurring task families:
  (1) quarterly portfolio-mix reviews/readouts (category mix vs a mix_targets
  row), (2) SLA aging/breach audits for reliability & security work, and
  (3) release-readiness assessments. Triggers whenever a task references
  <TASK_ENV_BASE_URL> / environment_access.md plus /api/work-items and asks for
  category mix, SLA/overdue/breach, or ship-readiness, with a payloads/
  answer_template.json to conform to.
---

# Portfolio environment analysis

You are given a task prompt, an `environment_access.md` with the base URL/endpoints/token,
and an answer template at `payloads/answer_template.json` (prompts reference it as
`input/payloads/answer_template.json`). Query the shared environment, apply the operating
rules below, and emit **only** the JSON the template requires — no prose.

Read `references/data-model.md` first: it is the field-authority map, category
conventions, enum vocabularies, and distractor catalog that the rules below depend on.

## The one principle that runs through every task

The environment is seeded with **decoy fields and adversarial signals**. Winning means
using authoritative fields and ignoring the decoys, consistently:

- Completion/closure → **`status`**, never `mirror_status`.
- Portfolio category → **`work_type`**, never `legacy_category`; `labels`/`title` are
  noise that do not override the type.
- SLA deadline → **`due_at`**, not recomputed from `sla_policy`.
- Release truth → authoritative `status` / blocker / dependency records, not mirrors.
- Primary work excludes **duplicates** (`status='Duplicate'` OR `duplicate_of` set) and
  **cancelled** (`status='Cancelled'`); report them separately where asked, never count
  them as primary.

If two authoritative fields genuinely conflict in a way that changes the answer, that is a
*data conflict* — surface it through whatever the template provides (e.g. an
`INVESTIGATE_DATA_QUALITY` / `DATA_CONFLICT` path) rather than guessing.

## General workflow

1. **Read the environment access notes** → base URL, endpoint list, token. Substitute the
   real base URL for `<TASK_ENV_BASE_URL>`.
2. **Read the answer_template fully.** It is the contract: exact keys, enums, `const`
   values, ordering notes in `description`s, rounding precision, and self-attestation
   flags. Build your output to match it exactly (respect `additionalProperties:false`).
3. **Pin the scope** from the prompt: teams, product area(s), quarter / as-of date /
   window, release id, `scope_id`. Scope match uses authoritative `team` **and**
   `product_area` (both must be in scope), plus the relevant time window.
4. **Pull the data** (prefer `POST /api/query` for filtering/aggregation; the token is
   required there). Get the candidate work items, plus mix_targets / sla_policy /
   milestones / blockers / dependencies as the family needs.
5. **Partition primary vs excluded** (duplicates, cancelled, out-of-window, decoys).
6. **Classify / compute** per the family playbook below, using authoritative fields only.
7. **Apply ordering & rounding exactly** as the template states.
8. **Validate** against the template and the checklist, then output JSON only.

Determinism defaults (unless a template says otherwise): sort id lists lexicographically;
list teams/product areas alphabetically; category rows in the fixed order
`NewFeature, TechDebt, Reliability, Security`; percentages as percentage points to **1
decimal**; rates (breach/readiness) to **3 decimals**. Counts are **item counts, not
story points**.

## Family A — Portfolio-mix review / readout

Goal: the count-based category mix of in-scope **closed** portfolio work vs a target mix,
plus gaps and a rebalance recommendation.

1. **Population**: primary items where `team ∈ scope.teams` AND `product_area ∈
   scope.product_areas` AND the item is completed within the quarter — i.e.
   `status ∈ {Closed, Done, Deployed, Verified}` with `closed_at` inside the quarter
   window (2025-Q4 = `2025-10-01 .. 2025-12-31`). Exclude duplicates, cancelled, and
   anything closed outside the quarter.
2. **Classify** each included item into exactly one category via the `work_type` map
   (see data-model). `category_counts` = item counts per category; `total_included` =
   their sum.
3. **Actual mix**: `actual_pct(c) = 100 * count(c) / total_included`, 1 dp.
4. **Target mix**: fetch the `mix_targets` row for the task's exact `scope_id`; each
   `*_pct` fraction ×100 → `target_pct`, 1 dp.
5. **Gaps**: `gap_pct = actual_pct - target_pct`, 1 dp, one row per category in fixed
   order.
6. **Under-invested / largest deficit**: categories with negative gap; order most-negative
   first; the single most-negative is the largest deficit / primary rebalance target.
7. **Recommendation**:
   - Any negative gap → `REBALANCE_CAPACITY`; primary = largest negative gap, secondary =
     next (rationale e.g. `LARGEST_NEGATIVE_GAP`). For a single `owner_team`, pick
     deterministically the in-scope team best positioned to close that deficit (derive
     from the data — e.g. the team with the most in-scope closed volume — and apply a
     stable tiebreak); confirm the template's allowed enum.
   - No negative gaps → `MAINTAIN_CURRENT_MIX` / nulls / `NO_NEGATIVE_GAPS`.
   - Irreconcilable data conflict → the data-quality path if the template offers one.
8. **Exclusions / attestation**: list excluded duplicate ids and cancelled ids as the
   template splits them; set any "ignored mirror_status and legacy_category" attestation
   flag to `true` (and actually ignore those fields). Order excluded/included id lists as
   instructed (commonly `closed_at` asc, then id asc).

## Family B — SLA aging / breach audit

Goal: the primary reliability+security SLA population, which items are overdue, aging
distribution, hotspots, duplicate clusters, missing owners, and the breach rate.

Inputs: `scope.teams` (2), target `categories` (Reliability, Security), `as_of` date,
`recent_closed_window_days` N.

1. **In-scope** = primary items with `team ∈ scope.teams` AND portfolio category (via
   `work_type`) ∈ scope categories.
2. **Included primary population** = in-scope items that are still **active**
   (`status ∉ COMPLETE`) **or** recently closed (`closed_at` within `(as_of − N, as_of]`).
   Exclude items closed before that window, and exclude duplicates/cancelled (duplicates
   go to `duplicate_clusters`, not the population).
3. **Overdue** = included primary items still unresolved with `due_at < as_of`
   (authoritative `due_at`). Recently-closed items stay in the denominator but are not
   overdue. (If a template's field descriptions imply closed-late items count as breached,
   reconcile to that wording — decide once and apply consistently.)
4. **Aging buckets** by `days_overdue = as_of − due_at` for overdue items, into
   `0-3 / 4-7 / 8-14 / 15-30 / 31+` (inclusive ranges as the template lists them).
5. **Breakdowns**: overdue counts by team (alphabetical) and/or by `severity` (S1..S4) as
   the template requires. **Hotspot** = the `(team, owner)` pair with the most overdue;
   `owner` null → `UNASSIGNED`.
6. **Missing owners** = included primary ids with null/empty `owner`, sorted.
7. **Duplicate clusters** = in-scope duplicates grouped by `duplicate_of` → `{primary_id,
   duplicate_ids sorted}`, clusters sorted by `primary_id`.
8. **Escalation queue** (when asked) = overdue primary ids in follow-up priority: by
   `severity` (S1 first) → most overdue (`due_at` asc) → id. Confirm the template's stated
   priority definition.
9. **`breach_rate` = |overdue primary| / |included primary|**, rounded to **3 dp**
   (guard against divide-by-zero → template-appropriate zero).

## Family C — Release-readiness assessment

Goal: ship decision, per-milestone completion, gating items, blocker-cause counts,
critical dependency chains, readiness score — for one release id.

1. **Release work items** = items with `release_id = <release>` (each also has a
   `milestone_id`). Drop duplicates/cancelled from primary.
2. **Per milestone** (all milestones with that `release_id`, sorted by `milestone_id`
   asc): `primary_total` = primary items with that `milestone_id`; `complete_primary` =
   those with `status ∈ COMPLETE`; `completion_pct = 100 * complete/total`, 1 dp.
3. **Gating work item ids** = non-complete primary release items (`status ∉ COMPLETE`),
   sorted ascending, unique.
4. **Blocker cause counts** = blockers for this release that are **unresolved**
   (`resolved_at IS NULL`) and **high-impact** (`severity ∈ {Critical, High}`), grouped by
   **exact** `cause` string.
5. **Critical dependency chains** = ordered `blocked_id → depends_on_id → ...` paths that
   start at a blocked release work item and end at a non-complete dependency, following
   the release-gating relation (`blocks-release-readiness`). Emit each path as an ordered
   id list; sort chains lexicographically by the full path.
6. **`readiness_score`** = completed primary ÷ primary denominator across the release,
   rounded to **3 dp** (the aggregate of the milestone completion).
7. **`ship_decision`** (`SHIP` / `SHIP_WITH_WATCH` / `NO_SHIP`): decide from readiness +
   gating + unresolved high-impact blockers. Defensible rule (confirm against the prompt's
   thresholds): any unresolved high-impact blocker or critical unmet dependency → tends to
   `NO_SHIP`; full readiness (score = 1.0) with no gating/blockers → `SHIP`; partial
   readiness with manageable risk → `SHIP_WITH_WATCH`. Apply one explicit rule
   consistently.
8. Do **not** use `mirror_status` as release truth.

## Validation checklist (before returning)

- Output is a single JSON object, no prose, matching the template's keys/enums/`const`s
  exactly; no extra keys (`additionalProperties:false`).
- No decoy field influenced the answer: `mirror_status` and `legacy_category` ignored;
  category came from `work_type`; SLA deadline from `due_at`.
- Duplicates and cancelled items excluded from primary and reported where required;
  clusters grouped by `duplicate_of`.
- Scope filter used authoritative `team` + `product_area` + the correct time window;
  out-of-window items excluded.
- Ordering applied (ids lexicographic, teams/areas alphabetical, category rows in fixed
  order, chains/clusters sorted as specified).
- Rounding correct: percentage points to 1 dp; rates to 3 dp. Counts are item counts.
- Percentages/gaps are internally consistent (actual − target = gap; counts sum to
  total_included; completion = complete ÷ total).
- Any self-attestation flag (e.g. ignored-mirror/legacy) set truthfully.
