---
name: public-health-statistical-data-audits
description: Reusable workflow for solving public-health statistical audit tasks from a browser-accessible evidence portal with linked CSV downloads, including filtering, joins, modeling, rounding, and pitfalls.
---

## Operating Rules

- Work from the staged prompt, answer template, source request, `environment_access.md`, and the portal's browser-visible pages plus linked CSV downloads. Do not assume implementation files or unstaged answers exist.
- Read the relevant portal pages before downloading data. Page notes often define missing rows, stale years, territory flags, invalid FIPS, blank strata, name variants, and scale anomalies.
- Treat the answer template as the contract. Match enum spelling exactly, preserve required object keys, and order arrays exactly as requested.
- Keep identifiers as strings where they are identifiers: state abbreviations, ISO3, and especially 5-digit county FIPS. Never let CSV parsing drop leading zeroes.

## Portal And Field Conventions

- State health rows are long-format. For crude state analyses, filter by exact `year`, `measure_id`, `stratum_type == "Total"`, `stratum == "Total"`, and non-territory rows unless the prompt says otherwise. Do not mix stale prior-year rows or stratified rows with Total estimates.
- State SES rows are attribute-value records. True state rows require both `geo_level == "state"` and a `geo_fips` ending in `000`; county-like distractors can share state abbreviations.
- Use the region or neighbor reference files as supplied. Count territories, invalid rows, isolates, or analysis-valid states from their explicit flags rather than from memory.
- County health rows are long-format by `measure_id`; pivot only after filtering to the requested year and measures. Preserve the original measure ids in the final answer.
- County SES rows must be pivoted by 5-digit FIPS. Join through county metadata when the task asks for RUCC, economic typology, census division, invalid FIPS, or old-name handling.
- Country panels usually join most safely by ISO3. Use name-variant tables to report reconciliation coverage or repair names only when the current panel actually needs it.

## Filtering And Reconciliation

- Build a clear analysis universe before modeling. A reliable county sequence is: metadata universe, remove invalid FIPS, remove outside requested states, join SES, join health, then count missing SES and missing health among the remaining records.
- Keep requested state arrays in prompt order unless the template explicitly asks for sorted order. Keep exclusion arrays sorted when requested.
- For complete-case counts, define the exact variables needed for the model first; count missingness against that set, not against every column in a CSV.
- For country anomaly logs, identify country-year scale issues and complete variable gaps explicitly. Do not silently fix or drop anomalies unless the task wording says to use corrected values.

## Modeling Habits

- State and county regression audits commonly expect continuous variables to be standardized before reporting `std_beta` or path `beta` fields. Standardize within the analytic sample.
- Be explicit about the adjustment formula before fitting. Distinguish current-level SES controls from dynamic change controls such as income 2023 minus income 2022 and unemployment 2023 minus unemployment 2010.
- Treat RUCC as categorical dummies when requested; do not use it as a linear score unless the template says so.
- For VIF and collinearity diagnostics, compute VIF on the actual adjusted predictor matrix and report the largest predictor and its strongest high-correlation pair.
- For leverage and residual outliers, fit the stated adjusted model first. Use leverage order for leverage fields, positive residual order for positive-residual flags, and absolute residual order only when the field says residual outlier without direction.
- For mediation, report the indirect effect as the product of the poverty-to-mediator path and mediator-to-outcome path from the same model specification. Bootstrap the product, not the two paths separately.
- For PCA burden scores, report missing rates before complete-case filtering, standardize retained variables, orient PC1 so higher score means higher burden, and then order loading fields by signed or absolute loading as named.
- For grouped country models, join income group onto the same rows used for the score and compare a random-intercept structure against pooled interpretation. Report variance ratios on the fitted score scale.

## Ranking And Spatial Checks

- For ranking audits, define priority direction first. Screening and prevention measures usually make lower values worse; risk-factor or mortality measures usually make higher values worse.
- Document whether an adjusted ranking uses direct standardization, sample-size weighting, residualization, or fixed effects. The same rows can produce different rank shifts.
- Compute rank shifts from a single convention and keep the sign consistent. If higher priority is rank 1, a positive shift can mean moving upward only if defined as crude rank minus adjusted rank.
- Use the portal neighbor table for spatial residual summaries. Do not infer county adjacency from FIPS or geography. Count isolate states from `isolate_flag`.
- If the neighbor table is state-level and the residuals are county-level, decide whether the task calls for state-mean residual Moran's I or county pairs induced by state-neighbor edges; keep the residual outlier flags at the county level unless the template says otherwise.

## Rounding And Buckets

- Round only at final serialization: betas and PCA/model shares usually to 3 decimals, AIC and means to 2 decimals, attenuation to 1 decimal, and VIF to 2 decimals when requested.
- P-value buckets are thresholded in order: `<0.001`, `<0.01`, `<0.05`, otherwise `ge_0_05`; use `not_computed` only when no valid model was fit.
- Bucket numeric diagnostics from the unrounded value, then serialize the rounded number separately.
- Preserve exact enum values from the template. Do not invent synonyms such as "significant" or "stable_after_controls".

## Common Pitfalls

- Do not treat blank stratum labels as valid demographic strata.
- Do not include territory or invalid FIPS rows in state or county analytic samples unless explicitly requested.
- Do not merge SES state rows with county-like distractors, and do not merge county FIPS after converting them to integers.
- Do not confuse `income_group` with lending category in country metadata.
- Do not let one scale anomaly dominate PCA without at least logging it and checking the task's intended anomaly handling.
- Do not copy portal table previews as the full dataset; use the linked CSV downloads for calculations.
