---
name: public-health-portal-audit
description: Reusable workflow for public-health statistical data audits using a browser-accessible evidence portal and linked CSV downloads.
---

## Operating Boundary

Work from the staged attempt directory only. Read `environment_access.md` to obtain `<TASK_ENV_BASE_URL>`, then use only the browser-visible portal pages and linked CSV downloads exposed by that remote site. Do not assume access to portal implementation files or any unstaged local materials.

Always read the task prompt, `payloads/source_request.txt`, and `payloads/answer_template.json` before analysis. Treat the template as the contract: exact keys, exact enum labels, exact rounding, and JSON-only output when requested.

## Evidence Collection

Use the portal pages to identify the relevant CSV downloads and page-level cautions, but use the full CSV files for computations. The visible HTML tables are samples and are not complete enough for audits.

Load CSVs with explicit string types for identifiers:

- State abbreviations and ISO3 codes: uppercase strings.
- State FIPS and county FIPS: strings, preserving leading zeroes.
- County FIPS: exactly five characters in final output.
- Pipe-delimited neighbor lists: split on `|`, treating blanks as no neighbors.

Keep a short reproducible script or notebook in the staged directory when calculations are nontrivial. Prefer `pandas`, `numpy`, `scipy`, `statsmodels`, and `sklearn` if available, and set a random seed for bootstrap or clustering steps.

## Portal Table Conventions

State health data are long format. Key filters usually include `year`, `state`, `territory_flag`, `measure_id`, `stratum_type`, and `stratum`. Use `data_value` for the estimate, not confidence-limit columns, unless the prompt asks otherwise. For crude state analyses, use `stratum_type == "Total"` and `stratum == "Total"`; do not mix age, sex, income, or race strata into a Total analysis.

State SES data are Attribute-Value rows. True state rows require both `geo_level == "state"` and `geo_fips` ending in `000`; county-like records in that file are distractors. Pivot SES rows wide by `state` or `geo_fips` only after filtering to the correct geography.

State region data provide region/division lookups and a `state_level_analysis_flag`. Exclude territory distractors for state-level models. Do not drop DC unless the prompt or template specifically limits the sample to the 50 states.

County health data are long format keyed by `year`, `fips`, `state`, `county`, and `measure_id`. Preserve measure identity by `measure_id`; labels are useful for interpretation but are not stable keys. Some counties intentionally lack selected measures or population values, so build complete-case counts after selecting the requested measure set.

County SES data are Attribute-Value rows keyed by five-digit `fips` and `attribute`. Pivot requested attributes wide only after filtering valid requested states. Join county metadata for `rucc_code`, `economic_typology`, and `census_division`; treat RUCC as categorical dummies when the template says so.

Country health data are country-year panels keyed by `iso3` and `year`. Join metadata by `iso3`, not by country name. Use name-variant rows only as reconciliation hints; they are not a complete authority table. Distinguish `income_group` from `lending_category`.

## Filtering And Reconciliation Rules

Follow the prompt's requested geography and year exactly. For state tasks, exclude `territory_flag == "Y"` and stale years that do not match the analysis year. For county tasks, restrict to the prompt's states before calculating exclusions. For country tasks, use the template's year range and retained-variable candidates.

Report exclusions from the final analytic join, not from raw source row counts. Common exclusion buckets are invalid FIPS, outside requested states, missing SES, and missing health data. Compute each bucket with mutually exclusive rules so counts reconcile to the final complete-case sample.

Do not treat blank demographic labels as valid strata. Direct demographic standardization is feasible only when the required age/sex or other demographic strata are explicitly available and populated for the selected measure and geography. Income quartile rows are proxy strata, not demographic standardization rows.

When comparing crude and adjusted rankings, define priority direction first. If higher values are worse, descending values rank as higher priority; if lower values are worse, ascending values rank as higher priority. Preserve ordered result arrays where the template says "in order"; otherwise sort identifiers ascending.

## Modeling Checks

Use complete cases for every model and record the row count. Standardized coefficients should come from z-scored outcome and predictors, or equivalently `beta * sd(x) / sd(y)`. Round only after all model comparisons are complete.

For bivariate-versus-adjusted claims, fit the bivariate model first, then add socioeconomic controls and requested fixed effects. Compute attenuation from standardized coefficient magnitudes as:

`100 * (abs(bivariate_beta) - abs(adjusted_beta)) / abs(bivariate_beta)`

Use the sign and significance of the adjusted coefficient for the final conclusion, not the crude association alone.

For weighted models, use the task-specified population or sample-size weight, not an unweighted regression. For rank audits, compare crude and adjusted rankings with Spearman correlation and explicit upward/downward rank shifts.

For collinearity checks, calculate VIFs on the final predictor matrix after dummy expansion and complete-case filtering. The culprit pair is the two predictor IDs with the largest absolute correlation; sort that pair ascending unless the template gives another order.

For regional or grouped structure, estimate the requested intraclass or random-intercept quantity from a grouped model when possible. ICC-style summaries use group variance divided by total variance. If a likelihood-ratio or grouped-model decision is requested, compare grouped and pooled specifications on the same complete-case data.

For influence and residual diagnostics, define the ordering before extracting IDs:

- High leverage: sort by leverage descending.
- Positive residual outliers: sort residuals descending.
- Shared outliers across outcomes: rank within each outcome, then combine consistently.
- AIC model winners: lower AIC wins on the same complete-case rows.

For county dynamic specifications, construct change variables exactly from the named attributes, such as current unemployment minus 2010 unemployment or current income minus prior-year income. Keep static SES levels and dynamic changes separate so AIC comparisons are interpretable.

For mediation audits, estimate the poverty-to-mediator path and mediator-to-outcome path on the same complete-case data. The indirect effect is the product of those two coefficients. Bootstrap by resampling rows with a fixed seed, and classify the interval only after sorting bootstrap effects and taking the requested percentiles.

For spatial residual summaries, join residuals back to state, division, and neighbor metadata. Treat isolate states as having no contiguous neighbors. When computing Moran-style statistics, use the same residual vector and neighbor graph used for hotspot summaries, and state clearly whether the action label calls for additional spatial review.

For PCA burden summaries, first log missing rates for all candidate variables. Retain only variables allowed by the template and justified by coverage/anomaly checks. Standardize retained variables before PCA, orient the first component so larger scores match the burden direction implied by adverse indicators, and report loadings by exact variable IDs.

## Rounding, Buckets, And JSON Output

Return exactly one JSON object when the prompt asks for JSON. Do not add prose, comments, Markdown, NaN, Infinity, or trailing commas.

Use template-specified numeric precision:

- Percent attenuation: 1 decimal.
- AIC and tercile means: 2 decimals when requested.
- Standardized betas, ICCs, correlations, variance shares, missing rates, Moran I, and bootstrap limits: 3 decimals when requested.
- VIF: 2 decimals when requested.

Round at the final step. Keep integers as integers. Keep FIPS, state abbreviations, ISO3 codes, measure IDs, enum labels, and variable IDs as strings.

Use p-value buckets exactly:

- `lt_0_001` for `p < 0.001`
- `lt_0_01` for `0.001 <= p < 0.01`
- `lt_0_05` for `0.01 <= p < 0.05`
- `ge_0_05` for `p >= 0.05`
- `not_computed` only when the requested model or test truly cannot be estimated

Use other enum buckets by comparing against the literal thresholds in the template. Boundary values belong in the higher bucket when labels are written as ranges starting at that boundary, such as `0_05_to_0_15`.

## Common Pitfalls

Do not calculate from HTML sample rows. Download the CSVs.

Do not let spreadsheet-style parsing strip leading zeroes from FIPS codes.

Do not mix Total rows with stratified rows unless the task explicitly asks for stratified comparisons.

Do not treat state SES county-like distractors as state records.

Do not join countries by names before applying ISO3 reconciliation.

Do not confuse portal notes with model results. Page cautions identify rows requiring scrutiny; the final structured answer still needs calculations from the downloaded data.

Do not silently drop duplicates or missing values. Deduplicate only after identifying the duplicate key and recording the effect on the analytic sample.

Do not reorder output arrays casually. Sort ascending only for identifier lists described that way; preserve analytic order for leverage, residual, rank, loading, and priority arrays.
