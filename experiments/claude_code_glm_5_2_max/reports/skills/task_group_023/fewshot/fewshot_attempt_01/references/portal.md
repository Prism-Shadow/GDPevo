# PHO Portal Reference

The Public Health Observatory (PHO) Data Portal is the **only authorized evidence
source**. Reach it only through `environment_access.md`: the base URL
(`GDPEVO_ENV_BASE_URL`, e.g. `http://task-env:9023/`) and the allow-list of
endpoints. No other network source is permitted.

## Allowed endpoints

- `GET /` — portal home.
- `GET /catalog` — dataset catalog: per-dataset row counts, coverage years,
  columns, available filters, and the measure dictionary.
- `GET /geographies/states` · `/geographies/counties` · `/geographies/countries` —
  geography reference (HTML browse).
- `GET /data/state-health` · `/data/state-socioeconomic` · `/data/county-health` ·
  `/data/county-socioeconomic` · `/data/country-indicators` · `/data/revisions` —
  browsable data with query filters.
- `GET /methodology` — methodology library (document index + per-doc text via
  `?doc=<slug>`).
- `GET /download?dataset=<name>&format=csv&<filter>=<value>&...` — **CSV export**
  of any filtered dataset. This is the cleanest way to ingest rows.

## How to fetch rows

Prefer CSV: `/download?dataset=<dataset>&format=csv&<filter>=<value>&...`. The
first row is a header; values are comma-separated; types follow the catalog
(REAL/INTEGER/TEXT). Filter names and allowed values are listed per dataset in the
catalog. The HTML browse pages (`/data/...`, `/geographies/...`) render the same
filtered rows but require stripping markup — use them only for ad-hoc inspection.

Combine filters to scope fetches (e.g. `measure_id=...&year=...&release_status=...`
on health data). Filters are exact-match; partial/unknown values return
`Invalid request`. For repeated entity labels (e.g. country `portal_label`), match
a known label exactly or reconcile via the geography reference.

## Datasets (columns · coverage · key filters)

### `states` — 51 rows (50 states + DC)
`state_fips` (TEXT), `state_abbr` (TEXT), `state_name` (TEXT), `region` (TEXT),
`division` (TEXT), `is_state` (INTEGER). Filters: `state_abbr`, `state_fips`,
`region`, `division`. Region values include `South`, `West`, `Midwest`,
`Northeast`; division values include the nine Census divisions (e.g.
`East South Central`, `Mountain`, `Pacific`). DC is present (`is_state` flags
statehood).

### `counties` — 1,224 rows
`county_fips` (TEXT), `state_abbr` (TEXT), `county_name` (TEXT), `region` (TEXT),
`rucc` (INTEGER 1–9), `metro_class` (TEXT), `population_base` (INTEGER),
`latitude` (REAL), `longitude` (REAL). Filters: `county_fips`, `state_abbr`,
`region`, `rucc`, `metro_class`. `county_fips` is the 2-char state code + 3-char
county suffix; **leading zeros are meaningful** (FIPS are TEXT). RUCC 1–3 =
metropolitan, 4–9 = nonmetropolitan.

### `countries` — 72 rows
`iso3` (TEXT), `canonical_name` (TEXT), `portal_label` (TEXT),
`alternate_labels` (TEXT), `region` (TEXT), `income_group` (TEXT). Filters:
`iso3`, `label`, `region`, `income_group`. **`portal_label` can differ from
`canonical_name`**; reconcile analyst-supplied labels to stable `iso3` via
`portal_label` / `alternate_labels` / `canonical_name`.

### `state_health` — 4,861 rows, coverage 2020–2024
`observation_id`, `state_fips`, `state_abbr`, `year`, `measure_id`, `value_type`,
`source_type`, `release_status`, `revision` (INTEGER), `value` (REAL),
`standard_error` (REAL), `sample_size` (INTEGER), `suppression_flag` (INTEGER),
`quality_flag` (TEXT), `released_at` (TEXT). Filters: `state_abbr`, `measure_id`,
`year`, `value_type`, `source_type`, `release_status`, `revision`.

- `value_type`: `AGE_ADJUSTED` or `CRUDE`.
- `source_type`: `DIRECT_SURVEY` (primary state series) or `COUNTY_ROLLUP`
  (parallel coverage estimate — do not silently substitute for direct).
- `release_status`: `FINAL` (supersedes provisional) vs provisional.
- Multiple final revisions per key can coexist (e.g. revision 1 `REVIEWED` and
  revision 2 `REVISED`); pick by the request's declared priority.
- `suppression_flag=1` means no published `value` — treat as unavailable, never 0.
- `quality_flag` describes review state (e.g. `REVIEWED`, `REVISED`,
  `PARALLEL_ESTIMATE`); it does **not** change release precedence — retain it.

### `state_socioeconomic` — 323 rows, coverage 2020–2024
`record_id`, `state_fips`, `state_abbr`, `year`, `release_status`, `revision`,
`released_at`, `poverty`, `bachelors`, `median_income`, `unemployment`,
`uninsured`, `food_insecurity`, `population`, `quality_flag`. Filters:
`state_abbr`, `year`, `release_status`, `revision`. Fields are revised
independently; a sparse null in one field does **not** invalidate other fields in
the same record. Record-id tie-break direction is task-local.

### `county_health` — 47,938 rows, coverage 2021–2024
`observation_id`, `county_fips`, `state_abbr`, `region`, `year`, `measure_id`,
`value_type`, `release_status`, `revision`, `released_at`, `value`, `low_ci`,
`high_ci`, `population`, `suppression_flag`, `quality_flag`. Filters:
`county_fips`, `state_abbr`, `region`, `measure_id`, `year`, `value_type`,
`release_status`, `revision`, `suppression_flag`. County health has `value_type`
but no `source_type`; CI bounds accompany the value.

### `county_socioeconomic` — 6,772 rows, coverage 2020–2024
`record_id`, `county_fips`, `state_abbr`, `region`, `year`, `release_status`,
`revision`, `released_at`, `poverty`, `median_income`, `bachelors`,
`unemployment`, `net_migration`, `uninsured`, `population`, `quality_flag`.
Filters: `county_fips`, `state_abbr`, `region`, `year`, `release_status`,
`revision`. Population and net_migration are separately released and may move in
either direction year over year.

### `country_indicators` — 9,812 rows, coverage 2013–2024
`observation_id`, `country_label`, `iso3`, `year`, `indicator_id`,
`release_status`, `revision`, `released_at`, `value`, `unit`, `quality_flag`.
Filters: `iso3`, `country_label`, `indicator_id`, `year`, `release_status`,
`revision`, `quality_flag`. Check `unit` before combining indicators (percentages
vs mortality rates are not interchangeable). Applied scale corrections appear in
later final revisions; pending/withdrawn notices do **not** authorize replacement.

### `revisions` — 130 rows, coverage 2015–2024
`revision_event_id`, `domain` (e.g. `COUNTRY`, `STATE_HEALTH`), `entity_id`,
`field_id`, `effective_year`, `old_value`, `new_value`, `status`, `issued_at`,
`reason_code`, `note`. Filters: `domain`, `entity_id`, `field_id`,
`effective_year`, `status`. `status` is `APPLIED` / pending / withdrawn; only
`APPLIED` authorizes publication use. `reason_code` includes `SCALE_CORRECTION`
(apparent unit/scale discontinuity — `old` vs `new` differ by ~10×) and
`SOURCE_RESTATE` (routine release notice). Use this for quality-audit modules
that report applied vs non-applied events and unresolved scale-break anomalies.

## Measure dictionary (`/catalog`)

The catalog lists every `measure_id` with `domain`, `display_name`, `unit`, and
`direction` (`HIGHER_WORSE` / `HIGHER_BETTER` / `NEUTRAL`). Domains: `COUNTRY`,
`COUNTY_HEALTH`, `STATE_HEALTH`. Verify a measure exists in the right domain before
fetching; some ids (e.g. `adult_obesity`, `diagnosed_diabetes`) appear in both
state and county domains with different coverage years.

## Methodology library (`/methodology`)

Index page lists documents with version, date, status (`CURRENT` / `DRAFT` /
`SUPERSEDED`), and topic; fetch a doc with `?doc=<slug>`. Authoritative facts:

- **Release lifecycle** (`release-lifecycle`, CURRENT): provisional supports timely
  review; **final replaces provisional**; the **highest applied final revision**
  governs when several final revisions exist. The earlier `release-lifecycle-v2`
  is **SUPERSEDED** — do not apply it. Draft docs (e.g. `revisions-draft`) do not
  supersede policy.
- **Suppression** (`suppression`): suppressed rows retain metadata but publish no
  value; **never treat suppressed/missing as zero**.
- **Value types** (`publication-values`): age-adjusted supports state comparison;
  crude retains each county's population structure.
- **State direct vs rollup** (`state-estimates`): direct survey is the primary
  state series; county rollups are parallel estimates for coverage review.
- **Quality flags** (`quality`): describe review state, do not change precedence;
  retain stale/caution flags in extracts.
- **Socioeconomic fields** (`socioeconomic-fields`): revised independently; sparse
  nulls don't invalidate sibling fields.
- **Geographic IDs** (`geographic-ids`): FIPS are TEXT; leading zeros meaningful;
  county FIPS = 2-char state + 3-char county.
- **RUCC** (`rucc`): 1–3 metropolitan, 4–9 nonmetropolitan; belongs to county
  geography.
- **Country labels** (`aliases`): `portal_label` ≠ `canonical_name`; reconcile via
  `alternate_labels` and `iso3`.
- **Influence diagnostics** (`influence`): report declared model, eligible record
  set, and the effect of any sensitivity exclusion.

## Fetch discipline

- Always filter server-side to keep payloads small; combine `measure_id`, `year`,
  `release_status`, `value_type`, `source_type` as the request requires.
- Preserve the full release metadata (`revision`, `released_at`, record/observation
  id) for every candidate row — you need it for tie-breaks.
- Keep `suppression_flag`, `quality_flag`, `sample_size`, `standard_error`,
  low/high CI as the modules may consume them (e.g. reliability weights, validity
  filters, audit reporting).
- Re-fetch rather than cache across tasks; the portal is the source of truth.
