#!/usr/bin/env python3
"""Granular deterministic evaluator for train_002."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

POINTS = [
    ("SP001", "Four-year publication reconciliation and three linked cohorts", 1),
    ("SP002", "Cluster-robust multi-period difference-GMM mediation with ordered state deletions", 3),
    ("SP003", "Nested state-blocked ridge grids and outer-fold predictive diagnostics", 3),
    ("SP004", "Restricted-null paired-state wild-cluster bootstrap-t with PRNG checkpoints", 3),
    ("SP005", "State-grouped split-conformal calibration cycles and state coverage", 3),
    ("SP006", "Partial-R2 causal-mediation sensitivity surface and tipping boundary", 3),
    ("SP007", "Four-year trajectory PCA, deterministic clustering, and stability audit", 3),
    ("SP008", "Controlled six-module obesity-mediation decision", 2),
]
TOTAL = sum(x[2] for x in POINTS)
MISSING = object()


def at(obj: Any, path: str) -> Any:
    cur = obj
    for key in path.split(".") if path else []:
        if not isinstance(cur, dict) or key not in cur:
            return MISSING
        cur = cur[key]
    return cur


def number(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    x = float(v)
    return x if math.isfinite(x) else None


def numeq(a: Any, b: Any) -> float:
    x, y = number(a), number(b)
    return float(x is not None and y is not None and abs(x-y) <= 0.00005 + 1e-12)


def inteq(a: Any, b: Any) -> float:
    x, y = number(a), number(b)
    return float(x is not None and y is not None and x == int(x) and y == int(y) and int(x) == int(y))


def texteq(a: Any, b: Any) -> float:
    return float(isinstance(a, str) and isinstance(b, str) and a.strip().upper() == b.strip().upper())


def booleq(a: Any, b: Any) -> float:
    return float(isinstance(a, bool) and isinstance(b, bool) and a is b)


CHECKERS: dict[str, Callable[[Any, Any], float]] = {"n": numeq, "i": inteq, "t": texteq, "b": booleq}


def paths_fraction(pred: dict, gold: dict, specs: list[tuple[str, str]]) -> float:
    if not specs:
        return 0.0
    return sum(CHECKERS[k](at(pred, p), at(gold, p)) for p, k in specs) / len(specs)


def ordered_rows_fraction(pv: Any, gv: Any, specs: list[tuple[str, str]]) -> float:
    if not isinstance(gv, list) or not isinstance(pv, list):
        return 0.0
    denom = 1 + len(gv) * len(specs)
    earned = float(len(pv) == len(gv))
    for i, grow in enumerate(gv):
        prow = pv[i] if i < len(pv) and isinstance(pv[i], dict) else {}
        if not isinstance(grow, dict):
            continue
        for field, kind in specs:
            earned += CHECKERS[kind](at(prow, field), at(grow, field))
    return earned / denom


def num_list_fraction(pv: Any, gv: Any) -> float:
    if not isinstance(pv, list) or not isinstance(gv, list):
        return 0.0
    return (float(len(pv) == len(gv)) + sum(numeq(pv[i], v) for i, v in enumerate(gv) if i < len(pv))) / (1 + len(gv))


def weighted(items: list[tuple[str, float, float]]) -> tuple[float, list[dict[str, Any]]]:
    if not math.isclose(sum(x[1] for x in items), 1.0, abs_tol=1e-12):
        raise ValueError("subcheck shares must sum to one")
    earned = 0.0
    details = []
    for name, share, fraction in items:
        f = max(0.0, min(1.0, float(fraction)))
        earned += share * f
        details.append({"name": name, "share_within_point": share, "earned_fraction": round(f, 12), "passed": math.isclose(f, 1.0, abs_tol=1e-12)})
    return earned, details


def score_points(p: dict, g: dict) -> list[tuple[float, list[dict[str, Any]]]]:
    cohort_lists = [
        ordered_rows_fraction(at(p, f"cohort_audit.{key}"), at(g, f"cohort_audit.{key}"), [("year", "i"), ("count", "i")])
        for key in ["selected_health_rows_by_year", "selected_socioeconomic_rows_by_year", "complete_count_by_year"]
    ]
    sp1 = weighted([
        ("county universe and cohort totals", .45, paths_fraction(p, g, [(f"cohort_audit.{x}", "i") for x in ["requested_county_count", "primary_2023_count", "balanced_four_year_count", "machine_learning_complete_count", "state_count"]])),
        ("ordered selected health publications", .20, cohort_lists[0]),
        ("ordered selected socioeconomic publications", .15, cohort_lists[1]),
        ("ordered annual completeness audit", .20, cohort_lists[2]),
    ])

    eqspec = [("coefficient", "n"), ("cluster_se", "n"), ("t_statistic", "n"), ("confidence_interval_95.lower", "n"), ("confidence_interval_95.upper", "n")]
    eqscores = [
        paths_fraction(at(p, f"difference_gmm_mediation.{x}") if isinstance(at(p, f"difference_gmm_mediation.{x}"), dict) else {}, at(g, f"difference_gmm_mediation.{x}"), eqspec)
        for x in ["total_poverty", "path_a_poverty", "path_b_inactivity", "direct_poverty"]
    ]
    loso = ordered_rows_fraction(at(p, "difference_gmm_mediation.leave_one_state_out"), at(g, "difference_gmm_mediation.leave_one_state_out"), [("omitted_state", "t"), ("n", "i"), ("indirect_effect", "n"), ("direct_poverty", "n")])
    sp2 = weighted([
        ("GMM panel dimensions", .06, paths_fraction(p, g, [(f"difference_gmm_mediation.{x}", "i") for x in ["observation_count", "county_count", "state_count"]])),
        ("total-equation clustered inference", .10, eqscores[0]),
        ("path-a clustered inference", .10, eqscores[1]),
        ("path-b clustered inference", .10, eqscores[2]),
        ("direct-poverty clustered inference", .10, eqscores[3]),
        ("two endogenous first-stage partial F statistics", .08, paths_fraction(p, g, [("difference_gmm_mediation.first_stage_partial_f.delta_poverty", "n"), ("difference_gmm_mediation.first_stage_partial_f.delta_inactivity", "n")])),
        ("stacked cross-equation indirect delta", .18, paths_fraction(p, g, [(f"difference_gmm_mediation.stacked_indirect.{x}", "n") for x in ["cross_equation_correction", "a_b_covariance", "estimate", "cluster_se", "confidence_interval_95.lower", "confidence_interval_95.upper"]])),
        ("ascending leave-one-state-out diagnostics", .28, loso),
    ])

    pf, gf = at(p, "nested_state_ridge.outer_folds"), at(g, "nested_state_ridge.outer_folds")
    foldmeta = ordered_rows_fraction(pf, gf, [("state", "t"), ("n", "i"), ("base_lambda", "n"), ("augmented_lambda", "n")])
    outermetrics = ordered_rows_fraction(pf, gf, [("state", "t"), ("base_outer_rmse", "n"), ("augmented_outer_rmse", "n")])

    def grids(which: str) -> float:
        if not isinstance(pf, list) or not isinstance(gf, list):
            return 0.0
        vals = []
        for i, gr in enumerate(gf):
            pr = pf[i] if i < len(pf) and isinstance(pf[i], dict) else {}
            vals.append(num_list_fraction(pr.get(which), gr.get(which)))
        return sum(vals) / len(vals) if vals else 0.0

    sp3 = weighted([
        ("ridge cohort, folds, and lambda grid", .08, (paths_fraction(p, g, [("nested_state_ridge.n", "i"), ("nested_state_ridge.fold_count", "i")]) + num_list_fraction(at(p, "nested_state_ridge.lambda_grid"), at(g, "nested_state_ridge.lambda_grid"))) / 2),
        ("pooled outer errors and state win count", .12, paths_fraction(p, g, [("nested_state_ridge.pooled_base_rmse", "n"), ("nested_state_ridge.pooled_augmented_rmse", "n"), ("nested_state_ridge.augmented_better_state_count", "i")])),
        ("ascending fold sizes and selected hyperparameters", .15, foldmeta),
        ("all base inner-grid RMSE diagnostics", .25, grids("base_inner_rmse")),
        ("all augmented inner-grid RMSE diagnostics", .25, grids("augmented_inner_rmse")),
        ("all held-out-state RMSE pairs", .15, outermetrics),
    ])

    beq = ordered_rows_fraction(at(p, "wild_cluster_bootstrap_t.equations"), at(g, "wild_cluster_bootstrap_t.equations"), [("equation", "t"), ("observed_coefficient", "n"), ("observed_cr1_se", "n"), ("observed_t", "n"), ("bootstrap_p_value", "n"), ("bootstrap_t_q025", "n"), ("bootstrap_t_q975", "n"), ("confidence_interval_95.lower", "n"), ("confidence_interval_95.upper", "n")])
    bcp = ordered_rows_fraction(at(p, "wild_cluster_bootstrap_t.checkpoints"), at(g, "wild_cluster_bootstrap_t.checkpoints"), [("replicate", "i"), ("prng_state", "i"), ("total_poverty_t", "n"), ("path_a_poverty_t", "n"), ("path_b_inactivity_t", "n")])
    sp4 = weighted([
        ("bootstrap method, seed, replicate count, and terminal state", .10, paths_fraction(p, g, [("wild_cluster_bootstrap_t.method", "t"), ("wild_cluster_bootstrap_t.seed", "i"), ("wild_cluster_bootstrap_t.replicate_count", "i"), ("wild_cluster_bootstrap_t.final_prng_state", "i")])),
        ("three ordered restricted-null bootstrap-t distributions", .55, beq),
        ("ordered PRNG and equation-t checkpoints", .35, bcp),
    ])

    cyc = ordered_rows_fraction(at(p, "state_grouped_conformal.cycles"), at(g, "state_grouped_conformal.cycles"), [("test_fold", "i"), ("calibration_fold", "i"), ("training_state_count", "i"), ("calibration_state_count", "i"), ("test_state_count", "i"), ("calibration_count", "i"), ("test_count", "i"), ("qhat_state_max", "n"), ("test_coverage", "n"), ("mean_interval_width", "n"), ("worst_test_state", "t")])
    scov = ordered_rows_fraction(at(p, "state_grouped_conformal.state_coverage"), at(g, "state_grouped_conformal.state_coverage"), [("state", "t"), ("n", "i"), ("coverage", "n"), ("mean_width", "n")])
    sp5 = weighted([
        ("conformal nominal level and fixed learner", .05, paths_fraction(p, g, [("state_grouped_conformal.nominal_coverage", "n"), ("state_grouped_conformal.fixed_lambda", "n")])),
        ("pooled calibration performance", .15, paths_fraction(p, g, [("state_grouped_conformal.overall_coverage", "n"), ("state_grouped_conformal.mean_interval_width", "n"), ("state_grouped_conformal.state_count_at_or_above_80pct", "i")])),
        ("five ordered train-calibration-test cycles", .38, cyc),
        ("ascending per-state coverage and width", .42, scov),
    ])

    surfvals = ordered_rows_fraction(at(p, "mediation_sensitivity_surface.surface"), at(g, "mediation_sensitivity_surface.surface"), [("adjusted_path_b", "n"), ("adjusted_indirect", "n"), ("adjusted_direct", "n"), ("proportion", "n")])
    coords = ordered_rows_fraction(at(p, "mediation_sensitivity_surface.surface"), at(g, "mediation_sensitivity_surface.surface"), [("r2_mediator", "n"), ("r2_outcome", "n"), ("direction", "t")])
    sp6 = weighted([
        ("baseline mediation and residual degrees of freedom", .15, paths_fraction(p, g, [("mediation_sensitivity_surface.baseline_path_a", "n"), ("mediation_sensitivity_surface.baseline_path_b", "n"), ("mediation_sensitivity_surface.baseline_path_b_se", "n"), ("mediation_sensitivity_surface.residual_degrees_of_freedom", "i")])),
        ("equal-strength tipping boundary", .08, paths_fraction(p, g, [("mediation_sensitivity_surface.equal_strength_tipping_r2", "n")])),
        ("ordered two-dimensional R2 grid coordinates", .17, coords),
        ("all adjusted path and mediation surface values", .60, surfvals),
    ])

    loads = ordered_rows_fraction(at(p, "trajectory_pca_clustering.loadings"), at(g, "trajectory_pca_clustering.loadings"), [("feature", "t"), ("pc1", "n"), ("pc2", "n")])
    sts = ordered_rows_fraction(at(p, "trajectory_pca_clustering.states"), at(g, "trajectory_pca_clustering.states"), [("state", "t"), ("balanced_county_count", "i"), ("pc1_score", "n"), ("pc2_score", "n"), ("cluster", "i")])
    stab = ordered_rows_fraction(at(p, "trajectory_pca_clustering.leave_one_year_out_stability"), at(g, "trajectory_pca_clustering.leave_one_year_out_stability"), [("omitted_year", "i"), ("adjusted_rand_index", "n")])
    sp7 = weighted([
        ("trajectory dimensions and deterministic k-means iterations", .08, paths_fraction(p, g, [("trajectory_pca_clustering.state_count", "i"), ("trajectory_pca_clustering.feature_count", "i"), ("trajectory_pca_clustering.kmeans_iterations", "i")])),
        ("leading PCA spectrum", .14, (num_list_fraction(at(p, "trajectory_pca_clustering.eigenvalues"), at(g, "trajectory_pca_clustering.eigenvalues")) + num_list_fraction(at(p, "trajectory_pca_clustering.explained_variance_ratio"), at(g, "trajectory_pca_clustering.explained_variance_ratio"))) / 2),
        ("ordered signed PC1 and PC2 loadings", .24, loads),
        ("ascending state scores and cluster assignments", .40, sts),
        ("leave-year-out ARI sequence and stability summaries", .14, (stab + paths_fraction(p, g, [("trajectory_pca_clustering.mean_stability_ari", "n"), ("trajectory_pca_clustering.minimum_stability_ari", "n")])) / 2),
    ])

    sp8 = weighted([
        ("six controlled evidence flags", .75, paths_fraction(p, g, [(f"controlled_conclusion.{x}", "b") for x in ["difference_gmm_supported", "nested_ridge_supported", "bootstrap_supported", "grouped_conformal_calibrated", "sensitivity_robust", "trajectory_stable"]])),
        ("supported-module count and ordered classification", .25, paths_fraction(p, g, [("controlled_conclusion.supported_module_count", "i"), ("controlled_conclusion.classification", "t")])),
    ])
    return [sp1, sp2, sp3, sp4, sp5, sp6, sp7, sp8]


def evaluate(prediction: Any, gold: dict) -> dict[str, Any]:
    valid = isinstance(prediction, dict) and bool(prediction)
    results = score_points(prediction, gold) if valid else [(0.0, []) for _ in POINTS]
    rubric = []
    score = 0.0
    for (pid, goal, weight), (fraction, subs) in zip(POINTS, results):
        point_pass = valid and bool(subs) and all(item.get("passed") is True for item in subs)
        earned = weight / TOTAL if point_pass else 0.0
        score += earned
        rubric.append({"id": pid, "goal": goal, "raw_weight": weight, "normalized_max": round(weight / TOTAL, 12), "point_pass": point_pass, "diagnostic_fraction": round(fraction, 12), "earned_fraction": 1.0 if point_pass else 0.0, "earned_normalized_score": round(earned, 12), "subchecks": subs})
    return {"score": round(score, 12), "max_score": 1.0, "total_raw_weight": TOTAL, "rubric": rubric}


def main() -> None:
    gold = json.loads('{"cohort_audit":{"requested_county_count":696,"selected_health_rows_by_year":[{"year":2021,"count":1325},{"year":2022,"count":1324},{"year":2023,"count":1338},{"year":2024,"count":1323}],"selected_socioeconomic_rows_by_year":[{"year":2021,"count":696},{"year":2022,"count":696},{"year":2023,"count":696},{"year":2024,"count":696}],"complete_count_by_year":[{"year":2021,"count":573},{"year":2022,"count":564},{"year":2023,"count":571},{"year":2024,"count":580}],"primary_2023_count":571,"balanced_four_year_count":315,"machine_learning_complete_count":553,"state_count":29},"difference_gmm_mediation":{"observation_count":630,"county_count":315,"state_count":29,"total_poverty":{"coefficient":-1.5009,"cluster_se":0.8709,"t_statistic":-1.7234,"confidence_interval_95":{"lower":-3.2849,"upper":0.283}},"path_a_poverty":{"coefficient":0.5503,"cluster_se":0.8569,"t_statistic":0.6423,"confidence_interval_95":{"lower":-1.2049,"upper":2.3056}},"path_b_inactivity":{"coefficient":1.8019,"cluster_se":3.1423,"t_statistic":0.5734,"confidence_interval_95":{"lower":-4.6348,"upper":8.2387}},"direct_poverty":{"coefficient":-2.4926,"cluster_se":3.2106,"t_statistic":-0.7764,"confidence_interval_95":{"lower":-9.0693,"upper":4.0841}},"first_stage_partial_f":{"delta_poverty":1.1813,"delta_inactivity":1.0512},"stacked_indirect":{"cross_equation_correction":1.0432,"a_b_covariance":1.4496,"estimate":0.9917,"cluster_se":2.8722,"confidence_interval_95":{"lower":-4.8918,"upper":6.8752}},"leave_one_state_out":[{"omitted_state":"AL","n":604,"indirect_effect":1.6037,"direct_poverty":-3.1689},{"omitted_state":"AR","n":612,"indirect_effect":0.8621,"direct_poverty":-2.1249},{"omitted_state":"DC","n":608,"indirect_effect":0.4657,"direct_poverty":-1.7938},{"omitted_state":"DE","n":606,"indirect_effect":0.9221,"direct_poverty":-2.3853},{"omitted_state":"FL","n":610,"indirect_effect":0.8369,"direct_poverty":-2.3897},{"omitted_state":"GA","n":604,"indirect_effect":1.3135,"direct_poverty":-2.8821},{"omitted_state":"IA","n":612,"indirect_effect":1.0189,"direct_poverty":-2.4828},{"omitted_state":"IL","n":612,"indirect_effect":1.0404,"direct_poverty":-2.5097},{"omitted_state":"IN","n":604,"indirect_effect":0.8313,"direct_poverty":-1.9461},{"omitted_state":"KS","n":612,"indirect_effect":1.0599,"direct_poverty":-2.5025},{"omitted_state":"KY","n":610,"indirect_effect":0.3974,"direct_poverty":-1.8086},{"omitted_state":"LA","n":610,"indirect_effect":1.0299,"direct_poverty":-2.6493},{"omitted_state":"MD","n":610,"indirect_effect":2.2393,"direct_poverty":-4.1242},{"omitted_state":"MI","n":610,"indirect_effect":1.1103,"direct_poverty":-2.9985},{"omitted_state":"MN","n":614,"indirect_effect":0.7258,"direct_poverty":-2.2075},{"omitted_state":"MO","n":606,"indirect_effect":9.6063,"direct_poverty":-11.1967},{"omitted_state":"MS","n":612,"indirect_effect":1.1684,"direct_poverty":-2.7105},{"omitted_state":"NC","n":606,"indirect_effect":2.2043,"direct_poverty":-3.6588},{"omitted_state":"ND","n":606,"indirect_effect":0.3828,"direct_poverty":-1.8566},{"omitted_state":"NE","n":606,"indirect_effect":0.5557,"direct_poverty":-1.9541},{"omitted_state":"OH","n":606,"indirect_effect":0.6378,"direct_poverty":-2.2074},{"omitted_state":"OK","n":610,"indirect_effect":0.3721,"direct_poverty":-1.8945},{"omitted_state":"SC","n":612,"indirect_effect":0.3875,"direct_poverty":-2.1701},{"omitted_state":"SD","n":612,"indirect_effect":0.9406,"direct_poverty":-2.2615},{"omitted_state":"TN","n":612,"indirect_effect":3.0658,"direct_poverty":-4.6238},{"omitted_state":"TX","n":606,"indirect_effect":1.6481,"direct_poverty":-3.4813},{"omitted_state":"VA","n":600,"indirect_effect":0.9541,"direct_poverty":-2.54},{"omitted_state":"WI","n":606,"indirect_effect":0.841,"direct_poverty":-2.1287},{"omitted_state":"WV","n":602,"indirect_effect":0.783,"direct_poverty":-2.2139}]},"nested_state_ridge":{"n":553,"fold_count":29,"lambda_grid":[0.02,0.2,2.0,20.0,200.0],"pooled_base_rmse":2.5549,"pooled_augmented_rmse":2.0658,"augmented_better_state_count":26,"outer_folds":[{"state":"AL","n":19,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5976,2.587,2.5764,2.5774,2.7099],"augmented_inner_rmse":[2.1268,2.1151,2.0988,2.082,2.1232],"base_outer_rmse":2.1176,"augmented_outer_rmse":1.6407},{"state":"AR","n":15,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5465,2.5373,2.5308,2.5406,2.675],"augmented_inner_rmse":[2.0959,2.0852,2.0718,2.0602,2.1043],"base_outer_rmse":3.3365,"augmented_outer_rmse":2.3244},{"state":"DC","n":18,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5463,2.5369,2.532,2.5389,2.6675],"augmented_inner_rmse":[2.1165,2.1041,2.088,2.0718,2.1111],"base_outer_rmse":3.1097,"augmented_outer_rmse":1.933},{"state":"DE","n":21,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5809,2.5708,2.5629,2.5675,2.7108],"augmented_inner_rmse":[2.1321,2.1195,2.1038,2.0879,2.1319],"base_outer_rmse":2.3766,"augmented_outer_rmse":1.483},{"state":"FL","n":19,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5852,2.5751,2.5666,2.5689,2.6992],"augmented_inner_rmse":[2.1142,2.102,2.0861,2.0693,2.1122],"base_outer_rmse":2.3547,"augmented_outer_rmse":2.0418},{"state":"GA","n":22,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5714,2.5616,2.554,2.558,2.6922],"augmented_inner_rmse":[2.1276,2.1159,2.1,2.0837,2.1263],"base_outer_rmse":2.6889,"augmented_outer_rmse":1.6997},{"state":"IA","n":20,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5809,2.5709,2.563,2.5667,2.7012],"augmented_inner_rmse":[2.1017,2.0897,2.0736,2.0576,2.1009],"base_outer_rmse":2.422,"augmented_outer_rmse":2.2911},{"state":"IL","n":17,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.575,2.5644,2.5567,2.5607,2.6981],"augmented_inner_rmse":[2.12,2.108,2.0926,2.0767,2.1194],"base_outer_rmse":2.5813,"augmented_outer_rmse":1.747},{"state":"IN","n":18,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5914,2.5801,2.5702,2.5712,2.7012],"augmented_inner_rmse":[2.1202,2.1077,2.0911,2.0739,2.1148],"base_outer_rmse":2.3579,"augmented_outer_rmse":1.9126},{"state":"KS","n":17,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5943,2.5852,2.5799,2.5864,2.711],"augmented_inner_rmse":[2.1134,2.1021,2.0867,2.074,2.1147],"base_outer_rmse":1.9259,"augmented_outer_rmse":1.8296},{"state":"KY","n":15,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5796,2.5691,2.5596,2.5634,2.6985],"augmented_inner_rmse":[2.087,2.0757,2.0597,2.0442,2.0892],"base_outer_rmse":2.444,"augmented_outer_rmse":2.644},{"state":"LA","n":18,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.6028,2.5909,2.5821,2.5848,2.7111],"augmented_inner_rmse":[2.1241,2.1122,2.096,2.0796,2.1221],"base_outer_rmse":1.8432,"augmented_outer_rmse":1.6666},{"state":"MD","n":17,"base_lambda":20.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5776,2.567,2.5545,2.5544,2.6964],"augmented_inner_rmse":[2.1051,2.0956,2.0801,2.0631,2.1066],"base_outer_rmse":2.588,"augmented_outer_rmse":2.1323},{"state":"MI","n":18,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.589,2.579,2.5708,2.5746,2.7035],"augmented_inner_rmse":[2.1217,2.1105,2.0949,2.0797,2.1191],"base_outer_rmse":2.1485,"augmented_outer_rmse":1.6827},{"state":"MN","n":19,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5874,2.5762,2.5675,2.5713,2.7016],"augmented_inner_rmse":[2.1105,2.0989,2.0832,2.0668,2.107],"base_outer_rmse":2.3082,"augmented_outer_rmse":2.107},{"state":"MO","n":19,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5826,2.572,2.5613,2.5617,2.6947],"augmented_inner_rmse":[2.108,2.0971,2.0811,2.0646,2.1064],"base_outer_rmse":2.4759,"augmented_outer_rmse":2.0985},{"state":"MS","n":23,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5592,2.5488,2.5389,2.5437,2.6874],"augmented_inner_rmse":[2.1007,2.0884,2.0718,2.0557,2.1025],"base_outer_rmse":2.9212,"augmented_outer_rmse":2.2932},{"state":"NC","n":21,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.6097,2.599,2.5899,2.5926,2.7264],"augmented_inner_rmse":[2.1137,2.1017,2.0854,2.0688,2.112],"base_outer_rmse":1.6791,"augmented_outer_rmse":2.0086},{"state":"ND","n":20,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.552,2.5429,2.5385,2.5458,2.6756],"augmented_inner_rmse":[2.1021,2.0903,2.0753,2.0611,2.1031],"base_outer_rmse":2.9889,"augmented_outer_rmse":2.2585},{"state":"NE","n":20,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5891,2.5809,2.574,2.577,2.7064],"augmented_inner_rmse":[2.1005,2.0922,2.0814,2.0674,2.1123],"base_outer_rmse":2.2657,"augmented_outer_rmse":2.0824},{"state":"OH","n":19,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5944,2.5842,2.5754,2.5795,2.7135],"augmented_inner_rmse":[2.105,2.0935,2.0776,2.0619,2.1063],"base_outer_rmse":2.0336,"augmented_outer_rmse":2.1842},{"state":"OK","n":17,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5231,2.5174,2.5113,2.5124,2.6283],"augmented_inner_rmse":[2.0914,2.0806,2.0656,2.0483,2.079],"base_outer_rmse":3.6457,"augmented_outer_rmse":2.6507},{"state":"SC","n":21,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5907,2.5803,2.5713,2.575,2.702],"augmented_inner_rmse":[2.1045,2.0931,2.0772,2.0618,2.1035],"base_outer_rmse":2.2323,"augmented_outer_rmse":2.1937},{"state":"SD","n":20,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5675,2.5581,2.5488,2.5536,2.6928],"augmented_inner_rmse":[2.1192,2.1077,2.0911,2.0747,2.1169],"base_outer_rmse":2.7652,"augmented_outer_rmse":1.8873},{"state":"TN","n":18,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5466,2.535,2.5243,2.5318,2.6801],"augmented_inner_rmse":[2.0774,2.0658,2.0506,2.0383,2.0918],"base_outer_rmse":3.2808,"augmented_outer_rmse":2.6723},{"state":"TX","n":21,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.6013,2.5906,2.5822,2.5866,2.7242],"augmented_inner_rmse":[2.1256,2.1139,2.0982,2.082,2.1244],"base_outer_rmse":1.8371,"augmented_outer_rmse":1.6512},{"state":"VA","n":20,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5645,2.5554,2.5492,2.5533,2.6876],"augmented_inner_rmse":[2.1059,2.0958,2.0843,2.0701,2.113],"base_outer_rmse":2.7246,"augmented_outer_rmse":1.9874},{"state":"WI","n":20,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5677,2.5575,2.5507,2.5577,2.6914],"augmented_inner_rmse":[2.1005,2.0893,2.0749,2.0612,2.1062],"base_outer_rmse":2.7081,"augmented_outer_rmse":2.2036},{"state":"WV","n":21,"base_lambda":2.0,"augmented_lambda":20.0,"base_inner_rmse":[2.5589,2.5487,2.54,2.5427,2.6724],"augmented_inner_rmse":[2.1055,2.0936,2.0783,2.0624,2.1047],"base_outer_rmse":2.95,"augmented_outer_rmse":2.2052}]},"wild_cluster_bootstrap_t":{"method":"RESTRICTED_NULL_PAIRED_STATE_XORSHIFT32_BOOTSTRAP_T","seed":23032023,"replicate_count":2047,"final_prng_state":633790947,"equations":[{"equation":"TOTAL_POVERTY","observed_coefficient":0.9275,"observed_cr1_se":0.093,"observed_t":9.9753,"bootstrap_p_value":0.0005,"bootstrap_t_q025":-2.1796,"bootstrap_t_q975":2.2012,"confidence_interval_95":{"lower":0.7228,"upper":1.1302}},{"equation":"PATH_A_POVERTY","observed_coefficient":0.8562,"observed_cr1_se":0.0794,"observed_t":10.7832,"bootstrap_p_value":0.0005,"bootstrap_t_q025":-2.2557,"bootstrap_t_q975":2.1785,"confidence_interval_95":{"lower":0.6832,"upper":1.0353}},{"equation":"PATH_B_INACTIVITY","observed_coefficient":0.6862,"observed_cr1_se":0.0411,"observed_t":16.6797,"bootstrap_p_value":0.0005,"bootstrap_t_q025":-2.1888,"bootstrap_t_q975":2.1696,"confidence_interval_95":{"lower":0.5969,"upper":0.7762}}],"checkpoints":[{"replicate":1,"prng_state":1043009011,"total_poverty_t":-0.3104,"path_a_poverty_t":-0.5735,"path_b_inactivity_t":0.3982},{"replicate":2,"prng_state":3453684193,"total_poverty_t":-0.683,"path_a_poverty_t":-0.9977,"path_b_inactivity_t":-0.5622},{"replicate":4,"prng_state":2039393463,"total_poverty_t":-0.2854,"path_a_poverty_t":-0.1419,"path_b_inactivity_t":-0.3779},{"replicate":8,"prng_state":2637430752,"total_poverty_t":-0.0746,"path_a_poverty_t":0.2022,"path_b_inactivity_t":0.3515},{"replicate":16,"prng_state":2832156832,"total_poverty_t":-1.2343,"path_a_poverty_t":-0.9874,"path_b_inactivity_t":-0.9636},{"replicate":32,"prng_state":2665796618,"total_poverty_t":-1.9718,"path_a_poverty_t":-1.7708,"path_b_inactivity_t":-1.7322},{"replicate":64,"prng_state":1841784346,"total_poverty_t":0.3788,"path_a_poverty_t":0.0756,"path_b_inactivity_t":0.8276},{"replicate":128,"prng_state":3986400019,"total_poverty_t":-1.0496,"path_a_poverty_t":-0.8527,"path_b_inactivity_t":-1.4309},{"replicate":256,"prng_state":2055712123,"total_poverty_t":0.7648,"path_a_poverty_t":1.3707,"path_b_inactivity_t":0.3802},{"replicate":512,"prng_state":202963239,"total_poverty_t":0.6279,"path_a_poverty_t":0.4621,"path_b_inactivity_t":0.326},{"replicate":1024,"prng_state":1199888146,"total_poverty_t":0.599,"path_a_poverty_t":0.4389,"path_b_inactivity_t":0.0548},{"replicate":2047,"prng_state":633790947,"total_poverty_t":0.8465,"path_a_poverty_t":0.5212,"path_b_inactivity_t":0.4663}]},"state_grouped_conformal":{"nominal_coverage":0.9,"fixed_lambda":2.0,"overall_coverage":0.9928,"mean_interval_width":11.9003,"state_count_at_or_above_80pct":29,"cycles":[{"test_fold":0,"calibration_fold":4,"training_state_count":18,"calibration_state_count":5,"test_state_count":6,"calibration_count":93,"test_count":115,"qhat_state_max":5.5283,"test_coverage":0.9913,"mean_interval_width":11.0566,"worst_test_state":"KY"},{"test_fold":1,"calibration_fold":0,"training_state_count":17,"calibration_state_count":6,"test_state_count":6,"calibration_count":115,"test_count":113,"qhat_state_max":5.5088,"test_coverage":0.9823,"mean_interval_width":11.0176,"worst_test_state":"AR"},{"test_fold":2,"calibration_fold":1,"training_state_count":17,"calibration_state_count":6,"test_state_count":6,"calibration_count":113,"test_count":114,"qhat_state_max":6.6981,"test_coverage":1.0,"mean_interval_width":13.3961,"worst_test_state":"DC"},{"test_fold":3,"calibration_fold":2,"training_state_count":17,"calibration_state_count":6,"test_state_count":6,"calibration_count":114,"test_count":118,"qhat_state_max":5.8246,"test_coverage":0.9915,"mean_interval_width":11.6493,"worst_test_state":"ND"},{"test_fold":4,"calibration_fold":3,"training_state_count":18,"calibration_state_count":6,"test_state_count":5,"calibration_count":118,"test_count":93,"qhat_state_max":6.2506,"test_coverage":1.0,"mean_interval_width":12.5013,"worst_test_state":"FL"}],"state_coverage":[{"state":"AL","n":19,"coverage":1.0,"mean_width":11.0566},{"state":"AR","n":15,"coverage":0.9333,"mean_width":11.0176},{"state":"DC","n":18,"coverage":1.0,"mean_width":13.3961},{"state":"DE","n":21,"coverage":1.0,"mean_width":11.6493},{"state":"FL","n":19,"coverage":1.0,"mean_width":12.5013},{"state":"GA","n":22,"coverage":1.0,"mean_width":11.0566},{"state":"IA","n":20,"coverage":1.0,"mean_width":11.0176},{"state":"IL","n":17,"coverage":1.0,"mean_width":13.3961},{"state":"IN","n":18,"coverage":1.0,"mean_width":11.6493},{"state":"KS","n":17,"coverage":1.0,"mean_width":12.5013},{"state":"KY","n":15,"coverage":0.9333,"mean_width":11.0566},{"state":"LA","n":18,"coverage":1.0,"mean_width":11.0176},{"state":"MD","n":17,"coverage":1.0,"mean_width":13.3961},{"state":"MI","n":18,"coverage":1.0,"mean_width":11.6493},{"state":"MN","n":19,"coverage":1.0,"mean_width":12.5013},{"state":"MO","n":19,"coverage":1.0,"mean_width":11.0566},{"state":"MS","n":23,"coverage":1.0,"mean_width":11.0176},{"state":"NC","n":21,"coverage":1.0,"mean_width":13.3961},{"state":"ND","n":20,"coverage":0.95,"mean_width":11.6493},{"state":"NE","n":20,"coverage":1.0,"mean_width":12.5013},{"state":"OH","n":19,"coverage":1.0,"mean_width":11.0566},{"state":"OK","n":17,"coverage":0.9412,"mean_width":11.0176},{"state":"SC","n":21,"coverage":1.0,"mean_width":13.3961},{"state":"SD","n":20,"coverage":1.0,"mean_width":11.6493},{"state":"TN","n":18,"coverage":1.0,"mean_width":12.5013},{"state":"TX","n":21,"coverage":1.0,"mean_width":11.0566},{"state":"VA","n":20,"coverage":1.0,"mean_width":11.0176},{"state":"WI","n":20,"coverage":1.0,"mean_width":13.3961},{"state":"WV","n":21,"coverage":1.0,"mean_width":11.6493}]},"mediation_sensitivity_surface":{"baseline_path_a":0.8562,"baseline_path_b":0.6862,"baseline_path_b_se":0.0358,"residual_degrees_of_freedom":558,"equal_strength_tipping_r2":0.5468,"surface":[{"r2_mediator":0.04,"r2_outcome":0.04,"direction":"NEGATIVE","adjusted_path_b":0.7207,"adjusted_indirect":0.617,"adjusted_direct":0.3105,"proportion":0.6652},{"r2_mediator":0.04,"r2_outcome":0.04,"direction":"POSITIVE","adjusted_path_b":0.6517,"adjusted_indirect":0.558,"adjusted_direct":0.3696,"proportion":0.6016},{"r2_mediator":0.04,"r2_outcome":0.08,"direction":"NEGATIVE","adjusted_path_b":0.735,"adjusted_indirect":0.6293,"adjusted_direct":0.2983,"proportion":0.6784},{"r2_mediator":0.04,"r2_outcome":0.08,"direction":"POSITIVE","adjusted_path_b":0.6374,"adjusted_indirect":0.5457,"adjusted_direct":0.3818,"proportion":0.5884},{"r2_mediator":0.04,"r2_outcome":0.16,"direction":"NEGATIVE","adjusted_path_b":0.7552,"adjusted_indirect":0.6466,"adjusted_direct":0.281,"proportion":0.6971},{"r2_mediator":0.04,"r2_outcome":0.16,"direction":"POSITIVE","adjusted_path_b":0.6172,"adjusted_indirect":0.5284,"adjusted_direct":0.3991,"proportion":0.5697},{"r2_mediator":0.04,"r2_outcome":0.24,"direction":"NEGATIVE","adjusted_path_b":0.7707,"adjusted_indirect":0.6598,"adjusted_direct":0.2677,"proportion":0.7114},{"r2_mediator":0.04,"r2_outcome":0.24,"direction":"POSITIVE","adjusted_path_b":0.6017,"adjusted_indirect":0.5152,"adjusted_direct":0.4124,"proportion":0.5554},{"r2_mediator":0.04,"r2_outcome":0.32,"direction":"NEGATIVE","adjusted_path_b":0.7837,"adjusted_indirect":0.671,"adjusted_direct":0.2565,"proportion":0.7235},{"r2_mediator":0.04,"r2_outcome":0.32,"direction":"POSITIVE","adjusted_path_b":0.5886,"adjusted_indirect":0.504,"adjusted_direct":0.4235,"proportion":0.5434},{"r2_mediator":0.08,"r2_outcome":0.04,"direction":"NEGATIVE","adjusted_path_b":0.736,"adjusted_indirect":0.6302,"adjusted_direct":0.2974,"proportion":0.6794},{"r2_mediator":0.08,"r2_outcome":0.04,"direction":"POSITIVE","adjusted_path_b":0.6364,"adjusted_indirect":0.5448,"adjusted_direct":0.3827,"proportion":0.5874},{"r2_mediator":0.08,"r2_outcome":0.08,"direction":"NEGATIVE","adjusted_path_b":0.7567,"adjusted_indirect":0.6478,"adjusted_direct":0.2797,"proportion":0.6985},{"r2_mediator":0.08,"r2_outcome":0.08,"direction":"POSITIVE","adjusted_path_b":0.6157,"adjusted_indirect":0.5272,"adjusted_direct":0.4004,"proportion":0.5684},{"r2_mediator":0.08,"r2_outcome":0.16,"direction":"NEGATIVE","adjusted_path_b":0.7858,"adjusted_indirect":0.6728,"adjusted_direct":0.2547,"proportion":0.7254},{"r2_mediator":0.08,"r2_outcome":0.16,"direction":"POSITIVE","adjusted_path_b":0.5865,"adjusted_indirect":0.5022,"adjusted_direct":0.4253,"proportion":0.5414},{"r2_mediator":0.08,"r2_outcome":0.24,"direction":"NEGATIVE","adjusted_path_b":0.8082,"adjusted_indirect":0.692,"adjusted_direct":0.2355,"proportion":0.7461},{"r2_mediator":0.08,"r2_outcome":0.24,"direction":"POSITIVE","adjusted_path_b":0.5641,"adjusted_indirect":0.483,"adjusted_direct":0.4445,"proportion":0.5207},{"r2_mediator":0.08,"r2_outcome":0.32,"direction":"NEGATIVE","adjusted_path_b":0.8271,"adjusted_indirect":0.7082,"adjusted_direct":0.2193,"proportion":0.7635},{"r2_mediator":0.08,"r2_outcome":0.32,"direction":"POSITIVE","adjusted_path_b":0.5452,"adjusted_indirect":0.4668,"adjusted_direct":0.4607,"proportion":0.5033},{"r2_mediator":0.16,"r2_outcome":0.04,"direction":"NEGATIVE","adjusted_path_b":0.7599,"adjusted_indirect":0.6506,"adjusted_direct":0.2769,"proportion":0.7015},{"r2_mediator":0.16,"r2_outcome":0.04,"direction":"POSITIVE","adjusted_path_b":0.6124,"adjusted_indirect":0.5244,"adjusted_direct":0.4032,"proportion":0.5653},{"r2_mediator":0.16,"r2_outcome":0.08,"direction":"NEGATIVE","adjusted_path_b":0.7905,"adjusted_indirect":0.6768,"adjusted_direct":0.2507,"proportion":0.7297},{"r2_mediator":0.16,"r2_outcome":0.08,"direction":"POSITIVE","adjusted_path_b":0.5819,"adjusted_indirect":0.4982,"adjusted_direct":0.4293,"proportion":0.5371},{"r2_mediator":0.16,"r2_outcome":0.16,"direction":"NEGATIVE","adjusted_path_b":0.8337,"adjusted_indirect":0.7138,"adjusted_direct":0.2137,"proportion":0.7696},{"r2_mediator":0.16,"r2_outcome":0.16,"direction":"POSITIVE","adjusted_path_b":0.5387,"adjusted_indirect":0.4612,"adjusted_direct":0.4663,"proportion":0.4973},{"r2_mediator":0.16,"r2_outcome":0.24,"direction":"NEGATIVE","adjusted_path_b":0.8668,"adjusted_indirect":0.7422,"adjusted_direct":0.1854,"proportion":0.8002},{"r2_mediator":0.16,"r2_outcome":0.24,"direction":"POSITIVE","adjusted_path_b":0.5055,"adjusted_indirect":0.4328,"adjusted_direct":0.4947,"proportion":0.4667},{"r2_mediator":0.16,"r2_outcome":0.32,"direction":"NEGATIVE","adjusted_path_b":0.8948,"adjusted_indirect":0.7661,"adjusted_direct":0.1614,"proportion":0.826},{"r2_mediator":0.16,"r2_outcome":0.32,"direction":"POSITIVE","adjusted_path_b":0.4776,"adjusted_indirect":0.4089,"adjusted_direct":0.5186,"proportion":0.4409},{"r2_mediator":0.24,"r2_outcome":0.04,"direction":"NEGATIVE","adjusted_path_b":0.7811,"adjusted_indirect":0.6688,"adjusted_direct":0.2587,"proportion":0.7211},{"r2_mediator":0.24,"r2_outcome":0.04,"direction":"POSITIVE","adjusted_path_b":0.5912,"adjusted_indirect":0.5062,"adjusted_direct":0.4213,"proportion":0.5458},{"r2_mediator":0.24,"r2_outcome":0.08,"direction":"NEGATIVE","adjusted_path_b":0.8205,"adjusted_indirect":0.7025,"adjusted_direct":0.225,"proportion":0.7574},{"r2_mediator":0.24,"r2_outcome":0.08,"direction":"POSITIVE","adjusted_path_b":0.5519,"adjusted_indirect":0.4725,"adjusted_direct":0.455,"proportion":0.5094},{"r2_mediator":0.24,"r2_outcome":0.16,"direction":"NEGATIVE","adjusted_path_b":0.8761,"adjusted_indirect":0.7501,"adjusted_direct":0.1774,"proportion":0.8087},{"r2_mediator":0.24,"r2_outcome":0.16,"direction":"POSITIVE","adjusted_path_b":0.4963,"adjusted_indirect":0.4249,"adjusted_direct":0.5026,"proportion":0.4581},{"r2_mediator":0.24,"r2_outcome":0.24,"direction":"NEGATIVE","adjusted_path_b":0.9188,"adjusted_indirect":0.7866,"adjusted_direct":0.1409,"proportion":0.8481},{"r2_mediator":0.24,"r2_outcome":0.24,"direction":"POSITIVE","adjusted_path_b":0.4536,"adjusted_indirect":0.3883,"adjusted_direct":0.5392,"proportion":0.4187},{"r2_mediator":0.24,"r2_outcome":0.32,"direction":"NEGATIVE","adjusted_path_b":0.9548,"adjusted_indirect":0.8175,"adjusted_direct":0.1101,"proportion":0.8813},{"r2_mediator":0.24,"r2_outcome":0.32,"direction":"POSITIVE","adjusted_path_b":0.4176,"adjusted_indirect":0.3575,"adjusted_direct":0.57,"proportion":0.3855},{"r2_mediator":0.32,"r2_outcome":0.04,"direction":"NEGATIVE","adjusted_path_b":0.8021,"adjusted_indirect":0.6867,"adjusted_direct":0.2408,"proportion":0.7404},{"r2_mediator":0.32,"r2_outcome":0.04,"direction":"POSITIVE","adjusted_path_b":0.5703,"adjusted_indirect":0.4882,"adjusted_direct":0.4393,"proportion":0.5264},{"r2_mediator":0.32,"r2_outcome":0.08,"direction":"NEGATIVE","adjusted_path_b":0.8501,"adjusted_indirect":0.7279,"adjusted_direct":0.1997,"proportion":0.7847},{"r2_mediator":0.32,"r2_outcome":0.08,"direction":"POSITIVE","adjusted_path_b":0.5222,"adjusted_indirect":0.4471,"adjusted_direct":0.4804,"proportion":0.4821},{"r2_mediator":0.32,"r2_outcome":0.16,"direction":"NEGATIVE","adjusted_path_b":0.918,"adjusted_indirect":0.786,"adjusted_direct":0.1415,"proportion":0.8474},{"r2_mediator":0.32,"r2_outcome":0.16,"direction":"POSITIVE","adjusted_path_b":0.4543,"adjusted_indirect":0.389,"adjusted_direct":0.5385,"proportion":0.4194},{"r2_mediator":0.32,"r2_outcome":0.24,"direction":"NEGATIVE","adjusted_path_b":0.9701,"adjusted_indirect":0.8306,"adjusted_direct":0.0969,"proportion":0.8955},{"r2_mediator":0.32,"r2_outcome":0.24,"direction":"POSITIVE","adjusted_path_b":0.4022,"adjusted_indirect":0.3444,"adjusted_direct":0.5831,"proportion":0.3713},{"r2_mediator":0.32,"r2_outcome":0.32,"direction":"NEGATIVE","adjusted_path_b":1.0141,"adjusted_indirect":0.8682,"adjusted_direct":0.0593,"proportion":0.9361},{"r2_mediator":0.32,"r2_outcome":0.32,"direction":"POSITIVE","adjusted_path_b":0.3583,"adjusted_indirect":0.3068,"adjusted_direct":0.6207,"proportion":0.3308}]},"trajectory_pca_clustering":{"state_count":29,"feature_count":12,"kmeans_iterations":5,"eigenvalues":[10.9691,0.845,0.042],"explained_variance_ratio":[0.9141,0.0704,0.0035],"loadings":[{"feature":"2021_POVERTY","pc1":0.2775,"pc2":0.4208},{"feature":"2021_INACTIVITY","pc1":0.2946,"pc2":-0.1546},{"feature":"2021_OBESITY","pc1":0.294,"pc2":-0.2152},{"feature":"2022_POVERTY","pc1":0.2799,"pc2":0.3989},{"feature":"2022_INACTIVITY","pc1":0.295,"pc2":-0.1548},{"feature":"2022_OBESITY","pc1":0.291,"pc2":-0.2585},{"feature":"2023_POVERTY","pc1":0.2782,"pc2":0.4151},{"feature":"2023_INACTIVITY","pc1":0.2938,"pc2":-0.1895},{"feature":"2023_OBESITY","pc1":0.295,"pc2":-0.1911},{"feature":"2024_POVERTY","pc1":0.2778,"pc2":0.4166},{"feature":"2024_INACTIVITY","pc1":0.2951,"pc2":-0.16},{"feature":"2024_OBESITY","pc1":0.291,"pc2":-0.2429}],"states":[{"state":"AL","balanced_county_count":13,"pc1_score":3.0132,"pc2_score":0.7151,"cluster":1},{"state":"AR","balanced_county_count":9,"pc1_score":4.1178,"pc2_score":-0.8739,"cluster":1},{"state":"DC","balanced_county_count":11,"pc1_score":5.8493,"pc2_score":-0.4988,"cluster":1},{"state":"DE","balanced_county_count":12,"pc1_score":0.4502,"pc2_score":-0.0903,"cluster":3},{"state":"FL","balanced_county_count":10,"pc1_score":1.2869,"pc2_score":-1.7648,"cluster":1},{"state":"GA","balanced_county_count":13,"pc1_score":-1.391,"pc2_score":0.1423,"cluster":3},{"state":"IA","balanced_county_count":9,"pc1_score":-3.0796,"pc2_score":0.5085,"cluster":3},{"state":"IL","balanced_county_count":9,"pc1_score":0.269,"pc2_score":0.0366,"cluster":3},{"state":"IN","balanced_county_count":13,"pc1_score":-5.7899,"pc2_score":-0.4148,"cluster":2},{"state":"KS","balanced_county_count":9,"pc1_score":-6.4809,"pc2_score":-0.7396,"cluster":2},{"state":"KY","balanced_county_count":10,"pc1_score":3.4814,"pc2_score":0.7815,"cluster":1},{"state":"LA","balanced_county_count":10,"pc1_score":-2.0345,"pc2_score":-0.384,"cluster":3},{"state":"MD","balanced_county_count":10,"pc1_score":2.6625,"pc2_score":1.4762,"cluster":1},{"state":"MI","balanced_county_count":10,"pc1_score":-2.4901,"pc2_score":-1.0822,"cluster":3},{"state":"MN","balanced_county_count":8,"pc1_score":-1.8099,"pc2_score":0.3399,"cluster":3},{"state":"MO","balanced_county_count":12,"pc1_score":3.7188,"pc2_score":0.5214,"cluster":1},{"state":"MS","balanced_county_count":9,"pc1_score":0.3287,"pc2_score":-0.7495,"cluster":3},{"state":"NC","balanced_county_count":12,"pc1_score":1.3613,"pc2_score":1.0561,"cluster":1},{"state":"ND","balanced_county_count":12,"pc1_score":0.9466,"pc2_score":1.7308,"cluster":1},{"state":"NE","balanced_county_count":12,"pc1_score":-2.6635,"pc2_score":0.2869,"cluster":3},{"state":"OH","balanced_county_count":12,"pc1_score":-0.6336,"pc2_score":0.6102,"cluster":3},{"state":"OK","balanced_county_count":10,"pc1_score":-8.0468,"pc2_score":1.2554,"cluster":2},{"state":"SC","balanced_county_count":9,"pc1_score":4.8933,"pc2_score":-0.2306,"cluster":1},{"state":"SD","balanced_county_count":9,"pc1_score":-2.3372,"pc2_score":0.4606,"cluster":3},{"state":"TN","balanced_county_count":9,"pc1_score":-0.3623,"pc2_score":-1.5922,"cluster":3},{"state":"TX","balanced_county_count":12,"pc1_score":1.0403,"pc2_score":0.1936,"cluster":1},{"state":"VA","balanced_county_count":15,"pc1_score":1.013,"pc2_score":-1.3116,"cluster":1},{"state":"WI","balanced_county_count":12,"pc1_score":2.0491,"pc2_score":0.8533,"cluster":1},{"state":"WV","balanced_county_count":14,"pc1_score":0.6379,"pc2_score":-1.236,"cluster":3}],"leave_one_year_out_stability":[{"omitted_year":2021,"adjusted_rand_index":0.753},{"omitted_year":2022,"adjusted_rand_index":1.0},{"omitted_year":2023,"adjusted_rand_index":1.0},{"omitted_year":2024,"adjusted_rand_index":1.0}],"mean_stability_ari":0.9383,"minimum_stability_ari":0.753},"controlled_conclusion":{"difference_gmm_supported":false,"nested_ridge_supported":true,"bootstrap_supported":true,"grouped_conformal_calibrated":true,"sensitivity_robust":true,"trajectory_stable":true,"supported_module_count":5,"classification":"PARTIAL_OBESITY_MEDIATION_AUDIT"}}')
    parse_error = None
    try:
        prediction = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) == 2 and sys.argv[1] else {}
    except Exception as exc:
        prediction = {}
        parse_error = f"invalid prediction JSON: {type(exc).__name__}"[:120]
    result = evaluate(prediction, gold)
    if parse_error is not None:
        result["notice"] = parse_error
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
