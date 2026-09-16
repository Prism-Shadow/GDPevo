# Data Resolution Rules

## Release Resolution Algorithm

For every combination of entity, year, measure, value type, and source type
needed by a task, resolve exactly one authoritative record:

```
def resolve_record(records, filters):
    # 1. Apply explicit filters from the analysis request
    candidates = [r for r in records if matches_request_filters(r, filters)]

    # 2. Among candidates, select the one with the greatest revision number
    max_rev = max(r.revision for r in candidates)
    candidates = [r for r in candidates if r.revision == max_rev]

    # 3. Among remaining, select the one with the latest released_at
    latest = max(r.released_at for r in candidates)
    candidates = [r for r in candidates if r.released_at == latest]

    # 4. Among remaining, select the one with the lowest record identifier
    #    (observation_id for health, record_id for socioeconomic)
    selected = min(candidates, key=lambda r: r.record_id)
    return selected
```

**Key rules:**

- **Revision supremacy**: A higher revision number ALWAYS beats a lower one,
  regardless of release date. The `revision` field is an integer.
- **Timestamp tiebreak**: Only when revisions are equal, prefer the record
  released later.
- **ID tiebreak**: Only when both revision and released_at are equal, prefer
  the record with the lower `observation_id` (health) or `record_id`
  (socioeconomic/county).
- **Provisional exclusion**: When the request specifies `FINAL` (as all
  audit tasks do), PROVISIONAL records are excluded from consideration at
  step 1.

## Request Filter Composition

The `analysis_request.json` declares filters through several mechanisms:

### Explicit declaration (state health)
```json
"primary_health_filter": "AGE_ADJUSTED_AND_DIRECT_SURVEY_AND_FINAL"
```
This means: `value_type=AGE_ADJUSTED`, `source_type=DIRECT_SURVEY`, `release_status=FINAL`.

Other common compactions:
- `CRUDE_AND_DIRECT_SURVEY_AND_FINAL` → CRUDE, DIRECT_SURVEY, FINAL
- `FINAL` → release_status=FINAL only

### Per-measure filters (county health)
```json
"health_filters": {"value_type": "CRUDE", "release_status": "FINAL"}
```
Apply to every health measure pulled.

### Per-dataset filters (socioeconomic)
```json
"socioeconomic_filter": {"release_status": "FINAL"}
```

### Inline source specifications (state)
```json
"baseline_outcome_source": {
    "measure_id": "diagnosed_diabetes",
    "value_type": "AGE_ADJUSTED",
    "source_type": "DIRECT_SURVEY",
    "release_status": "FINAL"
}
```

## Missing Value Handling

### Health observations
- The HTML table shows suppressed values as an em dash character.
- In CSV, suppressed cells appear as empty/blank or contain the em dash.
- `suppression_flag=1` marks suppressed records.
- `quality_flag=SUPPRESSED` may also appear.
- **Never zero-fill.** Suppressed, blank, null, or emdash values mean the
  observation is unavailable for analytic computation.

### Socioeconomic releases
- Fields are independently revised; a null in `unemployment` does not
  invalidate the `poverty` value in the same record.
- Missing values appear as an em dash in HTML, blank in CSV.
- The methodology note "Socioeconomic release fields" confirms sparse null
  fields do not invalidate other published fields in the same record.

### Country indicators
- Missing values appear as an em dash.
- Scale anomalies: cross-check with `/data/revisions?domain=COUNTRY`.
  Records of the form `iso3|YEAR|indicator_id` matching a non-APPLIED
  (PENDING or WITHDRAWN) revision event are scale-anomalous. Applied
  corrections are already reflected in later final values.

## Dual-Source Resolution (state health)

When both a primary (direct) and parallel (rollup) source are required
(e.g. for source perturbation audits):

1. Resolve the primary series independently using the primary filter.
2. Resolve the parallel series independently using the parallel filter.
3. A state is "dual-source complete" for a year only when BOTH series
   resolve with nonsuppressed, nonmissing values for that state-year.

## County Health Resolution

County health observations differ from state health in several ways:
- They have `county_fips` instead of `state_fips`
- They include `region` directly in the record
- They have `low_ci`/`high_ci` confidence interval bounds
- They may have `AGE_ADJUSTED` or `CRUDE` value types
- The revision priority order is the same: highest revision, then latest
  released_at, then lowest observation_id

## Country Indicator Resolution

Country indicator observations require an extra reconciliation step:
1. Pull the geography reference `/geographies/countries` to build the
   label-to-ISO3 mapping.
2. For each label in the request's `country_labels` array, find the
   resolving ISO3 by matching against all `portal_label`, `canonical_name`,
   and pipe-separated `alternate_labels` entries.
3. Pull indicator data by the resolved ISO3 codes, not by labels directly.
4. Additionally pull `/data/revisions?domain=COUNTRY` to identify which
   indicator-country-year combinations are affected by scale anomalies.
