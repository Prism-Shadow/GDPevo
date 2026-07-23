# Audit module families (catalog)

The exact module set is declared by the effective request; execute in declared order. These are the recurring families and their registered method variants. Numerical detail lives in `numerical_conventions.md`.

## 0. Publication / cohort resolution (always first)

Filter portal publications; resolve one record per key; build the requested cohorts; preserve order. See `portal_evidence.md`.

## 1. Delete-cluster fixed-effects / jackknife

- Variants: two-way FE OLS delete-one-state jackknife; reliability-weighted delete-one-division jackknife; delete-state bias-corrected two-step linear GMM.
- Output family: full coefficient, every delete-cluster coefficient/percent-change, mean delete coefficient, bias-corrected coefficient, jackknife SE/t/p, extrema or most-influential cluster, maximum shifts.

## 2. Nested grouped ridge / elastic-net CV

- Variants: nested leave-division-out ridge; nested leave-state-out ridge (base vs augmented feature maps); division-grouped nested weighted elastic-net; state-blocked nested elastic-net.
- Output family: fold counts, complete inner grid (RMSE aligned to the lambda / alpha-l1 grid), selected hyperparameters per outer fold, outer RMSE per fold, pooled OOF RMSE/MAE/R^2, augmented-win counts or nonzero counts, standardized coefficients.

## 3. Wild cluster bootstrap-t

- Variants: PCG32 Webb wild cluster bootstrap-t; restricted-null xorshift32 wild cluster bootstrap-t (single-target or paired across equations).
- Output family: observed coefficient/CR1 SE/t, PRNG metadata (seed, stream, replicate count, final state), checkpoints at declared replicates (PRNG state + t), exceedance count, plus-one p-value, requested t quantiles, batch exceedance counts, first weight-index rows (for PCG32).

## 4. Grouped split conformal

- Variants: grouped split conformal ridge (division-grouped); state-grouped split conformal (cyclic partitions, per-state max residual); cross-fold grouped split conformal (OOF predictions, RUCC-band and prediction-decile diagnostics).
- Output family: per-fold calibration count, rank, radius/width, coverage, test MAE; per-state and per-band coverage; aggregate coverage and weighted mean width; worst group.

## 5. Trajectory PCA + clustering + stability

- Variants: state trajectory PCA + 3-means + leave-year-out ARI; county trajectory PCA + k-selection by silhouette + delete-state ARI; weighted/region trajectory variants.
- Output family: spectrum/eigenvalues, explained ratios, signed loadings, entity scores, initialization, centroids, sizes, labels, update/iteration count, candidate-k grid with silhouette/inertia, leave-out/delete ARI vector, min/median/mean ARI.

## 6. Source / year perturbation

- Variants: exhaustive source-year fixed-effects perturbation (primary vs parallel series); source-group deletion (no retune); exhaustive direct-vs-rollup with exact Shapley.
- Output family: cohort audit, all subsets/scenarios, coefficient and p-value vectors, shift vector, same-sign summary, worst subset, Shapley effects and sum, by-popcount strata.

## 7. Mediation / GMM (when declared; replaces or augments family 1)

- Difference-GMM mediation with cross-equation delta inference; two-step linear GMM with Hansen J; partial-R^2 mediation sensitivity surface.
- Output family: panel dimensions, coefficient summaries with cluster SE/CI, first-stage partial F, stacked indirect effect + interval, delete-state diagnostics, Hansen J, sensitivity surface, tipping R^2.

## 8. Country burden reconciliation (when declared; different module set)

- Label/alias reconciliation to ISO3; revision/quality audit (applied vs non-applied revisions, anomaly/scale-break cells, missing/imputed counts); burden PCA; k-means with silhouette k-selection; region-adjusted panel model; controlled advisory enum.
- Output family: reconciliation counts, quality-audit cell lists/counts, PCA loadings, cluster sizes/membership, panel coefficient/SE/p/R^2, advisory.

## 9. Controlled decision (always last)

See `numerical_conventions.md` § Decision.
