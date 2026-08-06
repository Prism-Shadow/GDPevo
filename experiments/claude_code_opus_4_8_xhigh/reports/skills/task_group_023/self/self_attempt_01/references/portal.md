# PHO Web portal reference

The portal is a read-only HTML site. The base URL comes from the environment (the prompt writes it as
`<TASK_ENV_BASE_URL>`; the environment exposes it, e.g. `GDPEVO_ENV_BASE_URL`). Do not hardcode it —
read it fresh each task, since the host/port can change.

## Endpoints

| Path | Purpose |
| --- | --- |
| `GET /` | Home; release-notice summary and browse forms. |
| `GET /catalog` | Every dataset: row count, coverage years, **columns with types**, filterable fields, and the **measure dictionary** (domain, measure_id, display_name, unit, direction). Start here. |
| `GET /methodology` | Document index + inline articles. `GET /methodology?doc=<id>` for one doc. Encodes the resolution rules you must apply. |
| `GET /geographies/states` | State reference (also `dataset=states`). |
| `GET /geographies/counties` | County reference (also `dataset=counties`). |
| `GET /geographies/countries` | Country reference incl. aliases (also `dataset=countries`). |
| `GET /data/state-health` | State health observations (dataset `state_health`). |
| `GET /data/state-socioeconomic` | State socioeconomic releases (`state_socioeconomic`). |
| `GET /data/county-health` | County health observations (`county_health`). |
| `GET /data/county-socioeconomic` | County socioeconomic releases (`county_socioeconomic`). |
| `GET /data/country-indicators` | Country indicator observations (`country_indicators`). |
| `GET /data/revisions` | Revision notices (`revisions`). |
| `GET /download?dataset=<name>&format=csv` | **Machine-readable export.** Accepts the same filters as the dataset's browse page as extra query params. Use this for all data pulls. |

There is **no JSON API** — `format=json` returns an error page. Always use `format=csv`. The download is
unpaginated: it returns all rows matching the filters. Verify row counts against the `/catalog` totals.

## Dataset schemas (columns)

Confirm against `/catalog` each run (columns are stable but the task may add measures). As observed:

- **states** (51): `state_fips, state_abbr, state_name, region, division, is_state`.
  `region` ∈ {Northeast, Midwest, South, West}; `division` = the 9 Census divisions used for
  `CENSUS_DIVISION` grouping. Join health/SES rows to this table for region/division.
- **counties** (~1224): `county_fips, state_abbr, county_name, region, rucc, metro_class,
  population_base, latitude, longitude`. `rucc` is an integer 1–9 (1–3 metro, 4–9 nonmetro). County
  FIPS = 2-char state code + 3-char county suffix; leading zeros are meaningful (text, not int).
- **countries** (~72): `iso3, canonical_name, portal_label, alternate_labels, region, income_group`.
  `alternate_labels` is a `|`-delimited list; use it plus ISO3 to reconcile analyst-supplied labels.
- **state_health** (coverage 2020–2024): `observation_id, state_fips, state_abbr, year, measure_id,
  value_type, source_type, release_status, revision, value, standard_error, sample_size,
  suppression_flag, quality_flag, released_at`.
- **state_socioeconomic** (2020–2024): `record_id, state_fips, state_abbr, year, release_status,
  revision, released_at, poverty, bachelors, median_income, unemployment, uninsured, food_insecurity,
  population, quality_flag`.
- **county_health** (2021–2024): `observation_id, county_fips, state_abbr, region, year, measure_id,
  value_type, release_status, revision, released_at, value, low_ci, high_ci, population,
  suppression_flag, quality_flag`. (County health has value_type but no source_type column.)
- **county_socioeconomic** (2020–2024): `record_id, county_fips, state_abbr, region, year,
  release_status, revision, released_at, poverty, median_income, bachelors, unemployment,
  net_migration, uninsured, population, quality_flag`.
- **country_indicators** (2013–2024): `observation_id, country_label, iso3, year, indicator_id,
  release_status, revision, released_at, value, unit, quality_flag`.
- **revisions** (2015–2024): `revision_event_id, domain, entity_id, field_id, effective_year,
  old_value, new_value, status, issued_at, reason_code, note`. `domain` ∈ {STATE_HEALTH, STATE_SES,
  COUNTY_HEALTH, COUNTY_SES, COUNTRY}; `status` ∈ {APPLIED, PENDING, WITHDRAWN}; `reason_code` includes
  `SCALE_CORRECTION`.

## Enumerations you will filter on

- `release_status`: `FINAL` vs `PROVISIONAL`. FINAL supersedes PROVISIONAL for publication.
- `revision`: integer; PROVISIONAL rows are revision 0, FINAL rows are revision ≥ 1 (some 2 = restated).
- `value_type`: `AGE_ADJUSTED` vs `CRUDE`.
- `source_type` (state_health): `DIRECT_SURVEY` (primary state series) vs `COUNTY_ROLLUP` (parallel).
- `suppression_flag`: `1` = value not published (unavailable, never 0), `0` = published.
- `quality_flag`: e.g. `SUPPRESSED, PROVISIONAL, REVISED, REVIEWED, PARALLEL_ESTIMATE`, and for
  scale issues `INVALID_SCALE, INVALID, WITHDRAWN`. Quality flags do **not** change release precedence,
  but a task's `analysis_request` may list specific `invalid_quality_flags` to exclude — honor that list.

## Measure dictionary highlights (from /catalog)

- STATE_HEALTH measures: `adult_obesity, adult_smoking, diagnosed_diabetes, food_insecurity,
  frequent_mental_distress, life_expectancy, physical_inactivity, premature_mortality_rate`.
- COUNTY_HEALTH measures: `adult_obesity, adult_smoking, copd, depression, diagnosed_diabetes,
  physical_inactivity, severe_housing_cost_burden, short_sleep`.
- COUNTRY indicators: `adult_mortality, alcohol_harm, bmi_burden, health_spending_gap, hiv_burden,
  immunization_gap, infant_mortality, life_expectancy, poverty_rate, schooling_gap, unemployment,
  urbanization`.
- Each carries `direction` (`HIGHER_WORSE`, `HIGHER_BETTER`, `NEUTRAL`) and `unit`. Check units before
  combining indicators; percentages and mortality rates are not interchangeable. `life_expectancy` is
  `HIGHER_BETTER` and in years.

## Methodology rules that govern resolution (from /methodology)

Read these each run; they justify the resolution logic in `data_resolution_and_cohorts.md`.

- **release-lifecycle**: "Final records replace provisional records for publication, and the highest
  applied final revision governs when several final revisions exist." → filter FINAL, take max revision,
  break ties by latest `released_at`.
- **suppression**: suppressed/missing values keep metadata but publish no value; never treat as zero.
- **quality**: flags describe review state and do not change release precedence (retain in extracts).
- **publication-values**: age-adjusted supports cross-jurisdiction comparison; crude describes observed
  local burden. Use whichever the task's filter specifies.
- **state-estimates**: DIRECT_SURVEY is the primary state series; COUNTY_ROLLUP is a parallel estimate
  and must not silently replace direct records (relevant to source-perturbation modules).
- **socioeconomic-fields**: SES fields are revised independently; a sparse null field does not
  invalidate other published fields in the same record.
- **aliases / country-revisions**: portal labels differ from canonical names; reconcile via ISO3 and
  `alternate_labels`. Applied scale corrections appear in later FINAL revisions; PENDING/WITHDRAWN
  notices do not authorize replacement.
- **rucc**: 1–3 metro, 4–9 nonmetro; RUCC lives on the county geography table.
- **geographic-ids**: FIPS are text with meaningful leading zeros; county FIPS = state(2) + county(3).
- **indicator-direction**: the dictionary declares favorable/unfavorable/neutral and units.
