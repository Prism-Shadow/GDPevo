# PHO Portal API Reference

## Base URL

The task environment provides a base URL. All endpoints are relative to it.

## Endpoints

### GET /
Root endpoint. Returns portal status.

### GET /catalog
Returns a catalog of available datasets, indicators, and metadata.

### GET /geographies/states
Returns state geography data. Each record includes state code (two-letter), state name, census division, census region, and other attributes.

### GET /geographies/counties
Returns county geography data. Each record includes FIPS code, county name, state code, RUCC (rural-urban continuum code, integer 1-9), and other attributes.

### GET /geographies/countries
Returns country geography data. Each record includes ISO3 code, country name, region, and other attributes. Many country names appear under multiple label forms (e.g., "Republic of X", "X Federation", "X Isles") but share the same ISO3 code.

### GET /data/state-health
Returns state-level health indicator publications. Each record includes:
- `state_code` (two-letter uppercase)
- `measure_id` (indicator identifier)
- `year` (integer)
- `value` (numeric, may be suppressed/missing)
- `value_type` (e.g., AGE_ADJUSTED, CRUDE)
- `source_type` (e.g., DIRECT_SURVEY, COUNTY_ROLLUP)
- `release_status` (e.g., FINAL)
- `revision` (integer — select greatest)
- `released_at` (datetime — select latest)
- `observation_id` (record identifier — select greatest as tiebreaker)
- `sample_size` (optional — used as reliability weight)
- `quality_flag` (optional — INVALID_SCALE, INVALID, WITHDRAWN must be rejected)
- Suppressed values are flagged and their value field is missing

### GET /data/state-socioeconomic
Returns state-level socioeconomic publications. Similar structure to health data:
- `state_code`, `measure_id`, `year`, `value`, `release_status`, `revision`, `released_at`, `record_id`
- Typical measures: poverty, median_income, bachelors, unemployment, uninsured, region, food_insecurity (socio variant)

### GET /data/county-health
Returns county-level health indicator publications. Each record includes:
- `county_fips`, `state_code`, `measure_id`, `year`, `value`, `value_type`, `source_type`, `release_status`, `revision`, `released_at`, `observation_id`
- Typical measures: adult_obesity, diagnosed_diabetes, physical_inactivity, food_insecurity
- Same revision and quality rules as state health

### GET /data/county-socioeconomic
Returns county-level socioeconomic publications:
- `county_fips`, `state_code`, `measure_id`, `year`, `value`, `release_status`, `revision`, `released_at`, `record_id`
- Typical measures: poverty, median_income, bachelors, unemployment, net_migration, uninsured, food_insecurity (socio variant)

### GET /data/country-indicators
Returns country-level burden indicators. Each record includes:
- `iso3` (three-letter uppercase)
- `indicator_id` (e.g., adult_mortality, bmi_burden, health_spending_gap, hiv_burden, immunization_gap, infant_mortality, poverty_rate, schooling_gap, life_expectancy)
- `year` (integer)
- `value` (numeric, may be missing)
- `scale_break` flag (indicates unresolved measurement break)
- Other metadata

### GET /data/revisions
Returns revision events. Each record includes:
- `revision_event_id` (e.g., RV00000001)
- `event_type` (e.g., APPLIED — affects data; others are non-applied)
- `description` and other metadata

Use this to identify which revision events have been applied to the current data release and which are pending or informational.

### GET /methodology
Returns methodology documentation describing indicator definitions, data collection, and revision processes.

### GET /download
Bulk download endpoint (use only if needed for large-scale resolution).

## Release Resolution Priority

For every publication key (entity + year + measure), resolve one record:

1. Filter by effective: `release_status`, `value_type`, `source_type`
2. Exclude records with quality_flag in [INVALID_SCALE, INVALID, WITHDRAWN]
3. Among remaining: select greatest `revision`
4. Among tied revisions: select latest `released_at`
5. Among tied timestamps: select greatest record identifier (`observation_id` or `record_id`)

## Geography Hierarchy

Census Divisions and their member states (as returned by /geographies/states):
- **New England:** CT, MA, ME, NH, RI, VT
- **Middle Atlantic:** NJ, NY, PA
- **East North Central:** IL, IN, MI, OH, WI
- **West North Central:** IA, KS, MN, MO, ND, NE, SD
- **South Atlantic:** DC, DE, FL, GA, MD, NC, SC, VA, WV
- **East South Central:** AL, KY, MS, TN
- **West South Central:** AR, LA, OK, TX
- **Mountain:** AZ, CO, ID, MT, NM, NV, UT, WY
- **Pacific:** AK, CA, HI, OR, WA

Census Regions:
- **Northeast:** New England + Middle Atlantic
- **Midwest:** East North Central + West North Central
- **South:** South Atlantic + East South Central + West South Central
- **West:** Mountain + Pacific

## Common Measures

State health: life_expectancy, adult_obesity, adult_smoking, diagnosed_diabetes, physical_inactivity, frequent_mental_distress, food_insecurity, premature_mortality_rate

State socioeconomic: poverty, median_income, bachelors, unemployment, uninsured

County health: adult_obesity, diagnosed_diabetes, physical_inactivity, food_insecurity

County socioeconomic: poverty, median_income, bachelors, unemployment, net_migration, uninsured, socio_food_insecurity, RUCC (from geography)

Country indicators: adult_mortality, bmi_burden, health_spending_gap, hiv_burden, immunization_gap, infant_mortality, poverty_rate, schooling_gap, life_expectancy
