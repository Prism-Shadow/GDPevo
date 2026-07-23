# Task Family Procedures

Scope parameters (teams, product area, quarter, `scope_id`, as-of date,
recent-closed window, `release_id`, etc.) come from the **task prompt** — read
them fresh each time. All computations use primary records only (see SKILL.md
record-handling rules) unless a step explicitly handles duplicates/cancelled.

---

## Family A — Portfolio mix

*Templates ask for: included ids, category counts, actual percentages, target
gaps, under-invested categories, a follow-up action, and exclusion flags/lists.*

### 1. Scope filter
Select `work_items` where:
- `team` ∈ scope teams, **and**
- `product_area` ∈ scope product areas (if the prompt names them), **and**
- `closed_at` falls within the scope quarter (e.g. `2025-Q4` → Oct–Dec).

### 2. Included (primary closed portfolio work)
From the scoped set, keep records that are:
- **Closed**: `closed_at` is not null **and** `status` is terminal
  (`Closed`/`Done`/`Verified`/`Deployed`), **and**
- **Primary**: `duplicate_of` is null **and** `status` not `Duplicate` **and**
  `status` not `Cancelled`.

Order `included_work_item_ids` by `closed_at` ascending, then `id` ascending.

### 3. Classify & count
Classify each included primary item per `classification.md`. `category_counts`
are **item counts** (not story points). The four categories are always present:
`NewFeature`, `TechDebt`, `Reliability`, `Security`.

### 4. Actual mix percentages
`actual_pct = count / total_included * 100`, rounded to 1 decimal.
(`total_included` = sum of the four counts.)

### 5. Target mix
Fetch the `mix_targets` row whose `scope_id` matches the task scope. Convert the
fractional fields to percentage points (`* 100`), 1 decimal. Map:
`new_feature_pct`→NewFeature, `tech_debt_pct`→TechDebt,
`reliability_pct`→Reliability, `security_pct`→Security.

### 6. Gap table
One row per category in fixed order `NewFeature, TechDebt, Reliability,
Security`. `gap_pct = actual_pct − target_pct` (1 decimal). Include
`target_pct` and `actual_pct` columns as the template requires.

### 7. Under-invested categories
Categories with negative `gap_pct`, ordered from **most negative** to **least
negative**.

### 8. Follow-up / recommended action
- If any negative gaps exist → action `REBALANCE_CAPACITY`; `primary_category` =
  the largest-negative-gap category; `secondary_category` = the next
  largest-negative-gap (or null if only one); rationale `LARGEST_NEGATIVE_GAP`.
- If no negative gaps → `MAINTAIN_CURRENT_MIX`, categories null, rationale
  `NO_NEGATIVE_GAPS`.
- If the data conflicts (e.g. target row missing/mismatched) →
  `INVESTIGATE_DATA_QUALITY`, rationale `DATA_CONFLICT`.
- Some templates pin the action enum (e.g. only `REBALANCE_CAPACITY`) and ask
  for an `owner_team` (the scope team most associated with the deficit category)
  — follow that template's exact fields.

### 9. Exclusions
Report in-scope records that were excluded, in the shape the template requires:
- Duplicates (`duplicate_of` non-null or `status == Duplicate`) — grouped or
  listed.
- Cancelled (`status == Cancelled`).
- "Distractors" = same-scope, same-quarter closed records that are duplicates or
  cancelled (some templates collapse both into one `excluded_distractor_ids`
  list ordered by `closed_at` then `id`).
- Set `ignored_mirror_status_and_legacy_category: true` when the template asks
  for that flag.

---

## Family B — SLA aging

*Templates ask for: primary SLA population, overdue primary ids, aging buckets,
overdue counts (by team and/or severity), a hotspot, an escalation queue,
duplicate clusters, missing-owner ids, and a breach rate.*

### 1. SLA population (included primary ids)
Select `work_items` where:
- `team` ∈ scope teams, **and**
- classified category ∈ {`Reliability`, `Security`} (the SLA-relevant
  categories — note the template may list them as `Security, Reliability`), and
- **Primary** (`duplicate_of` null, `status` not `Duplicate`/`Cancelled`), and
- **SLA-relevant as of the as-of date**: either still open (non-terminal
  `status`) on the as-of date, **or** closed within the `recent_closed_window`
  days ending on the as-of date (`closed_at` between `as_of − window` and
  `as_of`).

Sort `included_primary_ids` ascending.

### 2. Overdue
A primary item is **overdue** when:
- `due_at` is before the as-of date, **and**
- it was not completed on time: `closed_at` is null **or** `closed_at > due_at`.

(Use the authoritative `due_at`; do not derive a due date from `sla_policy`.)
Sort `overdue_primary_ids` ascending.

### 3. Aging buckets
For each included primary item compute `age_in_days`:
- If closed within the window: `age = closed_at − created_at`.
- If still open: `age = as_of − created_at`.

Bucket: `0-3`, `4-7`, `8-14`, `15-30`, `31+`. Count **all** included primary
items (not just overdue).

### 4. Overdue breakdowns
- `team_overdue_counts`: count overdue primary per scope team; teams listed
  alphabetically.
- `overdue_counts_by_severity`: count overdue primary per `S1`/`S2`/`S3`/`S4`
  (all four keys present, zero allowed).
- `top_hotspot`: the (team, owner) pair with the most overdue primary items;
  `owner` is `UNASSIGNED` when null. Ties → pick deterministically (e.g.
  alphabetical team then owner) and keep the count.

### 5. Escalation queue (when the template asks)
`escalation_queue_ids`: overdue primary ids ordered for follow-up — highest
`priority` first (lower `priority` number = higher urgency), then by severity
(`S1`>`S2`>…), then by age (older first). Apply the template's stated ordering
if it differs.

### 6. Duplicate clusters
Group duplicates (`duplicate_of` non-null or `status == Duplicate`) by their
`duplicate_of` target. Each cluster: `primary_id` = the target,
`duplicate_ids` sorted ascending. Clusters sorted by `primary_id`. These are
**reported only** — not in the primary population.

### 7. Missing owners
`missing_owner_ids`: included primary ids with `owner` null, sorted ascending.

### 8. Breach rate
`breach_rate` (or `sla_breach_rate`) = `overdue_primary_count /
included_primary_count`, rounded to **3 decimals**.

---

## Family C — Release readiness

*Templates ask for: ship decision, milestone completion, gating work item ids,
blocker cause counts, critical dependency chains, and a readiness score.*

### 1. Release work set
Select `work_items` where `release_id` == the target release and **primary**
(`duplicate_of` null, `status` not `Duplicate`/`Cancelled`).

### 2. Milestone completion
For each milestone of the release (from `milestones` where `release_id`
matches), over the primary release work whose `milestone_id` == that milestone:
- `primary_total` = count of primary items assigned to the milestone.
- `complete_primary` = count of those with terminal `status`
  (`Closed`/`Done`/`Verified`/`Deployed`).
- `completion_pct` = `complete_primary / primary_total * 100`, 1 decimal.

Sort `milestone_completion` by `milestone_id` ascending.

### 3. Readiness score
`readiness_score` = `sum(complete_primary) / sum(primary_total)` across all
milestones of the release, rounded to **3 decimals**.

### 4. High-impact unresolved blockers
From `blockers` for the release, keep those that are **unresolved**
(`status` in `{Open, Monitoring}`) **and high-impact** (`severity` in
`{High, Critical}`). `blocker_cause_counts`: group these by exact `cause` text
→ count. Keys are the exact cause strings.

### 5. Gating work item ids
Non-complete primary release work items (terminal? no — **non-terminal**
`status`) that have **at least one** high-impact unresolved blocker (from step
4, by `work_item_id`). Sorted ascending, unique. (A complete item with a blocker
does **not** gate.)

### 6. Critical dependency chains
Build from the `dependencies` table. Starting from **gating** release work items
(step 5), follow `blocked_id → depends_on_id` edges to a dependency that is
itself non-complete and primary (non-terminal `status`, not Duplicate/Cancelled).
Emit each chain as an ordered id path `[blocked_id, ..., depends_on_id]`. Sort
chains lexicographically by the full path. If none, emit `[]`.

### 7. Ship decision
`SHIP` / `SHIP_WITH_WATCH` / `NO_SHIP`:
- `NO_SHIP` when there are gating work items, or unresolved high-impact
  blockers, or `readiness_score` is below the release's threshold.
- `SHIP_WITH_WATCH` for marginal cases (e.g. readiness acceptable but low-severity
  unresolved blockers or minor concerns remain).
- `SHIP` when readiness is high and no gating items or high-impact blockers
  remain.

The exact threshold is release-specific; weigh gating items and high-impact
blockers most heavily.

---

## Universal output rules

- One JSON object matching `answer_template.json` exactly (field names, required
  keys, enums, per-field ordering). No prose outside the JSON.
- Reuse the template's field names — do **not** import names from a different
  task's template.
- Precision: percentages 1 decimal; rates/scores 3 decimals.
- ID lists ascending/lexicographic; included-portfolio lists by `closed_at`
  then `id`; teams alphabetical; duplicate clusters by `primary_id`.
- Recompute every value from the live environment for the current scope; never
  copy values from an example answer.
