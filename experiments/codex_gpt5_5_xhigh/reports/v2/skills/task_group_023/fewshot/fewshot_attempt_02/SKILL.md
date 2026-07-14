---
name: public-health-portal-audit
description: Public-health statistical data audit workflow for browser-accessible evidence portals with linked CSV downloads. Use when solving staged tasks that ask Codex to audit state, county, or country health claims using portal pages, CSV exports, socioeconomic/reference joins, regression/PCA/mediation/spatial diagnostics, and strict JSON answer templates.
---

# Public Health Portal Audit

## Operating Rules

- Read the staged task prompt, `environment_access.md`, and any staged answer template in the current attempt directory. Do not use hidden implementation files, evaluator files, previous runs, source answers, or paths outside the staged attempt.
- Replace `<TASK_ENV_BASE_URL>` with the base URL from `environment_access.md`. Use only browser-visible portal pages and linked CSV downloads.
- Download CSVs from the relevant portal pages instead of retyping tables. Inspect headers, row counts, unique IDs, years, strata, and missingness before modeling.
- Return exactly the requested JSON object. Match template keys, enums, array order expectations, capitalization, and numeric precision. Do not add prose outside JSON.

## Data Assembly

- Keep health data in long format until filtering is complete. Filter by exact `measure_id`, `year`, geography, and total rows such as `stratum_type == "Total"` and `stratum == "Total"` when the task asks for overall state/county rates.
- Preserve measure IDs in outputs. Labels are useful for interpretation, but IDs drive joins and answer fields.
- Treat state, county, and country pages as separate grains. Never join state SES rows to county health rows or county SES rows to state health rows.
- Preserve FIPS and ISO codes as strings. County FIPS must remain 5 characters with leading zeros; flag invalid FIPS separately from valid counties with missing data.
- Exclude territories unless the prompt requests them. Include DC when it appears as a state-level row and the prompt asks for states/state rankings without excluding it.
- Use complete-case analytic samples for models unless the task explicitly requests imputation. Count exclusions transparently: outside requested geography, invalid geography code, missing health data, and missing SES/reference data.
- For demographic standardization tasks, verify that demographic strata actually exist. If demographic strata are blank or only total rows are available, report standardization as infeasible and use the requested proxy adjustment.
- Build income proxies or brackets from available SES fields after confirming coverage. For quantile brackets, report the actual bracket counts because ties and odd sample sizes can make groups uneven.

## Common Field Conventions

- State SES fields often use explicit year suffixes such as median household income, poverty, and unemployment columns. Use the exact field names from the CSV in output fields that ask for culprit variables or dynamic rules.
- County dynamic change variables are usually constructed from named-year differences, for example current unemployment minus baseline unemployment and current income minus prior-year income. State the subtraction rule explicitly when requested.
- RUCC/rurality fields are categorical. Use dummy variables or fixed effects; do not treat RUCC as a continuous linear score unless the prompt explicitly says to.
- Region, division, neighbor, metadata, and name-reconciliation pages are reference joins. Audit join coverage and unresolved rows before using their fields in models.

## Modeling Checks

- Standardize continuous predictors and outcomes before reporting standardized betas. Fit the bivariate model first, then the adjusted model on the same complete-case sample when comparing attenuation.
- Compute attenuation as the percent reduction from the bivariate standardized coefficient to the adjusted standardized coefficient, using the unrounded coefficients.
- For confounding audits, report p-value buckets, VIF or correlation diagnostics, the most collinear pair, regional clustering/ICC when a region reference is supplied, and influential states or counties using leverage/Cook's distance/residual criteria.
- For ranking audits, respect the priority direction. Some prevention measures are worse at lower values, so priority rank may be ascending rather than descending. Compare crude and adjusted ranks on the same valid geography set.
- For weighted state models, use the row's population/sample-size weight when a task asks for weighted direction or weighted ranking adjustment.
- For county reconciliation audits, compare static and dynamic SES specifications with AIC on the same complete-case sample. The lower AIC wins; if reporting residual outliers, sort by the requested residual direction/magnitude and use stable code ordering for ties.
- For mediation audits, estimate the poverty-to-mediator path, mediator-to-outcome path, indirect effect, and bootstrap confidence interval. The bootstrap enum should reflect whether the interval includes zero.
- For residual spatial checks, use the portal neighbor reference. Exclude or count isolates explicitly; compute Moran's I on model residuals for counties with valid neighbor links.
- For country panels, reconcile country names/ISO codes before modeling, audit metadata coverage, log scaled or anomalous country-year values, standardize retained variables for PCA, and orient burden scores consistently with the task's burden definition.
- Prefer grouped/mixed interpretations only when the income-group or region random-intercept variance is material and join coverage supports the grouping variable.

## Rounding And Enums

- Run calculations at full precision and round only at the final JSON step.
- Typical precision: coefficients, standardized betas, ICC, Moran's I, variance ratios, missing rates, and PCA variance shares to 3 decimals; AIC to 2 decimals; rank correlations to 2 decimals; counts as integers.
- Use task/template bucket enums instead of raw p-values when requested. Common p buckets are `lt_0_001`, `lt_0_01`, `lt_0_05`, and `ge_0_05`; common diagnostic buckets use threshold names such as `lt_5`, `ge_0_15`, or `includes_zero`.
- Sort arrays by the task's analytic criterion, not alphabetically, unless the field is an inventory such as included states, requested states, retained variables, or excluded territories.

## Pitfalls

- Do not infer unavailable demographic detail from total-only rows.
- Do not mix labels and IDs in filters; labels can change while IDs are stable.
- Do not let pandas parse FIPS as integers.
- Do not count excluded rows after an inner join has already dropped them; compute exclusions from the pre-join universe.
- Do not round intermediate coefficients before calculating attenuation, indirect effects, PCA loadings, or rank shifts.
- Do not ignore missing SES/reference rows just because the model can run after dropping them; report the analytic sample and exclusions.
- Do not use local implementation files or hidden task notes to shortcut the portal audit.
