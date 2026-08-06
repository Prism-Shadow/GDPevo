# Portal reference — PHO Data Portal

The portal at `<TASK_ENV_BASE_URL>` (see `environment_access.md`) is the **only** evidence
source. It is read-only; no credentials. Use only the allowed GET endpoints.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Home / navigation (HTML). |
| `GET /catalog` | Dataset catalog: column schemas, available filters, row counts, measure dictionary (HTML). **Read first.** |
| `GET /geographies/states` | State geography reference (HTML; also CSV via `/download`). |
| `GET /geographies/counties` | County geography reference. |
| `GET /geographies/countries` | Country geography reference. |
| `GET /data/state-health` | State health observations (HTML browse). |
| `GET /data/state-socioeconomic` | State socioeconomic releases. |
| `GET /data/county-health` | County health observations. |
| `GET /data/county-socioeconomic` | County socioeconomic releases. |
| `GET /data/country-indicators` | Country indicator observations. |
| `GET /data/revisions` | Revision notices. |
| `GET /methodology` | Methodology library index. |
| `GET /methodology?doc=<slug>` | A single methodology document. |
| `GET /download?dataset=<d>&format=csv&<filters>` | CSV export of any dataset with the same filters. **Use this for bulk records.** |

The HTML browse pages and `/download` accept the same filter query params documented in the
catalog card for each dataset. Filter per measure/year/value_type/source_type to keep payloads
small, then resolve locally. **Cross-check the jurisdiction universe against `/geographies`**
(e.g., `states` has 51 rows = 50 states + DC; do not assume a filtered data view is complete).

## Dataset schemas (from /catalog)

**states** (51 rows): `state_fips, state_abbr, state_name, region, division, is_state`.
Filters: `state_abbr, state_fips, region, division`.
- `division` is the Census division name (e.g., `Pacific`, `East South Central`, `New England`). Use these names **verbatim** in outputs.
- `is_state` flags DC vs true states when a task says "50 states" vs "50 states + DC".

**counties** (1,224 rows): `county_fips, state_abbr, county_name, region, rucc, metro_class,
population_base, latitude, longitude`. Filters: `county_fips, state_abbr, region, rucc,
metro_class`. `rucc` is integer 1–9.

**countries** (72 rows): `iso3, canonical_name, portal_label, alternate_labels, region,
income_group`. `alternate_labels` is a `|`-separated list. Use for alias→ISO3 reconciliation.

**state_health** (4,861; 2020–2024): `observation_id, state_fips, state_abbr, year,
measure_id, value_type, source_type, release_status, revision, value, standard_error,
sample_size, suppression_flag, quality_flag, released_at`. Filters: `state_abbr, measure_id,
year, value_type, source_type, release_status, revision`.
- `value_type`: `AGE_ADJUSTED` | `CRUDE`.
- `source_type`: `DIRECT_SURVEY` | `COUNTY_ROLLUP` (rollup is the parallel coverage estimate).
- `release_status`: `FINAL` | `PROVISIONAL` (final replaces provisional).
- `revision`: integer; higher = later revision.
- `suppression_flag`: nonzero ⇒ value unpublished (unavailable, never zero).
- `quality_flag`: review state (e.g., `REVIEWED`, `STALE`); does not change release precedence.
  Exclude only the request's `invalid_quality_flags` (e.g., `INVALID_SCALE`, `INVALID`, `WITHDRAWN`).

**state_socioeconomic** (323; 2020–2024): `record_id, state_fips, state_abbr, year,
release_status, revision, released_at, poverty, bachelors, median_income, unemployment,
uninsured, food_insecurity, population, quality_flag`. Filters: `state_abbr, year,
release_status, revision`. Note: `food_insecurity` lives here too (state level).

**county_health** (47,938; 2021–2024): `observation_id, county_fips, state_abbr, region, year,
measure_id, value_type, release_status, revision, released_at, value, low_ci, high_ci,
population, suppression_flag, quality_flag`. Filters: `county_fips, state_abbr, region,
measure_id, year, value_type, release_status, revision, suppression_flag`. County health has
no `source_type` column (county series is the observed-burden series); value_type is CRUDE by
default for county burden.

**county_socioeconomic** (6,772; 2020–2024): `record_id, county_fips, state_abbr, region, year,
release_status, revision, released_at, poverty, median_income, bachelors, unemployment,
net_migration, uninsured, population, quality_flag`. Filters: `county_fips, state_abbr, region,
year, release_status, revision`.

**country_indicators** (9,812; 2013–2024): `observation_id, country_label, iso3, year,
indicator_id, release_status, revision, released_at, value, unit, quality_flag`. Filters:
`iso3, country_label, indicator_id, year, release_status, revision, quality_flag`. Multiple
labels may map to one `iso3` (alias reconciliation). `unit` matters — percentages and mortality
rates are not interchangeable (check the measure dictionary direction/unit before combining).

**revisions** (130; 2015–2024): `revision_event_id, domain, entity_id, field_id,
effective_year, old_value, new_value, status, issued_at, reason_code, note`. `status`:
`APPLIED` | `PENDING` | `WITHDRAWN`. `reason_code`: e.g., `SCALE_CORRECTION`, `SOURCE_RESTATE`,
`GEOGRAPHY_RECODE`, `LATE_RESPONSE`. Domain/entity/field/effective_year identify the affected
cell.

## Methodology library (resolution policy)

Read the **CURRENT** docs; **ignore DRAFT and SUPERSEDED** for publication decisions. Fetch a
doc with `GET /methodology?doc=<slug>`.

| slug | status | governs |
|---|---|---|
| `release-lifecycle` | CURRENT | Final replaces provisional; highest applied final revision governs. |
| `quality` | CURRENT | Quality flags describe review state; do not change release precedence; retain in extracts. |
| `publication-values` | CURRENT | Age-adjusted for state comparisons; crude for observed county burden. |
| `state-estimates` | CURRENT | Direct survey = primary state series; county rollup = parallel coverage estimate, never silently replace direct. |
| `suppression` | CURRENT | Suppressed/missing values are unavailable; never treat as zero. |
| `aliases` | CURRENT | Portal labels differ from canonical names; reconcile to stable ISO3 via alternate labels. |
| `country-revisions` | CURRENT | Applied scale corrections appear in later final revisions; pending/withdrawn do not authorize replacement. |
| `socioeconomic-fields` | CURRENT | Socioeconomic release field semantics (final, like-for-like across years). |
| `geographic-ids` | CURRENT | Geographic identifier rules (FIPS, ISO3, division names). |
| `rucc` | CURRENT | Rural-Urban Continuum Codes (1–9); RUCC1 reference, RUCC2–9 indicators. |
| `indicator-direction` | CURRENT | Indicator direction (HIGHER_WORSE / HIGHER_BETTER / NEUTRAL) and units; check before combining. |
| `influence` | CURRENT | Influence diagnostics guidance (jackknife / delete-one). |
| `county-windows` | CURRENT | County socioeconomic comparability across years. |
| `country-revisions` | CURRENT | (listed above) |
| `revisions-draft` | **DRAFT** | Does NOT supersede current policy — ignore for decisions. |
| `release-lifecycle-v2` | **SUPERSEDED** | Ignore; use `release-lifecycle`. |

## Release / revision resolution algorithm

For each requested cell (jurisdiction × year × measure × value_type × source_type, or the
country analogue):

1. **Final only.** Keep `release_status = FINAL`. Provisional records are dropped for
   publication (release-lifecycle).
2. **Highest applied revision.** Among final records for the same cell, keep the one with the
   highest `revision` whose corresponding revision event (if any) is `APPLIED`. If no revision
   event applies, the latest final record stands.
3. **Pending/withdrawn ignored.** Revision events with `status` PENDING or WITHDRAWN do not
   authorize replacement (country-revisions).
4. **Tie-break.** Apply the request's declared `revision_priority` exactly. Common forms:
   - `[revision, released_at, observation_id]` (state health)
   - `[revision, released_at, record_id]` (socioeconomic)
   - `HIGHEST_FINAL_REVISION_THEN_LATEST_RELEASE` (county panel)
   Break ties by the first differing key, in listed order.
5. **Quality exclusion.** Drop records whose `quality_flag` is in the request's
   `invalid_quality_flags`. Retain all other flags (they do not change precedence).
6. **Suppression/missing.** A suppressed flag or blank value ⇒ unavailable. Drop from the
   complete-case cohort; never zero-fill.
7. **Source/value-type discipline.** Keep `DIRECT_SURVEY` as the primary state series;
   `COUNTY_ROLLUP` only where the request calls for it (parallel exposure / source
   perturbation replacement). Keep `AGE_ADJUSTED` and `CRUDE` as separate series — primary vs
   parallel exposure — never merged.
8. **Country alias reconciliation.** Map each requested `country_label`/portal label to its
   `iso3` via the `countries` geography file (`portal_label`, `alternate_labels`). Count
   alias resolutions (labels whose canonical name differs from the requested label).

Record the resolution outputs the template requires: selected release counts by year, alias
resolution count, applied vs non-applied revision event ids, anomaly/scale-break cells
(unresolved `SCALE_CORRECTION` breaks), raw-missing vs imputed cell counts, usable country /
indicator counts, yearly complete-case counts, cohort counts, excluded jurisdiction codes.
