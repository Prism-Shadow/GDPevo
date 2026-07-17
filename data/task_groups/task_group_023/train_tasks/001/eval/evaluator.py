#!/usr/bin/env python3
"""Deterministic partial-credit evaluator for train task 001."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable


RAW_WEIGHTS = [1, 3, 3, 3, 3, 3, 3, 2]
TOTAL_WEIGHT = sum(RAW_WEIGHTS)
PRECISION = 4
HALF_UNIT = 0.5 * 10 ** -PRECISION
GOLD = json.loads((Path(__file__).resolve().parent.parent / "output" / "answer.json").read_text(encoding="utf-8"))


def nested(document: Any, *path: str) -> Any:
    current = document
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def exact(candidate: Any, expected: Any) -> float:
    return 1.0 if candidate == expected else 0.0


def number(candidate: Any, expected: float) -> float:
    if isinstance(candidate, bool):
        return 0.0
    try:
        value = float(candidate)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    return 1.0 if abs(round(value, PRECISION) - expected) <= HALF_UNIT + 1e-12 else 0.0


def state_f1(candidate: Any, expected: list[str]) -> float:
    if not isinstance(candidate, list) or not all(isinstance(x, str) for x in candidate):
        return 0.0
    predicted = {x.strip().upper() for x in candidate}
    target = set(expected)
    if not predicted and not target:
        return 1.0
    if not predicted or not target:
        return 0.0
    overlap = len(predicted & target)
    precision = overlap / len(predicted)
    recall = overlap / len(target)
    return 2 * precision * recall / (precision + recall)


def vector_fraction(candidate: Any, expected: list[Any], comparator: Callable[[Any, Any], float]) -> float:
    if not isinstance(candidate, list) or len(candidate) != len(expected):
        return 0.0
    return sum(comparator(x, y) for x, y in zip(candidate, expected)) / len(expected)


def matrix_fraction(candidate: Any, expected: list[list[Any]], comparator: Callable[[Any, Any], float]) -> float:
    if not isinstance(candidate, list) or len(candidate) != len(expected):
        return 0.0
    total = sum(len(row) for row in expected)
    if total == 0:
        return 1.0
    earned = 0.0
    for crow, erow in zip(candidate, expected):
        if isinstance(crow, list) and len(crow) == len(erow):
            earned += sum(comparator(x, y) for x, y in zip(crow, erow))
    return earned / total


def build_point(point_id: str, goal: str, raw_weight: int, subchecks: list[tuple[str, float, float]]) -> dict[str, Any]:
    earned_fraction = min(1.0, max(0.0, sum(share * result for _, share, result in subchecks)))
    normalized_max = raw_weight / TOTAL_WEIGHT
    return {
        "id": point_id,
        "goal": goal,
        "raw_weight": raw_weight,
        "normalized_max": normalized_max,
        "earned_fraction": earned_fraction,
        "earned_normalized_score": normalized_max * earned_fraction,
        "subchecks": [
            {
                "name": name,
                "point_fraction": share,
                "earned_fraction": round(result, 12),
                "passed": abs(result - 1.0) < 1e-12,
            }
            for name, share, result in subchecks
        ],
    }


def point_specs(p: dict[str, Any]) -> list[dict[str, Any]]:
    g = GOLD
    a, b, c, d = "publication_cohort", "delete_cluster_fixed_effects", "nested_ridge_division_cv", "wild_cluster_bootstrap"
    e, f, h, j = "grouped_split_conformal", "trajectory_pca_clustering", "source_year_perturbation", "robustness_decision"
    return [
        build_point("SP001", "Resolve all declared releases and establish the yearly, balanced, and broad cohorts.", 1, [
            ("universe_and_years", 0.10, exact((nested(p, a, "target_jurisdictions"), nested(p, a, "analysis_years")), (g[a]["target_jurisdictions"], g[a]["analysis_years"]))),
            ("resolved_record_counts", 0.10, exact((nested(p, a, "resolved_health_observations"), nested(p, a, "resolved_socioeconomic_records")), (g[a]["resolved_health_observations"], g[a]["resolved_socioeconomic_records"]))),
            ("yearly_core_counts", 0.15, vector_fraction(nested(p, a, "yearly_core_complete_n"), g[a]["yearly_core_complete_n"], exact)),
            ("balanced_dimensions", 0.15, exact((nested(p, a, "core_balanced_state_n"), nested(p, a, "core_balanced_observation_n")), (g[a]["core_balanced_state_n"], g[a]["core_balanced_observation_n"]))),
            ("balanced_excluded_states", 0.40, state_f1(nested(p, a, "core_balanced_excluded_state_codes"), g[a]["core_balanced_excluded_state_codes"])),
            ("broad_2023_count", 0.10, exact(nested(p, a, "broad_2023_complete_state_n"), g[a]["broad_2023_complete_state_n"])),
        ]),
        build_point("SP002", "Run the full delete-one-state fixed-effects jackknife and bias-corrected inference.", 3, [
            ("state_order", 0.05, vector_fraction(nested(p, b, "state_order"), g[b]["state_order"], exact)),
            ("panel_dimensions", 0.05, exact((nested(p, b, "state_n"), nested(p, b, "observation_n")), (g[b]["state_n"], g[b]["observation_n"]))),
            ("full_coefficient", 0.05, number(nested(p, b, "full_obesity_coefficient"), g[b]["full_obesity_coefficient"])),
            ("delete_coefficient_vector", 0.35, vector_fraction(nested(p, b, "delete_obesity_coefficients"), g[b]["delete_obesity_coefficients"], number)),
            ("delete_mean_and_jackknife_se", 0.15, 0.5 * number(nested(p, b, "delete_mean_coefficient"), g[b]["delete_mean_coefficient"]) + 0.5 * number(nested(p, b, "jackknife_standard_error"), g[b]["jackknife_standard_error"])),
            ("jackknife_t_and_p", 0.15, 0.5 * number(nested(p, b, "jackknife_t_statistic"), g[b]["jackknife_t_statistic"]) + 0.5 * number(nested(p, b, "jackknife_p_value"), g[b]["jackknife_p_value"])),
            ("bias_corrected_coefficient", 0.05, number(nested(p, b, "bias_corrected_obesity_coefficient"), g[b]["bias_corrected_obesity_coefficient"])),
            ("delete_extremes", 0.15, 0.25 * sum([
                exact(nested(p, b, "minimum_delete_state"), g[b]["minimum_delete_state"]),
                number(nested(p, b, "minimum_delete_coefficient"), g[b]["minimum_delete_coefficient"]),
                exact(nested(p, b, "maximum_delete_state"), g[b]["maximum_delete_state"]),
                number(nested(p, b, "maximum_delete_coefficient"), g[b]["maximum_delete_coefficient"]),
            ])),
        ]),
        build_point("SP003", "Execute nested division-blocked ridge tuning and full out-of-division prediction.", 3, [
            ("broad_cohort", 0.10, 0.25 * exact(nested(p, c, "broad_state_n"), g[c]["broad_state_n"]) + 0.75 * vector_fraction(nested(p, c, "broad_state_order"), g[c]["broad_state_order"], exact)),
            ("feature_division_and_grid_order", 0.10, (vector_fraction(nested(p, c, "feature_order"), g[c]["feature_order"], exact) + vector_fraction(nested(p, c, "division_order"), g[c]["division_order"], exact) + vector_fraction(nested(p, c, "lambda_grid"), g[c]["lambda_grid"], number)) / 3),
            ("outer_fold_counts", 0.10, 0.5 * vector_fraction(nested(p, c, "outer_train_n"), g[c]["outer_train_n"], exact) + 0.5 * vector_fraction(nested(p, c, "outer_test_n"), g[c]["outer_test_n"], exact)),
            ("selected_lambdas", 0.10, vector_fraction(nested(p, c, "selected_lambda"), g[c]["selected_lambda"], number)),
            ("inner_rmse_grid", 0.30, matrix_fraction(nested(p, c, "inner_rmse_grid"), g[c]["inner_rmse_grid"], number)),
            ("outer_rmse", 0.15, vector_fraction(nested(p, c, "outer_rmse"), g[c]["outer_rmse"], number)),
            ("pooled_metrics", 0.10, (number(nested(p, c, "pooled_rmse"), g[c]["pooled_rmse"]) + number(nested(p, c, "pooled_mae"), g[c]["pooled_mae"]) + number(nested(p, c, "pooled_q_squared"), g[c]["pooled_q_squared"])) / 3),
            ("worst_outer_division", 0.05, exact(nested(p, c, "worst_outer_division"), g[c]["worst_outer_division"])),
        ]),
        build_point("SP004", "Reproduce the declared PCG32 Webb-weight wild-cluster bootstrap-t audit.", 3, [
            ("seed_stream_and_replicates", 0.05, exact((nested(p, d, "seed"), nested(p, d, "stream"), nested(p, d, "replicate_n")), (g[d]["seed"], g[d]["stream"], g[d]["replicate_n"]))),
            ("state_order", 0.05, vector_fraction(nested(p, d, "state_order"), g[d]["state_order"], exact)),
            ("observed_fit", 0.10, (number(nested(p, d, "observed_obesity_coefficient"), g[d]["observed_obesity_coefficient"]) + number(nested(p, d, "observed_cr1_standard_error"), g[d]["observed_cr1_standard_error"]) + number(nested(p, d, "observed_t_statistic"), g[d]["observed_t_statistic"])) / 3),
            ("first_weight_index_rows", 0.25, matrix_fraction(nested(p, d, "first_three_weight_index_rows"), g[d]["first_three_weight_index_rows"], exact)),
            ("batch_exceedance_counts", 0.20, vector_fraction(nested(p, d, "batch_exceedance_counts"), g[d]["batch_exceedance_counts"], exact)),
            ("exceedance_and_p_value", 0.10, 0.5 * exact(nested(p, d, "exceedance_n"), g[d]["exceedance_n"]) + 0.5 * number(nested(p, d, "bootstrap_p_value"), g[d]["bootstrap_p_value"])),
            ("bootstrap_coefficient_summary", 0.10, 0.5 * number(nested(p, d, "bootstrap_coefficient_mean"), g[d]["bootstrap_coefficient_mean"]) + 0.5 * number(nested(p, d, "bootstrap_coefficient_sample_sd"), g[d]["bootstrap_coefficient_sample_sd"])),
            ("bootstrap_t_quantiles", 0.15, 0.2 * vector_fraction(nested(p, d, "t_quantile_probabilities"), g[d]["t_quantile_probabilities"], number) + 0.8 * vector_fraction(nested(p, d, "bootstrap_t_quantiles"), g[d]["bootstrap_t_quantiles"], number)),
        ]),
        build_point("SP005", "Construct all grouped split-conformal folds and aggregate calibrated coverage and width.", 3, [
            ("alpha_and_lambda", 0.05, 0.5 * number(nested(p, e, "alpha"), g[e]["alpha"]) + 0.5 * number(nested(p, e, "fixed_lambda"), g[e]["fixed_lambda"])),
            ("division_and_calibration_order", 0.10, 0.5 * vector_fraction(nested(p, e, "division_order"), g[e]["division_order"], exact) + 0.5 * vector_fraction(nested(p, e, "calibration_division"), g[e]["calibration_division"], exact)),
            ("fold_sizes", 0.15, (vector_fraction(nested(p, e, "proper_train_n"), g[e]["proper_train_n"], exact) + vector_fraction(nested(p, e, "calibration_n"), g[e]["calibration_n"], exact) + vector_fraction(nested(p, e, "test_n"), g[e]["test_n"], exact)) / 3),
            ("thresholds", 0.20, vector_fraction(nested(p, e, "threshold"), g[e]["threshold"], number)),
            ("fold_coverage", 0.15, vector_fraction(nested(p, e, "fold_coverage"), g[e]["fold_coverage"], number)),
            ("fold_mean_width", 0.15, vector_fraction(nested(p, e, "fold_mean_width"), g[e]["fold_mean_width"], number)),
            ("fold_test_mae", 0.10, vector_fraction(nested(p, e, "fold_test_mae"), g[e]["fold_test_mae"], number)),
            ("aggregate_coverage_and_width", 0.10, 0.5 * number(nested(p, e, "aggregate_coverage"), g[e]["aggregate_coverage"]) + 0.5 * number(nested(p, e, "aggregate_mean_width"), g[e]["aggregate_mean_width"])),
        ]),
        build_point("SP006", "Reproduce trajectory PCA, deterministic clustering, and five leave-year-out stability refits.", 3, [
            ("state_and_feature_order", 0.05, 0.5 * vector_fraction(nested(p, f, "state_order"), g[f]["state_order"], exact) + 0.5 * vector_fraction(nested(p, f, "feature_order"), g[f]["feature_order"], exact)),
            ("eigenvalues_and_explained_ratios", 0.10, (vector_fraction(nested(p, f, "first_two_eigenvalues"), g[f]["first_two_eigenvalues"], number) + vector_fraction(nested(p, f, "first_two_explained_ratios"), g[f]["first_two_explained_ratios"], number) + number(nested(p, f, "first_two_cumulative_explained_ratio"), g[f]["first_two_cumulative_explained_ratio"])) / 3),
            ("component_loadings", 0.20, 0.5 * vector_fraction(nested(p, f, "pc1_loadings"), g[f]["pc1_loadings"], number) + 0.5 * vector_fraction(nested(p, f, "pc2_loadings"), g[f]["pc2_loadings"], number)),
            ("component_scores", 0.20, 0.5 * vector_fraction(nested(p, f, "pc1_scores"), g[f]["pc1_scores"], number) + 0.5 * vector_fraction(nested(p, f, "pc2_scores"), g[f]["pc2_scores"], number)),
            ("initial_centroids", 0.05, vector_fraction(nested(p, f, "initial_centroid_states"), g[f]["initial_centroid_states"], exact)),
            ("cluster_centroids", 0.10, matrix_fraction(nested(p, f, "cluster_centroids"), g[f]["cluster_centroids"], number)),
            ("cluster_sizes_and_labels", 0.15, 0.25 * vector_fraction(nested(p, f, "cluster_sizes"), g[f]["cluster_sizes"], exact) + 0.75 * vector_fraction(nested(p, f, "cluster_labels"), g[f]["cluster_labels"], exact)),
            ("leave_year_out_ari", 0.10, 0.2 * vector_fraction(nested(p, f, "leave_year_out_order"), g[f]["leave_year_out_order"], exact) + 0.8 * vector_fraction(nested(p, f, "leave_year_out_adjusted_rand_index"), g[f]["leave_year_out_adjusted_rand_index"], number)),
            ("leave_year_out_agreement", 0.05, vector_fraction(nested(p, f, "leave_year_out_aligned_agreement"), g[f]["leave_year_out_aligned_agreement"], number)),
        ]),
        build_point("SP007", "Exhaustively refit both exposure sources over all 16 three-to-five-year subsets.", 3, [
            ("strict_cohort", 0.10, 0.25 * exact((nested(p, h, "strict_state_n"), nested(p, h, "strict_observation_n")), (g[h]["strict_state_n"], g[h]["strict_observation_n"])) + 0.75 * state_f1(nested(p, h, "strict_excluded_state_codes"), g[h]["strict_excluded_state_codes"])),
            ("subset_order", 0.10, vector_fraction(nested(p, h, "subset_order"), g[h]["subset_order"], exact)),
            ("primary_coefficients", 0.15, vector_fraction(nested(p, h, "primary_obesity_coefficients"), g[h]["primary_obesity_coefficients"], number)),
            ("parallel_coefficients", 0.15, vector_fraction(nested(p, h, "parallel_obesity_coefficients"), g[h]["parallel_obesity_coefficients"], number)),
            ("primary_cr1_p_values", 0.10, vector_fraction(nested(p, h, "primary_cr1_p_values"), g[h]["primary_cr1_p_values"], number)),
            ("parallel_cr1_p_values", 0.10, vector_fraction(nested(p, h, "parallel_cr1_p_values"), g[h]["parallel_cr1_p_values"], number)),
            ("percent_shift_vector", 0.15, vector_fraction(nested(p, h, "absolute_percent_shifts"), g[h]["absolute_percent_shifts"], number)),
            ("same_sign_summary", 0.05, 0.5 * exact(nested(p, h, "same_sign_subset_n"), g[h]["same_sign_subset_n"]) + 0.5 * number(nested(p, h, "same_sign_subset_fraction"), g[h]["same_sign_subset_fraction"])),
            ("shift_summaries_and_worst_subset", 0.10, (number(nested(p, h, "median_absolute_percent_shift"), g[h]["median_absolute_percent_shift"]) + number(nested(p, h, "maximum_absolute_percent_shift"), g[h]["maximum_absolute_percent_shift"]) + exact(nested(p, h, "worst_shift_subset"), g[h]["worst_shift_subset"])) / 3),
        ]),
        build_point("SP008", "Apply all six robustness gates and the controlled transportability classification.", 2, [
            ("delete_cluster_fe_gate", 0.10, exact(nested(p, j, "delete_cluster_fe"), g[j]["delete_cluster_fe"])),
            ("nested_ridge_gate", 0.10, exact(nested(p, j, "nested_ridge"), g[j]["nested_ridge"])),
            ("wild_cluster_bootstrap_gate", 0.10, exact(nested(p, j, "wild_cluster_bootstrap"), g[j]["wild_cluster_bootstrap"])),
            ("grouped_split_conformal_gate", 0.10, exact(nested(p, j, "grouped_split_conformal"), g[j]["grouped_split_conformal"])),
            ("trajectory_stability_gate", 0.10, exact(nested(p, j, "trajectory_stability"), g[j]["trajectory_stability"])),
            ("source_year_stability_gate", 0.10, exact(nested(p, j, "source_year_stability"), g[j]["source_year_stability"])),
            ("passed_gate_count", 0.10, exact(nested(p, j, "passed_gate_count"), g[j]["passed_gate_count"])),
            ("classification", 0.30, exact(nested(p, j, "classification"), g[j]["classification"])),
        ]),
    ]


def zero_result(reason: str) -> dict[str, Any]:
    points = [build_point(f"SP{i:03d}", "Submission unavailable for scoring.", w, [("unavailable", 1.0, 0.0)]) for i, w in enumerate(RAW_WEIGHTS, 1)]
    return {"score": 0.0, "max_score": 1.0, "raw_weight_total": TOTAL_WEIGHT, "rubric": points, "diagnostics": {"prediction_parsed": False, "reason": reason}}


def evaluate(path: Path) -> dict[str, Any]:
    try:
        prediction = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return zero_result("prediction file not found")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return zero_result(f"prediction could not be parsed: {type(exc).__name__}")
    if not isinstance(prediction, dict):
        return zero_result("prediction root must be a JSON object")
    points = point_specs(prediction)
    for point in points:
        point_pass = all(item.get("passed") is True for item in point["subchecks"])
        point["diagnostic_fraction"] = point["earned_fraction"]
        point["point_pass"] = point_pass
        point["earned_fraction"] = 1.0 if point_pass else 0.0
        point["earned_normalized_score"] = point["normalized_max"] if point_pass else 0.0
    score = sum(point["earned_normalized_score"] for point in points)
    return {
        "score": min(1.0, max(0.0, score)),
        "max_score": 1.0,
        "raw_weight_total": TOTAL_WEIGHT,
        "rubric": points,
        "diagnostics": {
            "prediction_parsed": True,
            "numeric_precision": PRECISION,
            "numeric_tolerance": HALF_UNIT,
            "point_scoring": "Every subcheck in a rubric point must pass for the point to earn its full normalized weight; otherwise the point earns zero.",
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        result = zero_result("usage: evaluator.py PREDICTION_JSON")
    else:
        result = evaluate(Path(argv[1]))
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
