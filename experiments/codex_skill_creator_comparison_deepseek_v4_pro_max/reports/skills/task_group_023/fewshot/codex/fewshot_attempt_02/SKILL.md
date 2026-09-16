---
name: pho-audit
description: Execute Public Health Observatory algorithmic audits from registered protocol specifications. Use when Codex needs to resolve evidence from the PHO task-environment portal, construct epidemiologic cohorts, implement statistical modules (fixed-effects, ridge, elastic net, GMM, conformal inference, wild cluster bootstrap, PCA clustering, sensitivity analysis, source perturbation), and apply controlled decision rules. Supports PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_STATE_ROBUSTNESS_TRANSPORT_V1, PHO_COUNTY_PANEL_TRANSPORT_V1 protocols, and custom country-level audits.
---

# PHO Audit — Public Health Observatory Algorithmic Audit Execution

## Overview

This skill teaches Codex to execute Public Health Observatory algorithmic audits end-to-end: resolve evidence through the PHO portal API, construct analytic cohorts under registered release-and-completeness rules, implement statistical modules from modular protocol profiles, and apply controlled business decision predicates.

**Before starting, read these references:**

- [portal_api.md](references/portal_api.md) — PHO portal endpoint catalog, release resolution, revision priority, geography hierarchies
- [statistical_methods.md](references/statistical_methods.md) — Reusable statistical building blocks referenced by all protocols

## Core Workflow

Every audit follows the same pattern:

1. **Activate the protocol profile.** Each request carries a `protocol_id`. Read the request, identify the protocol, and activate the matching reusable method profile. Bind all task-local values (entities, measures, time coordinates, sources, random seeds, hyperparameter grids, business cutoffs, output labels) from the effective request. The instance boundary is strict: method semantics only; never carry task-local solved values across invocations.

2. **Resolve overrides.** Build one effective request: start from the registered method profile, then deeply merge explicit overrides from the request. Direct root keys target identically-named canonical keys. Keys named `<section>_overrides` target canonical `<section>`; `module_overrides.<module_name>` targets that exact top-level module. Strip only the terminal `_overrides` suffix. Objects merge by exact key recursively; arrays replace whole (never concatenate or union); scalars/strings/Booleans replace only at exact path; absent paths inherit unchanged. Reject unknown targets, implicit renames, type coercion, and incompatible types before evidence resolution. Task-local direct bindings and resolved overrides take precedence over inherited values at the same path. Freeze one contract before any computation.

3. **Execute module order.** Run modules in the declared execution order. Each module consumes the outputs of earlier modules when required (cohort definitions, pooled metrics, outer predictions). Complete each module fully before starting the next.

4. **Collect all required evidence.** Every module has required output keys declared by the request or answer template. Collect them all with the declared precision, list orders, and identifier formats. Preserve state-code and division/region ordering exactly as resolved.

5. **Apply the decision rule.** Evaluate every business predicate on unrounded values. Complete all modules first, then evaluate gates in declared precedence order. Apply the controlled decision mapping from the effective request. Use only the valid enum values from the request or answer template.

## Protocol Profiles

### PHO_STATE_TRANSPORT_AUDIT_V1 — State longitudinal transportability

**Trigger:** `protocol_id` equals ` PHO_STATE_TRANSPORT_AUDIT_V1`.

**Geography:** All 50 states and DC. **Sources:** `/data/state-health`, `/data/state-socioeconomic`. **Answer template:** Includes `publication_cohort`, six audit modules, `robustness_decision`.

**Module execution order:**

1. **release_resolution_and_cohorts** — Filter each publication key by effective status, source, value type, and validity flags. Select greatest revision, then latest release timestamp, then lowest record identifier. Suppressed, invalid, withdrawn, blank, or null analytic values are unavailable and never zero-filled. Count selected publications before analytic completeness exclusions when requested. Join independently resolved series by stable entity and time keys. Construct each complete, balanced, broad, or dual-source analytic set from its effective required fields; preserve entity-code then time order, and every declared feature and group order.

2. **delete_cluster_fixed_effects** — On every fit transform each modeled variable as `z_it` minus its active entity mean minus its active time mean plus its active grand mean, then solve OLS without an intercept in declared predictor order. A deletion removes the whole cluster, recomputes every mean, and refits from scratch in entity-code order. For `G` delete estimates `b_-g` and mean `bbar`, `SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))` and `b_BC = G*b - (G-1)*bbar`. Test uses `b/SE_JK` with two-sided Student-t and `G-1` degrees of freedom. Select extrema by coefficient value, then entity code.

3. **nested_ridge_division_cv** — Hold out one ordered group per outer fold; within each outer training set hold out every remaining group once in the same order. For every fit, subtract training-only feature means and divide by training sample SD with ddof one, then apply those moments to validation or test rows. Center the training outcome, keep intercept unpenalized, initialize coefficients to zero, and cycle in declared feature order minimizing `mean((y-a-Xb)^2) + lambda*sum_j(b_j^2)`. Update `b_j = sum_i x_ij * r_ij / (sum_i x_ij^2 + n*lambda)` where `r` excludes feature `j`. Stop after a full sweep when max coefficient change is below tolerance or at the sweep cap. For each penalty pool all inner validation squared errors at row level, take RMSE, choose smallest RMSE then smaller penalty, refit on all outer-training rows, and predict all outer rows. Pool exactly one outer prediction per eligible row; compute RMSE, MAE, and `Q^2 = 1 - pooled_SSE / full_sample_SST`.

4. **wild_cluster_bootstrap** — PCG32-based wild cluster bootstrap-t. Initialize 64-bit state with `increment = 2*stream + 1`; advance then add seed modulo `2^64`. Each advance: `state = old * 6364136223846793005 + increment` modulo `2^64`; `xorshifted = low32(((old >> 18) xor old) >> 27)`; `rot = old >> 59`; output = `rotate_right_32(xorshifted, rot)`. Map output modulo six to weights `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`. Use same double-demeaned matrix as FE module. For cluster scores `s_g = X_g' e_g`, `V_CR1 = [G/(G-1)]*[(n-1)/(n-k)]*(X'X)^(-1)*sum_g(s_g*s_g')*(X'X)^(-1)`. Studentize target, fit restricted model without target, retain fitted values and residuals. Maintain one continuous generator; draw once per cluster in entity-code order per replicate; `y* = restricted_fit + restricted_residual * cluster_weight`; refit unrestricted; recompute CR1; studentize. Checkpoints recorded after completed replicate. Count `abs(t*) >= abs(t_observed)`; p = `(1+count)/(1+B)`. Nearest-rank quantiles: `x[min(B, ceil(p*B)) - 1]` (one-based).

5. **grouped_split_conformal** — For each ordered outer group, use it as test; among remaining groups choose calibration by greatest row count then ascending group name; use all others for proper training. Fit ridge from scratch with effective fixed penalty and identical training-only scaling and solver rules. Sort `m` absolute calibration residuals. With effective miscoverage `alpha`, use one-based `r = min(m, ceil((m+1)*(1-alpha)))` and `q = score[r]`. Intervals prediction plus or minus `q` are inclusive. Report fold coverage, width, MAE, and aggregate coverage and width by outer-test row counts.

6. **trajectory_pca_clustering** — Build columns in effective variable-major/time order, standardize by active-column sample SD, and form `C = Z'Z/(n-1)`. Symmetric Jacobi: select largest absolute upper-triangle off-diagonal, tying by lower row then column; `tau = (Aqq-App)/(2*Apq)`; `t = sign_nonnegative(tau)/(abs(tau)+sqrt(1+tau^2))`; `c = 1/sqrt(1+t^2)`; `s = t*c`; rotate A and eigenvectors; stop at off-diagonal tolerance or step cap. Order components by descending eigenvalue then original diagonal index; flip each loading so earliest maximum-absolute entry is positive; scores = Z times loadings. Deterministic farthest-first k-means on leading scores: first center is ASCII-first entity; each next is entity maximizing distance to nearest center, tied by entity code. Assign to nearest center, tied by lower working id; update by member means; stop when assignments unchanged or at cap. Canonicalize final ids by centroid coordinates then working id. For each omitted time block in ascending order, rebuild scaling, PCA, orientation, initialization, and clustering. Adjusted Rand index: `(sum_ij C(n_ij,2) - expected) / (0.5*(sum_i C(a_i,2) + sum_j C(b_j,2)) - expected)` where `expected = sum_i C(a_i,2)*sum_j C(b_j,2)/C(n,2)`. Align refit labels by maximum agreement, tying to lexicographically smallest permutation.

7. **source_year_perturbation** — Enumerate effective time subsets by increasing requested subset size and lexicographic tuple order. Keep strict analytic set unchanged. For each subset refit complete double-demeaned model separately with primary and parallel series, recomputing CR1 and two-sided `G-1`-df inference for each fit. For baseline coefficient `b` and alternate `b_alt`, `shift = abs(b_alt - b)/abs(b)*100`; same-sign requires both nonzero with identical sign. Compute ordinary median of ordered shifts. Choose worst by greatest unrounded shift, then earlier subset order.

8. **controlled_decision** — Complete every module. Evaluate every effective business predicate on unrounded values. Preserve listed module order for gate reporting. Count satisfied predicates and apply only the effective request's controlled decision mapping and precedence rules.

### PHO_COUNTY_MEDIATION_TRANSPORT_V1 — County mediation audit

**Trigger:** `protocol_id` equals `PHO_COUNTY_MEDIATION_TRANSPORT_V1`.

**Geography:** Midwest and South census regions. **Sources:** `/data/county-health`, `/data/county-socioeconomic`, `/geographies/counties`. **Answer template:** Includes `cohort_audit`, seven audit modules, `controlled_conclusion`.

**Module execution order:**

1. **publication_and_linked_cohorts** — Filter each publication by effective filters; select best record per county-year-measure using ordered revision priority. Count selected publications before completeness exclusions. Construct primary (reference-year complete), balanced-panel (complete in all years), and machine-learning (extended completeness) cohorts.

2. **primary_mediation_models** — Build total-effect, path-a, and direct/path-b OLS designs from effective exposure, mediator, outcome, covariates, transformations, references, and column order. These unrounded fitted objects are the shared source for downstream bootstrap and sensitivity modules.

3. **difference_gmm_mediation** — Create adjacent-change rows in entity then end-period order using effective lag structure and equation bindings. For each equation `W = (Z'Z)^(-1)` and `beta = (X'Z W Z'X)^(-1) X'Z W Z'y`. With residual `u` and cluster score `q_g = Z_g' u_g`, use registered finite-sample cluster sandwich; for two equations use corresponding cross-cluster score product. For indirect `theta = a*b`, `Var(theta) = b^2*Var(a) + a^2*Var(b) + 2ab*Cov(a,b)`, with Student-t inference at cluster degrees of freedom. First-stage partial F from full-versus-reduced RSS using effective instrument counts. For every delete-state diagnostic, rebuild rows and refit all affected equations from scratch in state order.

4. **nested_state_ridge** — Use effective feature arrays in exact order. Within every fit, standardize from training arithmetic means and population SDs, with unit divisor for zero variance. Fit ridge with unpenalized intercept minimizing training SSE + lambda times squared non-intercept norm. Outer: leave one state out; inner: leave one state out. Pool county squared errors before RMSE. Select smallest unrounded inner RMSE, breaking equality toward smaller penalty; refit on all outer-training rows. Aggregate OOF metrics from single prediction per eligible row.

5. **paired_state_wild_bootstrap** — For each target, fit restricted model with that target removed; form synthetic outcomes from restricted fitted values plus cluster-weighted restricted residuals; refit unrestricted models and recompute CR1 t statistics. Use unsigned xorshift32: `x ^= x<<13`, `x ^= x>>17`, `x ^= x<<5`, masking to 32 bits after each operation. Map odd state to +1, even to -1. Maintain one continuous stream; draw once per state in ascending order per replicate; reuse same state sign across paired equations. Two-sided absolute exceedances: `p = (count+1)/(B+1)`. Nearest-rank order statistics for declared probabilities and bootstrap-t inversion with observed standard error. Record checkpoints after listed replicate is complete.

6. **state_grouped_conformal** — Index states in ascending order and assign cyclic partitions by index modulo effective partition count. For each test partition, use registered preceding calibration partition and remaining partitions for proper training. Reduce calibration residuals to one maximum absolute residual per calibration state. `k = min(m, ceil((m+1)*coverage))` and use one-based k-th state maximum. Build symmetric inclusive intervals; aggregate county coverage and width by cycle and state, using declared order for worst-state selection.

7. **partial_r2_sensitivity** — From unrounded baseline `a`, `b`, `SE_b`, and residual `df`, compute `magnitude = SE_b * sqrt(df * rY * rM / (1-rM))`. For each declared direction, `adjusted_b = b - s*magnitude`, `adjusted_indirect = a*adjusted_b`, `adjusted_direct = total - adjusted_indirect`, `proportion = adjusted_indirect/total`. Enumerate complete effective surface in declared R2 and direction order. Compute equal-strength positive tipping root from unrounded inputs: the R2 value where `b - magnitude(R2) = 0`.

8. **state_trajectory_pca_clustering** — Aggregate effective balanced-panel measures to state-period means in declared feature order. Standardize across states with sample SDs; covariance = `Z'Z/(G-1)`. Sort eigenpairs descending; orient eigenvectors so earliest maximum-absolute loading is positive; score with oriented loadings. Deterministic farthest-first Lloyd k-means with effective cluster count, lower cluster id on assignment equality, arithmetic centroid updates, unchanged-label plus registered center-tolerance convergence. For every leave-period stability fit, rebuild standardization, PCA orientation, seeds, and clusters from scratch; compare labels with adjusted Rand index.

9. **controlled_precedence** — Complete every evidence module. Evaluate effective business predicates on unrounded values. Count satisfied gates and return first applicable controlled class in effective precedence order.

### PHO_STATE_ROBUSTNESS_TRANSPORT_V1 — State reliability-weighted audit

**Trigger:** `protocol_id` equals `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`.

**Geography:** All 50 states and DC. **Sources:** `/data/state-health`, `/data/state-socioeconomic`. **Answer template:** Includes `release_and_cohort`, six audit modules, `decision_audit`. Uses reliability-weighted WLS throughout.

**Module execution order:**

1. **release_and_cohort** — Filter publications, construct primary and balanced cohorts. Keep direct-record outcome `sample_size` as fixed positive reliability weight, preserved even during source perturbations.

2. **common_weighted_linear_algebra** — WLS: `Xw = diag(sqrt(w))*X`, `yw = diag(sqrt(w))*y`, `b = (Xw'Xw)^(-1)*Xw'yw`. HC3: `h_i = diag(Xw*(Xw'Xw)^(-1)*Xw')`, `ew_i = sqrt(w_i)*(y_i - X_i*b)`, `V_HC3 = (Xw'Xw)^(-1)*Xw'*diag(ew_i^2/(1-h_i)^2)*Xw*(Xw'Xw)^(-1)`. CR1: for ordered clusters `g` and `s_g = Xw_g'*ew_g`, `V_CR1 = [G/(G-1)]*[(n-1)/(n-k)]*(Xw'Xw)^(-1)*sum_g(s_g*s_g')*(Xw'Xw)^(-1)`.

3. **cluster_jackknife** — Fit full weighted design, then delete every registered cluster in order and refit unchanged design from scratch. `b_BC = G*b - (G-1)*bbar`. Percent change = `100*abs((b_-g - b)/b)`. Choose greatest unrounded change, tied by earlier cluster. `SE_JK = sqrt((G-1)/G*sum_g((b_-g - bbar)^2))`. Test `b_BC/SE_JK` two-sided with `G-1` df.

4. **nested_elastic_net** — Hold out each registered cluster as outer fold and each remaining cluster as ordered inner fold. Build effective raw, transformed, squared, and interaction features in declared order. Standardize only from training moments (weighted mean, weighted population SD). Center y by training weighted mean. Minimize `sum(w_i*(y_i-Z_i*b)^2)/(2*sum(w_i)) + lambda*[alpha*sum|b_j| + (1-alpha)*sum(b_j^2/2)]`. Cold-start at zero. Cyclic coordinate descent: `rho_j = sum(w_i*Z_ij*(y_i-sum_{l!=j}Z_il*b_l))/sum(w_i)`; `b_j = S(rho_j, lambda*alpha)/(1+lambda*(1-alpha))` with `S(a,t) = sign(a)*max(|a|-t,0)`. Stop at max-change tolerance or cycle cap. Select smallest inner RMSE then smaller penalty. Recompute nonzero count with effective cutoff. Pool outer metrics in entity order; R2 uses full-sample unweighted mean.

5. **wild_cluster_bootstrap** — Studentize full weighted target coefficient with CR1. Fit weighted restricted model without target; retain untransformed fitted values and residuals. xorshift32 PRNG: `x ^= x<<13`, `x ^= x>>17`, `x ^= x<<5`, mask to 32 bits after each. One continuous stream; draw once per cluster in registered order; map low bit one to +1, otherwise -1. `y* = restricted_fit + restricted_residual*cluster_sign`; refit full WLS; recompute CR1; record absolute studentized target. Record checkpoints after completed replicate. Count `t* >= t_observed` with effective tolerance; `p = (1+count)/(1+B)`. Type-seven quantile: `h = (B-1)*p`, `j = floor(h)`, `gamma = h-j`, `(1-gamma)*x[j] + gamma*x[j+1]` (zero-based).

6. **grouped_conformal** — Reuse each outer elastic-net prediction and its selected penalty. For outer cluster `d`, hold out each other training cluster once; cold-refit identical weighted elastic-net on remaining clusters; predict held-out calibration rows; pool absolute residuals. `r = min(m, ceil((m+1)*c))` and radius `q = score[r]`. Inclusive intervals. Report ordered cluster diagnostics; pool covered and row counts; weight mean width by held-out count. Worst coverage by smallest fraction then earlier cluster.

7. **trajectory_pca_clustering** — Build variable-major/time-major blocks in declared order and entity ASCII order. Standardize each column by sample SD. Covariance `C = Z'Z/(n-1)`. Eigendecompose, orient eigenvectors, score. Deterministic farthest-first Lloyd k-means. For empty cluster ids in order, move ASCII-first entity among those farthest from assigned center. For every omitted time block, delete complete variable block; rebuild scaling, PCA orientation, initialization, clustering. Adjusted Rand index. Align by permutation with maximum matches, tied lexicographically.

8. **exhaustive_source_perturbation** — Resolve alternate outcomes with effective release filters and priority. Order paired entities by descending absolute alternate-minus-primary difference, tied by entity code. For each mask from zero through `2^m-1`, replace entity `j` iff `mask & (1<<j)` is nonzero; retain fixed direct reliability weights and design; refit WLS and HC3. `shift = 100*abs((b_mask - b_zero)/b_zero)`. For each popcount stratum report scenario count, coefficient range, HC3 p-value range, and mean shift. Maximum shift by greatest unrounded shift tied by smaller mask. Exact Shapley: `phi_j = sum_{S not containing j} |S|!*(m-|S|-1)!/m! * [b(S union {j}) - b(S)]`. Verify `sum(phi_j) = b(all) - b(none)`.

9. **controlled_decision** — Complete every module. Evaluate effective business predicates on unrounded values. Select first unsatisfied module in precedence order. Apply effective request's controlled output mapping.

### PHO_COUNTY_PANEL_TRANSPORT_V1 — County dynamics panel audit

**Trigger:** `protocol_id` equals `PHO_COUNTY_PANEL_TRANSPORT_V1`.

**Geography:** West and Northeast census regions. **Sources:** `/data/county-health`, `/data/county-socioeconomic`. **Answer template:** Includes `cohort_and_state_census`, six audit modules, `decision`.

**Key pattern:** Constructs a county-level change-panel with lagged levels, dynamic changes, RUCC ordinal indicators, and end-period dummies. Panel end years define change periods.

**Module execution order:**

1. **publication_balanced_panel** — Filter effective county health and socioeconomic sources independently; resolve one final record per declared key using effective release priority. Suppressed, invalid, or missing values are incomplete, never zero. Retain entities complete across every effective balanced period with valid geography attributes. Create adjacent-change rows ordered by entity identifier then end period; derive lagged levels, dynamic changes, reference indicators, and interactions in declared order.

2. **delete_state_two_step_gmm** — Within every full or delete-state fit, residualize outcome, dynamic regressors, and instruments against intercept plus effective baseline terms. First-step moments: `g(theta) = Z'(y - D theta)/n` with identity weight. State scores: `s_g = Z_g' u_g`; `S = sum(s_g s_g')/n`; second-step weight is registered Moore-Penrose inverse of `S`. Second-step `theta` from weighted linear moments; Hansen `J = n*g(theta)'Wg(theta)`. Apply registered relative singular-value cutoff to every pseudoinverse. Refit both steps after each state deletion in state order. `theta_bc = G*theta_full - (G-1)*mean(theta_delete)`. Retain maximum absolute delete-state shifts.

3. **state_blocked_nested_elastic_net** — Allocate states by descending retained-entity counts, assigning each to currently smallest fold and using lower fold id on equality; sort state codes within folds; repeat inside each outer-training set. Standardize declared continuous columns from training population moments; leave indicators unchanged; keep intercept unpenalized. Minimize `SSE/(2n) + alpha*(rho*sum|beta_j| + 0.5*(1-rho)*sum(beta_j^2))`. Cold-start coefficients at zero and intercept at training outcome mean. Cyclic sweep: update intercept by mean residual; `beta_j = soft_threshold(mean(x_j*r_partial), alpha*rho) / (mean(x_j^2) + alpha*(1-rho))` in declared coefficient order. Stop at max-change tolerance or sweep cap. Traverse grid in declared outer/inner order. Pool inner squared errors before RMSE; select by smallest unrounded RMSE, then smaller alpha, then smaller l1_ratio. Refit outer models and pool OOF metrics.

4. **state_wild_cluster_bootstrap_t** — Fit full unpenalized OLS and state-cluster CR1 for target. Fit restricted model without target; synthetic outcomes from restricted fitted values plus state-weighted restricted residuals. xorshift32 with shifts 13, 17, 5; mask to 32 bits after each xor. One continuous stream; draw states in ascending order; odd maps to +1, even to -1. Refit full model and recompute CR1 each replicate. Absolute-tail exceedances: `p = (count+1)/(B+1)`. Nearest-rank order statistics at effective probabilities. Record each requested checkpoint after completing state draws and t statistic.

5. **cross_fold_grouped_conformal** — Use outer OOF predictions in original analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds. `r = min(m, ceil((m+1)*coverage))`; symmetric inclusive intervals. Report fold, state, effective RUCC-band, and rank-defined prediction-bin diagnostics. Assign prediction bins after sorting by prediction then declared tie-breaker identifiers. Signed gap = prediction mean minus observation mean. Use unrounded group coverages for minima and decision predicates; round only reported fields.

6. **county_trajectory_pca_clustering** — Build variable-major entity trajectories in declared variable and end-period order. Standardize each feature by population moments; covariance = `Z'Z/n`. Sort eigenpairs descending; orient loadings so earliest maximum-absolute element is positive; use effective retained scores. For each effective candidate k, initialize at smallest entity id then add point farthest from nearest center, breaking by entity id. Assign equality to lower cluster id; update arithmetic centers until unchanged labels and registered center tolerance or iteration cap. Euclidean silhouette with singleton value zero; select largest unrounded mean silhouette, then smaller k. For each state deletion, rebuild full trajectory pipeline at selected k; compare retained labels with adjusted Rand index.

7. **source_group_perturbation** — For every source group and outer fold in declared order, remove exactly the group terms and reuse that fold full-model selected hyperparameters without retuning. Apply same remaining-term preprocessing and solver; retain all outer-fold RMSEs; pool squared errors; subtract full-model OOF RMSE for deterioration. Count folds worse than corresponding full-model folds. Rank groups by decreasing unrounded deterioration, then declared group order.

8. **controlled_precedence** — Complete all evidence modules. Evaluate effective gates on unrounded values. Return first applicable controlled decision in effective precedence order.

### Custom country-level audits

When a request lacks a `protocol_id` but involves country health indicators:

1. **Reconciliation:** Resolve requested labels against country portal names. Many labels are aliases (e.g., "Republic of X", "X Federation", "X Isles"). Match by `/geographies/countries` endpoint. Report requested label count, resolved count (unique ISO3), and alias resolution count (labels differing from canonical country name). Return resolved ISO3 identifiers sorted ascending.

2. **Quality audit:** Query `/data/revisions` to identify applied and non-applied revision events by their `revision_event_id` and `event_type`. Apply relevant revisions. Query `/data/country-indicators` for the requested burden indicators in the reference year. Detect unresolved scale-break anomalies from the portal response. Impute missing cells after quality exclusions. Count raw missing, anomaly, and imputed cells.

3. **PCA:** Standardize usable indicator columns to zero mean and unit variance. Compute covariance matrix; eigendecompose. Retain components with eigenvalues above threshold. Report PC1 variance fraction and top 3 absolute loadings.

4. **Clustering:** Run k-means (k = 2, 3, 4, 5) on PC scores. Compute silhouette coefficient for each k. Select best k by largest mean silhouette. For three-cluster solution, label clusters LOW_BURDEN, MIDDLE_BURDEN, HIGH_BURDEN by ascending PC1 centroid mean. Report sizes and high-burden ISO3 set sorted ascending.

5. **Panel model:** Build region-fixed-effects panel joining multiple years of life_expectancy against PC1 burden score. Report coefficient, standard error, p-value, R-squared, and whether region fixed effects were included.

6. **Advisory:** `PRIORITIZE_HIGH_BURDEN_CLUSTER` if PC1 coefficient is significantly negative (p < 0.05). `MONITOR_GRADIENT` if coefficient is negative but not significant. `NO_ADVERSE_GRADIENT` otherwise (coefficient non-negative).

## Execution Guidelines

### Release Resolution

For every publication key, apply this cascade:
1. Filter by effective status, `value_type`, `source_type`, and validity flags.
2. Among matching records, select the greatest `revision` number.
3. Among tied revisions, select the latest `released_at` timestamp.
4. Among tied timestamps, select the greatest record identifier (`observation_id`, `record_id`, or whichever is present).
5. Reject records with flags: `INVALID_SCALE`, `INVALID`, `WITHDRAWN`.
6. Suppressed or null analytic values are unavailable and **never zero-filled**.

### Precision and Output Format

- Report non-integer statistics to the number of decimal places declared in the effective request's `reporting` section (typically 4). Grid and threshold values may use declared literal precision.
- Counts, seeds, replicate numbers, PRNG states, ranks, and fold numbers are integers.
- Use uppercase two-letter state codes exactly as returned by portal endpoints.
- Use census division and region names exactly as returned by portal endpoints.
- Preserve every declared array order (feature order, grid order, division order, state order, checkpoint order, source group order); never sort independently.
- Use JSON `null` only when a statistic is mathematically unavailable; never use NaN or Infinity.

### Stable Ordering Rules

Preserve these orderings unless overridden:
- **Entity order:** ASCII-ascending state codes, or county FIPS within state as returned by portal.
- **Time order:** Year or end-period ascending.
- **Feature/predictor order:** As declared in effective request.
- **Group/cluster order:** Census division order as returned by portal, or declared order.
- **Grid order:** Lambda/alpha/l1_ratio grid as declared.
- **Checkpoint order:** Replicate numbers as declared.
- **Source group order:** As declared in effective request.
- **Subset order:** Increasing size, then lexicographic tuple order within size.

### Decision Application

1. Complete every module before evaluating any decision predicate.
2. Evaluate each gate on **unrounded** values using the effective predicate from the request.
3. Apply the controlled decision mapping in the effective precedence order.
4. Use only the valid enum values from the request or answer template.
5. For protocol-driven audits, the final decision module reports each gate as PASS/FAIL plus the final classification.

### Override Resolution

- `{section}_overrides` at root targets canonical `{section}`.
- `module_overrides.{module_name}` targets that exact top-level module.
- `reporting_overrides` targets `reporting`.
- Direct root keys target identically-named canonical root keys.
- Strip only the terminal `_overrides` suffix.
- Merge in request document order: objects by exact key recursively, arrays replace whole, scalars at exact path.
- Task-local direct bindings and resolved overrides take precedence over inherited values at same path.
- Reject unknown targets, implicit renames, arrays treated positionally, and type coercion before evidence resolution.

### Protocol Instance Boundary

The reusable method profile carries **method semantics only**. From the effective future request, bind:
- Entities and measures
- Calendar scope (years, reference year, end years)
- Geography scope (states, counties, regions, divisions)
- Source filters (release status, value type, source type)
- Random initialization (seed, stream, replicate count, checkpoint schedule)
- Hyperparameter grids (lambda, alpha, l1_ratio)
- Business decision cutoffs and predicates
- Output labels and vocabulary

Never carry task-local solved values across invocations. Recompute all evidence and outputs for each future invocation.
