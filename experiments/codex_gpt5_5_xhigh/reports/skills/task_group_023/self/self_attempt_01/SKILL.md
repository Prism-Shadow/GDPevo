---
name: public-health-evidence-audits
description: Use for public-health statistical audit tasks that rely on the browser-visible Public Health Evidence Portal and linked CSV downloads, especially state, county, or country panel audits requiring filters, joins, model diagnostics, rankings, PCA, mediation, spatial summaries, rounding, and strict JSON schema outputs.
---

# Public Health Evidence Audits

## Source Discipline

- Work from the staged prompt, `environment_access.md`, the task's `source_request.txt`, the task's `answer_template.json`, portal pages, and CSV downloads linked from the portal.
- Read `GDPEVO_ENV_BASE_URL` from `environment_access.md` and substitute it for `<TASK_ENV_BASE_URL>`.
- Treat the portal and linked CSVs as the source of record. Do not assume implementation-file access, hidden data, evaluator behavior, or stale memo claims are correct.
- Read the relevant portal page notes before modeling; they often identify distractors, known missingness, duplicate rows, stale rows, scale anomalies, or join cautions.
- Use the full CSV downloads for analysis, not just visible HTML sample rows.

## Portal Map

- State health: `state_health_long.csv`, plus `state_life_expectancy.csv` for life expectancy. Health rows are long format by `year`, `state`, `measure_id`, `stratum_type`, and `stratum`; territories and confidence limits are included.
- State SES: `state_ses_long.csv` is Attribute/Value format keyed by `geo_fips`, `state`, `geo_level`, and `attribute`.
- State regions: `state_regions.csv` gives `region`, `division`, and `state_level_analysis_flag`; territory distractors are present.
- County health: `county_health_long.csv` is long format by `year`, 5-digit `fips`, `state`, `measure_id`, and `data_value`.
- County SES: `county_ses_long.csv` is Attribute/Value format by 5-digit `fips` and `attribute`; `county_metadata.csv` provides RUCC, economic typology, census division, invalid-FIPS notes, and old-name records.
- Neighbors: `state_neighbors.csv` stores pipe-delimited `neighbors`, `neighbor_count`, and `isolate_flag`; split neighbor strings on `|`.
- Country panel: `country_health_panel.csv` covers country-years with ISO3 and health/development indicators; `country_metadata.csv` has `region`, `income_group`, and `lending_category`; `country_name_variants.csv` is a hint table for name reconciliation.

## Data Assembly Rules

- Keep identifiers as strings: state abbreviations, ISO3, and especially FIPS. Preserve leading zeros and output county FIPS as 5-character strings.
- Preserve long-format measure identities. Select requested outcomes or mediators by `measure_id` after confirming labels on the page or CSV.
- Pivot SES Attribute/Value files only after filtering to the intended geographic level and checking duplicate keys.
- For state SES, true state rows require both `geo_level == "state"` and `geo_fips` ending in `000`; county-like rows are distractors.
- For state health, use `territory_flag == "N"` and, for state-level crude analyses, `stratum_type == "Total"` and `stratum == "Total"` unless the prompt explicitly asks for strata.
- Do not treat blank demographic labels as valid age, sex, race, or income strata. Blank labels usually mean direct demographic standardization is not supported.
- Exclude territories from state analyses unless the task explicitly asks for them. Report excluded territories or invalid rows only when the template asks.
- For county panels, filter to requested states in the exact prompt order, then count exclusions separately for invalid FIPS, outside requested states, missing SES, and missing health data.
- For country joins, join by `iso3` whenever possible. Use name variants only to reconcile stated country-name mismatches; the variant table is not a complete authority list.
- Do not confuse `income_group` with `lending_category`; lending category is a distractor for grouped health-burden models.

## Modeling SOP

- Build an explicit analytic table before fitting: one row per analysis unit, requested year(s), outcome columns, predictor columns, weights, region/division fields, and all exclusion flags.
- Use complete cases for each model and report the actual model row count requested by the template.
- For standardized coefficients, z-score the modeled outcome and continuous predictors over the model sample, then fit the stated OLS/weighted model. Leave categorical dummies unstandardized unless the task states otherwise.
- Bucket p-values in order: `<0.001`, `<0.01`, `<0.05`, `>=0.05`; use `not_computed` only when the statistic genuinely was not estimable.
- Compute attenuation from the bivariate standardized coefficient to the adjusted standardized coefficient on the same outcome direction. Use absolute magnitude for percent attenuation unless the task clearly expects signed change; separately flag sign flips.
- For VIF diagnostics, compute VIF across the adjusted continuous predictor matrix after dropping constants and one level of each categorical variable. Report the maximum VIF, predictor, and bucket.
- For influential states or counties, use the fitted model's hat values for leverage and residuals for outlier ordering. If the field says positive residuals, sort by residual descending; if it says residual outliers, sort by absolute residual unless the template specifies otherwise.
- For regional clustering, compute ICC or variance ratios from the requested grouping field (`region`, `division`, or `income_group`) on the modeled outcome or residuals as implied by the field name. Keep grouped-model and pooled-model samples identical.
- For static-vs-dynamic county specifications, compare AIC on the same complete-case rows. Treat RUCC as categorical dummies. Common dynamic variables are `Unemployment_rate_2023 - Unemployment_rate_2010` and `MEDHHINC_2023 - Median_Household_Income_2022`.
- For mediation audits, use the product of coefficients for the indirect effect, keep covariates consistent across mediator and outcome models, and bootstrap rows from the complete-case analytic table for confidence intervals.
- For spatial residual audits, build weights from the neighbor file, handle isolate states explicitly, and compute Moran's I on the residual aggregation level implied by the prompt.
- For country PCA burden summaries, audit missingness and scale anomalies first. Standardize retained numeric variables before PCA, orient PC1 so larger scores mean higher burden when burden labels are requested, and assign low/middle/high clusters by ordered PC1 score.

## Rankings And Directions

- Define priority before sorting. If `priority_direction` is `higher_value_worse`, rank larger values as higher priority; if `lower_value_worse`, rank smaller values as higher priority.
- For adjusted rankings, fit the specified income/poverty model using the template's weighting cue, then rank the adjusted priority metric consistently with the crude priority direction.
- Use stable tie-breaking: analytic value first, then state or FIPS alphabetically, unless the template gives another order.
- Follow array-order wording literally: "sorted ascending", "prompt order", "adjusted priority order", "leverage order", "residual order", "absolute loading descending", and similar phrases are output requirements.

## Output Contract

- `answer_template.json` is the schema and enum contract. Return exactly one valid JSON object matching it; no prose, comments, Markdown, NaN, Infinity, or extra keys.
- Use exact enum spellings from the template. Do not invent labels.
- Round only final reported numbers: usually 3 decimals for correlations, ICCs, PCA shares, standardized betas, Moran's I, and CIs; 2 decimals for AIC or tercile means; 1 decimal for attenuation percentages.
- Keep numeric values as JSON numbers, not strings. Keep FIPS, ISO3, state abbreviations, measure IDs, and enum values as strings.
- Counts are integers. Object keys such as `Q1`-`Q4`, `T1`-`T3`, or burden labels must exactly match the template.
- Before finalizing, validate JSON parsing, required `task_id`, enum membership, array lengths, sort order, rounding precision, and that all reported sample counts trace back to the analytic filters.

## Common Pitfalls

- Mixing territories, state rows, and county-like distractor rows.
- Losing leading zeros by reading FIPS as integers.
- Joining SES before filtering to the requested geography.
- Using visible HTML samples instead of full CSV downloads.
- Treating stale prior-year rows as current-year evidence.
- Treating missing demographic labels as real strata.
- Dropping known anomalies silently instead of reporting them when the template has anomaly fields.
- Reporting a model result from a different complete-case sample than the sample count.
- Reversing priority direction in ranking tasks.
- Confusing residual order, leverage order, and alphabetical order.
