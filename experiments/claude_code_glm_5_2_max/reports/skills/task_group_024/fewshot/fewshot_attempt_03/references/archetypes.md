# Archetype Playbooks

Step-by-step procedures for the three review archetypes. Apply the **core
correctness rules** in `SKILL.md` throughout (authoritative `status` only,
ignore `legacy_category`/`mirror_status`, primary-vs-duplicate, cancelled
excluded, closed/complete set, category resolution, stable ordering, rounding).

The formulas below are verified against the data model — they are the method,
not task-specific answers. Field names still follow whichever
`answer_template.json` the task provides.

---

## A. Portfolio-mix review

Goal: compare the actual count-based category mix of in-scope **closed** work to
a **target mix**, report gaps, and recommend a rebalance action.

### Steps

1. **Parse scope** from the prompt: `scope_id` (and target `scope_id` if
   separate), quarter, teams, product_area(s).
2. **Load the target**: from `mix_targets`, select the row where
   `scope_id` == the target scope id. Convert its four `*_pct` fractions ×100
   (round 1dp) → `target_pct` for NewFeature, TechDebt, Reliability, Security.
3. **Select in-scope closed primary work** from `work_items`:
   - `team` ∈ scope teams, `product_area` ∈ scope product areas.
   - `closed_at` falls in the scope quarter (confirm exact window from the
     prompt).
   - `status` ∈ {Closed, Done, Deployed, Verified} (terminal).
   - **Primary only**: `status != "Duplicate"` AND `duplicate_of` is null.
   - `status != "Cancelled"`.
4. **Classify** each included item into exactly one of NewFeature, TechDebt,
   Reliability, Security using the resolution rule (`SKILL.md` §6): scan
   `work_type` + `labels` + `title`, precedence Security > Reliability >
   TechDebt > NewFeature.
5. **Counts**: `category_counts` = item counts per category (not story points).
   `total_included` = sum of counts.
6. **Actual percentages**: `actual_pct` = count / total_included × 100, 1dp.
7. **Gap table / mix table**: one row per category in the fixed order
   NewFeature, TechDebt, Reliability, Security. Each row has `target_pct`,
   `actual_pct`, and `gap_pct = actual_pct − target_pct` (1dp).
8. **Under-invested / deficit**: categories with `gap_pct < 0`.
   - `under_invested_categories` (if the template has it): negative-gap
     categories ordered from **most negative** gap to least negative.
   - `largest_deficit_category` (if the template has it): the single most
     negative gap.
9. **Follow-up / recommended action**:
   - If no negative gaps → action `MAINTAIN_CURRENT_MIX`, rationale
     `NO_NEGATIVE_GAPS`, categories null (or per template).
   - Else → action `REBALANCE_CAPACITY` targeting the largest-deficit category
     (and next-deficit as secondary if the template has a secondary field),
     rationale `LARGEST_NEGATIVE_GAP`.
   - If the data is internally inconsistent (e.g. conflicting signals you cannot
     resolve) → action `INVESTIGATE_DATA_QUALITY`, rationale `DATA_CONFLICT`.
   - For templates with `owner_team`, pick the scope team that should absorb the
     rebalance per the prompt's business context.
10. **Exclusion lists** (shape follows the template):
    - **Duplicates**: in-scope records excluded because they are duplicates
      (`status == "Duplicate"` or `duplicate_of` non-null).
    - **Cancelled**: in-scope records excluded because `status == "Cancelled"`.
    - **Distractors**: in-scope records that look related to the scope (matching
      team/product_area/quarter, possibly with a tempting `mirror_status` or
      `legacy_category`) but are not primary closed portfolio work — e.g.
      duplicates and cancelled records when the template uses a single
      `excluded_distractor_ids` list.
    - `ignored_mirror_status_and_legacy_category: true` where the template has
      that flag.
11. **Ordering**: `included_work_item_ids` ordered by `closed_at` ascending,
    then `id` ascending. Exclusion ID lists ordered per the template (typically
    `closed_at` asc then `id` asc, or ascending/lexicographic).

### Output check
- `total_included` == `len(included_work_item_ids)` == sum of `category_counts`.
- `sum(actual_pct)` ≈ 100 (within rounding); `sum(target_pct)` ≈ 100.
- Rows in NewFeature, TechDebt, Reliability, Security order.

---

## B. SLA aging / breach audit

Goal: over reliability & security primary work, find overdue items, aging
distribution, hotspots, duplicate clusters, missing owners, and the breach rate.

### Verified core formulas

- **Overdue** = `as_of > due_at` (the item's due date has passed as of the
  as-of date). This holds **regardless** of closed/open status — a closed item
  whose `due_at` passed before `as_of` is still overdue. It is **not** computed
  by comparing an age to `sla_policy.days_to_due`.
- **Aging basis** (for `aging_bucket_counts`): `age = (closed_at if the item is
  closed else as_of) − created_at`, in days. Closed items use `closed_at`; open
  items use `as_of`.
- **Aging buckets**: `0-3`, `4-7`, `8-14`, `15-30`, `31+` (inclusive days).
- **Breach rate** = `overdue_primary_count / included_primary_count`, 3dp.

### Steps

1. **Parse scope**: teams, `as_of` date, `recent_closed_window_days`, categories
   (typically Reliability + Security, in the order the prompt lists them).
2. **Select in-scope primary SLA-relevant items** from `work_items`:
   - `team` ∈ scope teams.
   - Resolved category ∈ scope categories (use the resolution rule; an item is
     SLA-relevant if it resolves to Reliability or Security — signals include
     `reliability`/`outage`/`latency`/`flaky`/`incident` and
     `security`/`cve`/`encryption`/`auth`).
   - **Primary only** (`status != "Duplicate"` and `duplicate_of` null);
     `status != "Cancelled"`.
   - **Time window**: `created_at <= as_of`, AND the item is either still open
     as of `as_of` (`closed_at` is null or `closed_at > as_of`) **or** closed
     within the recent-closed window (`as_of − recent_closed_window_days <=
     closed_at <= as_of`).
3. **`included_primary_ids`**: sorted ascending/lexicographically.
4. **`overdue_primary_ids`**: subset with `as_of > due_at`; sorted ascending.
5. **`aging_bucket_counts`** (if the template has it): bucket each included
   primary's age (formula above) into 0-3 / 4-7 / 8-14 / 15-30 / 31+.
6. **`team_overdue_counts`** (if present): per scope team, count of overdue
   primary items; teams listed alphabetically.
7. **`top_hotspot`** (if present): the (team, owner) pair with the most overdue
   primary items; `owner` is `UNASSIGNED` when `owner` is null. Break ties
   deterministically (e.g. team then owner alphabetical) and confirm against the
   data.
8. **`overdue_counts_by_severity`** (if present): counts of overdue primary
   items per severity `S1`/`S2`/`S3`/`S4`.
9. **`escalation_queue_ids`** (if present): overdue primary ids in escalation
   order = **severity ascending (S1 → S4), then `due_at` ascending** (earliest
   due first). Note `due_at` — not `priority` or id — is the tiebreak.
10. **`duplicate_clusters`** (reported, not counted): for each in-scope primary
    that has duplicates, emit `{primary_id, duplicate_ids}` where
    `duplicate_ids` are the in-scope duplicates whose `duplicate_of` ==
    `primary_id`, sorted ascending. Clusters sorted by `primary_id`.
11. **`missing_owner_ids`**: included primary ids with `owner` null, sorted
    ascending.
12. **`breach_rate` / `sla_breach_rate`**: `overdue_primary_count /
    included_primary_count`, 3dp.

### Output check
- `breach_rate` ≈ `len(overdue_primary_ids) / len(included_primary_ids)`.
- `sum(aging_bucket_counts)` == `len(included_primary_ids)`.
- `sum(overdue_counts_by_severity)` == `len(overdue_primary_ids)`.
- Duplicate ids never appear in `included_primary_ids`.

---

## C. Release-readiness assessment

Goal: decide SHIP / SHIP_WITH_WATCH / NO_SHIP for a release, with milestone
completion, gating items, blocker causes, dependency chains, and a readiness
score.

### Verified core formulas

- **`readiness_score`** = `sum(complete_primary across milestones) /
  sum(primary_total across milestones)` — the **pooled** ratio, 3dp. It is **not**
  the mean of milestone completion percentages.
- **Complete/primary per milestone**: `complete_primary` = primary release work
  items for that milestone with `status` ∈ {Closed, Done, Deployed, Verified};
  `primary_total` = all primary release work items for that milestone
  (duplicates excluded).
- **`completion_pct`** = `complete_primary / primary_total × 100`, 1dp.
- **`gating_work_item_ids`**: non-complete primary release work items that carry
  an **unresolved high-impact blocker** (High/Critical, status ≠ Resolved).
  Sorted ascending, unique. (A complete item with a blocker is not gating; a
  non-complete item without a high-impact blocker is not gating.)
- **`critical_dependency_chains`**: ordered work-item-id paths from a blocked
  release work item to a **non-complete** dependency, following
  `dependencies` edges (`blocked_id → depends_on_id`). A chain is critical only
  if it terminates at a non-complete item. Sorted lexicographically by the full
  path. Empty array when every dependency in-scope is complete.

### Steps

1. **Parse scope**: `release_id`.
2. **Load release graph**:
   - `releases` row for the `release_id`.
   - `milestones` where `release_id` matches (these are the release's milestones).
   - `work_items` where `release_id` matches **or** `milestone_id` ∈ the
     release's milestone ids.
   - `blockers` where `release_id` matches.
   - `dependencies` where `blocked_id` or `depends_on_id` is a release work item
     (fetch the full graph you need to walk chains).
3. **`milestone_completion`**: one entry per milestone, sorted by `milestone_id`
   ascending. For each: `complete_primary`, `primary_total`, `completion_pct`
   (formulas above). Exclude duplicates from both numerator and denominator.
4. **`gating_work_item_ids`**: non-complete primary release items with an
   unresolved high-impact blocker; sorted ascending, unique.
5. **`blocker_cause_counts`**: unresolved high-impact blockers
   (`status != Resolved` AND `severity ∈ {High, Critical}`) for the release,
   keyed by the exact `cause` string, value = count.
6. **`critical_dependency_chains`**: walk dependency edges from blocked release
   work items; keep only paths ending at a non-complete dependency; sort
   lexicographically by full path. `[]` if none.
7. **`readiness_score`**: pooled `sum(complete_primary) / sum(primary_total)`,
   3dp.
8. **`ship_decision`**:
   - `NO_SHIP` if any gating work item exists, **or** any unresolved high-impact
     blocker exists, **or** any critical dependency chain exists.
   - `SHIP` if `readiness_score` is 1.0 (all primary release work complete) and
     there are no unresolved high-impact blockers and no critical chains.
   - `SHIP_WITH_WATCH` for the intermediate case (e.g. only low-impact
     unresolved blockers, or minor non-gating work remaining). Confirm the exact
     threshold from the prompt.

### Output check
- `readiness_score` × `sum(primary_total)` ≈ `sum(complete_primary)`.
- `sum(complete_primary)` across milestones == numerator used for
  `readiness_score`.
- `blocker_cause_counts` values sum to the count of unresolved high-impact
  blockers.
- `milestone_completion` sorted by `milestone_id`; `gating_work_item_ids` sorted
  and unique.
