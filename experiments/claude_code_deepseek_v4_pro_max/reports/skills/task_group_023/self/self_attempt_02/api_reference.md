# PHO Portal API Reference

Base URL: `http://task-env:9023/`

## Endpoints

### `GET /`
Portal health check. Returns server status and available endpoint listing.

### `GET /catalog`
Returns the data catalog as a JSON object describing every available measure.

Response fields per measure:
- `measure_id` — internal identifier string
- `title` — human-readable name
- `value_types` — array of available value types (e.g., `"AGE_ADJUSTED"`, `"CRUDE"`)
- `source_types` — array of available source types (e.g., `"DIRECT_SURVEY"`, `"COUNTY_ROLLUP"`)
- `geography_level` — `"state"`, `"county"`, or `"country"`
- `years_available` — array of integer years

### `GET /geographies/states`
Returns all US states and DC.

Response fields per state:
- `state_code` — two-letter uppercase code (e.g., `"AL"`, `"CA"`, `"DC"`)
- `state_name` — full name
- `census_division` — census division name
- `region` — census region name (`"Northeast"`, `"Midwest"`, `"South"`, `"West"`)

### `GET /geographies/counties`
Returns all US counties.

Response fields per county:
- `fips_code` — 5-digit string
- `county_name` — county name
- `state_code` — two-letter state code
- `rucc` — integer 1–9 (Rural-Urban Continuum Code)
- `census_division` — census division
- `region` — census region

### `GET /geographies/countries`
Returns all tracked countries.

Response fields per country:
- `iso3` — uppercase 3-letter code
- `country_name` — canonical name
- `aliases` — array of alternative label strings
- `region` — world region
- `sub_region` — sub-region

### `GET /data/state-health`
Returns state health measure observations.

Response fields:
- `state_code`
- `measure_id`
- `year`
- `value` — numeric value or null if suppressed/missing
- `value_type` — `"AGE_ADJUSTED"` or `"CRUDE"`
- `source_type` — `"DIRECT_SURVEY"` or `"COUNTY_ROLLUP"`
- `release_status` — `"FINAL"` or `"DRAFT"`
- `sample_size` — integer (may be null)
- `quality_flag` — string or null; values include `"INVALID_SCALE"`, `"INVALID"`, `"WITHDRAWN"`, or null for valid
- `release_id` — release identifier
- `revision` — integer revision number

### `GET /data/state-socioeconomic`
Returns state socioeconomic observations.

Response fields:
- `state_code`
- `year`
- Named fields: `poverty`, `median_income`, `bachelors`, `unemployment`, `uninsured`, `net_migration`, `region`
- `release_status` — `"FINAL"` or `"DRAFT"`
- `release_id` — release identifier
- `revision` — integer revision number
- `record_id` — unique row identifier

### `GET /data/county-health`
Returns county health measure observations.

Response fields:
- `fips_code`
- `state_code`
- `measure_id`
- `year`
- `value` — numeric or null
- `value_type`
- `source_type`
- `release_status`
- `sample_size`
- `quality_flag`
- `release_id`
- `revision`

### `GET /data/county-socioeconomic`
Returns county socioeconomic observations.

Response fields:
- `fips_code`
- `state_code`
- `year`
- Named fields: `poverty`, `median_income`, `bachelors`, `unemployment`, `uninsured`, `net_migration`
- `release_status`
- `release_id`
- `revision`
- `record_id`

### `GET /data/country-indicators`
Returns country-level indicator observations.

Response fields:
- `iso3`
- `indicator_id`
- `year`
- `value` — numeric or null
- `quality_flag` — string or null
- `scale_break` — boolean
- `release_id`
- `revision`

### `GET /data/revisions`
Returns revision event history.

Response fields:
- `revision_event_id` — string identifier
- `status` — `"APPLIED"` or other (SUPERSEDED, WITHDRAWN, etc.)
- `measure_id` or `indicator_id`
- `geography_level`
- `description` — human-readable description of the revision

### `GET /methodology`
Returns methodological documentation.

Response fields include variable definitions, quality-flag semantics, imputation guidance, and scale-break annotations.

### `GET /download`
Returns bulk data as a downloadable file (format varies by task context).

## Filtering conventions

When constructing analysis datasets:

1. **Release resolution:** When the protocol specifies `REGISTERED_FINAL_RELEASE_RESOLUTION`, select the highest-revision-number `FINAL` release for each (geography, measure, year, value_type, source_type) combination. When revision priority includes `revision`, `released_at`, and a row identifier, sort by those fields descending and take the first row per key.

2. **Health filters:** Apply `value_type`, `source_type`, and `release_status` exactly as declared.

3. **Socioeconomic filters:** Apply `release_status` exactly as declared. For revision resolution, sort by `revision`, then `released_at`, then `record_id` descending and take the first row per (state_code, year) or (fips_code, year) key.

4. **Quality exclusions:** Rows with `quality_flag` in the declared invalid set are excluded. Suppressed values (null value with no quality flag) are treated as missing.

5. **Complete case:** A row is complete when all declared fields are present, non-null, and (for health measures) have a non-invalid quality flag.
