# Portfolio Mix Review

## Workflow

1. Read the target mix from `GET /api/mix-targets`. Match on the `scope_id`
   given in the task prompt.
2. Fetch all work items via `GET /api/work-items` or the SQL endpoint.
3. Filter to in-scope closed work items:
   - `status` is `closed` (use the authoritative status field, never `mirror_status`)
   - `team` matches one of the scoped teams
   - `closed_at` falls within the scoped quarter
4. Separate primary items from exclusions:
   - **Duplicate**: any item where `duplicate_of` is non-null. These are excluded
     from the primary count but recorded in `excluded_duplicate_ids`.
   - **Cancelled**: any item where `status` is `cancelled`. These are excluded
     from the primary count but recorded in `excluded_cancelled_ids` (or
     `excluded_distractor_ids` depending on the answer schema).
   - **Mirror/legacy**: ignore `mirror_status` and `mirror_category`; classify
     using the authoritative `category` field only. Set
     `ignored_mirror_status_and_legacy_category` to `true` when the answer
     schema asks for it.
5. Classify each primary item into exactly one portfolio category:
   - `NewFeature`
   - `TechDebt`
   - `Reliability`
   - `Security`

   Use the `category` field directly. When the schema defines conflicting
   signals (type, labels, title), resolve conflicts using the `category` field
   as the authoritative source, then `type`/`labels` as tiebreakers.
6. Compute count-based percentages:
   - `actual_pct = (category_count / total_included) * 100`
   - Round all percentages to **1 decimal place**.
7. Compute gap for each category:
   - `gap_pct = actual_pct - target_pct`
   - Round to 1 decimal place.
8. Determine under-invested categories:
   - Categories where `gap_pct < 0`, ordered from most negative to least
     negative.
9. Determine follow-up action:
   - If any negative gap exists: `REBALANCE_CAPACITY` with `primary_category`
     set to the category with the largest negative gap, `secondary_category`
     set to the next largest (or null if only one), and `rationale_code` of
     `LARGEST_NEGATIVE_GAP`.
   - If no negative gaps: `MAINTAIN_CURRENT_MIX` with null categories and
     `rationale_code` of `NO_NEGATIVE_GAPS`.

## Sorting

- `included_work_item_ids`: sort by `closed_at` ascending, then `id` ascending.
- `excluded_duplicate_ids`: sort by `closed_at` ascending, then `id` ascending.
- `excluded_cancelled_ids` / `excluded_distractor_ids`: sort by `closed_at`
  ascending, then `id` ascending.
- `gap_table` / `mix_table` rows: always in this fixed order: `NewFeature`,
  `TechDebt`, `Reliability`, `Security`.
- `under_invested_categories`: most negative `gap_pct` first.
- Team arrays: sort alphabetically.
