# Grouped Split Conformal Calibration

## Partition Strategy

For each ordered group g in declared order:
1. Test fold: group g.
2. Calibration fold: among remaining groups, select the one with greatest row count; tie-break by ascending group name.
3. Proper training folds: all remaining groups not in test or calibration.
4. If only one group remains after test selection, use it as calibration and leave proper training empty (edge case; handle gracefully).

## Model Fitting

For each outer fold:
1. Fit the declared model on proper training rows from scratch.
2. Use the exact same algorithm, penalty, and hyperparameters as the source model (if reusing a prediction source) or as declared.
3. Predict calibration rows and test rows.
4. Compute absolute residuals for calibration rows: |y_i - yhat_i|.

## Calibration Threshold

1. Sort the m calibration absolute residuals ascending.
2. Compute rank r = min(m, ceil((m + 1) * (1 - alpha))) using one-based indexing.
3. The threshold q = sorted_residuals[r-1] (the r-th smallest residual).
4. If r > m, use q = max(residuals) (should not happen with the min guard).

Alternative for state-grouped conformal with per-state maxima:
- For each calibration state, compute the maximum absolute residual across its counties.
- Use these state-maxima (m = number of calibration states) as the scores.
- q = k-th smallest state maximum where k = min(m, ceil((m + 1) * coverage)).

## Prediction Intervals

For each test observation with prediction yhat:
- Interval = [yhat - q, yhat + q]
- Coverage check: y_i in [yhat - q, yhat + q] (inclusive)
- Interval width = 2 * q

## Aggregation

For each fold:
- fold_coverage = covered_count / test_n
- fold_mean_width = 2 * q  (or mean of 2 * q_i if per-state q)
- fold_test_mae = mean(|y_i - yhat_i|) for test rows

Pooled:
- aggregate_coverage = sum(covered_count across folds) / sum(test_n across folds)
- aggregate_mean_width = sum(test_n_fold * mean_width_fold) / sum(test_n across folds)
  i.e. weighted by test row counts

## Worst Division/State

Select the worst by smallest unrounded coverage fraction, tie-broken by earlier declared order.

## Subgroup Reporting

When reporting state-level, RUCC-band, or prediction-decile coverage:
- Partition test rows by the declared grouping attribute.
- Within each subgroup, compute coverage = covered / total.
- For prediction deciles: sort all test rows by prediction value, assign deciles by rank (equal-sized bins with remainders assigned to earlier bins as declared), and compute prediction_mean, observation_mean, and signed_gap = prediction_mean - observation_mean.

## Minimum State Coverage

The smallest unrounded state coverage value across all states. Used for decision gates.
