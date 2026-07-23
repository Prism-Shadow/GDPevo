# Portfolio Mix Task

Produce a closed-work portfolio mix for a scope and compare it to a target mix.

## Inputs

- Scope: `scope_id`, `quarter`, teams, product areas (from the task prompt and
  the `mix_targets` row for that `scope_id`).
- Target mix: the `mix_targets` row whose `scope_id` matches. Its
  `new_feature_pct`, `tech_debt_pct`, `reliability_pct`, `security_pct` are
  **fractions** (e.g. `0.34`); convert to percentage points (`34.0`) for the
  answer.

## Step 1 — Build the included set

1. Filter work items to scope (teams AND product_area) with `closed_at` in the
   quarter. See `scope-and-exclusions.md`.
2. From those, keep only **closed/complete** status (`Closed`, `Done`,
   `Verified`, `Deployed`).
3. Exclude duplicates and cancelled records (report them separately).
4. The remainder is `included_work_item_ids`, ordered by `closed_at` asc then
   `id` asc. `total_included` = its length.

## Step 2 — Classify

Classify each included item via `classification.md` into NewFeature, TechDebt,
Reliability, Security.

## Step 3 — Counts and percentages

- `category_counts`: integer item counts per category (counts are **item
  counts, not story points**).
- `category_percentages` / `actual_pct`: `count / total_included * 100`,
  rounded to 1 decimal.

## Step 4 — Gap table

For each category in the fixed order **NewFeature, TechDebt, Reliability,
Security**:

- `target_pct`: target fraction × 100, 1 decimal.
- `actual_pct`: from step 3.
- `gap_pct` = `actual_pct − target_pct`, 1 decimal.

## Step 5 — Under-invested / deficit

- `under_invested_categories` / `largest_deficit_category`: categories with
  negative `gap_pct`, ordered from **most negative to least negative**. The
  first is the largest deficit. (Ties: break by the fixed category order
  NewFeature, TechDebt, Reliability, Security.)

## Step 6 — Follow-up / recommended action

Two template variants exist; follow the task's `answer_template.json`.

**Variant A — `follow_up_action` (action, primary_category,
secondary_category, rationale_code):**

- If no negative gaps: `action = MAINTAIN_CURRENT_MIX`,
  `primary_category = null`, `secondary_category = null`,
  `rationale_code = NO_NEGATIVE_GAPS`.
- If any negative gap: `action = REBALANCE_CAPACITY`,
  `primary_category` = largest-negative-gap category,
  `secondary_category` = largest-positive-gap category (the over-invested
  source to rebalance capacity from),
  `rationale_code = LARGEST_NEGATIVE_GAP`.
- `DATA_CONFLICT` / `INVESTIGATE_DATA_QUALITY` is for records where
  authoritative vs stale fields disagree in a way that blocks classification.

**Variant B — `recommended_action` (action, category, owner_team):**

- `action = REBALANCE_CAPACITY` (only allowed enum).
- `category` = `largest_deficit_category`.
- `owner_team` = the team in scope that **owns the deficit category** — i.e.
  the team with the most included items in that category (the team already
  doing that kind of work). Pick from the scope's teams.

## Step 7 — Exclusion flags

Report what was excluded, in the shape the template requires:

- Separate `excluded_duplicate_ids` and `excluded_cancelled_ids` (each a list),
  plus `ignored_mirror_status_and_legacy_category: true`.
- OR a combined `excluded_distractor_ids` (duplicates **and** cancelled),
  ordered by `closed_at` asc then `id` asc.

## Precision checklist

- All percentages and gaps: 1 decimal.
- `total_included`: integer.
- `included_work_item_ids`: each id used once, ordered closed_at asc then id asc.
- No extra fields; match the template's key names exactly.
