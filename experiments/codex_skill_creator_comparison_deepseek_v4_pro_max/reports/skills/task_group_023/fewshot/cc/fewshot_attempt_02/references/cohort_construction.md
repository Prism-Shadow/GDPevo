# Cohort Construction Rules

## Universal Principles

Every cohort is a subset of the resolved authoritative records. Build each
cohort independently from the analysis request specification; different
modules may use different cohorts and their construction logic does not mix.

**Entity code ordering**: State cohorts sort by state abbreviation ascending.
County cohorts sort by county FIPS ascending. Country cohorts sort by ISO3
ascending. Within each entity, rows sort by year ascending.

## Required-Field Completeness

A record is "complete" for a set of fields when every field in that set has
a nonsuppressed, non-null, non-blank value. Suppressed records (emdash,
suppression_flag=1) are excluded. Null values are excluded.

**Socioeconomic nuance**: Because socioeconomic fields are independently
revised (see methodology doc `socioeconomic-fields`), a null in a field that
is not in the required set does not disqualify an otherwise-complete record.

## Cohort Types

### Complete-Case Cohort (single year)

For a specified reference year, collect entities where every field in the
required set is non-missing and nonsuppressed for that year.

**Construction:**
1. For each entity, check if all required fields resolve to valid values
   for the reference year.
2. The resulting count is the number of entities with complete cases.
3. Entities without complete cases for that year are excluded.

### Balanced Panel Cohort

For a specified set of years, collect entities that are complete for every
required field in every requested year.

**Construction:**
1. For each entity, check completeness for each year independently.
2. An entity belongs to the balanced cohort only if it is complete in ALL
   requested years.
3. The balanced observation count = balanced_entity_count * year_count.

### Broad Reference Cohort

For the reference year, collect entities complete for an expanded set of
features. Used in ridge/elastic-net modules that need more predictors.

**Construction:**
1. The required field set includes all features declared in the module's
   `feature_order` plus the outcome variable.
2. Build as a single-year complete-case cohort on the reference year using
   this expanded set.

### Strict Dual-Source Cohort

Entities must be complete for an outcome, a primary exposure, a parallel
(alternate-source) exposure, and all adjustments in EVERY requested year.

**Construction:**
1. For each year, check that the primary exposure, parallel exposure,
   outcome, and all adjustment variables all resolve with non-missing values.
2. An entity is in the strict cohort only if it passes the completeness
   check in ALL requested years.
3. This is the most restrictive cohort type.

### Machine Learning Cohort

A variant of the primary cohort that additionally requires completeness on
extra columns (e.g., unemployment, net_migration, uninsured for the
reference year only).

**Construction:**
1. Start with primary (reference-year) complete-case cohort members.
2. Additionally require completeness on the specified extra columns for
   the same reference year.

## Census Division / Region Assignment

When a module groups by census division or region, the assignment comes
from `/geographies/states` for state-level work or from the `region` field
in county records for county-level work.

**Division order** for state-level analysis is alphabetical:
`East North Central`, `East South Central`, `Middle Atlantic`, `Mountain`,
`New England`, `Pacific`, `South Atlantic`, `West North Central`,
`West South Central`

**Region order** is alphabetical: `Midwest`, `Northeast`, `South`, `West`

## Excluded State Reporting

When reporting excluded states:
- List every state code from the universe (all 50 states + DC = 51) that
  is NOT in the cohort.
- Sort ascending (ASCII order).
- The count of excluded = 51 - cohort_count.

## County Cohort Details

County cohorts use `county_fips` as the stable entity identifier. When
checking completeness:
- Health values are nonsuppressed (value is not emdash, suppression_flag=0).
- Socioeconomic values are non-null.
- RUCC comes from the county geography reference; it must be an integer
  1-9 and non-null.

For county balanced panels, a county must have complete records for ALL
requested years AND all required fields each year.

## Country Cohort Details

Country cohorts use ISO3 as the stable entity identifier. The label
reconciliation step is critical:
1. Build the ISO3 mapping from `/geographies/countries`.
2. Resolve each requested label to its ISO3.
3. Pull indicator data for those ISO3 codes.
4. Apply revision-based anomaly detection before computing completeness.
