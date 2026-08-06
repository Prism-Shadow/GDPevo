# PHO portal reference

The Public Health Observatory (PHO) portal is a **read-only** web app. It is the
sole authoritative evidence source. Never invent, memorize, or reuse values from
a previous task — every number must be pulled live for the current request.

## Reaching the portal

The base URL is provided out-of-band, not in the task payload. Read it from
`environment_access.md` (variable `GDPEVO_ENV_BASE_URL`, e.g.
`http://task-env:9023/`). Task prompts refer to it as `<TASK_ENV_BASE_URL>`.
Confirm connectivity with `GET /` before doing analysis.

Available routes (all GET):

```
/                         portal home
/catalog                  dataset list, columns, filters, measure dictionary
/geographies/states       state reference (browse)
/geographies/counties     county reference (browse)
/geographies/countries    country reference (browse)
/data/state-health        browse UI (also has CSV export)
/data/state-socioeconomic
/data/county-health
/data/county-socioeconomic
/data/country-indicators
/data/revisions
/methodology              methodology library index + ?doc=<id> pages
/download                 CSV export — the machine-readable data path
```

## Pulling data: use `/download`

Browse pages return HTML. For analysis, use the CSV export:

```
/download?dataset=<name>&format=csv&<filter>=<value>&...
```

- `format` **must** be `csv` (JSON is rejected).
- A filter with an **empty value is rejected** ("Filter X cannot be empty") —
  omit filters you are not constraining rather than passing blanks.
- The response is the full filtered CSV (no pagination observed). Filter server
  side where possible, then finish filtering/joining locally.
- `dataset` names are the catalog identifiers (underscored):
  `states, counties, countries, state_health, state_socioeconomic,
  county_health, county_socioeconomic, country_indicators, revisions`.

Always re-read `/catalog` at runtime to confirm the exact column list, row
counts, coverage years, and the measure dictionary — treat the schema below as
orientation, not gospel.

## Dataset schemas (as observed)

Geography (dimension tables):

- `states`: `state_fips, state_abbr, state_name, region, division, is_state`.
  Filters: `state_abbr, state_fips, region, division`. (51 rows = 50 + DC.)
- `counties`: `county_fips, state_abbr, county_name, region, rucc, metro_class,
  population_base, latitude, longitude`. Filters: `county_fips, state_abbr,
  region, rucc, metro_class`.
- `countries`: `iso3, canonical_name, portal_label, alternate_labels, region,
  income_group`. Filters: `iso3, label, region, income_group`.
  `portal_label` + `alternate_labels` are what you reconcile requested country
  labels against to resolve an ISO3.

Publication (fact tables) — each carries release/audit provenance:

- `state_health`: `observation_id, state_fips, state_abbr, year, measure_id,
  value_type, source_type, release_status, revision, value, standard_error,
  sample_size, suppression_flag, quality_flag, released_at`.
- `state_socioeconomic`: `record_id, state_fips, state_abbr, year,
  release_status, revision, released_at, poverty, bachelors, median_income,
  unemployment, uninsured, food_insecurity, population, quality_flag`.
- `county_health`: `observation_id, county_fips, state_abbr, region, year,
  measure_id, value_type, release_status, revision, released_at, value, low_ci,
  high_ci, population, suppression_flag, quality_flag`.
- `county_socioeconomic`: `record_id, county_fips, state_abbr, region, year,
  release_status, revision, released_at, poverty, median_income, bachelors,
  unemployment, net_migration, uninsured, population, quality_flag`.
- `country_indicators`: `observation_id, country_label, iso3, year,
  indicator_id, release_status, revision, released_at, value, unit,
  quality_flag`.
- `revisions`: `revision_event_id, domain, entity_id, field_id, effective_year,
  old_value, new_value, status, issued_at, reason_code, note`. Statuses seen:
  `APPLIED`, `WITHDRAWN`, (and draft/pending variants). `APPLIED` corrections are
  already reflected in later final revisions; `WITHDRAWN`/pending notices do not
  replace published values. Interpret per the methodology docs.

## Read the methodology library first

`/methodology` indexes governing docs. Their rules are binding and change the
numbers, so read the ones your request touches before computing. Docs observed:
release lifecycle, crude vs age-adjusted publication use, small-number
suppression, quality-flag interpretation, revision notices (state & country),
state direct vs rollup estimates, socioeconomic release fields, county
comparability windows, indicator direction/units, influence diagnostics,
geographic identifiers. Bind their definitions of validity, suppression, and
release-status semantics into your resolution step.
