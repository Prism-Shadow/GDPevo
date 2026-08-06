# PHO Audit Task Group -- Shared Skill Reference

This document captures the shared procedure, conventions, and pitfalls across the five PHO (Public Health Observatory) algorithmic audit train tasks. It is distilled from the solve scripts (`t1_solve.py` through `t5_solve.py`), their `analysis_request.json` specifications, `answer_template.json` contracts, and the shared libraries `common.py` and `t1_lib.py`.

---

## 1. Data Pipeline

### 1.1 Download from PHO Portal

All source CSVs are fetched from the task environment endpoint:

```
GET http://task-env:9023/download?dataset=<dataset>&format=csv
```

Typical datasets per geography level:

| Geography | Health file | Socioeconomic file | Metadata file |
|-----------|-------------|--------------------|---------------|
| State | `state_health_all.csv` | `state_socioeconomic_all.csv` | `states.csv` |
| County | `county_health_all.csv` | `county_socioeconomic_all.csv` | `counties.csv` |
| Country | `country_indicators_all.csv` | -- | `countries.csv` + `revisions.csv` |

The download helper (in `common.py`) is:

```python
BASE = "http://task-env:9023/"
def download(dataset, out):
    urllib.request.urlretrieve(f"{BASE}download?dataset={dataset}&format=csv", out)
```

### 1.2 Record Resolution: `pick_final`

Multiple records may exist for the same entity/year/measure (different revisions, releases). The selection rule is deterministic:

```python
def pick_final(recs):
    best = None
    for r in recs:
        rid = r.get("observation_id") or r.get("record_id") or ""
        key = (int(r["revision"]), r["released_at"], rid)
        if best is None or key > best[0]:
            best = (key, r)
    return best[1]
```

**Precedence**: highest `revision` number, then latest `released_at` timestamp (string comparison), then highest `observation_id`/`record_id`. Apply this *within* each filter group (e.g., among FINAL records with the same value_type and source_type).

### 1.3 Quality Flag Filtering

```python
INVALID_FLAGS = {"INVALID", "WITHDRAWN", "INVALID_SCALE"}
```

- A record whose `quality_flag` is in `INVALID_FLAGS` is **excluded entirely** -- its value is treated as unavailable.
- A record with `suppression_flag == "1"` is also excluded (suppressed values are unavailable).
- The missing rule per spec: *"SUPPRESSED_INVALID_OR_BLANK_VALUES_ARE_UNAVAILABLE_AND_NEVER_ZERO_FILLED"*.
- A value is valid only if it is non-null, non-empty, non-"nan" string, and convertible to float:

```python
def valid_val(v):
    if v is None or v == "" or str(v).lower() == "nan": return None
    try: return float(v)
    except: return None
```

### 1.4 Release and Value-Type Filters

Each task specifies filter triples. The common patterns:

| Filter label | value_type | source_type | release_status |
|---|---|---|---|
| Primary (age-adjusted) | `AGE_ADJUSTED` | `DIRECT_SURVEY` | `FINAL` |
| Parallel (crude) | `CRUDE` | `DIRECT_SURVEY` | `FINAL` |
| Crude county | `CRUDE` | `DIRECT_SURVEY` | `FINAL` |
| County rollup | `CRUDE` | `COUNTY_ROLLUP` | `FINAL` |

For socioeconomic tables, only `release_status == "FINAL"` is required (no value_type/source_type).

### 1.5 Canonical Value Resolution

When the spec calls for a "canonical" or "resolved" value (e.g., for trajectory PCA), prefer:
1. AGE_ADJUSTED DIRECT_SURVEY FINAL (primary)
2. Fall back to CRUDE DIRECT_SURVEY FINAL (parallel)

```python
canonical = {}
for k in set(primary) | set(parallel):
    canonical[k] = primary.get(k, parallel.get(k))
```

### 1.6 Country-Level Special: Scale Review and Revisions

For country-level tasks (train_003):
- A `SCALE_REVIEW` quality flag indicates a scale-break anomaly.
- If a higher-revision `CORRECTED` record supersedes it, use that corrected value.
- Otherwise the cell is unresolved (treated as missing/anomaly).
- Track `applied_revision_event_ids` and `nonapplied_revision_event_ids` from the revisions CSV.
- Missing non-anomaly cells may be imputed with column means for PCA.

---

## 2. Cohort Construction

### 2.1 Cohort Definitions

Each task defines up to four nested cohorts:

| Cohort | Definition |
|--------|-----------|
| **Primary / Reference-year** | Complete-case for all required variables in the reference year only |
| **Balanced panel** | Complete-case in *every* analysis year |
| **Broad reference** | Reference-year complete for outcome + all ridge/prediction features |
| **Strict dual-source** | Complete for outcome, primary exposure, parallel exposure, and adjustments in every year |
| **Machine learning** | Primary cohort + additional ML features (e.g., unemployment, net_migration, uninsured) in reference year |

### 2.2 Completeness Checks

A "complete" observation requires:
- All requested health values are present, nonsuppressed, and nonmissing (via `valid_val`)
- All requested socioeconomic fields are nonmissing
- RUCC code is a valid integer 1-9 (county-level tasks)
- For WLS tasks: required sample_size fields are nonmissing

**Never zero-fill** missing values.

### 2.3 State/County/Country Census

- State-level tasks: universe is 50 states + DC = 51 jurisdictions.
- County-level tasks: restrict by region (e.g., Midwest+South, or West+Northeast) using the metadata file's `region` field.
- Country-level tasks: reconcile `country_labels` from the request against `countries.csv` (canonical name, portal label, alternate labels) to get ISO3 codes.

### 2.4 RUCC Validity

For county-level tasks, `rucc` must be an integer from 1 to 9. Counties with missing or out-of-range RUCC are excluded from cohorts requiring RUCC indicators.

RUCC indicators: `RUCC2` through `RUCC9` (RUCC1 is the reference category).

### 2.5 Year Range Matching

- Analysis years come from `analysis_request.json` (e.g., `[2020,2021,2022,2023,2024]` or `[2021,2022,2023,2024]`).
- Reference year determines the cross-sectional cohort.
- Balanced panel requires completeness in *all* analysis years.
- Panel end-years for change models may be a subset (e.g., `[2022,2023,2024]` when panel years are `[2021,2022,2023,2024]`).

---

## 3. Statistical Modules

### 3.1 Delete-Cluster / Jackknife Fixed Effects

**Task appearances**: t1 (delete-one-state), t4 (delete-one-division), t5 (delete-state GMM)

**Core procedure**:
1. Fit the full model (two-way FE OLS with state + year dummies, or WLS) on the complete cohort.
2. For each cluster (state or division), delete that cluster's observations and refit.
3. Extract the target coefficient from each delete-one fit.

**Jackknife inference**:
- `jack_mean = mean(delete_coefs)`
- `jack_se = sqrt((G-1)/G * sum((delete_coefs - jack_mean)^2))` where G = number of clusters
- `jack_t = full_coef / jack_se`
- `bias_corrected = 2 * full_coef - jack_mean`
- For p-value: use t-distribution with G-1 df (small-sample) or normal approximation (task-specific).

**Key details**:
- Reference coding: drop the first state and first year dummy (intercept absorbs).
- The target coefficient index depends on design matrix column ordering (e.g., obesity is the first predictor after FEs, so it is at index `-4` when there are 4 predictors).
- For WLS jackknife (t4): transform X and y by `sqrt(weights)` before OLS. The delete-cluster refit also uses WLS.

### 3.2 Two-Step Linear GMM (Delete-State)

**Task appearance**: t5

**Procedure**:
1. Build the instrument matrix Z: all exogenous regressors (intercept, base terms, levels of dynamic terms) PLUS excluded instruments (e.g., interactions of dynamic terms with period indicators).
2. **First step**: 2SLS using `W = inv(Z'Z)` as the weighting matrix.
   - Project: `Pz = Z @ inv(Z'Z) @ Z.T`
   - `b_2sls = lstsq(Pz @ X, Pz @ y)`
3. **Second step**: Cluster-robust weighting matrix.
   - Compute residuals from 2SLS.
   - `S = sum_c (Z[c].T @ resid[c]) (Z[c].T @ resid[c]).T` over clusters c.
   - `W = inv(S)`
   - `b_gmm = solve(X.T @ Z @ W @ Z.T @ X, X.T @ Z @ W @ Z.T @ y)`
4. **Hansen J** statistic: `J = resid.T @ Z @ W @ Z.T @ resid`
5. **Delete-state jackknife**: For each state s, remove its rows, re-run full two-step GMM, record coefficients and Hansen J. Bias-correct via `2 * full - mean(delete)`.

**Critical instrument construction**: The Z matrix includes *all exogenous regressors* plus the *excluded instruments*. Do NOT use only the listed instruments. For t5, with 4 dynamic terms and 4 excluded interaction instruments, Z has 21 columns (intercept + 12 base + 4 dynamic levels + 4 excluded interactions).

### 3.3 Nested Elastic Net / Ridge

**Task appearances**: t1 (ridge), t2 (ridge), t4 (elastic net), t5 (elastic net)

**Common pattern**:
1. Outer folds: leave-one-group-out (group = census division or state).
2. Inner folds: leave-one-group-out within the outer training set.
3. For each inner fold, standardize continuous features using training-only mean/sd.
4. Fit the penalized model on the standardized training data.
5. Select hyperparameters (lambda or alpha+l1_ratio) by minimum inner RMSE.
6. Refit on full outer-train with selected hyperparameters, predict outer-test.

**Ridge** (closed-form):
```python
b = solve(X_s.T @ X_s + lam * I, X_s.T @ y)
```
- Intercept is added as a column of ones (not penalized).
- Standardization is training-only, applied to both train and test.

**Elastic Net** (coordinate descent, sklearn-compatible):

**The objective is**:
```
(1/(2n)) * ||y - Xb||^2 + alpha * l1_ratio * ||b||_1 + 0.5 * alpha * (1 - l1_ratio) * ||b||^2
```

**Critical penalty convention (sklearn divides by 2n)**:
- `rho_j = X[:,j].T @ r_j / n` (NOT `X[:,j].T @ r_j`)
- `z_j = (X[:,j]**2).sum() / n + alpha * (1 - l1_ratio)` (NOT without the /n)
- Soft-threshold at `alpha * l1_ratio` (NOT `n * alpha * l1_ratio`)
- The `alpha` grid values in the spec are already in sklearn's convention. Do NOT rescale them.

**Feature handling**:
- Standardize continuous features (training-only mean/sd).
- Indicator/dummy features are NOT standardized (t5 explicitly lists separate `continuous_terms_to_standardize` and `indicator_terms`).
- Intercept is not penalized. When adding an intercept column, either: (a) center y by subtracting weighted mean and fit without intercept, adding it back after, or (b) use the intercept column but do not penalize it.
- For WLS (t4): weight X and y by `sqrt(weights)` before fitting.

**Pooled metrics**: Collect all outer-test predictions, compute pooled RMSE, MAE, R-squared.

### 3.4 Wild Cluster Bootstrap

**Task appearances**: t1 (PCG32), t2 (XORSHIFT32), t4 (XORSHIFT32), t5 (XORSHIFT32)

**Common procedure**:
1. Fit the restricted-null model: impose H0 on the target coefficient (set it to 0).
2. Compute residuals under the null: `resid0 = y - X@b + b[target_idx] * X[:,target_idx]`
3. For each replication:
   a. Draw Webb weights per cluster using the PRNG.
   b. Construct `y* = X@b - b[target_idx]*X[:,target_idx] + wv * resid0` (restricted-null wild bootstrap).
   c. Refit the model on `y*`, compute the t-statistic for the target coefficient (using CR1 SE).
   d. Record if `|t*| >= |obs_t|`.
4. **Plus-one p-value**: `(exceed + 1) / (REPS + 1)` -- this is the standard bootstrap p-value convention for these tasks (not the simple fraction).

**PRNG implementations**:

**PCG32** (t1 -- uses seed + stream):
```python
class PCG32:
    M = (1 << 64) - 1
    def __init__(self, seed, stream):
        self.inc = ((stream << 1) | 1) & self.M
        self.state = (seed + self.inc) & self.M
    def next_uint32(self):
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & self.M
        xs = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = (old >> 59) & 0xFFFFFFFF
        return ((xs >> rot) | (xs << ((-rot) & 31))) & 0xFFFFFFFF
```

**XORSHIFT32** (t2, t4, t5 -- uses seed only):
```python
class XorShift32:
    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF
    def next_uint32(self):
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17)
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state
```

**Webb weights** (5-point distribution):
```python
WEBB_WEIGHTS = np.array([
    -np.sqrt(1.5), -np.sqrt(0.5), 0.0,
    np.sqrt(0.5), np.sqrt(1.5)
])
```

Weight selection per cluster: `widx = int(rng.next_uint32()) % len(WEBB_WEIGHTS)`, then assign `WEBB_WEIGHTS[widx]`.

**Checkpoint tracking**: Record PRNG state and t-statistic at specified replicate numbers (varies by task). The `prng_state` in the checkpoint is `int(rng.state)` captured *after* drawing weights for that replicate.

**CR1 variance for bootstrap**: Same formula as in section 3.1, but applied to the bootstrap sample `y*`. For WLS tasks (t4), remember to weight by `sqrt(weights)`.

**Key detail on restricted-null**: The null is imposed on the *target coefficient only*. The rest of the coefficient vector is from the unrestricted full-model fit.

### 3.5 Grouped Conformal Calibration

**Task appearances**: t1, t2, t4, t5

**Common pattern**:
1. For each held-out group (division, state fold, etc.):
   - Train ridge/elastic-net on all other groups.
   - Compute predictions on the calibration set (= training set or a held-out calibration fold).
   - Compute absolute residuals `|y - pred|` on calibration.
2. Compute the conformal quantile (threshold):
   ```python
   q_level = min(np.ceil((n_cal + 1) * nominal_coverage) / n_cal, 1.0)
   qhat = np.quantile(abs_resid_cal, q_level, method='higher')
   ```
   **Use `nominal_coverage` directly (e.g., 0.90), NOT `1 - nominal_coverage`**. The formula is the standard split-conformal finite-sample correction with the +1.
3. Predict on the test set, compute intervals `[pred - qhat, pred + qhat]`.
4. Coverage = fraction of test points inside the interval.

**Variants**:
- **t1**: Leave-one-division-out, calibration = training set, alpha=0.20.
- **t2**: 5 state-group partitions (round-robin), separate calibration fold.
- **t4**: Uses elastic-net OOF residuals. Nearest-rank formula: `rank = ceil((ncal+1)*(1-NOMC))`, threshold = sorted calibration residuals at that rank.
- **t5**: Cross-fold grouped, with per-state coverage, RUCC-band coverage, and prediction-decile calibration diagnostics.

**Critical: nearest-rank formula**. For t4/t5 the rank-based implementation is:
```python
rank = int(math.ceil((ncal + 1) * (1 - NOMC)))  # this is the rank in ascending residuals
rank = min(rank, ncal)
qhat = sorted_cal_resid[rank - 1]
```
Note: When `nominal_coverage = 0.90`, `(1 - NOMC) = 0.10`, so `rank = ceil(43 * 0.10) = 5`. Equivalently, `ceil((ncal+1) * nominal_coverage) = ceil(43 * 0.90) = 39`, which gives the (ncal+1-5+1)=39th position from the top -- both are the same quantile. The key is: **quantile method uses `nominal_coverage`, nearest-rank method uses `(1 - nominal_coverage)` to find the position from the top**. Do NOT accidentally use `1 - nominal_coverage` in the quantile formula or `nominal_coverage` in the rank-from-top formula.

### 3.6 Trajectory PCA + Clustering

**Task appearances**: t1, t2, t3, t4, t5

**Core procedure**:
1. Build a feature matrix: rows = units (states, counties, countries), columns = variable x year features.
2. Center the matrix (subtract column means). Do NOT scale (covariance PCA, not correlation).
3. Compute covariance matrix: `S = Xc.T @ Xc / (n - 1)`.
4. Eigendecompose via `np.linalg.eigh`, sort eigenvalues and eigenvectors in descending order.
5. Retain `ncomp` components (specified per task, typically 2-5).
6. Compute scores: `scores = Xc @ eigvecs[:, :ncomp]`.

**Deterministic k-means**:
- Initialization: k-means++ style, deterministic.
  - First centroid = point at index 0.
  - Subsequent centroids: pick the point with maximum minimum squared distance to already-selected centroids.
```python
init = [0]
for _ in range(k - 1):
    d = np.array([min(np.sum((X[i] - X[j])**2) for j in init) for i in range(n)])
    init.append(int(np.argmax(d)))
```
- Lloyd iterations until convergence (`np.allclose(new, old)`).
- Record: initial centroid states, cluster labels, sizes, iteration count.

**Silhouette selection** (t3, t5): Try k = 2..5 or 2..6, select k with highest silhouette score on standardized data.

**Leave-year-out stability** (t1, t2, t4): Remove one year's columns, redo PCA + k-means with same k, compute Adjusted Rand Index (ARI) between full and leave-year-out labels.

**Delete-state stability** (t5): Remove one state's observations, redo PCA + k-means, compute ARI. Report median and minimum ARI.

### 3.7 Source Group Perturbation

**Task appearances**: t1 (source-year), t4 (exhaustive source with Shapley), t5 (no-retune source-group)

**t1 -- Source year perturbation**:
- Exhaustive subsets of year combinations (sizes 3,4,5 from 5 years = 16 subsets).
- For each subset: fit twice (primary series = age-adjusted, parallel series = crude), with state + year FE + adjustments.
- Record: coefficient, CR1 p-value, absolute percent shift = `|coef_parallel - coef_primary| / |coef_primary| * 100`.

**t4 -- Exhaustive source perturbation with exact Shapley**:
- Baseline: direct survey AGE_ADJUSTED diabetes values.
- Replacement: CRUDE COUNTY_ROLLUP diabetes values.
- Enumerate all 2^M subsets (M = states with both sources eligible).
- For each subset, replace those states' outcome values with rollup, refit WLS, record coefficient and HC3 p-value.
- **Exact Shapley**: For each state j, `Shapley_j = average over all subsets S not containing j of (v(S union j) - v(S))` where v is the food_insecurity coefficient.

**t5 -- No-retune source group perturbation**:
- Six source groups (lagged context, rurality, interval, dynamics, etc.).
- For each group: drop its terms from features, **reuse the same outer-fold hyperparameters** (alpha, l1_ratio) from the full model, retrain elastic net on reduced features.
- Compute per-fold and pooled RMSE, deterioration = `pooled_rmse_reduced - pooled_rmse_full`.
- Rank groups by deterioration (descending: rank 1 = worst deterioration).

### 3.8 Mediation Sensitivity Surface

**Task appearance**: t2

- Baseline: path_a (poverty -> inactivity), path_b (inactivity -> obesity in direct model).
- Grid: `r2_mediator_confounder` x `r2_outcome_confounder` in `{0.04, 0.08, 0.16, 0.24, 0.32}`, directions NEGATIVE and POSITIVE.
- Adjusted path_b: `baseline_path_b + sign * sqrt(r2_m * r2_y) * |baseline_path_b|`.
- Equal-strength tipping R2: find smallest R2 where adjusted indirect flips sign.
- Output: baseline quantities, tipping R2, and complete sensitivity surface.

---

## 4. Decision Rules

Each task defines a set of gate-check conditions and a classification rule. The patterns are:

### t1 -- State longevity audit
| Gate | Condition |
|------|-----------|
| delete_cluster_fe | full coef < 0 AND jackknife p <= 0.05 |
| nested_ridge | pooled Q^2 >= 0.85 AND pooled RMSE <= 0.75 |
| wild_cluster_bootstrap | bootstrap p <= 0.05 |
| grouped_split_conformal | aggregate coverage >= 0.80 AND agg mean width <= 3.25 |
| trajectory_stability | min leave-year-out ARI >= 0.75 AND cum explained ratio >= 0.90 |
| source_year_stability | same-sign fraction >= 0.75 AND median shift <= 50 |

Classification: all 6 -> PRIMARY_TRANSPORTABLE_LONGEVITY_SIGNAL; 4-5 -> ASSOCIATED_LONGEVITY_SIGNAL_WITH_LIMITED_TRANSPORTABILITY; otherwise NO_TRANSPORTABLE_LONGEVITY_SIGNAL.

### t2 -- County mediation audit
| Gate | Condition |
|------|-----------|
| difference_gmm | indirect 95% CI excludes zero |
| nested_ridge | augmented RMSE < base RMSE AND augmented wins >= 16 states |
| bootstrap | PATH_A and PATH_B bootstrap p < 0.05 |
| conformal | overall coverage >= 0.90 AND >= 24 states >= 0.80 |
| sensitivity | every POSITIVE row with both R2 <= 0.08 preserves sign |
| trajectory | mean ARI >= 0.60 AND min ARI >= 0.40 |

Classification: 6 -> CONSISTENT; 4-5 -> PARTIAL; 2-3 -> FRAGILE; 0-1 -> NO_OBESITY_MEDIATION_AUDIT.

### t3 -- Country burden stratification
- Panel model p < 0.05 and coef < 0 -> PRIORITIZE_HIGH_BURDEN_CLUSTER
- p < 0.10 -> MONITOR_GRADIENT
- Otherwise -> NO_ADVERSE_GRADIENT

### t4 -- Weighted state diabetes audit
| Gate | Condition |
|------|-----------|
| cluster_jackknife | bias-corrected > 0 AND p < 0.05 AND max % change <= 25 |
| nested_prediction | pooled OOF R^2 >= 0.55 |
| wild_bootstrap | plus-one p < 0.05 |
| grouped_conformal | pooled coverage >= 0.85 |
| trajectory | min leave-year ARI >= 0.55 |
| source_exhaustive | all scenarios stable AND max |shift| <= 25 |

Classification: sequential -- first failed module name determines `NOT_ROBUST_AT_<MODULE>`. If none fail: ROBUST_ACROSS_REGISTERED_MODULES.

### t5 -- County dynamics audit
| Gate | Condition |
|------|-----------|
| GMM | bias-corrected poverty_change coef > 0.04 |
| elastic_net | OOF RMSE < 0.85 |
| wild_bootstrap | plus-one p < 0.06 |
| conformal | overall coverage >= 0.89 |
| trajectory | median delete-state ARI >= 0.70 |
| source_group | poverty_dynamics deterioration >= 0.006 |

Classification: 6 -> DEPLOY_DIABETES_DYNAMICS; 4-5 -> REVIEW_DIABETES_DYNAMICS; 0-3 -> RETAIN_LAGGED_DIABETES.

### Gate-check patterns across tasks
- **Coefficient sign + significance**: common in delete-cluster and GMM gates.
- **Predictive accuracy threshold**: pooled R^2 or RMSE ceiling.
- **Bootstrap p-value threshold**: typically 0.05, but t5 uses 0.06.
- **Conformal coverage floor**: 0.80, 0.85, 0.89, or 0.90 depending on task.
- **Trajectory stability**: ARI floors vary (0.40 to 0.75).
- **Source stability**: percent shift ceiling (25 or 50) or same-sign fraction.

---

## 5. Common Pitfalls

### 5.1 Elastic Net Penalty Convention (sklearn divides by 2n)

The sklearn ElasticNet objective divides the loss by 2n. When implementing coordinate descent from scratch:

```
rho_j = X[:,j]^T @ r_j / n        (NOT X[:,j]^T @ r_j)
z_j   = ||X_j||^2 / n + alpha*(1-l1_ratio)   (NOT without /n)
threshold = alpha * l1_ratio      (NOT n * alpha * l1_ratio)
```

The `alpha` values in the spec grid ARE in sklearn convention already. Do not rescale them. Getting this wrong produces coefficients differing by up to ~0.13 on realistic data, cascading into all downstream statistics.

### 5.2 Conformal Rank Formula

Use `nominal_coverage` directly (e.g., 0.90) in the quantile formula, NOT `1 - nominal_coverage`:

```python
q_level = np.ceil((n_cal + 1) * nominal_coverage) / n_cal
```

For the nearest-rank variant used in some tasks, the rank from the top of ascending residuals uses `(1 - nominal_coverage)`:
```python
rank = int(math.ceil((ncal + 1) * (1 - NOMC)))
rank = min(rank, ncal)
qhat = sorted_cal_resid[rank - 1]
```

Do NOT confuse which formula uses which direction. The quantile formula uses `nominal_coverage`; the rank-from-top formula uses `1 - nominal_coverage`. Mixing them yields thresholds near zero (giving ~100% coverage) or thresholds near max (giving ~0% coverage).

### 5.3 GMM Instrument Matrix

The Z matrix must include **all exogenous regressors** (intercept, state/year dummies, levels of dynamic terms) PLUS the **excluded instruments** (e.g., interactions). Do NOT build Z from only the listed instruments. The spec's `instrument_order` lists the 4 level + 4 interaction instruments, but Z has 21 columns including all exogenous regressors. Using only the 8 listed instruments gives J = 0 (just-identified or under-identified) and wrong coefficients.

### 5.4 XORSHIFT32 Implementation

The XORSHIFT32 state must be ANDed with `0xFFFFFFFF` at each step:
```python
x ^= (x << 13) & 0xFFFFFFFF
x ^= (x >> 17)
x ^= (x << 5) & 0xFFFFFFFF
self.state = x & 0xFFFFFFFF
```
Without the bitwise AND on the left shifts, the integer can grow beyond 32 bits, corrupting all downstream random numbers and making bootstrap results irreproducible.

### 5.5 CR1 Degrees of Freedom

For the CR1 small-sample correction:
```python
adj = (G / (G - 1)) * ((n - 1) / (n - k))
```
where G = number of clusters, n = observations, k = parameters. The p-value uses t-distribution with `G - 1` degrees of freedom (not `n - k`).

### 5.6 -0.0 Floating Point Cleanup

Python/numpy can produce `-0.0` which serializes as `-0.0` in JSON. This can fail exact-match grading. After computing, ensure:
```python
if isinstance(x, float) and x == 0.0:
    x = 0.0  # convert -0.0 to 0.0
```

Or apply `round(x, N)` which also cleans -0.0 in most cases. The `r4` and `r6` helpers in common.py handle this implicitly via `round()`.

### 5.7 Intercept Handling in Ridge/Elastic Net

The intercept is never penalized. Two approaches:
1. **Add intercept column**: Include a column of ones in the design matrix but do not include it in the penalty term (ridge: only penalize the feature columns).
2. **Center y and X**: Subtract means so intercept is implicitly zero, fit without intercept, then recover intercept as `intercept = y_mean - X_mean @ beta`.

The solve scripts use approach 1 for ridge and approach 2 for elastic net coordinate descent. Be consistent within each module.

### 5.8 Weighted Least Squares (WLS)

For WLS, transform: `X_w = X * sqrt(w)[:, None]`, `y_w = y * sqrt(w)`, then fit OLS on `X_w, y_w`. The HC3 variance must also work in weighted scale. Do NOT forget to apply the weight transformation in every delete-cluster refit and bootstrap replication.

### 5.9 Canonical vs Primary Value Preference

For the resolved/canonical health value, prefer AGE_ADJUSTED over CRUDE. For source perturbation, the "primary" series uses AGE_ADJUSTED and the "parallel" series uses CRUDE. Mixing these up produces wrong source-shift values.

### 5.10 PCA Covariance Divisor

The `common.cov_pca` function uses `n - 1` as the divisor (sample covariance). Some task implementations also use `n - 1`. Be consistent within a task -- check whether the spec or the solve script uses `n` or `n - 1`. The covariance matrix formula is `Xc.T @ Xc / (n - 1)` in common.py but `Xc.T @ Xc / ntr` in some solve scripts. The eigenvalues differ but the loadings and explained ratios are the same either way when dividing the whole matrix by a constant; however the eigenvalues themselves differ by the scaling factor. Follow the specific task's solve script for consistency.

---

## 6. Numerical Precision

The reporting precision varies by task:

| Task | Computed reals | Literal grid/threshold | Integers |
|------|---------------|----------------------|----------|
| t1, t2, t3, t4 | 4 decimal places | 4 decimal places | natural JSON |
| t5 | 6 decimal places | 4 decimal places | natural JSON |

**Rules**:
- Report computed reals to the specified decimal places using `round(x, N)`.
- Literal grid values (alpha, l1_ratio, lambda, nominal_coverage) are reported to 4 decimal places even in 6-decimal tasks.
- Counts, ranks, fold numbers, seeds, PRNG states, and replicate numbers are integers.
- Use `round(x, 6)` (or `round(x, 4)`) consistently -- do NOT use `np.round` (which can produce -0.0).
- The `r4` helper from `common.py`:
```python
def r4(x):
    if x is None: return None
    if isinstance(x, (float, np.floating)) and (math.isnan(x) or math.isinf(x)): return None
    return round(float(x), 4)
```

---

## 7. JSON Output Rules

### 7.1 Key Ordering

Match the `answer_template.json` key ordering exactly. The required top-level keys and their order are task-specific. Output no extra keys and omit none.

### 7.2 Array Ordering

- State abbreviation lists: sorted ascending (ASCII).
- Division order: sorted ascending by name.
- Coefficient arrays: follow the declared `coefficient_order` or `ordered_predictors` from the analysis request.
- Lambda/alpha grids: follow declared order from the analysis request.
- Checkpoint arrays: follow the `checkpoint_replicates` order from the analysis request.
- Leave-year-out arrays: follow year order from the analysis request.
- Source perturbation subsets: follow the natural enumeration order (combinations in lexicographic order of year subsets).
- Shapley effects: one-to-one with `ordered_rollup_state_codes`.
- RUCC-band arrays: follow the spec's `rucc_bands` order (e.g., `[[1,3],[4,6],[7,9]]`).
- Decile calibration: deciles 1 through 10.

### 7.3 Cardinality Alignment

Several arrays must be positionally aligned:
- `delete_obesity_coefficients` must align with `state_order`.
- `pc1_scores`, `pc2_scores`, `cluster_labels` must align with `state_order`.
- State assignments in trajectory PCA must be in the same order as `balanced_state_codes`.
- Inner RMSE grids must be aligned to `lambda_grid`.
- Batch exceedance counts: 20 batches of ~100 reps each (for 1999 total).
- `first_three_weight_index_rows`: each row has `state_order` length, columns aligned positionally.

### 7.4 Missing Values

Use `null` (JSON) for mathematically unavailable values. Never use NaN, Infinity, or -0.0 in numeric fields.

### 7.5 Boolean and Enum Fields

- Gate results: boolean `true`/`false`.
- PASS/FAIL: string literals `"PASS"`/`"FAIL"`.
- Classification: exactly one of the declared enum strings (e.g., `"PRIMARY_TRANSPORTABLE_LONGEVITY_SIGNAL"`, not `"Primary Transportable Longevity Signal"`).

### 7.6 Serialization

```python
import json
def dump_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2,
                  default=lambda o: int(o) if isinstance(o, np.integer)
                      else (float(o) if isinstance(o, np.floating) else o))
```

This handles numpy integer and float types that are not natively JSON-serializable.

---

## Appendix: Module-to-Task Cross-Reference

| Module | t1 | t2 | t3 | t4 | t5 |
|--------|----|----|----|----|-----|
| Delete-cluster/jackknife FE | X (state) | X (state, indirect) | -- | X (division WLS) | X (state GMM) |
| Nested ridge/elastic net | X (ridge, division) | X (ridge, state) | -- | X (enet, division) | X (enet, state) |
| Wild cluster bootstrap | X (PCG32) | X (XORSHIFT32, 3 eqs) | -- | X (XORSHIFT32, absolute t) | X (XORSHIFT32) |
| Grouped conformal calibration | X (division) | X (state, 5-partition) | -- | X (division, rank-based) | X (5-fold, RUCC/decile) |
| Trajectory PCA + clustering | X (leave-year) | X (leave-year, state agg) | X (silhouette select) | X (leave-year) | X (delete-state, silhouette) |
| Source group perturbation | X (source-year) | -- | -- | X (Shapley) | X (no-retune) |
| Mediation / sensitivity | -- | X (partial R2) | -- | -- | -- |
| Country reconciliation | -- | -- | X | -- | -- |
| Panel model | -- | -- | X | -- | -- |
