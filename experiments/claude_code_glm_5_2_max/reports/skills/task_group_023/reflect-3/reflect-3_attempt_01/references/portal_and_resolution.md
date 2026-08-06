# Portal datasets & evidence-resolution rules

## Portal access

- Base URL is supplied in the task prompt as `<TASK_ENV_BASE_URL>` (read from environment; credentials: none).
- **CSV export (use this for bulk loads):** `GET <BASE>/download?dataset=<name>&format=csv`. Filters available on browse pages (`GET <BASE>/data/<dataset>`) also work on the download endpoint as query params, but bulk CSV + local filtering is simplest.
- `GET <BASE>/catalog` — dataset list with columns, coverage, and filters.
- `GET <BASE>/methodology` — the resolution policy library (read it; only CURRENT documents bind). Key CURRENT documents:
  - *Surveillance release lifecycle v3.1* — FINAL replaces PROVISIONAL; highest applied FINAL revision governs; (the SUPERSEDED 2021 lifecycle and any DRAFT consultation are ignored).
  - *Small-number suppression v4.0* — suppressed/blank values are unavailable, never zero-filled.
  - *Quality flag interpretation v1.2* — flags describe review state, do not change release precedence; retain stale/caution flags in extracts; INVALID_SCALE/INVALID/WITHDRAWN excluded.
  - *State direct and rollup estimates v2.2* — DIRECT_SURVEY is the primary state series; COUNTY_ROLLUP is parallel, never silently substitutes.
  - *Crude and age-adjusted publication use v2.4* — age-adjusted supports state comparison; crude describes observed burden.
  - *Socioeconomic release fields v3.0* — socioeconomic fields revised independently; sparse null fields do not invalidate other published fields in the same record.
  - *Country indicator revision notices v2.7* — APPLIED scale corrections appear in a later FINAL revision; PENDING/WITHDRAWN do not authorize replacement.
  - *Indicator direction and units* — higher better / higher worse / neutral; units must be checked before combining.

## Dataset catalog (columns)

`states` (51 rows): `state_fips, state_abbr, state_name, region, division, is_state` — 4 regions, 9 census divisions; DC has `is_state=0` but is a jurisdiction (50_STATES_PLUS_DC ⇒ 51).

`counties` (1,224 rows): `county_fips, state_abbr, county_name, region, rucc, metro_class, population_base, latitude, longitude` — RUCC 1–3 metro, 4–9 nonmetro.

`countries` (72 rows): `iso3, canonical_name, portal_label, alternate_labels, region, income_group` — `alternate_labels` is pipe-separated; ISO3 codes are uppercase text (QA*/QB*/...). Country labels in requests are often aliases — reconcile via `canonical_name`, `portal_label`, and each `alternate_labels` entry.

`state_health` (coverage 2020–2024): `observation_id, state_fips, state_abbr, year, measure_id, value_type, source_type, release_status, revision, value, standard_error, sample_size, suppression_flag, quality_flag, released_at`. Measures: life_expectancy, adult_obesity, adult_smoking, diagnosed_diabetes, physical_inactivity, frequent_mental_distress, food_insecurity, premature_mortality_rate. `value_type` ∈ {AGE_ADJUSTED, CRUDE}; `source_type` ∈ {DIRECT_SURVEY, COUNTY_ROLLUP}.

`state_socioeconomic` (2020–2024): `record_id, state_fips, state_abbr, year, release_status, revision, released_at, poverty, bachelors, median_income, unemployment, uninsured, food_insecurity, population, quality_flag` — multi-field; sparse nulls OK; one FINAL record per (state,year) after revision resolution.

`county_health` (2021–2024): `observation_id, county_fips, state_abbr, region, year, measure_id, value_type, release_status, revision, released_at, value, low_ci, high_ci, population, suppression_flag, quality_flag`.

`county_socioeconomic` (2020–2024): `record_id, county_fips, state_abbr, region, year, release_status, revision, released_at, poverty, median_income, bachelors, unemployment, net_migration, uninsured, population, quality_flag`.

`country_indicators` (2013–2024): `observation_id, country_label, iso3, year, indicator_id, release_status, revision, released_at, value, unit, quality_flag`. Indicators: adult_mortality, alcohol_harm, bmi_burden, health_spending_gap, hiv_burden, immunization_gap, infant_mortality, life_expectancy, poverty_rate, schooling_gap, unemployment, urbanization. `quality_flag` includes `SCALE_REVIEW` (unresolved scale-break cell, wrong scale) and `CORRECTED` (APPLIED correction, right scale).

`revisions` (2015–2024): `revision_event_id, domain, entity_id, field_id, effective_year, old_value, new_value, status, issued_at, reason_code, note`. `domain` ∈ {COUNTRY, STATE_HEALTH, STATE_SES, COUNTY_HEALTH, COUNTY_SES}; `status` ∈ {APPLIED, WITHDRAWN, PENDING}; `reason_code` includes `SCALE_CORRECTION` (the scale-break notices) and `LATE_RESPONSE`/`GEOGRAPHY_RECODE`/`SOURCE_RESTATE` (routine 2024 release notices, not scale breaks).

## Resolution algorithm (apply to every dataset)

For a single-value table (health): for each natural key (geo, year, measure[, value_type, source_type]):
1. Keep `release_status == FINAL`.
2. Drop `quality_flag ∈ {INVALID_SCALE, INVALID, WITHDRAWN}`.
3. Drop `suppression_flag == 1` and blank/NaN `value`.
4. Pick the **highest `revision`**; tie-break `released_at` descending then `observation_id`/`record_id` descending. (Equivalent: sort ascending by `[revision, released_at, id]` and keep the last row.)
5. The retained `value` is the resolved observation.

For multi-field socioeconomic tables: same FINAL + revision pick per (geo, year), but do **not** drop the record for sparse null fields — keep the record and let individual fields be null. Each field is then read independently.

For country indicators: same as single-value, but a scale-break cell with an `APPLIED` SCALE_CORRECTION has a later `CORRECTED` FINAL revision (higher revision number) → resolution naturally yields the corrected value. A `WITHDRAWN`/`PENDING` SCALE_CORRECTION has no later correction → the retained `SCALE_REVIEW` value is the wrong-scale **anomaly** cell. Treat `SCALE_REVIEW` cells as unavailable for analysis (exclude then impute if the module needs a complete matrix).

## Cohort construction patterns

Read the request's `evidence_specification` / `publication_selection` / `scope_and_publication` for the exact per-task definitions. Recurring archetypes:
- **Core balanced panel:** jurisdictions complete for the core panel variables in **every** analysis year. `core_balanced_observation_n = state_n × n_years`. Report excluded jurisdiction codes.
- **Broad reference (cross-section):** jurisdictions complete at the reference year for the outcome and all ordered ridge/elastic-net features.
- **Strict dual-source:** complete for outcome + primary series + parallel series + adjustments in every year (used by source/year perturbation).
- **ML cohort:** primary-cohort members additionally complete for the ML feature set at the reference year.
- **Balanced county panel:** counties complete for required health + socioeconomic + RUCC fields across the balanced panel years.

"Complete" = every required variable present, non-suppressed, non-null, non-anomalous. Yearly complete counts are reported per analysis year. Never zero-fill.
