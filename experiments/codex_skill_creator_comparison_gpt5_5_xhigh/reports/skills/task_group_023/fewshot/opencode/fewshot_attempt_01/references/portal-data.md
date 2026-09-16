# Portal Data Reference

Use the task-supplied base URL. Prefer CSV downloads for computation:

```text
/download?dataset=states&format=csv
/download?dataset=counties&format=csv
/download?dataset=countries&format=csv
/download?dataset=state_health&format=csv
/download?dataset=state_socioeconomic&format=csv
/download?dataset=county_health&format=csv
/download?dataset=county_socioeconomic&format=csv
/download?dataset=country_indicators&format=csv
/download?dataset=revisions&format=csv
```

The browse endpoints are useful for inspection: `/catalog`, `/methodology`, `/geographies/states`, `/geographies/counties`, `/geographies/countries`, `/data/state-health`, `/data/state-socioeconomic`, `/data/county-health`, `/data/county-socioeconomic`, `/data/country-indicators`, and `/data/revisions`.

## Core Tables

- `states`: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`.
- `counties`: `county_fips`, `state_abbr`, `county_name`, `region`, `rucc`, `metro_class`, `population_base`, `latitude`, `longitude`.
- `countries`: `iso3`, `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group`.
- `state_health`: `observation_id`, `state_fips`, `state_abbr`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag`, `released_at`.
- `state_socioeconomic`: `record_id`, `state_fips`, `state_abbr`, `year`, `release_status`, `revision`, `released_at`, socioeconomic fields, `population`, `quality_flag`.
- `county_health`: `observation_id`, `county_fips`, `state_abbr`, `region`, `year`, `measure_id`, `value_type`, `release_status`, `revision`, `released_at`, `value`, intervals, `population`, `suppression_flag`, `quality_flag`.
- `county_socioeconomic`: `record_id`, `county_fips`, `state_abbr`, `region`, `year`, `release_status`, `revision`, `released_at`, socioeconomic fields, `population`, `quality_flag`.
- `country_indicators`: `observation_id`, `country_label`, `iso3`, `year`, `indicator_id`, `release_status`, `revision`, `released_at`, `value`, `unit`, `quality_flag`.
- `revisions`: `revision_event_id`, `domain`, `entity_id`, `field_id`, `effective_year`, `old_value`, `new_value`, `status`, `issued_at`, `reason_code`, `note`.

## Release Resolution

Resolve one selected publication record for each active entity-time-measure/source key before cohort filtering.

- Filter by the active request's geography, measure/field, year, value type, source type, release status, and validity flags.
- Use the active request's ordered release priority. Common patterns are greatest/highest final revision, latest `released_at`, then an observation or record identifier tie-breaker. The identifier tie-break can differ by protocol, so do not assume lowest or greatest unless the active request/profile says so.
- Count selected publication rows before analytic completeness exclusions when the template asks for publication counts.
- Suppressed records remain publication evidence but have unavailable analytic values.

## Missingness And Quality

- Unavailable analytic values: JSON blank, null, suppressed (`suppression_flag` set), invalid quality flags, withdrawn records, unresolved scale breaks, or fields outside the active validity rule.
- Never replace unavailable values with zero.
- Cohorts are complete-case intersections over the exact active variables, years, sources, and geography. Balanced cohorts require completeness in every active period.
- Socioeconomic records can contain nulls in fields not used by the active module; only requested fields affect completeness.

## Geography And Labels

- Preserve state abbreviations and Census division names as listed by the portal.
- County identifiers are text; preserve leading zeros in FIPS.
- For country tasks, reconcile requested labels against `canonical_name`, `portal_label`, and `alternate_labels`; report stable uppercase `iso3` identifiers. Set-like identifier lists are unique and sorted ascending unless the template declares another order.

## Methodology Checks

Use `/methodology` for public policy semantics. The recurring relevant rules are:

- Final releases supersede provisional records; later applied final revisions govern when multiple final revisions exist.
- Suppressed observations publish metadata but not values.
- Age-adjusted values support state comparisons when requested; crude values describe observed county burden when requested.
- RUCC belongs to county geography; RUCC 1 is the usual reference when the request declares indicators `RUCC2` through `RUCC9`.
- Applied country revision notices can authorize scale corrections; pending, withdrawn, or non-applied notices should not silently replace values.
