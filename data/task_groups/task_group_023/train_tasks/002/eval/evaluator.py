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
    gold_path = Path(__file__).resolve().parent.parent / "output" / "answer.json"
    gold = json.loads(gold_path.read_text())
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
