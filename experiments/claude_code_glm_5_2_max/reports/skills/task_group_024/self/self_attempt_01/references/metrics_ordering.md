# Metrics, rounding, and ordering

## Rounding
- **Percentage points** (`actual_pct`, `target_pct`, `gap_pct`, `completion_pct`): round to
  **1 decimal place**.
- **Rates** (`breach_rate`, `sla_breach_rate`, `readiness_score`): round to **exactly 3
  decimal places**.
- Counts are **item counts**, not story points — do not sum `story_points` for mix counts.
- `mix_targets` fractions are 0–1; **multiply by 100** to get percentage points before
  comparing, computing gaps, or reporting.

## Formulas
- `gap_pct` = `actual_pct` − `target_pct` (percentage points).
- `actual_pct` (per category) = `category_count` / `total_included` × 100.
- `under_invested_categories` = categories with negative `gap_pct`, ordered
  most-negative → least-negative.
- `largest_deficit_category` = category with the most-negative `gap_pct`.
- `breach_rate` / `sla_breach_rate` = `overdue_primary_count` / `included_primary_count`.
- `readiness_score` = `completed_primary_work` / `primary_denominator`.
- `completion_pct` (milestone) = `complete_primary` / `primary_total` × 100.
- **Overdue (SLA)** — a primary item is overdue when, as of the as-of date, it has exceeded
  its SLA due window: due = `created_at` (or `opened_at`) + `sla_policy.days_to_due[severity]`;
  compare against the as-of date (and the recent-closed window where the task defines one).
  Apply the task's exact overdue definition if it differs.

## Ordering
- ID lists: **ascending / lexicographic**, unless the template specifies
  **closed_at asc then id asc**.
- teams: **alphabetical** (or the explicit order a template states).
- categories: fixed order **NewFeature, TechDebt, Reliability, Security**.
- `milestone_completion`: by `milestone_id` ascending.
- `gating_work_item_ids`: sorted ascending, **unique**.
- `duplicate_clusters`: by `primary_id` ascending; `duplicate_ids` ascending within each.
- `critical_dependency_chains`: lexicographic by the **full path string**.
- Use each included id **exactly once**; no duplicates in any list.
