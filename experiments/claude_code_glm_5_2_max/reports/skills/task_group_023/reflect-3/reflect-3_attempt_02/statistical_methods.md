# Statistical Methods Reference

## Two-Way Fixed Effects via Within-Transformation

For panel data with entities (states/counties) and time periods (years), the two-way FE model is:

`y_it = alpha_i + gamma_t + X_it * beta + epsilon_it`

Instead of dummy variables (which create singular matrices when deleting entities), use **within-transformation**:

```
y_demeaned = y_it - y_i. - y_.t + y_..
X_demeaned = X_it - X_i. - X_.t + X_..
```

Then regress `y_demeaned` on `X_demeaned` via OLS (no intercept needed).

### Cluster-Robust Variance (CR1)

```python
bread_inv = np.linalg.inv(X_demean.T @ X_demean)
meat = sum(X_g.T @ np.outer(e_g, e_g) @ X_g for g in clusters)
vcv_cr1 = bread_inv @ meat @ bread_inv
se_cr1 = np.sqrt(np.diag(vcv_cr1))
```

## Delete-One-Cluster Jackknife

For g clusters, omit each cluster j in turn:
- `theta_j` = coefficient from model omitting cluster j
- `theta_mean` = mean of all `theta_j`
- `jackknife_se = sqrt((g-1)/g * sum((theta_j - theta_mean)^2))`
- `jackknife_t = theta_full / jackknife_se`
- `jackknife_p = 2 * t.sf(|jackknife_t|, df=g-1)`
- `bias_corrected = g * theta_full - (g-1) * theta_mean`

## Weighted Least Squares (WLS) with HC3

For reliability-weighted regression with weights `w_i`:

```python
W = np.diag(weights)
XtWX = X.T @ W @ X
beta = solve(XtWX, X.T @ W @ y)
resid = y - X @ beta

# HC3 variance
bread_inv = inv(XtWX)
hat = diag(X @ bread_inv @ (X.T * weights))
hc3 = resid**2 / (1 - hat)**2
meat = (X.T * (weights * hc3)) @ X
vcv = bread_inv @ meat @ bread_inv
```

## Ridge Regression

```python
# Standardize on training data
mu = X_train.mean(0)
sigma = X_train.std(0, ddof=0)
X_train_s = (X_train - mu) / sigma
X_test_s = (X_test - mu) / sigma
y_mu = y_train.mean()
y_train_c = y_train - y_mu

# Fit
I = np.eye(p)
beta = solve(X_train_s.T @ X_train_s + lambda * I, X_train_s.T @ y_train_c)
pred = X_test_s @ beta + y_mu
```

## Nested Cross-Validation

1. **Outer loop**: Leave one group out.
2. **Inner loop**: Within the outer training set, leave one group out to evaluate each hyperparameter.
3. Select the hyperparameter with lowest inner RMSE.
4. Retrain on full outer training set with selected hyperparameter.
5. Evaluate on outer test set.

## Conformal Prediction

For split-conformal with nominal coverage `1 - alpha`:

```python
# Calibration residuals
cal_resid = |y_cal - pred_cal|
n_cal = len(cal_resid)

# Threshold (conformal quantile)
level = ceil((1 - alpha) * (n_cal + 1)) / n_cal
level = min(level, 1.0)
threshold = np.quantile(cal_resid, level)

# Prediction interval
interval = [pred - threshold, pred + threshold]
# Coverage for test point: |y_test - pred_test| <= threshold
```

## Covariance PCA

```python
X_centered = X - X.mean(0)
cov_mat = np.cov(X_centered, rowvar=False)
eigenvalues, eigenvectors = np.linalg.eigh(cov_mat)
# eigh returns ascending order; reverse
eigenvalues = eigenvalues[::-1]
eigenvectors = eigenvectors[:, ::-1]
# Explained variance ratio
explained = eigenvalues / eigenvalues.sum()
```

## Deterministic K-Means

1. Initialize centroids at declared positions (e.g., specific entity indices).
2. Assign each point to nearest centroid.
3. Update centroids as cluster means.
4. Repeat until centroids converge (allclose with atol=1e-8).
5. Report iteration count, cluster sizes, labels.

## Adjusted Rand Index (ARI)

Use `sklearn.metrics.adjusted_rand_score(reference_labels, new_labels)`.

ARI = 1.0 means perfect agreement; ARI ≈ 0 means random; ARI can be negative.

## Mediation Analysis (Baron-Kenny / GMM)

- **Total effect**: Regress Y on X + controls → coefficient `c`
- **Path A**: Regress M on X + controls → coefficient `a`
- **Path B + Direct**: Regress Y on X + M + controls → coefficient `b` (for M) and `c'` (for X)
- **Indirect effect**: `a * b`
- **Delta method SE**: `sqrt((b * se_a)^2 + (a * se_b)^2)` (simplified without covariance term)

## Elastic Net

```python
# Coordinate descent with L1 (alpha * l1_ratio) + L2 (alpha * (1 - l1_ratio)) penalty
# Standardize features on training data first
# Use sklearn.linear_model.ElasticNet or manual coordinate descent
```
