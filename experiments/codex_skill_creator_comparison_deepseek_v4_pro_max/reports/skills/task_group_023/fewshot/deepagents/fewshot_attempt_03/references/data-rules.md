# Data Resolution and Cohort Construction Rules

## Release Selection

### Health Data (State and County)

For each (entity_key, year, measure_id, value_type, source_type):

1. Filter to release_status = FINAL (unless protocol says otherwise)
2. Apply additional value_type and source_type filters from request
3. Select highest revision number among remaining rows
4. If tied, select latest released_at
5. If still tied, select lowest observation_id (lexicographic)

Selected row provides value, standard_error, sample_size, suppression_flag, quality_flag.

### Socioeconomic Data (State and County)

For each (entity_key, year):

1. Filter to release_status = FINAL
2. Select highest revision
3. If tied, latest released_at
4. If still tied, lowest record_id

### Country Indicators

For each (iso3, year, indicator_id):

1. Filter to release_status = FINAL
2. Select highest revision
3. If tied, latest released_at
4. If still tied, lowest observation_id

## Suppression and Missing Values

- suppression_flag = 1: value suppressed. Never treat as zero.
- Blank/null value with any flag: unavailable.
- Quality flags INVALID, WITHDRAWN, INVALID_SCALE: may designate exclusions.
- In cohort construction: suppressed/invalid/missing makes observation incomplete for affected variable.

## Release Counting

Count selected publications AFTER applying filters and revision selection but BEFORE checking analytic completeness (suppression/missingness).

## Revision Notices

From /download?dataset=revisions&format=csv:
- APPLIED: revision reflected in published FINAL records
- Other statuses (PENDING, WITHDRAWN): do not replace published values

## Cohort Construction

### Complete Case
All required analytic variables present, nonsuppressed, non-null, not quality-excluded.

### Core Balanced Panel
Entities complete for all core variables in every analysis year.

### Primary (Reference-Year) Cohort
Entities complete for required variables in reference year only.

### Broad Reference Cohort
Entities complete for outcome and all ordered features in reference year.

### Dual-Source / Strict Cohort
Entities complete for outcome, primary exposure, parallel exposure, and all adjustment variables in every analysis year.

## Geography Joins

- State data: join on state_abbr
- County data: join on county_fips (text: state_fips + 3-char county suffix)
- State geography provides region and division
- RUCC from county geography table
- Country data: iso3 as stable key

## Variable Transformations

- median_income per 10000: Divide by 10000
- log(median_income): Natural log of unscaled value
- RUCC dummies: RUCC2-RUCC9 as 0/1, RUCC1 reference
- Region dummies: Region_Midwest, Region_South, Region_West; Northeast = reference
- Census division: 9-level categorical group for cluster operations

## Panel Construction

1. Resolve each year independently
2. Join by stable entity key
3. Lagged variables: shift resolved values by required years
4. Change variables: difference between consecutive resolved years

## Numeric Precision

- Non-integers to declared decimal places (commonly 4 or 6)
- Counts, seeds, PRNG states, fold numbers, ranks as integers
- JSON null for mathematically unavailable results; never NaN or Infinity
