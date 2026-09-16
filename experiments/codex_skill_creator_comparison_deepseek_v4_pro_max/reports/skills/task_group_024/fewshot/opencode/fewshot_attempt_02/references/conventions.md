## Sorting and Precision Conventions

### ID Sorting

- Work item IDs: lexicographic (ASCII) sort ascending. Example: `WI-24024-A005`
  before `WI-24024-B003`, `WI-24024-X001` before `WI-24024-X010`.
- Milestone IDs: lexicographic ascending.
- Duplicate cluster sort: by `primary_id` ascending, with the `duplicate_ids`
  array sorted lexicographically inside each cluster.

### Team Sorting

- Team names: alphabetical ascending (A-Z).

### Category Ordering

- Portfolio categories always appear in this fixed order:

  ```
  NewFeature, TechDebt, Reliability, Security
  ```

- Gap tables, mix tables, category_counts, and category_percentages must list
  rows/keys in this order.

### Under-Invested / Deficit Ordering

- When listing under-invested categories, order from the most negative gap
  (largest deficit) to the least negative gap.

### Escalation Queue Ordering

- For SLA escalation queues, order overdue primary items by priority:
  1. Severity descending (S1 first, then S2, S3, S4).
  2. Within the same severity, by `created_at` ascending (oldest first).
  3. Within the same created_at, by ID ascending.

### Precision Rules

- **Percentages** (completion_pct, actual_pct, target_pct, gap_pct): round to
  exactly 1 decimal place. Do not round to integer. Values like 11.111... become
  11.1, not 11 or 11.11.
- **Rates** (breach_rate, readiness_score): round to exactly 3 decimal places.
  Values like 0.454545... become 0.455.
- **Counts**: always integers.
- **Gap calculation**: `gap_pct = actual_pct - target_pct`. All three values
  are in percentage points, not decimals. A gap of -30.9 means the category is
  under-invested by 30.9 percentage points.
