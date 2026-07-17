#!/usr/bin/env python3
"""Deterministic whole-point evaluator for test_003.

The eight scoring points use raw weights [2, 3, 2, 3, 2, 2, 3, 2].
Each point reports its normalized maximum, binary pass result, normalized award,
and its business-result diagnostics. Candidate strings are trimmed and normalized
to the documented identifier casing. Set outputs are deduplicated. Numeric
statistics use a half-unit tolerance at the declared four-decimal precision.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable, Iterable


POINTS = [
    ("SP001", "Country-label reconciliation", 2),
    ("SP002", "Revision precedence and unresolved scale anomalies", 3),
    ("SP003", "Eligible PCA matrix and missingness audit", 2),
    ("SP004", "Burden PCA retention, variance, and loading order", 3),
    ("SP005", "Four-cluster burden size profile", 2),
    ("SP006", "Highest-burden country set", 2),
    ("SP007", "Region-controlled longevity panel interaction", 3),
    ("SP008", "Longevity-stall conclusion", 2),
]
TOTAL_RAW_WEIGHT = sum(weight for _, _, weight in POINTS)


def get_path(value: Any, *path: str) -> Any:
    current = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def normalized_string(value: Any, upper: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    result = value.strip()
    return result.upper() if upper else result.lower()


def integer_equal(value: Any, expected: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == expected


def number_equal(value: Any, expected: float, decimals: int = 4) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    number = float(value)
    if not math.isfinite(number):
        return False
    tolerance = 0.5 * (10 ** (-decimals)) + 1e-12
    return abs(number - expected) <= tolerance


def exact_detail(received: Any, expected: Any, earned: bool) -> dict[str, Any]:
    return {"earned": earned, "expected": expected, "received": received}


def normalize_string_set(value: Any, upper: bool = True) -> set[str]:
    if not isinstance(value, list):
        return set()
    normalized: set[str] = set()
    for item in value:
        text = normalized_string(item, upper=upper)
        if text:
            normalized.add(text)
    return normalized


def set_f1(predicted: set[Any], expected: set[Any]) -> tuple[float, dict[str, Any]]:
    correct = len(predicted & expected)
    precision = correct / len(predicted) if predicted else 0.0
    recall = correct / len(expected) if expected else 1.0
    fraction = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    detail = {
        "earned_fraction": round(fraction, 12),
        "predicted_count": len(predicted),
        "expected_count": len(expected),
        "correct_count": correct,
        "precision": round(precision, 12),
        "recall": round(recall, 12),
    }
    return fraction, detail


def event_set(
    value: Any,
    include_status: bool,
) -> set[tuple[Any, ...]]:
    if not isinstance(value, list):
        return set()
    result: set[tuple[Any, ...]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        iso3 = normalized_string(item.get("iso3"), upper=True)
        indicator = normalized_string(item.get("indicator_id"), upper=False)
        year = item.get("year")
        if not iso3 or not indicator or not isinstance(year, int) or isinstance(year, bool):
            continue
        if include_status:
            status = normalized_string(item.get("notice_status"), upper=True)
            if not status:
                continue
            result.add((iso3, indicator, year, status))
        else:
            result.add((iso3, indicator, year))
    return result


def lcs_length(left: list[str], right: list[str]) -> int:
    previous = [0] * (len(right) + 1)
    for left_item in left:
        current = [0]
        for index, right_item in enumerate(right, start=1):
            if left_item == right_item:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def ordered_list_fraction(value: Any, expected: list[str]) -> tuple[float, dict[str, Any]]:
    predicted = []
    if isinstance(value, list):
        for item in value:
            normalized = normalized_string(item, upper=False)
            if normalized:
                predicted.append(normalized)
    common = lcs_length(predicted, expected)
    denominator = len(predicted) + len(expected)
    fraction = (2 * common / denominator) if denominator else 1.0
    return fraction, {
        "earned_fraction": round(fraction, 12),
        "longest_common_subsequence": common,
        "predicted_length": len(predicted),
        "expected_length": len(expected),
        "received": predicted,
        "expected": expected,
    }


def point_result(
    point_id: str,
    title: str,
    raw_weight: int,
    fraction: float,
    subchecks: dict[str, Any],
) -> dict[str, Any]:
    bounded = min(1.0, max(0.0, float(fraction)))
    normalized_max = raw_weight / TOTAL_RAW_WEIGHT
    return {
        "id": point_id,
        "title": title,
        "raw_weight": raw_weight,
        "normalized_max": round(normalized_max, 12),
        "earned_fraction": round(bounded, 12),
        "earned_normalized": round(normalized_max * bounded, 12),
        "subchecks": subchecks,
    }


def score_prediction(prediction: Any, diagnostics: list[str]) -> dict[str, Any]:
    if not isinstance(prediction, dict):
        diagnostics.append("The prediction root must be a JSON object.")
        prediction = {}

    results: list[dict[str, Any]] = []

    # SP001: three independently checkable reconciliation counts.
    recon_expected = {
        "requested_label_count": 52,
        "matched_iso3_count": 52,
        "portal_alias_match_count": 14,
    }
    recon_checks: dict[str, Any] = {}
    recon_earned = 0
    for key, expected in recon_expected.items():
        received = get_path(prediction, "reconciliation", key)
        earned = integer_equal(received, expected)
        recon_earned += int(earned)
        recon_checks[key] = exact_detail(received, expected, earned)
    results.append(point_result(*POINTS[0], recon_earned / 3, recon_checks))

    # SP002: correction state, unresolved event state, and the resulting exclusions.
    applied_expected = {
        ("QAA", "adult_mortality", 2018),
        ("QAB", "infant_mortality", 2019),
        ("QAC", "poverty_rate", 2020),
        ("QAE", "unemployment", 2021),
    }
    unresolved_expected = {
        ("QAG", "immunization_gap", 2022, "PENDING"),
        ("QAI", "alcohol_harm", 2023, "PENDING"),
        ("QAJ", "schooling_gap", 2019, "WITHDRAWN"),
    }
    excluded_expected = {"QAG", "QAI", "QAJ"}
    audit = get_path(prediction, "revision_quality_audit")
    audit = audit if isinstance(audit, dict) else {}
    applied_count_ok = integer_equal(audit.get("applied_scale_correction_count"), 4)
    unresolved_count_ok = integer_equal(audit.get("unresolved_scale_anomaly_count"), 3)
    applied_fraction, applied_detail = set_f1(
        event_set(audit.get("applied_scale_corrections"), include_status=False),
        applied_expected,
    )
    unresolved_fraction, unresolved_detail = set_f1(
        event_set(audit.get("unresolved_scale_anomalies"), include_status=True),
        unresolved_expected,
    )
    excluded_fraction, excluded_detail = set_f1(
        normalize_string_set(audit.get("excluded_anomaly_iso3"), upper=True),
        excluded_expected,
    )
    revision_fraction = (
        0.15 * int(applied_count_ok)
        + 0.35 * applied_fraction
        + 0.15 * int(unresolved_count_ok)
        + 0.20 * unresolved_fraction
        + 0.15 * excluded_fraction
    )
    revision_checks = {
        "applied_scale_correction_count": exact_detail(
            audit.get("applied_scale_correction_count"), 4, applied_count_ok
        ),
        "applied_scale_correction_set_f1": applied_detail,
        "unresolved_scale_anomaly_count": exact_detail(
            audit.get("unresolved_scale_anomaly_count"), 3, unresolved_count_ok
        ),
        "unresolved_scale_anomaly_set_f1": unresolved_detail,
        "excluded_anomaly_iso3_set_f1": excluded_detail,
    }
    results.append(point_result(*POINTS[1], revision_fraction, revision_checks))

    # SP003: matrix eligibility and pre-imputation missingness.
    matrix_expected = {
        "eligible_country_count": 49,
        "raw_missing_cell_count": 47,
        "countries_with_missing_indicator_count": 30,
        "median_imputed_cell_count": 47,
    }
    matrix_checks: dict[str, Any] = {}
    matrix_earned = 0
    for key, expected in matrix_expected.items():
        received = get_path(prediction, "matrix_audit", key)
        earned = integer_equal(received, expected)
        matrix_earned += int(earned)
        matrix_checks[key] = exact_detail(received, expected, earned)
    results.append(point_result(*POINTS[2], matrix_earned / 4, matrix_checks))

    # SP004: component retention, explained fraction, and the full absolute-loading order.
    component_received = get_path(prediction, "pca", "retained_component_count")
    variance_received = get_path(prediction, "pca", "pc1_variance_fraction")
    component_ok = integer_equal(component_received, 1)
    variance_ok = number_equal(variance_received, 0.7318)
    loading_expected = [
        "adult_mortality",
        "infant_mortality",
        "poverty_rate",
        "immunization_gap",
        "health_spending_gap",
        "unemployment",
        "schooling_gap",
        "hiv_burden",
        "alcohol_harm",
    ]
    loading_fraction, loading_detail = ordered_list_fraction(
        get_path(prediction, "pca", "pc1_absolute_loading_order"), loading_expected
    )
    pca_fraction = 0.25 * int(component_ok) + 0.25 * int(variance_ok) + 0.50 * loading_fraction
    pca_checks = {
        "retained_component_count": exact_detail(component_received, 1, component_ok),
        "pc1_variance_fraction": exact_detail(variance_received, 0.7318, variance_ok),
        "pc1_absolute_loading_order": loading_detail,
    }
    results.append(point_result(*POINTS[3], pca_fraction, pca_checks))

    # SP005: positional partial credit for the four burden-ranked cluster sizes.
    sizes_received = get_path(prediction, "clusters", "sizes_by_ascending_burden")
    expected_sizes = [7, 17, 18, 7]
    received_sizes = sizes_received if isinstance(sizes_received, list) else []
    positional_matches = 0
    per_position = []
    for index, expected in enumerate(expected_sizes):
        received = received_sizes[index] if index < len(received_sizes) else None
        earned = integer_equal(received, expected)
        positional_matches += int(earned)
        per_position.append(
            {"burden_rank": index + 1, **exact_detail(received, expected, earned)}
        )
    sizes_fraction = positional_matches / max(len(expected_sizes), len(received_sizes), 1)
    size_checks = {
        "position_checks": per_position,
        "predicted_length": len(received_sizes),
        "expected_length": len(expected_sizes),
    }
    results.append(point_result(*POINTS[4], sizes_fraction, size_checks))

    # SP006: set F1 rewards correct inclusions while penalizing extras and omissions.
    high_expected = {"QAQ", "QBA", "QBD", "QBE", "QBM", "QBQ", "QBU"}
    high_fraction, high_detail = set_f1(
        normalize_string_set(get_path(prediction, "clusters", "high_burden_iso3"), upper=True),
        high_expected,
    )
    results.append(
        point_result(*POINTS[5], high_fraction, {"high_burden_iso3_set_f1": high_detail})
    )

    # SP007: panel coverage, two slopes, the target interaction, and its p-value.
    panel_specs: list[tuple[str, Any, Callable[[Any, Any], bool], float]] = [
        ("country_count", 49, integer_equal, 0.10),
        ("observation_count", 268, integer_equal, 0.10),
        ("other_countries_annual_slope", 0.1982, number_equal, 0.15),
        ("high_burden_by_year_interaction", -0.1649, number_equal, 0.30),
        ("interaction_p_value", 0.7479, number_equal, 0.20),
        ("high_burden_annual_slope", 0.0332, number_equal, 0.15),
    ]
    panel_fraction = 0.0
    panel_checks: dict[str, Any] = {}
    for key, expected, checker, share in panel_specs:
        received = get_path(prediction, "panel_model", key)
        earned = checker(received, expected)
        panel_fraction += share * int(earned)
        panel_checks[key] = {
            **exact_detail(received, expected, earned),
            "fraction_share": share,
        }
    results.append(point_result(*POINTS[6], panel_fraction, panel_checks))

    # SP008: controlled business conclusion.
    conclusion_received = normalized_string(get_path(prediction, "conclusion"), upper=True)
    conclusion_ok = conclusion_received == "STALL_NOT_SUPPORTED"
    conclusion_checks = {
        "conclusion": exact_detail(
            conclusion_received, "STALL_NOT_SUPPORTED", conclusion_ok
        )
    }
    results.append(point_result(*POINTS[7], int(conclusion_ok), conclusion_checks))

    binary_passes = [
        recon_earned == 3,
        abs(revision_fraction - 1.0) < 1e-12,
        matrix_earned == 4,
        component_ok,
        received_sizes == expected_sizes,
        abs(high_fraction - 1.0) < 1e-12,
        abs(panel_fraction - 1.0) < 1e-12,
        conclusion_ok,
    ]
    for result, passed in zip(results, binary_passes):
        result["point_pass"] = bool(passed)
        result["diagnostic_fraction"] = result["earned_fraction"]
        result["earned_fraction"] = 1.0 if passed else 0.0
        result["earned_normalized"] = result["normalized_max"] if passed else 0.0
    score = sum(item["earned_normalized"] for item in results)
    if abs(score - 1.0) < 1e-9:
        score = 1.0
    return {
        "score": round(score, 12),
        "total_raw_weight": TOTAL_RAW_WEIGHT,
        "points": results,
        "diagnostics": diagnostics,
    }


def load_prediction(path_text: str) -> tuple[Any, list[str]]:
    diagnostics: list[str] = []
    try:
        with Path(path_text).open("r", encoding="utf-8") as handle:
            return json.load(handle), diagnostics
    except Exception as exc:  # Parse and I/O failures are scored as zero with diagnostics.
        diagnostics.append(f"Could not parse prediction JSON: {exc}")
        return {}, diagnostics


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        result = score_prediction({}, ["usage: evaluator.py <prediction.json>"])
    else:
        prediction, diagnostics = load_prediction(argv[1])
        result = score_prediction(prediction, diagnostics)
    print(json.dumps(result, ensure_ascii=True, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
