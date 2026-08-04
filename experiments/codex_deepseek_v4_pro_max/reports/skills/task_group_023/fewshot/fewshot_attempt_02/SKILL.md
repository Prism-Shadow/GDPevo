 # Public Health Observatory Algorithmic Transportability Audit

 Conduct registered multi-module algorithmic audits against the Public Health
 Observatory Web portal.  This skill encodes reusable methodology only; every
 entity, measure, calendar window, geography, source filter, random seed,
 hyperparameter grid, business cutoff, output label, and solved numerical value
 must be recomputed from the effective future request and its authorized
 evidence.

 ## Activation

 This skill activates when a task references a `protocol_id` that matches one of
 the registered protocol identifiers listed under [Protocols](#protocols).
 Family membership or topical similarity is not sufficient.

 ## Evidence source

 All evidence comes from the read-only Public Health Observatory portal exposed
 at the environment variable `GDPEVO_ENV_BASE_URL` (or an equivalent
 `TASK_ENV_BASE_URL`).  No local files, external APIs, or prior knowledge may
 substitute for portal evidence.  Credentials are not required.

 Allowed endpoints and their accepted query strings are documented in the
 task-scope `environment_access.md`.  Dataset list endpoints support `page` and
 `page_size`.  CSV export uses
 `GET /download?dataset=<dataset>&format=csv` plus supported filter parameters.

 ## Override resolution

 When a future request is paired with a registered protocol profile, resolve one
 canonical effective request before any data access, random draw, fit,
 aggregation, or decision:

 1. Start from the registered method profile and any inherited canonical defaults
    for that exact protocol version.
 2. Direct request keys bind to the identically named canonical root key.  Inside
    a named section or module, a child key binds only to the identical child
    path.
 3. Suffix-alias resolution: a root key named `<section>_overrides` targets
    canonical `<section>`; `module_overrides.<module_name>` targets that exact
    top-level module; `reporting_overrides` targets `reporting`.  Strip only the
    terminal `_overrides` suffix during target resolution.
 4. Merge resolved entries in request document order:
    - Objects merge recursively by exact key.
    - Arrays replace whole arrays; never concatenate, union, or patch by position.
    - Explicit scalars, strings, Booleans, and null replace only their exact
      paths.
    - Absent paths inherit unchanged.
 5. Reject unknown targets, incompatible types, implicit renames, inferred
    aliases, and type coercion before proceeding.
 6. Task-local direct bindings and resolved overrides take precedence over
    inherited values at the same path.

 ## Instance boundary (reusable method only)

 These elements are always task-local and must never be carried across
 invocations:

 - Entities, measures, and geography
 - Calendar scope and panel years
 - Source filters (release status, value type, source type, validity flags)
 - Random seeds, streams, and replicate schedules
 - Hyperparameter grid values
 - Business decision cutoffs
 - Requested output labels and classification vocabulary
 - All solved analytical values (coefficients, p-values, RMSEs, coverages, etc.)

 ## Common methodology blocks

 ### Release resolution and cohort construction

 For each requested dataset and measure:

 1. Filter publications by effective status, source, value type, validity, and
    geography bindings.
 2. Select one record per declared entity-time-measure key using the declared
    ordered release priority (typically greatest revision, then latest release
    timestamp, then lowest record identifier).
 3. Count selected publications before analytic completeness exclusions when
    requested.
 4. Suppressed, invalid, withdrawn, blank, or null selected analytic values are
    unavailable and are never zero-filled.
 5. Join independently resolved series by effective stable entity and time keys.
 6. Construct each cohort (complete, balanced, broad-reference, dual-source,
    machine-learning) from its effective nonmissing and validity predicates.
 7. Preserve declared entity-code order, time order, feature order, and group
    order.

 ### Weighted linear algebra (when weights are specified)

 - For design X, outcome y, and positive weights w:
   - `Xw = diag(sqrt(w)) * X`, `yw = diag(sqrt(w)) * y`
   - `b = (Xw' Xw)^-1 Xw' yw` in declared column order.
 - **HC3**: With leverage `h_i = diag(Xw (Xw' Xw)^-1 Xw')` and weighted
   residuals `ew_i = sqrt(w_i)(y_i - X_i b)`,
   `V_HC3 = (Xw' Xw)^-1 Xw' diag(ew_i^2 / (1-h_i)^2) Xw (Xw' Xw)^-1`.
   Test with two-sided Student-t using n-k residual degrees of freedom.
 - **CR1**: For ordered clusters g with scores `s_g = Xw_g' ew_g`,
   `V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw' Xw)^-1 * sum_g(s_g s_g') * (Xw' Xw)^-1`.
   Test with two-sided Student-t using G-1 degrees of freedom.

 ### Delete-one-cluster jackknife

 1. Fit the full design.
 2. Delete every registered cluster one at a time in declared order.  Within
    each deletion recompute every mean (for within-transformed designs) and
    refit from scratch.
 3. For target coefficient b and G delete estimates b_-g with mean bbar:
    - Jackknife SE: `SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))`
    - Bias-corrected coefficient: `b_BC = G*b - (G-1)*bbar`
    - Test `b_BC / SE_JK` two-sided with G-1 Student-t degrees of freedom.
    (For jackknife on the full coefficient b directly, test `b / SE_JK`.)
 4. Percent change for deletion g: `100 * abs((b_-g - b) / b)`.
    Select extreme deletions by coefficient value, then entity code for ties.

 ### Nested grouped ridge cross-validation

 1. Hold out one ordered group per outer fold.  Within each outer training set,
    hold out every remaining group once in the same order for inner validation.
 2. Within every fit, standardize features using training-only means and
    training sample standard deviations (ddof=1).  Apply those moments to
    validation/test rows.  Center the training outcome (no scaling).
 3. Fit ridge with an unpenalized intercept: minimize
    `mean((y - a - Xb)^2) + lambda * sum_j(b_j^2)`.
    Initialize coefficients to zero; cycle in declared feature order.
    Update `b_j = sum_i(x_ij * r_ij) / (sum_i(x_ij^2) + n*lambda)`,
    where r excludes feature j.  Stop when max coefficient change is below
    the effective tolerance or at the declared sweep cap.
 4. Select the smallest unrounded inner RMSE for each outer fold, breaking ties
    toward the smaller penalty.  Refit on all outer-training rows.
 5. Pool squared errors before RMSE; aggregate OOF metrics from the single
    prediction assigned to every eligible row.

 ### State-blocked nested elastic net

 1. Allocate entities to folds: sort groups by descending retained-entity count,
    assign each to the currently smallest fold (lower fold id on equality).
    Repeat for inner folds within each outer-training set.
 2. Standardize declared continuous columns from training population moments;
    leave indicator columns unchanged.  Apply training moments to held-out rows.
    Keep intercept unpenalized.
 3. Minimize `SSE/(2n) + alpha * (rho * sum|beta_j| + 0.5*(1-rho) * sum(beta_j^2))`.
    Cold-start coefficients at zero, intercept at training outcome mean.
    In each cyclic sweep: update intercept by mean residual, then
    `beta_j = S(rho_j, alpha*rho) / (mean(x_j^2) + alpha*(1-rho))`
    where `S(a,t) = sign(a)*max(|a|-t, 0)` and
    `rho_j = mean(x_j * residual_partial_j)`.
    Stop at the registered max-change tolerance or sweep cap.
 4. Traverse the declared grid in outer/inner order.  Pool inner squared errors
    before RMSE.  Select by smallest unrounded RMSE, then smaller alpha, then
    smaller l1_ratio.

 ### Wild cluster bootstrap (restricted null)

 1. Fit the full model for each target and compute the observed CR1 t-statistic
    (or HC3 for weighted designs with group bootstrapping).
 2. Fit the restricted model without the target term.  Generate synthetic
    outcomes from restricted fitted values plus state-weighted restricted
    residuals multiplied by a random weight draw.
 3. Use the declared PRNG (XORSHIFT32 or PCG32) with the registered seed and
    stream.  Draw Rademacher weights (+1/-1 with equal probability), Mammen
    two-point weights, or Webb six-point weights as declared.
 4. For each replicate, refit the full model on the synthetic outcome and record
    the t-statistic.  Count exceedances where `|bootstrap_t| >= |observed_t|`.
 5. Plus-one p-value: `(exceedance_count + 1) / (replicate_count + 1)`.
 6. Record checkpoints at declared replicate numbers (PRNG state and t-values).
 7. For paired/three-equation designs, apply identical weight vectors across all
    equations in each replicate.  Report separate inference for each target.

 ### Grouped split conformal calibration

 1. Use held-out predictions from a declared source model (e.g., nested
    cross-validation outer predictions).
 2. Within each group fold, sort absolute residuals from the calibration split,
    compute the threshold as the residual at the nearest-rank index
    `ceil((n_cal + 1) * (1 - alpha))`.
 3. For every test observation, construct the prediction interval
    `[pred - threshold, pred + threshold]`.
 4. Report per-fold coverage, mean width, and test MAE.  Aggregate overall
    coverage and mean width.
 5. For state-level grouped conformal, report every state's coverage and width
    and identify the worst-division or worst-state.

 ### Trajectory PCA with deterministic k-means clustering

 1. Construct the trajectory feature matrix from declared within-year variable
    blocks across all trajectory years.
 2. Run registered-covariance PCA (center columns, compute covariance, extract
    eigenvalues/vectors).  Retain the declared number of components.
 3. Initialize k-means centroids from the declared initial-centroid entities
    (using their PC scores in declared order).
 4. Run Lloyd's algorithm deterministically: assign each entity to the nearest
    centroid by Euclidean distance in PC space, recompute centroids as the mean
    of assigned PC scores, repeat until convergence.  Break assignment ties by
    lower cluster id.
 5. Stability audit:
    - For leave-year-out: omit all features from one trajectory year, re-run
      full PCA + k-means on the reduced feature set, and compute adjusted Rand
      index (ARI) against the full-year clustering.
    - For delete-state: omit all rows belonging to one state, re-run full
      PCA + k-means, and compute ARI on the retained entities.
 6. Report the complete eigenvalue spectrum, loadings, PC scores, cluster
    labels, cluster sizes, centroids, initialization, iteration count, and all
    stability ARI values.

 ### Source perturbation (exhaustive source-year or source-group)

 **Exhaustive source-year perturbation:**
 1. For each combination of analysis years (sizes declared in `year_subset_sizes`
    or similar), fit the full model using only those years.
 2. For dual-source designs, compute both primary and parallel coefficients and
    the absolute percent shift between them for every subset.
 3. Report all subset coefficients, p-values, shifts, same-sign fraction,
    median/max absolute percent shift, and worst subset.

 **Exhaustive source replacement (direct vs rollup):**
 1. Identify all entities where both the baseline source and the replacement
    source resolve as eligible.
 2. Enumerate all 2^M scenarios of replacing vs. retaining the baseline source
    for those M entities.
 3. For each scenario, refit and record the target coefficient and p-value.
 4. Report by-replacement-count strata (min/max coefficient, min/max p-value,
    mean absolute percent shift), the maximum-shift scenario, and exact Shapley
    effects computed over the full coalition lattice.

 **Source-group deletion:**
 1. For each declared ordered source group, remove its terms from the design,
    reuse the full model's selected hyperparameters without retuning, and refit.
 2. Report per-outer-fold RMSE, pooled RMSE, RMSE deterioration vs. full model,
    worse-fold count, and deterioration rank (1 = largest deterioration).

 ### Controlled decision rules

 1. Evaluate each declared gate predicate in strict precedence order using the
    audit module outputs.
 2. Gates are typically Boolean predicates on audit statistics (e.g.,
    "coefficient is negative and p-value <= 0.05", "pooled R-squared >= 0.85").
 3. Count passing gates and classify according to the declared decision tiers:
    - Primary tier: all gates pass.
    - Secondary tier(s): intermediate gate counts.
    - Default tier: remaining cases.
 4. Report each gate result (`PASS`/`FAIL` or Boolean), the passed-gate count,
    the first-failed module (if applicable), and the classification label using
    the exact controlled vocabulary from the request.

 ## Protocols

 Detailed method profiles for each registered protocol are in `protocols/`.
 Select the profile whose `protocol_id` exactly matches the effective request.

 | Protocol ID | Family | Description |
 |---|---|---|
 | `PHO_STATE_TRANSPORT_AUDIT_V1` | state algorithmic transport | Six-module state obesity-longevity transportability audit |
 | `PHO_COUNTY_MEDIATION_TRANSPORT_V1` | county algorithmic transport | County poverty-obesity mediation through physical inactivity |
 | `PHO_STATE_ROBUSTNESS_TRANSPORT_V1` | state algorithmic transport | Reliability-weighted state food-insecurity-diabetes audit |
 | `PHO_COUNTY_PANEL_TRANSPORT_V1` | county algorithmic transport | County panel diabetes dynamics with six-algorithm audit |

 ## Reporting conventions

 - Round every non-integer reported statistic to the declared number of decimal
   places and encode as a JSON number.
 - Use uppercase two-letter state codes and portal division/country names exactly
   as they appear in the evidence.
 - Preserve every declared formal order in arrays; do not independently sort
   aligned result arrays.
 - Use JSON `null` only when a requested statistic is mathematically unavailable;
   never use `NaN` or `Infinity`.
 - Integers (counts, ranks, fold numbers, seeds, PRNG states, replicate numbers)
   retain their natural JSON integer type.
 - Omit the `protocol_registry_record` and `portable_protocol_profile` wrappers
   from the solver-visible output; they are metadata provenance only.
 - Return exactly one JSON object conforming to the effective answer template,
   with no narrative outside it.
