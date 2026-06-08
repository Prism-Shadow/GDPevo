#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Correct task, portfolio, date, quarter, and policy identifiers.",
        "field": "identity",
    },
    {
        "id": "SP002",
        "weight": 3,
        "goal": "Correct allocation view rows for the requested opportunity sets.",
        "field": "allocation_views",
    },
    {
        "id": "SP003",
        "weight": 3,
        "goal": "Correct energy credit rotation action and trade tickets.",
        "field": "energy_action_core",
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "Correct energy post-trade metrics and constraint flags.",
        "field": "energy_metrics_flags",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct international equity correlation summary.",
        "field": "correlation_summary",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Correct international diversification action.",
        "field": "international_action",
    },
    {
        "id": "SP007",
        "weight": 2,
        "goal": "Correct committee decision, trigger, and priority order.",
        "field": "committee_decision",
    },
    {
        "id": "SP008",
        "weight": 2,
        "goal": "Correct final risk flags.",
        "field": "risk_flags",
    },
]


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def round_number(value, digits):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), digits)
    return value


def normalize_identity(data):
    return {
        "task_id": data.get("task_id"),
        "portfolio_id": data.get("portfolio_id"),
        "as_of_date": data.get("as_of_date"),
        "review_quarter": data.get("review_quarter"),
        "policy_id": data.get("policy_id"),
    }


def normalize_allocation_views(value):
    if not isinstance(value, list):
        return value
    rows = []
    for row in value:
        if not isinstance(row, dict):
            rows.append(row)
            continue
        rows.append(
            {
                "opportunity_set": row.get("opportunity_set"),
                "asset_class": row.get("asset_class"),
                "prior_view": row.get("prior_view"),
                "signal_score": round_number(row.get("signal_score"), 3),
                "view": row.get("view"),
                "change": row.get("change"),
                "conviction": row.get("conviction"),
                "rationale_code": row.get("rationale_code"),
            }
        )
    return sorted(rows, key=lambda item: str(item.get("opportunity_set")) if isinstance(item, dict) else str(item))


def normalize_trades(value):
    if not isinstance(value, list):
        return value
    action_rank = {"SELL": 0, "BUY": 1, "HOLD": 2, "NO_TRADE": 3}
    rows = []
    for row in value:
        if not isinstance(row, dict):
            rows.append(row)
            continue
        rows.append(
            {
                "action": row.get("action"),
                "instrument_id": row.get("instrument_id"),
                "notional_usd_m": round_number(row.get("notional_usd_m"), 1),
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            action_rank.get(item.get("action"), 99) if isinstance(item, dict) else 99,
            str(item.get("instrument_id")) if isinstance(item, dict) else str(item),
        ),
    )


def normalize_energy_action_core(data):
    action = data.get("energy_credit_action")
    if not isinstance(action, dict):
        return action
    return {
        "action_type": action.get("action_type"),
        "theme": action.get("theme"),
        "trades": normalize_trades(action.get("trades")),
    }


def normalize_energy_metrics_flags(data):
    action = data.get("energy_credit_action")
    if not isinstance(action, dict):
        return action
    metrics = action.get("metrics") if isinstance(action.get("metrics"), dict) else {}
    flags = action.get("constraint_flags") if isinstance(action.get("constraint_flags"), dict) else {}
    return {
        "metrics": {
            "current_hy_allocation_pct": round_number(metrics.get("current_hy_allocation_pct"), 2),
            "post_trade_hy_allocation_pct": round_number(metrics.get("post_trade_hy_allocation_pct"), 2),
            "current_weighted_duration_years": round_number(metrics.get("current_weighted_duration_years"), 2),
            "post_trade_weighted_duration_years": round_number(metrics.get("post_trade_weighted_duration_years"), 2),
            "current_max_issuer_concentration_pct": round_number(
                metrics.get("current_max_issuer_concentration_pct"), 2
            ),
            "post_trade_max_issuer_concentration_pct": round_number(
                metrics.get("post_trade_max_issuer_concentration_pct"), 2
            ),
        },
        "constraint_flags": {
            "post_trade_hy_cap_pass": flags.get("post_trade_hy_cap_pass"),
            "post_trade_duration_band_pass": flags.get("post_trade_duration_band_pass"),
            "post_trade_issuer_concentration_pass": flags.get("post_trade_issuer_concentration_pass"),
            "watchlist_avoidance_pass": flags.get("watchlist_avoidance_pass"),
        },
    }


def normalize_correlation_summary(data):
    section = data.get("international_diversification")
    if not isinstance(section, dict):
        return section
    value = section.get("correlation_summary")
    if not isinstance(value, list):
        return value
    rows = []
    for row in value:
        if not isinstance(row, dict):
            rows.append(row)
            continue
        pair = row.get("pair")
        if isinstance(pair, list):
            pair = sorted(str(item) for item in pair)
        rows.append(
            {
                "pair_role": row.get("pair_role"),
                "pair": pair,
                "correlation": round_number(row.get("correlation"), 3),
                "threshold_breached": row.get("threshold_breached"),
            }
        )
    role_rank = {"highest_concentration": 0, "best_diversifier": 1}
    return sorted(rows, key=lambda item: role_rank.get(item.get("pair_role"), 99) if isinstance(item, dict) else 99)


def normalize_international_action(data):
    section = data.get("international_diversification")
    if not isinstance(section, dict):
        return section
    action = section.get("action")
    if not isinstance(action, dict):
        return action
    return {
        "action_type": action.get("action_type"),
        "trim_index_id": action.get("trim_index_id"),
        "add_index_id": action.get("add_index_id"),
        "rationale_code": action.get("rationale_code"),
    }


def normalize_committee_decision(data):
    value = data.get("committee_decision")
    if not isinstance(value, dict):
        return value
    return {
        "decision": value.get("decision"),
        "rebalance_trigger": value.get("rebalance_trigger"),
        "priority_order": value.get("priority_order"),
    }


def normalize_risk_flags(data):
    value = data.get("risk_flags")
    if not isinstance(value, dict):
        return value
    keys = [
        "correlation_threshold_breached",
        "china_dependence_flag",
        "current_issuer_concentration_breach",
        "post_trade_issuer_concentration_breach",
        "hy_cap_pressure",
        "duration_drift",
        "high_yield_underweight_signal",
    ]
    return {key: value.get(key) for key in keys}


def normalize_field(field, data):
    if field == "identity":
        return normalize_identity(data)
    if field == "allocation_views":
        return normalize_allocation_views(data.get("allocation_views"))
    if field == "energy_action_core":
        return normalize_energy_action_core(data)
    if field == "energy_metrics_flags":
        return normalize_energy_metrics_flags(data)
    if field == "correlation_summary":
        return normalize_correlation_summary(data)
    if field == "international_action":
        return normalize_international_action(data)
    if field == "committee_decision":
        return normalize_committee_decision(data)
    if field == "risk_flags":
        return normalize_risk_flags(data)
    return data.get(field)


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
        sys.exit(2)

    prediction_path = Path(sys.argv[1])
    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"

    try:
        prediction = load_json(prediction_path)
        answer = load_json(answer_path)
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
        sys.exit(1)

    score = 0
    details = []
    for point in POINTS:
        expected = normalize_field(point["field"], answer)
        actual = normalize_field(point["field"], prediction)
        matched = actual == expected
        earned = point["weight"] if matched else 0
        score += earned
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "earned": earned,
                "matched": matched,
                "expected": expected,
                "actual": actual,
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


if __name__ == "__main__":
    main()
