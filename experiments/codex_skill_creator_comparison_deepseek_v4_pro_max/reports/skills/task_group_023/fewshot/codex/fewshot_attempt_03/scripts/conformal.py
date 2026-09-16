#!/usr/bin/env python3
"""Split conformal prediction with grouped folds as used in PHO audits.
"""

import math


def grouped_split_conformal_fold(train_X, train_y, test_X, test_y,
                                  calib_X, calib_y,
                                  alpha, lambda_penalty,
                                  standardize_func, ridge_func):
    X_tr_sc, means, sds = standardize_func(train_X)
    coef, intercept, _ = ridge_func(X_tr_sc, train_y, lambda_penalty)

    X_ca_sc = [[(calib_X[i][j] - means[j]) / sds[j] for j in range(len(calib_X[0]))]
               for i in range(len(calib_X))]
    calib_pred = [sum(X_ca_sc[i][j] * coef[j] for j in range(len(coef))) + intercept
                  for i in range(len(calib_X))]

    calib_res = [abs(calib_y[i] - calib_pred[i]) for i in range(len(calib_y))]
    calib_res.sort()

    m = len(calib_res)
    r = min(m, math.ceil((m + 1) * (1.0 - alpha)))
    threshold = float('inf') if r == 0 else calib_res[r - 1]

    X_te_sc = [[(test_X[i][j] - means[j]) / sds[j] for j in range(len(test_X[0]))]
               for i in range(len(test_X))]
    test_pred = [sum(X_te_sc[i][j] * coef[j] for j in range(len(coef))) + intercept
                 for i in range(len(test_X))]

    covered = sum(1 for i in range(len(test_y))
                  if test_pred[i] - threshold <= test_y[i] <= test_pred[i] + threshold)
    coverage = covered / len(test_y) if len(test_y) > 0 else 0.0
    mean_width = 2.0 * threshold
    test_mae = sum(abs(test_y[i] - test_pred[i]) for i in range(len(test_y))) / len(test_y) if test_y else 0.0

    return {
        'threshold': threshold,
        'fold_coverage': coverage,
        'fold_mean_width': mean_width,
        'fold_test_mae': test_mae,
        'calib_n': len(calib_y),
        'test_n': len(test_y),
        'proper_train_n': len(train_y),
        'fold_predictions': test_pred,
    }


def cross_fold_conformal(predictions, observations, fold_ids, nominal_coverage):
    n = len(observations)
    alpha = 1.0 - nominal_coverage
    unique_folds = sorted(set(fold_ids))

    results = []
    all_covered = 0
    all_n = 0

    for fold in unique_folds:
        fold_idx = [i for i in range(n) if fold_ids[i] == fold]
        calib_idx = [i for i in range(n) if fold_ids[i] != fold]

        calib_res = sorted([abs(observations[i] - predictions[i]) for i in calib_idx])
        m = len(calib_res)
        r = min(m, math.ceil((m + 1) * (1.0 - alpha)))
        radius = calib_res[r - 1] if r > 0 else float('inf')

        covered = sum(1 for i in fold_idx
                       if abs(observations[i] - predictions[i]) <= radius)
        coverage = covered / len(fold_idx) if fold_idx else 0.0
        mean_width = 2.0 * radius

        all_covered += covered
        all_n += len(fold_idx)

        results.append({
            'outer_fold': fold,
            'calibration_rows': m,
            'nearest_rank': r,
            'radius': radius,
            'held_out_rows': len(fold_idx),
            'coverage': coverage,
            'mean_width': mean_width,
        })

    overall_coverage = all_covered / all_n if all_n > 0 else 0.0
    return results, overall_coverage


def state_grouped_coverage(predictions, observations, state_ids, radius):
    states = {}
    for i, s in enumerate(state_ids):
        states.setdefault(s, []).append(i)

    result = []
    for s in sorted(states.keys()):
        idxs = states[s]
        covered = sum(1 for i in idxs if abs(observations[i] - predictions[i]) <= radius)
        result.append({
            'state_abbr': s,
            'panel_rows': len(idxs),
            'coverage': covered / len(idxs) if idxs else 0.0,
        })
    return result
