#!/usr/bin/env python3
"""Explicit semantic partial-credit evaluator for train task 005.

Each of the eight rubric points is divided into a small set of fixed-weight
business checks.  Long ordered audit tables are evidence for one named check;
they cannot overwhelm the critical model summaries through recursive leaf
counting.  Registry metadata remains optional and entirely unscored.
"""

from __future__ import annotations

import json
import math
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable


POINTS = [
    ("SP001", "Balanced diabetes publication cohort and ordered state census", 1, "cohort_and_state_census"),
    ("SP002", "Delete-state bias-corrected two-step GMM", 3, "delete_state_two_step_gmm"),
    ("SP003", "Full-grid nested state-blocked elastic net and ridge", 3, "nested_elastic_net"),
    ("SP004", "Reproducible poverty wild-cluster bootstrap-t audit", 3, "wild_cluster_bootstrap_t"),
    ("SP005", "Grouped conformal coverage and ordered calibration", 3, "grouped_conformal_calibration"),
    ("SP006", "Diabetes/economic trajectory PCA, clustering, and delete-state stability", 3, "trajectory_pca_clustering"),
    ("SP007", "Exhaustive source-group perturbation surface", 3, "source_group_perturbation"),
    ("SP008", "Six-gate diabetes deployment decision", 2, "decision"),
]
TOTAL_WEIGHT = sum(point[2] for point in POINTS)
MISSING = object()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def at(value: Any, path: str) -> Any:
    current = value
    for key in path.split(".") if path else []:
        if not isinstance(current, dict) or key not in current:
            return MISSING
        current = current[key]
    return current


def numeric_equal(candidate: Any, gold: Any) -> float:
    if isinstance(candidate, bool) or not isinstance(candidate, (int, float, Decimal)):
        return 0.0
    if isinstance(gold, int) and not isinstance(gold, bool):
        return float(isinstance(candidate, int) and not isinstance(candidate, bool) and candidate == gold)
    try:
        left = Decimal(str(candidate))
        right = Decimal(str(gold))
        if not left.is_finite() or not right.is_finite():
            return 0.0
        quantum = Decimal("0.000001")
        return float(left.quantize(quantum, rounding=ROUND_HALF_UP) == right.quantize(quantum, rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return 0.0


def exact_equal(candidate: Any, gold: Any) -> float:
    if isinstance(gold, bool):
        return float(isinstance(candidate, bool) and candidate is gold)
    if isinstance(gold, (int, float, Decimal)) and not isinstance(gold, bool):
        return numeric_equal(candidate, gold)
    return float(type(candidate) is type(gold) and candidate == gold)


CHECKERS: dict[str, Callable[[Any, Any], float]] = {
    "n": numeric_equal,
    "x": exact_equal,
}


def paths_fraction(candidate: Any, gold: Any, specs: list[tuple[str, str]]) -> float:
    if not specs:
        return 0.0
    return sum(CHECKERS[kind](at(candidate, path), at(gold, path)) for path, kind in specs) / len(specs)


def ordered_list_fraction(candidate: Any, gold: Any, checker: Callable[[Any, Any], float] = exact_equal) -> float:
    if not isinstance(candidate, list) or not isinstance(gold, list):
        return 0.0
    if not gold:
        return float(candidate == gold)
    earned = 0.0
    for index, expected in enumerate(gold):
        if index < len(candidate):
            earned += checker(candidate[index], expected)
    fraction = earned / len(gold)
    if len(candidate) != len(gold) and math.isclose(fraction, 1.0, abs_tol=1e-12):
        return 0.99
    return fraction


def ordered_rows_fraction(candidate: Any, gold: Any, specs: list[tuple[str, str]]) -> float:
    if not isinstance(candidate, list) or not isinstance(gold, list):
        return 0.0
    if not gold or not specs:
        return float(candidate == gold)
    earned = 0.0
    possible = len(gold) * len(specs)
    for index, expected in enumerate(gold):
        received = candidate[index] if index < len(candidate) and isinstance(candidate[index], dict) else {}
        if not isinstance(expected, dict):
            continue
        for path, kind in specs:
            earned += CHECKERS[kind](at(received, path), at(expected, path))
    fraction = earned / possible
    if len(candidate) != len(gold) and math.isclose(fraction, 1.0, abs_tol=1e-12):
        return 0.99
    return fraction


def semantic_band(raw_fraction: float) -> float:
    """Map array accuracy to explicit audit-completeness levels.

    An almost-complete long table is useful partial evidence, not an almost
    complete business result.  Exact evidence earns 1.0; incomplete evidence
    earns one of the documented 0.75/0.50/0.25 tiers.
    """
    fraction = max(0.0, min(1.0, float(raw_fraction)))
    if math.isclose(fraction, 1.0, abs_tol=1e-12):
        return 1.0
    if fraction >= 0.90:
        return 0.75
    if fraction >= 0.60:
        return 0.50
    if fraction > 0.0:
        return 0.25
    return 0.0


def semantic_list(candidate: Any, gold: Any, checker: Callable[[Any, Any], float] = exact_equal) -> float:
    return semantic_band(ordered_list_fraction(candidate, gold, checker))


def semantic_rows(candidate: Any, gold: Any, specs: list[tuple[str, str]]) -> float:
    return semantic_band(ordered_rows_fraction(candidate, gold, specs))


def nested_numeric_matrix(candidate: Any, gold: Any) -> float:
    if not isinstance(candidate, list) or not isinstance(gold, list):
        return 0.0
    if not gold:
        return float(candidate == gold)
    earned = 0.0
    possible = 0
    for row_index, expected_row in enumerate(gold):
        if not isinstance(expected_row, list):
            continue
        possible += len(expected_row)
        received_row = candidate[row_index] if row_index < len(candidate) and isinstance(candidate[row_index], list) else []
        earned += sum(numeric_equal(received_row[index], value) for index, value in enumerate(expected_row) if index < len(received_row))
    fraction = earned / possible if possible else 0.0
    exact_shape = len(candidate) == len(gold) and all(
        isinstance(candidate[index], list) and len(candidate[index]) == len(row)
        for index, row in enumerate(gold)
    )
    if not exact_shape and math.isclose(fraction, 1.0, abs_tol=1e-12):
        fraction = 0.99
    return semantic_band(fraction)


def nested_fold_rows(candidate: Any, gold: Any, child: str, specs: list[tuple[str, str]]) -> float:
    """Score one ordered child table per outer fold, then band its completeness."""
    if not isinstance(candidate, list) or not isinstance(gold, list) or not gold:
        return 0.0
    fold_scores = []
    for index, expected_fold in enumerate(gold):
        received_fold = candidate[index] if index < len(candidate) and isinstance(candidate[index], dict) else {}
        expected_child = expected_fold.get(child) if isinstance(expected_fold, dict) else None
        fold_scores.append(semantic_rows(received_fold.get(child), expected_child, specs))
    raw = sum(fold_scores) / len(gold)
    if len(candidate) != len(gold) and math.isclose(raw, 1.0, abs_tol=1e-12):
        raw = 0.99
    return semantic_band(raw)


def nested_fold_lists(candidate: Any, gold: Any, child: str, checker: Callable[[Any, Any], float] = numeric_equal) -> float:
    if not isinstance(candidate, list) or not isinstance(gold, list) or not gold:
        return 0.0
    fold_scores = []
    for index, expected_fold in enumerate(gold):
        received_fold = candidate[index] if index < len(candidate) and isinstance(candidate[index], dict) else {}
        expected_child = expected_fold.get(child) if isinstance(expected_fold, dict) else None
        fold_scores.append(semantic_list(received_fold.get(child), expected_child, checker))
    raw = sum(fold_scores) / len(gold)
    if len(candidate) != len(gold) and math.isclose(raw, 1.0, abs_tol=1e-12):
        raw = 0.99
    return semantic_band(raw)


def weighted(checks: list[tuple[str, float, float]]) -> tuple[float, dict[str, Any]]:
    if not math.isclose(sum(share for _, share, _ in checks), 1.0, abs_tol=1e-12):
        raise ValueError("semantic subcheck shares must sum to one")
    earned = 0.0
    details: dict[str, Any] = {}
    for name, share, result in checks:
        bounded = max(0.0, min(1.0, float(result)))
        earned += share * bounded
        details[name] = {
            "share_within_point": share,
            "earned_fraction": round(bounded, 12),
            "passed": math.isclose(bounded, 1.0, abs_tol=1e-12),
        }
    return earned, details


def score_points(candidate: dict[str, Any], gold: dict[str, Any]) -> list[tuple[float, dict[str, Any]]]:
    c1, g1 = at(candidate, "cohort_and_state_census"), gold["cohort_and_state_census"]
    sp1 = weighted([
        ("publication status, value type, and revision rule", 0.15, paths_fraction(c1, g1, [
            ("health_release_status", "x"), ("health_value_type", "x"), ("revision_selection", "x"),
        ])),
        ("balanced county and panel dimensions", 0.25, paths_fraction(c1, g1, [
            ("balanced_counties", "n"), ("panel_rows", "n"),
        ])),
        ("ordered state census with county and panel counts", 0.60, semantic_rows(
            at(c1, "state_census"), g1["state_census"],
            [("state_abbr", "x"), ("balanced_counties", "n"), ("panel_rows", "n")],
        )),
    ])

    c2, g2 = at(candidate, "delete_state_two_step_gmm"), gold["delete_state_two_step_gmm"]
    sp2 = weighted([
        ("instrument, parameter, and state dimensions", 0.05, paths_fraction(c2, g2, [
            ("instrument_count", "n"), ("parameter_count", "n"), ("state_cluster_count", "n"),
        ])),
        ("complete full-sample two-step GMM coefficients", 0.20, semantic_list(
            at(c2, "full_two_step_coefficients"), g2["full_two_step_coefficients"], numeric_equal,
        )),
        ("full-sample Hansen J statistic", 0.10, paths_fraction(c2, g2, [("full_hansen_j", "n")])),
        ("complete jackknife bias-corrected coefficients", 0.25, semantic_list(
            at(c2, "bias_corrected_coefficients"), g2["bias_corrected_coefficients"], numeric_equal,
        )),
        ("complete maximum absolute delete-state shifts", 0.15, semantic_list(
            at(c2, "maximum_absolute_delete_state_shifts"), g2["maximum_absolute_delete_state_shifts"], numeric_equal,
        )),
        ("ordered delete-state coefficient audit", 0.15, semantic_rows(
            at(c2, "delete_state_diagnostics"), g2["delete_state_diagnostics"],
            [("state_abbr", "x"), ("deleted_panel_rows", "n"), ("coefficients", "x")],
        )),
        ("ordered delete-state Hansen audit", 0.10, semantic_rows(
            at(c2, "delete_state_diagnostics"), g2["delete_state_diagnostics"],
            [("state_abbr", "x"), ("hansen_j", "n")],
        )),
    ])

    c3, g3 = at(candidate, "nested_elastic_net"), gold["nested_elastic_net"]
    c3folds, g3folds = at(c3, "outer_fold_diagnostics"), g3["outer_fold_diagnostics"]
    sp3 = weighted([
        ("outer and inner fold counts", 0.05, paths_fraction(c3, g3, [
            ("outer_fold_count", "n"), ("inner_fold_count", "n"),
        ])),
        ("coefficient order and candidate grid", 0.10, (
            semantic_list(at(c3, "coefficient_order"), g3["coefficient_order"]) +
            semantic_rows(at(c3, "candidate_grid"), g3["candidate_grid"], [("alpha", "n"), ("l1_ratio", "n")])
        ) / 2),
        ("ordered outer-fold assignments and dimensions", 0.10, semantic_rows(
            c3folds, g3folds, [("outer_fold", "n"), ("held_out_states", "x"), ("held_out_panel_rows", "n")],
        )),
        ("complete inner tuning surfaces", 0.20, nested_fold_rows(
            c3folds, g3folds, "grid_results", [("alpha", "n"), ("l1_ratio", "n"), ("inner_rmse", "n")],
        )),
        ("selected alpha and l1 ratio by fold", 0.10, semantic_rows(
            c3folds, g3folds, [("outer_fold", "n"), ("selected_alpha", "n"), ("selected_l1_ratio", "n")],
        )),
        ("selected standardized coefficients by fold", 0.15, nested_fold_lists(
            c3folds, g3folds, "selected_standardized_coefficients", numeric_equal,
        )),
        ("outer-fold RMSE audit", 0.10, semantic_rows(
            c3folds, g3folds, [("outer_fold", "n"), ("outer_rmse", "n")],
        )),
        ("pooled OOF RMSE and R-squared", 0.20, paths_fraction(c3, g3, [
            ("oof_rmse", "n"), ("oof_r_squared", "n"),
        ])),
    ])

    c4, g4 = at(candidate, "wild_cluster_bootstrap_t"), gold["wild_cluster_bootstrap_t"]
    sp4 = weighted([
        ("PRNG, seed, replicate, and cluster protocol", 0.10, paths_fraction(c4, g4, [
            ("prng", "x"), ("seed", "n"), ("replicate_count", "n"), ("state_cluster_count", "n"),
        ])),
        ("observed poverty coefficient, CR1 SE, and t", 0.25, paths_fraction(c4, g4, [
            ("observed_coefficient", "n"), ("observed_cr1_se", "n"), ("observed_t", "n"),
        ])),
        ("absolute-tail count and plus-one p value", 0.25, paths_fraction(c4, g4, [
            ("absolute_tail_exceedance_count", "n"), ("plus_one_p_value", "n"),
        ])),
        ("bootstrap-t quantiles", 0.15, semantic_list(
            at(c4, "bootstrap_t_quantiles"), g4["bootstrap_t_quantiles"], numeric_equal,
        )),
        ("ordered continuous-stream PRNG checkpoints", 0.25, semantic_rows(
            at(c4, "prng_checkpoints"), g4["prng_checkpoints"],
            [("replicate", "n"), ("prng_state", "n"), ("bootstrap_t", "n")],
        )),
    ])

    c5, g5 = at(candidate, "grouped_conformal_calibration"), gold["grouped_conformal_calibration"]
    sp5 = weighted([
        ("nominal coverage", 0.05, paths_fraction(c5, g5, [("nominal_coverage", "n")])),
        ("ordered fold radii, ranks, coverage, and width", 0.20, semantic_rows(
            at(c5, "fold_diagnostics"), g5["fold_diagnostics"],
            [("outer_fold", "n"), ("calibration_rows", "n"), ("nearest_rank", "n"), ("radius", "n"),
             ("held_out_rows", "n"), ("coverage", "n"), ("mean_width", "n")],
        )),
        ("ordered state coverage audit", 0.20, semantic_rows(
            at(c5, "state_coverage"), g5["state_coverage"],
            [("state_abbr", "x"), ("panel_rows", "n"), ("coverage", "n")],
        )),
        ("RUCC-band coverage audit", 0.10, semantic_rows(
            at(c5, "rucc_band_coverage"), g5["rucc_band_coverage"],
            [("rucc_band", "x"), ("panel_rows", "n"), ("coverage", "n")],
        )),
        ("ordered prediction-decile calibration", 0.20, semantic_rows(
            at(c5, "decile_calibration"), g5["decile_calibration"],
            [("decile", "n"), ("panel_rows", "n"), ("prediction_mean", "n"),
             ("observation_mean", "n"), ("signed_gap", "n")],
        )),
        ("overall and minimum-state coverage summaries", 0.25, paths_fraction(c5, g5, [
            ("overall_coverage", "n"), ("minimum_state_coverage", "n"),
        ])),
    ])

    c6, g6 = at(candidate, "trajectory_pca_clustering"), gold["trajectory_pca_clustering"]
    sp6 = weighted([
        ("feature order and PCA dimensions", 0.08, (
            semantic_list(at(c6, "feature_order"), g6["feature_order"]) +
            paths_fraction(c6, g6, [("county_count", "n"), ("retained_component_count", "n")])
        ) / 2),
        ("first five eigenvalues", 0.10, semantic_list(
            at(c6, "first_five_eigenvalues"), g6["first_five_eigenvalues"], numeric_equal,
        )),
        ("first five explained shares", 0.10, semantic_list(
            at(c6, "first_five_explained_shares"), g6["first_five_explained_shares"], numeric_equal,
        )),
        ("first three oriented loading vectors", 0.15, nested_numeric_matrix(
            at(c6, "first_three_loading_vectors"), g6["first_three_loading_vectors"],
        )),
        ("ordered clustering grid", 0.15, semantic_rows(
            at(c6, "cluster_grid"), g6["cluster_grid"],
            [("cluster_count", "n"), ("inertia", "n"), ("average_silhouette", "n"), ("cluster_sizes", "x")],
        )),
        ("selected cluster count", 0.07, paths_fraction(c6, g6, [("selected_cluster_count", "n")])),
        ("ordered delete-state ARI stability", 0.15, semantic_rows(
            at(c6, "delete_state_stability"), g6["delete_state_stability"],
            [("deleted_state", "x"), ("retained_counties", "n"), ("adjusted_rand_index", "n")],
        )),
        ("median and minimum delete-state ARI summaries", 0.20, paths_fraction(c6, g6, [
            ("median_delete_state_ari", "n"), ("minimum_delete_state_ari", "n"),
        ])),
    ])

    c7, g7 = at(candidate, "source_group_perturbation"), gold["source_group_perturbation"]
    c7rows, g7rows = at(c7, "group_deletion_diagnostics"), g7["group_deletion_diagnostics"]
    sp7 = weighted([
        ("reference full OOF RMSE", 0.10, paths_fraction(c7, g7, [("reference_full_oof_rmse", "n")])),
        ("ordered source-group contract", 0.10, semantic_list(
            at(c7, "ordered_source_groups"), g7["ordered_source_groups"], exact_equal,
        )),
        ("source identities and removed-term sets", 0.15, semantic_rows(
            c7rows, g7rows, [("source_group", "x"), ("removed_terms", "x")],
        )),
        ("ordered fold RMSE surfaces", 0.20, nested_fold_lists(
            c7rows, g7rows, "outer_fold_rmses", numeric_equal,
        )),
        ("pooled deleted-source RMSEs", 0.15, semantic_rows(
            c7rows, g7rows, [("source_group", "x"), ("pooled_rmse", "n")],
        )),
        ("RMSE deterioration summaries", 0.15, semantic_rows(
            c7rows, g7rows, [("source_group", "x"), ("rmse_deterioration", "n")],
        )),
        ("worse-fold counts and deterioration ranks", 0.15, semantic_rows(
            c7rows, g7rows, [("source_group", "x"), ("worse_fold_count", "n"), ("deterioration_rank", "n")],
        )),
    ])

    sp8 = weighted([
        ("controlled six-gate deployment decision", 1.0, exact_equal(at(candidate, "decision"), gold["decision"])),
    ])
    return [sp1, sp2, sp3, sp4, sp5, sp6, sp7, sp8]


def zero_result(message: str) -> dict[str, Any]:
    return {
        "score": 0.0,
        "score_possible": 1.0,
        "rubric": [
            {
                "point_id": point_id,
                "goal": goal,
                "raw_weight": weight,
                "normalized_max": round(weight / TOTAL_WEIGHT, 12),
                "earned_fraction": 0.0,
                "earned_normalized_score": 0.0,
                "subchecks": {},
            }
            for point_id, goal, weight, _ in POINTS
        ],
        "diagnostics": [message],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps(zero_result("usage: evaluator.py <prediction.json>"), separators=(",", ":")))
        return 0
    try:
        candidate = load_json(Path(sys.argv[1]))
        gold = json.loads('{"cohort_and_state_census":{"health_release_status":"FINAL","health_value_type":"CRUDE","revision_selection":"HIGHEST_FINAL_REVISION","balanced_counties":305,"panel_rows":915,"state_census":[{"state_abbr":"AK","balanced_counties":17,"panel_rows":51},{"state_abbr":"AZ","balanced_counties":17,"panel_rows":51},{"state_abbr":"CA","balanced_counties":13,"panel_rows":39},{"state_abbr":"CO","balanced_counties":14,"panel_rows":42},{"state_abbr":"CT","balanced_counties":9,"panel_rows":27},{"state_abbr":"HI","balanced_counties":15,"panel_rows":45},{"state_abbr":"ID","balanced_counties":13,"panel_rows":39},{"state_abbr":"MA","balanced_counties":18,"panel_rows":54},{"state_abbr":"ME","balanced_counties":14,"panel_rows":42},{"state_abbr":"MT","balanced_counties":15,"panel_rows":45},{"state_abbr":"NH","balanced_counties":13,"panel_rows":39},{"state_abbr":"NJ","balanced_counties":15,"panel_rows":45},{"state_abbr":"NM","balanced_counties":13,"panel_rows":39},{"state_abbr":"NV","balanced_counties":9,"panel_rows":27},{"state_abbr":"NY","balanced_counties":13,"panel_rows":39},{"state_abbr":"OR","balanced_counties":12,"panel_rows":36},{"state_abbr":"PA","balanced_counties":18,"panel_rows":54},{"state_abbr":"RI","balanced_counties":11,"panel_rows":33},{"state_abbr":"UT","balanced_counties":15,"panel_rows":45},{"state_abbr":"VT","balanced_counties":15,"panel_rows":45},{"state_abbr":"WA","balanced_counties":17,"panel_rows":51},{"state_abbr":"WY","balanced_counties":9,"panel_rows":27}]},"delete_state_two_step_gmm":{"instrument_count":8,"parameter_count":4,"state_cluster_count":22,"full_two_step_coefficients":[0.04609,-0.017956,-0.022895,0.000576],"full_hansen_j":3.807725,"bias_corrected_coefficients":[0.04725,-0.026551,-0.038346,0.001394],"maximum_absolute_delete_state_shifts":[0.008991,0.015336,0.022139,0.00189],"delete_state_diagnostics":[{"state_abbr":"AK","deleted_panel_rows":51,"coefficients":[0.040344,-0.028859,-0.013892,-0.001118],"hansen_j":4.259924},{"state_abbr":"AZ","deleted_panel_rows":51,"coefficients":[0.049072,-0.029022,-0.032885,0.001509],"hansen_j":2.85781},{"state_abbr":"CA","deleted_panel_rows":39,"coefficients":[0.039654,-0.016886,-0.015982,0.001567],"hansen_j":5.712779},{"state_abbr":"CO","deleted_panel_rows":42,"coefficients":[0.045206,-0.02147,-0.01879,0.000715],"hansen_j":2.943699},{"state_abbr":"CT","deleted_panel_rows":27,"coefficients":[0.044462,-0.016327,-0.027289,-6.5e-05],"hansen_j":4.338324},{"state_abbr":"HI","deleted_panel_rows":45,"coefficients":[0.049554,-0.00388,-0.035793,-0.000646],"hansen_j":3.732159},{"state_abbr":"ID","deleted_panel_rows":39,"coefficients":[0.037099,-0.018263,-0.027924,0.000359],"hansen_j":3.479126},{"state_abbr":"MA","deleted_panel_rows":54,"coefficients":[0.042573,-0.018137,-0.019963,0.00041],"hansen_j":3.519147},{"state_abbr":"ME","deleted_panel_rows":42,"coefficients":[0.045105,-0.012327,-0.016699,0.000433],"hansen_j":3.583569},{"state_abbr":"MT","deleted_panel_rows":45,"coefficients":[0.050954,-0.025696,-0.024095,5.2e-05],"hansen_j":3.964192},{"state_abbr":"NH","deleted_panel_rows":39,"coefficients":[0.046351,-0.01304,-0.000756,-0.000441],"hansen_j":4.570454},{"state_abbr":"NJ","deleted_panel_rows":45,"coefficients":[0.047878,-0.023041,-0.022088,0.000757],"hansen_j":2.513374},{"state_abbr":"NM","deleted_panel_rows":39,"coefficients":[0.039929,-0.008756,-0.030852,0.002466],"hansen_j":4.347567},{"state_abbr":"NV","deleted_panel_rows":27,"coefficients":[0.047384,-0.027137,-0.032765,4e-05],"hansen_j":3.324064},{"state_abbr":"NY","deleted_panel_rows":39,"coefficients":[0.048172,-0.00262,-0.008595,4.8e-05],"hansen_j":4.489043},{"state_abbr":"OR","deleted_panel_rows":36,"coefficients":[0.048733,-0.019223,-0.04112,0.00158],"hansen_j":4.532806},{"state_abbr":"PA","deleted_panel_rows":54,"coefficients":[0.04343,-0.015669,-0.033952,0.000849],"hansen_j":3.400942},{"state_abbr":"RI","deleted_panel_rows":33,"coefficients":[0.050457,-0.02078,-0.015345,0.000113],"hansen_j":3.757825},{"state_abbr":"UT","deleted_panel_rows":45,"coefficients":[0.052528,-0.025557,-0.010448,0.000301],"hansen_j":2.929014},{"state_abbr":"VT","deleted_panel_rows":45,"coefficients":[0.04984,-0.002835,-0.024179,0.001412],"hansen_j":4.044464},{"state_abbr":"WA","deleted_panel_rows":51,"coefficients":[0.045311,-0.017756,-0.024002,0.000725],"hansen_j":2.919961},{"state_abbr":"WY","deleted_panel_rows":27,"coefficients":[0.048734,-0.018754,-0.010092,0.000742],"hansen_j":4.224234}]},"nested_elastic_net":{"outer_fold_count":5,"inner_fold_count":4,"coefficient_order":["lagged_diabetes","lagged_poverty","rucc_2","rucc_3","rucc_4","rucc_5","rucc_6","rucc_7","rucc_8","rucc_9","end_2023","end_2024","poverty_change","unemployment_change","median_income_change_per_10000","net_migration_change"],"candidate_grid":[{"alpha":0.02,"l1_ratio":0.0},{"alpha":0.02,"l1_ratio":0.45},{"alpha":0.02,"l1_ratio":0.8},{"alpha":0.2,"l1_ratio":0.0},{"alpha":0.2,"l1_ratio":0.45},{"alpha":0.2,"l1_ratio":0.8},{"alpha":2.0,"l1_ratio":0.0},{"alpha":2.0,"l1_ratio":0.45},{"alpha":2.0,"l1_ratio":0.8},{"alpha":20.0,"l1_ratio":0.0},{"alpha":20.0,"l1_ratio":0.45},{"alpha":20.0,"l1_ratio":0.8}],"outer_fold_diagnostics":[{"outer_fold":1,"held_out_states":["ID","MA","NY","UT"],"held_out_panel_rows":177,"grid_results":[{"alpha":0.02,"l1_ratio":0.0,"inner_rmse":0.857165},{"alpha":0.02,"l1_ratio":0.45,"inner_rmse":0.848248},{"alpha":0.02,"l1_ratio":0.8,"inner_rmse":0.845496},{"alpha":0.2,"l1_ratio":0.0,"inner_rmse":0.857829},{"alpha":0.2,"l1_ratio":0.45,"inner_rmse":0.878387},{"alpha":0.2,"l1_ratio":0.8,"inner_rmse":0.890379},{"alpha":2.0,"l1_ratio":0.0,"inner_rmse":0.886318},{"alpha":2.0,"l1_ratio":0.45,"inner_rmse":0.899343},{"alpha":2.0,"l1_ratio":0.8,"inner_rmse":0.899343},{"alpha":20.0,"l1_ratio":0.0,"inner_rmse":0.897365},{"alpha":20.0,"l1_ratio":0.45,"inner_rmse":0.899343},{"alpha":20.0,"l1_ratio":0.8,"inner_rmse":0.899343}],"selected_alpha":0.02,"selected_l1_ratio":0.8,"selected_standardized_coefficients":[-0.503631,0.395597,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.022534,0.0,0.001197,-0.00765],"outer_rmse":0.7929},{"outer_fold":2,"held_out_states":["NH","OR","PA","VT"],"held_out_panel_rows":174,"grid_results":[{"alpha":0.02,"l1_ratio":0.0,"inner_rmse":0.874365},{"alpha":0.02,"l1_ratio":0.45,"inner_rmse":0.864561},{"alpha":0.02,"l1_ratio":0.8,"inner_rmse":0.861218},{"alpha":0.2,"l1_ratio":0.0,"inner_rmse":0.87375},{"alpha":0.2,"l1_ratio":0.45,"inner_rmse":0.894846},{"alpha":0.2,"l1_ratio":0.8,"inner_rmse":0.909058},{"alpha":2.0,"l1_ratio":0.0,"inner_rmse":0.905491},{"alpha":2.0,"l1_ratio":0.45,"inner_rmse":0.919502},{"alpha":2.0,"l1_ratio":0.8,"inner_rmse":0.919502},{"alpha":20.0,"l1_ratio":0.0,"inner_rmse":0.917408},{"alpha":20.0,"l1_ratio":0.45,"inner_rmse":0.919502},{"alpha":20.0,"l1_ratio":0.8,"inner_rmse":0.919502}],"selected_alpha":0.02,"selected_l1_ratio":0.8,"selected_standardized_coefficients":[-0.546999,0.43891,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.028908,0.0,-0.004038,0.0],"outer_rmse":0.724043},{"outer_fold":3,"held_out_states":["AK","CO","HI","RI","WY"],"held_out_panel_rows":198,"grid_results":[{"alpha":0.02,"l1_ratio":0.0,"inner_rmse":0.844229},{"alpha":0.02,"l1_ratio":0.45,"inner_rmse":0.838542},{"alpha":0.02,"l1_ratio":0.8,"inner_rmse":0.836262},{"alpha":0.2,"l1_ratio":0.0,"inner_rmse":0.840876},{"alpha":0.2,"l1_ratio":0.45,"inner_rmse":0.85971},{"alpha":0.2,"l1_ratio":0.8,"inner_rmse":0.871185},{"alpha":2.0,"l1_ratio":0.0,"inner_rmse":0.865975},{"alpha":2.0,"l1_ratio":0.45,"inner_rmse":0.882351},{"alpha":2.0,"l1_ratio":0.8,"inner_rmse":0.882351},{"alpha":20.0,"l1_ratio":0.0,"inner_rmse":0.87979},{"alpha":20.0,"l1_ratio":0.45,"inner_rmse":0.882351},{"alpha":20.0,"l1_ratio":0.8,"inner_rmse":0.882351}],"selected_alpha":0.02,"selected_l1_ratio":0.8,"selected_standardized_coefficients":[-0.433554,0.320639,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.028792,0.0,0.0,-0.03369],"outer_rmse":0.843469},{"outer_fold":4,"held_out_states":["AZ","CT","ME","MT","NV"],"held_out_panel_rows":192,"grid_results":[{"alpha":0.02,"l1_ratio":0.0,"inner_rmse":0.822788},{"alpha":0.02,"l1_ratio":0.45,"inner_rmse":0.819604},{"alpha":0.02,"l1_ratio":0.8,"inner_rmse":0.81885},{"alpha":0.2,"l1_ratio":0.0,"inner_rmse":0.830568},{"alpha":0.2,"l1_ratio":0.45,"inner_rmse":0.856302},{"alpha":0.2,"l1_ratio":0.8,"inner_rmse":0.867779},{"alpha":2.0,"l1_ratio":0.0,"inner_rmse":0.863108},{"alpha":2.0,"l1_ratio":0.45,"inner_rmse":0.878308},{"alpha":2.0,"l1_ratio":0.8,"inner_rmse":0.878308},{"alpha":20.0,"l1_ratio":0.0,"inner_rmse":0.875931},{"alpha":20.0,"l1_ratio":0.45,"inner_rmse":0.878308},{"alpha":20.0,"l1_ratio":0.8,"inner_rmse":0.878308}],"selected_alpha":0.02,"selected_l1_ratio":0.8,"selected_standardized_coefficients":[-0.502767,0.390036,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,-0.028532,0.0,0.039494,-0.008139,-0.007388,-0.006264],"outer_rmse":0.882968},{"outer_fold":5,"held_out_states":["CA","NJ","NM","WA"],"held_out_panel_rows":174,"grid_results":[{"alpha":0.02,"l1_ratio":0.0,"inner_rmse":0.825428},{"alpha":0.02,"l1_ratio":0.45,"inner_rmse":0.819172},{"alpha":0.02,"l1_ratio":0.8,"inner_rmse":0.818049},{"alpha":0.2,"l1_ratio":0.0,"inner_rmse":0.826648},{"alpha":0.2,"l1_ratio":0.45,"inner_rmse":0.848426},{"alpha":0.2,"l1_ratio":0.8,"inner_rmse":0.857492},{"alpha":2.0,"l1_ratio":0.0,"inner_rmse":0.84998},{"alpha":2.0,"l1_ratio":0.45,"inner_rmse":0.861121},{"alpha":2.0,"l1_ratio":0.8,"inner_rmse":0.861121},{"alpha":20.0,"l1_ratio":0.0,"inner_rmse":0.859429},{"alpha":20.0,"l1_ratio":0.45,"inner_rmse":0.861121},{"alpha":20.0,"l1_ratio":0.8,"inner_rmse":0.861121}],"selected_alpha":0.02,"selected_l1_ratio":0.8,"selected_standardized_coefficients":[-0.424093,0.333184,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,-0.025951,0.0,0.016258,0.0,0.0,0.008043],"outer_rmse":0.895921}],"oof_rmse":0.83156,"oof_r_squared":0.123257},"wild_cluster_bootstrap_t":{"prng":"XORSHIFT32","seed":7152026,"replicate_count":399,"state_cluster_count":22,"observed_coefficient":0.035692,"observed_cr1_se":0.018558,"observed_t":1.923308,"absolute_tail_exceedance_count":25,"plus_one_p_value":0.065,"bootstrap_t_quantiles":[-1.895591,0.011561,2.213941],"prng_checkpoints":[{"replicate":1,"prng_state":1748335863,"bootstrap_t":-1.829719},{"replicate":2,"prng_state":3043402384,"bootstrap_t":-2.046189},{"replicate":4,"prng_state":2708623836,"bootstrap_t":0.05708},{"replicate":9,"prng_state":279822795,"bootstrap_t":-0.954947},{"replicate":20,"prng_state":2345470466,"bootstrap_t":1.1881},{"replicate":50,"prng_state":3566115207,"bootstrap_t":0.165481},{"replicate":100,"prng_state":893469102,"bootstrap_t":-0.206613},{"replicate":200,"prng_state":2924293522,"bootstrap_t":0.860945},{"replicate":399,"prng_state":524424136,"bootstrap_t":0.640373}]},"grouped_conformal_calibration":{"nominal_coverage":0.9,"fold_diagnostics":[{"outer_fold":1,"calibration_rows":738,"nearest_rank":666,"radius":1.344583,"held_out_rows":177,"coverage":0.920904,"mean_width":2.689166},{"outer_fold":2,"calibration_rows":741,"nearest_rank":668,"radius":1.355529,"held_out_rows":174,"coverage":0.948276,"mean_width":2.711058},{"outer_fold":3,"calibration_rows":717,"nearest_rank":647,"radius":1.326075,"held_out_rows":198,"coverage":0.888889,"mean_width":2.65215},{"outer_fold":4,"calibration_rows":723,"nearest_rank":652,"radius":1.312552,"held_out_rows":192,"coverage":0.880208,"mean_width":2.625105},{"outer_fold":5,"calibration_rows":741,"nearest_rank":668,"radius":1.312007,"held_out_rows":174,"coverage":0.873563,"mean_width":2.624014}],"state_coverage":[{"state_abbr":"AK","panel_rows":51,"coverage":0.901961},{"state_abbr":"AZ","panel_rows":51,"coverage":0.823529},{"state_abbr":"CA","panel_rows":39,"coverage":0.923077},{"state_abbr":"CO","panel_rows":42,"coverage":0.880952},{"state_abbr":"CT","panel_rows":27,"coverage":0.888889},{"state_abbr":"HI","panel_rows":45,"coverage":0.8},{"state_abbr":"ID","panel_rows":39,"coverage":0.897436},{"state_abbr":"MA","panel_rows":54,"coverage":0.981481},{"state_abbr":"ME","panel_rows":42,"coverage":1.0},{"state_abbr":"MT","panel_rows":45,"coverage":0.866667},{"state_abbr":"NH","panel_rows":39,"coverage":0.974359},{"state_abbr":"NJ","panel_rows":45,"coverage":0.733333},{"state_abbr":"NM","panel_rows":39,"coverage":0.897436},{"state_abbr":"NV","panel_rows":27,"coverage":0.814815},{"state_abbr":"NY","panel_rows":39,"coverage":0.871795},{"state_abbr":"OR","panel_rows":36,"coverage":0.916667},{"state_abbr":"PA","panel_rows":54,"coverage":0.962963},{"state_abbr":"RI","panel_rows":33,"coverage":0.969697},{"state_abbr":"UT","panel_rows":45,"coverage":0.911111},{"state_abbr":"VT","panel_rows":45,"coverage":0.933333},{"state_abbr":"WA","panel_rows":51,"coverage":0.941176},{"state_abbr":"WY","panel_rows":27,"coverage":0.925926}],"rucc_band_coverage":[{"rucc_band":"1-3","panel_rows":252,"coverage":0.892857},{"rucc_band":"4-6","panel_rows":339,"coverage":0.902655},{"rucc_band":"7-9","panel_rows":324,"coverage":0.907407}],"decile_calibration":[{"decile":1,"panel_rows":92,"prediction_mean":-0.695353,"observation_mean":-0.622467,"signed_gap":-0.072886},{"decile":2,"panel_rows":91,"prediction_mean":-0.491273,"observation_mean":-0.450495,"signed_gap":-0.040779},{"decile":3,"panel_rows":92,"prediction_mean":-0.353568,"observation_mean":-0.451717,"signed_gap":0.09815},{"decile":4,"panel_rows":91,"prediction_mean":-0.255085,"observation_mean":-0.317692,"signed_gap":0.062607},{"decile":5,"panel_rows":92,"prediction_mean":-0.176355,"observation_mean":-0.185652,"signed_gap":0.009297},{"decile":6,"panel_rows":91,"prediction_mean":-0.0995,"observation_mean":0.076615,"signed_gap":-0.176115},{"decile":7,"panel_rows":92,"prediction_mean":-0.024294,"observation_mean":0.080902,"signed_gap":-0.105196},{"decile":8,"panel_rows":91,"prediction_mean":0.069772,"observation_mean":0.020066,"signed_gap":0.049706},{"decile":9,"panel_rows":92,"prediction_mean":0.183851,"observation_mean":0.026228,"signed_gap":0.157622},{"decile":10,"panel_rows":91,"prediction_mean":0.430713,"observation_mean":0.47789,"signed_gap":-0.047177}],"overall_coverage":0.901639,"minimum_state_coverage":0.733333},"trajectory_pca_clustering":{"feature_order":["diabetes_change_end_2022","diabetes_change_end_2023","diabetes_change_end_2024","poverty_change_end_2022","poverty_change_end_2023","poverty_change_end_2024","unemployment_change_end_2022","unemployment_change_end_2023","unemployment_change_end_2024","median_income_change_per_10000_end_2022","median_income_change_per_10000_end_2023","median_income_change_per_10000_end_2024","net_migration_change_end_2022","net_migration_change_end_2023","net_migration_change_end_2024"],"county_count":305,"retained_component_count":5,"first_five_eigenvalues":[1.988493,1.802771,1.659571,1.597471,1.558787],"first_five_explained_shares":[0.132566,0.120185,0.110638,0.106498,0.103919],"first_three_loading_vectors":[[0.09653,-0.080616,0.066784,0.145685,-0.314567,0.170841,0.10112,-0.198384,0.186879,-0.403044,0.466687,-0.270824,-0.366704,0.38305,-0.105205],[-0.370656,0.647539,-0.518513,-0.032675,-0.06199,0.119693,0.209386,-0.100201,-0.083802,0.078918,-0.098911,0.032125,-0.164832,0.207054,-0.085005],[-0.190831,0.137632,-0.04339,0.09751,-0.241433,0.190119,-0.377076,0.563122,-0.359326,-0.070441,0.2989,-0.313113,0.134588,-0.171782,0.102188]],"cluster_grid":[{"cluster_count":2,"inertia":2264.315905,"average_silhouette":0.131368,"cluster_sizes":[161,144]},{"cluster_count":3,"inertia":2022.152553,"average_silhouette":0.127171,"cluster_sizes":[103,94,108]},{"cluster_count":4,"inertia":1796.764031,"average_silhouette":0.140349,"cluster_sizes":[70,65,90,80]},{"cluster_count":5,"inertia":1609.990178,"average_silhouette":0.148939,"cluster_sizes":[59,55,65,70,56]},{"cluster_count":6,"inertia":1506.223903,"average_silhouette":0.147123,"cluster_sizes":[57,41,68,58,39,42]}],"selected_cluster_count":5,"delete_state_stability":[{"deleted_state":"AK","retained_counties":288,"adjusted_rand_index":0.379786},{"deleted_state":"AZ","retained_counties":288,"adjusted_rand_index":0.785335},{"deleted_state":"CA","retained_counties":292,"adjusted_rand_index":0.860802},{"deleted_state":"CO","retained_counties":291,"adjusted_rand_index":0.744481},{"deleted_state":"CT","retained_counties":296,"adjusted_rand_index":0.298847},{"deleted_state":"HI","retained_counties":290,"adjusted_rand_index":0.824332},{"deleted_state":"ID","retained_counties":292,"adjusted_rand_index":0.362808},{"deleted_state":"MA","retained_counties":287,"adjusted_rand_index":0.353371},{"deleted_state":"ME","retained_counties":291,"adjusted_rand_index":0.838708},{"deleted_state":"MT","retained_counties":290,"adjusted_rand_index":0.364335},{"deleted_state":"NH","retained_counties":292,"adjusted_rand_index":0.891952},{"deleted_state":"NJ","retained_counties":290,"adjusted_rand_index":0.385448},{"deleted_state":"NM","retained_counties":292,"adjusted_rand_index":0.749489},{"deleted_state":"NV","retained_counties":296,"adjusted_rand_index":0.822425},{"deleted_state":"NY","retained_counties":292,"adjusted_rand_index":0.876982},{"deleted_state":"OR","retained_counties":293,"adjusted_rand_index":0.828215},{"deleted_state":"PA","retained_counties":287,"adjusted_rand_index":0.726149},{"deleted_state":"RI","retained_counties":294,"adjusted_rand_index":0.478181},{"deleted_state":"UT","retained_counties":290,"adjusted_rand_index":0.535726},{"deleted_state":"VT","retained_counties":290,"adjusted_rand_index":0.412853},{"deleted_state":"WA","retained_counties":288,"adjusted_rand_index":0.393984},{"deleted_state":"WY","retained_counties":296,"adjusted_rand_index":0.303085}],"median_delete_state_ari":0.630937,"minimum_delete_state_ari":0.298847},"source_group_perturbation":{"reference_full_oof_rmse":0.83156,"ordered_source_groups":["lagged_outcome_context","lagged_poverty_context","rurality_context","interval_context","poverty_dynamics","companion_economic_dynamics"],"group_deletion_diagnostics":[{"source_group":"lagged_outcome_context","removed_terms":["lagged_diabetes"],"outer_fold_rmses":[0.842144,0.740649,0.915338,0.928759,0.999517],"pooled_rmse":0.890951,"rmse_deterioration":0.059391,"worse_fold_count":5,"deterioration_rank":1},{"source_group":"lagged_poverty_context","removed_terms":["lagged_poverty"],"outer_fold_rmses":[0.822303,0.723833,0.904694,0.914899,0.960857],"pooled_rmse":0.871067,"rmse_deterioration":0.039506,"worse_fold_count":4,"deterioration_rank":2},{"source_group":"rurality_context","removed_terms":["rucc_2","rucc_3","rucc_4","rucc_5","rucc_6","rucc_7","rucc_8","rucc_9"],"outer_fold_rmses":[0.7929,0.724043,0.843469,0.882968,0.895921],"pooled_rmse":0.83156,"rmse_deterioration":0.0,"worse_fold_count":0,"deterioration_rank":4},{"source_group":"interval_context","removed_terms":["end_2023","end_2024"],"outer_fold_rmses":[0.7929,0.724043,0.843469,0.881708,0.894688],"pooled_rmse":0.831027,"rmse_deterioration":-0.000533,"worse_fold_count":1,"deterioration_rank":5},{"source_group":"poverty_dynamics","removed_terms":["poverty_change"],"outer_fold_rmses":[0.79435,0.725257,0.844774,0.882557,0.897264],"pooled_rmse":0.832499,"rmse_deterioration":0.000939,"worse_fold_count":4,"deterioration_rank":3},{"source_group":"companion_economic_dynamics","removed_terms":["unemployment_change","median_income_change_per_10000","net_migration_change"],"outer_fold_rmses":[0.792601,0.723704,0.838722,0.881521,0.894097],"pooled_rmse":0.829712,"rmse_deterioration":-0.001848,"worse_fold_count":0,"deterioration_rank":6}]},"decision":"RETAIN_LAGGED_DIABETES"}')
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        print(json.dumps(zero_result(f"invalid or missing JSON submission: {type(exc).__name__}"), separators=(",", ":")))
        return 0
    if not isinstance(candidate, dict) or not candidate:
        print(json.dumps(zero_result("submission root must be a nonempty JSON object"), separators=(",", ":")))
        return 0

    scores = score_points(candidate, gold)
    rubric = []
    total_score = 0.0
    for (point_id, goal, weight, _), (fraction, subchecks) in zip(POINTS, scores):
        bounded = max(0.0, min(1.0, fraction))
        subcheck_items = list(subchecks.values()) if isinstance(subchecks, dict) else list(subchecks)
        point_pass = bool(subcheck_items) and all(item.get("passed") is True for item in subcheck_items)
        earned = weight / TOTAL_WEIGHT if point_pass else 0.0
        total_score += earned
        rubric.append({
            "point_id": point_id,
            "goal": goal,
            "raw_weight": weight,
            "normalized_max": round(weight / TOTAL_WEIGHT, 12),
            "point_pass": point_pass,
            "diagnostic_fraction": round(bounded, 12),
            "earned_fraction": 1.0 if point_pass else 0.0,
            "earned_normalized_score": round(earned, 12),
            "subchecks": subchecks,
        })

    required_root_keys = set(gold)
    allowed_root_keys = set(gold)
    root_valid = required_root_keys.issubset(candidate) and set(candidate).issubset(allowed_root_keys)
    if not root_valid:
        total_score = min(total_score, 0.999999999999)
    result = {
        "score": round(total_score, 12),
        "score_possible": 1.0,
        "rubric": rubric,
        "diagnostics": [] if root_valid else ["top-level analytical keys differ from the required template"],
    }
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
