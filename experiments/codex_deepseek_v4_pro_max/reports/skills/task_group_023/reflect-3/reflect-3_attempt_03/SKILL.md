# Public Health Observatory Algorithmic Audit Skill

## Overview

This skill provides a reusable methodology for conducting registered algorithmic audits against the Public Health Observatory (PHO) data portal. It covers data access, cohort construction, statistical modeling, and decision-rule evaluation for state, county, and country-level health analyses.

## Portal Interaction

### Data Retrieval

Access all datasets through CSV export for efficient processing:

```
GET /download?dataset=<name>&format=csv
```

**Available datasets**: `states`, `counties`, `countries`, `state_health`, `state_socioeconomic`, `county_health`, `county_socioeconomic`, `country_indicators`, `revisions`

**Key endpoint reference** (`environment_access.md`):
- `GET /catalog` — column schemas, filter parameters, measure dictionary
- `GET /methodology` — publication policies, revision rules, suppression guidance
- `GET /data/<dataset>` — HTML-browsable filtered views

### Methodology Rules (from portal methodology)

1. **Release lifecycle**: FINAL records replace PROVISIONAL; the highest applied FINAL revision governs when several exist.
2. **Value types**: AGE_ADJUSTED for state comparisons; CRUDE for county burden (preserves population structure).
3. **Source types**: DIRECT_SURVEY is primary; COUNTY_ROLLUP is parallel and must not silently replace direct records.
4. **Suppression**: Records with `suppression_flag=1` have no published value. Never treat suppressed/missing as zero.
5. **Quality flags**: Describe review state (REVIEWED, REVISED, SUPPRESSED, etc.) and do not alter release precedence. Only exclude records with quality flags explicitly listed as invalid in the analysis request (typically `INVALID_SCALE`, `INVALID`, `WITHDRAWN`).
6. **Socioeconomic fields**: Revised independently after late responses. Sparse null fields in one record do not invalidate other fields in the same record. Resolve each field independently by scanning to the highest revision that contains a non-empty value for that field.

## Data Resolution Pipeline

### Health Data Resolution

For each `(measure_id, value_type, source_type, state_or_county, year)` combination:

1. Filter to `release_status == "FINAL"` and `year` in analysis years.
2. Exclude records where `quality_flag` is in the invalid set declared in the analysis request.
3. Exclude records where `suppression_flag == "1"` or `value` is empty/null.
4. From remaining candidates, select the record with the **highest `revision` number**. If tied, use the latest `released_at` date.
5. Extract the `value` field.

### Socioeconomic Data Resolution

For each field independently:

1. Filter to `release_status == "FINAL"` and target years.
2. For each `(state_or_county, year)`, scan records in descending `revision` order.
3. Return the first (highest-revision) record where the target field is non-empty and non-null.
4. This per-field approach respects the portal's independent field revision policy.

### Revision History

The `revisions` dataset records audit events. APPLIED corrections are already reflected in later FINAL revisions. PENDING and WITHDRAWN notices do not authorize value replacement. Use revision events for audit trail documentation, not for data resolution.

## Cohort Construction

### Pattern: Core Balanced Cohort

1. Define core variables (outcome, primary exposure, key socioeconomic controls).
2. For each jurisdiction and year, check that all core variables have resolved (non-null) values.
3. A jurisdiction belongs to the core balanced cohort only if it is complete in **every** analysis year.
4. Report counts: yearly complete N, core balanced state/county N, excluded jurisdictions.

### Pattern: Broad Reference-Year Cohort

1. Define the reference year and an ordered list of feature variables.
2. Include all jurisdictions with non-null outcome AND every feature variable in the reference year.
3. Used for cross-sectional ML models (ridge, elastic net) and conformal prediction.

### Pattern: Strict Dual-Source Cohort

1. Requires complete data for outcome, primary exposure, parallel exposure, and adjustments in **all** analysis years.
2. Used for source-stability perturbation analysis.
3. Typically smaller than the core balanced cohort due to the additional parallel-exposure requirement.

### Pattern: Machine Learning Cohort

1. Start from the primary (reference-year) cohort.
2. Additionally require completeness in extended feature variables (e.g., unemployment, net migration, uninsured).
3. Used for high-dimensional ridge/elastic net models.

## Statistical Methods

### Fixed Effects OLS with Cluster-Robust Inference

For panel data with state/county and year fixed effects:

1. **Specification**: Include jurisdiction dummies (N-1 if intercept included, or all N with no intercept) and year dummies (T-1). The within-transformation (demean by jurisdiction) is numerically equivalent.
2. **Cluster-robust standard errors (CR1)**: 
   ```
   V_cr1 = (G/(G-1)) * (X'X)^(-1) * [sum_g X_g' e_g e_g' X_g] * (X'X)^(-1)
   ```
   where G is the number of clusters, X_g and e_g are the design matrix rows and residuals for cluster g.
3. **t-statistic**: coefficient / cluster-robust SE, with G-1 degrees of freedom for p-values.

### Delete-One Jackknife

For coefficient stability assessment:

1. Fit the full model on all clusters.
2. For each cluster, refit the model excluding all observations from that cluster (removing its dummy column).
3. Compute jackknife mean, standard error: `SE_jack = sqrt(((G-1)/G) * sum((theta_i - theta_bar)^2))`.
4. Bias-corrected estimate: `theta_bc = G * theta_full - (G-1) * theta_jack`.
5. Report minimum and maximum delete-one coefficients with corresponding cluster identifiers.

### Nested Cross-Validation (Ridge/Elastic Net)

1. **Outer loop**: Leave-one-group-out (e.g., by census division or state).
2. **Inner loop**: Within the outer training set, perform leave-one-inner-group-out CV over the lambda/alpha grid.
3. **Standardization**: Fit scaler on the training portion only, then transform validation/test.
4. For each outer fold, select the hyperparameter with minimum mean inner RMSE.
5. Report: outer train/test sizes, selected hyperparameters, inner RMSE grid, outer RMSE per fold, pooled metrics (RMSE, MAE, Q²), and worst-performing group.

### Wild Cluster Bootstrap

For inference with few clusters using algorithm-specific RNGs:

1. **Null imposition**: Fit restricted model (coefficient of interest set to zero), compute restricted residuals.
2. **RNG initialization**: Use the declared `seed` and `stream` parameters. For PCG32, stream determines the increment value (`inc = (stream << 1) | 1`). Advance the RNG according to the stream before drawing.
3. **Weight generation**: For Webb 6-point distribution, draw uniform [0,1) and map to weights: `[-√1.5, -1, -√0.5, +√0.5, +1, +√1.5]` with equal probability.
4. **Bootstrap samples**: `y*_g = restricted_pred_g + weight_g * restricted_resid_g` for each cluster g.
5. **Bootstrap t-statistics**: On each bootstrap sample, fit the full model and compute `t* = (beta*_1 - 0) / CR1_SE(beta*_1)`.
6. **p-value**: `(sum(|t*_b| >= |t_obs|) + 1) / (R + 1)`.
7. **Quantiles**: Compute requested quantiles of the bootstrap t-distribution.
8. **Checkpoints**: Record PRNG state and t-statistics at requested replicate intervals.

**PCG32 Implementation**:
```
state = 0; inc = (stream << 1) | 1
state = state * 6364136223846793005 + inc  (mod 2^64)
state = state + seed  (mod 2^64)
// Each iteration:
old = state; state = state * 6364136223846793005 + inc
xorshifted = ((old >> 18) ^ old) >> 27
rot = old >> 59
result = (xorshifted >> rot) | (xorshifted << (-rot & 31))
return result / 2^32
```

**XORSHIFT32 Implementation**:
```
state = seed (non-zero)
// Each iteration:
x = state; x ^= x << 13; x ^= x >> 17; x ^= x << 5
state = x; return x / 2^32
```

### Grouped Split Conformal Prediction

1. **Training**: For each group (e.g., census division), train the model on all observations outside that group. This ensures adequate training data even for small groups.
2. **Calibration/Test split**: Within the group, randomly split observations into calibration and test sets (typically 50/50).
3. **Threshold**: Compute nonconformity scores |y - pred| on calibration set; threshold = (1 - alpha) quantile.
4. **Prediction intervals**: [pred - threshold, pred + threshold], width = 2 * threshold.
5. **Evaluation**: Coverage = fraction of test observations within intervals. Report per-group and aggregate.
6. **Minimum group size**: If a group has fewer than 4 observations, report nulls for that group (mathematically unavailable).

### Trajectory PCA Clustering

1. **Feature construction**: For each jurisdiction, create trajectory features by concatenating values of each variable across all analysis years.
2. **PCA**: Use covariance-based PCA (fit on raw data without standardization unless specified otherwise). Report eigenvalues, explained variance ratios, loadings, and scores.
3. **K-means clustering**: Apply k-means on either the trajectory features or the PCA scores (depending on specification: "THREE_MEANS" implies on PCA scores). Use fixed random_state for determinism.
4. **Leave-year-out stability**: For each year, remove that year's features, re-run PCA + k-means, compute Adjusted Rand Index against full-data labels. Report min/median ARI.

### Source/Year Perturbation

1. Generate all year subsets of declared sizes (e.g., all C(5,3)=10 + C(5,4)=5 + C(5,5)=1 = 16 subsets).
2. For each subset, fit the FE model using primary exposure and parallel exposure separately.
3. Compute coefficient vectors, CR1 p-values, and absolute percent shifts: `|(parallel - primary) / primary| * 100`.
4. Report same-sign fraction, median/max absolute percent shift, and worst subset.

## Decision Rules

### Gate Evaluation

Each module produces a PASS/FAIL gate verdict based on declared thresholds:

| Gate | Typical Condition |
|------|------------------|
| FE/Jackknife | Coefficient in expected direction AND jackknife p ≤ threshold |
| Ridge/Elastic Net CV | Q² ≥ threshold AND RMSE ≤ threshold |
| Wild Bootstrap | Bootstrap p-value ≤ threshold |
| Conformal | Aggregate coverage ≥ 1-α AND mean width ≤ threshold |
| Trajectory PCA | Min leave-year-out ARI ≥ threshold AND cumulative variance ≥ threshold |
| Source Perturbation | Same-sign fraction ≥ threshold AND median absolute shift ≤ threshold |

### Classification

- All gates pass → Highest confidence level
- 4-5 gates pass → Moderate confidence with noted limitations
- ≤3 gates pass → Insufficient evidence

## Answer Submission

### Template Matching

1. Identify all `required_top_level_keys` from the answer template.
2. For each section, include all `required_keys` with correct types.
3. Respect `array_lengths` and `cardinality_rules` (e.g., state_order must match across modules).
4. Lists must preserve the declared order; do not independently sort aligned arrays.

### Numeric Precision

- Non-integer statistics: round to the declared decimal places (typically 4 for state/county, 6 for some county models).
- Integer fields (counts, seeds, PRNG states, ranks): use natural JSON integer types (no decimal point).
- Use JSON `null` only when a statistic is mathematically unavailable (e.g., division with insufficient observations). Never use `NaN` or `Infinity`.

### Enum Values

- Gate values: `"PASS"` or `"FAIL"` exactly.
- Classification/conclusion values: use only the declared controlled vocabulary.
- RNG method names: use exact strings from the analysis request.

### Identifiers

- State codes: uppercase two-letter abbreviations (AL, AK, ..., WY).
- Census divisions: full names from portal geography ("New England", "Middle Atlantic", etc.).
- County FIPS: 5-character strings with leading zeros.
- Country codes: ISO3-like identifiers from the portal.

## Common Pitfalls

1. **Do not include SUPPRESSED in invalid quality flags** unless the analysis request explicitly lists it. Suppression is indicated by `suppression_flag=1`, not by quality_flag.
2. **Resolve socioeconomic fields independently**. The highest-revision record for poverty may differ from the highest-revision record for bachelors.
3. **Use the specified RNG algorithm**. PCG32, XORSHIFT32, and numpy's Mersenne Twister produce different sequences. Match the declared method name.
4. **Standardize features within each CV fold** using only training data statistics. Do not pre-standardize the full dataset.
5. **Year dummies exclude one reference year** (typically the first year) to avoid perfect multicollinearity with jurisdiction dummies.
6. **Income per 10,000**: When the analysis specifies `median_income per 10000`, divide raw median income values by 10,000 before use.
7. **RUCC dummies**: Use RUCC2-RUCC9 as indicator variables with RUCC1 as the reference category.

## Supporting Files

Place any reusable helper modules (RNG implementations, data resolution functions) in `skill/` alongside this SKILL.md.
