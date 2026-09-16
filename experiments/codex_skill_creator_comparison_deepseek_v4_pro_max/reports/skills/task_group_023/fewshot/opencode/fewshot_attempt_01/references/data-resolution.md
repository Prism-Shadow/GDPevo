# Data Resolution and Cohort Construction

How to resolve releases, filter records, check completeness, and build
analytic cohorts from portal data.

## Release resolution

For each entity--time--measure key, select exactly one record using the
declared revision priority in order:

1. **Greatest revision number** (newest revision wins).
2. **Latest release timestamp** (most recent release wins among ties).
3. **Lowest record identifier** (lowest `observation_id` or `record_id`
   wins among remaining ties).

This produces a single resolved value per key. Count selected publications
before analytic completeness exclusions when the request asks for them.

## Health measure resolution

When a request specifies a health measure (e.g. `diagnosed_diabetes`),
resolve both the primary value and any auxiliary fields (like `sample_size`)
from the same selected record. The record's fields are:

- `value` --- the numeric observation.
- `sample_size` --- the sample size (used as reliability weight when requested).
- `quality_flag` --- validity indicator.
- `value_type` --- AGE_ADJUSTED or CRUDE.
- `source_type` --- DIRECT_SURVEY or COUNTY_ROLLUP.

Filter health records by the request's declared value type, source type, and
release status before applying revision selection.

## Validity and missingness

Records whose `quality_flag` matches any entry in the request's invalid set
(e.g. INVALID_SCALE, INVALID, WITHDRAWN) are excluded from all analytic use,
even if the value field is populated.

Values that are explicitly `null`, blank, or marked as suppressed are
**unavailable**. Never substitute zero, the mean, or any other value for an
unavailable observation. Count them as missing for completeness checks.

When the request distinguishes between raw missing cells and anomaly cells
(e.g. scale-break observations identified through revision events), count
them separately and report both.

## Imputation (country-level only)

When the request requires imputation (e.g. for country-level PCA matrices),
use only the imputation method declared in the request. A typical pattern:
impute 2022 cross-section cells that are missing after anomaly exclusion using
the nearest available year within a 2-year window for the same
country--indicator pair, preferring more recent years on ties. Count imputed
cells and report the count.

## Completeness checks and cohort construction

A record is **complete** for a given set of fields when every required field
is present, non-null, nonsuppressed, and passes all declared validity
predicates. The request defines which fields must be non-null for each
completeness level.

### Common cohort types

- **Primary cohort**: complete cases in the reference/target year for the
  declared outcome, exposure, and adjustments, within the declared geography
  universe.
- **Balanced panel cohort**: the intersection of entities that are complete
  in every declared analysis year. Construct by taking year-specific complete
  sets and intersecting them across years.
- **Broad / machine-learning cohort**: primary-cohort members that are also
  complete for an extended set of fields (e.g. additional socioeconomic
  variables).
- **Strict dual-source cohort**: entities complete for the outcome, primary
  exposure, parallel exposure, and adjustments in every analysis year.

### Count reporting

When the answer template requires excluded state codes, report every state
code from the jurisdiction universe that is absent from the cohort. Sort them
ascending. When it requires cohort counts by year, report them in year
ascending order.

### State and entity order

Preserve the ASCII-ascending order of entity codes (state abbreviations,
county FIPS, ISO3 codes) for all arrays that track entity-level results. The
request or template may declare a specific order --- follow that exact order.

## Joining health and socioeconomic data

Join health and socioeconomic records on their shared entity and time keys
(state_code + year, county_fips + state_code + year, or iso3 + year). When
a measure appears in both health and socioeconomic datasets (e.g.
food_insecurity may have both a health survey value and a socioeconomic
estimate), use the dataset declared by the request for that measure.

## Reliability weights

When the request declares a reliability weight (e.g. diagnosed_diabetes
sample_size from the selected health record):

- Use the weight from the selected record's sample_size field.
- The weight is fixed per observation and does not change when the outcome
  source is replaced (e.g. in source perturbation modules).
- Apply weights in WLS: multiply the design matrix and outcome by sqrt(weight)
  before solving.
