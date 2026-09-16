# Release Resolution and Cohort Construction

## Release Resolution

For each data source, apply these steps in order:

### 1. Filter by Publication Parameters
- `release_status`: keep only records matching the effective status (e.g. `FINAL`)
- `value_type`: keep only matching value types (e.g. `AGE_ADJUSTED`, `CRUDE`)
- `source_type`: keep only matching source types (e.g. `DIRECT_SURVEY`, `COUNTY_ROLLUP`)
- `quality_flag`: discard records whose quality_flag is in the declared `invalid_quality_flags` list
- Geography: restrict to the declared geography scope

### 2. Select One Record Per Key
For each unique (entity, year, measure) combination, select one record by this strict precedence:
1. Greatest `revision` number
2. Latest `released_at` timestamp
3. Lowest `observation_id` or `record_id`

### 3. Analytic Availability
- A selected record whose `value` is suppressed, null, or blank is publication evidence but analytically unavailable.
- Never zero-fill missing values.
- Only records passing all completeness checks enter analytic cohorts.

### 4. Revision Reporting
When reporting applied/nonapplied revision event IDs: query `/data/revisions`, filter by records applicable to the requested measures and geographies, then split by `status == "APPLIED"` vs other statuses. Sort ascending.

## Cohort Construction

After resolving releases independently for each data source, join by entity and time:

### Complete Case
A row is complete when all required analytic fields (outcome, exposures, features, weights) are non-suppressed, non-null, non-blank, and pass validity checks.

### Primary/Reference Cohort
All complete-case entities in the declared reference year. For state-level tasks with a 51-jurisdiction universe, excluded state codes are those in the universe but not in the primary cohort, sorted ascending.

### Balanced Panel Cohort
Entities complete in every requested year. Count the balanced entities and their total observations (entities x years).

### Broad Reference Cohort
Entities complete for the outcome and all ordered model features in the reference year. May be larger than the core balanced cohort.

### Strict Dual-Source Cohort
Entities complete for outcome, primary exposure, parallel exposure, and all adjustments in every analysis year.

### Machine-Learning Cohort
Primary-cohort members that are also complete for additional declared fields (e.g. unemployment, net_migration, uninsured).

## Ordering

Preserve entity-code then time order within every analytic matrix:
- State codes: ASCII ascending (AK, AZ, CA, ..., WY)
- County codes: sort by county_fips ascending, or by state_abbr then county_fips
- ISO3 codes: ASCII ascending
- Within an entity, sort by year ascending
- For panel-change rows: entity order then end-period order

## Entity Exclusions
When reporting excluded entity codes, list every entity in the universe that is not in the cohort. Sort ascending. Never include entities outside the declared universe.

## Country Label Resolution
When a request provides `country_labels`, reconcile each label against `/geographies/countries`:
1. Exact match on `label` field: resolved directly.
2. Non-matching label: an alias. Search for known name patterns. The resolved count equals unique matches; alias_resolution_count counts labels where the requested string differs from the canonical label.
3. Output the `iso3` of each resolved country, sorted ascending.
