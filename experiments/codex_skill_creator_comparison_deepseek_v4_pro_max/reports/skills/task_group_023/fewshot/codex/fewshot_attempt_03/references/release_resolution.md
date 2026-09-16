# Release Resolution and Data Selection

## Priority rule for final releases

For each (entity, year, measure, value_type, source_type) combination where multiple FINAL rows exist:
1. Select the row with the greatest revision integer.
2. Among ties, select the latest released_at timestamp.
3. Among remaining ties, select the lowest observation_id or record_id.

Provisional rows are ignored when FINAL rows exist.

## Suppression and missing values

- suppression_flag = 1 means the value is suppressed (null/missing in publication).
- Invalid quality_flags (INVALID_SCALE, INVALID, WITHDRAWN) render a row unavailable.
- Suppressed, invalid, withdrawn, blank, or null analytic values are never zero-filled.
- A missing value in one field does not invalidate other non-missing fields in socioeconomic records.

## State health value types

- AGE_ADJUSTED: for state comparisons (remove age-structure confounding).
- CRUDE: observed values for county burden or coverage review.
- source_type: DIRECT_SURVEY (primary) or COUNTY_ROLLUP (parallel).
  DIRECT_SURVEY is the primary state publication series. COUNTY_ROLLUP should not silently replace direct records.

## County health

- All county health data uses CRUDE value_type (no AGE_ADJUSTED).
- Coverage: 2021-2024 (no 2020 data).

## Country data

- Country labels: requested labels may appear as portal_label or in the semicolon-delimited alternate_labels field of the countries geography reference. Resolve to stable iso3 identifiers.
- Revision events: APPLIED status means the revision is incorporated. PENDING or WITHDRAWN are not applied.
