# Portal data model, release resolution, cohorts, output contract

## Portal navigation
The task gives a read-only portal base URL. Discover everything from it:
- `GET /catalog` — every dataset, its columns and types, its filter params, and a
  CSV export link. Read this first; column names are authoritative.
- `GET /methodology` — the publication rules (release lifecycle, suppression,
  direct-vs-rollup, crude-vs-age-adjusted, RUCC, country-label reconciliation,
  revision notices). These rules define resolution — read them, don't assume.
- Data pages `GET /data/<dataset>` render filtered rows; the same filtered rows
  export as CSV via the "CSV" link (`/download?dataset=<name>&format=csv&<filters>`).
  Pull whole datasets as CSV and process locally (they are small: thousands of rows).

### Datasets (names / key columns)
- `states`: state_fips, state_abbr, state_name, region, division, is_state
  (51 jurisdictions = 50 states + DC; 4 regions; **9 census divisions**).
- `counties`: county_fips, state_abbr, county_name, region, rucc, metro_class,
  population_base, lat/long (RUCC 1–3 metro, 4–9 nonmetro).
- `countries`: iso3, canonical_name, portal_label, alternate_labels (pipe-sep),
  region, income_group.
- `state_health` / `county_health`: observation_id, fips, year, measure_id,
  value_type (AGE_ADJUSTED | CRUDE), source_type (DIRECT_SURVEY | COUNTY_ROLLUP),
  release_status, revision, value, standard_error, sample_size, suppression_flag,
  quality_flag, released_at.
- `state_socioeconomic` / `county_socioeconomic`: record_id, fips, year,
  release_status, revision, released_at, and the fields (poverty, bachelors,
  median_income, unemployment, uninsured, food_insecurity, net_migration,
  population, ...). Fields are revised independently; a sparse null field does
  not invalidate other fields in the same record.
- `country_indicators`: observation_id, country_label, iso3, year, indicator_id,
  release_status, revision, value, unit, quality_flag.
- `revisions`: revision_event_id, domain, entity_id, field_id, effective_year,
  old_value, new_value, status (APPLIED | PENDING | WITHDRAWN), reason_code, note.

## Release / revision resolution (the crux — get this exact)
For each series key `(entity, year, measure, value_type, source_type)`:
1. Drop `PROVISIONAL` (revision 0); keep `release_status == FINAL`.
2. Take the **highest revision** (a later FINAL revision, e.g. quality_flag
   `REVISED`, supersedes the earlier FINAL). Tie-break by the declared priority
   (usually `revision`, then `released_at`, then the row id).
3. The winning row is the "resolved" record. **Counts of resolved records include
   suppressed rows** (a suppressed record is still resolved; it just has no value).
4. `suppression_flag == 1` or `quality_flag == SUPPRESSED` → the value is
   **unavailable**; also treat declared `invalid_quality_flags` values as
   unavailable. **Never zero-fill** a suppressed/missing value.
5. Series semantics: `DIRECT_SURVEY` is the primary state series; `COUNTY_ROLLUP`
   is a *parallel* estimate (used only where a task's source-perturbation asks).
   `AGE_ADJUSTED` for cross-jurisdiction comparison, `CRUDE` for observed burden —
   use whichever the request's filter names.
6. FIPS are text with meaningful leading zeros; county_fips = 2-char state + 3-char.

### Country scale-break / revision-notice audit (country tasks)
`revisions` rows with `reason_code == SCALE_CORRECTION` flag a 10× scale break.
- **APPLIED** → a later FINAL revision carries the corrected value, so resolution
  picks the fixed value → the cell is *resolved* (not an anomaly).
- **PENDING / WITHDRAWN** (non-applied) → no correction was published, the resolved
  value is still the anomalous one → the cell is an **unresolved scale-break
  anomaly** (report as `ISO3|YEAR|indicator_id`) and is excluded before analysis.
- "Applicable" events = those whose entity is a resolved country, whose field is a
  requested indicator, and whose year is in the analysis window. Partition into
  applied vs non-applied event-id lists.

## Cohort construction (compute independently; report the audit counts)
Resolve every requested series, then build the declared cohorts:
- **Complete-case (per year)**: every *selected* health value present & non-
  suppressed & non-null, AND every required socioeconomic field (and RUCC, and any
  weight such as a `sample_size`) non-null. Never zero-fill a gap.
- **Reference/primary cohort**: complete in the reference year.
- **Balanced panel cohort**: complete in *every* analysis year (intersection).
- **ML / augmented cohort**: primary cohort ∩ complete on extra feature fields.
- **Strict dual-source cohort**: complete for outcome + primary series + parallel
  series + adjustments in every year.
Report exactly what the template asks: universe count, resolved-record counts by
year (health counts sum over the selected measures), per-year complete counts,
each cohort's n and its member/excluded id list (ascending), observation/panel-row
totals (e.g. balanced_counties × #panel-end-years), and the state census.

## Output contract
- One JSON object, exactly the template's required keys, no narrative outside it.
- Round every reported non-integer to the declared decimal places (usually 4; some
  tasks: 6 for computed reals, 4 for literal grids/thresholds) and encode as a JSON
  *number*. Counts, ranks, fold numbers, seeds, PRNG states, replicates are integers;
  booleans are booleans.
- **Preserve every declared order** (feature/coefficient/grid/checkpoint/division/
  source-group order). Never independently sort an array that is positionally
  aligned to another. Where the template says "sorted ascending", sort those.
- Identifiers exactly: uppercase 2-letter state codes, portal division names,
  uppercase ISO3, declared enum strings.
- Use JSON `null` only when a statistic is mathematically unavailable; never NaN/Inf.
