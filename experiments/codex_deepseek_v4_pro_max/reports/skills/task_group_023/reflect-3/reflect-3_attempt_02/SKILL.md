 # Public Health Observatory Algorithmic Audit Skill
 
 ## Purpose
 
 This skill enables systematic execution of registered multi-module algorithmic audits against the Public Health Observatory (PHO) data portal. It covers data resolution, cohort construction, module execution, and answer formatting for state-level, county-level, and country-level audits.
 
 ## Portal Overview
 
 The Public Health Observatory provides a read-only HTTP data portal at a configurable base URL. All evidence must be drawn exclusively from this portal. No external data sources are permitted.
 
 ### Available Datasets
 
 | Dataset | Endpoint | Coverage | Key Filters |
 |---|---|---|---|
 | States | `/geographies/states` or `/download?dataset=states&format=csv` | 50 states + DC | state_abbr, region, division |
 | Counties | `/geographies/counties` or `/download?dataset=counties&format=csv` | 1,224 counties | county_fips, state_abbr, region, rucc |
 | Countries | `/geographies/countries` or `/download?dataset=countries&format=csv` | 72 countries | iso3, label, region |
 | State Health | `/data/state-health` or `/download?dataset=state_health&format=csv` | 2020-2024 | measure_id, year, value_type, source_type, release_status |
 | State Socioeconomic | `/data/state-socioeconomic` or `/download?dataset=state_socioeconomic&format=csv` | 2020-2024 | year, release_status |
 | County Health | `/data/county-health` or `/download?dataset=county_health&format=csv` | 2021-2024 | measure_id, year, value_type, release_status |
 | County Socioeconomic | `/data/county-socioeconomic` or `/download?dataset=county_socioeconomic&format=csv` | 2020-2024 | year, release_status |
 | Country Indicators | `/data/country-indicators` or `/download?dataset=country_indicators&format=csv` | 2013-2024 | indicator_id, year, release_status |
 | Revisions | `/data/revisions` or `/download?dataset=revisions&format=csv` | 2015-2024 | domain, entity_id, effective_year, status |
 
 ### Data Access Pattern
 
 - Browse: `GET /data/{dataset}?{filters}&page={n}&page_size={m}`
 - Export: `GET /download?dataset={dataset}&format=csv&{filters}`
 - Always prefer CSV export for bulk analysis; use paginated JSON for targeted queries.
 
 ## Data Resolution Protocol
 
 Every audit specifies a release resolution method. The standard protocol is:
 
 ### Step 1: Filter by Release Status
 
 Apply the release status filter specified in the analysis request (typically `FINAL`). Provisional records are excluded unless the protocol explicitly allows fallback.
 
 ### Step 2: Filter by Value Type and Source Type
 
 Health observations come in combinations of:
 - **Value types**: `AGE_ADJUSTED` (preferred for comparability) or `CRUDE`
 - **Source types**: `DIRECT_SURVEY` (preferred) or `COUNTY_ROLLUP` (parallel estimate)
 
 The `analysis_request.json` specifies which combinations to use for each measure via named filters like `AGE_ADJUSTED_AND_DIRECT_SURVEY_AND_FINAL`.
 
 ### Step 3: Resolve Multiple Revisions
 
 When multiple FINAL records exist for the same (entity, year, measure, value_type, source_type) combination, select the record with the **highest revision number**. The release method `REGISTERED_FINAL_RELEASE_RESOLUTION` means: FINAL status only, latest revision wins.
 
 ### Step 4: Exclude Invalid Records
 
 Drop records where:
 - `quality_flag` is in the invalid set (typically `INVALID_SCALE`, `INVALID`, `WITHDRAWN`)
 - `suppression_flag` is 1 (suppressed records)
 - `value` is NULL, empty, or blank
 
 Never zero-fill missing values; they are genuinely unavailable.
 
 ### Step 5: Apply Missing Rule
 
 The standard missing rule is `SUPPRESSED_INVALID_OR_BLANK_VALUES_ARE_UNAVAILABLE_AND_NEVER_ZERO_FILLED`. Missing cells reduce cohort completeness and may exclude entities from balanced panels.
 
 ## Cohort Construction
 
 Audits define multiple cohorts for different modules. Each cohort is a subset of entities meeting specific completeness criteria.
 
 ### Core Balanced Cohort
 
 Entities with non-null values for all core variables in every analysis year. Used for fixed-effects models, jackknife, and trajectory analysis.
 
 ### Broad Reference Cohort
 
 Entities complete for the outcome variable and all ordered features in the reference year (typically the most recent or primary year). Used for cross-sectional prediction and conformal calibration.
 
 ### Strict Dual-Source Cohort
 
 Entities complete for the outcome, primary exposure, parallel exposure, and all adjustment variables in every analysis year. Used for source-year perturbation audits.
 
 ### Machine Learning Cohort
 
 Extended completeness requirements including additional socioeconomic variables. Used for elastic net and ridge models.
 
 ### Balanced Panel Cohort
 
 Entities with no missing cells across all years and all required variables. The most restrictive cohort, used for difference-GMM and two-step estimators.
 
 ## Audit Modules
 
 Each audit runs two or more of the following registered modules. Modules must be executed in the order declared by the analysis request.
 
 ### Module: Delete-Cluster Fixed Effects (Jackknife)
 
 **Purpose**: Assess coefficient stability under leave-one-cluster-out deletion.
 
 **Method**: Fit a two-way fixed-effects OLS model (entity + time dummies), then delete each cluster one at a time and refit. Report:
 - Full-sample coefficient
 - Complete delete-one-cluster coefficient vector
 - Jackknife mean, standard error, t-statistic, and p-value
 - Bias-corrected coefficient
 - Extreme deletion identifiers
 
 **Key requirements**:
 - Cluster variable is typically STATE
 - State and year dummies must be included as fixed effects
 - Standard errors are cluster-robust (CR1)
 - Jackknife uses (n-1)/n variance correction
 - Ordered predictors follow the analysis request's `ordered_predictors` list
 
 ### Module: Nested Ridge / Elastic Net Cross-Validation
 
 **Purpose**: Evaluate predictive performance with regularization under grouped cross-validation.
 
 **Method**: Nested cross-validation where:
 - **Outer loop**: Leave one group out (e.g., census division or state)
 - **Inner loop**: Within training set, leave one group out to select hyperparameters
 
 **Steps**:
 1. Standardize features using training-set moments only
 2. For each outer hold-out group, run inner CV over the lambda/alpha grid
 3. Select the hyperparameter minimizing inner RMSE
 4. Refit on full outer training set with selected hyperparameter
 5. Predict on held-out group, collect residuals
 6. Pool all predictions for aggregate metrics (RMSE, MAE, Q²)
 
 **Key requirements**:
 - Standardization uses training-only means and standard deviations
 - Inner RMSE grid is aligned to the lambda grid order
 - Pooled Q² = 1 - RSS/TSS
 - Report worst-performing outer group
 
 ### Module: Wild Cluster Bootstrap
 
 **Purpose**: Nonparametric inference robust to arbitrary within-cluster correlation.
 
 **Method**: Restricted-null wild cluster bootstrap-t using specified PRNG.
 
 **Steps**:
 1. Fit full model, extract observed coefficient and CR1 standard error
 2. Fit restricted model imposing null hypothesis on target coefficient
 3. Generate Rademacher (±1) weights using the specified PRNG with the audit's seed and stream
 4. For each replicate, construct bootstrap outcome by adding weighted restricted residuals
 5. Refit full model on bootstrap outcome, compute bootstrap t-statistic
 6. Count exceedances of observed |t|, compute bootstrap p-value
 7. Report quantiles of bootstrap t-distribution
 
 **PRNG implementations**:
 - **PCG32**: 64-bit state, RXS-M-XS output function. Use for state-level audits.
 - **Xorshift32**: 32-bit state, standard xorshift. Use for county-level audits.
 
 **Key requirements**:
 - Weights are generated cluster-by-cluster, not observation-by-observation
 - Each replicate uses a fresh weight vector applied to restricted residuals
 - Bootstrap p-value = (exceedance_count + 1) / (replicates + 1)
 - Checkpoint replicates must be reported at specified intervals
 - Weight-index rows show the first few weight vectors with cluster alignment
 
 ### Module: Grouped Split Conformal Prediction
 
 **Purpose**: Distribution-free prediction intervals with group-level calibration.
 
 **Method**: Split each group into proper training (50%), calibration (25%), and test (25%) sets.
 
 **Steps**:
 1. For each group, split data by order-preserving partition
 2. Fit ridge regression on proper training set
 3. Compute absolute residuals on calibration set
 4. Set threshold as (1-α) quantile of calibration residuals (with finite-sample correction)
 5. Apply threshold to test set predictions
 6. Report per-group coverage, mean width, and MAE
 7. Aggregate metrics across all groups
 
 **Key requirements**:
 - Fixed lambda for ridge (no tuning within conformal)
 - Quantile correction: q_level = min((1-α)*(n_cal+1)/n_cal, 1.0)
 - All groups must be represented in output arrays
 - For groups with insufficient sample size, reduce split proportions proportionally
 
 ### Module: Trajectory PCA Clustering
 
 **Purpose**: Identify stable longitudinal patterns using PCA decomposition of trajectory features followed by deterministic k-means clustering.
 
 **Steps**:
 1. Construct wide-format trajectory features (e.g., `{variable}_{year}` for each analysis year)
 2. Standardize features
 3. Run PCA, retain all components, report spectrum and loadings
 4. Initialize k-means with specified states/counties
 5. Run deterministic k-means on first two PC scores
 6. Order clusters by PC1 centroid value
 7. For leave-year-out stability: remove all features containing that year, rerun PCA, rerun k-means, compute Adjusted Rand Index
 
 **Key requirements**:
 - Feature order must match analysis request exactly
 - State/county order must match the fixed-effects module
 - Initialization centroids are the first N entities in state order
 - Leave-year-out ARI measures cluster label stability
 
 ### Module: Source Perturbation
 
 **Purpose**: Test coefficient stability under exhaustive source/variable deletion.
 
 **Variant A: Source-Year Perturbation** (state-level)
 - Enumerate all year subsets of sizes 3, 4, and 5
 - For each subset, fit the FE model and record coefficients
 - Report same-sign fraction and median absolute percent shift
 
 **Variant B: Source-Group Perturbation** (county-level)
 - Delete each source group (sets of related predictors) one at a time
 - Refit model without retuning hyperparameters
 - Report RMSE deterioration per group deletion
 
 ## Decision Framework
 
 Every audit concludes with a structured decision applying ordered gates:
 
 ### Gate Evaluation
 
 Each module produces a PASS/FAIL verdict based on registered thresholds from the analysis request. Typical gates:
 
 | Module | Typical Gate |
 |---|---|
 | Delete-cluster FE | Coefficient direction correct AND jackknife p ≤ 0.05 |
 | Nested Ridge/Elastic Net | Pooled Q² ≥ threshold AND Pooled RMSE ≤ threshold |
 | Wild Bootstrap | Bootstrap p ≤ 0.05 |
 | Grouped Conformal | Aggregate coverage ≥ 0.80 AND mean width ≤ threshold |
 | Trajectory Stability | Minimum leave-year-out ARI ≥ 0.75 AND cumulative variance ≥ threshold |
 | Source Stability | Same-sign fraction ≥ 0.75 AND median shift ≤ 50% |
 
 ### Classification
 
 - **All gates pass**: Primary signal is transportable/robust (highest confidence)
 - **4-5 gates pass**: Signal with limited transportability (further review)
 - **3 or fewer**: No transportable signal (retain baseline)
 
 ### First Failed Module
 
 When not all gates pass, identify the first module (in analysis request order) whose gate failed.
 
 ## Answer Formatting
 
 ### General Rules
 
 - Return exactly one JSON object with no narrative outside it
 - All required top-level keys from the answer template must be present
 - No extra top-level keys beyond those declared
 - Array lengths must match template specifications exactly
 - State codes: uppercase two-letter abbreviations
 - Division names: standard Census division names
 - Country identifiers: uppercase ISO3 codes
 
 ### Numeric Precision
 
 - Computed real-valued fields: 4 decimal places for state tasks, 6 for county tasks
 - Alpha, lambda, l1_ratio, nominal coverage: as specified in the request (typically 4 decimal places)
 - Counts, ranks, fold numbers, seeds, PRNG states: integers
 - Use JSON null for mathematically unavailable statistics (never NaN or Infinity)
 - JSON numbers need not preserve trailing zeros
 
 ### Ordering
 
 - Every list retains the exact order from the analysis request
 - Aligned arrays (e.g., delete coefficients and state order) must be positionally consistent
 - Do not sort results independently; preserve the declared computational order
 
 ### Decision Values
 
 Use only the controlled enum values from the answer template for conclusions, classifications, and gate verdicts (typically PASS/FAIL for gates, and template-specified strings for final classification).
 
 ## Execution Checklist
 
 1. **Read inputs**: Parse `analysis_request.json`, `answer_template.json`, and `prompt.txt` from the task directory
 2. **Resolve data**: Apply the evidence specification filters to portal datasets
 3. **Build cohorts**: Construct each declared cohort and verify counts
 4. **Run modules in order**: Execute each audit module in the declared sequence
 5. **Apply gates**: Evaluate each robustness gate against computed statistics
 6. **Format answer**: Build the JSON object conforming to the answer template
 7. **Validate**: Check all required keys present, array lengths correct, types match
 8. **Submit**: Return exactly the JSON object, no narrative wrapper
 
 ## Supporting Files
 
 This skill may be accompanied by helper scripts for:
 - Portal data fetching and caching
 - PRNG implementations (PCG32, Xorshift32)
 - Webb/Rademacher weight generation
 - Cluster-robust standard error computation (CR1)
 - PCA trajectory construction
