# Public Health Observatory Data Portal API Reference

## Base URL

`http://task-env:9023/`

The portal serves browsable HTML tables with filter forms and downloadable CSV exports for every dataset. JSON endpoints are not provided; all structured data retrieval must use the `/download` CSV endpoints.

## Datasets

### State Health (`state_health`)

Endpoints: `/data/state-health` (HTML), `/download?dataset=state_health&format=csv` (CSV)

Filter parameters: `state_abbr`, `measure_id`, `year`, `value_type`, `source_type`, `release_status`, `revision`

CSV columns: `observation_id`, `state_fips`, `state_abbr`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag`, `released_at`

Measure IDs: `life_expectancy`, `adult_obesity`, `adult_smoking`, `diagnosed_diabetes`, `physical_inactivity`, `frequent_mental_distress`, `food_insecurity`, `premature_mortality_rate`

Value types: `AGE_ADJUSTED`, `CRUDE`
Source types: `DIRECT_SURVEY`, `COUNTY_ROLLUP`
Release statuses: `FINAL`, `PROVISIONAL`
Quality flags: `REVIEWED`, `REVISED`, `SUPPRESSED`, `PROVISIONAL`, `PARALLEL_ESTIMATE`
Suppression flag: 0 (not suppressed), 1 (suppressed; value displayed as em dash in HTML, empty in CSV)

### State Socioeconomic (`state_socioeconomic`)

Endpoints: `/data/state-socioeconomic` (HTML), `/download?dataset=state_socioeconomic&format=csv`

Filter parameters: `state_abbr`, `year`, `release_status`, `revision`

CSV columns: `record_id`, `state_fips`, `state_abbr`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `bachelors`, `median_income`, `unemployment`, `uninsured`, `food_insecurity`, `population`, `quality_flag`

Note: Socioeconomic `food_insecurity` is distinct from state-health `food_insecurity` -- it is the socioeconomic release from a different source.

### County Health (`county_health`)

Endpoints: `/data/county-health` (HTML), `/download?dataset=county_health&format=csv`

Filter parameters: `state_abbr`, `county_fips`, `measure_id`, `year`, `value_type`, `source_type`, `release_status`, `revision`

CSV columns: `observation_id`, `state_fips`, `county_fips`, `state_abbr`, `county_name`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag`, `released_at`

### County Socioeconomic (`county_socioeconomic`)

Endpoints: `/data/county-socioeconomic` (HTML), `/download?dataset=county_socioeconomic&format=csv`

Filter parameters: `state_abbr`, `county_fips`, `year`, `release_status`, `revision`

CSV columns: `record_id`, `state_fips`, `county_fips`, `state_abbr`, `county_name`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `unemployment`, `median_income`, `net_migration`, `uninsured`, `population`, `quality_flag`

### Country Indicators (`country_indicators`)

Endpoints: `/data/country-indicators` (HTML), `/download?dataset=country_indicators&format=csv`

Filter parameters: `iso3`, `indicator_id`, `year`, `release_status`, `revision`

CSV columns: `observation_id`, `iso3`, `year`, `indicator_id`, `release_status`, `revision`, `value`, `quality_flag`, `released_at`

Indicator IDs: `adult_mortality`, `bmi_burden`, `health_spending_gap`, `hiv_burden`, `immunization_gap`, `infant_mortality`, `poverty_rate`, `schooling_gap`, `life_expectancy`

### Revision Notices (`revisions`)

Endpoints: `/data/revisions` (HTML), `/download?dataset=revisions&format=csv`

Filter parameters: `revision_event_id`, `dataset`, `release_status`

CSV columns: `revision_event_id`, `dataset`, `measure_or_field`, `scope`, `revision_type`, `release_status`, `summary`, `released_at`

### Geography References

#### States

Endpoints: `/geographies/states` (HTML), `/download?dataset=states&format=csv`

Columns: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`

Regions: `West`, `Midwest`, `South`, `Northeast`
Divisions: `Pacific`, `Mountain`, `West North Central`, `West South Central`, `East North Central`, `East South Central`, `New England`, `Middle Atlantic`, `South Atlantic`
Total: 51 rows (50 states + DC)

#### Counties

Endpoints: `/geographies/counties` (HTML), `/download?dataset=counties&format=csv`

Columns: `state_fips`, `county_fips`, `state_abbr`, `county_name`, `rucc`
RUCC: integer 1-9. 1-3 metropolitan, 4-9 nonmetropolitan.

#### Countries

Endpoints: `/geographies/countries` (HTML), `/download?dataset=countries&format=csv`

Columns: `iso3`, `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group`
72 rows. Regions: `Africa`, `Americas`, `Asia`, `Europe`, `Middle East`, `Oceania`
Income groups: `LOW`, `LOWER_MIDDLE`, `UPPER_MIDDLE`, `HIGH`

### Methodology

Endpoint: `/methodology` (HTML); `/methodology?doc=<doc-id>` (individual doc)

Key docs: `release-lifecycle`, `publication-values`, `suppression`, `quality`, `state-estimates`, `aliases`, `rucc`, `socioeconomic-fields`, `geographic-ids`, `country-revisions`, `indicator-direction`, `county-windows`, `influence`

## CSV Download Pattern

```
curl -s "http://task-env:9023/download?dataset=<name>&format=csv&<filters>"
```

Parse with Python `csv.DictReader`. CSV download returns all matching rows (no pagination).

## HTML Parsing Fallback

If CSV download fails, parse HTML tables. Suppressed values display as em dash; treat as missing/None.

## Data Characteristics

- Missing values: empty in CSV, em dash in HTML. Never zero-fill.
- Revision numbers: higher supersedes lower for same release_status.
- released_at: ISO-8601.
- Multiple FINAL records may exist per key; select: highest revision, then latest released_at, then lowest observation_id/record_id.
- sample_size can differ across value_types and source_types.
- State socioeconomic food_insecurity is separate from state health food_insecurity.
