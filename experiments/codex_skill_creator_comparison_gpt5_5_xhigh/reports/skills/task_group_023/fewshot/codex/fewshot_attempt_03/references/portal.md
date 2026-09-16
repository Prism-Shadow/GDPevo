# PHO Portal Reference

Use the base URL supplied by the task prompt or environment note. Do not browse outside the PHO portal for evidence.

## Common Endpoints

- `/catalog`: dataset names, columns, filters, and measure dictionary.
- `/methodology`: current methodology notes for releases, suppression, identifiers, country labels, state direct/rollup estimates, RUCC, and quality flags.
- `/geographies/states`: state FIPS, abbreviation, name, region, division, and state flag.
- `/geographies/counties`: county FIPS, state, region, RUCC, metro class, population base, latitude, longitude.
- `/geographies/countries`: ISO3, canonical name, portal label, alternate labels, region, income group.
- `/data/state-health`, `/data/state-socioeconomic`, `/data/county-health`, `/data/county-socioeconomic`, `/data/country-indicators`, `/data/revisions`: browsable filtered tables.
- `/download?dataset=<dataset>&format=csv`: reliable full CSV download for solver scripts.

## Dataset Columns

`state_health`:
`observation_id`, `state_fips`, `state_abbr`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag`, `released_at`.

`state_socioeconomic`:
`record_id`, `state_fips`, `state_abbr`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `bachelors`, `median_income`, `unemployment`, `uninsured`, `food_insecurity`, `population`, `quality_flag`.

`county_health`:
`observation_id`, `county_fips`, `state_abbr`, `region`, `year`, `measure_id`, `value_type`, `release_status`, `revision`, `released_at`, `value`, `low_ci`, `high_ci`, `population`, `suppression_flag`, `quality_flag`.

`county_socioeconomic`:
`record_id`, `county_fips`, `state_abbr`, `region`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`, `uninsured`, `population`, `quality_flag`.

`country_indicators`:
`observation_id`, `country_label`, `iso3`, `year`, `indicator_id`, `release_status`, `revision`, `released_at`, `value`, `unit`, `quality_flag`.

`revisions`:
`revision_event_id`, `domain`, `entity_id`, `field_id`, `effective_year`, `old_value`, `new_value`, `status`, `issued_at`, `reason_code`, `note`.

## Release Resolution

1. Apply request filters first: domain, measure/indicator/field, entity scope, years, source type, value type, release status, revision if declared, and any suppression/quality requirement.
2. Group by the stable publication key declared or implied by the request, usually entity id plus year plus measure/source/value type.
3. Select one record per key using the effective priority order. If the request names the priority fields, use that order exactly. If a protocol profile supplies a tie rule, use the profile's ascending/descending direction exactly.
4. Keep selected records with suppressed or missing analytic values in publication counts, but exclude them from complete-case cohorts.
5. Preserve identifiers as text. FIPS leading zeros are meaningful.

Quality and missingness:

- `suppression_flag` set to true/one means the analytic value is unavailable.
- Blank strings, JSON null-equivalents in CSV, and nonnumeric analytic values are unavailable.
- Invalid quality flags named by the request are unavailable. Common invalid flags in these audits include `INVALID`, `INVALID_SCALE`, and `WITHDRAWN`.
- Country scale-break or anomaly flags are audit evidence. Count and list unresolved anomaly cells when the template asks; exclude those cells before imputation or modeling.

## Cohort Construction

- Construct cohorts from selected records, not raw duplicated releases.
- State analyses commonly require 51-jurisdiction universes, reference-year complete cases, all-year balanced panels, or dual-source strict cohorts.
- County analyses commonly join selected health, selected socioeconomic, and county geography by `county_fips`, then require region, RUCC, requested measures, and panel years to be complete.
- Country analyses reconcile requested labels to ISO3 using canonical name, portal label, and alternate labels before selecting country indicator cells.
- When aggregating counties to states, compute the requested state-year means or counts only from the eligible county rows in the effective cohort.

## Ordering

- Use declared order from the request/template whenever present.
- If no order is declared, use stable entity-code order for aligned arrays: `state_abbr`, `county_fips`, then `iso3`.
- For groups such as census divisions, use the request's registered division order or the order implied by the geography table/template. Do not alphabetize an aligned result independently after computing it.
- For set-like audit lists explicitly described as sorted, sort unique identifiers ascending ASCII.
