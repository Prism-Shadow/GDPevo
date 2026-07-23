# PHO Portal Dataset Reference

## State Health (`/data/state-health`)
- **Rows**: ~4,861 | **Coverage**: 2020–2024
- **Columns**: observation_id, state_fips, state_abbr, year, measure_id, value_type, source_type, release_status, revision, value, standard_error, sample_size, suppression_flag, quality_flag, released_at
- **Filters**: state_abbr, measure_id, year, value_type, source_type, release_status, revision
- **Measures**: adult_obesity, adult_smoking, diagnosed_diabetes, food_insecurity, frequent_mental_distress, life_expectancy, physical_inactivity, premature_mortality_rate
- **value_type**: AGE_ADJUSTED, CRUDE
- **source_type**: DIRECT_SURVEY, COUNTY_ROLLUP
- **release_status**: FINAL, PROVISIONAL
- **quality_flag**: REVIEWED, PARALLEL_ESTIMATE, PROVISIONAL, SUPPRESSED, REVISED

## State Socioeconomic (`/data/state-socioeconomic`)
- **Rows**: ~323 | **Coverage**: 2020–2024
- **Columns**: record_id, state_fips, state_abbr, year, release_status, revision, released_at, poverty, bachelors, median_income, unemployment, uninsured, food_insecurity, population, quality_flag
- **Filters**: state_abbr, year, release_status, revision
- **51 states** (50 + DC) per year when FINAL

## County Health (`/data/county-health`)
- **Rows**: ~47,938 | **Coverage**: 2021–2024
- **Columns**: observation_id, county_fips, state_abbr, region, year, measure_id, value_type, release_status, revision, released_at, value, low_ci, high_ci, population, suppression_flag, quality_flag
- **No source_type column** (unlike state health)
- **Measures**: adult_obesity, adult_smoking, copd, depression, diagnosed_diabetes, physical_inactivity, severe_housing_cost_burden, short_sleep
- **value_type**: CRUDE only (no AGE_ADJUSTED for counties)

## County Socioeconomic (`/data/county-socioeconomic`)
- **Rows**: ~6,772 | **Coverage**: 2020–2024
- **Columns**: record_id, county_fips, state_abbr, region, year, release_status, revision, released_at, poverty, median_income, bachelors, unemployment, net_migration, uninsured, population, quality_flag

## Country Indicators (`/data/country-indicators`)
- **Rows**: ~9,812 | **Coverage**: 2013–2024
- **Columns**: observation_id, country_label, iso3, year, indicator_id, release_status, revision, released_at, value, unit, quality_flag
- **Indicators**: adult_mortality, alcohol_harm, bmi_burden, health_spending_gap, hiv_burden, immunization_gap, infant_mortality, life_expectancy, poverty_rate, schooling_gap, unemployment, urbanization

## States Reference (`/geographies/states`)
- **51 rows**: state_fips, state_abbr, state_name, region (South/West/Northeast/Midwest), division (9 Census divisions), is_state

## Counties Reference (`/geographies/counties`)
- **~1,224 rows**: county_fips, state_abbr, county_name, region, rucc (1-9), metro_class, population_base, latitude, longitude

## Countries Reference (`/geographies/countries`)
- **Up to 72 rows**: iso3, canonical_name, portal_label, alternate_labels (pipe-delimited), region, income_group

## Revisions (`/data/revisions`)
- **~130 rows**: revision_event_id, domain, entity_id, field_id, effective_year, old_value, new_value, status (APPLIED/PENDING/WITHDRAWN), issued_at, reason_code, note

## Census Divisions (9)
East North Central, East South Central, Middle Atlantic, Mountain, New England, Pacific, South Atlantic, West North Central, West South Central

## Census Regions (4)
Midwest, Northeast, South, West
