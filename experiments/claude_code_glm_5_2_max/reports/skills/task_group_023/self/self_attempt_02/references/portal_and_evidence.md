# Portal and Evidence Resolution

The single evidence source is the read-only Public Health Observatory (PHO) Web portal. This file captures the portal shape and the release/revision/quality rules that govern evidence resolution. All facts here are portal-level and stable across tasks; nothing here is a task-specific final value.

## Base URL and access

- Resolve the base URL from `environment_access.md`: `<TASK_ENV_BASE_URL>` maps to `GDPEVO_ENV_BASE_URL` (e.g. `http://task-env:9023/`).
- **No credentials.** Read-only GET access only.
- Allowed endpoints (per `environment_access.md`):
  - `GET /` — portal home.
  - `GET /catalog` — dataset catalog + measure dictionary.
  - `GET /geographies/states`, `/geographies/counties`, `/geographies/countries` — geography reference (HTML browse).
  - `GET /data/state-health`, `/data/state-socioeconomic`, `/data/county-health`, `/data/county-socioeconomic`, `/data/country-indicators`, `/data/revisions` — data browse (HTML).
  - `GET /methodology` — methodology library.
  - `GET /download` — machine-readable CSV export.
- Use only these endpoints. Do not invent paths.

## Machine-readable extraction (use this)

- Browse endpoints (`/data/*`, `/geographies/*`) return **HTML tables** and reject a `format` query parameter (`Unsupported parameter: format`). They also ignore `Accept: application/json`.
- The canonical machine-readable path is **`/download?dataset=<dataset>&format=csv`** with the same filter query params the browse form accepts. Example: `/download?dataset=state_health&format=csv&state_abbr=DC&year=2023&measure_id=life_expectancy&release_status=FINAL`.
- Filters accept **comma-separated exact values** (e.g. `year=2022,2023`). Filter keys per dataset are listed in the catalog.
- Prefer downloading whole datasets (or tightly filtered subsets) as CSV and parsing locally, rather than scraping HTML. Cache the extracts for the duration of the task.

## Dataset schemas (from `/catalog`)

| dataset | key columns | filters | coverage |
|---|---|---|---|
| `states` | state_fips, state_abbr, state_name, region, division, is_state | state_abbr, state_fips, region, division | 51 rows |
| `counties` | county_fips, state_abbr, county_name, region, rucc, metro_class, population_base, latitude, longitude | county_fips, state_abbr, region, rucc, metro_class | 1,224 rows |
| `countries` | iso3, canonical_name, portal_label, alternate_labels, region, income_group | iso3, label, region, income_group | 72 rows |
| `state_health` | observation_id, state_fips, state_abbr, year, measure_id, value_type, source_type, release_status, revision, value, standard_error, sample_size, suppression_flag, quality_flag, released_at | state_abbr, measure_id, year, value_type, source_type, release_status, revision | 2020–2024 |
| `state_socioeconomic` | record_id, state_fips, state_abbr, year, release_status, revision, released_at, poverty, bachelors, median_income, unemployment, uninsured, food_insecurity, population, quality_flag | state_abbr, year, release_status, revision | 2020–2024 |
| `county_health` | observation_id, county_fips, state_abbr, region, year, measure_id, value_type, release_status, revision, released_at, value, low_ci, high_ci, population, suppression_flag, quality_flag | county_fips, state_abbr, region, measure_id, year, value_type, release_status, revision, suppression_flag | 2021–2024 |
| `county_socioeconomic` | record_id, county_fips, state_abbr, region, year, release_status, revision, released_at, poverty, median_income, bachelors, unemployment, net_migration, uninsured, population, quality_flag | county_fips, state_abbr, region, year, release_status, revision | 2020–2024 |
| `country_indicators` | observation_id, country_label, iso3, year, indicator_id, release_status, revision, released_at, value, unit, quality_flag | iso3, country_label, indicator_id, year, release_status, revision, quality_flag | 2013–2024 |
| `revisions` | revision_event_id, domain, entity_id, field_id, effective_year, old_value, new_value, status, issued_at, reason_code, note | domain, entity_id, field_id, effective_year, status | 2015–2024 |

Notes:
- Health observation rows carry `value_type` (e.g. `AGE_ADJUSTED`, `CRUDE`), `source_type` (e.g. `DIRECT_SURVEY`, `COUNTY_ROLLUP`), `release_status` (e.g. `PROVISIONAL`, `FINAL`), integer `revision`, `suppression_flag`, and `quality_flag`. These are the fields the request filters on.
- The measure dictionary in `/catalog` declares each measure's `unit` and `direction` (`HIGHER_WORSE` / `HIGHER_BETTER` / `NEUTRAL`). Check units before combining indicators; percentages and mortality rates are not interchangeable.

## Release, revision, and quality resolution

Apply these rules when selecting which record represents a given (geography, year, measure, value_type, source_type):

1. **FINAL governs.** Provisional records support timely review but final records replace them for publication. Select `release_status = FINAL` unless the request explicitly says otherwise.
2. **Highest applied final revision wins.** When several final revisions exist for the same cell, the highest applied final `revision` number governs. Use the `revisions` dataset to confirm which revision events are `status = APPLIED` (vs `PENDING` / `WITHDRAWN`). Track applied vs non-applied revision event ids when the template asks for them.
3. **Pending/withdrawn never replace.** `PENDING` and `WITHDRAWN` revision notices do not authorize replacing a published value.
4. **Revision priority.** When the request declares a tie-break priority (e.g. `revision`, then `released_at`, then the record id), apply it in that order.
5. **Quality flags do not change release precedence.** A `REVIEWED`, stale, or caution flag describes review state; retain it in the audit extract. Exclude only the quality flags the request lists as invalid (commonly `INVALID`, `INVALID_SCALE`, `WITHDRAWN`).
6. **Suppression and missing are unavailable — never zero.** A suppressed (`suppression_flag = 1`) or blank `value` retains its identifying and release metadata but publishes no value. Treat it as unavailable. Never zero-fill. A cohort's "complete case" rule means the required values are present, nonsuppressed, and non-null.
7. **Socioeconomic fields are revised independently.** A sparse null in one socioeconomic field does not invalidate other published fields in the same record. Decide field-level completeness per the request's cohort rule.
8. **Value types are not interchangeable.** Age-adjusted values support cross-geography comparison where specified; crude values describe observed burden and retain local population structure. Select the `value_type` the request declares for each series (primary vs parallel exposure, etc.).
9. **Direct vs rollup.** Direct survey estimates are the primary state publication series; county rollups are parallel estimates for coverage review and must not silently replace direct records. When a module contrasts direct vs rollup sources, keep both and replace per the module's declared scenario rule.
10. **Resolve independently.** Resolve each measure/year/series from the portal on its own; do not let one measure's selection contaminate another's.

## Identifier rules

- **State codes:** uppercase two-letter `state_abbr` (e.g. `DC`). The jurisdiction universe is the 51 states+DC rows in `states` (`is_state = 1`).
- **FIPS are text.** `state_fips` and `county_fips` are strings; leading zeros are meaningful. A county FIPS is the 2-char state code followed by a 3-char county suffix.
- **ISO3:** uppercase. Country requests arrive as free-text labels; reconcile them to stable ISO3 via `countries.canonical_name`, `portal_label`, and `alternate_labels` (comma-separated alias list). Count alias resolutions when the template asks.
- **Division and region names:** use the portal's `division` and `region` strings verbatim (e.g. `East South Central`, `Pacific`, `South`, `West`). Census divisions number nine.
- **RUCC:** integer 1–9, lives on the county geography reference. RUCC 1–3 are metropolitan; 4–9 nonmetropolitan. When a model uses RUCC indicators, one category (commonly RUCC 1) is the reference and is omitted.

## Cohort archetypes

Requests name cohorts; resolve each from portal records using its completeness rule. Recurring archetypes:

- **Reference-year complete-case (primary):** jurisdictions complete for the outcome and required fields in the reference year only.
- **Balanced panel:** jurisdictions (or counties) complete in **every** requested analysis year. The balanced cohort is the intersection of complete-case sets across years.
- **Broad / machine-learning cohort:** primary-cohort members also complete for all ordered prediction features (often adds unemployment, net_migration, uninsured, etc.).
- **Strict dual-source cohort:** complete for outcome + primary exposure + parallel exposure + adjustments in every analysis year.

Compute **complete exclusion sets** exactly as the template specifies — e.g. "every jurisdiction-universe state code absent from the reference-year primary cohort, and no others," reported in the declared order (often ascending ASCII). Excluded-code lists are *sets* (sorted) only when the template says so; otherwise preserve declared order.

## Methodology library (`/methodology`)

The library lists documents with a status (`CURRENT`, `DRAFT`, `SUPERSEDED`). **Use CURRENT documents only** to interpret release, revision, quality, suppression, value-type, RUCC, and label-reconciliation semantics. DRAFT and SUPERSEDED documents do not govern publication policy. Key CURRENT topics: release lifecycle, small-number suppression, quality-flag interpretation, crude vs age-adjusted publication use, state direct vs rollup estimates, socioeconomic release fields, country indicator revisions, country label reconciliation, geographic identifiers, RUCC, indicator direction/units, influence diagnostics, county socioeconomic comparability.
