#!/usr/bin/env python3
"""Deterministic eight-point evaluator for train_003."""

import json
import math
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


WEIGHTS = [2, 3, 3, 2, 2, 2, 3, 2]
TOTAL_WEIGHT = sum(WEIGHTS)
PRECISION = Decimal("0.0001")


def at_path(value, path, default=None):
    current = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def exact(candidate, expected):
    return 1.0 if candidate == expected else 0.0


def integer(candidate, expected):
    if isinstance(candidate, bool):
        return 0.0
    try:
        return 1.0 if int(candidate) == int(expected) and float(candidate) == int(candidate) else 0.0
    except (TypeError, ValueError, OverflowError):
        return 0.0


def number4(candidate, expected):
    if isinstance(candidate, bool):
        return 0.0
    try:
        value = Decimal(str(candidate))
        target = Decimal(str(expected))
        if not value.is_finite():
            return 0.0
        return 1.0 if value.quantize(PRECISION, rounding=ROUND_HALF_UP) == target else 0.0
    except (InvalidOperation, TypeError, ValueError):
        return 0.0


def normalized_strings(value, uppercase=False):
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if uppercase:
            cleaned = cleaned.upper()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def set_f1(candidate, expected, uppercase=False):
    predicted = set(normalized_strings(candidate, uppercase=uppercase))
    gold = set(normalized_strings(expected, uppercase=uppercase))
    if not predicted and not gold:
        return 1.0
    if not predicted or not gold:
        return 0.0
    intersection = len(predicted & gold)
    precision = intersection / len(predicted)
    recall = intersection / len(gold)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def stable_sorted(value, uppercase=False):
    normalized = normalized_strings(value, uppercase=uppercase)
    if not isinstance(value, list) or len(normalized) != len(value):
        return 0.0
    return 1.0 if normalized == sorted(normalized) else 0.0


def weighted_fraction(subchecks):
    earned = sum(item["share"] * item["result"] for item in subchecks)
    return max(0.0, min(1.0, earned))


def point(point_id, goal, weight, subchecks):
    fraction = weighted_fraction(subchecks)
    maximum = weight / TOTAL_WEIGHT
    return {
        "point_id": point_id,
        "goal": goal,
        "weight": weight,
        "max_score": round(maximum, 10),
        "earned_fraction": round(fraction, 10),
        "earned_score": round(maximum * fraction, 10),
        "subchecks": {
            item["name"]: {"share": item["share"], "result": round(item["result"], 10)}
            for item in subchecks
        },
    }


def sc(name, share, result):
    return {"name": name, "share": share, "result": float(result)}


def evaluate(candidate, gold):
    c_recon = at_path(candidate, ["reconciliation"], {})
    g_recon = gold["reconciliation"]
    p1 = point(
        "SP001",
        "Reconcile all requested country labels to stable ISO3 identifiers.",
        WEIGHTS[0],
        [
            sc("requested_label_count", 0.15, integer(c_recon.get("requested_label_count"), g_recon["requested_label_count"])),
            sc("resolved_label_count", 0.20, integer(c_recon.get("resolved_label_count"), g_recon["resolved_label_count"])),
            sc("alias_resolution_count", 0.20, integer(c_recon.get("alias_resolution_count"), g_recon["alias_resolution_count"])),
            sc("resolved_iso3_f1", 0.35, set_f1(c_recon.get("resolved_iso3"), g_recon["resolved_iso3"], uppercase=True)),
            sc("resolved_iso3_order", 0.10, stable_sorted(c_recon.get("resolved_iso3"), uppercase=True)),
        ],
    )

    c_quality = at_path(candidate, ["quality_audit"], {})
    g_quality = gold["quality_audit"]
    p2 = point(
        "SP002",
        "Apply revision status correctly and identify unresolved scale breaks.",
        WEIGHTS[1],
        [
            sc("applied_revision_f1", 0.30, set_f1(c_quality.get("applied_revision_event_ids"), g_quality["applied_revision_event_ids"])),
            sc("applied_revision_order", 0.05, stable_sorted(c_quality.get("applied_revision_event_ids"))),
            sc("nonapplied_revision_f1", 0.20, set_f1(c_quality.get("nonapplied_revision_event_ids"), g_quality["nonapplied_revision_event_ids"])),
            sc("nonapplied_revision_order", 0.05, stable_sorted(c_quality.get("nonapplied_revision_event_ids"))),
            sc("anomaly_key_f1", 0.35, set_f1(c_quality.get("anomaly_observation_keys"), g_quality["anomaly_observation_keys"])),
            sc("anomaly_key_order", 0.05, stable_sorted(c_quality.get("anomaly_observation_keys"))),
        ],
    )

    p3 = point(
        "SP003",
        "Construct the usable 2022 matrix and account for missing and imputed cells.",
        WEIGHTS[2],
        [
            sc("raw_missing_2022_cells", 0.20, integer(c_quality.get("raw_missing_2022_cells"), g_quality["raw_missing_2022_cells"])),
            sc("anomaly_2022_cells", 0.15, integer(c_quality.get("anomaly_2022_cells"), g_quality["anomaly_2022_cells"])),
            sc("imputed_2022_cells", 0.25, integer(c_quality.get("imputed_2022_cells"), g_quality["imputed_2022_cells"])),
            sc("usable_country_count", 0.20, integer(c_quality.get("usable_country_count"), g_quality["usable_country_count"])),
            sc("usable_indicator_count", 0.20, integer(c_quality.get("usable_indicator_count"), g_quality["usable_indicator_count"])),
        ],
    )

    c_pca = at_path(candidate, ["pca"], {})
    g_pca = gold["pca"]
    p4 = point(
        "SP004",
        "Retain the correct PCA dimension and PC1 explained variance.",
        WEIGHTS[3],
        [
            sc("retained_component_count", 0.50, integer(c_pca.get("retained_component_count"), g_pca["retained_component_count"])),
            sc("pc1_variance_fraction", 0.50, number4(c_pca.get("pc1_variance_fraction"), g_pca["pc1_variance_fraction"])),
        ],
    )

    c_loadings = c_pca.get("top_absolute_loadings", [])
    g_loadings = g_pca["top_absolute_loadings"]
    candidate_ids = [item.get("indicator_id") for item in c_loadings if isinstance(item, dict)] if isinstance(c_loadings, list) else []
    gold_ids = [item["indicator_id"] for item in g_loadings]
    positional = sum(1 for index, item in enumerate(gold_ids) if index < len(candidate_ids) and candidate_ids[index] == item) / len(gold_ids)
    candidate_loading_map = {
        item.get("indicator_id"): item.get("loading")
        for item in c_loadings
        if isinstance(item, dict) and isinstance(item.get("indicator_id"), str)
    } if isinstance(c_loadings, list) else {}
    numeric_loading = sum(number4(candidate_loading_map.get(item["indicator_id"]), item["loading"]) for item in g_loadings) / len(g_loadings)
    p5 = point(
        "SP005",
        "Report the ordered strongest absolute PC1 loadings and their signed values.",
        WEIGHTS[4],
        [
            sc("ordered_indicator_positions", 0.45, positional),
            sc("exact_ordered_indicator_list", 0.15, exact(candidate_ids, gold_ids)),
            sc("loading_values_by_indicator", 0.40, numeric_loading),
        ],
    )

    c_cluster = at_path(candidate, ["clusters"], {})
    g_cluster = gold["clusters"]
    silhouette_fraction = sum(number4(at_path(c_cluster, ["silhouette_by_k", key]), value) for key, value in g_cluster["silhouette_by_k"].items()) / 4
    size_fraction = sum(integer(at_path(c_cluster, ["sizes", key]), value) for key, value in g_cluster["sizes"].items()) / 3
    p6 = point(
        "SP006",
        "Reproduce the candidate-k diagnostic and the requested three-cluster burden segmentation.",
        WEIGHTS[5],
        [
            sc("requested_k", 0.05, integer(c_cluster.get("requested_k"), g_cluster["requested_k"])),
            sc("silhouette_selected_k", 0.20, integer(c_cluster.get("silhouette_selected_k"), g_cluster["silhouette_selected_k"])),
            sc("silhouette_by_k", 0.20, silhouette_fraction),
            sc("cluster_sizes", 0.25, size_fraction),
            sc("high_burden_iso3_f1", 0.25, set_f1(c_cluster.get("high_burden_iso3"), g_cluster["high_burden_iso3"], uppercase=True)),
            sc("high_burden_iso3_order", 0.05, stable_sorted(c_cluster.get("high_burden_iso3"), uppercase=True)),
        ],
    )

    c_panel = at_path(candidate, ["panel_model"], {})
    g_panel = gold["panel_model"]
    p7 = point(
        "SP007",
        "Estimate the region-adjusted life-expectancy association with PC1 burden.",
        WEIGHTS[6],
        [
            sc("n_observations", 0.15, integer(c_panel.get("n_observations"), g_panel["n_observations"])),
            sc("pc1_coefficient", 0.30, number4(c_panel.get("pc1_coefficient"), g_panel["pc1_coefficient"])),
            sc("pc1_standard_error", 0.20, number4(c_panel.get("pc1_standard_error"), g_panel["pc1_standard_error"])),
            sc("pc1_p_value", 0.10, number4(c_panel.get("pc1_p_value"), g_panel["pc1_p_value"])),
            sc("r_squared", 0.15, number4(c_panel.get("r_squared"), g_panel["r_squared"])),
            sc("region_fixed_effects", 0.10, exact(c_panel.get("region_fixed_effects"), g_panel["region_fixed_effects"])),
        ],
    )

    p8 = point(
        "SP008",
        "Issue the controlled portfolio advisory supported by the panel result.",
        WEIGHTS[7],
        [sc("advisory", 1.0, exact(candidate.get("advisory"), gold["advisory"]))],
    )
    points = [p1, p2, p3, p4, p5, p6, p7, p8]
    for item in points:
        point_pass = abs(item["earned_fraction"] - 1.0) < 1e-12
        item["diagnostic_fraction"] = item["earned_fraction"]
        item["point_pass"] = point_pass
        item["earned_fraction"] = 1.0 if point_pass else 0.0
        item["earned_score"] = item["max_score"] if point_pass else 0.0
    score = sum(item["earned_score"] for item in points)
    if abs(score - 1.0) < 1e-9:
        score = 1.0
    return {
        "score": round(score, 10),
        "total_raw_weight": TOTAL_WEIGHT,
        "rubric": points,
    }


def zero_result(error):
    goals = [
        "Reconcile all requested country labels to stable ISO3 identifiers.",
        "Apply revision status correctly and identify unresolved scale breaks.",
        "Construct the usable 2022 matrix and account for missing and imputed cells.",
        "Retain the correct PCA dimension and PC1 explained variance.",
        "Report the ordered strongest absolute PC1 loadings and their signed values.",
        "Reproduce the candidate-k diagnostic and the requested three-cluster burden segmentation.",
        "Estimate the region-adjusted life-expectancy association with PC1 burden.",
        "Issue the controlled portfolio advisory supported by the panel result.",
    ]
    return {
        "score": 0.0,
        "total_raw_weight": TOTAL_WEIGHT,
        "error": error,
        "rubric": [
            {
                "point_id": f"SP{index:03d}",
                "goal": goal,
                "weight": weight,
                "max_score": round(weight / TOTAL_WEIGHT, 10),
                "earned_fraction": 0.0,
                "earned_score": 0.0,
                "subchecks": {},
            }
            for index, (goal, weight) in enumerate(zip(goals, WEIGHTS), start=1)
        ],
    }


def main():
    if len(sys.argv) != 2:
        print(json.dumps(zero_result("usage: evaluator.py <prediction.json>")))
        return
    try:
        candidate = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        if not isinstance(candidate, dict):
            raise ValueError("prediction must be a JSON object")
        gold_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        print(json.dumps(evaluate(candidate, gold), indent=2, allow_nan=False))
    except Exception as exc:
        print(json.dumps(zero_result(f"prediction parse/evaluation error: {exc}"), indent=2))


if __name__ == "__main__":
    main()
