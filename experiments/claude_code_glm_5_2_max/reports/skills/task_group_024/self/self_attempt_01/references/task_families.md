# Task families

Three families share the entry procedure in `SKILL.md`; each has a different deliverable
shape. Map the template's required fields to the relevant checklist. (Train task ids are
listed only as exemplars of each family.)

## 1. Portfolio mix  (exemplars: train_001, train_004)
Goal: count-based mix of closed in-scope **primary** work vs a target mix, plus a rebalance
signal.
- Scope: teams, quarter, product_area, scope_id. Target mix = the `mix_targets` row whose
  `scope_id` matches the task's scope_id.
- `included_work_item_ids`: primary, closed, in-scope, classified. Order per template
  (closed_at asc then id asc).
- `category_counts`: item counts per category (not story points).
- mix/gap table: `actual_pct`, `target_pct` (from `mix_targets` ×100), `gap_pct`. Row order
  NewFeature, TechDebt, Reliability, Security.
- `under_invested_categories` / `largest_deficit_category`: negative gaps.
- `recommended_action` / `follow_up_action`: controlled vocab from template enums (e.g.
  `REBALANCE_CAPACITY`; rationale `LARGEST_NEGATIVE_GAP` / `NO_NEGATIVE_GAPS` / `DATA_CONFLICT`).
- exclusions: `excluded_duplicate_ids`, `excluded_cancelled_ids`, `excluded_distractor_ids`
  (and `ignored_mirror_status_and_legacy_category: true` where present).

## 2. SLA aging / breach  (exemplars: train_002, train_005)
Goal: SLA-relevant (Reliability + Security) primary work; overdue items, aging, breach rate,
escalation.
- Scope: teams, `as_of`, `recent_closed_window_days`, categories (Reliability/Security).
- `included_primary_ids`: SLA-relevant primary work, sorted.
- `overdue_primary_ids`: subset exceeding the SLA due window.
- `aging_bucket_counts`: `0-3`, `4-7`, `8-14`, `15-30`, `31+` (bucket by age in days; use the
  task's age basis).
- `team_overdue_counts` and/or `overdue_counts_by_severity` (S1–S4).
- `top_hotspot`: team + owner pair with the most overdue primary records; `owner` =
  `UNASSIGNED` when owner is missing.
- `duplicate_clusters`: reported, **not** counted.
- `missing_owner_ids` (and/or missing-owner primary IDs).
- `escalation_queue_ids`: overdue primary ids in escalation/priority order (use the task's
  stated order — typically severity, then priority, then due date).
- `breach_rate` / `sla_breach_rate`: 3 decimals.

## 3. Release readiness  (exemplar: train_003)
Goal: ship decision for a release, built from authoritative release/milestone/blocker/
dependency data.
- `release_id` from the prompt. Build truth from `releases`, `milestones`, `blockers`,
  `dependencies` + work-item `status` — **not** mirror fields.
- `ship_decision`: `SHIP` / `SHIP_WITH_WATCH` / `NO_SHIP`.
- `milestone_completion`: per milestone, `complete_primary` / `primary_total` and
  `completion_pct` (1 dp); sort by `milestone_id` asc.
- `gating_work_item_ids`: sorted unique non-complete release work items gating readiness.
- `blocker_cause_counts`: **unresolved high-impact** blockers only, keyed by exact cause
  string.
- `critical_dependency_chains`: ordered work-item-id paths from blocked release work to a
  non-complete dependency; sort lexicographically by full path.
- `readiness_score`: completed primary / primary denominator, 3 decimals.
