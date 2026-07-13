---
name: public-health-portal-audits
description: Use for public-health statistical data audit tasks that rely on a browser-accessible evidence portal with linked CSV downloads and require structured JSON answers about state, county, or country health data, socioeconomic joins, reconciliation, regression, PCA, mediation, ranking, or spatial diagnostics.
---

# Public Health Portal Audits

## Operating Rules

1. Start from the staged prompt, `input/payloads/source_request.txt`, `input/payloads/answer_template.json`, and `environment_access.md`. Use the base URL only to access browser-visible portal pages and their linked CSV downloads. Do not use implementation files or paths outside the staged attempt directory.
2. Treat `answer_template.json` as the contract. Return one JSON object, no prose, exact keys, exact enum strings, real booleans/numbers, and the required `task_id`.
3. Prefer downloaded CSVs over hand-copying UI tables. Keep a local note of which portal page and CSV supplied each table, then compute from the raw rows.
4. Do not memorize solved values. Recompute each requested field from the current portal data and prompt scope.

## Data Assembly

- Preserve stable identifiers. Use `measure_id`, state abbreviation, 5-digit county FIPS string, ISO3, year, stratum fields, and reference-table IDs rather than display labels when both exist.
- Health tables are often long by measure/year/geography/stratum. Filter to the requested measure and year before pivoting. Keep long-format measure identities until all requested measures are selected.
- For state health rows, require `stratum_type == "Total"` and `stratum == "Total"` when the task asks for total estimates. Blank demographic labels are not valid age/sex strata and do not support direct demographic standardization.
- For state analyses, separate states/DC from territories. Report territory exclusions separately when requested, and do not let territories affect state rankings, regressions, or counts.
- For county analyses, keep FIPS as zero-padded strings. Filter requested states in prompt order, then count exclusions by reason: invalid FIPS, outside requested states, missing SES, and missing health data. Complete cases are counted after all required joins and filters.
- County socioeconomic data may be Attribute/Value long format. Pivot by exact attribute names only after validating one value per county/attribute. Common derived fields include income change as current median household income minus prior-year median household income, and unemployment change as current minus baseline unemployment.
- Use RUCC as categorical dummy variables when requested; do not treat RUCC as a continuous linear score unless the template explicitly says so.
- For country panels, reconcile name variants through the portal reconciliation/metadata tables and prefer ISO3 joins. Report variant row counts, resolved/unresolved rows, join coverage, and countries with complete-data gaps when requested.

## Modeling Checks

- Standardize continuous predictors and outcomes when reporting standardized betas. Fit the bivariate model first, then the adjusted model specified by the task. Calculate attenuation from unrounded coefficients, normally `100 * (abs(bivariate_beta) - abs(adjusted_beta)) / abs(bivariate_beta)`.
- Use sample weights when the task calls for weighted ranking or weighted regression. For ranking audits, confirm whether higher or lower values indicate worse priority before sorting; preventive screening commonly treats lower values as worse.
- Bucket p-values with strict thresholds: `lt_0_001`, `lt_0_01`, `lt_0_05`, `ge_0_05`, or `not_computed`.
- Compute VIFs on the adjusted predictor matrix excluding the intercept. The collinearity culprit pair is the two predictors with the largest absolute correlation, sorted ascending if the template says so. Use VIF buckets `lt_5`, `5_to_10`, and `ge_10`.
- For regional or group clustering, fit the requested random-intercept or grouped model and report ICC/variance ratios from the model components, not from visual cluster impressions.
- For sensitivity diagnostics, compare the adjusted standardized beta and p-bucket after the specified exclusion or influence check. Use verdicts consistently: sign flip, significance changed, magnitude shift greater than 20%, otherwise stable.
- For static-vs-dynamic county models, the static model uses level SES covariates; the dynamic model adds requested change variables. Lower AIC wins. If multiple outcomes are requested, decide the overall reconciliation label from the pattern across outcomes.
- For mediation, estimate the poverty-to-mediator path and mediator-to-outcome path under the requested covariate set, multiply them for the indirect effect, and classify the bootstrap CI by whether it excludes zero.
- For spatial residual audits, compute residuals from the selected socioeconomic model, join the portal neighbor graph, count isolates, compute Moran's I, and identify positive residual hotspots from residual ordering and reference geography.
- For PCA burden audits, screen for scale anomalies first, retain only allowed variables with acceptable missingness, standardize variables, compute PC1 on complete retained rows, and report loadings in the requested order. Do not flip the PC1 sign unless the task defines a burden orientation rule.

## Output Conventions

- Round only at the final reporting step: standardized betas and model ratios usually to 3 decimals, AIC to 2 decimals, attenuation percentages to 1 decimal, and counts as integers. Follow the template over any default.
- Preserve required ordering:
  - requested states: prompt order;
  - included/excluded states, territories, ISO3 lists: sorted ascending unless stated otherwise;
  - residual outliers, leverage states, priority states, and loadings: requested analytic order;
  - FIPS: 5-character strings with leading zeros;
  - bracket/tercile objects: exact keys such as `Q1`-`Q4` or `T1`-`T3`.
- Use exact measure IDs from the portal. Display labels can help identify measures, but output IDs when the template asks for IDs.
- Use exact enum labels from the template. Do not invent near-synonyms.
- Validate JSON syntax before finishing. No Markdown fences, comments, citations, or explanatory text should appear outside the JSON answer.

## Common Pitfalls

- Mixing territories into state-level models or failing to count an excluded state separately from excluded territories.
- Treating blank demographic fields as valid strata or claiming direct standardization when age/sex strata are absent.
- Dropping leading zeros from county FIPS during CSV import.
- Pivoting county SES rows before checking Attribute/Value uniqueness.
- Joining countries only by display name and missing portal-provided name variants.
- Averaging across measure IDs or years instead of filtering to the requested measure/year.
- Ranking in the wrong priority direction, especially for beneficial measures where lower values are worse.
- Rounding coefficients before ranking, bucketing, AIC comparison, or bootstrap CI classification.
- Reporting model labels from intuition instead of the actual fitted model comparison requested by the template.
