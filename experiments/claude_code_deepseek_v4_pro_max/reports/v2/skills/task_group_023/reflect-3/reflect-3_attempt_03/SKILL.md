# Public Health Evidence Portal — Statistical Audit Skill

Use this skill when solving structured audit tasks against the Public Health
Evidence Portal, a browser-accessible web application serving downloadable CSV
files for state, county, and country health/statistical analysis.

## Data Inventory

Reference data is served from `GET /data/<filename>.csv`. Companion
documentation pages are under `GET /pages/<page>.html`.

### State-Level CSVs

| CSV | Purpose |
|-----|---------|
| `state_health_long.csv` | Long-format health measures with `measure_id`, `stratum_type`, `stratum`, `sample_size`, `data_value`, `territory_flag` |
| `state_life_expectancy.csv` | Life expectancy by state, year, stratum |
| `state_ses_long.csv` | Socioeconomic Attribute-Value table; state rows identified by `geo_level == 'state'` AND `geo_fips` ending in `000` (county-like distractor rows exist) |
| `state_regions.csv` | Census-like region/division lookup; territory rows have `state_level_analysis_flag == 'N'` |

### County-Level CSVs

| CSV | Purpose |
|-----|---------|
| `county_health_long.csv` | Long-format CDC PLACES-style county measures: `fips`, `state`, `measure_id`, `data_value`, `population` |
| `county_ses_long.csv` | County SES Attribute-Value table keyed by 5-digit `fips` and `attribute`; includes `RUCC_2023`, `Unemployment_rate_2010`, `Unemployment_rate_2023`, `MEDHHINC_2023`, `Median_Household_Income_2022`, `PCTPOVALL_2023`, `Percent_bachelors_or_higher_2019_23` |
| `county_metadata.csv` | County metadata: `rucc_code`, `economic_typology`, `census_division`, `metadata_note`; includes FIPS `00000` invalid distractor row |

### Country-Level CSVs

| CSV | Purpose |
|-----|---------|
| `country_health_panel.csv` | 2015-2024 panel: `iso3`, `year`, `life_expectancy`, `adult_mortality`, `bmi`, `alcohol`, `health_expenditure`, `immunization`, `schooling`, `income_composition`, `gdp`, `population`, `infant_mortality`, `missingness_note` |
| `country_metadata.csv` | ISO3, `region`, `income_group`, `lending_category` (lending_category is a distractor - do not confuse with income_group) |
| `country_name_variants.csv` | `canonical_country`, `variant_name`, `iso3`, `reconciliation_note` |

### Other

| CSV | Purpose |
|-----|---------|
| `state_neighbors.csv` | State adjacency lists with `isolate_flag` (AK, HI are isolates) |

## Conventions for Every Task

### State-Level Filtering

1. **Total-only rows.** When the task refers to a state-level rate or prevalence,
   always filter `stratum_type == 'Total'` AND `stratum == 'Total'`. Do not mix
   demographic strata with Total rows.

2. **Territory exclusion.** Exclude rows with `territory_flag == 'Y'` (GU, PR,
   VI). Always report the excluded territories in `territories_excluded` sorted
   ascending by abbreviation.

3. **State-level SES extraction.** Filter `geo_level == 'state'` AND
   `geo_fips` ending in `000`. County-like rows (distractors with names like
   "Alabama sample county 1") exist in the same file and must be excluded.

4. **Known missing values.** California 2024 Total obesity is intentionally
   missing. Exclude CA from analyses requiring that measure and report it in
   `excluded_states`.

5. **DC treatment.** District of Columbia has `territory_flag == 'N'` and
   `state_level_analysis_flag == 'Y'`. It is conventionally included in
   state-level analyses unless the task explicitly restricts to the 50 states.

6. **Included/excluded state ordering.** Arrays of state abbreviations must be
   sorted ascending (e.g., `["AK","AL",...,"WY"]`).

### County-Level Filtering

1. **FIPS validation.** Check that every FIPS code is exactly 5 digits. The
   metadata file contains a `00000` invalid-FIPS distractor; never include it.

2. **Requested states.** Only include counties whose FIPS prefix (first two
   digits) matches the requested state FIPS codes. The typical mapping is:
   AL to 01, GA to 13, KY to 21, MS to 28, NC to 37, TN to 47, WV to 54.

3. **Complete-case handling.** Counties missing any required SES attribute
   (commonly `Percent_bachelors_or_higher_2019_23`) must be counted in
   `exclusions_by_reason.missing_ses`. Exclude them from model fitting.

4. **Dynamic socioeconomic variables.** Compute exactly:
   - `income_change = MEDHHINC_2023 - Median_Household_Income_2022`
   - `unemployment_change = Unemployment_rate_2023 - Unemployment_rate_2010`

   The rule is consistently named `MEDHHINC_2023_minus_Median_Household_Income_2022`
   for income and `unemployment_2023_minus_2010_and_income_2023_minus_2022` for
   the combined pair.

5. **RUCC handling.** Always declare `rucc_handling: "categorical_dummies"`.
   Include RUCC as a factor in models: create k-1 dummy variables for the
   k unique RUCC codes present in the data, omitting the lowest code as the
   reference category.

### Country-Level Conventions

1. **Known anomalies.** Three anomalies must ALWAYS be logged:
   - **Eswatini (SWZ):** adult_mortality drops about 10x in 2021 (from about 209 to about 20).
   - **Namibia (NAM):** BMI values are about 100x scaled for years 2018-2021 (values
     about 2600 instead of about 26).
   - **Japan (JPN):** Complete GDP gaps across all years.

   Report anomalous country-years in structured arrays
   `[{iso3, years:[...]}]`. Set `final_readiness` to
   `ready_with_anomaly_log` whenever any anomaly exists.

2. **Name reconciliation.** The `country_name_variants.csv` table provides a
   canonical-to-variant crosswalk. Every variant row has a known ISO3.
   `resolved_variant_rows` counts variant rows whose ISO3 appears in both the
   panel and metadata; `unresolved_variant_rows` counts rows whose ISO3 is
   missing from either source.

3. **Join coverage.** `metadata_join_coverage` = fraction of panel ISO3 codes
   with a matching metadata row. `income_group_join_coverage` = fraction of
   rows used in PCA that have a non-blank `income_group` in metadata.

### PCA and Burden Scoring

1. **Variable list.** The candidate retained-variable set comes from the panel:
   `adult_mortality`, `bmi`, `alcohol`, `health_expenditure`, `immunization`,
   `schooling`, `income_composition`, `gdp`, `population`, `infant_mortality`.
   Exclude `life_expectancy` from PCA (redundant with `adult_mortality`).

2. **Anomaly exclusion before PCA.** Drop anomalous observations (SWZ 2021
   adult_mortality, NAM 2018-2021 BMI) before computing country-level means.
   The country gets a mean computed from its remaining valid years.

3. **Missing-variable exclusion.** Countries entirely missing a retained
   variable (e.g., Japan for GDP) are excluded from PCA; count them in
   `missing_rate_by_variable` as a fraction of all countries. If GDP is
   retained, PCA uses 108 rows; without GDP it uses 109 rows.

4. **Standardisation.** Center and scale all variables to unit variance before
   PCA. Compute PC1 via power iteration on the correlation matrix.

5. **Burden clusters.** Sort PC1 scores ascending. Split into three equal (or
   nearly equal) groups: `low_burden`, `middle_burden`, `high_burden`.
   `high_burden_cluster_count` is the size of the third (highest-PC1) group.

6. **Top loadings.** `top_absolute_loadings` = three variable ids with largest
   absolute loading on PC1, ordered by absolute loading descending.
   `top_positive_loadings` = three variable ids with largest positive loading,
   ordered by loading descending.

### Regression Diagnostics

1. **Standardized betas.** For state-level bivariate and adjusted regressions,
   report standardized coefficients (betas from z-scored variables), rounded
   to 3 decimal places.

2. **Attenuation.** `attenuation_pct = (|bivariate_std_beta| -
   |adjusted_std_beta|) / |bivariate_std_beta| * 100`, rounded to 1 decimal.

3. **VIF.** Compute from the diagonal of the inverse correlation matrix of all
   predictors (including the exposure). Report `max_vif` rounded to 2 decimals,
   the `max_vif_predictor` string id, and bucket it as `lt_5`, `5_to_10`, or
   `ge_10`.

4. **Culprit pair.** The two predictor ids (among all predictors in the
   adjusted model) with the highest absolute pairwise correlation. Report as
   an array of two strings sorted ascending.

5. **High-leverage states.** Compute leverage (hat values) from the adjusted
   model with all SES predictors. Report the three states with the largest
   leverage, in descending leverage order.

6. **Regional ICC.** Compute from the residuals of the adjusted model grouped
   by census `division` (from `state_regions.csv`). Use the random-effects
   variance decomposition: `ICC = sigma2_between / (sigma2_between + sigma2_within)`.
   Bucket as `lt_0_05`, `0_05_to_0_15`, or `ge_0_15`.

7. **Sensitivity.** Remove the top three high-leverage states, re-fit the
   adjusted model, and report the new standardized beta for the exposure.
   Verdict categories:
   - `stable`: sign unchanged, p stays in same significance bucket, magnitude
     change at most 20%
   - `sign_flip`: sign reverses
   - `significance_changed`: p-value crosses a significance threshold
   - `magnitude_shift_gt_20`: |delta_beta| / |original_beta| > 0.20

### p-Value Bucketing

Always use these exact buckets, tested in order:
1. `lt_0_001` (p < 0.001)
2. `lt_0_01` (p < 0.01)
3. `lt_0_05` (p < 0.05)
4. `ge_0_05` (p at least 0.05)
5. `not_computed` (only when a test was intentionally not run)

### Coefficient Sign Classification

For regression coefficients in weighted or adjusted models:
- `positive`: beta > 0.1
- `negative`: beta < -0.1
- `near_zero`: -0.1 <= beta <= 0.1

### Ranking and Shift Computations

1. **Priority direction.** For preventive/screening measures, higher values are
   better, so `lower_value_worse`. For mortality/risk measures, higher values
   are worse, so `higher_value_worse`.

2. **Income-quartile adjustment.** When the health survey provides income
   quartile strata (Q1 lowest through Q4 highest) with sample sizes, compute
   the sample-size-weighted mean across quartiles for each state as the
   income-adjusted rate. Count available quartile rows in
   `income_proxy_bracket_counts` (keys `Q1`, `Q2`, `Q3`, `Q4`).

3. **Rank shift.** For each state, `shift = crude_rank - adjusted_rank` (where
   rank 1 = best). Positive shift means adjusted rank improved.
   - `top_upward_shift_states`: five states with largest positive shift,
     ordered by shift descending.
   - `top_downward_shift_states`: five states with largest negative shift,
     ordered by shift ascending (most negative first).

4. **Spearman.** Compute Spearman rank correlation between crude and adjusted
   ranks. Use `review_income_adjusted_rank_shifts` when rho < 0.95; otherwise
   `crude_ranking_stable`.

### Static vs. Dynamic Specification

For county-level models comparing static and dynamic SES specifications:

- **Static model:** `outcome ~ PCTPOVALL_2023 + MEDHHINC_2023 +
  Unemployment_rate_2023 + Percent_bachelors_or_higher_2019_23 + RUCC_dummies`

- **Dynamic model:** `outcome ~ PCTPOVALL_2023 + income_change +
  unemployment_change + Percent_bachelors_or_higher_2019_23 + RUCC_dummies`

  where income_change and unemployment_change are the derived variables above.

Compare models by AIC (`n * ln(RSS/n) + 2k`). The winning model is the one
with lower AIC. For a single outcome the `reconciliation_label` matches the
winner. For multiple outcomes, use `dynamic_changes_mixed_by_outcome` when
results differ across outcomes.

### Mediation

For county-level mediation (e.g., poverty to inactivity to obesity):

1. **Path a:** Mediator ~ Exposure + RUCC_dummies + dynamic_vars
2. **Path b:** Outcome ~ Mediator + Exposure + RUCC_dummies + dynamic_vars
3. **Indirect effect** = path_a_coefficient * path_b_coefficient (raw, not
   standardized).
4. **Bootstrap CI:** Resample counties with replacement (n = n_counties) 1000
   times, re-fit both paths, compute indirect effect each time. Report the
   2.5th and 97.5th percentiles rounded to 3 decimals.
5. **CI enum:** `positive_excludes_zero` (CI entirely above 0),
   `negative_excludes_zero` (CI entirely below 0), `includes_zero` (CI
   straddles 0).

### Spatial Diagnostics (County)

1. **Moran's I.** Compute from model residuals grouped by census division
   (from county metadata). Use the ANOVA variance-decomposition approximation:
   `I is about SSB / (SSB + SSW)`. Bucket as `lt_0_05`, `0_05_to_0_20`, or `ge_0_20`.

2. **Top residual hotspot division.** The census division with the highest
   mean residual.

3. **Isolate state count.** Count of states in the analysis that have no
   contiguous neighbors (from `state_neighbors.csv`). AK and HI are the
   canonical isolates, but they are absent from Appalachian/Southeastern
   county analyses, yielding `isolate_state_count: 0`.

4. **Action label.** Use `review_spatial_context` when Moran's I is at least 0.05;
   otherwise `socioeconomic_model_sufficient`.

### Demographic Adjustment Feasibility

When asked whether direct demographic standardization is feasible, check
whether the relevant measure has BOTH `Age` and `Sex` strata in the health
data. If either stratum type is missing or blank:
`not_feasible_blank_demographic_strata`. Only report `direct_strata_available`
when both Age and Sex strata are present with labeled values.

### Unemployment-Change Tercile Means

When reporting tercile means under a model outcome, compute the mean of the
**unemployment change** variable itself within each tercile (not the health
outcome). Sort counties by unemployment_change ascending, split into three
equal groups, and report the mean unemployment_change value for each group
(rounded to 2 decimals). Labels: `T1` (most negative change), `T2`, `T3`
(least negative or positive change).

## Common Pitfalls

1. **Mixing strata.** Always verify `stratum_type` and `stratum` before
   aggregating. A "Total" row and an "Age" row for the same state are NOT
   interchangeable.

2. **Territory pollution.** GU, PR, VI appear in health data with valid values.
   They must be excluded from state-level analyses and reported as
   `territories_excluded`.

3. **SES distractor rows.** The state SES file contains county-like rows with
   `geo_level == 'county-like distractor'`. Filter by `geo_level == 'state'`
   AND `geo_fips` ending in `000`.

4. **Stale rows.** The methodology page warns of stale 2023 Total rows.
   Always use the `year` column to select the analysis year.

5. **Blank demographic strata.** Some measures (notably SCREEN) have 270+
   rows with empty `stratum_type` and `stratum`. These are unusable for direct
   standardization.

6. **Missing education.** About 2-5% of county FIPS codes within the
   Appalachian/Southeast region lack `Percent_bachelors_or_higher_2019_23`.
   These must be excluded from complete-case analyses and counted in
   `missing_ses`.

7. **Anomaly contamination.** Do not include SWZ-2021 adult_mortality or
   NAM-2018-2021 BMI in PCA or model fits. Log them and proceed with the
   remaining data.

8. **Lending category confusion.** Country metadata includes a
   `lending_category` field distinct from `income_group`. Never use lending
   category for income-group stratification.

9. **Included state ordering.** Arrays of state abbreviations must always be
   sorted ascending alphabetically.

10. **Requested state order.** The `requested_states` array must preserve the
    order from the task prompt, NOT alphabetical order.

11. **Round to specified precision exactly.** If the template says "rounded to
    3 decimals," output exactly that precision (e.g., `0.750`, not `0.75`).

12. **Measure IDs from the portal.** Always copy measure IDs exactly as they
    appear in the CSV `measure_id` column (e.g., `OBESITY`, `DIAB_MORT`,
    `SCREEN`, `CASTHMA`, `LPA`). Never invent or abbreviate them.
