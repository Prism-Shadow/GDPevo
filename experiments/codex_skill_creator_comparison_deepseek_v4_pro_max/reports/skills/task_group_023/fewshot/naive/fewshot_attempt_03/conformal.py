"""
Grouped split conformal calibration and interval construction.

Builds symmetric inclusive intervals from sorted absolute residuals
using the nearest-rank quantile rule.
"""

import math


def conformal_interval(y_pred, calibration_residuals, coverage):
    """
    Compute conformal interval radius from calibration residuals.

    Args:
        y_pred: Single prediction value (or list).
        calibration_residuals: List of absolute residuals from calibration set.
        coverage: Nominal coverage fraction (e.g., 0.90).

    Returns:
        radius such that [y_pred - radius, y_pred + radius] is the interval.
    """
    m = len(calibration_residuals)
    if m == 0:
        return float('inf')

    sorted_scores = sorted(calibration_residuals)
    rank = min(m, math.ceil((m + 1) * coverage))
    radius = sorted_scores[rank - 1]  # one-based
    return radius


def calibrate_grouped(state_predictions, calibration_abs_residuals_by_state,
                      coverage):
    """
    Calibrate conformal with per-state maximum residual reduction.

    Args:
        state_predictions: Map state -> list of predictions.
        calibration_abs_residuals_by_state: Map state -> list of abs residuals.
        coverage: Nominal coverage.

    Returns:
        radius for symmetric inclusive intervals.
    """
    # Reduce to one maximum absolute residual per calibration state
    scores = []
    for state, residuals in calibration_abs_residuals_by_state.items():
        if residuals:
            scores.append(max(residuals))
    m = len(scores)
    if m == 0:
        return float('inf')

    scores.sort()
    rank = min(m, math.ceil((m + 1) * coverage))
    return scores[rank - 1]


def evaluate_coverage(holdout_predictions, holdout_actuals, interval_radius):
    """
    Compute coverage and mean width for a holdout fold.

    Args:
        holdout_predictions: List of predictions.
        holdout_actuals: List of actual values.
        interval_radius: Conformal radius.

    Returns:
        (covered_count, total_count, coverage_fraction, mean_width).
    """
    n = len(holdout_predictions)
    if n == 0:
        return 0, 0, 0.0, 0.0

    covered = 0
    for pred, actual in zip(holdout_predictions, holdout_actuals):
        if pred - interval_radius <= actual <= pred + interval_radius:
            covered += 1

    coverage_frac = covered / n
    mean_w = 2.0 * interval_radius
    return covered, n, coverage_frac, mean_w


def aggregate_conformal(fold_results):
    """
    Aggregate results across folds, weighting mean width by row counts.

    Args:
        fold_results: List of (covered, n, coverage, mean_width) tuples.

    Returns:
        (total_covered, total_n, aggregate_coverage, aggregate_mean_width).
    """
    total_covered = sum(r[0] for r in fold_results)
    total_n = sum(r[1] for r in fold_results)
    if total_n == 0:
        return 0, 0, 0.0, 0.0

    agg_coverage = total_covered / total_n
    agg_mean_width = sum(r[1] * r[3] for r in fold_results) / total_n
    return total_covered, total_n, agg_coverage, agg_mean_width
