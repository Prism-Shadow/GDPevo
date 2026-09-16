# Portal And Data Reference

## Evidence Access

Use the task's configured base URL only. The observed portal exposes:

- `/catalog`
- `/geographies/states`
- `/geographies/counties`
- `/geographies/countries`
- `/data/state-health`
- `/data/state-socioeconomic`
- `/data/county-health`
- `/data/county-socioeconomic`
- `/data/country-indicators`
- `/data/revisions`
- `/methodology`
- `/download?dataset=<dataset>&format=csv`

Prefer `/download?dataset=...&format=csv` for full extracts. The HTML browse endpoints are useful for checking filters, page counts, and methodology links but may paginate.

Dataset names for downloads:

- `states`: state FIPS, abbreviation, name, region, division, `is_state`.
- `counties`: county FIPS, state, region, RUCC, metro class, population base, coordinates.
- `countries`: ISO3-like ID, canonical name, portal label, alternate labels, region, income group.
- `state_health`: observation ID, state, year, measure, value type, source type, release status, revision, value, standard error, sample size, suppression flag, quality flag, released timestamp.
- `state_socioeconomic`: record ID, state, year, release status, revision, released timestamp, socioeconomic fields, population, quality flag.
- `county_health`: observation ID, county, state, region, year, measure, value type, release status, revision, released timestamp, value, CI, population, suppression flag, quality flag.
- `county_socioeconomic`: record ID, county, state, region, year, release status, revision, released timestamp, socioeconomic fields, population, quality flag.
- `country_indicators`: observation ID, country label, ISO3, year, indicator, release status, revision, released timestamp, value, unit, quality flag.
- `revisions`: revision event ID, domain, entity, field, effective year, old/new values, status, issued timestamp, reason, note.

## Methodology Rules To Recheck

Read `/methodology` and relevant `doc=` pages when the task depends on them.

- Final records replace provisional records; highest applied final revisions govern when multiple final revisions exist.
- Suppressed observations retain release metadata but do not publish analytic values. Do not treat suppression or missingness as zero.
- State direct survey estimates are the primary state publication series when requested; rollups are alternate/source-perturbation evidence and must not silently replace direct records.
- Crude and age-adjusted values are distinct publication series. Use only the value type requested.
- FIPS identifiers are text; preserve leading zeros.
- RUCC values live in the county geography reference.
- Country labels reconcile to stable ISO3-like identifiers through canonical names, portal labels, and alternate labels.
- Applied country scale corrections appear in later final revisions. Pending, withdrawn, or non-applied notices do not authorize replacement.
- Quality flags describe review state and do not override release precedence unless the active request declares flags invalid.

## Release Resolution Pattern

For each required data source:

1. Filter by exact active request bindings: geography, years, measure/field, value type, source type, release status, revision constraints, and domain.
2. Keep release metadata even if analytic values are suppressed or null, but mark those records incomplete for analytic cohorts.
3. Select one record per declared key after filtering. The key is usually entity plus year plus measure/field plus source/value type.
4. Use the active priority exactly. Known protocol profiles may require greatest revision, latest `released_at`, and then either lowest or greatest stable identifier. Do not assume the final tie direction; read the request/profile.
5. Reject records with request-declared invalid flags for analytic values. Common invalid flags include `INVALID_SCALE`, `INVALID`, and `WITHDRAWN`.

## Cohorts And Ordering

- State universes normally include all 50 states plus DC unless the request restricts `is_state` or a region.
- County tasks usually join county health, county socioeconomic, and county geography by `county_fips`; state grouping comes from `state_abbr`, region grouping from portal geography, and RUCC from the county geography reference.
- Country tasks resolve requested labels first, then join country indicators by `iso3`.
- Complete-case cohorts require every active analytic field to be present and valid. Balanced panels require the same entity complete in every requested period.
- Broad, strict, machine-learning, replacement, and source-perturbation cohorts have task-specific field requirements; bind them from the request.
- Preserve declared order for years, features, lambdas, alpha/l1 grids, folds, clusters, checkpoints, source groups, and output arrays. For state/county/country identifiers, use the order requested by the template; only sort when the field explicitly says sorted or set-like.

## Country Burden Audit Notes

When a task asks for country burden PCA, clusters, revision reconciliation, and a panel association:

- Resolve every requested label against canonical name, portal label, and alternate labels. Count aliases when the requested label differs from the canonical resolved name.
- For revision outputs, use the `revisions` table restricted to the requested countries, indicators/fields, and period. Report applied and non-applied event IDs according to template ordering.
- Treat unresolved anomaly or scale-break cells as unavailable. Report anomaly observation keys using the template's key format.
- Build the reference-year burden matrix from requested indicators after quality exclusions. Impute only as the request/methodology requires and count imputed cells.
- Orient the burden component so higher burden indicators contribute in the burden direction. If all requested indicators are higher-worse, a positive PC1 loading pattern is the natural high-burden orientation; otherwise use the dictionary direction before PCA sign orientation.
- For three burden labels, order clusters by PC1 burden score and map to `LOW_BURDEN`, `MIDDLE_BURDEN`, and `HIGH_BURDEN`. For candidate-k selection, compare silhouette values on unrounded scores and break ties by smaller k unless the request says otherwise.
- In the panel model, use the active country-year panel, region fixed effects when requested, and report the controlled advisory from the active decision rule.
