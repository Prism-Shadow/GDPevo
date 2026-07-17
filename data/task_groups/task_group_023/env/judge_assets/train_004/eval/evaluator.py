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
GOLD = json.loads('{"request_id":"OBS-STATE-WEIGHTED-ALGORITHMIC-AUDIT-2024-DIAB-R4","release_and_cohort":{"reference_year":2024,"jurisdiction_universe_count":51,"yearly_complete_case_counts":[{"year":2020,"count":42},{"year":2021,"count":43},{"year":2022,"count":43},{"year":2023,"count":41},{"year":2024,"count":41}],"primary_complete_case_count":41,"primary_excluded_state_codes":["AR","CO","GA","NE","NM","OK","RI","SC","SD","UT"],"balanced_state_count":20,"balanced_state_codes":["AK","AZ","CA","CT","IL","KS","KY","MA","ME","MI","MO","MT","NJ","NV","OR","PA","TX","VT","WA","WY"]},"cluster_jackknife":{"cluster_definition":"CENSUS_DIVISION","full_weighted_food_insecurity_coefficient":0.4559,"delete_one_cluster_results":[{"deleted_division":"New England","deleted_state_count":5,"coefficient":0.4769,"absolute_percent_change":4.5885},{"deleted_division":"Middle Atlantic","deleted_state_count":3,"coefficient":0.4438,"absolute_percent_change":2.6568},{"deleted_division":"East North Central","deleted_state_count":5,"coefficient":0.498,"absolute_percent_change":9.2341},{"deleted_division":"West North Central","deleted_state_count":5,"coefficient":0.4191,"absolute_percent_change":8.0903},{"deleted_division":"South Atlantic","deleted_state_count":7,"coefficient":0.3817,"absolute_percent_change":16.2797},{"deleted_division":"East South Central","deleted_state_count":4,"coefficient":0.4317,"absolute_percent_change":5.3192},{"deleted_division":"West South Central","deleted_state_count":2,"coefficient":0.4376,"absolute_percent_change":4.0325},{"deleted_division":"Mountain","deleted_state_count":5,"coefficient":0.5557,"absolute_percent_change":21.8809},{"deleted_division":"Pacific","deleted_state_count":5,"coefficient":0.4489,"absolute_percent_change":1.539}],"mean_delete_one_coefficient":0.4548,"bias_corrected_coefficient":0.4649,"jackknife_standard_error":0.1338,"jackknife_t_statistic":3.4744,"jackknife_t_p_value":0.0084,"maximum_delete_one_absolute_percent_change":21.8809,"most_influential_division":"Mountain"},"nested_elastic_net":{"alpha":0.6,"lambda_grid":[0.02,0.05,0.1,0.2,0.4,0.8],"feature_count":9,"outer_folds":[{"held_out_division":"New England","held_out_count":5,"chosen_lambda":0.05,"nonzero_feature_count":4,"coordinate_cycles":634,"outer_rmse":0.3463,"inner_grid":[{"lambda":0.02,"inner_grouped_rmse":0.7298},{"lambda":0.05,"inner_grouped_rmse":0.7171},{"lambda":0.1,"inner_grouped_rmse":0.7182},{"lambda":0.2,"inner_grouped_rmse":0.7339},{"lambda":0.4,"inner_grouped_rmse":0.7853},{"lambda":0.8,"inner_grouped_rmse":0.9414}]},{"held_out_division":"Middle Atlantic","held_out_count":3,"chosen_lambda":0.05,"nonzero_feature_count":5,"coordinate_cycles":1090,"outer_rmse":0.4967,"inner_grid":[{"lambda":0.02,"inner_grouped_rmse":0.7052},{"lambda":0.05,"inner_grouped_rmse":0.6962},{"lambda":0.1,"inner_grouped_rmse":0.6984},{"lambda":0.2,"inner_grouped_rmse":0.7137},{"lambda":0.4,"inner_grouped_rmse":0.7664},{"lambda":0.8,"inner_grouped_rmse":0.926}]},{"held_out_division":"East North Central","held_out_count":5,"chosen_lambda":0.05,"nonzero_feature_count":4,"coordinate_cycles":598,"outer_rmse":0.6917,"inner_grid":[{"lambda":0.02,"inner_grouped_rmse":0.6739},{"lambda":0.05,"inner_grouped_rmse":0.6645},{"lambda":0.1,"inner_grouped_rmse":0.6663},{"lambda":0.2,"inner_grouped_rmse":0.6852},{"lambda":0.4,"inner_grouped_rmse":0.745},{"lambda":0.8,"inner_grouped_rmse":0.9161}]},{"held_out_division":"West North Central","held_out_count":5,"chosen_lambda":0.05,"nonzero_feature_count":6,"coordinate_cycles":1086,"outer_rmse":0.8861,"inner_grid":[{"lambda":0.02,"inner_grouped_rmse":0.6545},{"lambda":0.05,"inner_grouped_rmse":0.6545},{"lambda":0.1,"inner_grouped_rmse":0.6579},{"lambda":0.2,"inner_grouped_rmse":0.6704},{"lambda":0.4,"inner_grouped_rmse":0.719},{"lambda":0.8,"inner_grouped_rmse":0.8769}]},{"held_out_division":"South Atlantic","held_out_count":7,"chosen_lambda":0.1,"nonzero_feature_count":7,"coordinate_cycles":1070,"outer_rmse":0.9669,"inner_grid":[{"lambda":0.02,"inner_grouped_rmse":0.657},{"lambda":0.05,"inner_grouped_rmse":0.6449},{"lambda":0.1,"inner_grouped_rmse":0.6423},{"lambda":0.2,"inner_grouped_rmse":0.6517},{"lambda":0.4,"inner_grouped_rmse":0.6936},{"lambda":0.8,"inner_grouped_rmse":0.836}]},{"held_out_division":"East South Central","held_out_count":4,"chosen_lambda":0.05,"nonzero_feature_count":6,"coordinate_cycles":921,"outer_rmse":0.715,"inner_grid":[{"lambda":0.02,"inner_grouped_rmse":0.7068},{"lambda":0.05,"inner_grouped_rmse":0.6988},{"lambda":0.1,"inner_grouped_rmse":0.6998},{"lambda":0.2,"inner_grouped_rmse":0.7167},{"lambda":0.4,"inner_grouped_rmse":0.7728},{"lambda":0.8,"inner_grouped_rmse":0.9406}]},{"held_out_division":"West South Central","held_out_count":2,"chosen_lambda":0.05,"nonzero_feature_count":5,"coordinate_cycles":1071,"outer_rmse":0.2349,"inner_grid":[{"lambda":0.02,"inner_grouped_rmse":0.7068},{"lambda":0.05,"inner_grouped_rmse":0.6973},{"lambda":0.1,"inner_grouped_rmse":0.699},{"lambda":0.2,"inner_grouped_rmse":0.7138},{"lambda":0.4,"inner_grouped_rmse":0.7655},{"lambda":0.8,"inner_grouped_rmse":0.9236}]},{"held_out_division":"Mountain","held_out_count":5,"chosen_lambda":0.05,"nonzero_feature_count":5,"coordinate_cycles":639,"outer_rmse":0.5014,"inner_grid":[{"lambda":0.02,"inner_grouped_rmse":0.7283},{"lambda":0.05,"inner_grouped_rmse":0.724},{"lambda":0.1,"inner_grouped_rmse":0.7249},{"lambda":0.2,"inner_grouped_rmse":0.7432},{"lambda":0.4,"inner_grouped_rmse":0.7989},{"lambda":0.8,"inner_grouped_rmse":0.9608}]},{"held_out_division":"Pacific","held_out_count":5,"chosen_lambda":0.05,"nonzero_feature_count":6,"coordinate_cycles":1266,"outer_rmse":0.5638,"inner_grid":[{"lambda":0.02,"inner_grouped_rmse":0.7059},{"lambda":0.05,"inner_grouped_rmse":0.6984},{"lambda":0.1,"inner_grouped_rmse":0.699},{"lambda":0.2,"inner_grouped_rmse":0.7139},{"lambda":0.4,"inner_grouped_rmse":0.7682},{"lambda":0.8,"inner_grouped_rmse":0.9362}]}],"pooled_oof_rmse":0.6844,"pooled_oof_mae":0.54,"pooled_oof_r_squared":0.7894},"wild_cluster_bootstrap":{"cluster_definition":"CENSUS_DIVISION","seed":24071544,"bootstrap_count":1999,"observed_absolute_cr1_t":3.768,"checkpoints":[{"replicate":1,"prng_state":548877146,"absolute_cluster_t":2.5058},{"replicate":10,"prng_state":2407537552,"absolute_cluster_t":0.5197},{"replicate":100,"prng_state":3899958010,"absolute_cluster_t":0.8137},{"replicate":500,"prng_state":3392555155,"absolute_cluster_t":3.6012},{"replicate":1000,"prng_state":683507284,"absolute_cluster_t":0.0397},{"replicate":1500,"prng_state":3906471010,"absolute_cluster_t":0.6222},{"replicate":1999,"prng_state":3944843368,"absolute_cluster_t":0.0261}],"exceedance_count":6,"plus_one_p_value":0.0035,"absolute_t_q90":2.0358,"absolute_t_q95":2.7998,"absolute_t_q99":3.6012,"final_prng_state":3944843368},"grouped_conformal":{"nominal_coverage":0.9,"division_results":[{"held_out_division":"New England","calibration_count":36,"finite_sample_rank":34,"interval_radius":1.4459,"held_out_count":5,"covered_count":5,"coverage_fraction":1.0,"mean_interval_width":2.8917,"maximum_excess":0},{"held_out_division":"Middle Atlantic","calibration_count":38,"finite_sample_rank":36,"interval_radius":1.4878,"held_out_count":3,"covered_count":3,"coverage_fraction":1.0,"mean_interval_width":2.9756,"maximum_excess":0},{"held_out_division":"East North Central","calibration_count":36,"finite_sample_rank":34,"interval_radius":1.3341,"held_out_count":5,"covered_count":5,"coverage_fraction":1.0,"mean_interval_width":2.6682,"maximum_excess":0},{"held_out_division":"West North Central","calibration_count":36,"finite_sample_rank":34,"interval_radius":1.253,"held_out_count":5,"covered_count":4,"coverage_fraction":0.8,"mean_interval_width":2.506,"maximum_excess":0.6171},{"held_out_division":"South Atlantic","calibration_count":34,"finite_sample_rank":32,"interval_radius":1.1686,"held_out_count":7,"covered_count":5,"coverage_fraction":0.7143,"mean_interval_width":2.3372,"maximum_excess":0.3423},{"held_out_division":"East South Central","calibration_count":37,"finite_sample_rank":35,"interval_radius":1.5217,"held_out_count":4,"covered_count":4,"coverage_fraction":1.0,"mean_interval_width":3.0434,"maximum_excess":0},{"held_out_division":"West South Central","calibration_count":39,"finite_sample_rank":36,"interval_radius":1.1259,"held_out_count":2,"covered_count":2,"coverage_fraction":1.0,"mean_interval_width":2.2517,"maximum_excess":0},{"held_out_division":"Mountain","calibration_count":36,"finite_sample_rank":34,"interval_radius":1.4695,"held_out_count":5,"covered_count":5,"coverage_fraction":1.0,"mean_interval_width":2.939,"maximum_excess":0},{"held_out_division":"Pacific","calibration_count":36,"finite_sample_rank":34,"interval_radius":1.361,"held_out_count":5,"covered_count":5,"coverage_fraction":1.0,"mean_interval_width":2.722,"maximum_excess":0}],"pooled_covered_count":38,"pooled_state_count":41,"pooled_coverage_fraction":0.9268,"held_out_weighted_mean_interval_width":2.6975,"worst_coverage_division":"South Atlantic"},"trajectory_pca_clustering":{"trajectory_feature_count":20,"first_three_explained_variance_ratios":[0.6996,0.0941,0.0616],"initial_centroid_state_codes":["AK","KS","WY"],"lloyd_update_count":3,"cluster_centroids_pc1_pc2_pc3":[{"cluster_id":1,"pc1":4.2312,"pc2":-0.1087,"pc3":0.0401},{"cluster_id":2,"pc1":-6.282,"pc2":0.0302,"pc3":0.4536},{"cluster_id":3,"pc1":-0.5947,"pc2":0.051,"pc3":-0.1456}],"state_assignments":[{"state_code":"AK","cluster_id":1,"pc1":5.705,"pc2":-1.9763,"pc3":0.0133},{"state_code":"AZ","cluster_id":2,"pc1":-6.5232,"pc2":1.3908,"pc3":-0.5039},{"state_code":"CA","cluster_id":3,"pc1":-0.5208,"pc2":-0.5226,"pc3":-0.3218},{"state_code":"CT","cluster_id":1,"pc1":4.349,"pc2":2.3398,"pc3":-1.651},{"state_code":"IL","cluster_id":3,"pc1":0.9315,"pc2":1.687,"pc3":-0.3621},{"state_code":"KS","cluster_id":2,"pc1":-7.4741,"pc2":-0.0753,"pc3":0.1661},{"state_code":"KY","cluster_id":1,"pc1":5.5538,"pc2":0.9398,"pc3":2.0979},{"state_code":"MA","cluster_id":3,"pc1":0.6462,"pc2":-1.5117,"pc3":0.1845},{"state_code":"ME","cluster_id":3,"pc1":-2.2529,"pc2":-0.5636,"pc3":-0.78},{"state_code":"MI","cluster_id":3,"pc1":-2.3883,"pc2":0.3659,"pc3":0.5905},{"state_code":"MO","cluster_id":1,"pc1":4.422,"pc2":-2.2569,"pc3":-0.8891},{"state_code":"MT","cluster_id":1,"pc1":3.1944,"pc2":-0.033,"pc3":0.1054},{"state_code":"NJ","cluster_id":3,"pc1":1.0732,"pc2":-0.3685,"pc3":1.7091},{"state_code":"NV","cluster_id":2,"pc1":-4.8485,"pc2":-1.2248,"pc3":1.6986},{"state_code":"OR","cluster_id":3,"pc1":1.5609,"pc2":1.9528,"pc3":-0.6477},{"state_code":"PA","cluster_id":3,"pc1":-1.9432,"pc2":-2.234,"pc3":-2.3612},{"state_code":"TX","cluster_id":1,"pc1":2.163,"pc2":0.3345,"pc3":0.5643},{"state_code":"VT","cluster_id":3,"pc1":-2.3205,"pc2":0.1243,"pc3":-0.0135},{"state_code":"WA","cluster_id":3,"pc1":-1.4406,"pc2":0.2182,"pc3":1.1371},{"state_code":"WY","cluster_id":3,"pc1":0.1131,"pc2":1.4137,"pc3":-0.7364}],"leave_one_year_out_stability":[{"omitted_year":2020,"adjusted_rand_index":0.8247,"aligned_assignment_changes":1},{"omitted_year":2021,"adjusted_rand_index":0.6611,"aligned_assignment_changes":2},{"omitted_year":2022,"adjusted_rand_index":0.8247,"aligned_assignment_changes":1},{"omitted_year":2023,"adjusted_rand_index":1.0,"aligned_assignment_changes":0},{"omitted_year":2024,"adjusted_rand_index":0.8202,"aligned_assignment_changes":1}],"minimum_adjusted_rand_index":0.6611},"exhaustive_source_perturbation":{"ordered_rollup_state_codes":["WI","MA","MI","MT","DC","CT","NV","LA","OH","KY","IL","NJ"],"scenario_count":4096,"by_replacement_count":[{"replacement_count":0,"scenario_count":1,"minimum_coefficient":0.4559,"maximum_coefficient":0.4559,"minimum_hc3_p_value":0.0026,"maximum_hc3_p_value":0.0026,"mean_absolute_percent_shift":0.0},{"replacement_count":1,"scenario_count":12,"minimum_coefficient":0.4152,"maximum_coefficient":0.5068,"minimum_hc3_p_value":0.0006,"maximum_hc3_p_value":0.0179,"mean_absolute_percent_shift":3.8854},{"replacement_count":2,"scenario_count":66,"minimum_coefficient":0.3964,"maximum_coefficient":0.5444,"minimum_hc3_p_value":0.0004,"maximum_hc3_p_value":0.0258,"mean_absolute_percent_shift":5.9233},{"replacement_count":3,"scenario_count":220,"minimum_coefficient":0.3874,"maximum_coefficient":0.562,"minimum_hc3_p_value":0.0003,"maximum_hc3_p_value":0.0284,"mean_absolute_percent_shift":7.2849},{"replacement_count":4,"scenario_count":495,"minimum_coefficient":0.3873,"maximum_coefficient":0.579,"minimum_hc3_p_value":0.0003,"maximum_hc3_p_value":0.0287,"mean_absolute_percent_shift":8.3766},{"replacement_count":5,"scenario_count":792,"minimum_coefficient":0.3884,"maximum_coefficient":0.5945,"minimum_hc3_p_value":0.0002,"maximum_hc3_p_value":0.0286,"mean_absolute_percent_shift":9.3122},{"replacement_count":6,"scenario_count":924,"minimum_coefficient":0.39,"maximum_coefficient":0.5973,"minimum_hc3_p_value":0.0002,"maximum_hc3_p_value":0.028,"mean_absolute_percent_shift":10.1507},{"replacement_count":7,"scenario_count":792,"minimum_coefficient":0.3927,"maximum_coefficient":0.5988,"minimum_hc3_p_value":0.0002,"maximum_hc3_p_value":0.0274,"mean_absolute_percent_shift":10.9593},{"replacement_count":8,"scenario_count":495,"minimum_coefficient":0.4082,"maximum_coefficient":0.5999,"minimum_hc3_p_value":0.0002,"maximum_hc3_p_value":0.023,"mean_absolute_percent_shift":11.8054},{"replacement_count":9,"scenario_count":220,"minimum_coefficient":0.4252,"maximum_coefficient":0.5999,"minimum_hc3_p_value":0.0002,"maximum_hc3_p_value":0.0194,"mean_absolute_percent_shift":12.752},{"replacement_count":10,"scenario_count":66,"minimum_coefficient":0.4428,"maximum_coefficient":0.5908,"minimum_hc3_p_value":0.0003,"maximum_hc3_p_value":0.0164,"mean_absolute_percent_shift":13.8619},{"replacement_count":11,"scenario_count":12,"minimum_coefficient":0.4804,"maximum_coefficient":0.5721,"minimum_hc3_p_value":0.0005,"maximum_hc3_p_value":0.0132,"mean_absolute_percent_shift":15.1524},{"replacement_count":12,"scenario_count":1,"minimum_coefficient":0.5313,"maximum_coefficient":0.5313,"minimum_hc3_p_value":0.005,"maximum_hc3_p_value":0.005,"mean_absolute_percent_shift":16.5299}],"stable_scenario_count":4096,"maximum_shift_bitmask":1839,"maximum_shift_replaced_state_codes":["WI","MA","MI","MT","CT","OH","KY","IL"],"maximum_shift_coefficient":0.5999,"maximum_shift_hc3_p_value":0.0002,"maximum_absolute_percent_shift":31.5776,"ordered_shapley_effects":[{"state_code":"WI","signed_shapley_coefficient_change":0.017},{"state_code":"MA","signed_shapley_coefficient_change":0.0509},{"state_code":"MI","signed_shapley_coefficient_change":0.0176},{"state_code":"MT","signed_shapley_coefficient_change":0.0376},{"state_code":"DC","signed_shapley_coefficient_change":-0.0187},{"state_code":"CT","signed_shapley_coefficient_change":0.0011},{"state_code":"NV","signed_shapley_coefficient_change":-0.0408},{"state_code":"LA","signed_shapley_coefficient_change":-0.0091},{"state_code":"OH","signed_shapley_coefficient_change":0.0155},{"state_code":"KY","signed_shapley_coefficient_change":0.0028},{"state_code":"IL","signed_shapley_coefficient_change":0.0015},{"state_code":"NJ","signed_shapley_coefficient_change":-0.0}],"shapley_sum":0.0754,"all_rollup_minus_all_direct_coefficient":0.0754},"decision_audit":{"cluster_jackknife_supported":true,"nested_prediction_stable":true,"wild_bootstrap_supported":true,"grouped_conformal_supported":true,"trajectory_stable":true,"source_exhaustive_stable":false,"first_failed_module":"SOURCE_EXHAUSTIVE","conclusion":"NOT_ROBUST_AT_SOURCE_EXHAUSTIVE"}}')
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
