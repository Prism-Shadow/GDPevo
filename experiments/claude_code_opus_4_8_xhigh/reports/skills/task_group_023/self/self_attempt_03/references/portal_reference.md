# Portal reference — Public Health Observatory data portal

The evidence source is a single read-only web portal. Its base URL is the value of
`GDPEVO_ENV_BASE_URL` in `environment_access.md` (observed: `http://task-env:9023/`)
and is what the prompts abbreviate as `<TASK_ENV_BASE_URL>`. Everything below was
confirmed against the live portal; treat column/row counts as illustrative (they may
shift per instance) and always re-read `/catalog` and `/methodology` for the instance
you are handed.

## Endpoints (GET)

| Path | Purpose |
|------|---------|
| `/` | Home / nav |
| `/catalog` | Dataset inventory: per-dataset row count, coverage years, **columns (with types)**, and **valid filters**; plus the measure dictionary |
| `/geographies/states` · `/geographies/counties` · `/geographies/countries` | HTML browse of geography reference tables |
| `/data/state-health` · `/data/state-socioeconomic` · `/data/county-health` · `/data/county-socioeconomic` · `/data/country-indicators` · `/data/revisions` | HTML browse of data tables (accept the same filters as the matching dataset) |
| `/methodology` | Methodology library — the publication *rules* (see bottom) |
| `/download` | **Machine export.** `?dataset=<name>&format=csv[&<filter>=<value>...]` returns CSV with a header row |

Notes:
- `format=csv` is accepted **only** on `/download`. Passing `format` (or any unknown
  filter) to `/data/*` returns "Invalid request — Unsupported parameter". An unknown
  `dataset` returns "Invalid request — Unknown dataset".
- Prefer `/download` CSV for all real work: pull the dataset (optionally filtered),
  parse locally, and keep the raw pull for reproducibility. Filters compose with `&`.
- Datasets are the underscore names below; the browse routes use hyphens.

## Datasets, columns, filters

`states` (51 rows — 50 states + DC) — `state_fips, state_abbr, state_name, region,
division, is_state`. Filters: `state_abbr, state_fips, region, division`.

`counties` (~1,224) — `county_fips, state_abbr, county_name, region, rucc,
metro_class, population_base, latitude, longitude`. Filters: `county_fips,
state_abbr, region, rucc, metro_class`.

`countries` (~72) — `iso3, canonical_name, portal_label, alternate_labels, region,
income_group`. Filters: `iso3, label, region, income_group`.
`alternate_labels` is a `|`-delimited list of aliases including the portal label.

`state_health` (~4,861; 2020–2024) — `observation_id, state_fips, state_abbr, year,
measure_id, value_type, source_type, release_status, revision, value,
standard_error, sample_size, suppression_flag, quality_flag, released_at`. Filters:
`state_abbr, measure_id, year, value_type, source_type, release_status, revision`.

`state_socioeconomic` (~323; 2020–2024) — `record_id, state_fips, state_abbr, year,
release_status, revision, released_at, poverty, bachelors, median_income,
unemployment, uninsured, food_insecurity, population, quality_flag`. Filters:
`state_abbr, year, release_status, revision`.

`county_health` (~47,938; 2021–2024) — `observation_id, county_fips, state_abbr,
region, year, measure_id, value_type, release_status, revision, released_at, value,
low_ci, high_ci, population, suppression_flag, quality_flag`. Filters: `county_fips,
state_abbr, region, measure_id, year, value_type, release_status, revision,
suppression_flag`. (County health has no `source_type` column; state health does.)

`county_socioeconomic` (~6,772; 2020–2024) — `record_id, county_fips, state_abbr,
region, year, release_status, revision, released_at, poverty, median_income,
bachelors, unemployment, net_migration, uninsured, population, quality_flag`.
Filters: `county_fips, state_abbr, region, year, release_status, revision`.

`country_indicators` (~9,812; 2013–2024) — `observation_id, country_label, iso3,
year, indicator_id, release_status, revision, released_at, value, unit,
quality_flag`. Filters: `iso3, country_label, indicator_id, year, release_status,
revision, quality_flag`.

`revisions` (~130; 2015–2024) — `revision_event_id, domain, entity_id, field_id,
effective_year, old_value, new_value, status, issued_at, reason_code, note`.
Filters: `domain, entity_id, field_id, effective_year, status`.
`domain` observed values include `COUNTRY`, `STATE_HEALTH`; `status` ∈ {`APPLIED`,
`WITHDRAWN`, `PENDING`}; `reason_code` ∈ {`SCALE_CORRECTION`, `SOURCE_RESTATE`, ...}.

## Geography reference (stable)

- **4 regions:** Midwest, Northeast, South, West.
- **9 census divisions:** New England, Middle Atlantic, East North Central,
  West North Central, South Atlantic, East South Central, West South Central,
  Mountain, Pacific. (Modules that group/cluster "by census division" produce
  9 groups; use portal division names exactly.)
- FIPS are TEXT; leading zeros are meaningful; a county FIPS is its 2-char state
  code followed by a 3-char county suffix.
- RUCC 1–3 = metropolitan, 4–9 = nonmetropolitan; RUCC lives on the county geography.

## Measure dictionary (from `/catalog`)

The catalog lists, per domain, `measure_id → display_name, unit, direction`
(`HIGHER_WORSE` / `HIGHER_BETTER` / `NEUTRAL`). Examples: COUNTRY
`life_expectancy` (years, HIGHER_BETTER), `adult_mortality` (deaths per 100k,
HIGHER_WORSE), `bmi_burden`/`poverty_rate`/`schooling_gap`/`immunization_gap`/
`hiv_burden`/`infant_mortality`/`health_spending_gap` (HIGHER_WORSE); COUNTY_HEALTH
`adult_obesity`, `adult_smoking`, etc. Check units before combining indicators
(percentages and mortality rates are not interchangeable) and check direction when a
task talks about "burden".

## Methodology library (the publication rules — `/methodology`)

Read these; the audits are graded against them. Current (non-superseded, non-draft)
documents and their operative content:

- **Surveillance release lifecycle** — Provisional supports timely review; FINAL
  replaces provisional; *the highest applied final revision governs when several
  final revisions exist.*
- **State direct and rollup estimates** — DIRECT_SURVEY is the primary state series;
  COUNTY_ROLLUP are parallel estimates for coverage review and must **not** silently
  replace direct records.
- **Crude and age-adjusted publication use** — Age-adjusted supports cross-state
  comparison where specified; crude describes observed county burden.
- **Small-number suppression** — Suppressed rows keep identifying/release metadata
  but publish no value; **never treat suppressed or missing as zero.**
- **Quality flag interpretation** — Flags describe review state, do **not** change
  release precedence, and should be retained in audit extracts (e.g. stale/caution).
- **Country indicator revision notices** — Applied scale corrections appear in later
  final revisions; pending/withdrawn notices do not authorise replacement; reconcile
  portal labels to stable ISO3-like identifiers.
- **Country label reconciliation** — Portal labels can differ from canonical names;
  use ISO3-like ids and the alternate-label reference to reconcile across releases.
- **Socioeconomic release fields** — Fields are revised independently; a sparse null
  field does not invalidate other published fields in the same record.
- **Geographic identifiers** — FIPS are text; leading zeros meaningful; county id =
  state code + county suffix.
- **Rural-Urban Continuum Codes** — 1–3 metro, 4–9 nonmetro; RUCC on county geography.
- **Influence diagnostics guidance** — report declared model, eligible record set,
  and the effect of any sensitivity exclusion.

Ignore `DRAFT` ("Draft revision consultation") and `SUPERSEDED` ("Earlier
surveillance release lifecycle") documents for current publication decisions.
