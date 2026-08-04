 # Public Health Observatory Algorithmic Audit Skill
 
 ## Overview
 
 Use this skill when an analyst must complete a registered algorithmic audit against the Public Health Observatory read-only REST portal. The portal publishes state, county, and country health and socioeconomic indicators with formal release records, revision histories, and quality flags. Every audit is defined by a structured analysis request and a fixed JSON answer template; the skill covers evidence resolution, cohort construction, statistical module execution, and controlled decision reporting.
 
 ## When to Apply
 
 - A `prompt.txt`, `analysis_request.json`, and `answer_template.json` are provided together.
 - The task references a read-only Observatory web portal at an environment-supplied base URL.
 - The request asks for publication-grade algorithmic audit evidence with formal numerical, ordering, and reproducibility requirements.
 
 ## Input Contract
 
 Every task instance supplies exactly three files:
 
 - **prompt.txt** – Natural-language briefing describing the business question, geography scope, and any special instructions.
 - **analysis_request.json** – Structured specification containing the request ID, protocol ID, scope, evidence filters, cohort definitions, audit module parameters, reporting rules, and the decision rule.
 - **answer_template.json** – The complete JSON response contract declaring every required top-level key, field types, array lengths, cardinality rules, and allowed enum values.
 
 Read all three files before starting any work. The analysis request is the sole source of truth for parameter values; the answer template is the sole source of truth for output shape.
 
 ## Portal Discovery and Querying
 
 The portal is a read-only REST API. Always begin by discovering available resources.
 
 ### Base Endpoints
 
 | Endpoint | Purpose |
 |---|---|
 | `GET /` | Root discovery; lists available dataset and geography endpoints. |
 | `GET /catalog` | Full catalog of measures, metadata, and available filters. |
 | `GET /geographies/states` | State and DC identifiers and metadata. |
 | `GET /geographies/counties` | County identifiers, state mappings, and RUCC codes. |
 | `GET /geographies/countries` | Country identifiers, ISO3 codes, and region mappings. |
 | `GET /data/state-health` | State-level health measures with value-type, source-type, and release metadata. |
 | `GET /data/state-socioeconomic` | State-level socioeconomic fields. |
 | `GET /data/county-health` | County-level health measures. |
 | `GET /data/county-socioeconomic` | County-level socioeconomic fields. |
 | `GET /data/country-indicators` | Country-level burden, health, and socioeconomic indicators. |
 | `GET /data/revisions` | Revision-event history with status, timestamps, and affected records. |
 | `GET /methodology` | Methodology documentation for measures, value types, and source types. |
 | `GET /download` | CSV export: `?dataset=<dataset>&format=csv` plus supported filters. |
 
 ### Pagination
 
 Dataset list endpoints support `?page=<n>&page_size=<n>`. Always page through complete results rather than truncating.
 
 ### Query Filters
 
 Each `/data/*` endpoint accepts filters as query parameters. Typical filter dimensions include:
 - **measure_id** (or indicator_id for countries)
 - **year** (integer or range)
 - **state_abbr** / **county_fips** / **iso3**
 - **value_type** (e.g., AGE_ADJUSTED, CRUDE)
 - **source_type** (e.g., DIRECT_SURVEY, COUNTY_ROLLUP)
 - **release_status** (e.g., FINAL, PRELIMINARY)
 
 Use the `/catalog` and `/methodology` endpoints to discover the exact filter vocabulary before querying data.
 
 ## Data Resolution Rules
 
 ### Release Resolution
 
 When the analysis request specifies a release method (e.g., REGISTERED_FINAL_RELEASE_RESOLUTION or HIGHEST_FINAL_REVISION_THEN_LATEST_RELEASE):
 
 1. Query `/data/revisions` to identify all revision events for the target measures and years.
 2. Filter revision events by the applicable status values declared in the analysis request (e.g., APPLIED, NON-APPLIED).
 3. For each measure-year-geography tuple, select the record matching the highest-priority revision according to the declared revision priority order (e.g., `["revision", "released_at", "observation_id"]`).
 4. Apply the declared `release_status` filter (e.g., `"FINAL"`) and `value_type`/`source_type` filters.
 
 ### Quality Flags
 
 Records carrying any of the declared invalid quality flags (e.g., `INVALID_SCALE`, `INVALID`, `WITHDRAWN`) must be treated as unavailable. Do not substitute or zero-fill them.
 
 ### Missing Value Rule
 
 Suppressed, invalid, or blank values are **unavailable** and must **never be zero-filled**. Treat them as missing. In the JSON output, use `null` only when a requested statistic is mathematically unavailable; never emit `NaN` or `Infinity`.
 
 ## Cohort Construction
 
 Cohorts are subsets of the resolved data that satisfy declared completeness conditions. Build them in this order:
 
 ### 1. Complete-Case Condition
 
 A geography-year row is complete when every required field is present, nonsuppressed, and non-null. The required fields are listed in the analysis request (typically selected health measures, socioeconomic fields, and any weights or sample sizes).
 
 ### 2. Primary (Reference-Year) Cohort
 
 The set of geographies that satisfy the complete-case condition in the declared reference year. This is the main analysis cohort for most cross-sectional modules.
 
 ### 3. Balanced Panel Cohort
 
 The intersection of geographies that satisfy the complete-case condition in **every** declared analysis year. Used for panel models, trajectory PCA, and any module requiring multi-year completeness.
 
 ### 4. Strict Dual-Source Cohort
 
 When two separate data sources must both resolve for the same geography (e.g., AGE_ADJUSTED+DIRECT_SURVEY and CRUDE+DIRECT_SURVEY), a geography is included only if both sources are complete in every analysis year.
 
 ### 5. Machine-Learning / Augmented Cohort
 
 Primary-cohort members that also have complete values for additional declared features (e.g., unemployment, net_migration, uninsured). Used for models with extended feature sets.
 
 ### Excluded Geographies
 
 Always report which geographies from the declared universe are excluded from each cohort and why (incomplete data, invalid quality flags, missing required fields).
 
 ## Statistical Audit Modules
 
 The analysis request declares which modules to run and their exact parameters. Modules vary across audits but follow canonical method families. Every module must preserve the declared order of features, states, divisions, folds, grids, and any other ordered sequences.
 
 ### Module Family: Delete-Cluster Diagnostics
 
 **Canonical names**: `delete_cluster_fixed_effects`, `cluster_jackknife`, `delete_state_two_step_gmm`
 
 **Core pattern**: Fit a model on the full cohort, then delete one cluster unit at a time, refit, and collect all delete-one coefficients. Compute jackknife bias correction, standard error, t-statistic, and p-value. Report the full coefficient vector, the complete delete-one vector (aligned positionally with the cluster-order list), extreme deletions, and influence summaries.
 
 - For OLS: use standard two-way fixed effects with cluster-robust inference.
 - For GMM: use two-step linear GMM with the declared instrument set and cluster-robust standard errors; report the full Hansen J statistic and delete-state Hansen J values.
 - For weighted models: apply the declared reliability or frequency weight in every fit, including delete-one refits.
 
 ### Module Family: Nested Cross-Validation
 
 **Canonical names**: `nested_ridge_division_cv`, `nested_state_ridge`, `nested_elastic_net`
 
 **Core pattern**: Group geographies by the declared outer grouping (e.g., census division, state). For each outer fold, hold out one group as the test set. Within the remaining training set, run an inner grouped cross-validation over a declared grid of hyperparameters. Select the hyperparameter that minimizes inner CV error. Evaluate on the held-out outer fold. Collect all outer-fold predictions and compute pooled metrics.
 
 - **Standardization**: When declared, standardize continuous features using training-set means and standard deviations only. Do not leak test-set information into standardization.
 - **Grid reporting**: Report the complete inner RMSE grid aligned to the declared lambda (and optionally alpha/l1_ratio) order for every outer fold.
 - **Pooled metrics**: Report pooled RMSE, MAE, and R² (or Q²) computed from all outer-fold predictions stacked together.
 
 ### Module Family: Wild Cluster Bootstrap
 
 **Canonical names**: `wild_cluster_bootstrap`, `wild_cluster_bootstrap_t`
 
 **Core pattern**: Using the declared PRNG (e.g., PCG32 with Webb weights, or XORSHIFT32), generate the declared number of bootstrap replicates under a restricted null. For each replicate, compute the target t-statistic. Report the observed statistic, the complete ordered checkpoint series (replicate number, PRNG state, and t-statistic at each declared checkpoint), tail exceedance counts, the plus-one p-value, and requested quantile values.
 
 - Always report the seed, PRNG family, replicate count, and cluster count.
 - The checkpoint list must match the declared replicate numbers exactly.
 - The plus-one p-value is `(exceedance_count + 1) / (replicate_count + 1)`.
 
 ### Module Family: Grouped Conformal Calibration
 
 **Canonical names**: `grouped_split_conformal`, `state_grouped_conformal`, `grouped_conformal_calibration`
 
 **Core pattern**: Split data into proper-training, calibration, and test folds grouped by the declared grouping variable. Fit the prediction model on proper-training folds. Compute nonconformity scores on calibration folds to determine the threshold (quantile). Evaluate interval coverage and width on test folds. Report per-fold diagnostics, per-group coverage, and pooled aggregate metrics.
 
 - The threshold is the `ceil((n+1)*(1-alpha))/n` quantile of calibration nonconformity scores.
 - Report calibration size, test size, threshold, coverage, and mean width for every fold.
 - When subgroup calibration is required (e.g., RUCC bands, prediction deciles), report coverage statistics for every subgroup.
 
 ### Module Family: Trajectory PCA Clustering
 
 **Canonical names**: `trajectory_pca_clustering`
 
 **Core pattern**: Construct a feature matrix where each row is a geography and each column is a measure-year combination (in declared order). Run PCA using the covariance matrix. Retain the declared number of components. Run deterministic k-means (fixed initialization, Lloyd's algorithm) for the declared cluster count. Assess stability by leave-one-out deletion (of a year or a cluster unit), recomputing PCA and k-means each time, and comparing assignments via Adjusted Rand Index.
 
 - Report the complete eigenvalue spectrum (up to the declared count), explained-variance ratios, loadings, scores, and cluster assignments.
 - Scores and assignments must align positionally with the declared geography order.
 - Report all leave-one-out ARI values and summary statistics (mean, minimum).
 - When the cluster count is a candidate among several, report silhouette scores for every candidate and identify the best-supported count.
 
 ### Module Family: Source/Group Perturbation
 
 **Canonical names**: `source_year_perturbation`, `exhaustive_source_perturbation`, `source_group_perturbation`
 
 **Core pattern**: Systematically replace or remove declared data sources or variable groups and measure the impact on the target coefficient or prediction error.
 
 - **Source perturbation**: For each geography where both baseline and replacement sources resolve, enumerate all 2^M replacement combinations. For each scenario, refit the primary model and record the target coefficient, standard error, and p-value. Classify scenarios as stable or unstable according to the declared stability criterion. Compute exact Shapley values for each geography's marginal contribution to the coefficient change.
 - **Group deletion**: For each declared source group, remove its terms from the model, refit using the same hyperparameters (no re-tuning), and report per-fold RMSE, pooled RMSE, deterioration, worse-fold count, and rank.
 - **Year perturbation**: For each analysis year, substitute the declared source variants exhaustively and record coefficient stability.
 
 ## Answer Generation
 
 ### Format Rules
 
 1. Return **exactly one JSON object** with no narrative, commentary, or explanation outside it.
 2. Every required top-level key from the answer template must be present.
 3. Every sub-key declared in the template must be present; no extra keys.
 4. Array lengths and cardinalities must match template specifications exactly.
 5. Ordering: preserve every declared order — state order, division order, feature order, grid order, fold order, checkpoint order, source-group order. Never sort an aligned result array independently.
 
 ### Numeric Precision
 
 Follow the precision rules declared in the analysis request and answer template. Common conventions:
 
 - **Computed real-valued statistics**: round to the declared number of decimal places (typically 4 or 6).
 - **Literal grid and threshold values**: report at the precision declared in the request (often 4 decimal places).
 - **Counts, ranks, fold numbers, seeds, PRNG states, replicate numbers**: integers.
 - **Booleans**: native JSON true/false.
 - Use JSON `null` only when a statistic is genuinely unavailable (e.g., a division with empty test set produces no coverage); never emit `NaN` or `Infinity`.
 
 ### Identifier Conventions
 
 - U.S. states: uppercase two-letter postal codes.
 - Census divisions: use portal division names exactly as returned.
 - Counties: FIPS codes as returned by the portal.
 - Countries: uppercase ISO3 codes, sorted ascending in set-like lists.
 - Cluster labels: use the exact enum strings declared in the template.
 
 ## Decision Framework
 
 Every audit ends with a controlled decision derived from the module results.
 
 ### Gate Evaluation
 
 The analysis request declares an ordered list of boolean gates. Each gate is a condition on a specific module output — for example, "bias-corrected coefficient > threshold", "OOF R² >= threshold", "bootstrap p-value < threshold", "coverage >= threshold", "minimum ARI >= threshold", "perturbation stability threshold". Evaluate gates in the declared order and record the first gate (if any) that fails.
 
 ### Precedence
 
 The decision rule declares a precedence table mapping gate-pass counts to controlled conclusions. Apply the precedence exactly:
 
 - Count how many gates pass.
 - If all gates pass, emit the first (most favorable) conclusion.
 - If the count falls into an intermediate tier, emit the corresponding conclusion.
 - Otherwise, emit the fallback conclusion.
 
 The conclusion value must be one of the allowed enum strings from the answer template.
 
 ### First-Failed Module
 
 When the template requires a `first_failed_module` field, report the enum value corresponding to the first gate (in declared order) that did not pass, or `"NONE"` if all gates passed.
 
 ## Reproducibility Requirements
 
 1. **Fixed seeds**: Use the exact seed, stream, and PRNG family declared in the analysis request. Never substitute.
 2. **Deterministic algorithms**: When the method specifies deterministic initialization (e.g., deterministic k-means), use it exactly.
 3. **Registered orders**: Preserve every declared order in lists and matrices. Positional alignment between parallel arrays must be exact.
 4. **No data leakage**: Standardization, imputation, and hyperparameter selection must use only training-set statistics within each cross-validation fold.
 5. **Exact filters**: Apply the exact filter values (release_status, value_type, source_type) declared in the request; do not broaden or narrow them.
 
 ## Common Pitfalls
 
 - **Zero-filling missing values**: Never substitute zero for unavailable data. Missing means missing.
 - **Sorting aligned arrays**: If `state_order` defines the row order for a coefficient vector, do not sort states alphabetically in the coefficient output.
 - **Rounding integers**: Counts, seeds, ranks, and fold numbers are integers; do not emit them as floats.
 - **Extra narrative**: The final response is just one JSON object. No preamble, no summary paragraph, no markdown fences around the JSON.
 - **NaN/Infinity**: JSON does not support NaN or Infinity. Use null when a value cannot be computed.
 - **Hyperparameter re-tuning during perturbation**: When the perturbation method specifies "no retune", use the full-model selected hyperparameters for every deletion fit.
