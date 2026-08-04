## Skill: Public-Health-Observatory Algorithmic Transportability Audit

### Activation

Activate when the task involves:
- A prompt mentioning the "Public Health Observatory" publication board or data portal
- An `analysis_request.json` payload with a `protocol_id` field
- An `answer_template.json` specifying the output contract
- A reference to a base URL like `<TASK_ENV_BASE_URL>` or an environment variable `GDPEVO_ENV_BASE_URL`
- Geography scopes of U.S. states/counties or a country cross-section
- Registered algorithmic audit modules such as delete-cluster jackknife, nested ridge/elastic-net CV, wild cluster bootstrap, grouped conformal, PCA trajectory clustering, source perturbation, or GMM panel models

### Core Principle

This skill describes **reusable methods only**. Every task-local value — entity codes, measure names, year ranges, geographic filters, random seeds, hyperparameter grids, decision thresholds, and output vocabulary — must be read from the effective request (`analysis_request.json` or equivalent). Never carry solved numerical results or entity lists across invocations. Recompute all evidence for each new request.

---

## Data Portal Access

The authoritative evidence source is a read-only HTTP portal. Discover its base URL from the prompt (`<TASK_ENV_BASE_URL>`) or from the environment file `environment_access.md` (`GDPEVO_ENV_BASE_URL`). Allowed endpoints:

- `GET /` — portal root
- `GET /catalog` — available datasets
- `GET /geographies/states` — state geography metadata
- `GET /geographies/counties` — county geography metadata
- `GET /geographies/countries` — country geography metadata
- `GET /data/state-health` — state health measures
- `GET /data/state-socioeconomic` — state socioeconomic measures
- `GET /data/county-health` — county health measures
- `GET /data/county-socioeconomic` — county socioeconomic measures
- `GET /data/country-indicators` — country-level indicators
- `GET /data/revisions` — revision history
- `GET /methodology` — methodology documentation
- `GET /download` — CSV export with `?dataset=<dataset>&format=csv` plus supported filters

**Query conventions:**
- Dataset list endpoints (`/data/state-health`, `/data/county-health`, `/data/state-socioeconomic`, `/data/county-socioeconomic`, `/data/country-indicators`) support `page` and `page_size` for pagination
- Filter by `measure_id`, `year`, `value_type`, `source_type`, `release_status`, `state`, `county`, `region`, `census_division`, `country` (ISO3), and other dataset-specific fields as supported by the portal
- CSV download at `/download?dataset=<dataset>&format=csv` accepts the same filters

**Access pattern:** Use `curl` or equivalent HTTP GET with query parameters. No authentication is required. Parse JSON responses. When paginated, walk all pages to collect the full result set.

---

## Publication Resolution

### Single Publication Key

For every requested measure-geography-time tuple, filter the dataset by the effective request fields:
- `measure_id` (health measures) or field name (socioeconomic)
- `value_type` (e.g., AGE_ADJUSTED, CRUDE) — only when specified
- `source_type` (e.g., DIRECT_SURVEY, COUNTY_ROLLUP) — only when specified
- `release_status` (e.g., FINAL) — only when specified
- Geography filters: `state`, `county`, `region`, `census_division`, or `country` as specified
- Year filters as specified

### Revision Priority

When multiple records match the publication key, select exactly one using this ordered priority:
1. **Highest `revision` number** (greatest numeric revision)
2. **Latest `released_at` timestamp** (ties broken by most recent)
3. **Lowest record identifier** (`observation_id`, `record_id`, or equivalent)

This resolves the "greatest revision, then latest release timestamp, then lowest record identifier" rule.

### Missing and Invalid Values

Selected health observations with suppressed, invalid, blank, or null analytic values:
- Remain **publication evidence** (they were selected) but are **analytically incomplete**
- Are **never zero-filled** — treat them as unavailable
- Invalid quality flags to watch for: `INVALID_SCALE`, `INVALID`, `WITHDRAWN`

Count selected publications before analytic completeness exclusions when the request asks for selected release counts.

---

## Cohort Construction

Cohorts are constructed by joining independently resolved publication series on stable entity and time keys. Preserve every declared entity-code then time order, and every declared feature and group order throughout.

### Cohort Types

| Cohort | Rule |
|--------|------|
| **Core balanced** / **Balanced panel** | Entity must be complete (nonsuppressed, nonmissing, valid) for all required fields in every analysis year |
| **Broad reference** / **Primary** | Entity must be complete for outcome and all declared features in the reference/primary year |
| **Dual source** / **Strict** | Complete for outcome, primary exposure, parallel/secondary exposure, and all adjustments in every analysis year |
| **Machine learning** | Primary-cohort members also complete for additional declared fields (e.g., unemployment, net_migration, uninsured) |

Excluded entity codes (those failing the cohort rule) must be reported as an ordered list when required by the template.

---

## Override Resolution System

Protocol profiles may include an override mechanism that allows future requests to customize canonical methods. Apply these rules when the request specifies an override section:

- **Base:** Start from the canonical method profile for the exact protocol version.
- **Direct keys:** A direct root key in the request targets the identically named canonical root key. Inside a named section or module, a child key targets only the identical child path.
- **Override aliases:** A root key named `<section>_overrides` targets canonical `<section>`; `module_overrides.<module_name>` targets that exact top-level module; `reporting_overrides` targets reporting. Strip only the terminal `_overrides` suffix during target resolution.
- **Merge:** Apply resolved entries in request document order. Objects recursively merge by exact key. Arrays replace whole arrays (no concatenation, no positional patch). Explicit scalars, strings, Booleans, and null replace only their exact paths. Absent paths inherit unchanged.
- **Validation:** Reject unknown targets, incompatible types, implicit aliases, key renaming, and type coercion before evidence resolution.
- **Single contract:** Resolve one effective request before any data access, folding, random draw, fit, aggregation, or decision. Use it consistently in every module.

---

## Reusable Statistical Modules

### Module: Publication Resolution and Cohorts

**When activated:** Always the first module.

**Method:**
1. For each requested publication key, filter by effective status, source, value type, validity, and geography bindings
2. Select one record per key using the revision priority rule
3. Count selected publications before analytic completeness exclusions when requested
4. Join resolved series by stable entity and time keys
5. Construct each analytic cohort from its effective required fields
6. Preserve entity-code then time order; preserve every declared feature and group order

**Outputs typically include:** target jurisdictions/geographies, analysis years, resolved observation counts, yearly complete counts, cohort sizes, excluded entity codes, and state/entity census

---

### Module: Delete-Cluster Fixed Effects / Cluster Jackknife

**When activated:** When the request specifies a delete-one-cluster jackknife with OLS/WLS, fixed-effects transformation, or similar leave-one-out influence diagnostic.

**Method:**

1. **Transformation:** On every active refit, transform each modeled variable as:
   - `z_it` minus its active entity mean minus its active time mean plus its active grand mean
   - (Standard two-way fixed-effects within-transformation)
2. **Fit:** Solve OLS without an intercept on the transformed variables in declared predictor order.
3. **Deletion:** Remove the whole cluster. Recompute every mean from the retained data. Refit from scratch in entity-code order.
4. **Jackknife inference:** For G delete estimates `b_-g` and mean `b_bar`:
   - `SE_JK = sqrt((G-1)/G * sum_g((b_-g - b_bar)^2))`
   - `b_BC = G * b_full - (G-1) * b_bar` (bias-corrected)
   - Test `b_BC / SE_JK` with two-sided Student-t and G-1 degrees of freedom
5. **Extrema:** Select minimum and maximum coefficient by value, tied by entity code order.
6. **Percent change:** For each deletion, `100 * abs((b_-g - b_full) / b_full)`.

**For weighted variants:** Apply weights w by setting `Xw = diag(sqrt(w)) * X` and `yw = diag(sqrt(w)) * y`, then proceed with the transformed weighted design. The weight is typically the selected outcome's sample_size.

---

### Module: Nested Ridge / Elastic Net Cross-Validation

**When activated:** When the request specifies nested cross-validation with a penalty grid, outer/inner grouping by cluster or division.

**Method:**

1. **Folds:** Hold out one ordered group per outer fold. Within each outer training set, hold out every remaining group once in the same order as inner folds.

2. **State-blocked fold allocation:** When states are the grouping unit, allocate states by descending retained-entity counts, assigning each to the currently smallest fold. Use lower fold ID on equality. Sort state codes within folds. Repeat allocation inside each outer-training set.

3. **Standardization:** Inside every fit, compute training-only feature means and standard deviations (population SD for ridge, or use ddof=1). Apply those moments to validation/test rows. Center the outcome by its training mean (weighted mean for weighted variants). Do NOT standardize the outcome. Leave indicator/categorical columns unstandardized.

4. **Ridge solver:** Minimize `mean((y - a - Xb)^2) + lambda * sum_j(b_j^2)`.
   - Keep intercept `a` unpenalized
   - Initialize coefficients to zero
   - Cycle in declared feature order: update `b_j = sum_i x_ij * r_ij / (sum_i x_ij^2 + n * lambda)`, where `r` excludes feature j
   - Stop after a full sweep when max coefficient change is below tolerance

5. **Elastic net solver:** Minimize `SSE/(2n) + alpha * (rho * sum|b_j| + 0.5 * (1-rho) * sum b_j^2)`.
   - Cold-start coefficients at zero, intercept at training outcome mean
   - In each cyclic sweep: update intercept by mean residual, then `b_j = soft_threshold(mean(x_j * r_partial), alpha * rho) / (mean(x_j^2) + alpha * (1-rho))` in declared coefficient order
   - Stop at maximum-change tolerance or sweep cap

6. **Hyperparameter selection:** For each outer fold, select by:
   - Smallest unrounded inner RMSE (pooling inner squared errors before RMSE)
   - Break ties toward the smaller penalty (lambda/alpha)
   - For elastic net with alpha grid and l1_ratio grid: traverse grid in declared outer/inner order; select smallest RMSE, then smaller alpha, then smaller l1_ratio

7. **Metrics:** Pool OOF (out-of-fold) predictions to compute pooled RMSE, MAE, and R²/Q². Report every outer fold's aligned inner grids, selected hyperparameters, and held-out RMSE.

---

### Module: Wild Cluster Bootstrap

**When activated:** When the request specifies a wild cluster bootstrap with restricted null, PCG32/XORSHIFT32 PRNG, or similar resampling procedure.

**Method:**

1. **Full model:** Fit the full unpenalized design (OLS or WLS) and compute cluster-robust standard errors (CR1):
   - `V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (X'X)^(-1) * sum_g(s_g * s_g') * (X'X)^(-1)`
   - where `s_g = X_g' * e_g` (cluster scores) for ordered clusters g

2. **Restricted model:** Fit the model with the target coefficient removed. Generate synthetic outcomes:
   - `y_synthetic = X_restricted * b_restricted + wild_weight * e_restricted`

3. **Wild weights:** Use the declared PRNG (PCG32 or XORSHIFT32) seeded with the request's seed and stream. For each replicate, generate weights (e.g., Webb 6-point distribution or Rademacher) per cluster. Apply the same weight to all observations within a cluster.

4. **Bootstrap distribution:** For each replicate, fit the full design on synthetic data, record the test statistic (typically t = b / SE). Repeat for the declared number of replicates.

5. **Inference:**
   - Count replicates where `|t_bootstrap| >= |t_observed|`
   - `p_plus_one = (exceedance_count + 1) / (replicates + 1)`
   - Report requested quantiles of the bootstrap-t distribution
   - Report checkpoint diagnostics at the requested replicate intervals (PRNG state, bootstrap t-statistic)

6. **Checkpoints:** Track PRNG state and bootstrap-t at each requested checkpoint replicate. Report the first few weight-index rows with full cluster alignment.

7. **HC3 variant** (for weighted designs): With `h_i = diag(Xw * (Xw'Xw)^(-1) * Xw')` and `ew_i = sqrt(w_i) * (y_i - X_i * b)`:
   - `V_HC3 = (Xw'Xw)^(-1) * Xw' * diag(ew_i^2 / (1-h_i)^2) * Xw * (Xw'Xw)^(-1)`

---

### Module: Grouped Split Conformal Prediction

**When activated:** When the request specifies grouped split conformal calibration with a fixed lambda, nominal coverage, and group-based folds.

**Method:**

1. **Split:** For each fold, partition the data into proper-training, calibration, and test sets by group assignment.
2. **Model:** Fit the declared model (ridge with fixed lambda, or elastic net with selected hyperparameters) on proper-training data.
3. **Calibration:** Compute nonconformity scores (absolute residuals) on the calibration set. Determine the threshold as the `ceil((n_cal + 1) * (1 - alpha)) / n_cal` quantile of sorted calibration scores.
4. **Prediction intervals:** For each test point, the interval is `[prediction - threshold, prediction + threshold]`.
5. **Metrics per fold:** Coverage (fraction of test points with true value inside interval), mean width, and test MAE.
6. **Aggregation:** Pool all test predictions to compute overall coverage and mean width. Report the worst-performing group/division.

**For cross-fold conformal:** When predictions come from nested-CV outer OOF, each row already has exactly one OOF prediction. Use those as the nonconformity base. For state-grouped, compute per-state coverage. For RUCC-band or decile-based calibration, bin rows accordingly.

**Decision threshold:** When the template requires interval diagnostics, the threshold is applied symmetrically around point predictions.

---

### Module: PCA Trajectory Clustering

**When activated:** When the request specifies PCA decomposition followed by deterministic k-means clustering with leave-one-out stability assessment.

**Method:**

1. **Feature construction:** Build the feature matrix from the declared feature order. Each row is an entity (state or county). Columns follow the declared variable-then-year or block-then-year order.

2. **PCA:** Center the feature matrix (subtract column means). Compute the covariance matrix (or use SVD). Extract eigenvalues, explained variance ratios, and loading vectors for the declared number of components.

3. **K-means initialization:** Use the declared initial centroid entities. Look up their PC scores as the starting centroids. (Deterministic initialization — no random seed.)

4. **K-means iteration:** Assign each entity to the nearest centroid by Euclidean distance on the PC score space. Recompute centroids as cluster means. Repeat until convergence (no assignment changes) or max iterations. Report the iteration count.

5. **Cluster labels:** Assign integer cluster labels 1, 2, 3, ... in the order of the initial centroid entities.

6. **Stability assessment:**
   - **Leave-year-out:** For each year in declared order, remove all feature columns for that year, recompute PCA and k-means from scratch, compute Adjusted Rand Index (ARI) against the full-data clustering, and aligned agreement (fraction of entities whose cluster label is unchanged after optimal Hungarian-algorithm matching).
   - **Delete-entity (state):** For each deletion unit, remove all rows for that entity, recompute PCA and k-means, compute ARI against labels for the retained entities from the full solution.

7. **Aligned agreement for leave-year-out:** After computing cluster labels for the reduced dataset, align labels to the full-data labels via maximum bipartite matching, then compute the fraction of identical assignments.

---

### Module: Source / Year Perturbation

**When activated:** When the request specifies source perturbation, year-subset stability, or exhaustive source replacement with Shapley attribution.

**Method:**

**Year-subset perturbation:** For every combination of analysis years (subsets of 3, 4, or 5 years in declared order), refit the primary model on the subset, record the target coefficient and p-value, and compute the absolute percent shift from the full-period coefficient:
- `abs_percent_shift = 100 * abs((coeff_subset - coeff_full) / coeff_full)`
- Report same-sign fraction, median and maximum absolute percent shift, and the worst-shift subset.

**Source replacement:** When the request specifies replacing the outcome source (e.g., DIRECT_SURVEY → COUNTY_ROLLUP), for every combination of k replaced entities (k=1 to total), refit the primary model. Report:
- Scenario counts per replacement level
- Minimum and maximum coefficient and p-value per level
- Mean absolute percent shift per level
- Maximum-shift bitmask and replaced entity codes
- Whether every scenario is stable (define by request thresholds)

**Shapley attribution:** Compute exact Shapley values by averaging marginal contributions over all possible orderings. For each entity, the Shapley coefficient change is the average change when that entity's outcome source is toggled, averaged over all orderings of other entities. Report the ordered Shapley effects and verify `sum(Shapley) = all_rollup_coefficient - all_direct_coefficient`.

**Source-group deletion:** For each declared source group, remove its terms from the design matrix, keep the full model's selected hyperparameters (no retuning), refit on each outer fold's training data, and compute outer-fold RMSEs, pooled RMSE, deterioration (pooled RMSE minus reference), worse-fold count, and deterioration rank.

---

### Module: Two-Step GMM (Difference/System Panel)

**When activated:** When the request specifies difference GMM, system GMM, or two-step linear GMM for panel data.

**Method:**

1. **Row construction:** Create adjacent-change rows (first-differenced) ordered by entity identifier then end period. Derive lagged levels, dynamic changes, reference indicators, and interactions in declared order.

2. **Residualization:** Within every full or delete-entity fit, residualize outcome, dynamic regressors, and instruments against intercept plus effective baseline terms.

3. **First-step moments:** `g(theta) = Z'(y - D*theta) / n` with identity weight matrix.
   - Build entity-cluster scores: `s_g = Z_g' * u_g` and `S = sum_g(s_g * s_g') / n`

4. **Second-step weight:** Moore-Penrose pseudoinverse of S, with a declared relative singular-value cutoff.

5. **Second-step estimation:** `theta = (X'Z * W * Z'X)^(-1) * X'Z * W * Z'y` where `W = (Z'Z)^(-1)` for first step or the efficient weight for second step.

6. **Hansen J statistic:** `J = n * g(theta)' * W * g(theta)`

7. **Cluster-robust inference:** With cluster scores `q_g = Z_g' * u_g`:
   - `Var(theta) = finite-sample cluster sandwich using the declared degrees-of-freedom correction`
   - For indirect effects `theta = a * b`: `Var(theta) = b^2 * Var(a) + a^2 * Var(b) + 2*a*b * Cov(a,b)`
   - Use Student-t with cluster degrees of freedom

8. **First-stage diagnostics:** Partial F-statistic from full-versus-reduced residual sums of squares using effective instrument counts.

9. **Delete-entity diagnostics:** For each entity deletion, rebuild rows and refit all affected equations from scratch in entity order. Report bias-corrected coefficients and maximum absolute delete-entity shifts.

---

### Module: Mediation Analysis

**When activated:** When the request specifies a mediation design with exposure, mediator, and outcome.

**Method:**

1. **Total-effect model:** `outcome ~ exposure + covariates`
2. **Path-a model:** `mediator ~ exposure + covariates`
3. **Direct/Path-b model:** `outcome ~ exposure + mediator + covariates`
4. **Indirect effect:** `a * b` (product of path-a coefficient and path-b coefficient)
5. Use the unrounded fitted objects as the shared source for downstream bootstrap and sensitivity modules.

**Sensitivity surface:** Given baseline path-a coefficient `a`, path-b coefficient `b`, path-b standard error `SE_b`, and residual degrees of freedom:
- For each `(R2_mediator_confounder, R2_outcome_confounder)` grid cell and bias direction:
  - Compute bias-adjusted coefficients and check whether the indirect effect sign flips
  - The "tipping R2" is the smallest equal-strength R2 where the sign flips

---

### Module: Exhaustive Source Perturbation (with Shapley)

**When activated:** When the request specifies replacing DIRECT_SURVEY with COUNTY_ROLLUP or similar source toggles for exhaustive stability analysis.

**Method:**

1. **Baseline fit:** Fit the primary model using the direct/requested outcome source.
2. **Enumeration:** For each k from 1 to N (where N is the number of entities), enumerate all C(N,k) combinations where k entities use the replacement source.
3. **Refit:** For each combination, refit the model and record the target coefficient and p-value.
4. **Stratified reporting:** Group results by replacement count. Report minimum/maximum coefficient and p-value, and mean absolute percent shift.
5. **Shapley values:** For each entity, compute its Shapley effect as the average marginal coefficient change across all orderings. Report ordered by absolute effect.
6. **Stability:** A scenario is "stable" if the coefficient sign is preserved (or meets the request's stability criterion).

---

## Decision Gates

Every audit concludes with a controlled decision. Apply the declared decision rules from the effective request. Typical patterns:

### Pattern: Boolean Gate Array
Each module produces a pass/fail flag based on declared thresholds. The conclusion is determined by:
- Count of passing gates
- Precedence ordering (first-failed module determines the classification)
- Controlled vocabulary from the request's enumerations

Common gate predicates:
- **Jackknife/FE:** bias-corrected coefficient sign and p-value threshold, maximum delete-cluster percent change threshold
- **Nested CV:** pooled OOF R² threshold, or RMSE threshold, or win-count threshold
- **Bootstrap:** plus-one p-value threshold
- **Conformal:** overall coverage threshold, per-group coverage threshold
- **Trajectory stability:** minimum leave-one-out ARI threshold, mean ARI threshold
- **Source perturbation:** maximum absolute percent shift threshold, stable scenario count

### Pattern: Precedence Enum
Walk the gates in declared precedence order. The first failed gate determines the conclusion string using the pattern `NOT_<CATEGORY>_AT_<FIRST_FAILED_MODULE>`. If all pass, use the declared success string.

---

## Output Formatting

1. **JSON only:** Return exactly one JSON object conforming to the answer template. No narrative outside the JSON.
2. **Numeric precision:** Round noninteger computed values to the declared number of decimal places (typically 4 or 6). Use natural JSON number encoding — do not quote numbers. Counts, ranks, fold numbers, seeds, PRNG states, and replicate numbers are integers.
3. **Array ordering:** Preserve every declared order from the analysis request. Do not sort result arrays independently.
4. **Entity codes:** Use the portal's native entity codes (uppercase two-letter state abbreviations, ISO3 country codes) exactly as returned by the geography endpoints.
5. **Missing values:** Use JSON `null` only when a requested statistic is mathematically unavailable. Never use `NaN` or `Infinity`.
6. **Booleans and enums:** Use JSON `true`/`false` for Boolean fields. Use the exact controlled-vocabulary strings from the template for enum fields.
7. **State/entity order:** When a module declares a state_order, it must match across modules that share the same cohort. Align coefficient vectors positionally with the entity order.
8. **Trailing zeros:** JSON numbers need not preserve trailing zeros — `1.0` and `1` are both acceptable for a numeric field unless the template specifies a particular decimal count.

---

## Workflow Checklist

When executing a PHO algorithmic audit:

1. **Read all inputs:** Parse `prompt.txt`, `analysis_request.json`, and `answer_template.json` from the task directory.
2. **Discover the portal URL:** From `<TASK_ENV_BASE_URL>` in the prompt or `environment_access.md`.
3. **Explore the portal:** GET `/catalog` and relevant geography endpoints to understand available data.
4. **Resolve publications:** Fetch all required data pages; select one record per key using revision priority.
5. **Construct cohorts:** Apply completeness rules from the request; report excluded entities.
6. **Execute modules in order:** Follow the declared module execution order. Each module's output feeds into or is independent of subsequent modules. Preserve all reproducibility checkpoints (seeds, PRNG states, grid orders).
7. **Apply decision gates:** Evaluate each gate against its declared threshold; determine the conclusion.
8. **Format output:** Assemble the JSON object matching the answer template exactly. Verify array lengths, cardinality rules, and precision.
9. **Validate:** Check all required keys are present, array lengths match declarations, entity orders are consistent across modules, and numeric precision is correct.

---

## Protocol Profile Registry

When the answer template includes a `protocol_registry_record` or `portable_protocol_profile` section:

- This section captures the **reusable method semantics** for the protocol version.
- It documents the override resolution rules, module execution order, and per-module methods.
- **Do not copy solved numerical values** into this section — it describes methods, not results.
- The `classification` is always `REUSABLE_METHOD_ONLY`.
- The `instance_boundary` states that entities, measures, time coordinates, sources, random initialization, parameter grids, reporting cutoffs, output names, and business predicates are bound from each future request — never carried across invocations.
- The `activation` rule is an exact case-sensitive match on `protocol_id`.
