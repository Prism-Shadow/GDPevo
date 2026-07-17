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
GOLD = json.loads('{"publication_cohort":{"target_jurisdictions":51,"analysis_years":[2020,2021,2022,2023,2024],"resolved_health_observations":2040,"resolved_socioeconomic_records":255,"yearly_core_complete_n":[44,45,47,46,47],"core_balanced_state_n":27,"core_balanced_observation_n":135,"core_balanced_excluded_state_codes":["AL","AR","DE","GA","HI","IL","IN","KS","KY","LA","MA","MI","MO","MS","NH","NM","NY","OH","SC","SD","TN","TX","WI","WV"],"broad_2023_complete_state_n":34},"delete_cluster_fixed_effects":{"state_order":["AK","AZ","CA","CO","CT","DC","FL","IA","ID","MD","ME","MN","MT","NC","ND","NE","NJ","NV","OK","OR","PA","RI","UT","VA","VT","WA","WY"],"state_n":27,"observation_n":135,"full_obesity_coefficient":-0.1062,"delete_obesity_coefficients":[-0.1147,-0.1173,-0.1108,-0.1191,-0.1039,-0.1108,-0.0929,-0.0908,-0.1095,-0.1038,-0.1168,-0.1084,-0.1197,-0.092,-0.1082,-0.1063,-0.1074,-0.0949,-0.0864,-0.1105,-0.1334,-0.1046,-0.1043,-0.1173,-0.0899,-0.0999,-0.0948],"delete_mean_coefficient":-0.1062,"jackknife_standard_error":0.0555,"jackknife_t_statistic":-1.9157,"jackknife_p_value":0.0665,"bias_corrected_obesity_coefficient":-0.1063,"minimum_delete_state":"PA","minimum_delete_coefficient":-0.1334,"maximum_delete_state":"OK","maximum_delete_coefficient":-0.0864},"nested_ridge_division_cv":{"broad_state_n":34,"broad_state_order":["AK","AZ","CA","CO","CT","DE","FL","IA","ID","IL","IN","LA","MA","MD","MN","MO","MS","MT","NH","NJ","NM","NV","NY","OK","OR","RI","SC","TN","TX","UT","VT","WA","WV","WY"],"feature_order":["adult_obesity","adult_smoking","diagnosed_diabetes","physical_inactivity","frequent_mental_distress","food_insecurity","premature_mortality_rate","poverty","bachelors","median_income","unemployment","uninsured","socio_food_insecurity"],"division_order":["East North Central","East South Central","Middle Atlantic","Mountain","New England","Pacific","South Atlantic","West North Central","West South Central"],"lambda_grid":[0.01,0.1,1.0,10.0,100.0],"outer_train_n":[32,32,32,26,29,30,29,31,31],"outer_test_n":[2,2,2,8,5,4,5,3,3],"selected_lambda":[0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,1.0],"inner_rmse_grid":[[0.6879,0.6036,0.6206,1.2441,2.0713],[0.6522,0.5888,0.6106,1.2638,2.1426],[0.6941,0.5988,0.6193,1.2652,2.1401],[0.7391,0.5809,0.6018,1.1945,1.9866],[0.5853,0.5639,0.6084,1.2012,1.9831],[0.6944,0.6016,0.617,1.2763,2.1635],[0.6286,0.6043,0.6344,1.241,2.0678],[0.7051,0.5921,0.6159,1.2631,2.1259],[0.7663,0.5961,0.567,1.2351,2.0773]],"outer_rmse":[0.3261,0.589,0.4145,0.6324,0.6949,0.4727,0.5259,0.6075,0.7371],"pooled_rmse":0.5911,"pooled_mae":0.5013,"pooled_q_squared":0.929,"worst_outer_division":"West South Central"},"wild_cluster_bootstrap":{"seed":14022023,"stream":17,"replicate_n":1999,"state_order":["AK","AZ","CA","CO","CT","DC","FL","IA","ID","MD","ME","MN","MT","NC","ND","NE","NJ","NV","OK","OR","PA","RI","UT","VA","VT","WA","WY"],"observed_obesity_coefficient":-0.1062,"observed_cr1_standard_error":0.0516,"observed_t_statistic":-2.0601,"first_three_weight_index_rows":[[2,0,5,2,2,4,2,0,0,2,0,1,1,3,0,0,4,4,5,1,2,3,0,4,2,3,0],[5,4,1,1,1,2,4,3,5,5,0,2,0,2,3,2,3,0,1,2,3,0,5,4,2,4,0],[3,0,0,2,4,3,2,2,2,5,4,1,0,5,4,4,0,0,1,1,2,0,0,2,4,1,4]],"batch_exceedance_counts":[6,5,6,8,4,7,7,9,4,4,6,1,8,8,5,7,3,8,2,6],"exceedance_n":114,"bootstrap_p_value":0.0575,"bootstrap_coefficient_mean":-0.0004,"bootstrap_coefficient_sample_sd":0.0567,"t_quantile_probabilities":[0.025,0.1,0.5,0.9,0.975],"bootstrap_t_quantiles":[-2.1038,-1.3491,-0.0328,1.4033,2.0836]},"grouped_split_conformal":{"alpha":0.2,"fixed_lambda":1.0,"division_order":["East North Central","East South Central","Middle Atlantic","Mountain","New England","Pacific","South Atlantic","West North Central","West South Central"],"calibration_division":["Mountain","Mountain","Mountain","New England","Mountain","Mountain","Mountain","Mountain","Mountain"],"proper_train_n":[24,24,24,21,21,22,21,23,23],"calibration_n":[8,8,8,5,8,8,8,8,8],"test_n":[2,2,2,8,5,4,5,3,3],"threshold":[1.2988,1.2719,1.3138,1.3959,1.5025,1.3413,1.2356,1.3572,1.23],"fold_coverage":[1.0,1.0,1.0,0.875,1.0,1.0,1.0,1.0,1.0],"fold_mean_width":[2.5975,2.5438,2.6277,2.7918,3.0051,2.6826,2.4712,2.7143,2.4599],"fold_test_mae":[0.4541,0.4151,0.4332,0.6379,0.7653,0.3133,0.4207,0.3341,0.5656],"aggregate_coverage":0.9706,"aggregate_mean_width":2.6914},"trajectory_pca_clustering":{"state_order":["AK","AZ","CA","CO","CT","DC","FL","IA","ID","MD","ME","MN","MT","NC","ND","NE","NJ","NV","OK","OR","PA","RI","UT","VA","VT","WA","WY"],"feature_order":["life_expectancy_2020","life_expectancy_2021","life_expectancy_2022","life_expectancy_2023","life_expectancy_2024","adult_obesity_2020","adult_obesity_2021","adult_obesity_2022","adult_obesity_2023","adult_obesity_2024"],"first_two_eigenvalues":[9.1947,0.3173],"first_two_explained_ratios":[0.9195,0.0317],"first_two_cumulative_explained_ratio":0.9512,"pc1_loadings":[0.3167,0.312,0.3194,0.3223,0.323,-0.3163,-0.3147,-0.3095,-0.3201,-0.3079],"pc2_loadings":[0.3778,0.4526,0.1954,0.1698,0.1856,0.2791,-0.0271,0.4979,0.251,0.4017],"pc1_scores":[-4.2805,4.8792,0.9408,3.0923,-3.0181,-6.29,-2.2771,1.654,-4.954,-2.9188,2.9709,0.1196,-2.0896,-1.9444,-1.2561,2.1883,-0.3062,2.7065,5.5471,-0.9349,1.906,4.8867,-1.5289,-1.5188,1.2415,0.6699,0.5149],"pc2_scores":[-0.0684,-0.8019,-0.536,0.2974,-0.3769,-0.1928,1.2351,0.226,0.3801,-0.827,0.0158,-1.0392,-0.7923,-0.591,-0.3074,0.1788,0.0233,-0.4567,0.1044,0.7247,0.298,0.3271,0.4831,1.0034,0.4687,-0.0136,0.237],"initial_centroid_states":["AK","OK","WA"],"cluster_centroids":[[-2.916,-0.0049],[0.7994,0.0568],[4.0138,-0.0856]],"cluster_sizes":[11,10,6],"cluster_labels":[1,3,2,3,1,1,1,2,1,1,3,2,1,1,1,2,2,3,3,2,2,3,1,1,2,2,2],"leave_year_out_order":[2020,2021,2022,2023,2024],"leave_year_out_adjusted_rand_index":[1.0,0.3747,0.7703,0.9041,0.8707],"leave_year_out_aligned_agreement":[1.0,0.7407,0.9259,0.963,0.963]},"source_year_perturbation":{"strict_state_n":24,"strict_observation_n":120,"strict_excluded_state_codes":["AL","AR","CO","DC","DE","GA","HI","IA","IL","IN","KS","KY","LA","MA","MI","MO","MS","NH","NM","NY","OH","SC","SD","TN","TX","WI","WV"],"subset_order":["2020-2021-2022","2020-2021-2023","2020-2021-2024","2020-2022-2023","2020-2022-2024","2020-2023-2024","2021-2022-2023","2021-2022-2024","2021-2023-2024","2022-2023-2024","2020-2021-2022-2023","2020-2021-2022-2024","2020-2021-2023-2024","2020-2022-2023-2024","2021-2022-2023-2024","2020-2021-2022-2023-2024"],"primary_obesity_coefficients":[-0.1581,-0.0703,-0.0073,-0.1357,-0.1416,-0.0651,-0.2196,-0.1232,-0.0308,-0.139,-0.1536,-0.1054,-0.039,-0.1269,-0.1232,-0.1089],"parallel_obesity_coefficients":[-0.0049,0.0002,0.0629,-0.0253,0.0587,0.0397,-0.0958,-0.053,-0.0628,-0.0466,-0.0382,0.0132,0.0056,-0.0014,-0.0668,-0.0195],"primary_cr1_p_values":[0.0904,0.4344,0.9213,0.1872,0.0964,0.4473,0.0029,0.0586,0.6472,0.0602,0.049,0.1332,0.5444,0.0935,0.0337,0.0824],"parallel_cr1_p_values":[0.9502,0.9983,0.4308,0.7246,0.5034,0.5844,0.2627,0.5034,0.4927,0.4765,0.5638,0.8434,0.9387,0.9807,0.3328,0.7463],"absolute_percent_shifts":[96.881,100.2476,962.0522,81.3304,141.4386,161.0407,56.3966,56.9777,103.6065,66.4853,75.1298,112.4958,114.3537,98.8926,45.7842,82.1412],"same_sign_subset_n":10,"same_sign_subset_fraction":0.625,"median_absolute_percent_shift":97.8868,"maximum_absolute_percent_shift":962.0522,"worst_shift_subset":"2020-2021-2024"},"robustness_decision":{"delete_cluster_fe":"FAIL","nested_ridge":"PASS","wild_cluster_bootstrap":"FAIL","grouped_split_conformal":"PASS","trajectory_stability":"FAIL","source_year_stability":"FAIL","passed_gate_count":2,"classification":"NO_TRANSPORTABLE_LONGEVITY_SIGNAL"}}')


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
