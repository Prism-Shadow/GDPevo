---
name: pho-audit-solver
description: Solve Public Health Observatory algorithmic transportability audits using an HTTP portal API. Covers release resolution, cohort construction, and a catalog of reusable statistical modules (fixed-effects jackknife, ridge/elastic-net CV, wild cluster bootstrap, grouped conformal, PCA clustering, source perturbation, GMM mediation, and sensitivity surfaces) with exact output formatting against a provided answer template.
---

# PHO Audit Solver

This skill equips you to solve Public Health Observatory (PHO) algorithmic audit tasks. Every task follows the same core pattern: read a prompt plus `analysis_request.json` and `answer_template.json`, gather evidence from the PHO web portal, run the declared statistical modules, and return one JSON object conforming to the template.

**What this skill covers**

- Navigating the PHO portal API to pull publication records
- Resolving final releases with revision and timestamp precedence
- Building analytic cohorts (complete, balanced, broad, dual-source, machine-learning)
- Implementing every statistical module that appears across the PHO audit family: fixed-effects OLS with jackknife inference, ridge and elastic-net nested cross-validation, PCG32/xorshift wild cluster bootstrap, grouped split conformal calibration, covariance PCA with farthest-first k-means, exhaustive source/time perturbation with Shapley attribution, difference GMM mediation, and partial-R2 sensitivity surfaces
- Formatting output exactly to an answer template, applying controlled decision rules

**What this skill does not cover**

It does not contain task-specific solved values (coefficients, p-values, cohort sizes) from any prior audit. All entities, measures, years, filters, hyperparameter grids, random seeds, and decision thresholds come from the current request. It does not require or assume a `protocol_registry_record` in the request input; when one is absent, build directly from the request.

---

## General Workflow

1. Read `prompt.txt`, `analysis_request.json`, and `answer_template.json` from the task input.
2. Resolve the portal base URL: the prompt contains `<TASK_ENV_BASE_URL>` as a placeholder. Replace it with the actual environment base URL. If the env var `TASK_ENV_BASE_URL` is set, use that; otherwise inspect the running environment for the portal address.
3. Query the portal endpoints to fetch all necessary publication records.
4. Apply release resolution: filter by effective status, source, value type, validity, and geography; select greatest revision, then latest release timestamp, then lowest record identifier.
5. Construct the analytic cohorts specified by the request.
6. Execute each audit module in declared order, respecting every checkpoint, seed, and reproducibility constraint.
7. Apply numerical precision rules, ordering rules, and identifier conventions.
8. Evaluate decision gates on unrounded values and produce the final classification.

---

## Portal API

See [references/portal_api.md](references/portal_api.md) for the full endpoint reference.

The base URL resolves to an HTTP server. All endpoints accept GET. Response bodies are JSON arrays of objects.

Key endpoints used across all tasks:

| Endpoint | Purpose |
|---|---|
| `GET /catalog` | Schema catalog with measure_ids, value_types, source_types, geographic scope |
| `GET /geographies/states` | U.S. state geography records |
| `GET /geographies/counties` | U.S. county geography records (includes `state_abbr`, `rucc`, `census_division`) |
| `GET /geographies/countries` | Country geography records (includes `iso3`, `label`, `region`) |
| `GET /data/state-health` | State-level health indicators |
| `GET /data/state-socioeconomic` | State-level socioeconomic data |
| `GET /data/county-health` | County-level health indicators |
| `GET /data/county-socioeconomic` | County-level socioeconomic data |
| `GET /data/country-indicators` | Country-level burden and health indicators |
| `GET /data/revisions` | Revision event records (`revision_event_id`, `status`, `applies_to`) |
| `GET /methodology` | Methodological notes |
| `GET /health` | Service health check |

When fetching data, filter client-side by the effective request bindings (measure, years, geography, release status, value type, source type). For health data, fields include `measure_id`, `year`, `state_abbr` (or `county_fips` / `iso3`), `value`, `value_type`, `source_type`, `release_status`, `revision`, `released_at`, `observation_id` / `record_id`, `sample_size`, and `quality_flag`. For socioeconomic data, similar fields with `poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`, `uninsured`, `region`, etc.

---

## Release Resolution

This is the universal first step for every task. See [references/release_and_cohorts.md](references/release_and_cohorts.md).

1. Filter records by the effective request's `release_status` (typically `FINAL`), `value_type` (e.g. `AGE_ADJUSTED`, `CRUDE`), and `source_type` (e.g. `DIRECT_SURVEY`, `COUNTY_ROLLUP`).
2. For each unique entity-time-measure key, select one record using this precedence:
   - Greatest `revision` number
   - Then latest `released_at` timestamp
   - Then lowest `observation_id` / `record_id`
3. Records with suppressed, invalid, withdrawn, blank, or null analytic values are *publication evidence* (they count toward selected-publication totals when requested) but are *analytically unavailable* and are never zero-filled.
4. Discard records with `quality_flag` values matching any declared `invalid_quality_flags` (e.g. `INVALID_SCALE`, `INVALID`, `WITHDRAWN`).

---

## Cohort Construction

See [references/release_and_cohorts.md](references/release_and_cohorts.md).

After release resolution, join independently resolved series by stable entity and time keys. Construct cohorts from the effective completeness predicates:

- **Complete case**: All required analytic fields are non-suppressed, non-null, and valid.
- **Primary/Reference cohort**: Complete in the effective reference year.
- **Balanced panel cohort**: Complete in every requested year.
- **Broad cohort**: Complete for outcome and all ordered features in the reference year.
- **Strict dual-source cohort**: Complete for outcome, primary exposure, parallel exposure, and all adjustments in every year.
- **Machine-learning cohort**: Primary-cohort members also complete for additional declared fields.

Preserve entity-code then time order throughout. State/county/country codes must be the stable identifiers from the portal (uppercase two-letter state codes, five-digit FIPS county codes, uppercase three-letter ISO3 country codes).

---

## Statistical Modules

Each audit module specifies a `method` and `required_evidence`. Implement the method exactly as described in the request, binding all design parameters (predictors, features, groups, grids, seeds, quantiles) from the request. The sections below document the reusable method patterns that recur across protocols. Detailed specifications are in the referenced files.

### Fixed-Effects OLS with Delete-One Jackknife

[references/fixed_effects_jackknife.md](references/fixed_effects_jackknife.md)

Double-demean each variable (subtract entity mean, subtract time mean, add grand mean), fit OLS without an intercept in declared predictor order. For each cluster deletion, remove the entire cluster, recompute all means, and refit. Jackknife inference uses the standard bias-correction formula. The test uses Student-t with G-1 degrees of freedom.

### Ridge Regression with Nested CV

[references/ridge_regression.md](references/ridge_regression.md)

Hold-out outer folds by group. Within each outer training set, hold out each remaining group for inner validation. For every fit: subtract training-only feature means, divide by training sample SD (ddof=1), center the outcome, keep the intercept unpenalized. Solve by cyclic coordinate descent in feature order, initializing coefficients to zero. Stop when max coefficient change falls below tolerance or at the sweep cap. Select lambda by smallest inner RMSE, tie-broken by smaller penalty. Pool outer predictions row-wise for RMSE, MAE, and Q-squared.

### Elastic Net with Nested CV

[references/elastic_net.md](references/elastic_net.md)

As ridge, but with an L1 penalty term. Minimize weighted SSE/(2n) + lambda * [alpha * sum|b_j| + (1-alpha) * sum(b_j^2)/2]. The coordinate update applies soft-thresholding: b_j = S(rho_j, lambda*alpha) / (1 + lambda*(1-alpha)) where S(a,t) = sign(a) * max(|a|-t, 0). Cold-start all coefficients at zero. Select by smallest RMSE, then smaller alpha, then smaller l1_ratio. Report nonzero counts using the effective numerical cutoff.

### Wild Cluster Bootstrap

[references/wild_cluster_bootstrap.md](references/wild_cluster_bootstrap.md)

**PCG32 variant**: Use unsigned 64-bit wraparound. increment = 2*stream + 1. Initialize state to 0, advance, add seed modulo 2^64, advance. Each advance: old=state, state = old*6364136223846793005 + increment mod 2^64, output from xorshift and rotate on old. Map modulo 6 to [-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)].

**XORSHIFT32 variant**: Unsigned 32-bit state. Each call: x ^= x<<13, x ^= x>>17, x ^= x<<5, masking to 32 bits after each xor. Map low bit 1 to +1, 0 to -1.

For both: fit the full model, compute CR1 cluster-robust standard errors, studentize the target coefficient. Fit the restricted model (without target), generate synthetic y* = restricted_fit + restricted_residual * cluster_weight, refit full model, recompute. Count |t*| >= |t_obs| (with comparison tolerance if specified). plus-one p = (count+1)/(B+1). For quantiles, use nearest-rank (type 1) or type-7 interpolation as declared.

### Grouped Split Conformal Calibration

[references/conformal_inference.md](references/conformal_inference.md)

For each ordered outer group: use it as test, select a calibration group from remaining (by greatest row count then ascending name), use the rest for proper training. Fit the model from scratch with the effective penalty. Sort absolute calibration residuals, compute threshold q = score[r] where r = min(m, ceil((m+1)*(1-alpha))) using one-based indexing. Intervals are prediction +/- q, inclusive. Aggregate coverage and width weighted by outer test row counts.

### PCA and Trajectory Clustering

[references/pca_clustering.md](references/pca_clustering.md)

Build columns in effective variable-major/time order. Standardize by sample SD. Form C = Z'Z/(n-1). Diagonalize by symmetric Jacobi: select the largest absolute upper-triangle off-diagonal (tie: lower row then column), compute rotation, apply, and iterate to tolerance or cap. Order eigenvalues descending (tie: original diagonal index). Flip each eigenvector so its earliest maximum-absolute entry is positive. Scores = Z * loadings.

Cluster with squared-Euclidean k-means. Initialize: first center is the ASCII-first entity; each next center is the entity maximizing distance to its nearest existing center (tie: entity code). Assign to nearest center (tie: lower cluster id). Update centers as member means. Stop when assignments are unchanged or at the iteration cap. Handle empty clusters by reassigning the farthest-from-center entity.

Stability: for each omitted time/state block, rebuild scaling, PCA, initialization, and clustering. Compare full and refit labels via adjusted Rand index. Align refit labels by the permutation maximizing agreement (tie: lexicographically smallest mapped-id vector).

### Source/Year Perturbation

[references/source_perturbation.md](references/source_perturbation.md)

Enumerate time subsets or source-replacement bitmasks. For each, refit the model from scratch. Compute absolute percent shift from baseline. Report stratum summaries and select the worst by greatest unrounded shift (tie: earlier order). For Shapley attribution: phi_j = sum_{S not containing j} |S|! * (m-|S|-1)! / m! * [b(S U {j}) - b(S)]. Verify that sum(phi) = b(all) - b(none) within numerical tolerance.

### Difference GMM Mediation

[references/gmm_mediation.md](references/gmm_mediation.md)

Create adjacent-change rows in entity then end-period order. Residualize outcome, dynamic regressors, and instruments against baseline terms. First-step: g(theta) = Z'(y - D theta)/n with identity weight. Second-step: W = Moore-Penrose inverse of S = sum_g(Z_g' u_g u_g' Z_g)/n. Apply declared relative singular-value cutoff to pseudoinverses. For indirect theta = a*b, use Var(theta) = b^2*Var(a) + a^2*Var(b) + 2ab*Cov(a,b) with the cross-equation covariance term. Hansen J = n * g(theta)' W g(theta).

### Partial-R2 Mediation Sensitivity

[references/sensitivity_surface.md](references/sensitivity_surface.md)

From baseline path-a coefficient a, path-b coefficient b, SE_b, and residual df: magnitude = SE_b * sqrt(df * rY * rM / (1 - rM)). For each direction: adjusted_b = b - sign * magnitude, adjusted_indirect = a * adjusted_b, adjusted_direct = total - adjusted_indirect, proportion = adjusted_indirect / total. Enumerate the R2 grid in declared order. Compute the equal-strength positive tipping root numerically.

---

## Output Formatting

The answer template defines the exact JSON structure. Follow these rules universally:

- **Numeric precision**: Round non-integer reported statistics to the declared decimal places (typically 4 or 6). Encode as JSON numbers. Do not preserve trailing zeros beyond what JSON requires.
- **Integers**: Counts, ranks, fold numbers, seeds, PRNG states, and replicate numbers are natural JSON integers.
- **Missing values**: Use JSON `null` when a statistic is mathematically unavailable (e.g. from a degenerate case). Never use `NaN`, `Infinity`, or string placeholders.
- **Identifiers**: Use the portal's stable codes exactly: uppercase two-letter state abbreviations, five-digit county FIPS, uppercase ISO3 country codes, and portal division/region names verbatim.
- **Ordering**: Preserve every formal order declared in the request or template. Do not sort an aligned result array independently. Entity code and time orders are stable across modules.
- **Booleans**: Use JSON `true`/`false` for gate evaluations and binary flags.
- **Enum values**: Use exactly the string values listed in the template.

---

## Decision Rules

Complete every module before evaluating any gate. Evaluate each business predicate on **unrounded** values (the full-precision computed results, not the rounded reported values). Gates typically take the form of threshold comparisons: "coefficient is negative", "p-value <= 0.05", "R-squared >= 0.85", "coverage >= 0.80", "ARI >= 0.75", etc.

Apply the effective request's classification precedence:
- Walk the ordered flag list in declared order.
- Count how many gates pass.
- Match against the classification rules (e.g. "all six pass", "at least four pass", "otherwise").
- Select the first matching class in precedence order.

For "first failed module" reporting: evaluate gates in the declared precedence order; the first module whose predicate fails is the first failed module. If none fail, report `NONE` or the equivalent sentinel.

---

## Reference Files

Detailed specifications for each module family are in the `references/` directory:

| File | Covers |
|---|---|
| [portal_api.md](references/portal_api.md) | Full endpoint reference, field schemas, query patterns |
| [release_and_cohorts.md](references/release_and_cohorts.md) | Release resolution, revision precedence, cohort construction |
| [linear_algebra.md](references/linear_algebra.md) | WLS with weights, HC3 heteroskedasticity-robust SE, CR1 cluster-robust SE |
| [fixed_effects_jackknife.md](references/fixed_effects_jackknife.md) | Double-demeaning, delete-one jackknife, bias correction |
| [ridge_regression.md](references/ridge_regression.md) | Training-only standardization, cyclic coordinate descent, nested CV |
| [elastic_net.md](references/elastic_net.md) | Weighted elastic net, soft-threshold updates, grid selection |
| [wild_cluster_bootstrap.md](references/wild_cluster_bootstrap.md) | PCG32 and XORSHIFT32 PRNG, restricted-null bootstrap, CR1 inference |
| [conformal_inference.md](references/conformal_inference.md) | Grouped split conformal, calibration, rank-based thresholds |
| [pca_clustering.md](references/pca_clustering.md) | Covariance PCA via Jacobi, farthest-first k-means, adjusted Rand index |
| [source_perturbation.md](references/source_perturbation.md) | Exhaustive enumeration, Shapley attribution, shift aggregation |
| [gmm_mediation.md](references/gmm_mediation.md) | Two-step GMM, delete-cluster diagnostics, indirect effect inference |
| [sensitivity_surface.md](references/sensitivity_surface.md) | Partial-R2 sensitivity, tipping-point computation |

