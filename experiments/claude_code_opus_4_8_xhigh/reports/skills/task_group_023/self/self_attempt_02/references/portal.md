# PHO portal reference — datasets, endpoints, and methodology conventions

The Public Health Observatory (PHO) portal is the **only** authoritative evidence
source for these tasks. Base URL comes from `environment_access.md`
(`GDPEVO_ENV_BASE_URL`, e.g. `http://task-env:9023/`). All access is GET-only.

## How to pull data (do this, not screen-scraping)

- **Bulk, complete, machine-readable:** `GET /download?dataset=<name>&format=csv[&<filter>=<value>...]`
  returns the **entire** table as CSV (verified: `county_health` returns all
  47,938 rows, no pagination). `format=csv` is required or you get an HTML error
  page (`format must be csv`). Filters are exact-match on the columns marked
  filterable below; unknown dataset/format returns an HTML `Invalid request` page.
- **Human browse pages** `GET /data/*` and `GET /geographies/*` **paginate**
  (`page_size=50&page=N`) — do not rely on them for completeness; use `/download`.
- `GET /catalog` — schema + row counts + filterable columns + measure dictionary.
- `GET /methodology` and `GET /methodology?doc=<id>` — audit conventions (below).
- `scripts/portal_client.py` wraps all of this: `Portal().fetch("state_health", year="2023")`.

Values in CSV arrive as **strings**. Cast deliberately. An empty cell = MISSING
(never zero). FIPS are TEXT with meaningful leading zeros.

## Datasets (from `/catalog`)

Geography references:
- `states` (51 rows): `state_fips, state_abbr, state_name, region, division, is_state`.
  Filters: `state_abbr, state_fips, region, division`. **Source of census `division`
  and `region` for state clustering/fixed effects.**
- `counties` (1,224): `county_fips, state_abbr, county_name, region, rucc, metro_class,
  population_base, latitude, longitude`. Filters: `county_fips, state_abbr, region,
  rucc, metro_class`. **Source of `rucc` and `region` for county tasks.**
- `countries` (72): `iso3, canonical_name, portal_label, alternate_labels, region,
  income_group`. Filters: `iso3, label, region, income_group`. `alternate_labels`
  is **pipe-delimited** — the alias table for reconciling request labels → ISO3.

Measure/observation tables:
- `state_health` (4,861; 2020–2024): `observation_id, state_fips, state_abbr, year,
  measure_id, value_type, source_type, release_status, revision, value,
  standard_error, sample_size, suppression_flag, quality_flag, released_at`.
  Filters: `state_abbr, measure_id, year, value_type, source_type, release_status, revision`.
- `state_socioeconomic` (323; 2020–2024): `record_id, state_fips, state_abbr, year,
  release_status, revision, released_at, poverty, bachelors, median_income,
  unemployment, uninsured, food_insecurity, population, quality_flag`.
- `county_health` (47,938; 2021–2024): `observation_id, county_fips, state_abbr,
  region, year, measure_id, value_type, release_status, revision, released_at, value,
  low_ci, high_ci, population, suppression_flag, quality_flag`.
- `county_socioeconomic` (6,772; 2020–2024): `record_id, county_fips, state_abbr,
  region, year, release_status, revision, released_at, poverty, median_income,
  bachelors, unemployment, net_migration, uninsured, population, quality_flag`.
- `country_indicators` (9,812; 2013–2024): `observation_id, country_label, iso3, year,
  indicator_id, release_status, revision, released_at, value, unit, quality_flag`.
- `revisions` (130; 2015–2024): `revision_event_id, domain, entity_id, field_id,
  effective_year, old_value, new_value, status, issued_at, reason_code, note`.
  Filters: `domain, entity_id, field_id, effective_year, status`.
  Observed `status` values: `APPLIED`, `PENDING`, `WITHDRAWN`.

Observed `state_health` value dimensions (combinations exist and matter):
`value_type ∈ {AGE_ADJUSTED, CRUDE}`, `source_type ∈ {DIRECT_SURVEY, COUNTY_ROLLUP}`,
`release_status ∈ {FINAL, PROVISIONAL}`. The request tells you which combination is
the "primary" series, which is "parallel", and which to perturb between.

## Methodology library (`/methodology?doc=<id>`) — the rules that decide ties

These CURRENT docs govern how to resolve evidence. Read the ones your task touches;
prefer CURRENT over SUPERSEDED/DRAFT documents (a DRAFT does **not** change policy).

- **release-lifecycle** (CURRENT): FINAL records replace PROVISIONAL for publication;
  when several FINAL revisions exist, **the highest APPLIED final revision governs**.
  (`release-lifecycle-v2` is SUPERSEDED — the old "first final is closed" policy; ignore.)
- **publication-values** (CURRENT): AGE_ADJUSTED supports cross-jurisdiction (state)
  comparison; CRUDE describes observed local (county) burden. Use whichever the request declares.
- **state-estimates** (CURRENT): DIRECT_SURVEY is the primary state series; COUNTY_ROLLUP
  is a parallel coverage series and must **not silently replace** direct records.
- **suppression** (CURRENT): suppressed rows keep metadata but publish no value; a
  suppressed/missing value must **never** be treated as zero.
- **quality** (CURRENT): quality flags describe review state and do **not** change
  release precedence; but the request may list specific `invalid_quality_flags`
  (e.g. INVALID_SCALE, INVALID, WITHDRAWN) that exclude a cell.
- **socioeconomic-fields** (CURRENT): socioeconomic fields are revised independently;
  a sparse null in one field does not invalidate the record's other fields.
- **country-revisions** / **revisions-draft**: APPLIED scale corrections appear in later
  FINAL revisions; **PENDING or WITHDRAWN notices do not authorize replacement**.
- **aliases** (CURRENT): reconcile portal labels to stable ISO3 via `alternate_labels`.
- **geographic-ids** (CURRENT): FIPS are TEXT; leading zeros are meaningful; county_fips =
  2-char state + 3-char county suffix.
- **rucc** (CURRENT): RUCC 1–3 metropolitan, 4–9 nonmetropolitan; RUCC lives on `counties`.
- **influence** (CURRENT): influence/sensitivity diagnostics must report the declared
  model, the eligible record set, and the effect of any exclusion.

Always confirm the exact wording live — versions can change. `portal_client.py raw
/methodology?doc=<id>` prints a doc.
