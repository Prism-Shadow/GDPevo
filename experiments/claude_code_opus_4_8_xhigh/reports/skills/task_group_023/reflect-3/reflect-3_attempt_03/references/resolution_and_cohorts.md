# Release resolution and cohort construction

Get this layer exactly right first; every module inherits it.

## 1. Final-release resolution (per cell)

Define a **cell** by its natural key:

- health: `(entity, year, measure_id, value_type, source_type)`
- socioeconomic: `(entity, year)` (fields resolved together within a record)
- country indicator: `(iso3, year, indicator_id)`

Algorithm:

1. Keep only `release_status == FINAL` records for the cell (PROVISIONAL never wins
   when a FINAL exists; if the spec says FINAL-only and none exist, the cell is
   unavailable).
2. Among finals, choose the record with the **highest `revision`**. Break ties by
   latest `released_at`, then by id. (Some requests phrase this as
   "HIGHEST_FINAL_REVISION_THEN_LATEST_RELEASE" — same rule. Others give an explicit
   revision-priority tuple like `[revision, released_at, observation_id]`; follow the
   tuple literally.)
3. Apply the request's health filter (`value_type`, `source_type`, `release_status`)
   *before* resolving, so you resolve within the requested series.

A resolved value is **usable** only if it is non-suppressed and non-null:
`suppression_flag != 1`, `quality_flag` not in the request's invalid set (commonly
`SUPPRESSED`, and any `INVALID`/`INVALID_SCALE`/`WITHDRAWN`), and `value` present.
Otherwise the cell is unavailable — **never zero-fill**.

## 2. Scale-break anomalies (country indicators)

An **unresolved scale break** is a cell whose SCALE_CORRECTION revision is *not*
APPLIED (PENDING or WITHDRAWN), so the anomalous (un-corrected) value stands. After
resolution these cells surface as a resolved record with quality flag `SCALE_REVIEW`
(APPLIED corrections instead resolve to a later `CORRECTED` revision). Treat unresolved
scale-break cells as anomalies:

- Key them `ISO3|YEAR|indicator_id` (sorted ascending) for the audit output.
- Exclude them from the analysis matrix, then impute alongside genuinely missing cells.
- `raw_missing` counts cells missing *before* anomaly exclusion; `anomaly` counts the
  scale-break cells; `imputed` counts everything filled after exclusions.
- "Applied vs non-applied revision event ids" for the audit = the in-scope revision
  events (matching resolved entity, requested field, in-scope year) split by
  `status == APPLIED`.

## 3. Country label reconciliation

For each requested label, match to a country by `portal_label`, else `canonical_name`,
else any of the pipe-separated `alternate_labels`. Report:

- `resolved_label_count` = labels uniquely reconciled.
- `alias_resolution_count` = resolved labels whose text differs from the country's
  `canonical_name` (i.e. matched via a non-canonical label).
- `resolved_iso3` = the unique uppercase ISO3 codes, sorted ascending.

## 4. Cohort patterns

Requests reuse a small vocabulary of cohorts. Compute **complete-case** membership per
(entity, year) first, then derive the rest.

- **Complete-case (year y)**: every *selected* health value for the required measures is
  resolved & usable; the required SES fields (e.g. poverty, median_income, bachelors)
  are non-null; any required extra key is valid (e.g. RUCC an integer 1–9; a required
  `sample_size` non-null). Exactly which fields are "required" is spelled out in the
  request's `evidence_specification` / `publication_selection` / `complete_case` text —
  follow it verbatim.
- **Primary / reference-year cohort**: complete-case in the reference year, drawn from
  the declared jurisdiction/geography universe.
- **Balanced panel cohort**: entities complete-case in **every** analysis year
  (intersection across years).
- **ML / augmented cohort**: primary-cohort members that are *also* complete for a set
  of extra fields (e.g. unemployment, net_migration, uninsured) in the reference year.
- **Strict dual-source cohort**: complete for the outcome, the primary exposure series,
  the parallel exposure series, and adjustments in every analysis year.
- **Broad reference cohort**: reference-year complete cases for the outcome and *all*
  ordered model features (health + socioeconomic).

For each cohort report the count and, when asked, the **sorted** member and **excluded**
code lists. An excluded set = (universe) − (cohort), and must be exactly complete —
"every universe code absent from the cohort, and no others."

Panel-row counts: a *dynamics* panel over end-years {2022,2023,2024} has
`panel_rows = balanced_entities × (#end_years)`; a per-state census reports
`{code, balanced_entities, panel_rows}` per state, ordered by code.

## 5. Cross-checks

- Region scope constrains the state universe: a region-scoped `state_count` cannot
  exceed the number of jurisdictions in those regions (read it off the geography
  reference). If your cohort spans states outside the scoped regions, a filter is wrong.
- "50 states and DC" ⇒ universe of 51.
- Socioeconomic fields revise independently; do not drop a record because an *unused*
  field is null.
