# Portal API Reference

The Public Health Observatory (PHO) read-only evidence portal is a REST API
serving JSON datasets. All endpoints return complete datasets; filter
client-side by the request's geography, years, value types, source types,
release status, and validity flags.

## Base URL

The base URL is provided in the prompt text as `<TASK_ENV_BASE_URL>`. Replace
the placeholder with the actual URL before making any requests.

## Endpoints

| Endpoint | Content |
|---|---|
| `GET /` | Portal health check and version information. |
| `GET /catalog` | Full catalog of available measures, geographies, and releases. |
| `GET /geographies/states` | State geography metadata including two-letter codes, names, census divisions, and regions. |
| `GET /geographies/counties` | County geography metadata including FIPS codes, names, state membership, and RUCC codes. |
| `GET /geographies/countries` | Country geography metadata including ISO3 codes, names, and region assignments. |
| `GET /data/state-health` | State-level health measure observations with value types, source types, sample sizes, and release metadata. |
| `GET /data/state-socioeconomic` | State-level socioeconomic records with release metadata. |
| `GET /data/county-health` | County-level health measure observations. |
| `GET /data/county-socioeconomic` | County-level socioeconomic records. |
| `GET /data/country-indicators` | Country-level burden and health indicators with release metadata. |
| `GET /data/revisions` | Revision event log with event IDs and statuses (APPLIED / non-APPLIED). |
| `GET /methodology` | Methodology documentation for measures and value types. |
| `GET /download` | Bulk data download endpoint. |

## Data shapes

### State-health observations

Each record typically includes: `state_code`, `measure_id`, `year`, `value`,
`value_type` (AGE_ADJUSTED or CRUDE), `source_type` (DIRECT_SURVEY or
COUNTY_ROLLUP), `sample_size`, `release_status` (FINAL vs other), `revision`,
`released_at`, `observation_id`, and a `quality_flag` field. Records with
quality flags matching the request's invalid set (e.g. INVALID_SCALE, INVALID,
WITHDRAWN) must be excluded from analytic use.

### County-health observations

Similar to state-health but keyed by `county_fips` and `state_code`. Includes
`measure_id`, `year`, `value`, `value_type`, `source_type`, and release
metadata.

### Socioeconomic records

State-level records include: `state_code`, `year`, fields like `poverty`,
`median_income`, `bachelors`, `unemployment`, `uninsured`, `region`, and
release metadata (`release_status`, `revision`, `released_at`, `record_id`).

County-level records include: `county_fips`, `state_code`, `year`, fields like
`poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`,
`uninsured`, and release metadata.

### Country indicators

Each record includes: `iso3`, `country_name`, `year`, `indicator_id`, `value`,
and release/revision metadata. Scale-break anomalies are flagged in the
revision data.

### Geography endpoints

- **States**: `state_code` (two-letter), `state_name`, `census_division`,
  `region` (Northeast, Midwest, South, West).
- **Counties**: `county_fips`, `county_name`, `state_code`, `rucc` (integer
  1-9), `census_division`, `region`.
- **Countries**: `iso3` (three-letter), `country_name`, `region`, `aliases`
  (list of alternative names).

## Filtering approach

For each dataset fetch the full endpoint response, then filter client-side:

1. **Geography**: keep only entities within the request's geography scope
   (e.g. specific states, regions, counties, or country labels).
2. **Years**: keep only records within the request's declared analysis years.
3. **Value type / source type**: keep only records matching the request's
   health filter (e.g. AGE_ADJUSTED + DIRECT_SURVEY).
4. **Release status**: keep only records with the declared release status
   (typically FINAL).
5. **Validity**: exclude records whose quality_flag appears in the request's
   invalid set, or whose value is suppressed/null for analytic purposes.

Never zero-fill missing values. Treat suppressed, invalid, withdrawn, blank,
or null values as unavailable.

## Country label resolution

When a request supplies human-readable country labels (e.g. "Republic of
Alder"), resolve them against the `/geographies/countries` endpoint:

1. Match each label to a canonical country name or alias in the geography data.
2. Collect the resolved ISO3 codes. Labels that differ from the canonical name
   count as alias resolutions.
3. Report the full sorted set of resolved ISO3 identifiers.
