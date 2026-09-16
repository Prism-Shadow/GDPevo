# PHO Portal API Endpoints

Full catalog of the Public Health Observatory read-only REST API endpoints,
query parameters, and response conventions.

## Base URL

Resolved from `TASK_ENV_BASE_URL` or as explicitly provided in the prompt.

## No authentication

All endpoints are open. No headers, tokens, or cookies are required.

## Response format

All data endpoints return JSON arrays of flat objects. Geography endpoints
return arrays of label objects. The `/catalog` endpoint returns a structured
catalog object.

## Required endpoints

Every endpoint listed in `environment_access.md` is available:

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | Portal root / status |
| GET | `/catalog` | Dataset, measure, geography, and field catalog |
| GET | `/geographies/states` | U.S. state metadata (code, name, census division, region) |
| GET | `/geographies/counties` | U.S. county metadata (FIPS, name, state) |
| GET | `/geographies/countries` | Country metadata (ISO3, label, region) |
| GET | `/data/state-health` | State-level health indicator records |
| GET | `/data/state-socioeconomic` | State-level socioeconomic records |
| GET | `/data/county-health` | County-level health indicator records |
| GET | `/data/county-socioeconomic` | County-level socioeconomic records |
| GET | `/data/country-indicators` | Country-level burden and outcome indicator records |
| GET | `/data/revisions` | Revision event records |
| GET | `/methodology` | Methodology documentation |
| GET | `/download` | Bulk download endpoint |

## Query parameters

Data endpoints support filtering through query parameters. Common parameters
seen across the train evidence:

- `measure_id` - Filter by measure identifier
- `state_code` - Filter by two-letter U.S. state code
- `county_fips` - Filter by county FIPS code
- `iso3` - Filter by three-letter country code
- `year` - Filter by year
- `value_type` - `AGE_ADJUSTED` or `CRUDE`
- `source_type` - `DIRECT_SURVEY` or `COUNTY_ROLLUP`
- `release_status` - Typically `FINAL`

## Data record shape

### State health records

Fields include: `observation_id`, `state_code`, `year`, `measure_id`,
`value_type`, `source_type`, `release_status`, `value`, `sample_size`,
`quality_flag`, `revision`, `released_at`.

### State socioeconomic records

Fields include: `record_id`, `state_code`, `year`, `measure_id`,
`release_status`, `value`, `revision`, `released_at`.

### County health records

Fields include: `observation_id`, `county_fips`, `year`, `measure_id`,
`value_type`, `source_type`, `release_status`, `value`, `sample_size`,
`quality_flag`, `revision`, `released_at`.

### County socioeconomic records

Fields include: `record_id`, `county_fips`, `year`, `measure_id`,
`release_status`, `value`, `revision`, `released_at`. Includes `rucc` (rural-urban
continuum code, integer 1-9).

### Country indicator records

Fields include: `observation_id`, `iso3`, `year`, `indicator_id`,
`release_status`, `value`, `scale_break`, `revision`, `released_at`.

### Revision events

Fields include: `revision_event_id`, `status` (`APPLIED` or other),
description, and applicability metadata.

## Using the catalog

Always fetch `/catalog` first to understand available measures, their
identifiers, geography constraints, and field meanings. The catalog reveals
which datasets contain which measures and what query parameters are effective.

## Fetch strategy

1. Fetch the catalog to identify relevant datasets and measures.
2. Fetch geography listings to resolve entity identifiers.
3. Fetch data with broad filters (e.g., all years, all states) then subset
   in code to avoid missing records from overly narrow queries.
4. Fetch `/data/revisions` when the audit requires revision-event
   classification.
5. Fetch `/methodology` for domain context when needed.
