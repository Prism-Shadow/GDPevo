# Data Resolution

Complete rules for PHO publication record selection, filtering, revision
precedence, validity checking, and cohort construction.

## Record selection precedence

For each entity-time-measure key, select exactly one record by comparing
candidates in this order, choosing the greater value at each step:

1. **Revision** - Highest `revision` number wins.
2. **Release timestamp** - Latest `released_at` wins (string or datetime comparison, later is greater).
3. **Record identifier** - Lowest `observation_id` (health datasets) or
   `record_id` (socioeconomic datasets) wins. Lower = more stable / earlier
   assigned.

This applies independently to health and socioeconomic sources. Each source
is resolved with its own key structure:
- Health: `(entity_code, year, measure_id, value_type, source_type)`
- Socioeconomic: `(entity_code, year, measure_id)`
- Country: `(iso3, year, indicator_id)`

### Edge cases

- If multiple records tie on revision and timestamp, the lowest id prevails.
- Records with missing or null revision numbers are treated as lower than any
  numeric revision.
- The `released_at` field may be ISO-8601 datetime or date-only; compare
  lexicographically.

## Filtering

### Pre-fetch filters

Use request-declared fields to narrow data fetches when the API supports
query parameters:

- `release_status` - Almost always `FINAL`; never use DRAFT, PRELIMINARY, or
  non-FINAL statuses unless explicitly requested.
- `value_type` - `AGE_ADJUSTED` or `CRUDE` for health measures.
- `source_type` - `DIRECT_SURVEY` or `COUNTY_ROLLUP` for health measures.
- `measure_id` - Requested measure identifier strings.
- `year` - Requested year ranges.

### Post-fetch filtering

After fetching, further filter in code by:
- Geographic constraints (state codes, county FIPS, ISO3 codes from the
  request's geography scope).
- Additional constraints not supported as query parameters.

## Validity and completeness

### Quality flags (health data)

The `quality_flag` field signals data problems:
- `INVALID_SCALE` - Measurement break makes value incomparable.
- `INVALID` - Value is not reliable.
- `WITHDRAWN` - Record has been formally withdrawn.
- Absent or blank flag = valid.

Records with these flags are **selected** for publication counting but their
values are **unavailable** for analysis.

### Suppressed values

A record with `value: null` or a sentinel suppression indicator is
**publication evidence** but **analytically incomplete**.

### Socioeconomic validity

A socioeconomic record is complete when its value is non-null and its
release status is valid. No quality-flag equivalent exists.

### Country data validity

Country indicators may have `scale_break` events. Records with unresolved
scale breaks are anomalies and must be excluded or imputed per the request's
methodology.

## Completeness predicates

A data row is **complete** for analysis when every required field has a
non-null, non-suppressed, non-invalid value. The specific required fields
vary by cohort type:

### State-level cohorts

- **Core complete**: `life_expectancy`, health exposure measure, plus
  socioeconomic fields (`poverty`, `bachelors`, `median_income`) are all
  non-null and valid.
- **Broad complete**: Outcome plus all ordered features (including derived
  fields like `socio_food_insecurity` from socioeconomic source) are non-null.
- **Strict dual-source complete**: Outcome, primary exposure, parallel
  exposure, and all adjustment variables are non-null in every year.

### County-level cohorts

- **Basic complete**: Selected health values plus poverty, median_income,
  bachelors, and RUCC are all non-null.
- **Primary cohort**: Basic-complete in the reference year.
- **Balanced panel**: Basic-complete in all requested years.
- **Machine-learning cohort**: Primary plus additional socioeconomic fields
  (unemployment, net_migration, uninsured) complete.

### Country-level cohorts

- **Usable**: Non-missing for all burden indicators after imputation.
- **Panel**: Usable in all requested panel years with non-missing outcome.

## Missing value rules

- **Never zero-fill** a missing value. Zero is a valid value for some fields
  (e.g., net_migration) and must not be confused with missing.
- Suppressed, invalid, withdrawn, blank, and null values are **unavailable**.
- When constructing a balanced panel, exclude any entity missing any required
  field in any required year.
- When constructing a cross-section, exclude any entity missing any required
  field in that year.

## Cohort construction patterns

### Balanced cohort

```text
balanced = {entities complete in ALL years of the analysis period}
balanced_n = len(balanced)
balanced_excluded = all_universe_entities - balanced
```

### Broad/reference-year cohort

```text
broad = {entities complete for outcome + all features in the reference year}
broad_n = len(broad)
```

### Strict dual-source cohort

```text
strict = {entities complete for outcome, primary, parallel, and adjustments
          in ALL analysis years}
```

## Entity ordering

- U.S. states: ASCII alphabetical by two-letter code (AK, AL, ..., WY).
  Include DC when in the 51-jurisdiction universe.
- Counties: By FIPS code (numeric string).
- Countries: By ISO3 code, ascending.
- Census divisions: Standard nine-division order (New England, Middle
  Atlantic, East North Central, West North Central, South Atlantic, East
  South Central, West South Central, Mountain, Pacific).
- Within-module entity-order arrays must exactly match their source cohort
  order; never independently re-sort.

## State and county metadata

### Census regions and divisions

Nine census divisions, each in exactly one of four regions:
- Northeast: New England, Middle Atlantic
- Midwest: East North Central, West North Central
- South: South Atlantic, East South Central, West South Central
- West: Mountain, Pacific

### RUCC codes

Rural-Urban Continuum Codes (1-9), with 1 = most urban. Available in county
socioeconomic data. RUCC1 is the reference category when used as indicators.

## Income scaling

`median_income` is typically divided by 10000 (or logged when specified) to
produce numerically stable coefficients. Check the analysis request for the
effective scaling rule.

## Country label reconciliation

Requested country labels may differ from canonical names. Resolution:
1. Fetch `/geographies/countries` for canonical label and ISO3.
2. Match requested labels against canonical names by case-insensitive
   comparison, substring matching, or known alias patterns ("Republic of X",
   "X Republic", "X Federation", "X Isles").
3. Count aliases as `alias_resolution_count` (resolved labels differing from
   canonical).
4. Every resolved label maps to exactly one ISO3.
