# PHO Algorithmic Audit Skill

## Purpose

Execute Public Health Observatory (PHO) registered algorithmic audits. Given an
`analysis_request.json` and an `answer_template.json`, access the read-only PHO
data portal, resolve publication records, construct analytic cohorts, run every
declared audit module in its registered order, evaluate controlled business
predicates, and return one completed JSON object conforming to the template.

This skill describes the reusable method. Every entity identifier, measure code,
time coordinate, source filter, random seed, hyperparameter grid value, business
cutoff, and output label is drawn from the effective request — never carried
across invocations.

---

## Portal Access

The PHO data portal is a read-only REST API. Resolve the base URL from the
effective `<TASK_ENV_BASE_URL>` binding. All endpoints are GET-only with no
authentication.

### Endpoints

| Endpoint                        | Content                                      |
|---------------------------------|----------------------------------------------|
| `GET /`                         | Portal landing page                          |
| `GET /catalog`                  | Dataset and field catalog                    |
| `GET /geographies/states`       | State-level geographic identifiers           |
| `GET /geographies/counties`     | County-level geographic identifiers          |
| `GET /geographies/countries`    | Country-level geographic identifiers         |
| `GET /data/state-health`        | State health measures (value types, sources) |
| `GET /data/state-socioeconomic` | State socioeconomic measures                 |
| `GET /data/county-health`       | County health measures                       |
| `GET /data/county-socioeconomic`| County socioeconomic measures                |
| `GET /data/country-indicators`  | Country-level indicators                     |
| `GET /data/revisions`           | Revision event metadata                      |
| `GET /methodology`              | Methodological documentation                 |
| `GET /download`                 | Bulk data access                             |

Use URL query parameters appropriate to each endpoint to filter by year,
measure, geography, release status, value type, and source type as declared
in the effective request. Fetch all required data before beginning any
analytic module — do not interleave data access with computation.

---

## Override Resolution: Building the Effective Request

Every PHO audit protocol supports an override/merge system. The canonical
baseline is the registered protocol profile for the effective `protocol_id`.
Then apply in document order:

1. **Direct keys** — a root key `k` in the request targets the canonical root key `k`
2. **Suffix aliases** — a root key named `<section>_overrides` targets canonical
   `<section>` after stripping the terminal `_overrides` suffix; similarly,
   `module_overrides.<module_name>` targets the top-level module block of that
   exact name, and `reporting_overrides` targets `reporting`
3. **Merge rules**:
   - Objects merge recursively by exact key match
   - Arrays replace whole — never concatenate or patch by position
   - Scalars, strings, Booleans, and `null` replace only at their exact path
   - Absent paths inherit unchanged
4. **Validation** — reject unknown targets, type-incompatible overrides, and
   implicit renames before any data access or computation
5. **Single contract** — freeze one resolved effective request; use it
   consistently in every module

After resolution, the effective request fully specifies the audit: measures,
geographies, time windows, source filters, cohort rules, module parameters,
hyperparameter grids, random seeds, checkpoint schedules, business predicates,
and decision mappings.

---

## Module Execution Order

Every PHO audit executes modules in a fixed, registered order. Commonalities
across protocol families:

1. **Publication resolution and cohort construction** — always first
2. **Primary analytic modules** — fixed-effects, cross-validation, bootstrap,
   conformal calibration, PCA clustering, perturbation/sensitivity
3. **Controlled decision** — always last

Execute modules strictly in the declared order. Each module's outputs may feed
into later modules (e.g., nested CV predictions → conformal calibration).
Never reorder.

---

## Reusable Module Methods

### Module 1: Publication Resolution and Cohort Construction

**Release resolution.** For each declared measure, geography, and time key,
filter publications by effective release status, value type, source type, and
validity flags. When multiple records match a key, select by:
1. Greatest revision number
2. Latest release timestamp
3. Lowest record/observation identifier

**Validity.** Treat records with suppressed values, invalid quality flags
(including `INVALID_SCALE`, `INVALID`, `WITHDRAWN`), blank values, or `null`
analytic values as unavailable. Never zero-fill unavailable values.

**Join and cohort construction.** Join independently resolved health and
socioeconomic series on stable entity and time keys. Build each declared
cohort from its effective completeness predicate:
- **Primary/reference-year cohort** — complete cases in the reference year for
  the declared outcome and all required fields
- **Balanced panel cohort** — entities complete in every analysis year
- **Broad/ML cohort** — reference-year complete plus additional declared fields
- **Strict dual-source cohort** — complete for outcome, primary exposure,
  parallel exposure, and adjustments in every analysis year

Preserve entity-code-then-time ordering and every declared feature, group, and
cluster order.

**Counting.** Report selected publication counts *before* analytic completeness
exclusions when requested. Report cohort sizes after applying completeness
predicates.

---

### Module 2: Delete-One/Cluster Fixed-Effects and Jackknife

**Fixed-effects transformation.** For the declared outcome and predictors,
transform each modeled variable as:
  z*_it = z_it − mean_i(z) − mean_t(z) + grand_mean(z)
where mean_i is the entity mean and mean_t is the time mean. Solve OLS without
an intercept on the double-demeaned variables in declared predictor order.

**Weighted variant.** When reliability weights are declared, use weighted
least squares: set Xw = diag(√w)·X and yw = diag(√w)·y, then solve
b = (Xw'Xw)⁻¹ Xw'yw. Use HC3 or CR1 variance estimators as declared.

**Delete-one/cluster jackknife.** For G clusters (states, divisions):
- Delete each cluster in registered order
- Recomputed every transformation mean and refit from scratch
- For delete estimates b₋g and mean b̄:
  SE_JK = √((G−1)/G · Σ_g (b₋g − b̄)²)
- Bias-corrected: b_BC = G·b − (G−1)·b̄
- Test: b_BC / SE_JK, two-sided Student-t with G−1 df
- Select extrema by coefficient value, then entity code

**Weighted jackknife.** Same structure, with weighted WLS refits and the
weighted-design coefficient as the target.

---

### Module 3: Nested Ridge/Elastic-Net Cross-Validation

**Fold structure.** Outer folds leave out each declared group (census
division, state) once. Within each outer training set, inner folds leave out
each remaining group once in the same declared order.

**Standardization.** Inside every fit, compute training-only feature means and
sample standard deviations (ddof=1). Apply those moments to validation/test
rows. For the weighted variant, use weighted means and population SD with
weighted denominators. Center the outcome by its training (weighted) mean;
do not scale the outcome.

**Ridge solver.** Minimize mean((y − a − Xb)²) + λ·Σ_j b_j². Initialize
coefficients to zero. Cycle in declared feature order:
  b_j = Σ_i x_ij·r_ij / (Σ_i x_ij² + n·λ)
where r_ij is the partial residual excluding feature j. Stop when max
coefficient change < tolerance or at the declared sweep cap. Keep the
intercept unpenalized.

**Elastic-net solver.** Minimize SSE/(2n) + λ·[α·Σ_j|b_j| + (1−α)·Σ_j b_j²/2].
Cold-start coefficients at zero, intercept at the outcome mean. Cycle in
declared order:
  ρ_j = mean_i(w_i·Z_ij·partial_residual_i)
  b_j = S(ρ_j, λ·α) / (1 + λ·(1−α))
where S(a,t) = sign(a)·max(|a|−t, 0). Stop at the declared tolerance or cycle cap.

**Selection.** For each penalty, pool all inner validation squared errors at
row level. Select smallest RMSE; break ties toward the smaller penalty (or
smaller α then smaller l1 ratio for elastic net). Refit on all outer-training
rows and predict the held-out outer rows.

**Aggregation.** Pool exactly one out-of-fold prediction per eligible row.
Compute RMSE, MAE, and R² = 1 − SSE / SST (using full-sample unweighted mean
of the outcome). For weighted variants, report unweighted metrics on
predictions.

**Nonzero count.** Count coefficients with absolute value above the declared
numerical zero tolerance.

---

### Module 4: Wild Cluster Bootstrap

**Setup.** For the full model, compute the target coefficient and CR1
cluster-robust standard error. Studentize: t_obs = b_target / SE_CR1. Fit the
restricted model *without* the target variable and retain restricted fitted
values and residuals in entity order.

**PRNG.** Use one of the registered generators:

*PCG32* (state-level transport): 64-bit state, 32-bit output. Increment =
2·stream + 1. Initialize state to zero, advance, add seed mod 2⁶⁴, advance.
Each step: state = old·6364136223846793005 + increment mod 2⁶⁴;
xorshifted = low32(((old ≫ 18) ⊕ old) ≫ 27); rot = old ≫ 59;
output = rotate_right_32(xorshifted, rot). Map output mod 6 to
[−√(3/2), −1, −√(1/2), √(1/2), 1, √(3/2)].

*Xorshift32* (county-level transport): unsigned 32-bit state. Each call:
x ⊕= x ≪ 13; x ⊕= x ≫ 17; x ⊕= x ≪ 5; mask to 32 bits after each xor.
Map to ±1: odd state → +1, even state → −1.

**Draw and refit.** Maintain one continuous generator across all replicates.
Each replicate: draw one weight per cluster in registered order, set
y* = restricted_fit + restricted_residual · cluster_weight, refit the full
model, recompute CR1, and studentize the target coefficient.

**Inference.** Count |t*| ≥ |t_obs| (or with declared numerical tolerance δ,
t* ≥ t_obs − δ for one-sided absolute). Report plus-one p = (count + 1)/(B + 1).

**Quantiles.** For sorted values x and probability p:
- Nearest-rank: x[⌈p·B⌉ − 1] (one-based rank)
- Type-7: h = (B−1)·p, j = ⌊h⌋, γ = h − j, (1−γ)·x[j] + γ·x[j+1] (zero-based)

**Checkpoints.** Record PRNG state and t-statistic only after the declared
replicate is fully complete. Never reset the stream mid-procedure.

**Bootstrap-t confidence intervals.** CI = b_obs ± t*_quantile · SE_obs, using
the declared quantile probabilities and the symmetric bootstrap-t distribution.

---

### Module 5: Grouped Split Conformal Calibration

**Partition.** For each declared outer group as test, select the calibration
group by greatest row count (then ascending group name), and use all remaining
groups for proper training.

**Fit and predict.** For the declared model (ridge, elastic-net with fixed
penalty), fit on proper-training rows with training-only standardization.
Predict calibration and test rows. Collect absolute residuals on calibration
rows.

**Rank and intervals.** Sort m calibration absolute residuals. With nominal
coverage c, use rank r = min(m, ⌈(m+1)·c⌉) and radius q = score[r − 1]
(one-based). Prediction intervals: ŷ ± q (inclusive).

**Reduction.** When calibration is at the group level (e.g., county
observations within states), reduce calibration residuals to one maximum
absolute residual per calibration group before ranking.

**Aggregation.** Report per-fold: test count, coverage fraction, mean interval
width, and calibration diagnostics. Aggregate overall coverage and mean width
weighted by per-fold test counts. Choose worst division/group by smallest
coverage fraction, then earlier declared order.

---

### Module 6: Trajectory PCA and Clustering

**Feature construction.** Build the declared variable-major/time-major blocks
in order. For state-aggregated trajectories, average entity-level measures to
the declared aggregation unit and period. Standardize each column by
active-sample sample standard deviation.

**PCA via covariance.** Form C = Z'Z / (n−1). Eigendecompose with symmetric
Jacobi sweeps: select the largest absolute upper-triangle off-diagonal, tie
by lower row then column; compute rotation c,s from the two-sided formula;
rotate A and eigenvectors. Stop at the declared off-diagonal tolerance or
iteration cap. Order eigenvalues descending; for ties, use original diagonal
index.

**Loading orientation.** For each retained eigenvector, find its earliest
(by index) maximum-absolute element and flip the entire vector sign so that
element is positive. Scores = Z · oriented_loadings.

**Clustering via k-means.** Run squared-Euclidean k-means on the declared
leading scores. Initialize the first centroid at the ASCII-first entity.
Each subsequent centroid is the entity maximizing distance to its nearest
existing center, tied by entity code. Assign each point to the nearest
centroid, tied by lower cluster ID. Update centroids as member means. Stop
when assignments are unchanged and centroid drift ≤ tolerance, or at the
declared iteration cap. For empty clusters, reassign the farthest non-singleton
point. Canonicalize final cluster IDs by centroid coordinates then working ID.

**Silhouette.** For each point i with cluster label c_i, compute a(i) = mean
distance to points in same cluster, b(i) = min_{k≠c_i} mean distance to points
in cluster k. Silhouette s(i) = (b(i)−a(i))/max(a(i),b(i)), with s(i)=0 for
singleton clusters. Report mean silhouette per k.

**Stability via leave-one-out.** For each declared omission (year, state, time
block), delete the corresponding observations, rebuild the full pipeline
(standardization, PCA, orientation, initialization, clustering) from scratch,
and compute the adjusted Rand index:
  ARI = (Σ_ij C(n_ij,2) − expected) / (0.5·(Σ_i C(a_i,2) + Σ_j C(b_j,2)) − expected)
  where expected = Σ_i C(a_i,2)·Σ_j C(b_j,2)/C(n,2)

Align refit labels to full labels by the permutation maximizing agreement,
tied by lexicographically smallest mapped-ID vector.

---

### Module 7: Source/Year Perturbation

**Enumeration.** Enumerate every time subset of the declared sizes in
lexicographic tuple order. For each subset, keep the analytic set unchanged
but restrict to those time points. Refit the full model (double-demeaned OLS,
weighted WLS, or GMM) and recompute inference for each subset.

**Exhaustive source perturbation.** For M entities with a valid replacement
source (e.g., county-rollup vs. direct-survey), enumerate all 2^M replacement
masks ordered by replacement count. Order entities by descending absolute
difference between replacement and baseline values, tied by entity code.
For mask m, replace entity j iff bit j of m is 1. Keep fixed reliability
weights. Refit WLS with HC3 for every scenario.

**Aggregation.** For each popcount stratum, report scenario count, coefficient
range, p-value range, and mean absolute percent shift. Compute relative shift
as 100·|b_mask − b_baseline| / |b_baseline|. Select the maximum unrounded
shift, tied by smaller mask.

**Same-sign fraction.** Count subsets where both baseline and alternate
coefficients are nonzero with identical sign.

**Shapley attribution.** For ordered entity j:
  φ_j = Σ_{S⊆M\{j}} |S|!·(M−|S|−1)! / M! · [b(S∪{j}) − b(S)]
Verify Σ_j φ_j = b(all) − b(none) within numerical tolerance.

**Stability evaluation.** A scenario is stable iff both its baseline and
alternate coefficients have the same sign (or other declared predicate).

---

### Module 8: Difference/System GMM Mediation

**First-difference transformation.** Create adjacent-change rows in entity
then end-period order. Apply the declared lag structure and instrument sets.

**Two-step GMM.** First-step moments: g(θ) = Z'(y − Dθ)/n with identity
weight. Build state-cluster scores s_g = Z_g'u_g and S = Σ_g s_g·s_g'/n.
Second-step weight W is the Moore-Penrose pseudoinverse of S, using the
declared relative singular-value cutoff. Second-step θ̂ minimizes the
weighted quadratic form.

**Hansen J.** J = n·g(θ̂)'·W·g(θ̂), distributed χ² with (number of
instruments − number of parameters) degrees of freedom.

**Indirect effect.** θ_indirect = â·b̂, with variance:
  Var(â·b̂) = b̂²·Var(â) + â²·Var(b̂) + 2·â·b̂·Cov(â,b̂)
Use clustered standard errors (CR1, finite-sample adjustment) and Student-t
inference with cluster degrees of freedom.

**First-stage diagnostics.** Partial F-statistics from full-versus-reduced
residual sums of squares for each endogenous regressor.

**Delete-one diagnostics.** For each state deletion, rebuild the panel and
refit all equations from scratch in state order.

---

### Module 9: Partial-R² Sensitivity

**Baseline.** From unrounded path-a coefficient a, path-b coefficient b,
path-b standard error SE_b, and residual degrees of freedom df.

**Magnitude.** For each (r²_M, r²_Y, direction) cell:
  magnitude = SE_b · √(df · r²_Y · r²_M / (1 − r²_M))
  adjusted_b = b − sign(direction)·magnitude
  adjusted_indirect = a · adjusted_b
  adjusted_direct = total_effect − adjusted_indirect
  proportion = adjusted_indirect / total_effect

**Tipping point.** The equal-strength R² where adjusted_indirect crosses
zero, computed from unrounded inputs.

**Evaluation.** A direction-row preserves the baseline sign if the adjusted
indirect effect maintains the same sign as the baseline indirect effect.

---

### Module 10: Source-Group Deletion Audit

**Setup.** Use the full model's selected hyperparameters (no retuning). For
each declared source group and each outer fold, remove exactly the group's
terms from the design matrix. Apply the same preprocessing (standardization
moments, intercept) and solver to the reduced model. Predict the held-out
outer rows and compute per-fold RMSE and pooled RMSE.

**Deterioration.** RMSE_deterioration = pooled_reduced_RMSE − full_OOF_RMSE.

**Ranking.** Rank source groups by decreasing unrounded deterioration, then
by declared group order. Count per-group outer folds where reduced RMSE
exceeds the corresponding full-model fold RMSE.

---

## Controlled Decision

Complete every evidence module before evaluating any business predicate.
Evaluate all predicates on unrounded computed values, not rounded reported
values.

For each declared gate in precedence order:
1. Evaluate the predicate (e.g., "coefficient > threshold", "p < 0.05",
   "coverage ≥ nominal", "minimum ARI ≥ cutoff")
2. Mark PASS or FAIL using exactly the declared PASS/FAIL vocabulary
3. Count satisfied gates

Apply the effective decision mapping:
- If the primary rule is "all gates pass," check the count equals the total
- If intermediate tiers exist, check counts against the declared thresholds
- Follow the declared precedence order strictly

The first-failed module (if any) is the earliest module in the declared
precedence order whose predicate evaluates to FAIL.

---

## Reporting Conventions

- **Decimal places:** Round non-integer reported statistics to the declared
  number of decimal places (4 or 6, depending on the protocol). Literal
  grid values, thresholds, and declared parameters retain their natural
  precision.
- **Identifiers:** Use uppercase two-letter state codes; uppercase ISO3
  country codes; portal division/region names exactly as returned.
- **Ordering:** Every list preserves its declared order. Do not sort an
  aligned result array independently. State order, feature order, division
  order, subset order — all are defined by the effective request and
  preserved exactly.
- **Missing values:** Use JSON `null` only when a statistic is mathematically
  unavailable (e.g., a bootstrap CI when no replicates exceed). Never emit
  NaN or Infinity.
- **Counts and integers:** Natural JSON integer types. Ranks, fold numbers,
  seeds, PRNG states, and replicate numbers are integers.
- **Booleans and enums:** Use the exact controlled vocabulary strings from
  the effective request and answer template.

---

## Execution Checklist

1. **Read** the portal catalog and methodology to understand available fields
2. **Resolve** the effective request by merging overrides onto the canonical
   protocol baseline
3. **Fetch** all required data from the portal: health, socioeconomic,
   geography, and revision metadata for all declared years, measures, and
   geographies
4. **Construct cohorts** — resolve releases, filter validity, join sources,
   apply completeness predicates
5. **Execute each module** in registered order, using only the effective
   request's bindings for every parameter, grid, seed, and cutoff
6. **Evaluate decisions** on unrounded values against the declared predicates
7. **Assemble** the answer JSON conforming to the answer template, with all
   required keys, declared array lengths, and cardinality constraints
8. **Validate** numeric precision, identifier format, list ordering, and
   controlled vocabulary fields
9. **Return** exactly one JSON object with no narrative outside it

## Portal Interaction Notes

- The portal returns JSON arrays of records. Parse and index them in memory
  before analysis — do not query the portal during module computation.
- Publication records have fields for `measure_id`, `year`, geographic
  identifiers, `value`, `value_type`, `source_type`, `release_status`,
  `revision`, `released_at`, `observation_id`/`record_id`, `sample_size`,
  and quality/validity flags.
- Socioeconomic records have analogous structure with their own field names.
- Revision events are listed at `/data/revisions` with `revision_event_id`
  and `status` fields.
- Country indicators use ISO3 codes and have a `country_name` field that
  must be reconciled against requested labels through the portal's geography
  endpoint.
