# Public Health Statistical Data Audit SKILL

## Overview

This skill covers statistical data audits using the Public Health Evidence Portal, a browser-accessible web application with linked CSV downloads for state, county, and country health and socioeconomic data. The portal data is synthetic but mirrors the shape and pitfalls of real public-health evidence sources.

## Data Download Workflow

### Portal Pages and CSV Endpoints

Every analysis page links to downloadable CSV files served from `/data/`. The following pages and their associated endpoints are available:

**State-level:**
- `/pages/state-health.html` → `/data/state_health_long.csv`, `/data/state_life_expectancy.csv`
- `/pages/state-ses.html` → `/data/state_ses_long.csv`
- `/pages/state-regions.html` → `/data/state_regions.csv`

**County-level:**
- `/pages/county-health.html` → `/data/county_health_long.csv`, `/data/county_metadata.csv`
- `/pages/county-ses.html` → `/data/county_ses_long.csv`
- `/pages/county-neighbors.html` → `/data/state_neighbors.csv`

**Country-level:**
- `/pages/country-indicators.html` → `/data/country_health_panel.csv`
- `/pages/country-metadata.html` → `/data/country_metadata.csv`
- `/pages/name-reconciliation.html` → `/data/country_name_variants.csv`

**Reference:**
- `/pages/methodology.html` — documents known data quality cautions, row counts, and anomaly flags.

### Download Pattern

Fetch CSVs directly from the portal using the full URL. Always inspect the corresponding HTML page for caveats, known missing data, anomaly flags, and filtering notes before building models. The methodology page lists intentional data gaps (e.g., "California 2024 Total obesity and Texas 2024 Total life expectancy are intentionally missing") and anomaly descriptions (e.g., "scaled BMI for Namibia 2018-2021, a 10x adult mortality drop for Eswatini, and complete GDP gaps for Japan").

## Statistical Conventions

### Rounding Rules

- **Standardized betas (std_beta):** Round to 3 decimal places.
- **P-values:** Bucket into `lt_0_001`, `lt_0_01`, `lt_0_05`, `ge_0_05`, or `not_computed` (if the statistic cannot be computed). Never report raw p-values in structured output — always use buckets.
- **AIC values:** Round to 2 decimal places.
- **Variance shares and ratios:** Round to 3 decimal places.
- **Coverage and missing rates:** Round to 3 decimal places.
- **Attenuation percentages:** Round to 1 decimal place.
- **VIF values:** Round to 2 decimal places.
- **Tercile means:** Round to 2 decimal places.
- **Moran's I:** Round to 3 decimal places.
- **Bootstrap CI bounds:** Round to 3 decimal places.

### Bucket Rules

| Measure | Buckets |
|---------|---------|
| VIF | `lt_5`, `5_to_10`, `ge_10` |
| Regional ICC / Random-intercept variance ratio | `lt_0_05`, `0_05_to_0_15`, `ge_0_15` (or `low`, `moderate`, `high` for mixed-model random-intercept variance) |
| Moran's I | `lt_0_05`, `0_05_to_0_20`, `ge_0_20` |
| P-value | `lt_0_001`, `lt_0_01`, `lt_0_05`, `ge_0_05`, `not_computed` |

### Correlation and Collinearity

- Report the **culprit pair** — the two predictor IDs with the highest absolute pairwise correlation — sorted ascending by ID.
- Compute VIF from the full design matrix (excluding the intercept). The predictor with the highest VIF is the `max_vif_predictor`.
- Collinearity assessment should use **all predictors** in the adjusted model, not just bivariate pairs.

### Model Attenuation

Compute attenuation as: `(bivariate_beta - adjusted_beta) / bivariate_beta * 100`. A positive value means the exposure coefficient shrank after adding covariates; a negative value means it grew. Report to 1 decimal place.

### Sensitivity Analysis

Re-run the adjusted model after removing the top 3 high-leverage states (by hat-matrix diagonal). Compare the exposure's standardized beta and significance bucket. Classify as:
- `stable` — magnitude change ≤ 20% and significance category unchanged
- `magnitude_shift_gt_20` — magnitude changed > 20% but sign and significance stable
- `significance_changed` — crossed a p-value bucket boundary
- `sign_flip` — coefficient sign reversed

### Income-Proxy Adjusted Rankings

When ranking states after income adjustment, use **sample-size-weighted least squares (WLS)** with the measure's `sample_size` column as weights. The adjusted ranking is based on residuals (observed minus expected given income/poverty). Rank shift = crude rank minus adjusted rank (negative = improved priority after adjustment, positive = worsened).

Ranking direction depends on the measure's polarity:
- For measures where **lower values are worse** (e.g., screening rates, life expectancy): sort ascending so worst states appear first.
- For measures where **higher values are worse** (e.g., mortality rates): sort descending.
- Report `priority_direction` as `lower_value_worse` or `higher_value_worse`.

### Regional ICC

Compute ICC from a one-way ANOVA of model residuals grouped by census division. `ms_between / (ms_between + ms_within)`. Valid census divisions are defined in `state_regions.csv`.

### Spatial Autocorrelation (Moran's I)

1. Compute state-level mean residuals from the outcome model.
2. Build a binary spatial-weight matrix from `state_neighbors.csv`. States flagged as isolates (`isolate_flag = Y`) contribute zero weight and do not participate in the numerator.
3. Compute Moran's I using only the non-isolate subset or the full state set with zero-weighted isolates. The choice of subset vs. full set depends on the task specification for `isolate_state_count`.
4. Bucket the absolute value of Moran's I.

### Bootstrap Confidence Intervals

For mediation indirect effects, use **percentile bootstrap** with 1,000 resamples. Draw county-level observations with replacement, re-estimate both path coefficients, and compute `a × b` for each bootstrap replicate. Report the 2.5th and 97.5th percentiles. Classify as:
- `positive_excludes_zero` — lower CI bound > 0
- `negative_excludes_zero` — upper CI bound < 0
- `includes_zero` — CI straddles zero

## Identifier and List Ordering Rules

### State Abbreviations

- Always use the two-letter postal abbreviation as stored in the `state` column.
- Sort state lists **ascending alphabetically** unless otherwise specified (e.g., "in prompt order" or "in leverage order").
- When a prompt specifies states in a particular order (e.g., "AL, GA, MS, TN, KY, and WV"), preserve that order in the `requested_states` field.

### FIPS Codes

- State FIPS are two-digit strings (e.g., `"01"` for Alabama).
- County FIPS are five-digit strings (e.g., `"01001"`). When a FIPS is used as an array element, always use the five-digit string representation with leading zeros preserved.
- Invalid FIPS (like `00000`) appear in metadata and SES tables but not in health data. They should be excluded with reason `invalid_fips`.

### Predictor and Measure IDs

- Use the exact measure_id as it appears in the CSV (e.g., `OBESITY`, `DIAB_MORT`, `LPA`, `CASTHMA`, `SCREEN`).
- When listing measure IDs in arrays, use the portal's exact identifier.
- For culprit pairs, sort the two predictor IDs ascending.

### Territory Abbreviations

Territories appear as data distractors: `PR` (Puerto Rico), `GU` (Guam), `VI` (U.S. Virgin Islands). They are flagged with `territory_flag = Y` in health data and `state_level_analysis_flag = N` in regions data. Always exclude territories from state-level analyses and report them in `territories_excluded` sorted ascending.

### ISO3 Codes

- Use three-letter ISO3 codes (e.g., `JPN`, `NAM`, `SWZ`) for country identification.
- Sort ISO3 arrays ascending.

## Filtering and Exclusion Habits

### State-Level Analyses

1. **Stratum filter:** For Total-only analyses, keep `stratum_type = "Total"` AND `stratum = "Total"`. Do not mix demographic substrata into state-level models.
2. **Territory exclusion:** Exclude rows where `territory_flag = "Y"` or `state_level_analysis_flag = "N"`.
3. **SES filtering:** In `state_ses_long.csv`, state-level rows have `geo_level = "state"` AND `geo_fips` ending in `"000"`. County-like rows with `geo_level = "county-like distractor"` must be excluded. The `"000"` suffix on `geo_fips` is the definitive state-row marker.
4. **Missing data:** States with intentionally missing health data (documented in the methodology page or the corresponding HTML page notes) must be excluded and listed in `excluded_states`.
5. **Year selection:** Use the most recent year specified (typically 2024 for current estimates, 2022 for some rankings). Check for stale rows from prior years that may remain in the table.

### County-Level Analyses

1. **State scope:** Filter counties to the exact set of requested states using the `state` column.
2. **FIPS validity:** Exclude FIPS codes flagged as invalid in `county_metadata.csv` (check the `metadata_note` column for "invalid").
3. **SES join:** Join county health and county SES on five-digit `fips`. Some counties intentionally lack selected SES attributes (e.g., `Percent_bachelors_or_higher_2019_23`). Counties missing any variable required by the model specification are excluded with reason `missing_ses`.
4. **Complete cases:** Report the number of counties with complete data for all variables in the model specification. The exclusion categories are `invalid_fips`, `outside_requested_states`, `missing_ses`, and `missing_health_data`.
5. **RUCC handling:** `RUCC_2023` is always treated as `categorical_dummies`. Omit the first category (lowest code) as the reference level.
6. **Dynamic variables:** Income change = `MEDHHINC_2023 - Median_Household_Income_2022`. Unemployment change = `Unemployment_rate_2023 - Unemployment_rate_2010`.

### Country-Level Analyses

1. **Anomaly handling:** Before computing PCA or panel statistics, identify and handle known anomalies:
   - Namibia (NAM) `bmi` for 2018–2021 is scaled ~100× too high. Exclude these country-years from the `bmi` variable.
   - Eswatini (SWZ) `adult_mortality` for 2021–2024 is 10× too low. Exclude these country-years from `adult_mortality`.
   - Japan (JPN) has complete `gdp` gaps (all years blank). Exclude Japan from PCA if `gdp` is a retained variable, or list JPN in `complete_gdp_gap_iso3`.
2. **Retained variables for PCA:** The standard variable set excludes `life_expectancy` from the burden-score PCA. Retained variables: `adult_mortality`, `bmi`, `alcohol`, `health_expenditure`, `immunization`, `schooling`, `income_composition`, `gdp`, `population`, `infant_mortality`.
3. **PCA method:** Standardize (z-score) all variables. Compute the correlation matrix. Extract the first principal component via eigendecomposition. PC1 variance share = eigenvalue ÷ number of variables. PC1 defines the burden score.
4. **Missing rates:** Compute over all country-year rows (e.g., 1,090 for 109 countries × 10 years). For anomalous variable-years that are excluded, count them as missing for that variable's rate.
5. **Income-group model check:** Compute the random-intercept variance ratio (between-group variance ÷ total variance of PC1 scores grouped by income group). Bucket as `low` (< 0.1), `moderate` (0.1–0.3), or `high` (> 0.3). A high ratio supports `mixed_model_supported`; otherwise `pooled_ols_sufficient`.
6. **Name reconciliation:** The `country_name_variants.csv` crosswalk maps canonical names to variant names. All 14 variant rows typically resolve to panel ISO3 codes. Report `variant_rows`, `resolved_variant_rows`, and `unresolved_variant_rows`.

## Reconciliation Patterns

### State SES Reconciliation

- State SES rows are identified by `geo_level = "state"` and `geo_fips` ending in `"000"`. The `state` column alone is not sufficient — county-like distractors also have a `state` abbreviation.
- Pivot the long-format SES table to wide format using `attribute` as the column key and `value` as the cell value.
- State SES attributes include: `PCTPOVALL_2023`, `MEDHHINC_2023`, `Unemployment_rate_2023`, `Percent_bachelors_or_higher_2019_23`, `POP_ESTIMATE_2023`, `R_NET_MIG_2023`.

### County SES Reconciliation

- County SES attributes include both static and time-differenced variables: `PCTPOVALL_2023`, `MEDHHINC_2023`, `Median_Household_Income_2022`, `Unemployment_rate_2023`, `Unemployment_rate_2010`, `Percent_bachelors_or_higher_2019_23`, `POP_ESTIMATE_2023`, `CENSUS_2020_POP`, `RUCC_2023`, `Economic_typology_2015`, `R_NET_MIG_2023`, `R_NATURAL_CHG_2023`.
- `Economic_typology_2015` is categorical; `RUCC_2023` is numeric but treated as categorical dummies.
- The `join_note` column in `county_ses_long.csv` flags FIPS with data quality issues. Cross-reference with `county_metadata.csv` for invalid FIPS and old-name records.

### Country Name and Metadata Reconciliation

- Join `country_health_panel.csv` to `country_metadata.csv` on `iso3`. Coverage is typically 100% (109/109).
- The `country_name_variants.csv` crosswalk provides canonical-to-variant name mappings for 14 country pairs. All variants typically resolve.
- Metadata join coverage = `|panel_iso3 ∩ metadata_iso3| / |panel_iso3|`.
- Income groups: `Low income`, `Lower middle income`, `Upper middle income`, `High income`.
- Do not confuse `lending_category` (a distractor) with `income_group` for group-level modeling.

### Spatial Neighbor Reconciliation

- `state_neighbors.csv` provides contiguous-neighbor lists and isolate flags.
- States with `isolate_flag = "Y"` have no contiguous neighbors and are excluded from spatial-weight computations.
- In the synthetic dataset, the set of isolates may differ from real-world expectations. Always use the portal's `state_neighbors.csv` as the source of record.

## Common Pitfalls

### Data Pitfalls

1. **Mixing strata:** Including demographic substrata (Age, Sex, Race/ethnicity, Income quartile) alongside Total rows inflates sample size and introduces pseudo-replication. Always filter to `stratum_type = "Total"` AND `stratum = "Total"` for state-level models.
2. **Territory contamination:** Territory rows (PR, GU, VI) are present in health tables and can distort rankings and regressions. Always check and exclude.
3. **County-like distractors in state SES:** The `state_ses_long.csv` includes rows with `geo_level = "county-like distractor"`. These can be mistaken for state-level data. Always filter to `geo_level = "state"` AND verify the `000` FIPS suffix.
4. **Missing data patterns:** Some state-measure combinations are intentionally missing (e.g., CA 2024 OBESITY). Exclude affected states from both bivariate and adjusted models to maintain consistent sample sizes.
5. **Stale rows:** Older-year rows may persist in multi-year tables. Verify the correct analysis year.
6. **Anomalous values:** Scaled or shifted values (NAM bmi, SWZ adult_mortality) can dominate PCA loadings and distort burden scores. Flag and handle before standardization.
7. **Complete variable gaps:** A country missing all years for a variable (JPN gdp) forces its exclusion from complete-case PCA. List in the anomaly log.

### Modeling Pitfalls

1. **Sample-size weighting:** For state-level rankings, use the `sample_size` column from health data as weights in WLS. Unweighted OLS may give different rankings.
2. **Demographic standardization feasibility:** Direct standardization requires non-blank Age and Sex strata. If these strata have zero rows with data values, report `not_feasible_blank_demographic_strata`.
3. **Income quartile bracket counts:** These come from the health data's `Income quartile` stratum (Q1 lowest through Q4 highest), not from SES poverty/income variables. Count unique states with data in each bracket.
4. **RUCC as categorical:** Never treat RUCC as continuous. Always use dummy coding with the lowest code as reference.
5. **AIC comparison:** When comparing static vs. dynamic specifications, use the same set of complete cases for both models. Differences in sample size will bias AIC.
6. **Moran's I computation:** Must account for isolate states. Use only non-isolate states in the spatial-weight matrix.
7. **Bootstrap resampling:** Resample county-level observations with replacement, not individual variables. Re-estimate both mediation paths on each bootstrap sample.
8. **Region vs. Division:** The portal uses census divisions (9 divisions) for regional ICC and hotspot analysis, not census regions (4 regions). `state_regions.csv` provides the `division` column.

### Reconciliation Pitfalls

1. **Name variants:** Countries may appear under variant names in different sources. Always reconcile through the `country_name_variants.csv` crosswalk before joining.
2. **FIPS leading zeros:** Five-digit FIPS codes must preserve leading zeros (e.g., `"01001"`, not `"1001"`). String-based joins prevent truncation.
3. **State FIPS vs. state abbreviation:** County data uses two-letter state abbreviations, not state FIPS codes. The `state` column in county CSVs is the abbreviation.
4. **DC inclusion:** The District of Columbia (`DC`) is flagged as a valid analysis state (`state_level_analysis_flag = "Y"`). Whether to include or exclude DC depends on the task specification. When excluded, list it in `excluded_states`.

### Output Pitfalls

1. **Enum values:** Use exact enum strings as specified in answer templates. Case and underscore positions matter.
2. **Boolean vs. string:** `state_level_ses_rows_only` takes a JSON boolean (`true`/`false`), not a string.
3. **List ordering:** Adhere precisely to the specified order for each array field (ascending sort, prompt order, statistical order such as "leverage order" or "residual order").
4. **Prose prohibition:** Structured audit results must not contain prose outside the JSON structure.
