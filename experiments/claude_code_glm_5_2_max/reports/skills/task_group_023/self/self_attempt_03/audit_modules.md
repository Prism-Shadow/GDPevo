# Recurring Audit-Module Families

Across the PHO audit family, modules recur in a small number of families. For each family below: read its parameters from `analysis_request.json`, implement the named method exactly, and produce the evidence the `answer_template.json` contract requires. These are generic shapes — every concrete parameter (cohort, grid, seed, threshold, order) comes from the request, not from this file.

## 0. Publication & cohort resolution (appears in every task)

The first block of every audit. All other modules consume its cohorts.

- **Read from request:** geography scope, analysis years, outcome/exposure/mediator, health measures to resolve, release method, revision-priority order, value-type / source-type / release-status filters, invalid quality flags, missing rule, and the named cohort definitions (primary, balanced, broad, strict, machine-learning).
- **Produce (per template):** target jurisdictions, analysis years, resolved health-observation and socioeconomic-record counts, yearly complete-case counts, excluded jurisdiction codes, and each named cohort's count. For country tasks: requested/resolved label counts, alias-resolution count, resolved ISO3, applied/non-applied revision event ids, anomaly/scale-break cells, raw-missing and imputed cell counts, usable country/indicator counts.
- **Pitfalls:** picking more than one record per (geography, year, measure); zero-filling suppressed/blank values; mis-applying the revision tie-break; forgetting that the balanced cohort is the intersection across ALL requested years.

## 1. Delete-one-cluster jackknife / fixed-effects / GMM

Cluster unit is declared (STATE or CENSUS_DIVISION). Variants: two-way fixed-effects OLS with delete-one jackknife; difference/linear GMM with delete-state bias correction.

- **Read from request:** cohort, outcome, ordered predictors / coefficient order, instrument order (GMM), cluster unit, pseudoinverse cutoff (GMM).
- **Produce:** full-sample coefficient(s); the delete-one coefficient vector aligned positionally to the cluster order; jackknife mean, standard error, t-statistic, p-value; bias-corrected coefficient; minimum/maximum delete cluster and coefficient; maximum absolute percent change; most-influential cluster. For GMM additionally: full two-step coefficients, Hansen J, bias-corrected coefficients, maximum delete-state shifts, and every delete-state coefficient vector and Hansen J.
- **Pitfalls:** re-sorting the delete-one vector independently of the cluster order; computing the jackknife SE from the wrong formula; dropping the bias-correction step.

## 2. Nested ridge / elastic-net cross-validation

Grouped nested CV with training-only standardization. Variants: ridge (lambda grid); elastic-net (alpha + l1_ratio grids).

- **Read from request:** cohort, target, feature/term order (base and augmented maps where present), lambda grid (and alpha / l1_ratio grids), outer and inner grouping, outer/inner fold counts, fixed lambda where conformal reuses it.
- **Produce:** cohort and fold counts; the grid(s); for every outer fold — held-out group, row count, complete inner-grid RMSE aligned to the grid order, selected hyperparameter(s), nonzero feature count (elastic-net), coordinate-cycle count (elastic-net), outer RMSE; pooled RMSE / MAE / R² / Q²; worst outer fold; augmented-vs-base comparison and augmented-win count where required; standardized coefficients where required.
- **Pitfalls:** standardizing using test-fold statistics; mis-aligning the inner-grid RMSE array to the grid order; using pooled metrics that ignore fold sizes.

## 3. Wild cluster bootstrap-t

Restricted-null wild cluster bootstrap on the t-statistic, with a declared PRNG family and reproducibility checkpoints.

- **Read from request:** cohort, cluster unit, target coefficient/term, source model, PRNG family (e.g., a PCG32 or XORSHIFT32 variant — implement the one declared), seed, stream where declared, replicate count, checkpoint-replicate list, quantile probabilities, batch structure where declared.
- **Produce:** method and randomization metadata; observed coefficient, CR1 standard error, and t-statistic; weight-index rows or batch exceedance counts as declared; total exceedance count; plus-one / bootstrap p-value; bootstrap coefficient mean and sample SD where declared; t-quantiles at the requested probabilities; every checkpoint replicate with its PRNG state and t-statistic in the declared order; terminal/final PRNG state.
- **Pitfalls:** substituting a different PRNG; skipping the restricted-null constraint; reporting checkpoints out of the declared replicate order; forgetting the final PRNG state.

## 4. Grouped split conformal calibration

State- or division-grouped split conformal, often reusing nested-CV outer predictions.

- **Read from request:** cohort, source predictions, group, fixed lambda where reused, partition/fold count, nominal coverage, RUCC bands / prediction deciles where declared.
- **Produce:** group assignments and fold sizes; per-fold thresholds, coverage, mean width, and test MAE; aggregate coverage and mean width; worst fold/group; per-state (and per-RUCC-band / per-decile where declared) coverage and width; finite-sample rank / interval radius where declared.
- **Pitfalls:** using non-grouped (i.i.d.) splits; reporting coverage on training folds; forgetting the worst-fold diagnostic.

## 5. Trajectory PCA + deterministic k-means clustering

Covariance PCA on a trajectory feature matrix (measures × years, or change variables × end-years), then deterministic k-means with leave-one-(year/state)-out stability via Adjusted Rand Index.

- **Read from request:** cohort, aggregation unit, feature order (within-year blocks and year order), retained component count, cluster count (and candidate cluster counts where silhouette selection is required), leave-out unit (year or state).
- **Produce:** feature order and cohort size; leading eigenvalues, explained-variance ratios, and cumulative ratio; signed loadings; state/county scores; deterministic initialization (e.g., initial centroid state codes); centroids; cluster sizes; labels aligned positionally to the cohort order; the leave-out ARI vector in declared order; aligned agreement / assignment-change counts; median and minimum ARI. Where silhouette selection is required: silhouette by candidate k and the selected k.
- **Pitfalls:** non-deterministic k-means initialization (the request fixes initialization); reporting ARI in the wrong leave-out order; mis-aligning labels to the cohort order.

## 6. Source / source-group perturbation (and exact Shapley)

Exhaustive perturbation of the outcome source or of feature source-groups, with stability summaries and (where declared) exact Shapley attribution.

- **Read from request:** cohort, target coefficient, baseline vs replacement outcome source, ordered source groups, year-subset sizes or scenario strata, reuse-full-model-hyperparameters flag.
- **Produce:** cohort audit; ordered rollup/source-group codes; every exhaustive subset or scenario stratum (e.g., all source/year subsets of declared sizes, or every replacement-count stratum from 0 through M); coefficient and p-value vectors; absolute percent shifts; same-sign subset count/fraction; median and maximum absolute percent shift; worst subset; maximum-shift bitmask and replaced codes; ordered exact Shapley effects and their sum; all-replacement-minus-all-baseline coefficient.
- **Pitfalls:** retuning hyperparameters when the request says reuse the full model's; computing Shapley approximately when "exact" is declared; mis-ordering scenario strata.

## 7. Decision / controlled conclusion (appears in every task)

- **Read from request:** the gate list, each gate's numeric threshold, the pass-count precedence, and the controlled enum values.
- **Produce:** one boolean per gate (and a per-module PASS/FAIL where the template uses those), the pass count or first-failed-module, and the classification enum.
- **Pitfalls:** inventing thresholds not in the request; using a narrative verdict instead of the controlled enum; mis-applying precedence (e.g., reporting "partial" when the rule is first-failed-module).
