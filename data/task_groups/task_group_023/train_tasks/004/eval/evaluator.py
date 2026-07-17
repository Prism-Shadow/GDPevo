#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

WEIGHTS = [1, 3, 3, 3, 3, 3, 3, 2]
TOTAL = sum(WEIGHTS)
GOALS = [
    "Reconcile releases and construct the 2024 primary and strict balanced cohorts.",
    "Reproduce the ordered delete-one-division reliability-weighted jackknife.",
    "Reproduce every grouped nested elastic-net grid, fold diagnostic, and pooled metric.",
    "Reproduce the seeded wild-division bootstrap-t stream, checkpoints, and test.",
    "Construct the grouped out-of-fold conformal intervals and division diagnostics.",
    "Reproduce trajectory PCA, deterministic clustering, and leave-one-year stability.",
    "Enumerate all direct-versus-rollup scenarios and reproduce the Shapley decomposition.",
    "Apply all six registered flags and the precedence decision.",
]
GOLD = json.loads((Path(__file__).resolve().parent.parent / "output" / "answer.json").read_text(encoding="utf-8"))
MISSING = object()


def zero_result(message):
    return {
        "score": 0.0,
        "total_raw_weight": TOTAL,
        "points": [
            {
                "point_id": f"SP{i:03d}", "goal": goal, "raw_weight": weight,
                "normalized_maximum": round(weight / TOTAL, 10),
                "earned_fraction": 0.0, "earned_normalized_score": 0.0,
                "subchecks": [],
            }
            for i, (goal, weight) in enumerate(zip(GOALS, WEIGHTS), 1)
        ],
        "diagnostics": [message],
    }


if len(sys.argv) != 2:
    print(json.dumps(zero_result("Usage: eval.sh <prediction.json>"), indent=2))
    raise SystemExit(0)
try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        prediction = json.load(handle)
    if not isinstance(prediction, dict):
        raise ValueError("prediction root must be an object")
except Exception as exc:
    print(json.dumps(zero_result(f"Prediction parse failure: {exc}"), indent=2))
    raise SystemExit(0)


def at(root, path):
    current = root
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return MISSING
        current = current[key]
    return current


def exact(value, expected):
    return 1.0 if value == expected and type(value) is type(expected) else 0.0


def number(value, expected):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return 0.0
    return 1.0 if abs(float(value) - float(expected)) <= 0.00011 else 0.0


def scalar(path):
    value, expected = at(prediction, path), at(GOLD, path)
    return number(value, expected) if isinstance(expected, float) else exact(value, expected)


def item_score(value, expected, fields):
    if not isinstance(value, dict):
        return 0.0
    scores = []
    for field in fields:
        actual, target = value.get(field, MISSING), expected[field]
        scores.append(number(actual, target) if isinstance(target, float) else exact(actual, target))
    return sum(scores) / len(scores)


def object_list(path, fields):
    value, expected = at(prediction, path), at(GOLD, path)
    if not isinstance(value, list):
        return 0.0
    positional = sum(
        item_score(value[i], target, fields) if i < len(value) else 0.0
        for i, target in enumerate(expected)
    ) / len(expected)
    return positional * min(1.0, len(expected) / max(len(value), 1))


def value_list(path):
    value, expected = at(prediction, path), at(GOLD, path)
    if not isinstance(value, list):
        return 0.0
    scores = []
    for i, target in enumerate(expected):
        if i >= len(value):
            scores.append(0.0)
        else:
            scores.append(number(value[i], target) if isinstance(target, float) else exact(value[i], target))
    return sum(scores) / len(scores) * min(1.0, len(expected) / max(len(value), 1))


def outer_fold_score():
    value, expected = at(prediction, "nested_elastic_net.outer_folds"), at(GOLD, "nested_elastic_net.outer_folds")
    if not isinstance(value, list):
        return 0.0
    scores = []
    simple_fields = ["held_out_division", "held_out_count", "chosen_lambda", "nonzero_feature_count", "coordinate_cycles", "outer_rmse"]
    for i, target in enumerate(expected):
        if i >= len(value) or not isinstance(value[i], dict):
            scores.append(0.0)
            continue
        actual = value[i]
        simple = item_score(actual, target, simple_fields)
        actual_grid, target_grid = actual.get("inner_grid"), target["inner_grid"]
        if isinstance(actual_grid, list):
            grid = sum(
                item_score(actual_grid[j], grid_target, ["lambda", "inner_grouped_rmse"])
                if j < len(actual_grid) else 0.0
                for j, grid_target in enumerate(target_grid)
            ) / len(target_grid)
            grid *= min(1.0, len(target_grid) / max(len(actual_grid), 1))
        else:
            grid = 0.0
        scores.append(0.35 * simple + 0.65 * grid)
    return sum(scores) / len(scores) * min(1.0, len(expected) / max(len(value), 1))


points = []


def add_point(index, checks):
    weight = WEIGHTS[index]
    share_total = sum(share for _, _, share in checks)
    fraction = sum(score * share for _, score, share in checks) / share_total
    points.append({
        "point_id": f"SP{index + 1:03d}", "goal": GOALS[index], "raw_weight": weight,
        "normalized_maximum": round(weight / TOTAL, 10),
        "earned_fraction": round(fraction, 10),
        "earned_normalized_score": round(fraction * weight / TOTAL, 10),
        "subchecks": [
            {
                "name": name, "within_point_share": round(share / share_total, 10),
                "earned_fraction": round(score, 10), "passed": abs(score - 1.0) <= 1e-12,
            }
            for name, score, share in checks
        ],
    })


add_point(0, [
    ("request id", scalar("request_id"), .05),
    ("reference year and universe", (scalar("release_and_cohort.reference_year") + scalar("release_and_cohort.jurisdiction_universe_count")) / 2, .10),
    ("ordered annual complete-case counts", object_list("release_and_cohort.yearly_complete_case_counts", ["year", "count"]), .25),
    ("primary complete-case count", scalar("release_and_cohort.primary_complete_case_count"), .10),
    ("ordered primary exclusions", value_list("release_and_cohort.primary_excluded_state_codes"), .15),
    ("balanced state count", scalar("release_and_cohort.balanced_state_count"), .10),
    ("ordered balanced state codes", value_list("release_and_cohort.balanced_state_codes"), .25),
])
add_point(1, [
    ("cluster definition and full coefficient", (scalar("cluster_jackknife.cluster_definition") + scalar("cluster_jackknife.full_weighted_food_insecurity_coefficient")) / 2, .08),
    ("ordered delete-one-cluster diagnostics", object_list("cluster_jackknife.delete_one_cluster_results", ["deleted_division", "deleted_state_count", "coefficient", "absolute_percent_change"]), .48),
    ("delete-one mean and bias correction", (scalar("cluster_jackknife.mean_delete_one_coefficient") + scalar("cluster_jackknife.bias_corrected_coefficient")) / 2, .10),
    ("jackknife standard error", scalar("cluster_jackknife.jackknife_standard_error"), .08),
    ("jackknife t and p", (scalar("cluster_jackknife.jackknife_t_statistic") + scalar("cluster_jackknife.jackknife_t_p_value")) / 2, .12),
    ("maximum change and influential cluster", (scalar("cluster_jackknife.maximum_delete_one_absolute_percent_change") + scalar("cluster_jackknife.most_influential_division")) / 2, .14),
])
add_point(2, [
    ("penalty settings and feature count", (scalar("nested_elastic_net.alpha") + value_list("nested_elastic_net.lambda_grid") + scalar("nested_elastic_net.feature_count")) / 3, .08),
    ("outer folds, coordinate cycles, and inner grids", outer_fold_score(), .72),
    ("pooled OOF RMSE", scalar("nested_elastic_net.pooled_oof_rmse"), .07),
    ("pooled OOF MAE", scalar("nested_elastic_net.pooled_oof_mae"), .06),
    ("pooled OOF R squared", scalar("nested_elastic_net.pooled_oof_r_squared"), .07),
])
add_point(3, [
    ("cluster definition, seed, and draw count", (scalar("wild_cluster_bootstrap.cluster_definition") + scalar("wild_cluster_bootstrap.seed") + scalar("wild_cluster_bootstrap.bootstrap_count")) / 3, .08),
    ("observed absolute CR1 t", scalar("wild_cluster_bootstrap.observed_absolute_cr1_t"), .10),
    ("ordered generator checkpoints", object_list("wild_cluster_bootstrap.checkpoints", ["replicate", "prng_state", "absolute_cluster_t"]), .32),
    ("exceedance count and plus-one p", (scalar("wild_cluster_bootstrap.exceedance_count") + scalar("wild_cluster_bootstrap.plus_one_p_value")) / 2, .18),
    ("absolute-t quantiles", (scalar("wild_cluster_bootstrap.absolute_t_q90") + scalar("wild_cluster_bootstrap.absolute_t_q95") + scalar("wild_cluster_bootstrap.absolute_t_q99")) / 3, .20),
    ("terminal generator state", scalar("wild_cluster_bootstrap.final_prng_state"), .12),
])
add_point(4, [
    ("nominal coverage", scalar("grouped_conformal.nominal_coverage"), .04),
    ("ordered division calibration and interval diagnostics", object_list("grouped_conformal.division_results", ["held_out_division", "calibration_count", "finite_sample_rank", "interval_radius", "held_out_count", "covered_count", "coverage_fraction", "mean_interval_width", "maximum_excess"]), .74),
    ("pooled covered and state counts", (scalar("grouped_conformal.pooled_covered_count") + scalar("grouped_conformal.pooled_state_count")) / 2, .06),
    ("pooled coverage", scalar("grouped_conformal.pooled_coverage_fraction"), .06),
    ("held-out weighted interval width", scalar("grouped_conformal.held_out_weighted_mean_interval_width"), .05),
    ("worst-coverage division", scalar("grouped_conformal.worst_coverage_division"), .05),
])
add_point(5, [
    ("trajectory dimension and leading spectrum", (scalar("trajectory_pca_clustering.trajectory_feature_count") + value_list("trajectory_pca_clustering.first_three_explained_variance_ratios")) / 2, .10),
    ("deterministic initialization and Lloyd updates", (value_list("trajectory_pca_clustering.initial_centroid_state_codes") + scalar("trajectory_pca_clustering.lloyd_update_count")) / 2, .07),
    ("ordered cluster centroids", object_list("trajectory_pca_clustering.cluster_centroids_pc1_pc2_pc3", ["cluster_id", "pc1", "pc2", "pc3"]), .11),
    ("ordered state scores and assignments", object_list("trajectory_pca_clustering.state_assignments", ["state_code", "cluster_id", "pc1", "pc2", "pc3"]), .49),
    ("ordered leave-one-year stability", object_list("trajectory_pca_clustering.leave_one_year_out_stability", ["omitted_year", "adjusted_rand_index", "aligned_assignment_changes"]), .18),
    ("minimum adjusted Rand index", scalar("trajectory_pca_clustering.minimum_adjusted_rand_index"), .05),
])
add_point(6, [
    ("registered rollup ordering and scenario count", (value_list("exhaustive_source_perturbation.ordered_rollup_state_codes") + scalar("exhaustive_source_perturbation.scenario_count")) / 2, .08),
    ("ordered replacement-count strata", object_list("exhaustive_source_perturbation.by_replacement_count", ["replacement_count", "scenario_count", "minimum_coefficient", "maximum_coefficient", "minimum_hc3_p_value", "maximum_hc3_p_value", "mean_absolute_percent_shift"]), .42),
    ("stable scenario count", scalar("exhaustive_source_perturbation.stable_scenario_count"), .05),
    ("maximum-shift mask and ordered states", (scalar("exhaustive_source_perturbation.maximum_shift_bitmask") + value_list("exhaustive_source_perturbation.maximum_shift_replaced_state_codes")) / 2, .10),
    ("maximum-shift fit diagnostics", (scalar("exhaustive_source_perturbation.maximum_shift_coefficient") + scalar("exhaustive_source_perturbation.maximum_shift_hc3_p_value") + scalar("exhaustive_source_perturbation.maximum_absolute_percent_shift")) / 3, .10),
    ("ordered exact Shapley effects", object_list("exhaustive_source_perturbation.ordered_shapley_effects", ["state_code", "signed_shapley_coefficient_change"]), .17),
    ("Shapley efficiency identity", (scalar("exhaustive_source_perturbation.shapley_sum") + scalar("exhaustive_source_perturbation.all_rollup_minus_all_direct_coefficient")) / 2, .08),
])
flag_fields = ["cluster_jackknife_supported", "nested_prediction_stable", "wild_bootstrap_supported", "grouped_conformal_supported", "trajectory_stable", "source_exhaustive_stable"]
add_point(7, [
    ("six registered module flags", sum(scalar("decision_audit." + field) for field in flag_fields) / 6, .62),
    ("first failed module", scalar("decision_audit.first_failed_module"), .15),
    ("registered conclusion", scalar("decision_audit.conclusion"), .23),
])

for point in points:
    point_pass = all(item.get("passed") is True for item in point["subchecks"])
    point["diagnostic_fraction"] = point["earned_fraction"]
    point["point_pass"] = point_pass
    point["earned_fraction"] = 1.0 if point_pass else 0.0
    point["earned_normalized_score"] = point["normalized_maximum"] if point_pass else 0.0
score = sum(point["raw_weight"] * point["earned_fraction"] for point in points) / TOTAL
print(json.dumps({"score": round(max(0.0, min(1.0, score)), 10), "total_raw_weight": TOTAL, "points": points, "diagnostics": []}, indent=2))
