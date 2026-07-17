#!/usr/bin/env python3
"""Deterministic whole-point evaluator for test task 001."""

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


def mean_score(*results: float) -> float:
    """Average a small set of commensurate semantic checks."""
    return sum(results) / len(results) if results else 0.0


def integrity_level(matched_fraction: float) -> float:
    """Convert element matches into explicit audit-completeness levels.

    A long audit is not twenty independent business accomplishments.  These
    levels reward useful partial work without allowing one mostly-correct
    vector to dominate a rubric point.
    """
    if matched_fraction >= 1.0 - 1e-12:
        return 1.0
    if matched_fraction >= 0.90:
        return 0.75
    if matched_fraction >= 0.60:
        return 0.50
    if matched_fraction > 0.0:
        return 0.25
    return 0.0


def bundle_level(*results: float) -> float:
    """Give fair, declared levels for a small semantic result bundle."""
    if not results:
        return 0.0
    if all(abs(result - 1.0) < 1e-12 for result in results):
        return 1.0
    average = mean_score(*results)
    if average >= 0.75:
        return 0.75
    if average >= 0.50:
        return 0.50
    if average > 0.0:
        return 0.25
    return 0.0


def critical_with_evidence(critical: float, evidence: float) -> float:
    """Bind supporting arrays to the critical key or summary they audit.

    With a correct critical result, complete evidence earns full credit.  If
    the critical result is absent or wrong, even perfect supporting evidence
    can earn only 20% of that semantic module.
    """
    critical = min(1.0, max(0.0, critical))
    evidence = min(1.0, max(0.0, evidence))
    if critical >= 1.0 - 1e-12:
        return 0.60 + 0.40 * evidence
    if critical >= 0.75:
        return min(0.75, 0.35 + 0.40 * evidence)
    if critical >= 0.50:
        return min(0.50, 0.20 + 0.30 * evidence)
    if critical > 0.0:
        return min(0.30, 0.10 + 0.20 * evidence)
    return 0.20 * evidence


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
            ("broad_2024_count", 0.10, exact(nested(p, a, "broad_2024_complete_state_n"), g[a]["broad_2024_complete_state_n"])),
        ]),
        build_point("SP002", "Run the full delete-one-state fixed-effects jackknife and bias-corrected inference.", 3, [
            ("panel_and_state_order_integrity", 0.15, critical_with_evidence(
                exact((nested(p, b, "state_n"), nested(p, b, "observation_n")), (g[b]["state_n"], g[b]["observation_n"])),
                integrity_level(vector_fraction(nested(p, b, "state_order"), g[b]["state_order"], exact)),
            )),
            ("full_fit_and_ordered_delete_audit", 0.35, critical_with_evidence(
                number(nested(p, b, "full_food_coefficient"), g[b]["full_food_coefficient"]),
                integrity_level(vector_fraction(nested(p, b, "delete_food_coefficients"), g[b]["delete_food_coefficients"], number)),
            )),
            ("jackknife_inference_summary", 0.30, bundle_level(
                number(nested(p, b, "delete_mean_coefficient"), g[b]["delete_mean_coefficient"]),
                number(nested(p, b, "jackknife_standard_error"), g[b]["jackknife_standard_error"]),
                number(nested(p, b, "jackknife_t_statistic"), g[b]["jackknife_t_statistic"]),
                number(nested(p, b, "jackknife_p_value"), g[b]["jackknife_p_value"]),
            )),
            ("bias_and_delete_extremes", 0.20, bundle_level(
                number(nested(p, b, "bias_corrected_food_coefficient"), g[b]["bias_corrected_food_coefficient"]),
                exact(nested(p, b, "minimum_delete_state"), g[b]["minimum_delete_state"]),
                number(nested(p, b, "minimum_delete_coefficient"), g[b]["minimum_delete_coefficient"]),
                exact(nested(p, b, "maximum_delete_state"), g[b]["maximum_delete_state"]),
                number(nested(p, b, "maximum_delete_coefficient"), g[b]["maximum_delete_coefficient"]),
            )),
        ]),
        build_point("SP003", "Execute nested division-blocked ridge tuning and full out-of-division prediction.", 3, [
            ("cohort_feature_and_fold_order_integrity", 0.20, bundle_level(
                exact(nested(p, c, "broad_state_n"), g[c]["broad_state_n"]),
                integrity_level(vector_fraction(nested(p, c, "broad_state_order"), g[c]["broad_state_order"], exact)),
                integrity_level(vector_fraction(nested(p, c, "feature_order"), g[c]["feature_order"], exact)),
                integrity_level(vector_fraction(nested(p, c, "division_order"), g[c]["division_order"], exact)),
                integrity_level(vector_fraction(nested(p, c, "lambda_grid"), g[c]["lambda_grid"], number)),
            )),
            ("ordered_inner_grid_and_selection_audit", 0.45, critical_with_evidence(
                bundle_level(
                    integrity_level(vector_fraction(nested(p, c, "outer_train_n"), g[c]["outer_train_n"], exact)),
                    integrity_level(vector_fraction(nested(p, c, "outer_test_n"), g[c]["outer_test_n"], exact)),
                    integrity_level(vector_fraction(nested(p, c, "selected_lambda"), g[c]["selected_lambda"], number)),
                ),
                integrity_level(matrix_fraction(nested(p, c, "inner_rmse_grid"), g[c]["inner_rmse_grid"], number)),
            )),
            ("outer_prediction_and_pooled_validation", 0.35, critical_with_evidence(
                bundle_level(
                    number(nested(p, c, "pooled_rmse"), g[c]["pooled_rmse"]),
                    number(nested(p, c, "pooled_mae"), g[c]["pooled_mae"]),
                    number(nested(p, c, "pooled_q_squared"), g[c]["pooled_q_squared"]),
                    exact(nested(p, c, "worst_outer_division"), g[c]["worst_outer_division"]),
                ),
                integrity_level(vector_fraction(nested(p, c, "outer_rmse"), g[c]["outer_rmse"], number)),
            )),
        ]),
        build_point("SP004", "Reproduce the declared PCG32 Webb-weight wild-cluster bootstrap-t audit.", 3, [
            ("protocol_and_observed_fit", 0.15, bundle_level(
                exact((nested(p, d, "seed"), nested(p, d, "stream"), nested(p, d, "replicate_n")), (g[d]["seed"], g[d]["stream"], g[d]["replicate_n"])),
                number(nested(p, d, "observed_food_coefficient"), g[d]["observed_food_coefficient"]),
                number(nested(p, d, "observed_cr1_standard_error"), g[d]["observed_cr1_standard_error"]),
                number(nested(p, d, "observed_t_statistic"), g[d]["observed_t_statistic"]),
            )),
            ("ordered_random_stream_checkpoints", 0.25, critical_with_evidence(
                integrity_level(vector_fraction(nested(p, d, "state_order"), g[d]["state_order"], exact)),
                integrity_level(matrix_fraction(nested(p, d, "first_three_weight_index_rows"), g[d]["first_three_weight_index_rows"], exact)),
            )),
            ("replicate_exceedance_and_inference_integrity", 0.35, critical_with_evidence(
                bundle_level(
                    exact(nested(p, d, "exceedance_n"), g[d]["exceedance_n"]),
                    number(nested(p, d, "bootstrap_p_value"), g[d]["bootstrap_p_value"]),
                ),
                integrity_level(vector_fraction(nested(p, d, "batch_exceedance_counts"), g[d]["batch_exceedance_counts"], exact)),
            )),
            ("bootstrap_distribution_summary", 0.25,
                0.40 * bundle_level(
                    number(nested(p, d, "bootstrap_coefficient_mean"), g[d]["bootstrap_coefficient_mean"]),
                    number(nested(p, d, "bootstrap_coefficient_sample_sd"), g[d]["bootstrap_coefficient_sample_sd"]),
                )
                + 0.60 * critical_with_evidence(
                    integrity_level(vector_fraction(nested(p, d, "bootstrap_t_quantiles"), g[d]["bootstrap_t_quantiles"], number)),
                    integrity_level(vector_fraction(nested(p, d, "t_quantile_probabilities"), g[d]["t_quantile_probabilities"], number)),
                )
            ),
        ]),
        build_point("SP005", "Construct all grouped split-conformal folds and aggregate calibrated coverage and width.", 3, [
            ("ordered_fold_assignment_and_sizes", 0.20, critical_with_evidence(
                bundle_level(
                    integrity_level(vector_fraction(nested(p, e, "division_order"), g[e]["division_order"], exact)),
                    integrity_level(vector_fraction(nested(p, e, "calibration_division"), g[e]["calibration_division"], exact)),
                ),
                bundle_level(
                    integrity_level(vector_fraction(nested(p, e, "proper_train_n"), g[e]["proper_train_n"], exact)),
                    integrity_level(vector_fraction(nested(p, e, "calibration_n"), g[e]["calibration_n"], exact)),
                    integrity_level(vector_fraction(nested(p, e, "test_n"), g[e]["test_n"], exact)),
                ),
            )),
            ("calibration_protocol_and_threshold_audit", 0.25, critical_with_evidence(
                bundle_level(
                    number(nested(p, e, "alpha"), g[e]["alpha"]),
                    number(nested(p, e, "fixed_lambda"), g[e]["fixed_lambda"]),
                ),
                integrity_level(vector_fraction(nested(p, e, "threshold"), g[e]["threshold"], number)),
            )),
            ("ordered_fold_performance_audit", 0.35, bundle_level(
                integrity_level(vector_fraction(nested(p, e, "fold_coverage"), g[e]["fold_coverage"], number)),
                integrity_level(vector_fraction(nested(p, e, "fold_mean_width"), g[e]["fold_mean_width"], number)),
                integrity_level(vector_fraction(nested(p, e, "fold_test_mae"), g[e]["fold_test_mae"], number)),
            )),
            ("aggregate_coverage_and_width_summary", 0.20, bundle_level(
                number(nested(p, e, "aggregate_coverage"), g[e]["aggregate_coverage"]),
                number(nested(p, e, "aggregate_mean_width"), g[e]["aggregate_mean_width"]),
            )),
        ]),
        build_point("SP006", "Reproduce trajectory PCA, deterministic clustering, and five leave-year-out stability refits.", 3, [
            ("ordered_eigensystem_summary", 0.20, critical_with_evidence(
                bundle_level(
                    integrity_level(vector_fraction(nested(p, f, "state_order"), g[f]["state_order"], exact)),
                    integrity_level(vector_fraction(nested(p, f, "feature_order"), g[f]["feature_order"], exact)),
                ),
                bundle_level(
                    integrity_level(vector_fraction(nested(p, f, "first_two_eigenvalues"), g[f]["first_two_eigenvalues"], number)),
                    integrity_level(vector_fraction(nested(p, f, "first_two_explained_ratios"), g[f]["first_two_explained_ratios"], number)),
                    number(nested(p, f, "first_two_cumulative_explained_ratio"), g[f]["first_two_cumulative_explained_ratio"]),
                ),
            )),
            ("loadings_and_state_score_audit", 0.30, bundle_level(
                integrity_level(vector_fraction(nested(p, f, "pc1_loadings"), g[f]["pc1_loadings"], number)),
                integrity_level(vector_fraction(nested(p, f, "pc2_loadings"), g[f]["pc2_loadings"], number)),
                integrity_level(vector_fraction(nested(p, f, "pc1_scores"), g[f]["pc1_scores"], number)),
                integrity_level(vector_fraction(nested(p, f, "pc2_scores"), g[f]["pc2_scores"], number)),
            )),
            ("deterministic_clustering_integrity", 0.25, critical_with_evidence(
                bundle_level(
                    integrity_level(vector_fraction(nested(p, f, "initial_centroid_states"), g[f]["initial_centroid_states"], exact)),
                    integrity_level(vector_fraction(nested(p, f, "cluster_sizes"), g[f]["cluster_sizes"], exact)),
                ),
                bundle_level(
                    integrity_level(matrix_fraction(nested(p, f, "cluster_centroids"), g[f]["cluster_centroids"], number)),
                    integrity_level(vector_fraction(nested(p, f, "cluster_labels"), g[f]["cluster_labels"], exact)),
                ),
            )),
            ("leave_year_out_stability_and_alignment", 0.25, critical_with_evidence(
                integrity_level(vector_fraction(nested(p, f, "leave_year_out_order"), g[f]["leave_year_out_order"], exact)),
                bundle_level(
                    integrity_level(vector_fraction(nested(p, f, "leave_year_out_adjusted_rand_index"), g[f]["leave_year_out_adjusted_rand_index"], number)),
                    integrity_level(vector_fraction(nested(p, f, "leave_year_out_aligned_agreement"), g[f]["leave_year_out_aligned_agreement"], number)),
                ),
            )),
        ]),
        build_point("SP007", "Exhaustively refit both exposure sources over all 16 three-to-five-year subsets.", 3, [
            ("strict_dual_source_cohort", 0.15, critical_with_evidence(
                exact((nested(p, h, "strict_state_n"), nested(p, h, "strict_observation_n")), (g[h]["strict_state_n"], g[h]["strict_observation_n"])),
                state_f1(nested(p, h, "strict_excluded_state_codes"), g[h]["strict_excluded_state_codes"]),
            )),
            ("ordered_subset_coefficient_audit", 0.35, critical_with_evidence(
                integrity_level(vector_fraction(nested(p, h, "subset_order"), g[h]["subset_order"], exact)),
                bundle_level(
                    integrity_level(vector_fraction(nested(p, h, "primary_food_coefficients"), g[h]["primary_food_coefficients"], number)),
                    integrity_level(vector_fraction(nested(p, h, "parallel_food_coefficients"), g[h]["parallel_food_coefficients"], number)),
                ),
            )),
            ("ordered_inference_and_shift_audit", 0.30, critical_with_evidence(
                integrity_level(vector_fraction(nested(p, h, "subset_order"), g[h]["subset_order"], exact)),
                bundle_level(
                    integrity_level(vector_fraction(nested(p, h, "primary_cr1_p_values"), g[h]["primary_cr1_p_values"], number)),
                    integrity_level(vector_fraction(nested(p, h, "parallel_cr1_p_values"), g[h]["parallel_cr1_p_values"], number)),
                    integrity_level(vector_fraction(nested(p, h, "absolute_percent_shifts"), g[h]["absolute_percent_shifts"], number)),
                ),
            )),
            ("source_shift_stability_summary", 0.20,
                0.45 * bundle_level(
                    exact(nested(p, h, "same_sign_subset_n"), g[h]["same_sign_subset_n"]),
                    number(nested(p, h, "same_sign_subset_fraction"), g[h]["same_sign_subset_fraction"]),
                )
                + 0.55 * bundle_level(
                    number(nested(p, h, "median_absolute_percent_shift"), g[h]["median_absolute_percent_shift"]),
                    number(nested(p, h, "maximum_absolute_percent_shift"), g[h]["maximum_absolute_percent_shift"]),
                    exact(nested(p, h, "worst_shift_subset"), g[h]["worst_shift_subset"]),
                )
            ),
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
    required_subchecks = {
        "SP001": {
            "resolved_record_counts",
            "yearly_core_counts",
            "balanced_dimensions",
            "balanced_excluded_states",
            "broad_2024_count",
        },
        "SP002": {"bias_and_delete_extremes"},
        "SP003": {"outer_prediction_and_pooled_validation"},
        "SP004": {"replicate_exceedance_and_inference_integrity"},
        "SP005": {"aggregate_coverage_and_width_summary"},
        "SP006": {"leave_year_out_stability_and_alignment"},
        "SP007": {"strict_dual_source_cohort"},
        "SP008": {"classification"},
    }
    for point in points:
        by_name = {item["name"]: item for item in point["subchecks"]}
        required = required_subchecks[point["id"]]
        point_pass = all(by_name.get(name, {}).get("passed") is True for name in required)
        point["point_pass"] = point_pass
        point["earned_fraction"] = 1.0 if point_pass else 0.0
        point["earned_normalized_score"] = point["normalized_max"] if point_pass else 0.0
        point["required_subchecks"] = sorted(required)
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
            "point_scoring": "Each rubric point earns its full normalized weight only when every named required subcheck passes; otherwise it earns zero.",
            "supporting_diagnostics": "Non-required subchecks are reported only to make errors auditable and never create fractional point credit.",
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
