# Public Health Observatory Portal API

## Base URL

`{TASK_ENV_BASE_URL}` — provided in the task prompt (e.g. `http://task-env:9023/`).

## Endpoints

### GET / — Portal home page (HTML)

### GET /catalog — Dataset catalog (HTML)
Lists all datasets with column schemas, row counts, coverage ranges, and filter params.

### GET /geographies/states
State geography reference (browse HTML or download CSV). 51 rows (50 states + DC).
Columns: state_fips (TEXT), state_abbr (TEXT), state_name (TEXT), region (TEXT), division (TEXT), is_state (INTEGER).
Filters: state_abbr, state_fips, region, division.

### GET /geographies/counties
County geography reference (browse HTML or download CSV). 1,224 rows.
Columns: county_fips (TEXT), state_abbr (TEXT), county_name (TEXT), region (TEXT), rucc (INTEGER), metro_class (TEXT), population_base (INTEGER), latitude (REAL), longitude (REAL).
Filters: county_fips, state_abbr, region, rucc, metro_class.

### GET /geographies/countries
Country geography reference (browse HTML or download CSV). 72 rows.
Columns: iso3 (TEXT), canonical_name (TEXT), portal_label (TEXT), alternate_labels (TEXT), region (TEXT), income_group (TEXT).
Filters: iso3, label, region, income_group.

### GET /data/state-health
State health observations (browse HTML or download CSV). ~4,861 rows, coverage 2020-2024.
Columns: observation_id (TEXT), state_fips (TEXT), state_abbr (TEXT), year (INTEGER), measure_id (TEXT), value_type (TEXT), source_type (TEXT), release_status (TEXT), revision (INTEGER), value (REAL), standard_error (REAL), sample_size (INTEGER), suppression_flag (INTEGER), quality_flag (TEXT), released_at (TEXT).
Filters: state_abbr, measure_id, year, value_type, source_type, release_status, revision.
Measures: life_expectancy, adult_obesity, adult_smoking, diagnosed_diabetes, physical_inactivity, frequent_mental_distress, food_insecurity, premature_mortality_rate.

### GET /data/state-socioeconomic
State socioeconomic releases (browse HTML or download CSV). ~323 rows, coverage 2020-2024.
Columns: record_id (TEXT), state_fips (TEXT), state_abbr (TEXT), year (INTEGER), release_status (TEXT), revision (INTEGER), released_at (TEXT), poverty (REAL), bachelors (REAL), median_income (REAL), unemployment (REAL), uninsured (REAL), food_insecurity (REAL), population (INTEGER), quality_flag (TEXT).
Filters: state_abbr, year, release_status, revision.

### GET /data/county-health
County health observations (browse HTML or download CSV). ~47,938 rows, coverage 2021-2024.
Columns: observation_id (TEXT), county_fips (TEXT), state_abbr (TEXT), region (TEXT), year (INTEGER), measure_id (TEXT), value_type (TEXT), release_status (TEXT), revision (INTEGER), released_at (TEXT), value (REAL), low_ci (REAL), high_ci (REAL), population (INTEGER), suppression_flag (INTEGER), quality_flag (TEXT).
Filters: county_fips, state_abbr, region, measure_id, year, value_type, release_status, revision, suppression_flag.

### GET /data/county-socioeconomic
County socioeconomic releases (browse HTML or download CSV). ~6,772 rows, coverage 2020-2024.
Columns: record_id (TEXT), county_fips (TEXT), state_abbr (TEXT), region (TEXT), year (INTEGER), release_status (TEXT), revision (INTEGER), released_at (TEXT), poverty (REAL), median_income (REAL), bachelors (REAL), unemployment (REAL), net_migration (REAL), uninsured (REAL), population (INTEGER), quality_flag (TEXT).

### GET /data/country-indicators
Country indicator observations (browse HTML or download CSV). ~9,812 rows, coverage 2013-2024.
Columns: observation_id (TEXT), country_label (TEXT), iso3 (TEXT), year (INTEGER), indicator_id (TEXT), release_status (TEXT), revision (INTEGER), released_at (TEXT), value (REAL), unit (TEXT), quality_flag (TEXT).
Filters: iso3, country_label, indicator_id, year, release_status, revision, quality_flag.

### GET /data/revisions
Revision notices (browse HTML or download CSV). ~130 rows, coverage 2015-2024.
Columns: revision_event_id (TEXT), domain (TEXT), entity_id (TEXT), field_id (TEXT), effective_year (INTEGER), old_value (REAL), new_value (REAL), status (TEXT), issued_at (TEXT), reason_code (TEXT), note (TEXT).

### GET /methodology
Methodology library index (HTML). Lists documents with title, version, status, and category.

### GET /methodology?doc={doc-id}
Individual methodology document (HTML). Key documents:
- `state-estimates` — Direct survey is primary for state publications; county rollups are parallel.
- `publication-values` — Age-adjusted for state comparisons; crude for observed county burden.
- `release-lifecycle` — Final supersedes provisional; highest applied final revision governs.
- `suppression` — Suppressed or missing values are never zero-filled.
- `quality` — Quality flags describe review state; do not change release precedence.
- `aliases` — Country label reconciliation: portal_label may differ from canonical_name; resolve via alternate_labels.
- `rucc` — RUCC 1-3 = metropolitan, 4-9 = nonmetropolitan.
- `geographic-ids` — State and county FIPS are text; leading zeros are meaningful.
- `country-revisions` — Applied scale corrections appear in later final revisions.
- `county-windows` — Compare like-for-like final fields across years.
- `socioeconomic-fields` — Sparse null fields do not invalidate other fields in the same record.

### GET /download?dataset={name}&format=csv
Download any dataset as CSV. Apply filters as query params. Bulk extraction via this endpoint.

## Data Access Pattern

Prefer CSV downloads for bulk extraction. Parse with Python `csv.DictReader`.

For state health, the portal returns HTML browse pages; filter programmatically after bulk CSV download.
For country data, reconcile requested labels via the countries geography reference (check portal_label and alternate_labels) to obtain stable iso3 identifiers.
