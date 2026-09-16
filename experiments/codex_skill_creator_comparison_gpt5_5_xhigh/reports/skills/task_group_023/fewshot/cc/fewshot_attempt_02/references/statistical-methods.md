# Statistical Methods And Determinism

Use this reference for formulas and implementation details across PHO protocols. The effective request and answer template always control names, precision, grids, and output fields.

## Release Resolution

- Fetch CSV exports when available: `/download?dataset=<dataset>&format=csv`.
- Apply all explicit filters first: geography, year, measure or field, value type, source type, release status, revision, and quality constraints.
- If the request specifies a release priority list, apply it exactly. Common patterns in the examples are:
  - Greatest final revision, latest `released_at`, then lowest observation or record id.
  - Greatest final revision, latest `released_at`, then greatest observation or record id.
- Keep FIPS identifiers as text. Preserve leading zeros.
- Missing, blank, suppressed, invalid, withdrawn, and unresolved scale-break cells are not zero. They either fail completeness or are imputed only when a workflow explicitly says to impute.

## Linear Models

- Always build design columns in the declared order.
- Keep intercept handling explicit. If the design order includes `intercept`, include it; fixed-effects double-demeaned designs generally omit it.
- OLS: `beta=(X'X)^-1 X'y`; use a pseudoinverse only if the registered method permits it.
- WLS: transform rows by `sqrt(w)` and solve OLS on weighted rows.
- HC3: with hat diagonal `h_i` and weighted residual `e_i`, use `(X'X)^-1 X' diag(e_i^2/(1-h_i)^2) X (X'X)^-1`.
- CR1 cluster variance: for ordered cluster scores `s_g=X_g'e_g`, use `[G/(G-1)]*[(n-1)/(n-k)]*(X'X)^-1 sum_g(s_g s_g') (X'X)^-1`. Use the protocol's weighted or unweighted design consistently.
- Student-t p-values use the degrees of freedom declared by the module, commonly `n-k` for HC3 and `G-1` for cluster tests.

## Jackknife

For delete-cluster estimates `b_g`:

- `bbar = mean(b_g)`
- `SE_JK = sqrt((G-1)/G * sum((b_g-bbar)^2))`
- `b_BC = G*b_full - (G-1)*bbar`
- Test statistic uses the target coefficient required by the protocol, either `b_full/SE_JK` or `b_BC/SE_JK`.
- Tie-break influence extrema using unrounded statistics and the declared cluster order.

## Ridge And Elastic Net

- Compute scaling moments on training rows only, then apply them unchanged to validation, test, and prediction rows.
- For sample-SD protocols, use `ddof=1`; for population-SD protocols, use `ddof=0`. If a protocol says unit divisor for zero variance, set the scale to 1.
- Ridge uses an unpenalized intercept. Select penalties from pooled validation squared errors, not averages of fold RMSEs, unless the request explicitly says otherwise.
- Elastic net coordinate descent should cold-start each fold and penalty unless the effective protocol says to warm-start.
- Soft threshold: `S(a,t)=sign(a)*max(abs(a)-t,0)`.
- Report selected hyperparameters using unrounded RMSE tie-breaks, then the request's secondary tie-breaks.

## Wild Bootstrap PRNGs

### Xorshift32

Use unsigned 32-bit state and mask after every operation:

```text
x ^= (x << 13)
x ^= (x >> 17)
x ^= (x << 5)
```

Map the resulting state to signs as the protocol declares; examples map odd to `+1` and even to `-1`. Maintain one continuous stream across all replicates and checkpoints.

### PCG32 Webb Weights

Use unsigned 64-bit wraparound:

1. `increment = 2*stream + 1`.
2. Initialize state to zero, advance once, add the effective seed modulo `2^64`, and advance again.
3. Each advance sets `old=state`, then `state=old*6364136223846793005+increment mod 2^64`.
4. Output `rotate_right_32(low32(((old >> 18) xor old) >> 27), old >> 59)`.
5. Map output modulo 6 in order to `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.

For bootstrap p-values, use the registered absolute-tail comparison and plus-one rule `(count+1)/(B+1)`. Record checkpoints only after completing the replicate's draws and refit.

## Conformal Calibration

- Use absolute residuals from the calibration set required by the protocol.
- Sort calibration scores ascending.
- For coverage `c`, rank is `min(m, ceil((m+1)*c))`.
- For miscoverage `alpha`, rank is `min(m, ceil((m+1)*(1-alpha)))`.
- Use one-based ranks against the sorted list. Intervals are inclusive and symmetric around the prediction unless the request declares otherwise.
- Aggregate coverage with row counts, not an unweighted mean of fold coverages, unless specified.

## PCA

- Build columns in declared feature order. Standardize each active column with the protocol's sample or population SD.
- Use the covariance matrix declared by the protocol: commonly `Z'Z/(n-1)` for sample covariance and `Z'Z/n` for population covariance.
- Sort eigenpairs by descending eigenvalue, then the protocol's deterministic tie-break.
- Flip each eigenvector so the earliest maximum-absolute loading is positive, unless a burden workflow requires orienting by adverse direction.
- Scores equal standardized rows multiplied by oriented loadings.

## Deterministic K-Means And Silhouette

- Use squared Euclidean assignment for k-means unless silhouette explicitly needs Euclidean distances.
- Farthest-first initialization usually starts from the ASCII-first or smallest entity id, then adds the point farthest from its nearest center with entity id tie-breaks.
- Assign ties to the lower cluster id. Update centers by arithmetic mean.
- Stop when labels are unchanged or the declared center tolerance or iteration cap is met.
- Canonicalize cluster ids only when the protocol requires it; otherwise preserve working ids or label by ordered burden as requested.
- Silhouette for singleton clusters is zero. Select the largest unrounded average silhouette, then the smaller k.

## Adjusted Rand Index

Given contingency counts `n_ij`, row sums `a_i`, column sums `b_j`, and total `n`:

```text
index = sum_ij C(n_ij, 2)
expected = sum_i C(a_i, 2) * sum_j C(b_j, 2) / C(n, 2)
max_index = 0.5 * (sum_i C(a_i, 2) + sum_j C(b_j, 2))
ARI = (index - expected) / (max_index - expected)
```

When aligning refit labels for agreement counts, search all label permutations, maximize matches, and break ties lexicographically by mapped-id vector.

## Two-Step GMM

- Residualize variables against baseline terms when the protocol says so.
- First step with identity weight: `g(theta)=Z'(y-D theta)/n`.
- Second-step covariance from ordered cluster scores, then Moore-Penrose inverse with the declared relative singular cutoff.
- Hansen `J = n * g(theta)' W g(theta)`.
- Delete-cluster diagnostics refit both steps from scratch and preserve cluster order.

## Source Perturbation And Shapley

- Keep the analytic cohort, design, and weights fixed unless the request says replacement changes them.
- Enumerate subsets in the exact requested order. For bitmasks, preserve the registered entity order and use the lower mask as a tie-break when required.
- Relative shift is `100*abs((b_alt-b_base)/b_base)`.
- Exact Shapley contribution for entity `j` is the sum over subsets not containing `j` of `|S|!*(m-|S|-1)!/m! * (b(S union {j})-b(S))`.
- Verify Shapley effects sum to all-replacement minus no-replacement coefficient before reporting.

## Finalization Checklist

- All modules completed even after failed gates.
- Every array cardinality matches the template.
- All aligned arrays preserve their identifier order.
- All numeric fields are rounded only at serialization.
- Enum values match the template byte-for-byte.
- No extra top-level keys unless explicitly requested.
