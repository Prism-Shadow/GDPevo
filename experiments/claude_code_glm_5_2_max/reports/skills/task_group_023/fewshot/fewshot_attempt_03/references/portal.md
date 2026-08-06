# PHO Portal Access

The Public Health Observatory (PHO) portal is the **only** authorized source of evidence.
Reach it exclusively through `environment_access.md`, which gives the base URL and the
allow-listed endpoints. In a task, `<TASK_ENV_BASE_URL>` in `prompt.txt` resolves to that base
URL.

## Base URL and credentials

- `environment_access.md` contains `GDPEVO_ENV_BASE_URL=http://task-env:9023/` (or equivalent).
  Substitute it for `<TASK_ENV_BASE_URL>` everywhere.
- No credentials. All access is read-only GET.

## Allowed endpoints (use only these)

```
GET /
GET /catalog
GET /geographies/states
GET /geographies/counties
GET /geographies/countries
GET /data/state-health
GET /data/state-socioeconomic
GET /data/county-health
GET /data/county-socioeconomic
GET /data/country-indicators
GET /data/revisions
GET /methodology
GET /download
```

The browse endpoints (`/data/*`, `/geographies/*`) return HTML; `/download` returns CSV and is
the efficient machine-readable path. `/catalog` lists every dataset's columns, filters, and
row counts. `/methodology` is the canonical policy library — consult it for release
precedence, suppression, quality flags, value types, RUCC, and country label reconciliation.

## Downloading data (CSV)

`GET /download?dataset=<NAME>&format=csv&<filters>` returns CSV with a header row.

- `dataset` is one of: `states`, `counties`, `countries`, `state_health`,
  `state_socioeconomic`, `county_health`, `county_socioeconomic`, `country_indicators`,
  `revisions`.
- Filters accept **comma-separated exact values** (e.g. `state_abbr=CA,NV,TX`). Each dataset's
  supported filters are listed on `/catalog`.
- Filter on the release-discriminating fields directly (`release_status`, `revision`,
  `value_type`, `source_type`, `year`, `measure_id`/`indicator_id`, geography) to keep payloads
  small, but **do not over-filter** in a way that discards records needed to apply the
  declared release priority — fetch enough rows to select the winning record per key.
- Parse CSV as text (FIPS codes have meaningful leading zeros; the `note` field in `revisions`
  contains commas, so use a real CSV parser, not naive comma splitting).

## Datasets and key columns

| Dataset | Entity key | Release / revision columns | Value / validity columns |
|---|---|---|---|
| `state_health` | `state_abbr` + `year` + `measure_id` + `value_type` + `source_type` | `release_status`, `revision`, `released_at`, `observation_id` | `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag` |
| `state_socioeconomic` | `state_abbr` + `year` | `release_status`, `revision`, `released_at`, `record_id` | `poverty`, `bachelors`, `median_income`, `unemployment`, `uninsured`, `food_insecurity`, `population`, `quality_flag` |
| `county_health` | `county_fips` + `year` + `measure_id` + `value_type` | `release_status`, `revision`, `released_at`, `observation_id` | `value`, `low_ci`, `high_ci`, `population`, `suppression_flag`, `quality_flag` (no `source_type` — county health is one series) |
| `county_socioeconomic` | `county_fips` + `year` | `release_status`, `revision`, `released_at`, `record_id` | `poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`, `uninsured`, `population`, `quality_flag` |
| `country_indicators` | `country_label`/`iso3` + `year` + `indicator_id` | `release_status`, `revision`, `released_at`, `observation_id` | `value`, `unit`, `quality_flag` |
| `revisions` | `domain` + `entity_id` + `field_id` + `effective_year` | `revision_event_id`, `status`, `issued_at` | `old_value`, `new_value`, `reason_code`, `note` |
| `states` | `state_abbr` | — | `state_fips`, `state_name`, `region`, `division`, `is_state` |
| `counties` | `county_fips` | — | `state_abbr`, `county_name`, `region`, `rucc`, `metro_class`, `population_base` |
| `countries` | `iso3` | — | `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group` |

### Measure / indicator dictionaries

- **STATE_HEALTH measures:** `adult_obesity`, `adult_smoking`, `diagnosed_diabetes`,
  `food_insecurity`, `frequent_mental_distress`, `life_expectancy`, `physical_inactivity`,
  `premature_mortality_rate`.
- **COUNTY_HEALTH measures:** `adult_obesity`, `adult_smoking`, `copd`, `depression`,
  `diagnosed_diabetes`, `physical_inactivity`, `severe_housing_cost_burden`, `short_sleep`.
- **COUNTRY indicators:** `adult_mortality`, `alcohol_harm`, `bmi_burden`,
  `health_spending_gap`, `hiv_burden`, `immunization_gap`, `infant_mortality`,
  `life_expectancy`, `poverty_rate`, `schooling_gap`, `unemployment`, `urbanization`.
  Each has a `unit` and a direction (`HIGHER_WORSE`, `HIGHER_BETTER`, `NEUTRAL`) on the
  measure dictionary (visible on `/catalog`).

### Vocabularies seen on the portal

- `release_status`: `FINAL`, `PROVISIONAL`.
- `value_type` (state/county health): `AGE_ADJUSTED`, `CRUDE`.
- `source_type` (state health): `DIRECT_SURVEY`, `COUNTY_ROLLUP`.
- `suppression_flag`: `0` / `1` (integer). Suppressed rows retain metadata but publish no
  `value`.
- `quality_flag`: e.g. `REVIEWED`, plus stale/caution flags — describes review state, **does
  not change release precedence**; retain it in audit extracts.
- `revisions.status`: `APPLIED`, `PENDING`, `WITHDRAWN` (and possibly others). Only `APPLIED`
  scale corrections are reflected in later final revisions; `PENDING`/`WITHDRAWN` do **not**
  authorize replacing a published value.

## Methodology library (canonical policy — read before resolving evidence)

`/methodology` indexes versioned policy documents. The rules that govern audit resolution:

- **Surveillance release lifecycle (CURRENT):** Provisional records support timely review;
  **final records replace provisional** for publication; when several final revisions exist,
  the **highest applied final revision governs**. (An earlier SUPERSEDED policy treated the
  first final file as closed — do not use it.)
- **Small-number suppression (CURRENT):** Suppressed observations retain identifying and
  release metadata but publish no value. **Never treat a suppressed or missing value as zero.**
- **Quality flag interpretation (CURRENT):** Quality flags describe review state and do not
  change release precedence. Retain stale/caution flags in audit extracts.
- **Crude and age-adjusted publication use (CURRENT):** Age-adjusted values support
  cross-jurisdiction comparison where specified; crude values describe observed burden and
  retain each jurisdiction's population structure. Do not mix value types.
- **State direct and rollup estimates (CURRENT):** Direct survey estimates are the primary
  state series; county rollups are parallel estimates for coverage review and must **not
  silently replace** direct records.
- **Socioeconomic release fields (CURRENT):** Socioeconomic fields are revised independently;
  sparse null fields do not invalidate other published fields in the same record.
- **County socioeconomic comparability (CURRENT):** Cross-year comparisons use like-for-like
  final fields; population and net_migration are separately released and may move either way.
- **Rural-Urban Continuum Codes (CURRENT):** RUCC 1–9, with 1–3 metropolitan and 4–9
  nonmetropolitan in this portal. RUCC lives on the county geography reference (integer).
- **Country label reconciliation (CURRENT):** Portal labels can differ from canonical names.
  Reconcile to stable ISO3-like identifiers using the `countries` reference
  (`canonical_name`, `portal_label`, `alternate_labels`). ISO3 values are uppercase.
- **Geographic identifiers (CURRENT):** State and county FIPS are text; leading zeros are
  meaningful; a county FIPS is the 2-char state code + 3-char county suffix.
- **Country indicator revision notices (CURRENT):** Applied scale corrections appear in later
  final revisions; pending/withdrawn notices do not authorize replacement; reconcile portal
  labels to stable country identifiers.
- **Influence diagnostics guidance (CURRENT):** Report the declared model, eligible record
  set, and the effect of any sensitivity exclusion.

A `DRAFT` revision-consultation document may appear; it **does not supersede** current
publication policy — ignore it for resolution.

## Practical extraction pattern

1. Read `analysis_request.json` and note every dataset, measure/field, year, geography, and
   filter binding the effective request needs.
2. For each dataset, `GET /download?dataset=...&format=csv&<filters>` enough rows to apply the
   declared release priority (typically filter by `release_status`, `value_type`,
   `source_type`, `measure_id`, `year`, geography — but keep all competing revisions for a key
   so you can pick the winner).
3. Select one record per entity-time-measure key per the release priority in
   [`request_resolution.md`](request_resolution.md).
4. Join resolved series by stable entity-time keys to build cohorts.
5. Fetch `revisions` (filter by `domain`, `entity_id`, `field_id`, `effective_year`,
   `status`) when a module needs applied/non-applied revision events or scale-break anomaly
   detection.
