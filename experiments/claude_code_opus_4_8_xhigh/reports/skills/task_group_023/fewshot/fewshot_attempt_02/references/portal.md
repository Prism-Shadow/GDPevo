# Portal reference — Public Health Observatory web portal

The base URL and endpoint list are given per run in `environment_access.md`
(as `GDPEVO_ENV_BASE_URL` / `<TASK_ENV_BASE_URL>`). Treat that file as the only
source of the address; do not hardcode a host. All access is read-only HTTP GET.

## Endpoints

```
GET /                         portal home (human landing page)
GET /catalog                  dataset schemas + measure dictionary
GET /methodology              methodology library (release/quality policy)
GET /geographies/states       state reference (fips, abbr, name, region, division, is_state)
GET /geographies/counties     county reference (fips, abbr, name, region, rucc, metro_class, ...)
GET /geographies/countries    country reference (iso3, canonical_name, portal_label, alternate_labels, ...)
GET /data/state-health        state health observations (browsable HTML)
GET /data/state-socioeconomic state socioeconomic releases
GET /data/county-health       county health observations
GET /data/county-socioeconomic county socioeconomic releases
GET /data/country-indicators  country indicator observations
GET /data/revisions           revision notices (scale corrections etc.)
GET /download                 CSV export of any dataset (see below)
```

The `/data/*` and `/geographies/*` pages render **paginated HTML tables** (page
size selectable, e.g. 25/50/100/200). For analysis, prefer the CSV export, which
returns **all matching rows unpaginated**.

## CSV download pattern (preferred data access)

```
GET /download?dataset=<name>&format=csv[&<filter>=<value> ...]
```

- `format=csv` is **required** (other values / omission → "Invalid request").
- `dataset` is the catalog dataset name (see table below), e.g. `state_health`,
  `state_socioeconomic`, `county_health`, `county_socioeconomic`,
  `country_indicators`, `states`, `counties`, `countries`, `revisions`.
- Filters are the catalog's declared filter columns for that dataset. Filter
  values are matched as **exact values**; the revisions filters accept
  **comma-separated** lists of exact values. Missing cells render as an em dash
  in HTML; in CSV they are empty fields.
- Response is a header row + data rows. Pull the whole dataset (or a
  server-side-filtered slice) and do the release resolution / joins yourself.

Example: `GET /download?dataset=state_health&format=csv&state_abbr=CA&measure_id=life_expectancy`

Fetch programmatically (e.g. `curl`) and parse the CSV. Downloading a full
dataset unfiltered is fine (largest, `county_health`, is ~48k rows).

## Datasets and columns (from `/catalog`)

Coverage years and row counts drift; always re-read `/catalog`. Column sets:

- **states** — `state_fips, state_abbr, state_name, region, division, is_state`.
  Filters: `state_abbr, state_fips, region, division`. Holds the census
  **division** used for division-clustered modules and the **region** used for
  region fixed effects / regional scope.
- **counties** — `county_fips, state_abbr, county_name, region, rucc,
  metro_class, population_base, latitude, longitude`.
  Filters: `county_fips, state_abbr, region, rucc, metro_class`. `rucc` is the
  Rural-Urban Continuum Code (integer 1–9) used for RUCC indicators/bands.
- **countries** — `iso3, canonical_name, portal_label, alternate_labels,
  region, income_group`. Filters: `iso3, label, region, income_group`.
  `alternate_labels` supports label→ISO3 reconciliation (aliases).
- **state_health** — `observation_id, state_fips, state_abbr, year, measure_id,
  value_type, source_type, release_status, revision, value, standard_error,
  sample_size, suppression_flag, quality_flag, released_at`.
  Filters: `state_abbr, measure_id, year, value_type, source_type,
  release_status, revision`.
- **state_socioeconomic** — `record_id, state_fips, state_abbr, year,
  release_status, revision, released_at, poverty, bachelors, median_income,
  unemployment, uninsured, food_insecurity, population, quality_flag`.
  Filters: `state_abbr, year, release_status, revision`.
- **county_health** — `observation_id, county_fips, state_abbr, region, year,
  measure_id, value_type, release_status, revision, released_at, value, low_ci,
  high_ci, population, suppression_flag, quality_flag`.
  Filters: `county_fips, state_abbr, region, measure_id, year, value_type,
  release_status, revision, suppression_flag`.
- **county_socioeconomic** — `record_id, county_fips, state_abbr, region, year,
  release_status, revision, released_at, poverty, median_income, bachelors,
  unemployment, net_migration, uninsured, population, quality_flag`.
  Filters: `county_fips, state_abbr, region, year, release_status, revision`.
- **country_indicators** — `observation_id, country_label, iso3, year,
  indicator_id, release_status, revision, released_at, value, unit,
  quality_flag`.
  Filters: `iso3, country_label, indicator_id, year, release_status, revision,
  quality_flag`.
- **revisions** — `revision_event_id, domain, entity_id, field_id,
  effective_year, old_value, new_value, status, issued_at, reason_code, note`.
  Filters: `domain, entity_id, field_id, effective_year, status`.

The `/catalog` page also prints a **measure dictionary** (domain, measure_id,
display_name, unit, direction such as HIGHER_WORSE / HIGHER_BETTER / NEUTRAL).
Check units before combining indicators; percentages and rates are not
interchangeable.

## Release / revision resolution semantics (from `/methodology`)

Read the request's declared resolution, but the portal's standing policy is:

- **Release lifecycle.** Records carry `release_status` (e.g. FINAL,
  PROVISIONAL) and an integer `revision`. Final releases may supersede
  provisional ones. Canonical selection for one final record per key:
  **greatest `revision`, then latest `released_at`, then the record-id
  tiebreak the request names** (lowest or greatest `observation_id`/`record_id`).
- **Value type / source type.** `value_type` distinguishes AGE_ADJUSTED vs
  CRUDE; `source_type` distinguishes DIRECT_SURVEY vs COUNTY_ROLLUP. Direct
  survey is the primary series; **county rollups are parallel estimates for
  coverage review and must not silently replace direct records**. Filter to the
  requested value_type/source_type before resolving.
- **Suppression & validity.** `suppression_flag=1` means the value is withheld
  though metadata remains; a suppressed/blank/null value is **unavailable and
  never zero**. `quality_flag` describes review state (e.g. REVIEWED, caution,
  stale) and does **not** change release precedence, but the request may name
  specific invalid flags (e.g. INVALID_SCALE, INVALID, WITHDRAWN) that exclude a
  record.
- **Revisions dataset.** Scale-correction and other notices have a `status`.
  Only **APPLIED** notices are reflected in later final revisions; **PENDING /
  WITHDRAWN / DRAFT** notices do **not** authorize replacing a published value.
  Unresolved scale breaks (e.g. an apparent order-of-magnitude discontinuity
  that no applied notice corrects) are treated as anomalies/quality exclusions
  when the request asks for that audit.
- **Label reconciliation (countries).** Requests may give portal labels or
  aliases; reconcile each to a stable **ISO3** via `canonical_name` /
  `portal_label` / `alternate_labels`. Count alias resolutions where the
  resolved label differs from the canonical name if the template asks.
- **Geographic identifiers.** FIPS codes are text with meaningful leading zeros;
  keep them as strings. Region and census division come from the geography
  reference, not the observation rows.

Socioeconomic fields are revised independently; a sparse null field does not
invalidate other published fields in the same record. Population and net
migration are released separately and may move up or down year to year.
