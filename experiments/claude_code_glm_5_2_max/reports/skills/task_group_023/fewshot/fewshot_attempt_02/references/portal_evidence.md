# Portal evidence access

## Access contract

- The base URL and allowed endpoints come **only** from `environment_access.md` (e.g. the `GDPEVO_ENV_BASE_URL` line or the URL stated there). Credentials: none.
- Use only the allowed GET endpoints listed there: home `/`, `/catalog`, `/geographies/states`, `/geographies/counties`, `/geographies/countries`, `/data/state-health`, `/data/state-socioeconomic`, `/data/county-health`, `/data/county-socioeconomic`, `/data/country-indicators`, `/data/revisions`, `/methodology`, `/download`.
- Reach the network only through this file. Do not fetch external resources or invent URLs.
- Use `/download?dataset=...&format=csv` for bulk rows; use the browse/filter endpoints (with their declared query filters) for targeted lookups. Parse rows exactly as returned.

## Data model (portal)

- **Geographies.**
  - `states`: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state` (51 jurisdictions: 50 states + DC).
  - `counties`: `county_fips`, `state_abbr`, `county_name`, `region`, `rucc` (integer 1–9), `metro_class`, `population_base`, `latitude`, `longitude`.
  - `countries`: country names/aliases, ISO3, region.
- **Health/socioeconomic records** retain publication-audit fields: `release_status` (e.g. FINAL/PROVISIONAL), `revision`, `released_at`, `value_type` (e.g. AGE_ADJUSTED/CRUDE), `source_type` (e.g. DIRECT_SURVEY/COUNTY_ROLLUP), validity/quality flags, `sample_size`, and a record/observation id. Socioeconomic records carry fields such as `poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`, `uninsured`, `region`.
- **Revisions.** `/data/revisions` lists revision events with a status (APPLIED vs non-APPLIED such as pending/withdrawn) and affected observation keys. Applied revisions are reflected in later final revisions; pending/withdrawn notices do not replace published values. Final releases may supersede provisional records.
- **Methodology.** `/methodology` documents quality-flag interpretation, suppression, indicator direction/units, socioeconomic release fields, influence diagnostics, and country/county revision notices. Consult the relevant doc when a flag or unit is ambiguous.

## Release resolution (one record per declared entity-time-measure key)

1. Filter each publication key by the effective release status, source type, value type, validity/quality flags, and geography bindings.
2. Among records surviving the filter for the same key, select by:
   - greatest `revision`,
   - then latest `released_at`,
   - then record/observation id in the **direction declared by the request** (lowest or greatest; follow the request's `revision_priority`).
3. Count selected publications **before** analytic completeness exclusions when the request asks for release counts.
4. Suppressed, invalid, withdrawn, blank, or null analytic values remain **unavailable and are never zero-filled**. They may still count as a selected publication for release-count purposes, but they fail completeness.

## Cohorts (construct from effective completeness predicates; preserve entity-code then time order)

- **Primary / reference-year complete cases:** entities complete on the outcome and required fields in the reference year.
- **Balanced panel:** the intersection of entities complete across every requested analysis year.
- **Broad reference:** reference-year entities complete for the outcome and every ordered ridge/PCA feature.
- **Strict dual-source:** entities complete for outcome, primary exposure, parallel exposure, and adjustments in every analysis year.
- **Machine-learning cohort:** primary-cohort members also complete on the extra ML fields the request declares.
- Always preserve declared entity-code order, then time order, and every declared feature/group/division order.

## Identifiers & grouping

- Use uppercase two-letter state codes and portal division/region names exactly as returned; ISO3 uppercase.
- Census divisions and regions come from the states geography table; preserve the request's declared division/region order.
- County RUCC (1–9) supports rurality bands and RUCC indicator expansions (RUCC1 as reference, RUCC2–RUCC9 as indicators).
- When the request declares a reliability weight, use the selected direct outcome-record `sample_size` as the fixed positive weight — including source-perturbation fits — unless the request overrides this.

## Adjacent-change / panel rows (when the audit is dynamic)

Create adjacent-change rows ordered by entity identifier then end period; derive lagged levels, dynamic changes, reference indicators, and interactions in the declared order. Treat selected suppressed/invalid/missing values as incomplete, never zero; retain only entities complete across every effective balanced period with valid geography attributes.
