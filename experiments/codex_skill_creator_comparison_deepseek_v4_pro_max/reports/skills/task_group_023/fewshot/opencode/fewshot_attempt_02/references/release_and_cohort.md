# Release Resolution and Cohort Construction

Every audit begins by resolving the correct release of each data record and building the required analytic cohorts.

## Release Resolution Algorithm

For each unique entity (state/county/country), measure, year, and value type combination, select the single authoritative record:

1. Filter records matching the effective `release_status` (typically `FINAL`), `value_type`, `source_type` (if applicable), and valid `quality_flag` (exclude `INVALID_SCALE`, `INVALID`, `WITHDRAWN`).
2. Among matching records, select the one with the **greatest `revision`** number.
3. If ties remain, select the one with the **latest `released_at`** timestamp.
4. If ties still remain, select the one with the **lowest `observation_id`** (or `record_id` for socioeconomic).

Suppressed values (`suppression_flag` = 1) and null/blank values remain unavailable and are never zero-filled. Count resolved publications before analytic completeness exclusions.

## Cohort Construction

### Basic completeness

A record is **basic-complete** for year Y when all required health values are present, non-suppressed, and non-null, and all required socioeconomic values are non-null. RUCC values must be integer 1–9.

### Core balanced cohort

Entities that are basic-complete for the outcome and all core predictors in **every** analysis year. Sort by entity code ascending. Excluded entities are those missing any required field in any year.

### Broad reference cohort

Entities that are basic-complete for the outcome and all ordered features in the **reference year** (typically specified in the request). Sort by entity code ascending.

### Strict dual-source cohort

Entities that are basic-complete for the outcome, the primary exposure, the parallel exposure, and all adjustment variables in **every** analysis year. This is the most restrictive cohort.

### Machine learning cohort

Broad reference cohort members that are also complete for additional socioeconomic or health fields declared in the request.

### County panels

For county-level audits with change/dynamics specifications, construct balanced panels across the declared panel years. Compute changes as `value_end_year - value_start_year` or as specified in the request. Handle lagged variables by joining across years.

## Sorting and Ordering

- Entity codes: sort ASCII ascending (uppercase two-letter state codes, five-character county FIPS codes)
- Within entity: sort by year ascending
- Feature order: preserve the declared order from the request
- Group order: preserve the declared order from the request (e.g., census division order, source group order)
