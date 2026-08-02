# Portal reference — Public Health Observatory Data Portal

The portal is a read-only HTML site with matching CSV exports. `environment_access.md`
gives the base URL as `GDPEVO_ENV_BASE_URL=<base>/` and lists the GET endpoints. Use only
this portal for evidence.

## Endpoints (from environment_access.md)

```
GET /                       portal home
GET /catalog                dataset catalog + measure dictionary
GET /geographies/states     states reference
GET /geographies/counties   counties reference
GET /geographies/countries  countries reference
GET /data/state-health              GET /data/state-socioeconomic
GET /data/county-health             GET /data/county-socioeconomic
GET /data/country-indicators        GET /data/revisions
GET /methodology            methodology library (release lifecycle, suppression, RUCC, etc.)
GET /download               CSV export
```

### CSV download recipe (preferred for computation)

Every dataset exports as CSV via:

```
GET <base>/download?dataset=<name>&format=csv
```

Optional column filters can be appended (e.g. `&state_abbr=CA&year=2024&measure_id=...`),
but the simplest robust path is to download each full dataset once and filter locally.
`released_at`/`issued_at` are ISO date strings; FIPS/ISO3 identifiers are **TEXT with
meaningful leading zeros** — read them as strings.

## Datasets and schemas

Row counts below are indicative of the live portal at capture time; always trust the live
`/catalog`.

| dataset (`?dataset=`) | grain / coverage | key columns |
|---|---|---|
| `states` | 51 rows | `state_fips, state_abbr, state_name, region, division, is_state` |
| `counties` | ~1,224 | `county_fips, state_abbr, county_name, region, rucc, metro_class, population_base, latitude, longitude` |
| `countries` | ~72 | `iso3, canonical_name, portal_label, alternate_labels, region, income_group` |
| `state_health` | 2020–2024 | `observation_id, state_fips, state_abbr, year, measure_id, value_type, source_type, release_status, revision, value, standard_error, sample_size, suppression_flag, quality_flag, released_at` |
| `state_socioeconomic` | 2020–2024 | `record_id, state_fips, state_abbr, year, release_status, revision, released_at, poverty, bachelors, median_income, unemployment, uninsured, food_insecurity, population, quality_flag` |
| `county_health` | 2021–2024 | `observation_id, county_fips, state_abbr, region, year, measure_id, value_type, release_status, revision, released_at, value, low_ci, high_ci, population, suppression_flag, quality_flag` |
| `county_socioeconomic` | 2020–2024 | `record_id, county_fips, state_abbr, region, year, release_status, revision, released_at, poverty, median_income, bachelors, unemployment, net_migration, uninsured, population, quality_flag` |
| `country_indicators` | 2013–2024 | `observation_id, country_label, iso3, year, indicator_id, release_status, revision, released_at, value, unit, quality_flag` |
| `revisions` | 2015–2024 | `revision_event_id, domain, entity_id, field_id, effective_year, old_value, new_value, status, issued_at, reason_code, note` |

### Categorical domains observed (bind exact filter values from the request)

- `state_health.value_type` ∈ {`AGE_ADJUSTED`, `CRUDE`}; `source_type` ∈ {`DIRECT_SURVEY`,
  `COUNTY_ROLLUP`}. `county_health.value_type` ∈ {`AGE_ADJUSTED`, `CRUDE`}.
- `release_status` ∈ {`FINAL`, `PROVISIONAL`}; `revision` is an integer (0/1/2…).
- `quality_flag` examples: `REVIEWED, REVISED, PROVISIONAL, SUPPRESSED, PARALLEL_ESTIMATE`
  (health) and other domain-specific tokens. `suppression_flag` ∈ {0, 1}.
- `revisions.status` ∈ {`APPLIED`, `WITHDRAWN`, `PENDING`}; `domain` ∈ {`COUNTRY`,
  `STATE_HEALTH`, `STATE_SES`, `COUNTY_HEALTH`, `COUNTY_SES`}; `reason_code` includes
  `SCALE_CORRECTION, SOURCE_RESTATE, GEOGRAPHY_RECODE, LATE_RESPONSE`.

Do not treat these enumerations as exhaustive across future data — always read the actual
filter/validity tokens from the effective request and apply them literally.

## Geography references (join keys)

- **states**: `state_abbr` ↔ `state_fips`; `region` (Northeast/Midwest/South/West) and
  Census `division` (e.g. "New England", "Mountain", "West South Central"). Use `division`
  for census-division clustering/grouping and the portal division names *exactly*.
- **counties**: `county_fips` = 2-char state code + 3-char county suffix; `rucc` integer
  1–9 (1–3 metropolitan, 4–9 nonmetropolitan); `region`.
- **countries**: `iso3` (stable id), `canonical_name`, `portal_label`, and
  `alternate_labels` (pipe-separated `A|B|C`) used for label reconciliation; `region`,
  `income_group`.

## Methodology library (policy, read when a rule is ambiguous)

`GET /methodology` documents the release lifecycle and validity policy that the requests
encode. Salient points:

- **Release lifecycle**: FINAL records replace PROVISIONAL for publication; when several
  FINAL revisions exist, the highest applied final revision governs.
- **Suppression**: a suppressed/missing value keeps its metadata but publishes no value;
  never treat it as zero.
- **Direct vs rollup**: DIRECT_SURVEY is the primary state series; COUNTY_ROLLUP is a
  parallel estimate for coverage review and must not silently replace direct records.
- **Crude vs age-adjusted**: age-adjusted supports cross-state comparison; crude reflects
  observed burden. Pick the `value_type` the request names.
- **Revisions**: APPLIED scale corrections appear in later final revisions; PENDING and
  WITHDRAWN notices do not authorize replacement.
- **Country labels / RUCC / geographic identifiers / units**: reconcile labels to ISO3;
  RUCC lives on the county reference; FIPS/ISO3 are text; check units before combining
  indicators.
