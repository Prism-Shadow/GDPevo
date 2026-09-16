# PHO Portal API Reference

## Base URL

Replace `<TASK_ENV_BASE_URL>` from the prompt with the actual base URL. All requests are GET with no authentication.

## Endpoints

- `GET /` — Portal root, useful for verifying connectivity.
- `GET /catalog` — Lists available datasets and their field descriptions.
- `GET /geographies/states` — State-level geography metadata (codes, names, divisions, regions).
- `GET /geographies/counties` — County-level geography metadata (codes, names, state membership, RUCC codes).
- `GET /geographies/countries` — Country-level geography metadata (ISO3 codes, names, regions).
- `GET /data/state-health` — State-level health measures (life expectancy, adult obesity, smoking, diabetes, physical inactivity, mental distress, food insecurity, premature mortality, etc.).
- `GET /data/state-socioeconomic` — State-level socioeconomic measures (poverty, median income, bachelors attainment, unemployment, uninsured, etc.).
- `GET /data/county-health` — County-level health measures.
- `GET /data/county-socioeconomic` — County-level socioeconomic measures.
- `GET /data/country-indicators` — Country-level burden indicators (adult mortality, BMI burden, health spending gap, HIV burden, immunization gap, infant mortality, poverty rate, schooling gap, life expectancy).
- `GET /data/revisions` — Revision event log (revision_event_id, status, affected records, timestamps).
- `GET /methodology` — Documentation about measure definitions, value types, and source types.
- `GET /download` — Bulk data downloads.

## Data Record Structure

Every health record has keys including: measure_id, geography_code (state abbreviation or county FIPS or ISO3), year, value (float or suppressed), sample_size, value_type (AGE_ADJUSTED or CRUDE), source_type (DIRECT_SURVEY or COUNTY_ROLLUP or COUNTRY_SURVEY), release_status (FINAL or PRELIMINARY), revision (integer), released_at (timestamp), and an observation_id or record_id.

Socioeconomic records have similar keys: geography_code, year, value for each socioeconomic field, release_status, revision, released_at, and a record_id.

Revision events have: revision_event_id, status (APPLIED or other), and associated record references.

## Release Resolution

For each unique (geography_code, year, measure_id) tuple:
1. Filter to the effective release_status (typically FINAL).
2. Filter to the effective value_type and source_type if specified.
3. Exclude records flagged as suppressed, INVALID_SCALE, INVALID, WITHDRAWN, or with null/blank values.
4. From remaining candidates, select the record with the greatest revision number.
5. On revision ties, select the record with the latest released_at timestamp.
6. On timestamp ties, select the record with the lowest observation_id/record_id.

Suppressed, invalid, or missing analytic values are unavailable and never zero-filled. Records that resolve successfully (have a useable value) count as "selected" even if they are later excluded from a cohort due to missing companion fields.

## Geography Linking

State health records link to state socioeconomic records by state code and year. County health records link to county socioeconomic records by county FIPS code and year. Country indicator records are self-contained by ISO3 code and year.

Census divisions and regions come from the geography endpoints. County RUCC (Rural-Urban Continuum Code) values come from `/geographies/counties`.

## Multiple Requests

The portal may return large arrays. Fetch all required data before beginning computation. If the portal paginates, iterate through all pages. Cache responses locally to avoid re-fetching.

## Revision Events

Read `/data/revisions` to identify APPLIED and non-APPLIED revision events that affect the requested country/state/county measures. Use revision_event_id for the audit record; report applied and nonapplied IDs sorted ascending.

## Anomaly Detection (Scale Breaks)

Some records may be flagged with anomaly markers in the data. Identify cells where the value is marked as a scale break or unresolved anomaly. Report these as `ISO3|YEAR|indicator_id` triplets sorted ascending. Exclude these cells from analysis and count them in the quality audit.
