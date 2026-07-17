#!/usr/bin/env python3
"""Deterministic whole-point evaluator for test task 005."""

from __future__ import annotations

import json
import math
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable


POINTS = [
    ("SP001", "Balanced publication cohort and ordered state census", 1, "cohort_and_state_census"),
    ("SP002", "Delete-state bias-corrected two-step GMM", 3, "delete_state_two_step_gmm"),
    ("SP003", "Full-grid nested state-blocked elastic net", 3, "nested_elastic_net"),
    ("SP004", "Reproducible wild-cluster bootstrap-t audit", 3, "wild_cluster_bootstrap_t"),
    ("SP005", "Grouped conformal coverage and ordered calibration", 3, "grouped_conformal_calibration"),
    ("SP006", "Trajectory PCA, clustering, and delete-state stability", 3, "trajectory_pca_clustering"),
    ("SP007", "Exhaustive source-group perturbation surface", 3, "source_group_perturbation"),
    ("SP008", "Six-gate deployment decision", 2, "decision"),
]
TOTAL_WEIGHT = sum(point[2] for point in POINTS)
MISSING = object()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def numeric_equal(candidate: Any, gold: Any) -> bool:
    if isinstance(candidate, bool) or not isinstance(candidate, (int, float, Decimal)):
        return False
    if isinstance(gold, int) and not isinstance(gold, bool):
        return isinstance(candidate, int) and not isinstance(candidate, bool) and candidate == gold
    try:
        left = Decimal(str(candidate))
        right = Decimal(str(gold))
        if not left.is_finite() or not right.is_finite():
            return False
        quantum = Decimal("0.000001")
        return left.quantize(quantum, rounding=ROUND_HALF_UP) == right.quantize(
            quantum, rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError):
        return False


def semantic_fraction(candidate: Any, gold: Any) -> float:
    """Compare a value while giving sibling fields/rows equal semantic influence.

    Unlike a global leaf count, this recursive mean prevents a long correct table
    from overwhelming a missing sibling component. Missing rows/fields earn zero;
    unexpected rows/fields add zero-valued slots, so malformed shapes are penalized.
    """
    if isinstance(gold, dict):
        if not isinstance(candidate, dict):
            return 0.0
        keys = list(gold)
        slots = len(keys) + len(set(candidate) - set(gold))
        if slots == 0:
            return 1.0
        return sum(semantic_fraction(candidate.get(key, MISSING), gold[key]) for key in keys) / slots
    if isinstance(gold, list):
        if not isinstance(candidate, list):
            return 0.0
        slots = max(len(candidate), len(gold))
        if slots == 0:
            return 1.0
        return sum(
            semantic_fraction(candidate[index] if index < len(candidate) else MISSING, expected)
            for index, expected in enumerate(gold)
        ) / slots
    if isinstance(gold, (int, float)) and not isinstance(gold, bool):
        return float(numeric_equal(candidate, gold))
    if isinstance(gold, bool):
        return float(isinstance(candidate, bool) and candidate is gold)
    return float(type(candidate) is type(gold) and candidate == gold)


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def field_fraction(candidate: Any, gold: Any, field: str) -> float:
    received = as_dict(candidate).get(field, MISSING)
    expected = as_dict(gold).get(field, MISSING)
    if expected is MISSING:
        return 0.0
    return semantic_fraction(received, expected)


def fields_fraction(candidate: Any, gold: Any, fields: Iterable[str]) -> float:
    names = list(fields)
    if not names:
        return 0.0
    return sum(field_fraction(candidate, gold, field) for field in names) / len(names)


def table_fields_fraction(
    candidate: Any,
    gold: Any,
    table_field: str,
    item_fields: Iterable[str],
) -> float:
    """Compare selected semantic columns of an ordered diagnostic table."""
    received = as_dict(candidate).get(table_field, MISSING)
    expected = as_dict(gold).get(table_field, MISSING)
    if not isinstance(received, list) or not isinstance(expected, list):
        return 0.0
    slots = max(len(received), len(expected))
    if slots == 0:
        return 1.0
    names = list(item_fields)
    total = 0.0
    for index, expected_row in enumerate(expected):
        received_row = received[index] if index < len(received) else MISSING
        total += fields_fraction(received_row, expected_row, names)
    return total / slots


def module(name: str, share: float, fraction: float) -> dict[str, Any]:
    bounded = min(1.0, max(0.0, fraction if math.isfinite(fraction) else 0.0))
    return {
        "name": name,
        "share_within_point": share,
        "earned_fraction": round(bounded, 12),
        "passed": math.isclose(bounded, 1.0, abs_tol=1e-12),
    }


def score_modules(modules: list[dict[str, Any]]) -> float:
    return sum(item["share_within_point"] * item["earned_fraction"] for item in modules)


def point_modules(point_id: str, candidate: Any, gold: Any) -> list[dict[str, Any]]:
    """Define a small, auditable set of semantic modules for every rubric point."""
    if point_id == "SP001":
        return [
            module("publication_contract", 0.35, fields_fraction(candidate, gold, [
                "health_release_status", "health_value_type", "revision_selection"
            ])),
            module("balanced_cohort_totals", 0.20, fields_fraction(candidate, gold, [
                "balanced_counties", "panel_rows"
            ])),
            module("ordered_state_census", 0.45, field_fraction(candidate, gold, "state_census")),
        ]
    if point_id == "SP002":
        return [
            module("gmm_design_dimensions", 0.15, fields_fraction(candidate, gold, [
                "instrument_count", "parameter_count", "state_cluster_count"
            ])),
            module("full_two_step_fit", 0.25, fields_fraction(candidate, gold, [
                "full_two_step_coefficients", "full_hansen_j"
            ])),
            module("jackknife_bias_and_shift_summary", 0.25, fields_fraction(candidate, gold, [
                "bias_corrected_coefficients", "maximum_absolute_delete_state_shifts"
            ])),
            module("ordered_delete_state_refits", 0.35, field_fraction(
                candidate, gold, "delete_state_diagnostics"
            )),
        ]
    if point_id == "SP003":
        return [
            module("fold_design_and_coefficient_order", 0.10, fields_fraction(candidate, gold, [
                "outer_fold_count", "inner_fold_count", "coefficient_order"
            ])),
            module("declared_candidate_grid", 0.10, field_fraction(candidate, gold, "candidate_grid")),
            module("outer_fold_membership", 0.15, table_fields_fraction(
                candidate, gold, "outer_fold_diagnostics",
                ["outer_fold", "held_out_states", "held_out_panel_rows"]
            )),
            module("complete_inner_grid_results", 0.25, table_fields_fraction(
                candidate, gold, "outer_fold_diagnostics", ["grid_results"]
            )),
            module("selected_outer_models", 0.25, table_fields_fraction(
                candidate, gold, "outer_fold_diagnostics",
                ["selected_alpha", "selected_l1_ratio", "selected_standardized_coefficients"]
            )),
            module("outer_and_pooled_oof_performance", 0.15,
                0.5 * table_fields_fraction(candidate, gold, "outer_fold_diagnostics", ["outer_rmse"])
                + 0.5 * fields_fraction(candidate, gold, ["oof_rmse", "oof_r_squared"])),
        ]
    if point_id == "SP004":
        return [
            module("randomization_contract", 0.10, fields_fraction(candidate, gold, [
                "prng", "seed", "replicate_count", "state_cluster_count"
            ])),
            module("observed_cluster_robust_statistic", 0.20, fields_fraction(candidate, gold, [
                "observed_coefficient", "observed_cr1_se", "observed_t"
            ])),
            module("tail_count_and_plus_one_inference", 0.20, fields_fraction(candidate, gold, [
                "absolute_tail_exceedance_count", "plus_one_p_value"
            ])),
            module("bootstrap_distribution_quantiles", 0.15, field_fraction(
                candidate, gold, "bootstrap_t_quantiles"
            )),
            module("ordered_prng_and_t_checkpoints", 0.35, field_fraction(
                candidate, gold, "prng_checkpoints"
            )),
        ]
    if point_id == "SP005":
        return [
            module("fold_conformal_intervals", 0.25,
                0.20 * field_fraction(candidate, gold, "nominal_coverage")
                + 0.80 * field_fraction(candidate, gold, "fold_diagnostics")),
            module("ordered_state_coverage", 0.20, field_fraction(candidate, gold, "state_coverage")),
            module("ordered_rucc_band_coverage", 0.15, field_fraction(
                candidate, gold, "rucc_band_coverage"
            )),
            module("ordered_prediction_decile_calibration", 0.20, field_fraction(
                candidate, gold, "decile_calibration"
            )),
            module("overall_and_minimum_coverage", 0.20, fields_fraction(candidate, gold, [
                "overall_coverage", "minimum_state_coverage"
            ])),
        ]
    if point_id == "SP006":
        return [
            module("trajectory_feature_contract", 0.15, field_fraction(candidate, gold, "feature_order")),
            module("pca_cohort_retention_and_spectrum", 0.20, fields_fraction(candidate, gold, [
                "county_count", "retained_component_count", "first_five_eigenvalues",
                "first_five_explained_shares", "first_three_loading_vectors"
            ])),
            module("cluster_grid_and_selection", 0.25, fields_fraction(candidate, gold, [
                "cluster_grid", "selected_cluster_count"
            ])),
            module("ordered_delete_state_stability", 0.25, field_fraction(
                candidate, gold, "delete_state_stability"
            )),
            module("stability_summary", 0.15, fields_fraction(candidate, gold, [
                "median_delete_state_ari", "minimum_delete_state_ari"
            ])),
        ]
    if point_id == "SP007":
        return [
            module("full_model_reference", 0.10, field_fraction(
                candidate, gold, "reference_full_oof_rmse"
            )),
            module("declared_source_group_order", 0.10, field_fraction(
                candidate, gold, "ordered_source_groups"
            )),
            module("group_deletion_contract", 0.15, table_fields_fraction(
                candidate, gold, "group_deletion_diagnostics", ["source_group", "removed_terms"]
            )),
            module("all_outer_fold_perturbation_results", 0.25, table_fields_fraction(
                candidate, gold, "group_deletion_diagnostics", ["outer_fold_rmses"]
            )),
            module("pooled_rmse_and_deterioration", 0.25, table_fields_fraction(
                candidate, gold, "group_deletion_diagnostics", ["pooled_rmse", "rmse_deterioration"]
            )),
            module("worse_fold_counts_and_ranks", 0.15, table_fields_fraction(
                candidate, gold, "group_deletion_diagnostics", ["worse_fold_count", "deterioration_rank"]
            )),
        ]
    return [module("controlled_decision", 1.0, semantic_fraction(candidate, gold))]


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
        print(json.dumps(
            zero_result(f"invalid or missing JSON submission: {type(exc).__name__}"),
            separators=(",", ":"),
        ))
        return 0
    if not isinstance(candidate, dict):
        print(json.dumps(zero_result("submission root must be a JSON object"), separators=(",", ":")))
        return 0

    required_modules = {
        "SP001": {"publication_contract", "balanced_cohort_totals", "ordered_state_census"},
        "SP002": {"full_two_step_fit", "jackknife_bias_and_shift_summary"},
        "SP003": {"fold_design_and_coefficient_order", "declared_candidate_grid"},
        "SP004": {"tail_count_and_plus_one_inference"},
        "SP005": {"overall_and_minimum_coverage"},
        "SP006": {"stability_summary"},
        "SP007": {"group_deletion_contract"},
        "SP008": {"controlled_decision"},
    }
    rubric = []
    total_score = 0.0
    for point_id, goal, weight, key in POINTS:
        received = candidate.get(key, MISSING)
        expected = gold[key]
        modules = point_modules(point_id, received, expected)
        by_name = {item["name"]: item for item in modules}
        required = required_modules[point_id]
        point_pass = all(by_name.get(name, {}).get("passed") is True for name in required)
        earned = weight / TOTAL_WEIGHT if point_pass else 0.0
        total_score += earned
        rubric.append({
            "point_id": point_id,
            "goal": goal,
            "raw_weight": weight,
            "normalized_max": round(weight / TOTAL_WEIGHT, 12),
            "point_pass": point_pass,
            "earned_fraction": 1.0 if point_pass else 0.0,
            "earned_normalized_score": round(earned, 12),
            "required_subchecks": sorted(required),
            "subchecks": {item["name"]: item for item in modules},
        })

    root_exact = set(candidate) == set(gold)
    if not root_exact:
        total_score = min(total_score, 0.999999999999)
    result = {
        "score": round(total_score, 12),
        "score_possible": 1.0,
        "rubric": rubric,
        "diagnostics": [] if root_exact else ["top-level keys differ from the required template"],
    }
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
