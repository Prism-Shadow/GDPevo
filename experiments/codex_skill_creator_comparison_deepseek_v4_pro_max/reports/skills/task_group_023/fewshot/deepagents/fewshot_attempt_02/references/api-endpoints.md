## API Endpoints

### Base URL

The prompt provides `<TASK_ENV_BASE_URL>`. This is typically `http://task-env:9023/`.

### Endpoint Catalog

#### Root and Metadata

| Endpoint | Description |
|----------|-------------|
| `GET /` | Root health check |
| `GET /catalog` | Full catalog of available datasets, measures, fields, and geographies |
| `GET /methodology` | Methodology notes and documentation |

#### Geography Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /geographies/states` | U.S. state and DC identifiers, names, census divisions, regions, FIPS codes |
| `GET /geographies/counties` | U.S. county identifiers, names, parent states, RUCC codes (1-9), FIPS codes |
| `GET /geographies/countries` | Country identifiers, ISO3 codes, names, aliases, regions |

#### Data Endpoints

| Endpoint | Query Parameters | Description |
|----------|-----------------|-------------|
| `GET /data/state-health` | `measure_id`, `value_type`, `source_type`, `release_status`, `year`, `state_code` | State health measures |
| `GET /data/state-socioeconomic` | `release_status`, `year`, `state_code` | State socioeconomic data |
| `GET /data/county-health` | `measure_id`, `value_type`, `release_status`, `year`, `state_code`, `county_code` | County health measures |
| `GET /data/county-socioeconomic` | `release_status`, `year`, `state_code`, `county_code` | County socioeconomic data |
| `GET /data/country-indicators` | `indicator_id`, `year`, `iso3` | Country burden and health indicators |
| `GET /data/revisions` | — | Revision event log (APPLIED / non-APPLIED) |
| `GET /download` | `dataset`, `year`, `format` | Bulk data downloads |

### Common Response Fields

Every data record includes:

- `observation_id` / `record_id` — unique row identifier
- `year` — integer observation year
- `revision` — integer revision number (higher is newer)
- `released_at` — ISO-formatted release timestamp string
- `release_status` — `"FINAL"` or other status
- `value_type` — `"AGE_ADJUSTED"`, `"CRUDE"`, or similar (health records only)
- `source_type` — `"DIRECT_SURVEY"`, `"COUNTY_ROLLUP"`, or similar (health records only)
- `value` — the analytic numeric value; `null`, blank, `"SUPPRESSED"`, `"INVALID"`, or `"WITHDRAWN"` when unavailable
- `sample_size` — optional record-level sample size (used as reliability weight for some protocols)

For state records, state identifiers are uppercase two-letter postal codes plus `"DC"`.
For county records, county identifiers are typically FIPS codes.
For country records, country identifiers are ISO3 codes (uppercase three-letter).

### Release Selection Priority

When multiple records exist for the same entity—time—measure key, select one by applying these rules in order:

1. **Release status filter**: keep only records matching the effective `release_status` (typically `"FINAL"`)
2. **Greatest revision**: among remaining, keep the record with the highest `revision` number
3. **Latest release timestamp**: break revision ties by the most recent `released_at` string
4. **Greatest record identifier**: break timestamp ties by the highest `observation_id` or `record_id`

### Value Validity Rules

- Suppressed values (`"SUPPRESSED"`), `"INVALID"`, `"WITHDRAWN"`, blank strings, and `null` are never valid analytic values
- These records count as selected publications (they exist) but are excluded from any complete-case cohort
- Never zero-fill missing or invalid values

### State Geography Reference

- **Regions**: Northeast, Midwest, South, West
- **Census Divisions** (9): New England, Middle Atlantic, East North Central, West North Central, South Atlantic, East South Central, West South Central, Mountain, Pacific

### Country Geography Reference

- Country labels may appear under multiple alias forms (Republic of X, X Federation, X Isles). Use the `/geographies/countries` endpoint to resolve aliases to canonical names and ISO3 codes.

### Common Health Measures

- `life_expectancy`, `adult_obesity`, `diagnosed_diabetes`, `physical_inactivity`, `adult_smoking`, `frequent_mental_distress`, `food_insecurity`, `premature_mortality_rate`, `infant_mortality`

### Common Socioeconomic Fields

- `poverty`, `median_income`, `bachelors`, `unemployment`, `uninsured`, `net_migration`, `region`

### Common Country Indicators

- `life_expectancy`, `adult_mortality`, `bmi_burden`, `health_spending_gap`, `hiv_burden`, `immunization_gap`, `infant_mortality`, `poverty_rate`, `schooling_gap`

### Revision Events

The `/data/revisions` endpoint provides a log of revision events. Each event has a `revision_event_id` and a `status` field of `"APPLIED"` or other values. The status determines whether the event is applied or nonapplied in the quality audit.
