#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "id": "SP001",
        "weight": 2,
        "goal": "Correct current-data override and stale-packet reconciliation.",
        "field": "source_reconciliation",
        "kind": "source_reconciliation",
    },
    {
        "id": "SP002",
        "weight": 3,
        "goal": "Correct ranked risk exceptions with materiality evidence.",
        "field": "ranked_exceptions",
        "kind": "ranked_exceptions",
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Correct fixed-income current credit metrics.",
        "field": "credit_metrics",
        "kind": "current_credit_metrics",
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct post-rotation credit metrics and watchlist cleanup.",
        "field": "credit_metrics",
        "kind": "post_trade_credit_metrics",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct correlation concentration pair, threshold breach, and diversifier evidence.",
        "field": "correlation_concentration",
        "kind": "correlation",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Correct rebalance action package.",
        "field": "rebalance_package",
        "kind": "rebalance_package",
    },
    {
        "id": "SP007",
        "weight": 2,
        "goal": "Correct pass/fail constraint flags.",
        "field": "constraint_flags",
        "kind": "object",
    },
    {
        "id": "SP008",
        "weight": 2,
        "goal": "Correct combined credit and correlation board decision.",
        "field": "board_decision",
        "kind": "object",
    },
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def round_number(value, digits):
    if isinstance(value, bool):
        return value
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def normalize_source_reconciliation(value):
    if not isinstance(value, dict):
        return value
    overrides = value.get("quantity_overrides")
    if isinstance(overrides, list):
        rows = []
        for item in overrides:
            if not isinstance(item, dict):
                rows.append(item)
                continue
            rows.append(
                {
                    "instrument_id": item.get("instrument_id"),
                    "local_quantity_usd_m": round_number(item.get("local_quantity_usd_m"), 1),
                    "current_quantity_usd_m": round_number(item.get("current_quantity_usd_m"), 1),
                    "override_applied": item.get("override_applied"),
                }
            )
        overrides = sorted(rows, key=lambda row: str(row.get("instrument_id")) if isinstance(row, dict) else "")
    return {
        "authoritative_source": value.get("authoritative_source"),
        "local_packet_status": value.get("local_packet_status"),
        "quantity_overrides": overrides,
        "correlation_window_override": value.get("correlation_window_override"),
    }


def normalize_ranked_exceptions(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if not isinstance(item, dict):
            rows.append(item)
            continue
        rows.append(
            {
                "rank": item.get("rank"),
                "exception_code": item.get("exception_code"),
                "primary_driver": item.get("primary_driver"),
                "materiality": item.get("materiality"),
                "severity_metric": item.get("severity_metric"),
                "severity_value": round_number(item.get("severity_value"), 3),
            }
        )
    return sorted(rows, key=lambda row: row.get("rank", 999) if isinstance(row, dict) else 999)


def normalize_current_credit_metrics(value):
    if not isinstance(value, dict):
        return value
    return {
        "current_hy_allocation_pct": round_number(value.get("current_hy_allocation_pct"), 2),
        "current_duration_years": round_number(value.get("current_duration_years"), 2),
        "current_watchlist_exposure_usd_m": round_number(value.get("current_watchlist_exposure_usd_m"), 1),
    }


def normalize_post_trade_credit_metrics(value):
    if not isinstance(value, dict):
        return value
    return {
        "post_trade_hy_allocation_pct": round_number(value.get("post_trade_hy_allocation_pct"), 2),
        "post_trade_duration_years": round_number(value.get("post_trade_duration_years"), 2),
        "hy_reduction_pct_points": round_number(value.get("hy_reduction_pct_points"), 2),
        "post_trade_watchlist_exposure_usd_m": round_number(value.get("post_trade_watchlist_exposure_usd_m"), 1),
    }


def normalize_correlation(value):
    if not isinstance(value, dict):
        return value
    pair = value.get("pair")
    if isinstance(pair, list):
        pair = sorted(str(item) for item in pair)
    return {
        "pair_role": value.get("pair_role"),
        "pair": pair,
        "correlation": round_number(value.get("correlation"), 3),
        "high_threshold_breached": value.get("high_threshold_breached"),
        "threshold_excess": round_number(value.get("threshold_excess"), 3),
        "paired_sleeve_exposure_usd_m": round_number(value.get("paired_sleeve_exposure_usd_m"), 1),
        "diversifier_index_id": value.get("diversifier_index_id"),
        "diversifier_pair_correlation": round_number(value.get("diversifier_pair_correlation"), 3),
    }


def normalize_trade_rows(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if not isinstance(item, dict):
            rows.append(item)
            continue
        rows.append(
            {
                "action": item.get("action"),
                "instrument_id": item.get("instrument_id"),
                "quantity_usd_m": round_number(item.get("quantity_usd_m"), 1),
            }
        )
    action_rank = {"SELL": 0, "BUY": 1}
    return sorted(rows, key=lambda row: (action_rank.get(row.get("action"), 9), str(row.get("instrument_id"))))


def normalize_equity_actions(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if not isinstance(item, dict):
            rows.append(item)
            continue
        rows.append(
            {
                "action": item.get("action"),
                "index_id": item.get("index_id"),
                "quantity_usd_m": round_number(item.get("quantity_usd_m"), 1),
            }
        )
    action_rank = {"trim": 0, "add": 1, "hold": 2, "hedge": 3, "monitor": 4, "rotate": 5}
    return sorted(rows, key=lambda row: (action_rank.get(row.get("action"), 9), str(row.get("index_id"))))


def normalize_rebalance_package(value):
    if not isinstance(value, dict):
        return value
    return {
        "fixed_income_trades": normalize_trade_rows(value.get("fixed_income_trades")),
        "equity_actions": normalize_equity_actions(value.get("equity_actions")),
        "rebalance_trigger": value.get("rebalance_trigger"),
    }


def normalize_object(value):
    if isinstance(value, dict):
        return {key: normalize_object(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return sorted((normalize_object(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, float):
        return round(value, 10)
    return value


def normalize_field(kind, value):
    if kind == "source_reconciliation":
        return normalize_source_reconciliation(value)
    if kind == "ranked_exceptions":
        return normalize_ranked_exceptions(value)
    if kind == "current_credit_metrics":
        return normalize_current_credit_metrics(value)
    if kind == "post_trade_credit_metrics":
        return normalize_post_trade_credit_metrics(value)
    if kind == "correlation":
        return normalize_correlation(value)
    if kind == "rebalance_package":
        return normalize_rebalance_package(value)
    if kind == "object":
        return normalize_object(value)
    return value


def main():
    max_score = sum(point["weight"] for point in POINTS)
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": max_score,
                    "normalized_score": 0.0,
                    "error": "Usage: python eval.py <prediction_json_path>",
                    "details": [],
                },
                indent=2,
            )
        )
        return 2

    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        expected = load_json(answer_path)
        predicted = load_json(sys.argv[1])
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": max_score,
                    "normalized_score": 0.0,
                    "error": str(exc),
                    "details": [],
                },
                indent=2,
            )
        )
        return 1

    score = 0
    details = []
    for point in POINTS:
        expected_value = normalize_field(point["kind"], expected.get(point["field"]))
        predicted_value = normalize_field(point["kind"], predicted.get(point["field"]))
        matched = expected_value == predicted_value
        earned = point["weight"] if matched else 0
        score += earned
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "earned": earned,
                "matched": matched,
                "expected": expected_value,
                "predicted": predicted_value,
            }
        )

    print(
        json.dumps(
            {
                "score": score,
                "max_score": max_score,
                "normalized_score": round(score / max_score, 6),
                "details": details,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
