# Public Health Evidence Portal — Statistical Audit SOP

## Environment

The portal is served at `GDPEVO_ENV_BASE_URL` (the remote HTTP URL provided in
`environment_access.md`). All pages and CSV downloads are relative to that base.
Never use localhost, 127.0.0.1, or any other base URL.

### Portal pages (HTML documentation with embedded tables)
| Page | Path |
|---|---|
| Home / download index | `/` |
| State Health | `/pages/state-health.html` |
| State SES | `/pages/state-ses.html` |
| State Regions | `/pages/state-regions.html` |
| County Health | `/pages/county-health.html` |
| County SES | `/pages/county-ses.html` |
| County Metadata | included on county-health page |
| County Neighbors | `/pages/county-neighbors.html` |
| Country Indicators | `/pages/country-indicators.html` |
| Country Metadata | `/pages/country-metadata.html` |
| Name Reconciliation | `/pages/name-reconciliation.html` |
| Methodology | `/pages/methodology.html` |

### CSV downloads (direct from `/data/`)
| CSV | Key columns | Rows |
|---|---|---|
| `state_health_long.csv` | year, state_fips, state, state_name, territory_flag, measure_id, measure, category, stratum_type, stratum, sample_size, data_value_type, data_value, low_confidence_limit, high_confidence_limit, source_note | 29161 |
| `state_life_expectancy.csv` | year, state, state_name, territory_flag, stratum_type, stratum, life_expectancy, low_confidence_limit, high_confidence_limit, note | 4859 |
| `state_ses_long.csv` | geo_fips, state, state_name, geo_name, geo_level, attribute, attribute_label, value, unit, extraction_note | 972 |
| `state_regions.csv` | state_fips, state, state_name, region, division, state_level_analysis_flag, note | 54 |
| `state_neighbors.csv` | state, state_name, region, division, neighbors (pipe-delimited), neighbor_count, isolate_flag, neighbor_names (pipe-delimited), note | 51 |
| `county_health_long.csv` | year, fips, state, county, measure_id, measure, category, data_value_type, data_value, low_confidence_limit, high_confidence_limit, population | 40108 |
| `county_ses_long.csv` | fips, state, county, attribute, attribute_label, value, unit, join_note | 7536 |
| `county_metadata.csv` | fips, state, state_name, county, rucc_code, economic_typology, census_division, metadata_note | 631 |
| `country_health_panel.csv` | country, iso3, year, life_expectancy, adult_mortality, bmi, alcohol, health_expenditure, immunization, schooling, income_composition, gdp, population, infant_mortality, missingness_note | 1090 |
| `country_metadata.csv` | country, iso3, region, income_group, lending_category, metadata_note | 109 |
| `country_name_variants.csv` | canonical_country, variant_name, iso3, reconciliation_note | 14 |

---

## State-Level Audit Workflow

### 1. Identify the analytic sample

**Measures:** Use `measure_id` column (not `measure` label). Available state health measure IDs:
`OBESITY`, `DIAB_MORT`, `INACTIVE`, `SCREEN`, `VACC_COMP`, `LIFE_EXP`.

**Year selection:** Pick the year specified in the task (typically 2022 or 2024). If the
task says "2024", use only rows with `year == 2024`.

**Stratum filter:** Most audits use Total/Total rows only. Filter:
- `stratum_type == "Total" AND stratum == "Total"`

Do not use stratified rows (Age, Sex, Income quartile, Race/ethnicity) unless the
task explicitly asks for income-bracket or demographic analysis.

**Territory exclusion:** Always check `territory_flag`. Territories are GU (Guam, FIPS 66),
PR (Puerto Rico, FIPS 72), and VI (U.S. Virgin Islands, FIPS 78). Exclude them from
state-level analysis unless the task is specifically about territories.

**Missing-rows check:** The portal explicitly documents:
- California 2024 Total adult obesity is intentionally missing
- Texas 2024 Total life expectancy is intentionally missing

When a state lacks a row for your filtered measure/year/stratum, exclude it from the
model (not zero-fill). List excluded states in the `excluded_states` field sorted
alphabetically.

**Stale rows:** The portal warns about stale 2023 Total rows. When the analysis year is
2024, only use rows with the exact year — do not fall back to 2023 rows.

**Duplicate rows:** One Ohio stratified row is duplicated per the portal documentation.
When joining or pivoting, deduplicate by (state, measure_id, year, stratum_type, stratum).

### 2. State SES join

Use `state_ses_long.csv`. True state rows have `geo_fips` ending in `000` AND
`geo_level == "state"`. County-like distractor rows have `geo_level == "county-like
distractor"` and non-000 FIPS suffixes — always exclude them.

Pivot the Attribute-Value long table to wide format using the `attribute` column as
column names and `value` as cell values. State-level SES attributes include:
- `PCTPOVALL_2023` — Percent in poverty, all ages
- `MEDHHINC_2023` — Median household income, 2023
- `Unemployment_rate_2023` — Unemployment rate, 2023
- `Percent_bachelors_or_higher_2019_23` — Bachelor degree or higher, 2019-23
- `POP_ESTIMATE_2023` — Population estimate, 2023
- `R_NET_MIG_2023` — Net migration rate, 2023

Join to health data on state abbreviation (the `state` column is consistent across
state health and state SES files).

### 3. Regional data

Join `state_regions.csv` on `state` (2-letter abbreviation). The file contains 50 states
+ DC + 3 territories. Filter to rows where `state_level_analysis_flag == "Y"` for models.
Regions: South, West, Northeast, Midwest. Divisions are sub-region groupings.

For neighbor/spatial analysis, use `state_neighbors.csv`. Isolate states have
`isolate_flag == "Y"` and `neighbor_count == 0`. Neighbors are pipe-delimited.

### 4. Confounding / mediation model specification

**Bivariate model:** Regress outcome on exposure alone (standardized beta, p-value).

**Adjusted model:** Add SES covariates to the bivariate specification. For state-level
confounding audits, the standard covariate set typically includes `PCTPOVALL_2023`,
`MEDHHINC_2023`, `Unemployment_rate_2023`, and `Percent_bachelors_or_higher_2019_23`.

**Attenuation percentage:** `((bivariate_beta - adjusted_beta) / bivariate_beta) * 100`,
rounded to 1 decimal place.

**Standardized betas:** Use standard OLS standardized coefficients (scale all variables
to mean 0, variance 1 before regression). Round to 3 decimal places.

**p-value bucketing rules (universal):**
| Condition | Bucket |
|---|---|
| p < 0.001 | `lt_0_001` |
| 0.001 ≤ p < 0.01 | `lt_0_01` |
| 0.01 ≤ p < 0.05 | `lt_0_05` |
| p ≥ 0.05 | `ge_0_05` |
| Not applicable / not computed | `not_computed` |

### 5. Collinearity diagnostics

**VIF:** Compute Variance Inflation Factors on the adjusted model (excluding the
intercept). Report the maximum VIF rounded to 2 decimal places and identify the
predictor with that maximum VIF.

**VIF bucket rules:**
| Condition | Bucket |
|---|---|
| max_vif < 5 | `lt_5` |
| 5 ≤ max_vif < 10 | `5_to_10` |
| max_vif ≥ 10 | `ge_10` |

**Culprit pair:** The two predictor IDs with the highest pairwise correlation (or
the two highest VIFs). Return sorted alphabetically/ascending.

### 6. Regional clustering

Fit a linear mixed model with the same fixed effects as the adjusted model plus a
random intercept for `region`. Compute the intraclass correlation coefficient (ICC):
`ICC = random_intercept_variance / (random_intercept_variance + residual_variance)`.
Round to 3 decimal places.

**ICC bucket rules:**
| Condition | Bucket |
|---|---|
| ICC < 0.05 | `lt_0_05` |
| 0.05 ≤ ICC < 0.15 | `0_05_to_0_15` |
| ICC ≥ 0.15 | `ge_0_15` |

### 7. Sensitivity / influential-states analysis

Identify high-leverage states: compute Cook's distance or leverage values for each
state in the adjusted model. Sort by leverage descending and take the top 3 states.
Report in leverage-descending order.

**Sensitivity re-fit:** Remove the high-leverage states and re-run the adjusted model.
Report the exposure standardized beta (rounded to 3 decimals), p-value bucket, and
a verdict:
- `stable` — sign preserved, significance preserved, beta shift ≤ 20%
- `sign_flip` — exposure coefficient changes sign
- `significance_changed` — p-value crosses a bucket boundary
- `magnitude_shift_gt_20` — beta changes > 20% of original magnitude

**Conclusion labels:**
- `supported_after_adjustment` — exposure remains significant with meaningful effect
- `partly_confounded` — attenuation > some threshold but still significant
- `not_primary_after_adjustment` — exposure loses significance

### 8. Identifier and list ordering rules

- **State abbreviations:** Sort alphabetically in all arrays (`included_states`,
  `excluded_states`, `territories_excluded`, etc.)
- **Territory abbreviations:** Sort alphabetically
- **Predictor/measure IDs:** Sort alphabetically when in arrays (e.g., `culprit_pair`)
- **High-leverage states:** Report in leverage order (highest first), not alphabetical
- **FIPS codes:** Sort in residual-magnitude order unless otherwise specified

---

## Income-Adjusted Ranking Audit Workflow

### Measure & direction

- `SCREEN` (Preventive screening prevalence): `lower_value_worse` — lower screening
  rates mean worse performance, so rank ascending by data_value.
- For measures like `OBESITY`: `higher_value_worse`.
- The `priority_direction` field captures this: rank 1 = worst outcome = most priority.

### Crude ranking

Filter to Total/Total rows for the target year. Rank states by data_value according
to the priority direction (ascending for lower_value_worse, descending for
higher_value_worse).

### Income-proxy adjusted ranking

The state health file contains income quartile strata for each measure:
`stratum_type == "Income quartile"` with values `Q1 lowest`, `Q2`, `Q3`, `Q4 highest`.

Count states in each bracket. Use these to construct income-proxy weights or to
regress out income effects. The standard approach:
1. Compute income-quartile–specific means of the outcome.
2. Fit a weighted regression of outcome on income proxy variables (from SES:
   `MEDHHINC_2023`, `PCTPOVALL_2023`).
3. Use residuals or predicted-minus-actual to construct adjusted ranks.
4. Re-rank and compare to crude.

**Demographic adjustment feasibility:** Check whether demographic strata (Age, Sex,
Race/ethnicity) have non-blank, non-null data values for the target measure. If
demographic strata are present with valid values, report `direct_strata_available`.
If demographic strata rows are blank/null/missing, report
`not_feasible_blank_demographic_strata`.

**Sample-size–weighted rows:** Sum the `sample_size` column across all rows used in
the analysis (Total stratum rows). This is the count of rows weighted by sample_size,
not a sum of sample_size values.

### Rank shift reporting

- `spearman_crude_vs_adjusted`: Spearman rank correlation between crude and adjusted
  rankings, rounded to 3 decimals.
- `top_upward_shift_states`: 5 states whose adjusted rank is most improved (rank
  number decreases the most, i.e., adjusted_rank - crude_rank is most negative).
  Ordered by rank shift descending (most improvement first).
- `top_downward_shift_states`: 5 states whose adjusted rank most worsens (rank
  number increases the most, i.e., adjusted_rank - crude_rank is most positive).
  Ordered by rank shift ascending (most worsening first — most negative shift).
- `priority_review_states`: Top 5 states by adjusted priority (worst adjusted rank
  first).

### Weighted model signs

Regress the measure on income and poverty proxies with sample-size weights.
- `income_coefficient_sign`: `positive`, `negative`, or `near_zero`
- `poverty_coefficient_sign`: `positive`, `negative`, or `near_zero`
- p-value buckets as defined in Section 1.

---

## County-Level Audit Workflow

### Data assembly

County audits use:
1. `county_health_long.csv` — long-format health measures by FIPS and year
2. `county_ses_long.csv` — long-format SES attributes by FIPS
3. `county_metadata.csv` — RUCC codes, economic typology, census division

**County health measure IDs:** `CASTHMA`, `OBESITY`, `DIABETES`, `DEPRESSION`, `CHD`,
`LPA`, `GHLTH`, `CSMOKING`, `SLEEP`, `BINGE`, `MAMMOUSE`, `BPMED`, `CHECKUP`, `DENTAL`,
`COREM`, `COREW`.

**Measure labels (human-readable):**
- `CASTHMA` = "Current asthma among adults"
- `OBESITY` = "Obesity among adults"
- `LPA` = "No leisure-time physical activity"
- `DIABETES` = "Diagnosed diabetes among adults"

### County SES attribute pivot

Pivot `county_ses_long.csv` from long (attribute-value) to wide using the `attribute`
column as feature names and `value` as cell values. Key attributes:
- `PCTPOVALL_2023` — Percent poverty, all ages
- `MEDHHINC_2023` — Median household income, 2023
- `Unemployment_rate_2010` — Unemployment rate, 2010
- `Unemployment_rate_2023` — Unemployment rate, 2023
- `Median_Household_Income_2022` — Median household income, 2022
- `Percent_bachelors_or_higher_2019_23` — Bachelor degree or higher, 2019-23
- `POP_ESTIMATE_2023` — Population estimate, 2023
- `CENSUS_2020_POP` — Census population, 2020
- `R_NET_MIG_2023` — Net migration rate, 2023
- `R_NATURAL_CHG_2023` — Natural change rate, 2023
- `RUCC_2023` — Rural-urban continuum code, 2023
- `Economic_typology_2015` — Economic typology, 2015

### Exclusion cascade

Apply exclusions in this order and count each reason:
1. **`outside_requested_states`:** County rows whose `state` is not in the requested
   state abbreviation list.
2. **`invalid_fips`:** FIPS codes that are malformed (not 5-digit strings) or flagged
   in metadata notes as invalid. Check `county_metadata.csv` for invalid-fips notes.
3. **`missing_health_data`:** Counties with null/blank `data_value` for the target
   measure in the analysis year, or counties missing entirely from health data.
4. **`missing_ses`:** Counties missing any required SES attribute after the pivot
   (null values in any of the model covariates).

`complete_case_count` = number of counties remaining after all exclusions.

### Static vs. dynamic specification

**Static model:** Baseline SES covariates only (e.g., `PCTPOVALL_2023`, `MEDHHINC_2023`).

**Dynamic model:** Static covariates PLUS change/delta variables:
- `Unemployment_rate_2023 - Unemployment_rate_2010`
- `MEDHHINC_2023 - Median_Household_Income_2022`

The dynamic variable rule is always:
`unemployment_2023_minus_2010_and_income_2023_minus_2022`.

**RUCC handling:** Always `categorical_dummies`. RUCC is an integer code 1-9; treat
as categorical with dummy encoding (drop first or use k-1 dummies).

**Model comparison:** Use AIC (Akaike Information Criterion), rounded to 2 decimals.
Lower AIC wins. Compare static vs. dynamic for each outcome measure.

**Residual outliers:** After fitting the winning model, compute residuals. Identify
the top 5 counties with the largest positive residuals. Report as 5-digit FIPS strings
in residual-descending order.

**Unemployment change terciles:** Split counties into terciles by the unemployment
change variable (`Unemployment_rate_2023 - Unemployment_rate_2010`). Report T1, T2, T3
means of the outcome variable, rounded to 2 decimals.

### Mediation audit (county level)

For mediation (exposure → mediator → outcome):
1. Regress mediator on exposure + covariates → `exposure_to_mediator_beta`
2. Regress outcome on exposure + mediator + covariates → `mediator_to_outcome_beta`
3. `indirect_effect = exposure_to_mediator_beta * mediator_to_outcome_beta`
4. Bootstrap the indirect effect (e.g., 1000 resamples of counties with replacement).
   Report `bootstrap_ci_low`, `bootstrap_ci_high` (2.5th and 97.5th percentiles),
   rounded to 3 decimals.
5. `bootstrap_ci_enum`:
   - `includes_zero` — CI contains 0
   - `positive_excludes_zero` — both bounds > 0
   - `negative_excludes_zero` — both bounds < 0

All beta coefficients rounded to 3 decimals.

### Spatial residual analysis

After fitting the county model, compute residuals per county. Then:
1. **Moran's I:** Compute on residuals using a spatial weights matrix defined by
   state membership (counties in same state are neighbors). Round to 3 decimals.

   **Moran's I bucket rules:**
   | Condition | Bucket |
   |---|---|
   | \|Moran's I\| < 0.05 | `lt_0_05` |
   | 0.05 ≤ \|Moran's I\| < 0.20 | `0_05_to_0_20` |
   | \|Moran's I\| ≥ 0.20 | `ge_0_20` |

2. **Isolate state count:** Number of requested states whose neighbor count is 0
   (check `state_neighbors.csv` for isolate_flag == "Y"). Isolates have no contiguous
   neighbors.

3. **Top residual hotspot division:** Compute mean residual per census division
   (from `county_metadata.csv`). Report the division with the highest mean positive
   residual.

4. **Top positive residual FIPS:** Top 5 FIPS with largest positive residuals,
   in residual-descending order.

---

## Country-Level Audit Workflow

### Data assembly

Country audits use:
1. `country_health_panel.csv` — 109 countries × 10 years (2015–2024)
2. `country_metadata.csv` — ISO3, region, income_group, lending_category
3. `country_name_variants.csv` — canonical → variant mappings (14 rows)

### Name reconciliation

The health panel uses `country` column names that may match canonical or variant forms
from `country_name_variants.csv`. The variants file is a hint table, not authoritative.

**Join strategy:**
1. Try direct join on `country` = `canonical_country`.
2. For unmatched rows, try `country` = `variant_name`.
3. After variant resolution, all rows should map to a canonical ISO3.

Report:
- `variant_rows`: total rows in the variants crosswalk (always 14).
- `resolved_variant_rows`: how many health-panel country names matched a variant
  and were resolved to a canonical ISO3.
- `unresolved_variant_rows`: variants that could not be matched (should be 0 after
  full reconciliation).
- `metadata_join_coverage`: fraction of health-panel country-year rows that
  successfully join to `country_metadata.csv` via ISO3. Rounded to 3 decimals.

### Variable selection for PCA

The 10 retained variables are always these (in analysis order):
`adult_mortality`, `bmi`, `alcohol`, `health_expenditure`, `immunization`,
`schooling`, `income_composition`, `gdp`, `population`, `infant_mortality`.

**Missingness:** Compute `missing_rate_by_variable` as the fraction of (country × year)
rows where the variable is null/blank, within the complete panel (109 countries × 10
years = 1090 rows). Round to 3 decimals. Note that `schooling` and `gdp` have
inherent missingness; `income_composition` and `population` also have some gaps.

**Complete-case PCA:** Drop any row with any missing value among the 10 retained
variables. Report `rows_used`. Run PCA on the standardized (z-scored) complete-case
matrix. `variable_count` is always 10.

**Year range:** Always `year_start: 2015`, `year_end: 2024`.

**PCA outputs:**
- `pc1_variance_share`: fraction of total variance explained by PC1, rounded to 3 decimals.
- `top_absolute_loadings`: 3 variable IDs with highest absolute loading on PC1,
  ordered by absolute loading descending.
- `top_positive_loadings`: 3 variable IDs with highest positive loading on PC1,
  ordered by loading descending.

### Burden clustering

After PCA, extract PC1 scores. Run k-means clustering with k=3 on the PC1 scores.
Sort cluster centers ascending; label clusters:
- Lowest center → `low_burden`
- Middle center → `middle_burden`
- Highest center → `high_burden`

Report `cluster_counts` with the count of rows in each cluster and
`high_burden_cluster_count` as the count in the high-burden cluster.

### Anomaly detection

**Scale anomalies — adult_mortality:** The portal documents a ~10× drop for Eswatini
(SWZ) in 2021–2024 (from ~200 to ~20). Flag all consecutive years where the anomaly
persists. Report as `{iso3: "SWZ", years: [2021, 2022, 2023, 2024]}`.

**Scale anomalies — BMI:** Namibia (NAM) has scaled BMI values 2018–2021 per the
portal. Report as `{iso3: "NAM", years: [2018, 2019, 2020, 2021]}`.

**Complete GDP gap:** Japan (JPN) has missing GDP across all years in the panel.

These anomalies should be detected programmatically (not hardcoded):
- For Swaziland: adult_mortality drops by > 80% between consecutive year groups,
  flagged when sustained.
- For Namibia: bmi values substantially out of range vs. other countries in same
  region.
- For GDP: identify ISO3 codes with 100% missing GDP.

### Mixed model for income-group structure

Join health panel to metadata on ISO3. Regress the burden score (PC1 score) on
income_group as a fixed effect with a random intercept for country (ISO3).

- `income_group_join_coverage`: fraction of health panel rows with non-null
  income_group, rounded to 3 decimals.
- `random_intercept_variance_ratio`: ratio of random-intercept variance to residual
  variance, rounded to 3 decimals.

**Random intercept variance bucket:**
| Ratio | Bucket |
|---|---|
| < 0.3 | `low` |
| 0.3 to 1.0 | `moderate` |
| > 1.0 | `high` |

- `lr_decision`: `mixed_model_supported` if the random-intercept variance is
  substantial (ratio > 0.5 or so) and income groups show meaningful separation;
  otherwise `pooled_ols_sufficient`.

**`final_readiness`:**
- `ready_with_anomaly_log` — analysis complete with anomalies documented
- `ready_without_flags` — analysis complete, no anomalies to report

---

## Universal Rounding Rules

| Field type | Rounding |
|---|---|
| Standardized betas | 3 decimals |
| p-value buckets | categorical (see bucketing rules) |
| Attenuation percentage | 1 decimal |
| AIC | 2 decimals |
| VIF | 2 decimals |
| ICC | 3 decimals |
| Spearman rho | 3 decimals |
| Bootstrap CI bounds | 3 decimals |
| Indirect effect | 3 decimals |
| Moran's I | 3 decimals |
| Missing rates | 3 decimals |
| Variance shares (PC1) | 3 decimals |
| Join coverage fractions | 3 decimals |
| Tercile means | 2 decimals |
| Variance ratios | 3 decimals |

---

## Common Pitfalls

1. **Territory contamination:** Always check `territory_flag` or `state_level_analysis_flag`
   before state models. PR, GU, VI are distractors.

2. **County-like distractors in state SES:** `geo_fips` ending in non-000 (`01001`,
   `02001`, etc.) with `geo_level == "county-like distractor"` must be excluded from
   state analyses. Use BOTH the 000-suffix rule AND `geo_level == "state"` together.

3. **Stale year rows:** The state health file may contain 2023 Total rows that are
   marked as stale. When the analysis year is 2024, ONLY use year=2024 rows.

4. **Missing Total rows:** Do NOT impute missing Total rows. CA 2024 OBESITY Total
   and TX 2024 LIFE_EXP Total are intentionally absent. Exclude these states from
   analyses requiring that measure/year.

5. **Duplicate rows:** The portal documents one duplicated Ohio stratified row. Always
   deduplicate before pivoting or aggregating.

6. **Country name join failures:** If a country in the health panel doesn't match
   metadata, check `country_name_variants.csv` for canonical ↔ variant mappings
   before excluding it.

7. **Lending category confusion:** `country_metadata.csv` has both `income_group` and
   `lending_category`. Only `income_group` is used for models; `lending_category` is
   a distractor.

8. **Bootstrap vs. theoretical SE:** For mediation indirect effects, use empirical
   bootstrap (resample counties with replacement) not delta-method SE.

9. **Rank direction:** Always confirm the priority direction of each measure before
   ranking. `SCREEN` = lower is worse; `OBESITY` = higher is worse.

10. **Moran's I computation:** Use a spatial weights matrix based on state membership
    (counties in same state are neighbors). Do NOT use geographic distance or contiguity
    between counties — use the `state_neighbors.csv` neighbor definitions and the
    `state` column in county data for membership grouping.
