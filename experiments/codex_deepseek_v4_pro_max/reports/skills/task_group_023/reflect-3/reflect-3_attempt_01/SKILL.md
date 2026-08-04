 # Public Health Observatory (PHO) Algorithmic Audit Skill

 ## Purpose
 Solve registered algorithmic audits against the Public Health Observatory read-only data portal. Every task follows a fixed pipeline: read the analysis request and answer template, resolve portal data under publication rules, execute all declared statistical modules, apply the controlled decision gates, and return one JSON object conforming to the answer template.

 ## Portal Interaction

 ### Base URL
 The portal root is provided through the environment variable `TASK_ENV_BASE_URL` or an equivalent task-context substitution token.

 ### Data Retrieval
 - Use `GET /download?dataset=<dataset>&format=csv` to download full datasets as CSV.
 - Supported datasets: `states`, `counties`, `countries`, `state_health`, `state_socioeconomic`, `county_health`, `county_socioeconomic`, `country_indicators`, `revisions`.
 - Browse endpoints (`/data/state-health`, etc.) accept filters and pagination (`page`, `page_size`).
 - The `/catalog` endpoint lists available columns, filters, row counts, and measure dictionaries.
 - The `/methodology` endpoint documents publication policies (release lifecycle, suppression rules, RUCC codes, label reconciliation, etc.).
 - Never call any endpoint not listed in the environment access document. Do not call the judge endpoint directly; use the provided local submission command.

 ### Geography Reference Tables
 - `states`: 50 states plus District of Columbia may appear in health/socioeconomic data even if absent from the states reference. Include DC when the scope says "50_STATES_PLUS_DC". Division for DC is "South Atlantic".
 - `counties`: Contains `rucc` (1–9), `region`, `state_abbr`, `county_fips` (leading zeros meaningful).
 - `countries`: Contains `iso3`, `canonical_name`, `portal_label`, `alternate_labels` (semicolon-separated), `region`, `income_group`.

 ## Data Resolution Rules

 ### Release Precedence
 1. Keep only `release_status = "FINAL"` rows. Discard `PROVISIONAL`.
 2. Drop rows whose `quality_flag` is `INVALID_SCALE`, `INVALID`, or `WITHDRAWN`.
 3. When multiple FINAL revisions exist for the same entity key, select the **highest `revision` number**.
 4. If multiple rows share the highest revision, select the **latest `released_at`** timestamp.
 5. Suppressed values (`suppression_flag = 1` or blank `value`) are treated as **unavailable** — never zero-fill or impute from suppressed rows.

 ### Entity Keys
 - **State health**: `(state_abbr, year, measure_id, value_type, source_type)`
 - **State socioeconomic**: `(state_abbr, year)`
 - **County health**: `(county_fips, year, measure_id, value_type)`
 - **County socioeconomic**: `(county_fips, year)`
 - **Country indicators**: `(iso3, year, indicator_id)`

 ### Value Type and Source Filters
 - `AGE_ADJUSTED` values support state comparisons. `CRUDE` values describe observed burden.
 - `DIRECT_SURVEY` is the primary publication series. `COUNTY_ROLLUP` is a parallel estimate — do not silently substitute one for the other.
 - When the analysis request declares `primary_health_filter` or similar strings, parse them: e.g., `"AGE_ADJUSTED_AND_DIRECT_SURVEY_AND_FINAL"` means use only AGE_ADJUSTED, DIRECT_SURVEY, and FINAL rows.

 ### Cohort Construction
 Every task defines one or more cohorts. Build them in order:
 1. **Basic-complete**: All declared core variables present and non-null for the specified year(s).
 2. **Primary/Reference cohort**: Basic-complete in the reference year.
 3. **Balanced panel cohort**: Basic-complete in every analysis year.
 4. **Machine-learning/exogenous cohorts**: Primary-cohort members also complete for additional declared fields.

 Report excluded jurisdiction codes in ascending alphabetical order.

 ## Statistical Module Patterns

 Each audit module declares a `method` string, a `cohort`, and `required_evidence`. Implement the method literally — do not substitute a similar estimator. Key recurring modules:

 ### Fixed-Effects Panel Models
 - **Two-way FE OLS** with delete-one-cluster jackknife: Regress outcome on continuous predictors plus state and year dummies (drop one state and one year as reference). Compute full-sample coefficient, then delete each cluster unit, refit, and report jackknife bias-corrected inference.
 - **Clustered standard errors (CR1)**: For G-cluster data with N observations and K parameters, compute the CR1 covariance as `(G/(G-1)) * ((N-1)/(N-K)) * bread * meat * bread` where `meat` aggregates cluster-level gradient contributions.

 ### Nested Cross-Validation (Ridge / Elastic Net)
 - **Outer loop**: Leave-one-group-out (e.g., leave one census division or one state out).
 - **Inner loop**: Within the training set, leave one group out to select the best hyperparameter from the declared grid by minimizing mean inner RMSE.
 - **Scaling**: Standardize features using training-set statistics only (fit on training, transform test).
 - Report: outer fold sizes, inner RMSE grid per outer fold, selected hyperparameter per outer fold, outer RMSE per fold, and pooled metrics (RMSE, MAE, Q²/R²).

 ### Wild Cluster Bootstrap
 - Implement the declared PRNG (e.g., PCG32, Xorshift32) from the given seed and stream.
 - Generate Webb wild weights or Rademacher weights as specified per cluster unit.
 - For restricted-null bootstrap: resample under the null hypothesis, refit the declared model, compute t-statistics, and count exceedances.
 - Report: observed statistic, bootstrap p-value (exceedance count plus one over replicates plus one), requested quantiles, and all checkpoint values at the declared replicate milestones.

 ### Split/Grouped Conformal Prediction
 - Within each group (e.g., census division or state), split into proper training (≈60%), calibration (≈20%), and test (≈20%).
 - Train the declared model on proper training. Compute absolute residuals on calibration set. Threshold = the `⌈(n_cal + 1) * (1 − α)⌉`-th smallest residual.
 - On test set: prediction interval = prediction ± threshold. Report coverage, mean width, and MAE per group, plus aggregate pooled coverage and width.

 ### Trajectory PCA with K-Means Clustering
 - Build trajectory features: each variable repeated per year in declared order (e.g., `life_expectancy_2020, ..., adult_obesity_2024`).
 - Standardize features, compute covariance PCA, retain the declared number of components.
 - Run deterministic k-means (fixed random state) on the retained PC scores.
 - **Leave-year-out stability**: Omit each year, recompute PCA and clustering on the reduced feature set, and compute Adjusted Rand Index against the full-data clustering.
 - Report: eigenvalues, explained variance ratios, PC loadings and scores, cluster centroids, sizes, labels, and all leave-year-out ARIs.

 ### Source/Year Perturbation Audits
 - **Source perturbation**: Fit the declared model under every possible subset of replacement sources (e.g., direct survey vs. rollup). Compute the coefficient shift between baseline and each replacement scenario. Report Shapley effects, shift magnitudes, and worst-case scenarios.
 - **Year subset perturbation**: For every combination of years of the declared sizes (e.g., 3, 4, 5), fit both primary and parallel models. Report all coefficients, p-values, absolute percent shifts, same-sign fraction, median/max shift, and worst subset.

 ### Difference GMM / Instrumental Variables
 - First-difference or system GMM with declared instruments and lag structures.
 - Report first-stage partial F-statistics, clustered coefficient summaries, stacked indirect effect with cross-equation delta-method inference, and leave-one-unit-out diagnostics.

 ### Mediation Sensitivity
 - Given baseline path coefficients and standard errors, compute the sensitivity surface over the declared grid of `R²_mediator_confounder` × `R²_outcome_confounder` values.
 - Report baseline quantities, equal-strength tipping R², and the complete ordered surface with adjusted coefficients.

 ## Decision Gates

 Every audit concludes with controlled decision rules. Each gate maps one module's output to PASS/FAIL based on declared thresholds. The classification precedence selects the final conclusion from the number of passed gates. Use only the declared `classification_values` or `allowed_values` from the answer template — never invent a conclusion label.

 ## Answer Formatting

 ### Contract
 - Return **one JSON object** with exactly the `required_top_level_keys` listed in the answer template.
 - **No narrative outside the JSON**. No comments, no explanatory text.

 ### Numeric Precision
 - Round every non-integer reported statistic to the declared number of decimal places (typically 4). Encode as a JSON number.
 - Integer fields (counts, seeds, PRNG states, replicate numbers, ranks, fold numbers) use natural JSON integer types.
 - Use JSON `null` only when a requested statistic is mathematically unavailable — never use `NaN` or `Infinity`.

 ### Identifiers and Ordering
 - Uppercase two-letter state codes. Portal division names exactly as returned by the geography reference.
 - ISO3 values are uppercase. Set-like identifier lists are unique and sorted ascending.
 - **Preserve every formal order**: do not sort an aligned result array independently. Array positions must align with their corresponding identifier arrays (e.g., `state_order`, `feature_order`).
 - Every declared list length and nested array shape must match the `array_lengths` or `cardinality_rules` in the answer template.

 ### Enum Values
 - Gate outcomes: exactly `"PASS"` or `"FAIL"`.
 - Classification and advisory values: exactly one of the `allowed_values` declared in the template.

 ## Workflow Summary

 1. Read `analysis_request.json` and `answer_template.json` from the task input.
 2. Download all required datasets from the portal (`/download?dataset=...&format=csv`).
 3. Resolve final releases following the rules above. Build every declared cohort.
 4. Execute each audit module in the declared order, using the specified method, cohort, and parameters.
 5. Apply the robustness gates and classification precedence rules.
 6. Assemble the answer JSON matching every required key, array length, identifier, precision, and ordering constraint.
 7. Submit the answer using only the provided local submission command — never call the judge endpoint directly.
