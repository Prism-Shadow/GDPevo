# Public Health Observatory Audit Methods

This reference captures reusable procedures only. Bind all entities, measures, years, source filters, grids, seeds, thresholds, labels, and output names from the future request and template.

## Evidence Resolution

Use `/catalog` to confirm columns and `/download?dataset=<dataset>&format=csv` for complete local extracts. Join geography tables before cohort construction so state, region, division, RUCC, country aliases, and stable identifiers are available.

For every publication source:

1. Filter by the effective request: geography, year, measure or field, release status, value type, source type, validity flags, and requested entity list.
2. Resolve one selected record per declared entity-time-measure key using the request's priority. Common priority is greatest revision, latest `released_at`, then the requested identifier tie-breaker. Some profiles specify lowest or greatest record id; follow the exact future contract.
3. Count selected publication records before analytic completeness exclusions when requested.
4. Treat selected records with suppression, invalid flags, withdrawn status, blank values, or null analytic values as unavailable in analytic cohorts.
5. Build primary, balanced, broad, strict, machine-learning, and panel cohorts from the effective nonmissing predicates. Preserve entity-code and time order declared by the request or template.

## Contract and Protocol Profiles

Exact protocol IDs in the staged evidence map to reusable method families:

- `PHO_STATE_TRANSPORT_AUDIT_V1`: state release/cohort audit; two-way fixed-effect delete-state jackknife; nested leave-division-out ridge; PCG32 Webb wild cluster bootstrap; grouped split conformal; state trajectory PCA and deterministic k-means; source-year perturbation; controlled decision.
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1`: county publication/cohort audit; primary mediation OLS; state-clustered difference GMM with cross-equation delta inference; nested leave-state-out ridge; paired xorshift32 wild bootstrap; state-grouped conformal; partial-R2 sensitivity surface; state trajectory PCA/k-means; controlled conclusion.
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`: reliability-weighted state WLS; HC3 and CR1 inference; delete-census-division jackknife; weighted nested elastic net; xorshift32 wild bootstrap; grouped conformal; trajectory PCA/k-means; exhaustive direct-vs-rollup source perturbation with Shapley attribution; controlled decision.
- `PHO_COUNTY_PANEL_TRANSPORT_V1`: balanced county panel; delete-state two-step linear GMM; state-blocked nested elastic net; state wild bootstrap-t; cross-fold grouped conformal; county trajectory PCA/k-means with silhouette selection; source-group deletion perturbation; controlled precedence.
- No protocol ID country-burden requests: reconcile country labels to stable ISO3 identifiers; audit revision notices and scale-break anomalies; impute the requested cross-section after exclusions; run burden PCA, deterministic clusters, silhouette selection, region-adjusted panel regression, and controlled advisory.

Profiles are method guidance. Do not copy any solved answer values or reconstructed train answer records into a future answer.

## Linear Models and Inference

Use declared column order for every design matrix.

OLS:

- Include an intercept only when declared.
- Fit `b = (X'X)^-1 X'y`; use a Moore-Penrose inverse only when the method requests it or the design is singular under a registered pseudoinverse rule.
- For two-way fixed effects, transform every modeled variable as `z_it - entity_mean - time_mean + grand_mean`, then fit without an intercept.

WLS:

- With positive weights `w`, solve OLS on `sqrt(w) * X` and `sqrt(w) * y`.
- Keep reliability weights fixed when the request says source replacements reuse direct-record weights.

HC3:

- Let `Xw=sqrt(w)X` and `ew=sqrt(w)(y-Xb)` for WLS, or `Xw=X`, `ew=e` for OLS.
- `h_i = diag(Xw (Xw'Xw)^-1 Xw')`.
- `V_HC3 = (Xw'Xw)^-1 Xw' diag(ew_i^2/(1-h_i)^2) Xw (Xw'Xw)^-1`.
- Use two-sided Student t with `n-k` residual degrees of freedom unless the request says otherwise.

CR1:

- For clusters `g`, use scores `s_g = Xw_g' ew_g`.
- `V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw'Xw)^-1 * sum_g(s_g s_g') * (Xw'Xw)^-1`.
- Use two-sided Student t with `G-1` degrees of freedom for cluster tests.

Jackknife:

- Delete the whole registered cluster, rebuild all transformations and means, and refit from scratch in declared cluster order.
- With `G` delete estimates, `bbar = mean(b_-g)`, `SE_JK = sqrt((G-1)/G * sum((b_-g-bbar)^2))`, and `b_BC = G*b_full - (G-1)*bbar`.
- Select maximum influence by unrounded absolute or percent change, using the declared tie-breaker, usually earlier registered order.

## GMM Modules

Difference GMM:

- Build adjacent-change rows in entity order then end-period order.
- For one equation, use `W=(Z'Z)^-1` and `beta=(X'Z W Z'X)^-1 X'Z W Z'y`.
- Build cluster scores from instruments and residuals. For mediation, compute cross-equation covariance from matching cluster score products.
- For indirect effect `theta=a*b`, use `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)` and Student-t cluster inference.
- Compute first-stage partial F from full versus reduced residual sums of squares using effective instrument counts.

Two-step linear GMM:

- Residualize outcome, regressors, and instruments against the declared intercept and baseline terms in every full or delete fit.
- First step uses identity weighting on `g(theta)=Z'(y-D theta)/n`.
- Build state scores `s_g=Z_g'u_g`, `S=sum_g(s_g s_g')/n`, and use the registered Moore-Penrose inverse of `S` as the second-step weight.
- Compute second-step coefficients from weighted linear moments and `J=n*g(theta)'Wg(theta)`.
- Refit both steps after each state deletion.

## Penalized Prediction

Training-only scaling is mandatory. Compute feature means and divisors only on the training rows of each inner, outer, or conformal fit, then apply those moments to held-out rows.

Ridge:

- Center the training outcome; keep the intercept unpenalized.
- Use declared feature order and penalty grid order.
- For the mean-squared objective, coordinate update is `b_j = sum_i x_ij*r_ij / (sum_i x_ij^2 + n*lambda)`, where `r` excludes feature `j`.
- Pool validation squared errors at row level before RMSE. Select the smallest unrounded RMSE, then smaller penalty.

Elastic net:

- Cold-start every penalty and fold; do not warm-start.
- Objective forms vary by protocol. Follow the exact scale in the future request.
- Common coordinate update: `rho_j = weighted_mean(x_j * partial_residual)` and `b_j = soft_threshold(rho_j, lambda*l1_ratio) / (mean(x_j^2) + lambda*(1-l1_ratio))`.
- Leave declared indicator columns unstandardized when requested.
- Count nonzero coefficients using the effective numerical cutoff.

State-blocked folds:

- When requested, allocate states by descending retained-row count to the currently smallest fold, using lower fold id on ties. Sort state codes inside folds.

## Wild Cluster Bootstraps

Always maintain one continuous PRNG stream. Draw clusters in declared order for each replicate. Record checkpoints only after completing that replicate and its statistic.

XORSHIFT32 sign bootstrap:

- Start with the effective 32-bit seed.
- Each call: `x ^= x << 13`, `x ^= x >> 17`, `x ^= x << 5`, masking to 32 bits after each xor.
- Map odd state to `+1`, even state to `-1`.
- Fit the restricted model with the target removed, form `y* = restricted_fit + restricted_residual * cluster_sign`, refit unrestricted, recompute CR1, and studentize.
- Use plus-one p-values `(exceedances+1)/(B+1)`.

PCG32 Webb bootstrap:

- Use 64-bit unsigned wraparound. Increment is `2*stream+1`.
- Initialize state to zero, advance once, add the effective seed modulo `2^64`, and advance again.
- Each output uses the PCG XSH-RR 32-bit output. Map `output % 6` to Webb weights in order `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
- For requested weight-index rows, report the indices before mapping to numeric weights.

Quantiles:

- Nearest rank: sort values and return one-based rank `min(B, ceil(p*B))`.
- Type seven: `h=(B-1)p`, `j=floor(h)`, `gamma=h-j`, value `(1-gamma)x[j] + gamma*x[j+1]`.
- Use the quantile type declared by the request/profile.

## Conformal Calibration

- Use the prediction source specified by the module: fixed ridge, nested outer predictions, or cross-fold OOF predictions.
- Sort absolute calibration residuals.
- With nominal coverage `c`, one-based rank is `min(m, ceil((m+1)*c))`; with miscoverage `alpha`, use `c=1-alpha`.
- The radius is the sorted value at zero-based index `rank-1`. Intervals are symmetric and inclusive.
- Aggregate coverage by requested unit. For widths, use row-count weighting unless the template says otherwise.
- Choose worst groups by unrounded coverage or excess, then declared tie order.

## PCA, Clustering, and Stability

Build trajectory matrices in declared variable-major and time order, unless the request says time-major. Use the specified covariance denominator: sample `n-1` or population `n`.

PCA:

- Standardize each active column with the required sample or population divisor.
- Sort eigenpairs by descending eigenvalue, with the specified tie-breaker.
- Orient each eigenvector so the earliest maximum-absolute loading is positive.
- Scores are standardized rows times oriented loadings. Explained ratios divide by the sum of all eigenvalues.

K-means:

- Use squared Euclidean distance for assignment unless silhouette explicitly uses Euclidean distance.
- First center is the smallest entity id or ASCII-first entity; each next center is the entity farthest from its nearest center, tied by entity id.
- Assign to the nearest center, tied by lower cluster id. Update by arithmetic means.
- Stop when assignments are unchanged or the registered cap/tolerance is reached.
- Canonicalize labels only when the profile says to do so; otherwise preserve working cluster ids.

Stability:

- For leave-year, leave-period, or delete-state checks, rebuild scaling, PCA orientation, initialization, and clustering from scratch.
- Compute adjusted Rand index from the contingency table.
- Align refit labels by maximum agreement when requested, breaking ties by lexicographically smallest mapped-id vector.

Country burden:

- Reconcile each requested label against canonical, portal, and alternate labels; output ISO3 identifiers sorted when the template says set-like lists are sorted.
- Apply only `APPLIED` revision notices. Pending or withdrawn revisions are audit evidence but do not authorize replacement.
- Exclude unresolved scale-break anomalies before cross-section imputation. Count raw missing cells before anomaly exclusions and total imputed cells after exclusions as requested.
- For burden PCA, indicators marked higher-worse already share burden direction. If a request mixes directions, reverse favorable indicators before burden interpretation.
- Run requested three-cluster grouping and also evaluate candidate silhouette counts. Label burden segments by the ordering of cluster burden scores, not by arbitrary k-means ids.
- For region-adjusted panel association, regress the panel outcome on PC1 burden plus region fixed effects as declared.

## Source Perturbation and Shapley

Source-year perturbation:

- Enumerate year subsets by increasing subset size, then lexicographic tuple order.
- Keep the strict analytic set unchanged. Refit primary and alternate source models separately for every subset.
- Percent shift is `100*abs(b_alt-b_base)/abs(b_base)`. Compute medians and extrema from unrounded shifts.

Exhaustive direct-vs-rollup perturbation:

- Resolve baseline and replacement sources separately.
- Order replacement entities by descending absolute source disagreement, tied by entity code.
- For masks `0` through `2^m-1`, replace entity `j` iff bit `j` is set. Refit with fixed design and fixed direct reliability weights when required.
- Summarize every popcount stratum. Select maximum shift by unrounded shift, tied by smaller mask.
- Shapley value for ordered entity `j` is the factorial-weighted mean of `b(S union {j}) - b(S)` over all subsets not containing `j`. Verify the sum equals all-replacement coefficient minus no-replacement coefficient within tolerance.

Source-group perturbation:

- For each declared source group and outer fold, remove exactly the group terms.
- Reuse the full-model selected hyperparameters for that fold; do not retune.
- Recompute remaining preprocessing and solver fits. Pool squared errors before RMSE. Rank deterioration by unrounded deterioration, then declared group order.

## Controlled Decisions

Complete every evidence module before deciding. Evaluate gates on unrounded values. Preserve the gate order and controlled enum values from the future request/template. For first-failed precedence, return the first unsatisfied module in the declared precedence list; for count-based classification, count all satisfied flags before mapping.
