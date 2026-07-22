# PHO Algorithmic Audit Skill

Use this skill for Public Health Observatory audit tasks that provide a prompt,
an `analysis_request.json`, an `answer_template.json`, and a read-only PHO data
portal. The objective is to produce exactly the requested JSON answer from the
portal evidence and the registered algorithm definitions.

## Operating Rules

1. Read the prompt, request, template, environment access notes, catalog, and
   methodology before computing anything.
2. Treat the answer template as the output contract. Build the output object
   from its required keys, list lengths, enum values, precision rules, and
   ordering rules.
3. Use only portal data and methodology documents. Do not import outside
   reference data or silently infer missing values.
4. Preserve every declared order: geography order, year order, coefficient
   order, feature order, grid order, checkpoint order, subset order, and source
   group order. Never sort an aligned result array independently from its key
   array.
5. Keep identifiers as text. Preserve leading zeros in FIPS-like identifiers and
   use uppercase state and ISO-style codes where requested.
6. Compute using unrounded values. Round only when writing the final JSON.
   Encode unavailable numeric results as `null`, never `NaN`, `Infinity`, or a
   zero placeholder.

## Data Resolution

Download complete portal extracts for the relevant geography, health,
socioeconomic, country indicator, and revision tables, then filter locally. This
is safer than relying on paginated display pages.

For publication records:

- Apply the task's release filters first, usually `FINAL` plus value type and
  source type.
- When several eligible final records describe the same entity, year, and
  measure, select the highest final revision, then the latest release timestamp,
  then the stable row identifier as the final tie-breaker.
- Suppressed, blank, invalid-scale, invalid, or withdrawn values are unavailable
  unless the request explicitly says otherwise. Do not zero-fill them.
- Socioeconomic fields revise independently. A null in one field does not
  invalidate other fields unless the cohort definition requires all fields.
- For countries, reconcile requested labels through canonical labels and
  alternate labels to stable ISO-style identifiers. Count alias resolutions
  separately from exact canonical matches. Apply only revision events whose
  status authorizes use; unresolved scale-break cells remain anomalies.

Build reusable selected-record tables keyed by entity, year, measure, value
type, and source. All cohorts and models should consume these selected tables,
not raw duplicate release rows.

## Cohorts

Translate each request's cohort definition literally:

- Primary or reference cohorts are complete cases in the named reference year.
- Balanced panels are intersections of complete-case entities across all
  requested years.
- Machine-learning cohorts add completion for extra predictors required by the
  feature map.
- Strict dual-source cohorts require both primary and perturbation source series
  plus all adjustments for every registered year.
- County dynamic panels require complete baseline and end-year observations for
  every change interval. Validate RUCC values and region filters before forming
  panel rows.

Report cohort audits from the selected data: eligible geography universe,
selected row counts, annual complete counts, excluded identifiers, balanced
entity counts, panel rows, state counts, and any requested publication tokens.

## Statistical Implementation

Use deterministic numerical code and keep a single source of truth for design
matrices. Include an intercept when the registered design order lists one.

Linear models:

- For OLS and WLS, solve by QR or a stable least-squares routine. For reliability
  weights, multiply rows by the square root of the fixed selected weight.
- Use HC3 only where requested. Use cluster CR1 only where requested, with the
  registered cluster unit and finite-sample correction if the protocol requires
  it.
- For two-way fixed effects, residualize by entity and year or include the
  corresponding fixed-effect dummies, then report the focal coefficient in the
  requested scale.
- Delete-cluster or delete-state jackknife arrays must be aligned to the
  registered cluster order. Bias-corrected estimates use the standard
  jackknife correction from the full estimate and the mean deletion estimate.

GMM and mediation:

- Construct changes from selected records only, using the registered baseline
  and end years.
- Build instruments in the declared order, use the stated pseudoinverse cutoff,
  and compute the two-step weighting matrix from first-step residual moments.
- For mediation, keep total, path-a, path-b, and direct equations distinct.
  Compute indirect effects from unrounded path coefficients and use the
  registered cross-equation covariance or delta-method correction.

Nested prediction models:

- Split by the declared group, not by rows. Keep all rows from a held-out group
  out of training and inner validation.
- Standardize continuous features using training data only for each outer and
  inner fit. Reuse the same transformation for validation and test rows.
- Evaluate every grid point in the declared order. Choose by lowest inner RMSE;
  break exact ties by earliest grid order.
- For ridge, solve the penalized normal equations without penalizing the
  intercept. For elastic net, use deterministic coordinate descent and report
  the requested cycle or nonzero-count checkpoints.
- Pool out-of-fold predictions before computing pooled RMSE, MAE, R-squared, or
  Q-squared. Do not average fold metrics unless the template specifically asks
  for fold averages.

Bootstrap:

- Implement the exact named generator and seed from the request. Record every
  requested checkpoint after the corresponding replicate.
- Restricted-null bootstrap means refit or generate residuals under the null
  model described by the request, then compute the same t-statistic as the
  observed model.
- Use the requested weight distribution and cluster unit. Count absolute-tail or
  signed-tail exceedances exactly as declared, and use plus-one p-values when
  requested.
- Batch counts and quantiles are computed from the full unrounded replicate
  statistic vector, then rounded only for output.

Conformal calibration:

- Use the declared grouped split. Calibration groups and test groups must be
  disjoint from proper training groups.
- Compute residual scores from the source model named by the request.
- Use the finite-sample nearest-rank threshold specified by the protocol, most
  commonly `ceil((n_calibration + 1) * coverage)` for nominal coverage or
  `ceil((n_calibration + 1) * (1 - alpha))` for alpha notation, capped at the
  maximum available residual when needed.
- Report fold-level coverage, widths, MAE or excess diagnostics, then pool
  covered counts and held-out counts for aggregate coverage.

PCA, clustering, and stability:

- Build the feature matrix in the exact feature order. Center columns before
  covariance PCA; scale columns only when the request or methodology requires
  standardized variables.
- Orient components deterministically. For burden analyses, flip PC1 so higher
  PC1 means higher adverse burden when the requested indicators are worse in the
  same direction.
- Run deterministic k-means with the registered cluster count and initialization
  rule. Keep cluster labels stable by sorting or naming clusters according to
  the request, such as low, middle, and high burden by cluster mean PC1.
- For leave-year, leave-state, or delete-cluster stability, rebuild the reduced
  feature matrix, rerun PCA and clustering, align labels to the full-sample
  solution, and report adjusted Rand index plus any requested agreement counts.

Source perturbation and sensitivity:

- Enumerate perturbation scenarios exactly in the registered source, subset,
  bitmask, year, or source-group order.
- Do not retune models during no-retune perturbation audits. Reuse the full
  model's selected hyperparameters when requested.
- For exact Shapley attribution, average marginal coefficient changes over all
  coalitions in the registered player order and verify that the Shapley sum
  equals the all-replacement minus all-baseline coefficient after rounding.
- For partial-R2 sensitivity surfaces, compute every grid cell in the declared
  nested order and direction order from the unrounded baseline quantities.

## Decision and Validation

Evaluate controlled gates after all statistics are computed and rounded only for
reporting. Apply the request's precedence rule exactly: first failed module,
pass count, or named classification thresholds as written.

Before returning the answer:

- Check every required top-level key and nested key from the template.
- Check all list lengths and positional alignments.
- Check identifier ordering and exclusion-set completeness.
- Check integer, number, Boolean, enum, and `null` types.
- Check that every reported noninteger follows the requested decimal precision.
- Keep solution artifacts free of worked examples and task-specific numeric
  results.
