---
name: public-health-evidence-audits
description: Use this skill for public-health statistical data audits using a browser-accessible evidence portal with linked CSV downloads, especially state, county, and country health/socioeconomic panels that require strict filtering, joins, model diagnostics, rounded JSON outputs, and audit-safe treatment of stale, distractor, or anomalous records.
---

# Public Health Evidence Audits

## Start Here

1. Work from the staged attempt directory. Read `environment_access.md`, the task prompt, and `input/payloads/answer_template.json`.
2. Use the portal base URL from `environment_access.md` for `<TASK_ENV_BASE_URL>`. Use only browser-visible pages and linked CSV downloads from that portal.
3. Open the relevant portal pages before modeling. Page notes often identify stale rows, missing rows, distractors, invalid geographies, or scale anomalies that affect the audit.
4. Return exactly one JSON object matching the answer template. Do not add prose, comments, markdown fences, or fields not requested.

## Data Loading Rules

- Prefer direct CSV links from the portal pages or home page. If saving intermediate files, save only inside the staged directory.
- Preserve identifier columns as strings: `state`, `state_fips`, `geo_fips`, `fips`, and `iso3`. Never let county FIPS such as `01001` become integers.
- Convert numeric analysis columns with explicit coercion and then inspect missingness before dropping rows.
- Check uniqueness before pivoting long data. If duplicate keys remain after correct filters, investigate them; do not silently average unless the task explicitly asks.
- Treat page sample rows as previews only. Use the full linked CSVs for counts, models, and rankings.

Useful loading pattern:

```python
import pandas as pd

base = "http://..."
df = pd.read_csv(
    f"{base}/data/county_health_long.csv",
    dtype={"fips": "string", "state": "string", "measure_id": "string"}
)
```

## Portal Field Conventions

State health tables are long format. Core fields include `year`, `state_fips`, `state`, `territory_flag`, `measure_id`, `stratum_type`, `stratum`, `sample_size`, and `data_value`. For state-level estimates, filter to the requested year, `territory_flag == "N"`, and usually `stratum_type == "Total"` with `stratum == "Total"`.

State life expectancy may be in a separate CSV with the same state, territory, year, and stratum conventions. Join it only after applying matching year and Total-row filters.

State SES tables are attribute-value records. True state rows require both `geo_level == "state"` and `geo_fips` ending in `000`; county-like rows are distractors. Pivot `attribute` to columns only after this filter.

State region/reference tables include `state_level_analysis_flag`. Use this flag to exclude territory distractors for state-level analyses, and use `region` or `division` only from the reference table.

County health tables are long format with `year`, 5-digit `fips`, `state`, `county`, `measure_id`, `measure`, `data_value`, confidence limits, and `population`. Select requested measures by `measure_id` whenever possible, not by fuzzy label, then pivot to one row per county-year.

County SES tables are attribute-value records keyed by 5-digit `fips`. Pivot attributes such as poverty, income, unemployment, education, population, and RUCC-related fields after filtering to requested states/counties.

County metadata provides `rucc_code`, `economic_typology`, and `census_division`. Join counties by `fips`, not county name. Treat RUCC as categorical dummies unless the prompt explicitly says otherwise.

State neighbor tables contain pipe-delimited state neighbors and isolate flags. Use them only at the geography they support; for county residual summaries, aggregate residuals to the state level before applying state-neighbor Moran or isolate logic unless a county adjacency file is provided.

Country panels are wide country-year tables keyed by `iso3` and `year`. Join metadata on `iso3`. Use name-variant tables only to reconcile names that do not already join by ISO3. Do not confuse `lending_category` with `income_group`.

## Filtering And Sample Accounting

- Determine the analysis year from the prompt or template. Do not mix stale prior-year rows into a current-year audit.
- Apply geography filters before modeling: requested states in prompt order, state-level flags for state tasks, valid 5-digit FIPS for county tasks, and valid ISO3 joins for country tasks.
- Exclude territories unless the task explicitly requests them. Record territory exclusions sorted ascending when the template asks.
- For state health rows, Total rows are not interchangeable with Age, Sex, Income quartile, Race/ethnicity, or blank labels.
- Blank demographic labels are not valid demographic strata. Direct demographic standardization is feasible only when the required Age/Sex strata and weights are actually present.
- Build complete-case samples after all required joins, pivots, outcomes, predictors, and weights are available. Keep exclusion counts reproducible and mutually understandable, commonly in this order: invalid FIPS, outside requested states, missing SES, missing health data.
- Preserve prompt order where requested, such as `requested_states`; sort arrays only when the template says sorted.

## Modeling Rules

Use transparent, reproducible models. Set a fixed random seed for bootstrap, k-means, or other stochastic procedures when the prompt does not specify one.

For standardized betas:

- Fit the model on the final analytic sample.
- Standardize the outcome and numeric predictors within that same sample.
- Include an intercept.
- For categorical covariates such as region, division, RUCC, or typology, use dummy variables with one reference level.

For bivariate and adjusted attenuation:

- Use the same analytic sample for the bivariate and adjusted models unless the task explicitly compares different samples.
- Compute attenuation from final standardized exposure coefficients. A robust default is `100 * (abs(beta_bivariate) - abs(beta_adjusted)) / abs(beta_bivariate)`.
- If the sign flips, report the sign-flip sensitivity/verdict rather than treating the attenuation percent as sufficient.

For p-value buckets:

- `lt_0_001`: p < 0.001
- `lt_0_01`: 0.001 <= p < 0.01
- `lt_0_05`: 0.01 <= p < 0.05
- `ge_0_05`: p >= 0.05
- `not_computed`: only when the model or term genuinely cannot be estimated

For collinearity:

- Calculate VIFs on the adjusted numeric/coded predictor design matrix, excluding the intercept.
- Report the maximum VIF and its predictor.
- If asked for a culprit pair, use the pair of predictors with the largest absolute correlation among candidate predictors and sort the two predictor IDs ascending.

For leverage and residual audits:

- Use hat values from the specified adjusted model for leverage ordering.
- For residual outliers, follow the template wording: "positive residual" means signed residual descending; generic "outlier" usually means absolute residual descending.
- Return FIPS as 5-digit strings and states as two-letter abbreviations.

For weighted ranking or weighted regressions:

- Use `sample_size` for state survey rows when the task indicates survey weighting, and `population` for county rows when population-weighted modeling is requested.
- Drop or flag rows with missing/nonpositive weights before fitting; include them in sample accounting.
- Define priority direction from measure semantics: for disease/risk outcomes, higher is worse; for preventive services/screening, lower coverage is worse unless the prompt says otherwise.

For regional clustering:

- Compute ICC or random-intercept summaries on the requested grouping variable, usually region, division, or income group.
- A practical ICC is between-group variance divided by total variance from a one-way/random-intercept model.
- Use the task's bucket cutpoints when provided; otherwise document and apply consistent thresholds.

For model comparison:

- Compare static vs dynamic specifications on identical complete-case rows.
- Use AIC with lower values winning.
- Dynamic county SES variables commonly mean changes such as current unemployment minus baseline unemployment and current income minus prior income; verify exact attribute names in the CSV.

For mediation:

- Use the same complete-case sample and covariate set for the exposure-to-mediator and mediator-to-outcome models.
- Estimate `a` as exposure -> mediator, `b` as mediator -> outcome adjusted for exposure and covariates, and indirect effect as `a * b`.
- Bootstrap rows with a fixed seed for confidence intervals. Classify the CI by whether it excludes zero and its sign.

For spatial residual checks:

- Use row-standardized adjacency from the available neighbor table.
- Exclude isolate geographies from Moran calculations, but count/report them when requested.
- For hotspot summaries, aggregate the modeled residual quantity to the requested geography or division and rank by mean positive residual unless the prompt specifies another statistic.

For PCA burden summaries:

- Inspect missingness and scale anomalies before PCA. Anomalies are data-quality flags, not automatic exclusions unless the task says to exclude them.
- Retain only candidate variables requested or allowed by the template.
- Standardize retained variables before PCA.
- Orient PC1 consistently so higher scores mean higher burden when reporting burden clusters.
- Label clusters by ordered PC1 means (`low_burden`, `middle_burden`, `high_burden`) after deterministic three-cluster assignment or the task-specified clustering method.

For country grouped models:

- Join income groups from metadata by `iso3`.
- Use `income_group`, not lending category, for grouped/random-intercept checks.
- Compare grouped vs pooled interpretation with a likelihood-ratio or equivalent nested-model check when feasible, and report random-intercept variance ratios from the fitted model.

## Rounding And Enumeration

- Round only final reported values, not intermediate model inputs.
- Match the template precision exactly: common fields use 3 decimals for coefficients/correlations/ICC/PCA shares, 2 decimals for AIC or grouped means, and 1 decimal for percentages.
- Use JSON numbers for numeric outputs, not quoted strings.
- Use exact enum spellings from the answer template.
- For ordered lists, use the requested ordering exactly: sorted ascending, prompt order, leverage order, adjusted priority order, residual order, or loading order.
- For p-values, compute buckets from unrounded p-values.
- For ties, use a deterministic secondary key such as state abbreviation, FIPS, ISO3, or variable ID.

## Final Audit Checklist

- Portal pages read and linked CSVs used as source of record.
- Identifiers preserved with leading zeros.
- Year, geography, stratum, territory, and valid-row filters applied before joins.
- Long tables pivoted only after filters and duplicate checks.
- Complete-case count and exclusions can be reproduced.
- Model formulas, weights, categorical handling, and comparison samples match the prompt.
- All template fields are filled, enums are exact, arrays have the requested length/order, and no extra prose is returned.

## Common Pitfalls

- Mixing Total state rows with stratified rows.
- Treating blank demographic labels as valid Age/Sex strata.
- Including territories or county-like distractors in state analyses.
- Losing county FIPS leading zeros.
- Joining county records by names instead of FIPS.
- Treating RUCC as continuous when the template expects categorical dummies.
- Using page preview rows instead of full CSV downloads.
- Confusing income group with lending category in country metadata.
- Ignoring page-noted scale anomalies or stale rows.
- Rounding before model comparison, ranking, bucketing, or sorting.
