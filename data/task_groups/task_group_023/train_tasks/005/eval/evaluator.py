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
        gold = load_json(Path(__file__).resolve().parents[1] / "output" / "answer.json")
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

    required_root_keys = set(gold) - {"protocol_registry_record"}
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
