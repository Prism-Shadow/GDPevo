# Portal API Reference

The Public Health Observatory portal provides read-only access to surveillance, socioeconomic, geography, and revision data. All endpoints are GET requests returning HTML tables or CSV downloads.

Base URL: provided by the task prompt, typically `<TASK_ENV_BASE_URL>`.

## Endpoints

### Metadata

- `GET /` — Portal home with dataset listings
- `GET /catalog` — Dataset catalog with column descriptions and row counts
- `GET /methodology` — Methodology documents index
- `GET /methodology?doc=<doc-id>` — Individual methodology document

### Geography

- `GET /geographies/states` — 51 rows (50 states + DC). Columns: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`. Filters: `state_abbr`, `state_fips`, `region`, `division`.
- `GET /geographies/counties` — 1,224 rows. Columns: `county_fips`, `state_abbr`, `county_name`, `region`, `rucc`, `metro_class`, `population_base`, `latitude`, `longitude`. Filters: `county_fips`, `state_abbr`, `region`, `rucc`, `metro_class`.
- `GET /geographies/countries` — 72 rows. Columns: `iso3`, `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group`. Filters: `iso3`, `label`, `region`, `income_group`.

### Health data

- `GET /data/state-health` — ~4,861 rows, 2020–2024. Columns: `observation_id`, `state_fips`, `state_abbr`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag`, `released_at`. Filters: `state_abbr`, `measure_id`, `year`, `value_type`, `source_type`, `release_status`, `revision`.
- `GET /data/county-health` — ~47,938 rows, 2021–2024. Columns: `observation_id`, `county_fips`, `state_abbr`, `region`, `year`, `measure_id`, `value_type`, `release_status`, `revision`, `released_at`, `value`, `low_ci`, `high_ci`, `population`, `suppression_flag`, `quality_flag`. Filters: `county_fips`, `state_abbr`, `region`, `measure_id`, `year`, `value_type`, `release_status`, `revision`, `suppression_flag`.

### Socioeconomic data

- `GET /data/state-socioeconomic` — ~323 rows, 2020–2024. Columns: `record_id`, `state_fips`, `state_abbr`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `bachelors`, `median_income`, `unemployment`, `uninsured`, `food_insecurity`, `population`, `quality_flag`. Filters: `state_abbr`, `year`, `release_status`, `revision`.
- `GET /data/county-socioeconomic` — ~6,772 rows, 2020–2024. Columns: `record_id`, `county_fips`, `state_abbr`, `region`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`, `uninsured`, `population`, `quality_flag`. Filters: `county_fips`, `state_abbr`, `region`, `year`, `release_status`, `revision`.

### Country data

- `GET /data/country-indicators` — ~9,812 rows, 2013–2024. Columns: `observation_id`, `country_label`, `iso3`, `year`, `indicator_id`, `release_status`, `revision`, `released_at`, `value`, `unit`, `quality_flag`. Filters: `iso3`, `country_label`, `indicator_id`, `year`, `release_status`, `revision`, `quality_flag`.

### Revisions

- `GET /data/revisions` — 130 rows. Columns: `revision_event_id`, `domain`, `entity_id`, `field_id`, `effective_year`, `old_value`, `new_value`, `status`, `issued_at`, `reason_code`, `note`. Filters: `domain`, `entity_id`, `field_id`, `effective_year`, `status`.

### Downloads

- `GET /download?dataset=<name>&format=csv` — CSV export. Add filter params (same as browse endpoints) to subset. Datasets: `states`, `counties`, `countries`, `state_health`, `state_socioeconomic`, `county_health`, `county_socioeconomic`, `country_indicators`, `revisions`.

## Retrieval strategy

For each dataset needed, use the CSV download endpoint with appropriate filters to minimize data transfer. Parse CSV with Python's `csv` module. HTML table parsing is a fallback when CSV is unavailable — use BeautifulSoup or manual parsing.

Query strategy for a typical state audit:
1. Download `states` CSV for geography reference
2. Download `state_health` CSV with needed `measure_id` and `year` filters
3. Download `state_socioeconomic` CSV with needed `year` filters

Query strategy for a typical county audit:
1. Download `counties` CSV with `state_abbr` or `region` filters
2. Download `county_health` CSV with needed filters
3. Download `county_socioeconomic` CSV with needed filters
4. Download `states` CSV for state-level geography

## Important data properties

- `state_fips` and `county_fips` are TEXT with leading zeros
- `suppression_flag` = 1 means value is suppressed (null)
- `quality_flag`: `INVALID_SCALE`, `INVALID`, `WITHDRAWN` values should be excluded
- `release_status`: `FINAL` supersedes `PROVISIONAL`
- `value_type` for state health: `AGE_ADJUSTED` or `CRUDE`
- `source_type` for state health: `DIRECT_SURVEY` or `COUNTY_ROLLUP`
- County health does not have `source_type`; `value_type` is always `CRUDE`
- `rucc` is integer 1–9 on the county geography reference
- Country `portal_label` may differ from `canonical_name`; reconcile using `iso3` and `alternate_labels`
