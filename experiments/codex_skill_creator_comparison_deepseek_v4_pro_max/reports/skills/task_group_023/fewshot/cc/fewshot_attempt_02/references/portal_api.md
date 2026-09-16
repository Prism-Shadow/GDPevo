# Portal API Reference

Base URL: `<TASK_ENV_BASE_URL>` (substituted from the task prompt)

All endpoints return HTML tables with optional CSV download via
`/download?dataset=<name>&format=csv` using the same filter parameters.
CSV downloads include a header row and do not paginate.

## Data Endpoints

### State Health Observations

```
GET /data/state-health
```

**Filter parameters:**
- `state_abbr` — comma-separated uppercase two-letter codes (e.g. `CA,NY,TX`)
- `year` — single year or comma-separated
- `measure_id` — comma-separated (e.g. `adult_obesity,life_expectancy`)
- `value_type` — e.g. `AGE_ADJUSTED`, `CRUDE`
- `source_type` — e.g. `DIRECT_SURVEY`, `COUNTY_ROLLUP`
- `release_status` — e.g. `FINAL`, `PROVISIONAL`
- `revision` — integer revision number
- `quality_flag` — e.g. `REVIEWED`, `REVISED`, `SUPPRESSED`, `PROVISIONAL`, `PARALLEL_ESTIMATE`, `STALE`, `CAUTION`
- `page_size` — 25, 50, 100, 200

**CSV download:**
```
GET /download?dataset=state_health&format=csv&year=2023&state_abbr=CA,NY
```

**Field schema:**

| Field | Type | Description |
|---|---|---|
| `observation_id` | string | Unique record identifier, prefix `SH` |
| `state_fips` | string | Two-digit state FIPS code |
| `state_abbr` | string | Uppercase two-letter state code |
| `year` | integer | Observation year |
| `measure_id` | string | e.g. `adult_obesity`, `life_expectancy`, `diagnosed_diabetes` |
| `value_type` | string | `AGE_ADJUSTED` or `CRUDE` |
| `source_type` | string | `DIRECT_SURVEY` or `COUNTY_ROLLUP` |
| `release_status` | string | `FINAL` or `PROVISIONAL` |
| `revision` | integer | Revision number; 0 for provisional |
| `value` | number or emdash | The published value; emdash when suppressed |
| `standard_error` | number | Standard error estimate |
| `sample_size` | integer | Survey sample size |
| `suppression_flag` | integer | 1 when suppressed, 0 otherwise |
| `quality_flag` | string | Review state tag |
| `released_at` | date string | Publication timestamp, format `YYYY-MM-DD` |

### County Health Observations

```
GET /data/county-health
```

**Filter parameters:** `county_fips`, `state_abbr`, `region`, `year`, `measure_id`, `value_type`, `release_status`, `revision`, `page_size`

**CSV download:**
```
GET /download?dataset=county_health&format=csv&year=2023&state_abbr=ME
```

**Field schema:**

| Field | Type | Description |
|---|---|---|
| `observation_id` | string | Unique record identifier, prefix `CH` |
| `county_fips` | string | Five-digit county FIPS code |
| `state_abbr` | string | Uppercase two-letter state code |
| `region` | string | Census region |
| `year` | integer | Observation year |
| `measure_id` | string | Health measure identifier |
| `value_type` | string | `AGE_ADJUSTED` or `CRUDE` |
| `release_status` | string | `FINAL` or `PROVISIONAL` |
| `revision` | integer | Revision number |
| `released_at` | date string | Publication timestamp |
| `value` | number or emdash | The published value |
| `low_ci` | number | Lower confidence interval bound |
| `high_ci` | number | Upper confidence interval bound |
| `population` | integer | County population |
| `suppression_flag` | integer | 1 when suppressed |
| `quality_flag` | string | Review state tag |

### State Socioeconomic Releases

```
GET /data/state-socioeconomic
```

**Filter parameters:** `state_abbr`, `year`, `release_status`, `revision`, `page_size`

**CSV download:**
```
GET /download?dataset=state_socioeconomic&format=csv&year=2023
```

**Field schema:**

| Field | Type | Description |
|---|---|---|
| `record_id` | string | Unique record identifier, prefix `SS` |
| `state_fips` | string | Two-digit state FIPS code |
| `state_abbr` | string | Uppercase two-letter code |
| `year` | integer | Observation year |
| `release_status` | string | `FINAL` or `PROVISIONAL` |
| `revision` | integer | Revision number |
| `released_at` | date string | Publication timestamp |
| `poverty` | number or emdash | Poverty rate |
| `bachelors` | number or emdash | Bachelor's degree attainment rate |
| `median_income` | number or emdash | Median household income (USD) |
| `unemployment` | number or emdash | Unemployment rate |
| `uninsured` | number or emdash | Uninsured rate |
| `food_insecurity` | number or emdash | Food insecurity rate |
| `population` | integer | Population estimate |
| `quality_flag` | string | Review state tag |

### County Socioeconomic Releases

```
GET /data/county-socioeconomic
```

**Filter parameters:** `county_fips`, `state_abbr`, `region`, `year`, `release_status`, `revision`, `page_size`

**CSV download:**
```
GET /download?dataset=county_socioeconomic&format=csv&state_abbr=ME&year=2023
```

**Field schema:**

| Field | Type | Description |
|---|---|---|
| `record_id` | string | Unique record identifier, prefix `CS` |
| `county_fips` | string | Five-digit county FIPS code |
| `state_abbr` | string | Uppercase two-letter state code |
| `region` | string | Census region |
| `year` | integer | Observation year |
| `release_status` | string | `FINAL` or `PROVISIONAL` |
| `revision` | integer | Revision number |
| `released_at` | date string | Publication timestamp |
| `poverty` | number or emdash | Poverty rate |
| `median_income` | number or emdash | Median household income (USD) |
| `bachelors` | number or emdash | Bachelor's degree attainment |
| `unemployment` | number or emdash | Unemployment rate |
| `net_migration` | number or emdash | Net migration rate |
| `uninsured` | number or emdash | Uninsured rate |
| `population` | integer | Population estimate |
| `quality_flag` | string | Review state tag |

### Country Indicator Observations

```
GET /data/country-indicators
```

**Filter parameters:** `country_label`, `iso3`, `year`, `indicator_id`, `release_status`, `revision`, `quality_flag`, `page_size`

**CSV download:**
```
GET /download?dataset=country_indicators&format=csv&year=2022
```

**Field schema:**

| Field | Type | Description |
|---|---|---|
| `observation_id` | string | Unique record identifier, prefix `CI` |
| `country_label` | string | Portal label; must be reconciled against geography reference |
| `iso3` | string | Stable ISO3-like identifier |
| `year` | integer | Observation year |
| `indicator_id` | string | e.g. `adult_mortality`, `bmi_burden`, `health_spending_gap`, etc. |
| `release_status` | string | `FINAL` or `PROVISIONAL` |
| `revision` | integer | Revision number; 0 for provisional |
| `released_at` | date string | Publication timestamp |
| `value` | number or emdash | The published value |
| `unit` | string | Unit label |
| `quality_flag` | string | Review state tag |

**Scale anomalies:** Always cross-check country indicators against
`/data/revisions?domain=COUNTRY`. An APPLIED revision notice means later
FINAL records already incorporate the correction. A PENDING or WITHDRAWN
notice means the published FINAL values may still contain uncorrected scale
breaks. For country tasks, resolve observations whose
`iso3|YEAR|indicator_id` matches an unapplied (non-APPLIED) revision event
as anomalous.

### Revision Notices

```
GET /data/revisions
```

**Filter parameters:** `domain` (`COUNTRY`, `STATE`), `entity_id` (ISO3 or state FIPS), `field_id` (indicator or measure id), `effective_year`, `status` (`APPLIED`, `PENDING`, `WITHDRAWN`), `reason_code`, `page_size`

**CSV download:**
```
GET /download?dataset=revisions&format=csv&domain=COUNTRY
```

**Field schema:**

| Field | Type | Description |
|---|---|---|
| `revision_event_id` | string | Unique event identifier, prefix `RV` |
| `domain` | string | `COUNTRY` or `STATE` |
| `entity_id` | string | ISO3 code or state FIPS |
| `field_id` | string | Indicator or measure identifier |
| `effective_year` | integer | Year the correction applies to |
| `old_value` | number | Pre-correction value |
| `new_value` | number | Post-correction value |
| `status` | string | `APPLIED`, `PENDING`, or `WITHDRAWN` |
| `issued_at` | date string | Notice issuance date |
| `reason_code` | string | e.g. `SCALE_CORRECTION` |
| `note` | string | Human-readable explanation |

## Geography Reference Endpoints

### States

```
GET /geographies/states
```

**Filter parameters:** `state_abbr`, `state_fips`, `region`, `division`, `page_size`

**CSV download:**
```
GET /download?dataset=states&format=csv
```

**Field schema:** `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`

There are 51 rows: 50 states plus District of Columbia (DC).

Regions: `Midwest`, `Northeast`, `South`, `West`

Divisions: `East North Central`, `East South Central`, `Middle Atlantic`, `Mountain`, `New England`, `Pacific`, `South Atlantic`, `West North Central`, `West South Central`

### Counties

```
GET /geographies/counties
```

**Filter parameters:** `county_fips`, `state_abbr`, `region`, `rucc`, `metro_class`, `page_size`

**CSV download:**
```
GET /download?dataset=counties&format=csv&state_abbr=ME
```

**Field schema:** `county_fips`, `state_abbr`, `county_name`, `region`, `rucc`, `metro_class`, `population_base`, `latitude`, `longitude`

### Countries

```
GET /geographies/countries
```

**Filter parameters:** `iso3`, `region`, `income_group`, `page_size`

**CSV download:**
```
GET /download?dataset=countries&format=csv
```

**Field schema:**

| Field | Type | Description |
|---|---|---|
| `iso3` | string | Stable ISO3-like identifier (uppercase, starts with Q) |
| `canonical_name` | string | Canonical country name |
| `portal_label` | string | Label used in indicator observations |
| `alternate_labels` | string | Pipe-separated alternate labels |
| `region` | string | World region |
| `income_group` | string | `LOW`, `LOWER_MIDDLE`, `UPPER_MIDDLE`, or `HIGH` |

**Label reconciliation:**
Portal labels used in `/data/country-indicators` may differ from canonical
names. For each requested label, match it against all `portal_label`,
`canonical_name`, and individual `alternate_labels` entries. Each label
resolves to exactly one ISO3. Resolved ISO3s must be unique (sorted
ascending). Count a label as an "alias resolution" if the resolving row's
`portal_label` differs from its `canonical_name`.

## Methodology Documents

```
GET /methodology          # list all documents
GET /methodology?doc=<doc-name>  # single document
```

Document names and key rules:

- `release-lifecycle` (CURRENT) — FINAL replaces PROVISIONAL; highest applied final revision governs.
- `release-lifecycle-v2` (SUPERSEDED) — Earlier lifecycle; not authoritative.
- `suppression` (CURRENT) — Suppressed observations retain metadata but no value; never treat as zero.
- `state-estimates` (CURRENT) — Direct survey is primary; county rollups are parallel for coverage review.
- `publication-values` (CURRENT) — Age-adjusted for state comparisons; crude for observed county burden.
- `aliases` (CURRENT) — Portal labels can differ from canonical names; use geography reference for reconciliation.
- `indicator-direction` (CURRENT) — Higher values may be favorable or unfavorable; check units before combining.
- `country-revisions` (CURRENT) — APPLIED corrections in later final revisions; PENDING/WITHDRAWN do not authorize replacement.
- `quality` (CURRENT) — Quality flags describe review state; do not change release precedence.
- `influence` (CURRENT) — Influence diagnostics assess fitted result dependence on individual observations.
- `socioeconomic-fields` (CURRENT) — Fields revised independently; sparse nulls do not invalidate other fields.
- `rucc` (CURRENT) — RUCC 1-3 metropolitan; 4-9 nonmetropolitan. RUCC belongs to county geography reference.
- `geographic-ids` (CURRENT) — FIPS are text with meaningful leading zeros.
- `county-windows` (CURRENT) — Like-for-like final fields for year comparisons.
- `revisions-draft` (DRAFT) — Draft proposal; not authoritative.
