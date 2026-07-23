# Task archetypes — computation playbooks

Three archetypes recur. Each lists the inputs, the computation, and the output shape. The field
names here are the conventional names; **always conform to the specific `answer_template.json`**,
which is authoritative for field names, enums, and structure.

---

## §A. Portfolio-mix review

**Trigger:** the prompt names a `scope_id`, a quarter, teams, and a product area, and asks to
compare the actual mix of closed work to a target mix.

**Inputs:**
- work items for the scope (teams + product area + quarter), filtered to closed/complete + primary
  (see `data_hygiene.md` §5).
- the `mix_targets` row whose `scope_id` equals the task's target scope.

**Computation:**
1. Include the in-scope closed primary work items; record excluded duplicates / cancelled /
   distractors.
2. Classify each included item into one portfolio category (`data_hygiene.md` §6).
3. `category_counts` = item counts per category (counts, not story points).
4. `actual_pct` (per category) = count ÷ total included × 100, to 1 decimal.
5. `target_pct` (per category) = the mix_targets row's matching fraction × 100, to 1 decimal.
6. `gap_pct` = `actual_pct − target_pct`, to 1 decimal. (Some schemas name it `gap_pct`; others put
   `actual_pct`/`target_pct`/`gap_pct` in a `mix_table` or `gap_table`.)
7. **Under-invested / largest deficit** = category(ies) with negative gap, ordered most-negative
   first; the largest deficit is the most-negative gap.
8. **Follow-up / recommended action** — choose per the schema's enum and the gaps:
   - `REBALANCE_CAPACITY` when there is a meaningful negative gap (rationale `LARGEST_NEGATIVE_GAP`,
     primary/secondary = the deficit categories).
   - `INVESTIGATE_DATA_QUALITY` when the data itself conflicts (rationale `DATA_CONFLICT`).
   - `MAINTAIN_CURRENT_MIX` when there are no negative gaps (rationale `NO_NEGATIVE_GAPS`).
   - Some schemas instead require a single `recommended_action` with `action: REBALANCE_CAPACITY`,
     the deficit `category`, and an `owner_team` drawn from the prompt's teams.

**Output shape (conventional):** `scope`/`scope_id`, `included_work_item_ids`, `category_counts`,
`category_percentages`/`mix_table`/`gap_table`, `under_invested_categories`/`largest_deficit_category`,
`follow_up_action`/`recommended_action`, and exclusion fields (`excluded_duplicate_ids`,
`excluded_cancelled_ids`, `excluded_distractor_ids`, and/or
`ignored_mirror_status_and_legacy_category`). Match the template exactly.

**Ordering:** `included_work_item_ids` by `closed_at` ascending then id ascending; mix/gap tables in
fixed order NewFeature, TechDebt, Reliability, Security; under-invested from most-negative gap to
least; exclusion ID lists by the schema's stated order (usually closed_at then id, or ascending).

---

## §B. SLA-aging review

**Trigger:** the prompt names teams, an as-of date, a recent-closed window (days), and
reliability/security as the SLA categories.

**Inputs:**
- work items for the scope's teams, SLA-relevant (category `Reliability` or `Security`), primary
  only (duplicates excluded — `data_hygiene.md` §1, §7).
- `sla_policy` (severity → `days_to_due`).

**Computation:**
1. `included_primary_ids` = the primary SLA-relevant population in scope (closed within the recent
   window plus any still-open/overdue as-of, per the task's rule), sorted ascending.
2. `overdue_primary_ids` = subset past their SLA horizon as of the as-of date, sorted ascending.
3. **Aging buckets** (where the schema asks) — age in days of each included primary (basis per the
   task, typically `as_of − created_at`), binned into the schema's buckets (e.g.
   `0-3, 4-7, 8-14, 15-30, 31+`). Bucket counts sum to the included primary count.
4. **Overdue by severity** (where the schema asks) — `S1/S2/S3/S4` counts of overdue primaries;
   counts sum to the overdue count.
5. **Team overdue counts / top hotspot** (where the schema asks) — per-team overdue counts (teams
   alphabetical); `top_hotspot` = the team+owner pair with the most overdue primaries
   (`owner: "UNASSIGNED"` when missing).
6. **Escalation queue** (where the schema asks) — overdue primary ids in urgency/priority order
   (e.g. priority ascending, then severity, then id — per the task's stated priority order), not
   lexicographic.
7. `duplicate_clusters` — `{primary_id, duplicate_ids:[...]}`, sorted by `primary_id`, each
   `duplicate_ids` sorted ascending. Duplicates reported but **not** counted as primary.
8. `missing_owner_ids` — included primaries with `owner` null, sorted ascending.
9. `breach_rate` / `sla_breach_rate` = `overdue_primary_count ÷ included_primary_count`, exactly 3
   decimals.

**Output shape (conventional):** `scope` (`teams, as_of, recent_closed_window_days,
sla_categories`/`categories`), `included_primary_ids`, `overdue_primary_ids`,
`aging_bucket_counts` and/or `overdue_counts_by_severity`, `team_overdue_counts`/`top_hotspot`
and/or `escalation_queue_ids`, `duplicate_clusters`, `missing_owner_ids`, `breach_rate`/
`sla_breach_rate`. Match the template exactly — schemas vary in which of these they request.

---

## §C. Release-readiness assessment

**Trigger:** the prompt names a `release_id` and asks for a ship decision and readiness metrics.

**Inputs:**
- `GET /api/releases/{release_id}` (release + its milestones + its blockers), plus
  `GET /api/milestones`, `GET /api/dependencies`, `GET /api/blockers`, and the release's work items
  (work items whose `release_id` matches, or linked via `milestone_id`).
- Use **authoritative** work-item `status`; ignore stale mirror fields (`data_hygiene.md` §2).

**Computation:**
1. `milestone_completion` — for each milestone of this release (sorted by `milestone_id` ascending):
   `primary_total` = primary work items in the milestone; `complete_primary` = those with a
   terminal status; `completion_pct` = complete ÷ total × 100, to 1 decimal.
2. `gating_work_item_ids` — sorted unique **non-complete** release work items that gate readiness.
3. `blocker_cause_counts` — for **unresolved high-impact** blockers of this release
   (`resolved_at` is null **and** `severity` in {`High`,`Critical`}), count by exact `cause`
   string. Keys are the exact cause text.
4. `critical_dependency_chains` — ordered work-item-id paths from blocked release work following
   `dependencies` (`blocked_id` → `depends_on_id` → …) to a non-complete dependency. One array per
   chain; chains sorted lexicographically by the full path. Empty array when none exist.
5. `readiness_score` = total `complete_primary` ÷ total `primary_total` across the release's
   milestones, exactly 3 decimals.
6. `ship_decision` — one of `SHIP`, `SHIP_WITH_WATCH`, `NO_SHIP`, from readiness + unresolved
   high-impact blockers + gating items (apply the task's stated decision criteria; when blocked by
   unresolved high-impact blockers or below the readiness bar, `NO_SHIP`).

**Output shape (conventional):** `release_id`, `ship_decision`, `milestone_completion`,
`gating_work_item_ids`, `blocker_cause_counts`, `critical_dependency_chains`, `readiness_score`.
Match the template exactly.

**Ordering:** `milestone_completion` by `milestone_id` ascending; `gating_work_item_ids` sorted
ascending unique; `blocker_cause_counts` keys are exact cause strings; `critical_dependency_chains`
sorted lexicographically by full path; `readiness_score` to 3 decimals.
