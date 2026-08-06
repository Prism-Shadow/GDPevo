# Release resolution, revision notices, and cohort construction

This is the highest-leverage stage: modelling on the wrong cohort fails every
downstream field. Do it deterministically and report the audit counts the template
asks for. The request names the rules (`evidence_specification`,
`publication_selection`, `evidence_and_cohorts`, `scope_and_publication`, ...); the
patterns below recur across every variant.

## 1. Resolve the governing release for each logical cell

A *logical cell* is the tuple that identifies one published quantity, e.g. for state
health: `(state, year, measure_id, value_type, source_type)`; for socioeconomic:
`(entity, year)` per field. Steps:

1. **Filter to the declared release.** Keep only rows matching the request's
   `release_status` (almost always `FINAL`), and for health the declared `value_type`
   (`AGE_ADJUSTED` vs `CRUDE`) and `source_type` (`DIRECT_SURVEY` vs `COUNTY_ROLLUP`).
   A primary vs parallel exposure means two different (value_type, source_type)
   pulls of the *same* measure.
2. **FINAL supersedes PROVISIONAL** — if any FINAL row exists for the cell, discard
   provisional rows for that cell entirely.
3. **Pick the governing revision.** When multiple FINAL revisions remain, apply the
   request's declared priority, which is consistently *highest final `revision`*,
   then latest `released_at`, then a stable id tiebreak (`observation_id` /
   `record_id`). Requests spell this out (e.g. `health_revision_priority:
   [revision, released_at, observation_id]`, or `HIGHEST_FINAL_REVISION_THEN_
   LATEST_RELEASE`). Example: a cell with FINAL rev 1 (`REVIEWED`) and FINAL rev 2
   (`REVISED`) resolves to **rev 2**.
4. Quality flags do **not** change precedence — a `STALE`/`CAUTION`/`REVISED` flag on
   the governing revision is retained, not a reason to fall back to an earlier one.

## 2. Apply revision notices and flag anomalies

The `revisions` dataset records scale corrections and source restatements keyed by
`domain, entity_id, field_id, effective_year`:

- **`status = APPLIED`** notices are authoritative and are already reflected in the
  later final revisions. When the template asks, list applied vs non-applied
  `revision_event_id`s (sorted as specified).
- **`WITHDRAWN` / `PENDING`** notices do **not** authorise replacing a value.
- An **unresolved scale break** — a cell whose published value still exhibits the
  discontinuity that only a non-APPLIED notice would have fixed — is an **anomaly**:
  exclude it from the analytic matrix (it is not a valid observation) and, when
  required, report it as `ISO3|YEAR|indicator_id` (or the template's key form).
  Anomalies are excluded *before* counting imputable missing cells.
- Distinguish, when the template separates them: raw missing cells, anomaly cells,
  and cells imputed after quality exclusions.

## 3. Missing / suppression discipline (never zero-fill)

A value is **unavailable** if it is suppressed (`suppression_flag = 1`), blank/null,
carries an invalid quality flag (the request lists these, e.g. `INVALID_SCALE`,
`INVALID`, `WITHDRAWN`), or is an unresolved-scale-break anomaly. Unavailable ≠ 0:
never substitute 0, and never emit NaN/Infinity. A record missing any field a cohort
requires is dropped from that cohort (complete-case). Report the unavailable value as
JSON `null` only where the *template* asks for that statistic and it is genuinely
undefined.

## 4. Build each named cohort exactly

Requests define several cohorts; build each to its literal definition. Recurring ones:

- **Reference-year complete-case / "primary" cohort** — jurisdictions with all
  required fields present (non-suppressed, non-null) in the single reference year,
  drawn from the full jurisdiction universe (51 states + DC, or the requested county
  or country set).
- **Balanced panel cohort** — the intersection: entities complete in *every*
  requested analysis year.
- **Strict / dual-source / machine-learning cohort** — primary members that are also
  complete for an extra set of variables (e.g. parallel exposure, extra
  socioeconomic fields) in the required years.
- **Broad reference cohort** — reference-year complete cases for the outcome and all
  ordered feature-list variables.

For each, report exactly what the template names: the cohort `n`, per-year complete
counts (in year order), the included entity codes, and the **complete** excluded set
(every universe code absent from the cohort, and no others), all in the template's
identifier order (usually ascending ASCII/code order). Panel row counts =
entities × years for balanced panels.

## 5. Country label reconciliation (country tasks)

Resolve each requested `country_label` to a canonical country via the `countries`
dataset: match against `canonical_name`, `portal_label`, and the `|`-split
`alternate_labels`. Emit `iso3` (uppercase). `alias_resolution_count` = resolved
labels whose matched string differs from the `canonical_name`. Deduplicate;
set-like id lists are unique and sorted ascending.

## 6. Reproducibility checkpoints

Keep the raw CSV pulls and the resolved-cohort table. Every later module consumes the
*same* governing-release values (including, e.g., a fixed reliability weight taken
from the selected record's `sample_size`). Recompute cohorts from cached raw pulls so
the whole pipeline is deterministic and re-runnable.
