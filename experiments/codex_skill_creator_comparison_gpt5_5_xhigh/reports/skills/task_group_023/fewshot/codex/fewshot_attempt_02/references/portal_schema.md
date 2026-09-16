# Public Health Observatory Portal Schema

Use only the base URL supplied by the task. The portal serves HTML browse pages and CSV downloads. Prefer CSV downloads for computation:

```text
GET <base_url>/download?dataset=<dataset_name>&format=csv
```

Allowed dataset names observed from the portal catalog:

| Dataset | Columns |
| --- | --- |
| `states` | `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state` |
| `counties` | `county_fips`, `state_abbr`, `county_name`, `region`, `rucc`, `metro_class`, `population_base`, `latitude`, `longitude` |
| `countries` | `iso3`, `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group` |
| `state_health` | `observation_id`, `state_fips`, `state_abbr`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag`, `released_at` |
| `state_socioeconomic` | `record_id`, `state_fips`, `state_abbr`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `bachelors`, `median_income`, `unemployment`, `uninsured`, `food_insecurity`, `population`, `quality_flag` |
| `county_health` | `observation_id`, `county_fips`, `state_abbr`, `region`, `year`, `measure_id`, `value_type`, `release_status`, `revision`, `released_at`, `value`, `low_ci`, `high_ci`, `population`, `suppression_flag`, `quality_flag` |
| `county_socioeconomic` | `record_id`, `county_fips`, `state_abbr`, `region`, `year`, `release_status`, `revision`, `released_at`, `poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`, `uninsured`, `population`, `quality_flag` |
| `country_indicators` | `observation_id`, `country_label`, `iso3`, `year`, `indicator_id`, `release_status`, `revision`, `released_at`, `value`, `unit`, `quality_flag` |
| `revisions` | `revision_event_id`, `domain`, `entity_id`, `field_id`, `effective_year`, `old_value`, `new_value`, `status`, `issued_at`, `reason_code`, `note` |

## Portal Methodology Signals

- Final records govern publication. When several final revisions exist, use the request/profile's revision priority.
- Suppressed observations keep metadata but publish no analytic value. Do not treat suppression, blanks, invalid flags, or nulls as zero.
- Socioeconomic fields are revised independently; a sparse null field does not invalidate other fields unless the cohort predicate requires it.
- State direct survey estimates are primary when requested. County rollups are parallel estimates for coverage review and must not silently replace direct records.
- FIPS fields are text and leading zeros are meaningful.
- RUCC values 1 through 3 are metropolitan; 4 through 9 are nonmetropolitan.
- Country labels can differ from canonical names. Reconcile requested labels against `portal_label`, `canonical_name`, and `alternate_labels`, then use stable `iso3`.
- Country applied scale corrections appear in later final revisions. Pending or withdrawn revision notices do not authorize replacement; unresolved scale-break cells remain anomalies if no applied correction resolves them.

## Common Release Resolution

For each requested series, filter first by the effective request:

1. Geography/entity universe.
2. Year or period.
3. Measure/indicator/field.
4. `release_status`.
5. Health `value_type` and `source_type` when present.
6. Request-specific validity flags.

Then select one record per declared entity-time-measure key using the active request/profile priority. Common observed priorities are:

- Greatest `revision`, latest `released_at`, then lowest `observation_id` or `record_id`.
- Greatest `revision`, latest `released_at`, then greatest `observation_id` or `record_id`.
- For country revisions, include APPLIED events separately from non-applied events when the template asks for both.

Always report release counts before analytic completeness exclusions when the request asks for selected publication counts.
