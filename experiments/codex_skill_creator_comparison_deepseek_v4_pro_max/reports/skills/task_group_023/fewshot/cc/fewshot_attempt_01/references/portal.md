# Public Health Observatory Portal Reference

The portal is a read-only web application serving health, socioeconomic, geography, and revision data. All data is browsable as HTML tables and downloadable as CSV.

## Base URL

Provided by the task environment, typically `http://task-env:9023/`.

## Endpoints

### Home and catalog

- `GET /` — landing page with navigation and release notices.
- `GET /catalog` — full dataset catalog with row counts, column schemas, and measure dictionary.

### Geography references

- `GET /geographies/states` — 51 rows (50 states + DC). Columns: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`. Filters: `state_abbr`, `state_fips`, `region`, `division`.
- `GET /geographies/counties` — 1,224 rows. Columns: `county_fips`, `state_abbr`, `county_name`, `region`, `rucc`, `metro_class`, `population_base`, `latitude`, `longitude`. Filters: `county_fips`, `state_abbr`, `region`, `rucc`, `metro_class`.
- `GET /geographies/countries` — 72 rows. Columns: `iso3`, `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group`. Filters: `iso3`, `label`, `region`, `income_group`.

### Health data

- `GET /data/state-health` — ~4,861 rows, coverage 2020–2024. Columns: `observation_id`, `state_fips`, `state_abbr`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag`, `released_at`. Filters: `state_abbr`, `measure_id`, `year`, `value_type`, `source_type`, `release_status`, `revision`.

  State-level measures: `adult_obesity`, `adult_smoking`, `diagnosed_diabetes`, `food_insecurity`, `frequent_mental_distress`, `life_expectancy`, `physical_inactivity`, `premature_mortality_rate`.

- `GET /data/county-health` — ~47,938 rows, coverage 2021–2024. Columns: `observation_id`, `county_fips`, `state_abbr`, `region`, `year`, `measure_id`, `value_type`, `release_status`, `revision`, `released_at`, `value`, `low_ci`, `high_ci`, `population`, `suppression_flag`, `quality_flag`. Filters: `county_fips`, `state_abbr`, `region`, `measure_id`, `year`, `value_type`, `release_status`, `revision`, `suppression_flag`.

  County-level measures: `adult_obesity`, `adult_smoking`, `copd`, `depression`, `diagnosed_diabetes`, `physical_inactivity`, `severe_housing_cost_burden`, `short_sleep`.

- `GET /data/country-indicators` — ~9,812 rows, coverage 2013–2024. Columns: `observation_id`, `country_label`, `iso3`, `year`, `indicator_id`, `release_status`, `revision`, `released_at`, `value`, `unit`, `quality_flag`. Filters: `iso3`, `country_label`, `indicator_id`, `year`, `release_status`, `revision`, `quality_flag`.

### Socioeconomic data

- `GET /data/state-socioeconomic` — 323 rows, coverage 2020–2024. Columns: `record_id`, `state_fips`, `state_abbr`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `bachelors`, `median_income`, `unemployment`, `uninsured`, `food_insecurity`, `population`, `quality_flag`. Filters: `state_abbr`, `year`, `release_status`, `revision`.

- `GET /data/county-socioeconomic` — 6,772 rows, coverage 2020–2024. Columns: `record_id`, `county_fips`, `state_abbr`, `region`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`, `uninsured`, `population`, `quality_flag`. Filters: `county_fips`, `state_abbr`, `region`, `year`, `release_status`, `revision`.

### Revisions

- `GET /data/revisions` — 130 rows, coverage 2015–2024. Columns: `revision_event_id`, `domain`, `entity_id`, `field_id`, `effective_year`, `old_value`, `new_value`, `status`, `issued_at`, `reason_code`, `note`. Filters: `domain`, `entity_id`, `field_id`, `effective_year`, `status`.

### Methodology

- `GET /methodology` — index of methodology documents. Append `?doc=<name>` to view a specific document.

### Download

- `GET /download?dataset=<name>&format=csv` — returns the full dataset as CSV. Valid dataset names: `states`, `counties`, `countries`, `state_health`, `state_socioeconomic`, `county_health`, `county_socioeconomic`, `country_indicators`, `revisions`.

**Always prefer CSV download over HTML browsing for analytic work.** The portal returns all rows in one call via the download endpoint; HTML pages require pagination and parsing.

## Value types and source types

- `value_type`: `AGE_ADJUSTED` or `CRUDE`. Age-adjusted values support state comparisons. Crude values describe observed county burden and retain each county's population structure.
- `source_type`: `DIRECT_SURVEY` (primary publication series), `COUNTY_ROLLUP` (parallel diagnostic for coverage review). Never substitute rollup for direct unless a perturbation module explicitly authorizes it.

## Release status and revision precedence

- Records have `release_status` of `FINAL` or `PROVISIONAL`, and a numeric `revision` (0 = original, 1+ = revised).
- Selection priority: greatest FINAL revision, then latest `released_at`, then lowest observation/record identifier.
- Ignore PROVISIONAL records when a FINAL record exists for the same entity-time-measure key.
- A PROVISIONAL record that has no corresponding FINAL record is still not a publication-grade observation.

## Suppression and quality flags

- `suppression_flag=1` means the value is suppressed (shown as an em dash in HTML). The record metadata remains but the numeric value is unavailable.
- `quality_flag` values: `REVIEWED`, `PROVISIONAL`, `PARALLEL_ESTIMATE`, `SUPPRESSED`, `INVALID_SCALE`, `INVALID`, `WITHDRAWN`. Treat flags listed in the request's invalid set as making that field's value unavailable.
- Never zero-fill suppressed or invalid values. A suppressed record still counts as a selected publication when the request asks for row counts before completeness filtering.

## Country label reconciliation

- Country records have a `portal_label` that may differ from the `canonical_name`. The `alternate_labels` column (semicolon-delimited) maps aliases to the canonical ISO3 identifier.
- Resolve requested labels to ISO3 identifiers via exact match on `portal_label`, `canonical_name`, or any entry in `alternate_labels`. Labels are case-sensitive.

## Geography reference

- State FIPS are 2-character text with leading zero (e.g., `02` for AK).
- County FIPS are 5-character text: 2-char state prefix + 3-char county suffix.
- Census divisions (ordered): `New England`, `Middle Atlantic`, `East North Central`, `West North Central`, `South Atlantic`, `East South Central`, `West South Central`, `Mountain`, `Pacific`.
- Census regions: `Northeast`, `Midwest`, `South`, `West`.
- RUCC values 1–3 are metropolitan; 4–9 are nonmetropolitan.
- State codes are two-letter uppercase abbreviations.

## Measure dictionary

| Domain | measure_id | Unit | Direction |
|---|---|---|---|
| COUNTRY | adult_mortality | deaths per 100,000 | HIGHER_WORSE |
| COUNTRY | bmi_burden | percent | HIGHER_WORSE |
| COUNTRY | health_spending_gap | percent | HIGHER_WORSE |
| COUNTRY | hiv_burden | percent | HIGHER_WORSE |
| COUNTRY | immunization_gap | percent | HIGHER_WORSE |
| COUNTRY | infant_mortality | deaths per 1,000 | HIGHER_WORSE |
| COUNTRY | life_expectancy | years | HIGHER_BETTER |
| COUNTRY | poverty_rate | percent | HIGHER_WORSE |
| COUNTRY | schooling_gap | percent | HIGHER_WORSE |
| STATE_HEALTH | adult_obesity | percent | HIGHER_WORSE |
| STATE_HEALTH | adult_smoking | percent | HIGHER_WORSE |
| STATE_HEALTH | diagnosed_diabetes | percent | HIGHER_WORSE |
| STATE_HEALTH | food_insecurity | percent | HIGHER_WORSE |
| STATE_HEALTH | frequent_mental_distress | percent | HIGHER_WORSE |
| STATE_HEALTH | life_expectancy | years | HIGHER_BETTER |
| STATE_HEALTH | physical_inactivity | percent | HIGHER_WORSE |
| STATE_HEALTH | premature_mortality_rate | deaths per 100,000 | HIGHER_WORSE |
| COUNTY_HEALTH | adult_obesity | percent | HIGHER_WORSE |
| COUNTY_HEALTH | diagnosed_diabetes | percent | HIGHER_WORSE |
| COUNTY_HEALTH | physical_inactivity | percent | HIGHER_WORSE |
