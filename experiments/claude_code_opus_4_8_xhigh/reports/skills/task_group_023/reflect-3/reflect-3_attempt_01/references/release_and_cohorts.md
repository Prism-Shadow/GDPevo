# Release resolution & cohort construction (the shared foundation)

Every PHO audit begins with the **same** two-step foundation, then feeds the resulting
tidy panel into the modules. Getting this exactly right is worth more than any single
model, because every downstream count, coefficient and gate depends on it — and the
answer template's first block is almost always a cohort/census audit whose integer counts
you can reason about directly.

## Step 1 — resolve the registered FINAL release for each cell

For the relevant dataset, define the **cell key** from the task's filters. Examples:

- state health cell = `(state_abbr, measure_id, year, value_type, source_type)`
- county health cell = `(county_fips, measure_id, year, value_type)` (+ region as needed)
- socioeconomic cell = `(entity, year)` (all fields share one record)
- country cell = `(iso3, indicator_id, year)`

Then, **within each cell**, keep one record by the registered priority:

1. `release_status == FINAL` (drop provisional unless the task explicitly allows it),
2. highest `revision`,
3. latest `released_at`,
4. descending id (`observation_id` / `record_id`) as the final tiebreak.

Some tasks state this priority verbatim (e.g. `["revision","released_at","observation_id"]`
or `HIGHEST_FINAL_REVISION_THEN_LATEST_RELEASE`). Use `Portal.resolve_final` in
`assets/portal.py`. Apply declared **value_type / source_type / release_status** filters
*before* resolving so you resolve within the requested series.

Apply revision notices where relevant: `APPLIED` scale corrections should already be in
the final series; `PENDING`/`WITHDRAWN` scale breaks make a cell an unresolved anomaly to
exclude.

## Step 2 — availability, then complete-case cohorts

A cell is **available** iff: not suppressed (`suppression_flag != 1`), value non-null, and
quality flag not in the task's declared invalid set. `Portal.available` does this. Socio
fields are revised independently — a null in one field does not invalidate the others in
the same record, so evaluate availability **per requested field**.

Build cohorts as **complete-case** sets over the task's *required* variable list. Read the
task's exact wording; the recurring cohort shapes are:

| cohort archetype | definition |
|---|---|
| per-year complete | jurisdictions with **all** required "core panel" variables available in that year |
| **balanced panel** | jurisdictions complete in **every** requested analysis year (intersection across years); rows = states × years |
| **reference-year / broad** | complete cases in the reference year for the outcome **and every ordered model feature** (often a longer feature list than the core panel) |
| **strict / dual-source** | complete for outcome + primary exposure + parallel exposure + adjustments in every year (used by source-perturbation modules) |
| **machine-learning** | a base cohort intersected with extra required predictors (e.g. unemployment, migration, uninsured) |

Rules that trip people up:

- The **jurisdiction universe** for states is 51 (50 states + DC). "50 states + DC".
- **Excluded-code** fields = universe minus the cohort, sorted as the template says
  (usually ascending ASCII), *complete set, no others*.
- Counts you will typically report: resolved observation/record totals, per-year complete
  counts, primary/reference count, balanced count, ML count, distinct state count,
  balanced observation rows (= states × years).
- Region/division come from the **geography** tables (`states.division`,
  `counties.region`/`rucc`); join them on, don't infer them.
- `median_income` is frequently rescaled (`per_10000`, or natural-log of the *unscaled*
  value). Apply the transform the model spec names, not before cohorting.

## Census divisions & regions (from `states`)

Nine Census **divisions** (used as CV/cluster groups). The portal's `states.division`
strings are the canonical labels; sort/emit them in the order the task registers (often
this fixed geographic order):

1. New England 2. Middle Atlantic 3. East North Central 4. West North Central
5. South Atlantic 6. East South Central 7. West South Central 8. Mountain 9. Pacific

Four **regions**: Northeast, Midwest, South, West (South Atlantic includes DC). Always read
`division`/`region` from the live `states`/`counties` tables — never hardcode a mapping.

## Sanity checks before modelling

- resolved cells == distinct keys (no duplicate survivors after resolution).
- balanced rows == balanced states × number of years, exactly.
- every excluded list is the exact complement of its cohort within the universe.
- no zero-filled cell entered any cohort.
