# PHO Portal API Reference
The Public Health Observatory portal provides read-only access to
surveillance, socioeconomic, geography, revision, and methodology records.

## Base URL
Given by the task prompt as TASK_ENV_BASE_URL. Typical form: http://task-env:9023/

## Endpoints

### GET /
HTML landing page. Confirms portal availability.

### GET /catalog
HTML page listing all datasets with row counts, column schemas, filter
parameters, and a measure dictionary. Essential for understanding available
fields without querying every endpoint.

**Measure dictionary** (indexed by domain:measure_id):
- STATE_HEALTH: adult_obesity, adult_smoking, diagnosed_diabetes,
  food_insecurity, frequent_mental_distress, life_expectancy,
  physical_inactivity, premature_mortality_rate
- COUNTY_HEALTH: adult_obesity, adult_smoking, copd, depression,
  diagnosed_diabetes, physical_inactivity, severe_housing_cost_burden,
  short_sleep
- COUNTRY: adult_mortality, alcohol_harm, bmi_burden, health_spending_gap,
  hiv_burden, immunization_gap, infant_mortality, life_expectancy,
  poverty_rate, schooling_gap, unemployment, urbanization

### GET /geographies/states
HTML with 51 state rows. Columns: state_fips (TEXT), state_abbr (TEXT),
state_name (TEXT), region (TEXT), division (TEXT), is_state (INTEGER).

Nine census divisions: East North Central, East South Central,
Middle Atlantic, Mountain, New England, Pacific, South Atlantic,
West North Central, West South Central.

Four regions: Midwest, Northeast, South, West.

Division-to-region mapping:
- New England, Middle Atlantic -> Northeast
- East North Central, West North Central -> Midwest
- South Atlantic, East South Central, West South Central -> South
- Mountain, Pacific -> West

Access CSV with /download?dataset=states&format=csv or filter with
query parameters ?state_abbr=, ?region=, ?division=.

### GET /geographies/counties
HTML with 1,224 county rows. Columns: county_fips (TEXT, 5 chars:
2-char state prefix + 3-char county suffix), state_abbr (TEXT),
county_name (TEXT), region (TEXT), rucc (INTEGER 1-9),
metro_class (TEXT), population_base (INTEGER), latitude (REAL),
longitude (REAL).

RUCC values 1-3 are metropolitan; 4-9 are nonmetropolitan.

Access CSV with /download?dataset=counties&format=csv or filter with
?state_abbr=, ?region=, ?rucc=, ?metro_class=.

### GET /geographies/countries
HTML with 72 country rows. Columns: iso3 (TEXT, 3 uppercase chars),
canonical_name (TEXT), portal_label (TEXT), alternate_labels (TEXT,
pipe-separated), region (TEXT), income_group (TEXT).

Country label reconciliation: portal_label may differ from canonical_name.
The alternate_labels field (pipe-delimited) supports matching
analyst-provided labels to iso3. Match any pipe-delimited alternative
or the portal_label itself. Resolve to iso3.

Six world regions; income groups: LOW, LOWER_MIDDLE, UPPER_MIDDLE, HIGH.

Access CSV with /download?dataset=countries&format=csv or filter with
?iso3=, ?label=, ?region=, ?income_group=.

### GET /data/state-health
4,861 rows covering 2020-2024. Columns: observation_id (TEXT),
state_fips (TEXT), state_abbr (TEXT), year (INTEGER), measure_id (TEXT),
value_type (TEXT: AGE_ADJUSTED or CRUDE), source_type (TEXT:
DIRECT_SURVEY or COUNTY_ROLLUP), release_status (TEXT: FINAL or
PROVISIONAL), revision (INTEGER), value (REAL), standard_error (REAL),
sample_size (INTEGER), suppression_flag (INTEGER), quality_flag (TEXT),
released_at (TEXT, ISO date).

Suppression: when suppression_flag=1, value is suppressed and
unavailable. Never zero-fill.

Value types: AGE_ADJUSTED for state comparisons; CRUDE for observed burden.

Source types: DIRECT_SURVEY is the primary state publication series;
COUNTY_ROLLUP is a parallel estimate for coverage review.

Access CSV: /download?dataset=state_health&format=csv.
Filter: ?state_abbr=, ?measure_id=, ?year=, ?value_type=,
?source_type=, ?release_status=, ?revision=.

### GET /data/state-socioeconomic
323 rows covering 2020-2024. Columns: record_id (TEXT), state_fips (TEXT),
state_abbr (TEXT), year (INTEGER), release_status (TEXT), revision
(INTEGER), released_at (TEXT), poverty (REAL), bachelors (REAL),
median_income (REAL), unemployment (REAL), uninsured (REAL),
food_insecurity (REAL), population (INTEGER), quality_flag (TEXT).

Access CSV: /download?dataset=state_socioeconomic&format=csv.
Filter: ?state_abbr=, ?year=, ?release_status=, ?revision=.

### GET /data/county-health
47,938 rows covering 2021-2024. Columns: observation_id (TEXT),
county_fips (TEXT), state_abbr (TEXT), region (TEXT), year (INTEGER),
measure_id (TEXT), value_type (TEXT), release_status (TEXT),
revision (INTEGER), released_at (TEXT), value (REAL), low_ci (REAL),
high_ci (REAL), population (INTEGER), suppression_flag (INTEGER),
quality_flag (TEXT).

Access CSV: /download?dataset=county_health&format=csv.
Filter: ?county_fips=, ?state_abbr=, ?region=, ?measure_id=,
?year=, ?value_type=, ?release_status=, ?revision=,
?suppression_flag=.

### GET /data/county-socioeconomic
6,772 rows covering 2020-2024. Columns: record_id (TEXT),
county_fips (TEXT), state_abbr (TEXT), region (TEXT), year (INTEGER),
release_status (TEXT), revision (INTEGER), released_at (TEXT),
poverty (REAL), median_income (REAL), bachelors (REAL),
unemployment (REAL), net_migration (REAL), uninsured (REAL),
population (INTEGER), quality_flag (TEXT).

Access CSV: /download?dataset=county_socioeconomic&format=csv.
Filter: ?county_fips=, ?state_abbr=, ?region=, ?year=,
?release_status=, ?revision=.

### GET /data/country-indicators
9,812 rows covering 2013-2024. Columns: observation_id (TEXT),
country_label (TEXT), iso3 (TEXT), year (INTEGER), indicator_id (TEXT),
release_status (TEXT), revision (INTEGER), released_at (TEXT),
value (REAL), unit (TEXT), quality_flag (TEXT).

Access CSV: /download?dataset=country_indicators&format=csv.
Filter: ?iso3=, ?country_label=, ?indicator_id=, ?year=,
?release_status=, ?revision=, ?quality_flag=.

### GET /data/revisions
130 rows covering 2015-2024. Columns: revision_event_id (TEXT),
domain (TEXT), entity_id (TEXT), field_id (TEXT), effective_year
(INTEGER), old_value (REAL), new_value (REAL), status (TEXT: APPLIED,
PENDING, WITHDRAWN), issued_at (TEXT), reason_code (TEXT), note (TEXT).

APPLIED revisions are reflected in later final revisions. PENDING
and WITHDRAWN notices do not replace published values.

Access CSV: /download?dataset=revisions&format=csv.
Filter: ?domain=, ?entity_id=, ?field_id=, ?effective_year=,
?status=.

### GET /methodology
HTML index of methodology documents. Add ?doc=<doc-id> for a specific
document. Doc IDs: aliases, quality, suppression, rucc,
release-lifecycle, publication-values, state-estimates,
geographic-ids, socioeconomic-fields, influence,
country-revisions, county-windows, indicator-direction,
revisions-draft, release-lifecycle-v2.

### GET /download
?dataset=<dataset>&format=csv returns the full dataset as CSV.
Dataset names: states, counties, countries, state_health,
state_socioeconomic, county_health, county_socioeconomic,
country_indicators, revisions.

**Preferred approach**: Download full datasets as CSV, then filter and
resolve locally. This is more efficient than many filtered HTML queries.

## Key Methodology Rules

- Release lifecycle: FINAL records replace PROVISIONAL. The highest
  applied FINAL revision governs when several FINAL revisions exist.
- Suppression: Suppressed observations (suppression_flag=1) retain
  metadata but do not publish a value. Never treat suppressed/missing
  as zero.
- Value types: AGE_ADJUSTED supports state comparisons. CRUDE describes
  observed burden. County rollups should not silently replace direct records.
- Geographic IDs: State and county FIPS are TEXT with meaningful leading
  zeros. County FIPS = 2-char state + 3-char county suffix.
- Country labels: Match analyst labels to iso3 via portal_label or
  alternate_labels (pipe-delimited). The alias resolution count is the
  number of resolved labels whose match differs from the canonical
  country name.
- Quality flags: Describe review state; do not change release precedence.
  INVALID_SCALE, INVALID, and WITHDRAWN flags mark observations that must
  be excluded.
