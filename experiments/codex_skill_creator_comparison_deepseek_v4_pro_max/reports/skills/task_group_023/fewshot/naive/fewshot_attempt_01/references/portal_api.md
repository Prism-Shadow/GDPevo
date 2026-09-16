# PHO Portal API Reference

## Base URL

The portal runs at the address replacing `<TASK_ENV_BASE_URL>` in the task prompt. All endpoints are read-only GET. Response bodies are JSON arrays of objects.

## Geography Endpoints

### GET /geographies/states
Returns state geography records.
Fields: `state_abbr` (uppercase 2-letter), `state_name`, `census_division`, `census_region`, `fips_code`.

### GET /geographies/counties
Returns county geography records.
Fields: `county_fips` (5-digit string), `county_name`, `state_abbr`, `rucc` (integer 1-9), `census_division`, `census_region`.

### GET /geographies/countries
Returns country geography records.
Fields: `iso3` (uppercase 3-letter), `label`, `region`, `sub_region`, `income_group`.

Canonical country label resolution: a requested label that differs from the canonical `label` field is an alias. Resolve aliases by matching against `label`; if a requested label does not match any record's `label` exactly, look for partial matches or known name variants. The `iso3` is the stable identifier for cross-walking.

## Data Endpoints

### GET /data/state-health
State-level health indicators. One record per observation.
Fields: `measure_id`, `year`, `state_abbr`, `value` (numeric), `value_type` (e.g. `AGE_ADJUSTED`, `CRUDE`), `source_type` (e.g. `DIRECT_SURVEY`, `COUNTY_ROLLUP`), `release_status` (e.g. `FINAL`, `PROVISIONAL`), `revision` (integer), `released_at` (ISO datetime), `observation_id`, `sample_size` (integer), `quality_flag` (string or null).

Common `measure_id` values: `life_expectancy`, `adult_obesity`, `adult_smoking`, `diagnosed_diabetes`, `physical_inactivity`, `frequent_mental_distress`, `food_insecurity`, `premature_mortality_rate`.

### GET /data/state-socioeconomic
State-level socioeconomic data. One record per observation.
Fields: `measure_id` or field-specific keys (`poverty`, `median_income`, `bachelors`, `unemployment`, `uninsured`), `year`, `state_abbr`, `value` (numeric), `release_status`, `revision`, `released_at`, `record_id`.

Common fields: `poverty` (percent), `median_income` (dollars), `bachelors` (percent with bachelor's degree), `unemployment` (percent), `uninsured` (percent uninsured), `region` (census region name).

### GET /data/county-health
County-level health indicators.
Fields: `measure_id`, `year`, `county_fips`, `state_abbr`, `value`, `value_type`, `source_type`, `release_status`, `revision`, `released_at`, `observation_id`, `sample_size`, `quality_flag`.

### GET /data/county-socioeconomic
County-level socioeconomic data.
Fields: `poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`, `uninsured`, `year`, `county_fips`, `state_abbr`, `release_status`, `revision`, `released_at`, `record_id`.

`net_migration` may be per-1000 or raw count depending on the portal version. For `median_income_per_10000`, divide raw `median_income` by 10000.

### GET /data/country-indicators
Country-level burden and health indicators.
Fields: `iso3`, `year`, `indicator_id`, `value` (numeric), `release_status`, `revision`, `released_at`, `record_id`, `quality_flag`, `scale_description`.

Common `indicator_id` values: `adult_mortality`, `bmi_burden`, `health_spending_gap`, `hiv_burden`, `immunization_gap`, `infant_mortality`, `life_expectancy`, `poverty_rate`, `schooling_gap`.

Country-indicator records with non-null `scale_description` represent a scale break. Such records are anomalous: their values are not comparable to the main series and should be excluded from analysis (marked as anomaly observation keys). They count toward `anomaly_2022_cells` / `anomaly_observation_keys` reporting.

### GET /data/revisions
Revision event records.
Fields: `revision_event_id` (string), `status` (e.g. `APPLIED`, `SUPERSEDED`, `WITHDRAWN`), `applies_to` (measure/geography scope description), `released_at`.

### GET /catalog
Schema catalog listing available measures, their geographic levels, value types, and source types.

### GET /methodology
Methodological notes.

### GET /download
Data download endpoint.

### GET /health
Service health check. Returns status.

## Query Patterns

1. Fetch all records for a geography level, then filter client-side by the effective request parameters.
2. For health data, filter by `measure_id`, `year` range, `value_type`, `source_type`, and `release_status`.
3. For socioeconomic data, filter by `year` range and `release_status`.
4. After filtering, apply revision selection within each entity-time-measure key group.
5. Join different data series by entity code and year.

## Numeric Conversions

- `median_income_per_10000`: divide `median_income` by 10000
- `log(median_income)`: natural log of unscaled `median_income`
- `log(diagnosed_diabetes_sample_size)`: natural log of `sample_size`
- `sample_size` from health records is the reliability weight when requested
