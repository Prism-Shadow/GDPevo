---
name: public-health-evidence-audit
description: Reusable workflow for public-health statistical data audits using a browser-accessible evidence portal and linked CSV downloads. Use when Codex must solve state, county, or country health audit tasks that require strict JSON outputs, long-format measure filtering, SES pivots, confounding/mediation/regression checks, ranking adjustments, PCA burden summaries, anomaly logs, spatial residual checks, and exact rounding/enumeration conventions.
---

# Public Health Evidence Audit

## Source Workflow

Use only the current attempt materials and the browser-visible portal named in `environment_access.md`. Read the task prompt, `source_request.txt`, and `answer_template.json` first, then inspect the portal page notes before downloading CSVs. Treat page notes as data-quality requirements: stale rows, blank strata, territory flags, invalid FIPS, old names, scale anomalies, and complete gaps are often intentional.

Download only linked CSVs from the portal. Do not infer from server files or unstaged notes. Load long files with stable dtypes: state abbreviations and ISO3 as strings, FIPS as zero-padded strings, years as integers, and numeric measures with `to_numeric(..., errors="coerce")`.

Preserve measure IDs from the portal. Do not replace IDs with labels in output fields. For county health, physical inactivity is commonly `LPA`; adult obesity is commonly `OBESITY`; current asthma is commonly `CASTHMA`.

## Filtering Rules

For state health Total estimates, require `stratum_type == "Total"` and `stratum == "Total"`. Do not use stale prior-year Total rows unless the prompt explicitly asks for them. Exclude territories using portal flags or state-region validity fields, not by hand-built abbreviation lists. Keep DC when the portal marks it valid for state-level analysis.

For state SES, require both `geo_level == "state"` and a `geo_fips` ending in `000`; county-like rows are distractors. Pivot Attribute-Value SES tables after filtering.

For county audits, pivot county health by `fips`, `state`, `county`, and `measure_id`; pivot county SES by `fips`, `state`, `county`, and `attribute`. Keep FIPS as five-character strings throughout joins and output. Count exclusions explicitly: invalid FIPS, outside requested states, missing SES fields actually needed by the model, and missing health measures actually requested.

For country audits, join by `iso3` whenever available. Use name-variant tables to audit reconciliation coverage, but do not confuse `lending_category` with `income_group`.

## Modeling Conventions

Use standardized coefficients when fields ask for `std_beta` or mediation `beta`: standardize the outcome and continuous predictors on the analysis sample, then fit OLS. Use the same complete-case sample when comparing static and dynamic specifications.

Use the core SES level variables unless the prompt asks for more: `PCTPOVALL_2023`, `MEDHHINC_2023`, `Unemployment_rate_2023`, and `Percent_bachelors_or_higher_2019_23`. Treat `POP_ESTIMATE_2023`, migration, and natural-change fields as optional only when the prompt or schema implies them.

For county dynamic SES fields, compute:

```text
unemployment_change = Unemployment_rate_2023 - Unemployment_rate_2010
income_change = MEDHHINC_2023 - Median_Household_Income_2022
```

Handle RUCC as categorical dummies when requested; do not treat it as a linear numeric score. For static/dynamic AIC comparisons, fit models on identical complete cases and choose the lower AIC. Report AIC rounded to 2 decimals.

For mediation audits, fit the mediator model and outcome model on the same rows, compute the indirect effect as `poverty_to_mediator_beta * mediator_to_outcome_beta`, and use a percentile bootstrap for the CI. Set CI enum by sign: positive excludes zero, negative excludes zero, or includes zero.

For VIF diagnostics, compute VIF on the adjusted predictor matrix excluding the intercept. Identify collinearity culprit pairs by highest absolute predictor correlation, and sort the two predictor IDs ascending in the output when the schema requires it. For leverage sensitivity, compute hat values from the adjusted model, drop the top leverage units, refit, and classify sign flips, significance changes, or magnitude shifts.

Avoid residual-index bugs: after fitting a model, attach residuals positionally to a reset-index copy of the model data.

## Ranking Audits

Determine priority direction from the measure semantics before ranking. For prevention/screening prevalence, lower values are usually worse; for burden/risk outcomes, higher values are usually worse.

When income-quartile rows are used, require `stratum_type == "Income quartile"` and map bracket labels deterministically to `Q1`-`Q4`. Count coverage by bracket. If rows are modeled with sample-size weights, `sample_size_weighted_rows` is the number of analytic rows with usable weights unless the schema explicitly asks for a sum of sample sizes.

Use rank 1 as highest priority/worst after applying `priority_direction`. Define rank shifts consistently, for example `crude_rank - adjusted_rank`, so positive values move upward in priority after adjustment and negative values move downward. Break ties deterministically by adjusted rank, then state/FIPS.

Do not treat blank demographic labels as valid age or sex strata. If required demographic strata are blank or missing, report direct demographic standardization as not feasible, even if other non-demographic strata exist.

## Spatial And Residual Checks

Use the portal neighbor reference for residual spatial summaries. Count isolate states directly from the neighbor table. For Moran's I, state the unit used by the task context: state-mean residuals for state-neighbor references, or county-level weights only when county adjacency is actually available.

If a field says `top_positive_residual`, sort residuals descending. If it says `outlier` without direction, use absolute residual magnitude unless the prompt frames hotspots or excess burden. For division hotspots, aggregate residuals by census division and report the division with the largest positive mean or positive-residual burden, matching the field wording.

## Country PCA Audits

Detect and log scale anomalies before PCA. Values that are clearly off by a factor such as 10 or 100 should either be corrected with an anomaly log or excluded from PCA, but never silently retained raw. Complete variable gaps for a country must be reported and considered when choosing retained variables.

For PCA burden scores, choose retained variables from the schema's allowed IDs, compute missing rates for retained candidates, complete-case rows across retained variables, standardize variables, and fit PCA. Orient PC1 so higher scores mean higher burden: mortality variables should load positively after orientation. Report top absolute loadings by absolute value and top positive loadings by signed loading.

When clustering PC1 burden scores, order clusters by their PC1 centers or score ranges and label them `low_burden`, `middle_burden`, and `high_burden`. For grouped model checks, join income group by ISO3, compute join coverage, then compare pooled versus income-group random-intercept structure and report the variance ratio bucket.

## Rounding And JSON Hygiene

Follow `answer_template.json` exactly. Return one JSON object only for task answers. Use numeric JSON values, not strings, for rounded numbers.

Round only at the final output:

- AIC and VIF: 2 decimals.
- Standardized betas, ICC, Moran's I, PCA variance share, join coverage, missing rates, CI bounds: 3 decimals unless the schema says otherwise.
- Attenuation percentages: 1 decimal.
- Tercile means and similar grouped means: the schema's requested precision, often 2 decimals.

Use p-value buckets strictly: `<0.001`, `<0.01`, `<0.05`, otherwise `ge_0_05`; use `not_computed` only when no model/p-value was fit. Apply bucket thresholds after computing exact values, not after rounded display values.

Sort arrays only when the schema says sorted; otherwise preserve semantic order: prompt order for `requested_states`, metric order for leverage/residual/rank-shift arrays, and analysis order for retained PCA variables.

## Common Pitfalls

Do not mix territories with states. Do not mix state SES county-like distractors with true state rows. Do not let old county names or invalid FIPS pass joins unnoticed. Do not include optional SES attributes in complete-case counts unless the model actually uses them. Do not let a single complete variable gap silently drop an entire country from PCA without reporting it.

Check every enum value against the template before finalizing. Many wrong answers come from correct analysis with the wrong enum, ordering, or rounding precision.
