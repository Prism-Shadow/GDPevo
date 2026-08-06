---
name: portfolio-env-analysis
description: >-
  Answer engineering-portfolio review tasks that run against the shared read-only
  work-item HTTP environment (base URL + endpoints + query token supplied in an
  environment_access.md / runtime-access file). Covers the three recurring task
  families: (1) quarterly portfolio-mix reviews vs. a mix_targets row, (2) SLA
  aging / breach reviews for Reliability+Security work, and (3) release-readiness
  ship decisions from releases/milestones/blockers/dependencies. Use whenever a
  prompt references work items, mix targets, an SLA policy, releases, milestones,
  blockers, or dependencies and asks for a single JSON answer matching an
  input/payloads/answer_template.json. Encodes the shared conventions: which
  fields are authoritative vs. stale, how to exclude duplicates/cancelled/
  distractors, how to classify work into the four portfolio categories, and the
  ordering + precision rules that make answers deterministic.
---

# Portfolio environment analysis

You are given (a) a task `prompt.txt` describing a business scope, (b) an
`answer_template.json` (usually under `input/payloads/`) that is the exact output
contract, and (c) a runtime-access note (`environment_access.md`) with the base
URL, endpoint list, and query token. Produce **one JSON object** that satisfies
the template. Nothing else is graded.

## 0. Orient before you compute

1. Read the runtime-access file for the **base URL**, the **allowed endpoints**,
   and the **query token**. The token (header `X-Env-Token`) is required *only*
   for `POST /api/query`; GET endpoints are open. Do not hardcode a base URL —
   read it each run (`<TASK_ENV_BASE_URL>` in the prompt maps to that value).
2. Read the task `prompt.txt` and the `answer_template.json` **together**. The
   template's required keys, `const` values, `enum`s, `pattern`s, `minItems`/
   `maxItems`, and field `description`s are binding instructions — they often
   state the ordering and rounding rules verbatim. Echo every `const`/fixed
   scope value straight from the template.
3. Identify which of the three **task families** you are in (see §5). Field names
   in the template tell you: `category_*`/`mix_table` → portfolio mix; `*_primary_ids`/
   `aging_*`/`breach_rate` → SLA aging; `ship_decision`/`milestone_completion`/
   `readiness_score` → release readiness.

## 1. Pull data — prefer the SQL endpoint

`POST /api/query` accepts SQLite-flavored read-only SQL over these tables:
`work_items`, `mix_targets`, `sla_policy`, `releases`, `milestones`, `blockers`,
`dependencies`. Request body `{"sql": "..."}`, header `X-Env-Token: <token>`.
Use it to filter and aggregate server-side (`GROUP BY`, `julianday()` date math,
`ORDER BY`) rather than paging the GET lists by hand. GET endpoints return the
same data if you prefer. `work_items` has ~239 rows — small enough to pull whole
and reason in code. See `reference.md` for the field dictionary and query recipes.

## 2. Authoritative vs. stale fields (the #1 recurring trap)

Every family warns about "stale mirror / legacy / export fields." Concretely:

| Use (authoritative)                     | Ignore (planted distractor)             |
|-----------------------------------------|-----------------------------------------|
| `status`                                | `mirror_status`                         |
| `work_type`, `labels`, `title`          | `legacy_category`                       |
| `closed_at`, `created_at`, `owner`, `severity`, `team`, `product_area`, `duplicate_of`, `release_id`, `milestone_id` | (any field the prompt names as mirror/export) |

Never let `mirror_status` or `legacy_category` drive inclusion or classification.
For release truth (family 3), use milestone/status/blocker/dependency records, not
mirror fields.

## 3. Exclusions & the primary population

Before counting anything, split in-scope records into **primary** vs **excluded**:

- **Duplicates** — exclude if `status = 'Duplicate'` **OR** `duplicate_of IS NOT NULL`.
  These two signals only partly overlap, so test both. When the answer wants
  *duplicate clusters*, group the duplicate records by their `duplicate_of` target
  (that target is the `primary_id`); duplicates whose target is null have no cluster.
- **Cancelled** — exclude if `status = 'Cancelled'`.
- **Distractors** — same-scope records that are not primary closed portfolio work
  (duplicates, cancelled, wrong-status, or records the prompt calls out). Report
  their ids where the template asks (`excluded_*_ids`), but never count them in the
  primary metrics.

`primary = in-scope AND not duplicate AND not cancelled`. Report excluded ids in
the template's exclusion fields; they are graded too.

## 4. Classify work into the four portfolio categories

Categories are exactly: **NewFeature, TechDebt, Reliability, Security**. Derive
each item's category from authoritative signals (`work_type` first, then
`labels`/`title`); never from `legacy_category`. Canonical `work_type` map:

- Feature, Enhancement → **NewFeature**
- Refactor, Chore, Dependency → **TechDebt**
- Bug, Incident, Reliability → **Reliability**
- Security, Compliance → **Security**

When signals **conflict** (e.g. a generic `work_type` but a strong label/title
keyword, or multiple categories in the labels), resolve with the fixed
risk-priority precedence **Security > Reliability > TechDebt > NewFeature**, using
the keyword sets in `reference.md`. Apply the same rule to every item consistently.

## 5. Family playbooks (map each to the template fields)

### 5a. Portfolio-mix review
Scope = quarter + teams + product area(s) + `scope_id`.
1. Primary population = closed portfolio work in scope: `team` ∈ scope teams,
   `product_area` ∈ scope areas, `closed_at` inside the quarter, and a terminal
   completed `status` (`Closed`, `Deployed`, `Done`, `Verified` — **not** Backlog/
   In Progress/Review/Reopened/Duplicate/Cancelled). Apply §3 exclusions.
2. Classify each (§4); `category_counts` are **item counts, not story points**.
3. `actual_pct` = count / total × 100, rounded to **1 dp**.
4. `target_pct` = the `mix_targets` row **whose `scope_id` equals the task
   `scope_id`** — its `new_feature_pct`/`tech_debt_pct`/`reliability_pct`/
   `security_pct` are fractions; ×100 and round to 1 dp.
5. `gap_pct = actual_pct − target_pct` (1 dp). Under-invested / largest-deficit =
   most-negative gap(s). Follow the template's action enum and rationale-code logic
   (largest negative gap → REBALANCE_CAPACITY; no negative gaps → MAINTAIN; data
   conflict → INVESTIGATE_DATA_QUALITY).
6. `included_work_item_ids` ordered by `closed_at` asc, then `id` asc.

### 5b. SLA aging / breach review
Scope = teams + as-of date + recent-closed-window (days) + SLA categories
(Reliability, Security).
1. Primary population = in-scope, primary (§3) items classified into the SLA
   categories, whose `closed_at` falls in `[as_of − window_days, as_of]`.
2. **SLA deadline** for an item = `created_at + days_to_due[severity]` from
   `/api/sla-policy` (currently S1=3, S2=10, S3=21, S4=45 days — re-fetch, don't
   assume). `due_at` on the item deviates from policy and behaves like a mirror
   field — treat the **policy** as authoritative unless the task explicitly names
   `due_at`. **Overdue / breach** = resolution later than the deadline
   (`closed_at > deadline`; for unresolved items, `as_of > deadline`).
3. Aging = days overdue (`closed_at − deadline`, floored at 0), bucketed per the
   template's bucket labels; or by severity when the template keys by S1–S4.
4. Hotspot = the (team, owner) pair with the most overdue primary records; missing
   owner → the template's sentinel (e.g. `UNASSIGNED`). `missing_owner_ids` =
   primary items with null `owner`.
5. Duplicate clusters (§3) reported but excluded from primary counts.
6. `breach_rate = overdue_primary / included_primary`, rounded to **3 dp**.
   Escalation queue = overdue primary in priority order (severity, then age/due).

### 5c. Release-readiness assessment
Scope = one `release_id`.
1. Release work items = `work_items.release_id = <release>`. Milestones =
   `milestones.release_id = <release>`; each milestone's primary items = release
   work items with that `milestone_id` (apply §3; use authoritative `status`).
2. Per milestone: `complete_primary` = completed primary (terminal status),
   `primary_total` = primary denominator, `completion_pct` = ratio × 100 (1 dp).
   Sort `milestone_completion` by `milestone_id` asc.
3. `gating_work_item_ids` = non-complete release work items gating readiness,
   sorted asc, unique.
4. `blocker_cause_counts` = count **unresolved** (`resolved_at IS NULL`)
   **high-impact** (`severity ∈ {Critical, High}`) blockers for the release,
   keyed by the **exact** `cause` string.
5. `critical_dependency_chains` = ordered work-item-id paths from a blocked release
   work item to a non-complete dependency, walking `dependencies` (relations like
   `blocks-release-readiness`, `security-review-required`, `validation-required`,
   `audit-evidence-required`). Sort paths lexicographically by the full path.
6. `readiness_score` = completed primary / primary denominator, 3 dp. `ship_decision`
   ∈ {SHIP, SHIP_WITH_WATCH, NO_SHIP} per the template's threshold logic (unresolved
   high-impact blockers / low readiness → NO_SHIP; clean → SHIP; in-between → WATCH).

## 6. Determinism & precision (apply to every answer)

- **Ordering**: id lists lexicographic string sort unless told otherwise; portfolio
  `included_work_item_ids` by `closed_at` asc then `id` asc; teams/product areas
  alphabetical (or the template's stated order); duplicate clusters by `primary_id`
  with `duplicate_ids` sorted; dependency paths lexicographic. Note string sort puts
  digits before letters (`WI-24024-050` < `WI-24024-S004`).
- **Precision**: percentages / `*_pct` → 1 dp; `breach_rate` / `readiness_score` /
  other rates → 3 dp. `gap = actual − target`. Round only at output.
- **Counts** are item counts, never story points.

## 7. Before you submit

- Output is a **single JSON object**, no prose, no markdown fences, nothing outside it.
- Every `required` key present; with `additionalProperties: false` add **no** extra
  keys; respect every `const`/`enum`/`pattern`/`minItems`/`maxItems`.
- Re-verify each list's sort order and each number's decimal places.
- Sanity check: category counts sum to `total_included`; percentages ~100; excluded
  ∪ included covers the in-scope records with no overlap.
- Spot-check 2–3 records end-to-end (classification, exclusion, breach) against the
  raw fields before trusting the aggregate.

See `reference.md` for the field dictionary, full enum vocabularies, the
classification keyword sets, and copy-paste SQL recipes.
